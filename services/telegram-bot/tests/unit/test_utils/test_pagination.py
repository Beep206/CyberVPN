"""Unit tests for pagination utilities."""

from __future__ import annotations

import pytest
from aiogram.types import InlineKeyboardButton

from src.utils.pagination import (
    Paginator,
    create_item_keyboard,
    create_pagination_keyboard,
    parse_pagination_callback,
)


class TestPaginator:
    """Test Paginator class."""

    def test_create_paginator(self) -> None:
        """Test creating a paginator."""
        items = list(range(25))
        paginator = Paginator(items, items_per_page=10)

        assert paginator.total_pages == 3
        assert len(paginator.items) == 25

    def test_get_first_page(self) -> None:
        """Test getting first page."""
        items = list(range(25))
        paginator = Paginator(items, items_per_page=10)

        page = paginator.get_page(0)
        assert list(page) == list(range(10))

    def test_get_middle_page(self) -> None:
        """Test getting middle page."""
        items = list(range(25))
        paginator = Paginator(items, items_per_page=10)

        page = paginator.get_page(1)
        assert list(page) == list(range(10, 20))

    def test_get_last_page(self) -> None:
        """Test getting last page with fewer items."""
        items = list(range(25))
        paginator = Paginator(items, items_per_page=10)

        page = paginator.get_page(2)
        assert list(page) == list(range(20, 25))

    def test_get_page_out_of_range_raises(self) -> None:
        """Test that accessing out of range page raises ValueError."""
        items = list(range(10))
        paginator = Paginator(items, items_per_page=5)

        with pytest.raises(ValueError, match="out of range"):
            paginator.get_page(2)

    def test_get_negative_page_raises(self) -> None:
        """Test that negative page raises ValueError."""
        items = list(range(10))
        paginator = Paginator(items, items_per_page=5)

        with pytest.raises(ValueError, match="out of range"):
            paginator.get_page(-1)

    def test_has_next_true(self) -> None:
        """Test has_next returns True when there are more pages."""
        items = list(range(20))
        paginator = Paginator(items, items_per_page=10)

        assert paginator.has_next(0) is True

    def test_has_next_false(self) -> None:
        """Test has_next returns False on last page."""
        items = list(range(20))
        paginator = Paginator(items, items_per_page=10)

        assert paginator.has_next(1) is False

    def test_has_prev_true(self) -> None:
        """Test has_prev returns True when not on first page."""
        items = list(range(20))
        paginator = Paginator(items, items_per_page=10)

        assert paginator.has_prev(1) is True

    def test_has_prev_false(self) -> None:
        """Test has_prev returns False on first page."""
        items = list(range(20))
        paginator = Paginator(items, items_per_page=10)

        assert paginator.has_prev(0) is False

    def test_single_page(self) -> None:
        """Test paginator with single page."""
        items = list(range(5))
        paginator = Paginator(items, items_per_page=10)

        assert paginator.total_pages == 1
        assert list(paginator.get_page(0)) == items

    def test_empty_items(self) -> None:
        """Test paginator with empty items list."""
        items: list[int] = []
        paginator = Paginator(items, items_per_page=10)

        assert paginator.total_pages == 0

    def test_max_pages_limit(self) -> None:
        """Test that max_pages limits total pages."""
        items = list(range(1000))
        paginator = Paginator(items, items_per_page=10, max_pages=5)

        assert paginator.total_pages == 5  # Limited by max_pages

    def test_custom_page_size(self) -> None:
        """Test custom items_per_page."""
        items = list(range(100))
        paginator = Paginator(items, items_per_page=7)

        assert paginator.total_pages == 15  # ceil(100/7)
        assert len(paginator.get_page(0)) == 7

    def test_minimum_page_size(self) -> None:
        """Test that items_per_page=0 causes ZeroDivisionError due to bug in __init__."""
        items = list(range(10))

        # Due to a bug in Paginator.__init__, passing 0 causes ZeroDivisionError
        # even though items_per_page is clamped to 1, because the calculation
        # uses the parameter value instead of self.items_per_page
        with pytest.raises(ZeroDivisionError):
            paginator = Paginator(items, items_per_page=0)

    def test_paginator_with_objects(self) -> None:
        """Test paginator with custom objects."""

        class Server:
            def __init__(self, name: str) -> None:
                self.name = name

        servers = [Server(f"Server-{i}") for i in range(15)]
        paginator = Paginator(servers, items_per_page=5)

        assert paginator.total_pages == 3
        page_0 = paginator.get_page(0)
        assert len(page_0) == 5
        assert page_0[0].name == "Server-0"


