"""Admin statistics keyboard for CyberVPN Telegram Bot.

Provides navigation for various statistics views with pagination support.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

if TYPE_CHECKING:
    from collections.abc import Callable


def admin_stats_keyboard(
    i18n: Callable[[str], str],
    current_page: int = 0,
    total_pages: int = 1,
    has_prev: bool = False,
    has_next: bool = False,
) -> InlineKeyboardMarkup:
    """Build admin statistics keyboard with pagination.

    Args:
        i18n: Fluent translator function for localization.
        current_page: Current page number (0-indexed).
        total_pages: Total number of pages available.
        has_prev: Whether previous page is available.
        has_next: Whether next page is available.

    Returns:
        InlineKeyboardMarkup with stats navigation and pagination.
    """
    builder = InlineKeyboardBuilder()

    # Statistics sections
    builder.button(
        text=i18n("stats-overview"),
        callback_data="stats:overview",
        style="primary",
    )
    builder.button(
        text=i18n("stats-users"),
        callback_data="stats:users",
        style="primary",
    )
    builder.button(
        text=i18n("stats-revenue"),
        callback_data="stats:revenue",
        style="primary",
    )
    builder.button(
        text=i18n("stats-traffic"),
        callback_data="stats:traffic",
        style="primary",
    )

    # Pagination controls (if applicable)
    if total_pages > 1:
        pagination_row = []
        if has_prev:
            pagination_row.append(
                InlineKeyboardButton(
                    text=i18n("pagination-prev"),
                    callback_data=f"stats:page:{current_page - 1}",
                    style="primary",
                )
            )

        # Page indicator
        pagination_row.append(
            InlineKeyboardButton(
                text=f"{current_page + 1}/{total_pages}",
                callback_data="stats:page:current",
            )
        )

        if has_next:
            pagination_row.append(
                InlineKeyboardButton(
                    text=i18n("pagination-next"),
                    callback_data=f"stats:page:{current_page + 1}",
                    style="primary",
                )
            )

        # Add pagination row to builder
        for btn in pagination_row:
            builder.add(btn)

    # Navigation
    builder.button(
        text=i18n("button-back"),
        callback_data="admin:main",
        style="primary",
    )

    # Layout: 2 stats per row, pagination in one row, back button alone
    if total_pages > 1:
        builder.adjust(2, 2, len(pagination_row), 1)
    else:
        builder.adjust(2, 2, 1)

    return builder.as_markup()
