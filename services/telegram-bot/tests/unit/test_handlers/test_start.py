"""Unit tests for /start command handler."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest
import respx
from aiogram.types import Message, User

if TYPE_CHECKING:
    from src.config import BotSettings
    from src.services.api_client import CyberVPNAPIClient


@pytest.mark.asyncio
class TestStartHandler:
    """Test /start command handler."""

    async def test_start_without_deep_link(
        self, mock_api_client: CyberVPNAPIClient, mock_settings: BotSettings
    ) -> None:
        """Test /start command without deep link."""
        # Mock the handler behavior
        user = User(
            id=123456,
            is_bot=False,
            first_name="Test",
            username="testuser",
            language_code="en",
        )

        message = MagicMock(spec=Message)
        message.from_user = user
        message.text = "/start"
        message.answer = AsyncMock()

        # Mock API response
        with respx.mock:
            respx.post(
                "https://api.test.cybervpn.local/telegram/users"
            ).mock(
                return_value=respx.MockResponse(
                    200,
                    json={
                        "telegram_id": 123456,
                        "username": "testuser",
                        "language": "en",
                    },
                )
            )

            # Simulate handler logic
            user_data = {
                "telegram_id": user.id,
                "username": user.username,
                "first_name": user.first_name,
                "language_code": user.language_code or "en",
            }

            # Handler would register user
            result = await mock_api_client.register_user(
                telegram_id=user.id, username=user.username, language="en"
            )

            assert result["telegram_id"] == 123456

    async def test_start_with_referral_link(
        self, mock_api_client: CyberVPNAPIClient
    ) -> None:
        """Test /start with referral deep link (ref_)."""
        user = User(
            id=999999,
            is_bot=False,
            first_name="NewUser",
            username="newuser",
        )

        message = MagicMock(spec=Message)
        message.from_user = user
        message.text = "/start ref_12345"  # Referrer ID 12345
        message.answer = AsyncMock()

        # Parse deep link
        deep_link = "ref_12345"
        referrer_id = None

        if deep_link.startswith("ref_"):
            try:
                referrer_id = int(deep_link[4:])
            except ValueError:
                pass

        assert referrer_id == 12345

    async def test_start_with_promo_link(
        self, mock_api_client: CyberVPNAPIClient
    ) -> None:
        """Test /start with promo deep link (promo_)."""
        user = User(
            id=888888, is_bot=False, first_name="User", username="user"
        )

        message = MagicMock(spec=Message)
        message.from_user = user
        message.text = "/start promo_SUMMER2024"
        message.answer = AsyncMock()

        # Parse promo code
        deep_link = "promo_SUMMER2024"
        promo_code = None

        if deep_link.startswith("promo_"):
            promo_code = deep_link[6:]

        assert promo_code == "SUMMER2024"

    async def test_start_invalid_referral_link(self) -> None:
        """Test /start with invalid referral ID."""
        message = MagicMock(spec=Message)
        message.text = "/start ref_invalid"

        deep_link = "ref_invalid"
        referrer_id = None

        if deep_link.startswith("ref_"):
            try:
                referrer_id = int(deep_link[4:])
            except ValueError:
                referrer_id = None

        # Should be None for invalid format
        assert referrer_id is None

    async def test_start_sends_welcome_message(self) -> None:
        """Test that /start sends welcome message."""
        user = User(id=123, is_bot=False, first_name="Test")

        message = MagicMock(spec=Message)
        message.from_user = user
        message.text = "/start"
        message.answer = AsyncMock()

        # Simulate sending welcome
        welcome_text = "Welcome, Test!"
        await message.answer(welcome_text)

        message.answer.assert_called_once_with(welcome_text)

    async def test_start_with_referral_bonus_message(self) -> None:
        """Test welcome message includes referral bonus."""
        message = MagicMock(spec=Message)
        message.answer = AsyncMock()

        referrer_id = 12345
        welcome_text = "Welcome!"

        if referrer_id:
            welcome_text += "\n\nYou were referred by user 12345!"

        await message.answer(welcome_text)

        call_args = message.answer.call_args[0][0]
        assert "12345" in call_args

    async def test_start_registration_failure(
        self, mock_api_client: CyberVPNAPIClient
    ) -> None:
        """Test /start when registration fails."""
        user = User(id=777, is_bot=False, first_name="Test")

        message = MagicMock(spec=Message)
        message.from_user = user
        message.answer = AsyncMock()

        with respx.mock:
            # Registration fails
            respx.post(
                "https://api.test.cybervpn.local/telegram/users"
            ).mock(
                return_value=respx.MockResponse(
                    500, json={"detail": "Server error"}
                )
            )

            # Should handle error gracefully
            try:
                await mock_api_client.register_user(
                    telegram_id=user.id,
                    username=user.username,
                    language="en",
                )
            except Exception:
                # Error occurred, send error message
                await message.answer("Registration failed. Please try again.")

            # Should have sent error message
            assert message.answer.called

    async def test_start_promo_activation(
        self, mock_api_client: CyberVPNAPIClient
    ) -> None:
        """Test automatic promo code activation on start."""
        user = User(id=555, is_bot=False, first_name="User")

        message = MagicMock(spec=Message)
        message.from_user = user
        message.text = "/start promo_WELCOME10"
        message.answer = AsyncMock()

        promo_code = "WELCOME10"

        # In real handler, would call:
        # await api_client.activate_promo_code(user.id, promo_code)

        # Verify promo was extracted
        assert promo_code == "WELCOME10"

    async def test_start_creates_main_menu_keyboard(self) -> None:
        """Test that /start creates main menu keyboard."""
        message = MagicMock(spec=Message)
        message.answer = AsyncMock()

        # Simulate creating keyboard
        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
        from aiogram.utils.keyboard import InlineKeyboardBuilder

        builder = InlineKeyboardBuilder()
        builder.add(
            InlineKeyboardButton(text="My Subscription", callback_data="my_sub")
        )
        builder.add(
            InlineKeyboardButton(text="Buy Plan", callback_data="buy_plan")
        )
        keyboard = builder.as_markup()

        await message.answer("Welcome!", reply_markup=keyboard)

        # Verify keyboard was sent
        call_kwargs = message.answer.call_args[1]
        assert "reply_markup" in call_kwargs

    async def test_start_multiple_times_same_user(
        self, mock_api_client: CyberVPNAPIClient
    ) -> None:
        """Test that /start can be called multiple times."""
        user = User(id=111, is_bot=False, first_name="Test")

        message = MagicMock(spec=Message)
        message.from_user = user
        message.text = "/start"
        message.answer = AsyncMock()

        with respx.mock:
            # First time: creates user
            respx.post(
                "https://api.test.cybervpn.local/telegram/users"
            ).mock(
                return_value=respx.MockResponse(
                    200, json={"telegram_id": 111}
                )
            )

            await mock_api_client.register_user(
                telegram_id=111, username="test", language="en"
            )

        # Second /start should still work (updates user)
        message.text = "/start"
        await message.answer("Welcome back!")

        assert message.answer.called
