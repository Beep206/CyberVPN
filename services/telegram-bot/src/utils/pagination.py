"""Pagination utilities for inline keyboards."""

from __future__ import annotations

from typing import Any, Callable, Generic, Sequence, TypeVar

import structlog
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from .constants import ITEMS_PER_PAGE, MAX_PAGES

logger = structlog.get_logger(__name__)

T = TypeVar("T")


class Paginator(Generic[T]):
    """
    Generic paginator for splitting data into pages.

    Examples:
        >>> items = list(range(100))
        >>> paginator = Paginator(items, items_per_page=10)
        >>> paginator.total_pages
        10
        >>> paginator.get_page(0)
        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    """

    def __init__(
        self,
        items: Sequence[T],
        items_per_page: int = ITEMS_PER_PAGE,
        max_pages: int = MAX_PAGES,
    ):
        """
        Initialize paginator.

        Args:
            items: Sequence of items to paginate
            items_per_page: Number of items per page
            max_pages: Maximum number of pages to prevent abuse
        """
        self.items = items
        self.items_per_page = max(1, items_per_page)
        self.max_pages = max_pages
        self._total_pages = min(
            (len(items) + items_per_page - 1) // items_per_page,
            max_pages,
        )

    @property
    def total_pages(self) -> int:
        """Get total number of pages."""
        return self._total_pages

    def get_page(self, page: int) -> Sequence[T]:
        """
        Get items for a specific page.

        Args:
            page: Zero-indexed page number

        Returns:
            Sequence of items for the page

        Raises:
            ValueError: If page is out of range
        """
        if page < 0 or page >= self.total_pages:
            raise ValueError(f"Page {page} out of range [0, {self.total_pages})")

        start = page * self.items_per_page
        end = min(start + self.items_per_page, len(self.items))

        return self.items[start:end]

    def has_next(self, page: int) -> bool:
        """Check if there is a next page."""
        return page < self.total_pages - 1

    def has_prev(self, page: int) -> bool:
        """Check if there is a previous page."""
        return page > 0


def create_pagination_keyboard(
    current_page: int,
    total_pages: int,
    callback_prefix: str,
    additional_buttons: list[list[InlineKeyboardButton]] | None = None,
    show_page_numbers: bool = True,
    prev_text: str = "◀️",
    next_text: str = "▶️",
    page_format: str = "{current}/{total}",
) -> InlineKeyboardMarkup:
    """
    Create an inline keyboard with pagination controls.

    Args:
        current_page: Current page (zero-indexed)
        total_pages: Total number of pages
        callback_prefix: Prefix for callback data (e.g., "servers_page")
        additional_buttons: Additional button rows to add above pagination
        show_page_numbers: Whether to show page counter
        prev_text: Text for previous button
        next_text: Text for next button
        page_format: Format string for page counter (current and total available)

    Returns:
        InlineKeyboardMarkup with pagination controls

    Examples:
        >>> kb = create_pagination_keyboard(0, 5, "servers_page")
        >>> # Creates keyboard: [Prev] [1/5] [Next]
    """
    builder = InlineKeyboardBuilder()

    # Add additional buttons if provided
    if additional_buttons:
        for row in additional_buttons:
            builder.row(*row)

    # Create pagination row
    pagination_row = []

    # Previous button
    if current_page > 0:
        pagination_row.append(
            InlineKeyboardButton(
                text=prev_text,
                callback_data=f"{callback_prefix}:{current_page - 1}",
            )
        )
    else:
        # Disabled previous button (no callback)
        pagination_row.append(
            InlineKeyboardButton(
                text="·",
                callback_data="noop",
            )
        )

    # Page counter
    if show_page_numbers:
        page_text = page_format.format(
            current=current_page + 1,
            total=total_pages,
        )
        pagination_row.append(
            InlineKeyboardButton(
                text=page_text,
                callback_data="noop",
            )
        )

    # Next button
    if current_page < total_pages - 1:
        pagination_row.append(
            InlineKeyboardButton(
                text=next_text,
                callback_data=f"{callback_prefix}:{current_page + 1}",
            )
        )
    else:
        # Disabled next button
        pagination_row.append(
            InlineKeyboardButton(
                text="·",
                callback_data="noop",
            )
        )

    builder.row(*pagination_row)

    return builder.as_markup()


def parse_pagination_callback(
    callback_data: str,
    prefix: str,
) -> int | None:
    """
    Parse page number from pagination callback data.

    Args:
        callback_data: Full callback data string
        prefix: Expected prefix

    Returns:
        Page number (zero-indexed) or None if parsing fails

    Examples:
        >>> parse_pagination_callback("servers_page:3", "servers_page")
        3
        >>> parse_pagination_callback("other:5", "servers_page")
        None
    """
    if not callback_data.startswith(f"{prefix}:"):
        return None

    try:
        page_str = callback_data.split(":", 1)[1]
        page = int(page_str)
        return page if page >= 0 else None
    except (IndexError, ValueError):
        logger.warning(
            "pagination_callback_parse_failed",
            callback_data=callback_data,
            prefix=prefix,
        )
        return None


def create_item_keyboard(
    items: Sequence[T],
    current_page: int,
    total_pages: int,
    callback_prefix: str,
    item_button_factory: Callable[[T], InlineKeyboardButton],
    items_per_row: int = 1,
    **pagination_kwargs: Any,
) -> InlineKeyboardMarkup:
    """
    Create a keyboard with items and pagination controls.

    Args:
        items: Items for current page
        current_page: Current page number (zero-indexed)
        total_pages: Total number of pages
        callback_prefix: Prefix for pagination callbacks
        item_button_factory: Function to create button from item
        items_per_row: Number of item buttons per row
        **pagination_kwargs: Additional kwargs for create_pagination_keyboard

    Returns:
        InlineKeyboardMarkup with items and pagination

    Examples:
        >>> def make_button(server: dict) -> InlineKeyboardButton:
        ...     return InlineKeyboardButton(
        ...         text=server["name"],
        ...         callback_data=f"server:{server['id']}"
        ...     )
        >>> servers = [{"id": 1, "name": "US-01"}, {"id": 2, "name": "EU-01"}]
        >>> kb = create_item_keyboard(
        ...     servers, 0, 1, "servers_page", make_button
        ... )
    """
    # Create item buttons
    item_buttons = [item_button_factory(item) for item in items]

    # Split into rows
    button_rows = []
    for i in range(0, len(item_buttons), items_per_row):
        row = item_buttons[i : i + items_per_row]
        button_rows.append(row)

    # Create pagination keyboard with item buttons
    return create_pagination_keyboard(
        current_page=current_page,
        total_pages=total_pages,
        callback_prefix=callback_prefix,
        additional_buttons=button_rows,
        **pagination_kwargs,
    )