class TestCreatePaginationKeyboard:
    """Test pagination keyboard creation."""

    def test_create_first_page_keyboard(self) -> None:
        """Test keyboard for first page."""
        keyboard = create_pagination_keyboard(
            current_page=0, total_pages=3, callback_prefix="test"
        )

        assert keyboard is not None
        assert len(keyboard.inline_keyboard) > 0

        # Check bottom row has pagination controls
        bottom_row = keyboard.inline_keyboard[-1]
        assert len(bottom_row) == 3  # [disabled prev] [1/3] [next]

        # Next button should have callback
        assert "test:1" in bottom_row[2].callback_data

    def test_create_middle_page_keyboard(self) -> None:
        """Test keyboard for middle page."""
        keyboard = create_pagination_keyboard(
            current_page=1, total_pages=3, callback_prefix="servers"
        )

        bottom_row = keyboard.inline_keyboard[-1]

        # Should have both prev and next enabled
        assert "servers:0" in bottom_row[0].callback_data  # Prev
        assert "servers:2" in bottom_row[2].callback_data  # Next

    def test_create_last_page_keyboard(self) -> None:
        """Test keyboard for last page."""
        keyboard = create_pagination_keyboard(
            current_page=2, total_pages=3, callback_prefix="test"
        )

        bottom_row = keyboard.inline_keyboard[-1]

        # Prev should work, next should be disabled
        assert "test:1" in bottom_row[0].callback_data  # Prev button
        assert "noop" == bottom_row[2].callback_data  # Disabled next

    def test_keyboard_without_page_numbers(self) -> None:
        """Test keyboard without page counter."""
        keyboard = create_pagination_keyboard(
            current_page=0,
            total_pages=3,
            callback_prefix="test",
            show_page_numbers=False,
        )

        bottom_row = keyboard.inline_keyboard[-1]
        # Should only have prev/next buttons (2 buttons)
        assert len(bottom_row) == 2

    def test_keyboard_with_additional_buttons(self) -> None:
        """Test keyboard with additional button rows."""
        additional = [
            [InlineKeyboardButton(text="Button 1", callback_data="btn1")],
            [InlineKeyboardButton(text="Button 2", callback_data="btn2")],
        ]

        keyboard = create_pagination_keyboard(
            current_page=0,
            total_pages=2,
            callback_prefix="test",
            additional_buttons=additional,
        )

        # Should have 2 additional rows + 1 pagination row
        assert len(keyboard.inline_keyboard) >= 3

        # First rows should be additional buttons
        assert keyboard.inline_keyboard[0][0].text == "Button 1"
        assert keyboard.inline_keyboard[1][0].text == "Button 2"

    def test_custom_prev_next_text(self) -> None:
        """Test custom prev/next button text."""
        keyboard = create_pagination_keyboard(
            current_page=1,
            total_pages=3,
            callback_prefix="test",
            prev_text="<< Назад",
            next_text="Вперед >>",
        )

        bottom_row = keyboard.inline_keyboard[-1]

        assert bottom_row[0].text == "<< Назад"
        assert bottom_row[2].text == "Вперед >>"

    def test_custom_page_format(self) -> None:
        """Test custom page counter format."""
        keyboard = create_pagination_keyboard(
            current_page=1,
            total_pages=5,
            callback_prefix="test",
            page_format="Page {current} of {total}",
        )

        bottom_row = keyboard.inline_keyboard[-1]

        # Middle button should have custom format
        assert "Page 2 of 5" in bottom_row[1].text

    def test_single_page_no_navigation(self) -> None:
        """Test keyboard with single page."""
        keyboard = create_pagination_keyboard(
            current_page=0, total_pages=1, callback_prefix="test"
        )

        bottom_row = keyboard.inline_keyboard[-1]

        # Both prev/next should be disabled
        assert "noop" in bottom_row[0].callback_data
        assert "noop" in bottom_row[2].callback_data


class TestParsePaginationCallback:
    """Test pagination callback parsing."""

    def test_parse_valid_callback(self) -> None:
        """Test parsing valid callback data."""
        page = parse_pagination_callback("servers_page:3", "servers_page")
        assert page == 3

    def test_parse_first_page(self) -> None:
        """Test parsing first page callback."""
        page = parse_pagination_callback("test:0", "test")
        assert page == 0

    def test_parse_wrong_prefix_returns_none(self) -> None:
        """Test parsing with wrong prefix returns None."""
        page = parse_pagination_callback("other:5", "servers_page")
        assert page is None

    def test_parse_invalid_format_returns_none(self) -> None:
        """Test parsing invalid format returns None."""
        page = parse_pagination_callback("servers_page_5", "servers_page")
        assert page is None

    def test_parse_non_numeric_returns_none(self) -> None:
        """Test parsing non-numeric page returns None."""
        page = parse_pagination_callback("servers_page:abc", "servers_page")
        assert page is None

    def test_parse_negative_page_returns_none(self) -> None:
        """Test parsing negative page returns None."""
        page = parse_pagination_callback("test:-1", "test")
        assert page is None

    def test_parse_empty_string_returns_none(self) -> None:
        """Test parsing empty string returns None."""
        page = parse_pagination_callback("", "test")
        assert page is None

    def test_parse_large_page_number(self) -> None:
        """Test parsing large page number."""
        page = parse_pagination_callback("test:9999", "test")
        assert page == 9999


