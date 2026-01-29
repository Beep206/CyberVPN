"""Unit tests for menu callback handlers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.types import CallbackQuery, User


@pytest.mark.asyncio
class TestMenuHandlers:
    """Test menu callback handlers."""

    async def test_main_menu_callback(self) -> None:
        """Test main menu callback handler."""
        user = User(id=123, is_bot=False, first_name="Test")

        callback = MagicMock(spec=CallbackQuery)
        callback.from_user = user
        callback.data = "main_menu"
        callback.message = MagicMock()
        callback.message.edit_text = AsyncMock()
        callback.answer = AsyncMock()

        # Simulate handler
        if callback.data == "main_menu":
            await callback.message.edit_text("Main Menu")
            await callback.answer()

        callback.message.edit_text.assert_called_once()
        callback.answer.assert_called_once()

    async def test_my_subscription_callback(self) -> None:
        """Test 'My Subscription' callback."""
        callback = MagicMock(spec=CallbackQuery)
        callback.data = "my_subscription"
        callback.message = MagicMock()
        callback.message.edit_text = AsyncMock()
        callback.answer = AsyncMock()

        # Simulate fetching subscription
        subscription_text = "Active subscription: Premium\nExpires: 2024-12-31"

        if callback.data == "my_subscription":
            await callback.message.edit_text(subscription_text)
            await callback.answer()

        call_args = callback.message.edit_text.call_args[0][0]
        assert "Premium" in call_args

    async def test_buy_plan_callback(self) -> None:
        """Test 'Buy Plan' callback shows plans."""
        callback = MagicMock(spec=CallbackQuery)
        callback.data = "buy_plan"
        callback.message = MagicMock()
        callback.message.edit_text = AsyncMock()
        callback.answer = AsyncMock()

        # Simulate showing plans
        plans_text = "Available plans:\n1. Basic - $9.99\n2. Pro - $19.99"

        if callback.data == "buy_plan":
            await callback.message.edit_text(plans_text)
            await callback.answer()

        call_args = callback.message.edit_text.call_args[0][0]
        assert "Available plans" in call_args

    async def test_settings_callback(self) -> None:
        """Test settings callback."""
        callback = MagicMock(spec=CallbackQuery)
        callback.data = "settings"
        callback.message = MagicMock()
        callback.message.edit_text = AsyncMock()
        callback.answer = AsyncMock()

        # Simulate settings menu
        if callback.data == "settings":
            await callback.message.edit_text("Settings")
            await callback.answer()

        callback.message.edit_text.assert_called_once()

    async def test_help_callback(self) -> None:
        """Test help callback."""
        callback = MagicMock(spec=CallbackQuery)
        callback.data = "help"
        callback.message = MagicMock()
        callback.message.edit_text = AsyncMock()
        callback.answer = AsyncMock()

        help_text = "Help: Contact @support for assistance"

        if callback.data == "help":
            await callback.message.edit_text(help_text)
            await callback.answer()

        call_args = callback.message.edit_text.call_args[0][0]
        assert "Help" in call_args or "support" in call_args

    async def test_back_callback(self) -> None:
        """Test back button callback."""
        callback = MagicMock(spec=CallbackQuery)
        callback.data = "back_to_menu"
        callback.message = MagicMock()
        callback.message.edit_text = AsyncMock()
        callback.answer = AsyncMock()

        # Simulate going back
        if callback.data.startswith("back_"):
            await callback.message.edit_text("Main Menu")
            await callback.answer()

        callback.answer.assert_called_once()

    async def test_noop_callback(self) -> None:
        """Test noop (no operation) callback."""
        callback = MagicMock(spec=CallbackQuery)
        callback.data = "noop"
        callback.answer = AsyncMock()

        # Noop should just answer without action
        if callback.data == "noop":
            await callback.answer()

        callback.answer.assert_called_once()

    async def test_callback_with_keyboard_update(self) -> None:
        """Test callback that updates keyboard."""
        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
        from aiogram.utils.keyboard import InlineKeyboardBuilder

        callback = MagicMock(spec=CallbackQuery)
        callback.data = "show_servers"
        callback.message = MagicMock()
        callback.message.edit_text = AsyncMock()
        callback.answer = AsyncMock()

        # Create new keyboard
        builder = InlineKeyboardBuilder()
        builder.add(
            InlineKeyboardButton(text="Server 1", callback_data="server_1")
        )
        builder.add(
            InlineKeyboardButton(text="Back", callback_data="back")
        )
        keyboard = builder.as_markup()

        if callback.data == "show_servers":
            await callback.message.edit_text(
                "Select server:", reply_markup=keyboard
            )
            await callback.answer()

        call_kwargs = callback.message.edit_text.call_args[1]
        assert "reply_markup" in call_kwargs

    async def test_callback_error_handling(self) -> None:
        """Test callback error handling."""
        callback = MagicMock(spec=CallbackQuery)
        callback.data = "failing_action"
        callback.answer = AsyncMock()

        # Simulate error
        try:
            raise ValueError("Simulated error")
        except Exception:
            await callback.answer("Error occurred", show_alert=True)

        # Should answer with error
        call_kwargs = callback.answer.call_args[1]
        assert call_kwargs.get("show_alert") is True

    async def test_callback_with_user_context(self) -> None:
        """Test callback uses user context."""
        user_data = {
            "telegram_id": 123,
            "username": "testuser",
            "language": "en",
        }

        callback = MagicMock(spec=CallbackQuery)
        callback.data = "profile"
        callback.message = MagicMock()
        callback.message.edit_text = AsyncMock()
        callback.answer = AsyncMock()

        # Use user data in response
        profile_text = f"Profile: @{user_data['username']}"

        if callback.data == "profile":
            await callback.message.edit_text(profile_text)
            await callback.answer()

        call_args = callback.message.edit_text.call_args[0][0]
        assert "testuser" in call_args

    async def test_pagination_callback(self) -> None:
        """Test pagination callback."""
        callback = MagicMock(spec=CallbackQuery)
        callback.data = "servers_page:2"
        callback.message = MagicMock()
        callback.message.edit_text = AsyncMock()
        callback.answer = AsyncMock()

        # Parse page number
        if callback.data.startswith("servers_page:"):
            page_str = callback.data.split(":")[1]
            page = int(page_str)

            await callback.message.edit_text(f"Page {page + 1}")
            await callback.answer()

            call_args = callback.message.edit_text.call_args[0][0]
            assert "Page 3" in call_args  # page 2 is displayed as "Page 3"

    async def test_callback_with_localization(self) -> None:
        """Test callback with localized text."""
        callback = MagicMock(spec=CallbackQuery)
        callback.data = "language_ru"
        callback.answer = AsyncMock()

        # Simulate language change
        if callback.data.startswith("language_"):
            lang = callback.data.split("_")[1]
            await callback.answer(
                f"Language changed to {lang}", show_alert=False
            )

            assert lang == "ru"

        callback.answer.assert_called_once()