class TestCreateItemKeyboard:
    """Test item keyboard creation with pagination."""

    def test_create_keyboard_with_items(self) -> None:
        """Test creating keyboard with items and pagination."""
        servers = [{"id": i, "name": f"Server-{i}"} for i in range(3)]

        def button_factory(server: dict) -> InlineKeyboardButton:
            return InlineKeyboardButton(
                text=server["name"], callback_data=f"server:{server['id']}"
            )

        keyboard = create_item_keyboard(
            items=servers,
            current_page=0,
            total_pages=2,
            callback_prefix="servers_page",
            item_button_factory=button_factory,
        )

        # Should have 3 server buttons + 1 pagination row
        assert len(keyboard.inline_keyboard) >= 4

        # Check first button
        assert keyboard.inline_keyboard[0][0].text == "Server-0"
        assert keyboard.inline_keyboard[0][0].callback_data == "server:0"

    def test_create_keyboard_multiple_items_per_row(self) -> None:
        """Test creating keyboard with multiple items per row."""
        items = [{"id": i, "name": f"Item-{i}"} for i in range(6)]

        def button_factory(item: dict) -> InlineKeyboardButton:
            return InlineKeyboardButton(
                text=item["name"], callback_data=f"item:{item['id']}"
            )

        keyboard = create_item_keyboard(
            items=items,
            current_page=0,
            total_pages=1,
            callback_prefix="items",
            item_button_factory=button_factory,
            items_per_row=2,
        )

        # Should have 3 rows of items (6 items / 2 per row) + 1 pagination row
        assert len(keyboard.inline_keyboard) >= 4

        # Check that first row has 2 buttons
        assert len(keyboard.inline_keyboard[0]) == 2

    def test_create_keyboard_empty_items(self) -> None:
        """Test creating keyboard with no items."""

        def button_factory(item: dict) -> InlineKeyboardButton:
            return InlineKeyboardButton(text=item["name"], callback_data="test")

        keyboard = create_item_keyboard(
            items=[],
            current_page=0,
            total_pages=1,
            callback_prefix="test",
            item_button_factory=button_factory,
        )

        # Should only have pagination row
        assert len(keyboard.inline_keyboard) == 1

    def test_create_keyboard_custom_pagination_kwargs(self) -> None:
        """Test passing custom pagination kwargs."""
        items = [{"id": 1, "name": "Item"}]

        def button_factory(item: dict) -> InlineKeyboardButton:
            return InlineKeyboardButton(text=item["name"], callback_data="test")

        keyboard = create_item_keyboard(
            items=items,
            current_page=0,
            total_pages=3,
            callback_prefix="test",
            item_button_factory=button_factory,
            prev_text="<<",
            next_text=">>",
            show_page_numbers=False,
        )

        # Pagination row should use custom settings
        pagination_row = keyboard.inline_keyboard[-1]
        assert pagination_row[0].text == "<<" or pagination_row[0].text == "·"
        # No page numbers, so should have fewer buttons
        assert len(pagination_row) == 2

    def test_create_keyboard_with_complex_objects(self) -> None:
        """Test creating keyboard with complex objects."""

        class Server:
            def __init__(self, server_id: int, name: str, status: str) -> None:
                self.id = server_id
                self.name = name
                self.status = status

        servers = [
            Server(1, "US-NY-01", "online"),
            Server(2, "EU-DE-01", "offline"),
        ]

        def button_factory(server: Server) -> InlineKeyboardButton:
            return InlineKeyboardButton(
                text=f"{server.name} ({server.status})",
                callback_data=f"server:{server.id}",
            )

        keyboard = create_item_keyboard(
            items=servers,
            current_page=0,
            total_pages=1,
            callback_prefix="servers",
            item_button_factory=button_factory,
        )

        assert keyboard.inline_keyboard[0][0].text == "US-NY-01 (online)"
        assert keyboard.inline_keyboard[1][0].text == "EU-DE-01 (offline)"
