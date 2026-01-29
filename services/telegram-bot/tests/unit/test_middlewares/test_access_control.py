"""Unit tests for access control middleware."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.types import CallbackQuery, ChatMemberMember, Message, User

from src.middlewares.access_control import AccessControlMiddleware

if TYPE_CHECKING:
    from aiogram import Bot

    from src.config import BotSettings


@pytest.mark.asyncio
class TestAccessControlMiddleware:
    """Test access control middleware."""

    async def test_allows_access_in_open_mode(
        self, mock_settings: BotSettings, mock_bot: Bot
    ) -> None:
        """Test that open mode allows all users."""
        middleware = AccessControlMiddleware(
            bot_settings=mock_settings, bot=mock_bot
        )

        user_data = {"telegram_id": 123456, "username": "test"}
        data = {
            "user": user_data,
            "settings": {"access_mode": "open"},
        }

        message = MagicMock(spec=Message)
        handler = AsyncMock(return_value="ok")

        result = await middleware(handler, message, data)

        assert result == "ok"
        assert handler.called

    async def test_blocks_non_admin_in_maintenance_mode(
        self, mock_settings: BotSettings, mock_bot: Bot
    ) -> None:
        """Test that maintenance mode blocks non-admins."""
        middleware = AccessControlMiddleware(
            bot_settings=mock_settings, bot=mock_bot
        )

        user_data = {"telegram_id": 999999, "username": "regular_user"}
        data = {
            "user": user_data,
            "settings": {"access_mode": "maintenance"},
        }

        message = MagicMock(spec=Message)
        message.answer = AsyncMock()
        handler = AsyncMock()

        result = await middleware(handler, message, data)

        assert result is None  # Blocked
        assert not handler.called
        assert message.answer.called

    async def test_allows_admin_in_maintenance_mode(
        self, mock_settings: BotSettings, mock_bot: Bot
    ) -> None:
        """Test that admins bypass maintenance mode."""
        admin_id = mock_settings.admin_ids[0]

        middleware = AccessControlMiddleware(
            bot_settings=mock_settings, bot=mock_bot
        )

        user_data = {"telegram_id": admin_id, "username": "admin"}
        data = {
            "user": user_data,
            "settings": {"access_mode": "maintenance"},
        }

        message = MagicMock(spec=Message)
        handler = AsyncMock(return_value="ok")

        result = await middleware(handler, message, data)

        assert result == "ok"
        assert handler.called

    async def test_blocks_user_without_rules_acceptance(
        self, mock_settings: BotSettings, mock_bot: Bot
    ) -> None:
        """Test that users must accept rules if required."""
        middleware = AccessControlMiddleware(
            bot_settings=mock_settings, bot=mock_bot
        )

        user_data = {
            "telegram_id": 123,
            "has_accepted_rules": False,
        }
        data = {
            "user": user_data,
            "settings": {
                "access_mode": "open",
                "rules_url": "https://example.com/rules",
            },
        }

        message = MagicMock(spec=Message)
        message.answer = AsyncMock()
        handler = AsyncMock()

        result = await middleware(handler, message, data)

        assert result is None
        assert not handler.called
        assert message.answer.called
        # Check rules message was sent
        call_args = message.answer.call_args[0][0]
        assert "rules" in call_args.lower() or "правила" in call_args.lower()

    async def test_allows_user_with_rules_accepted(
        self, mock_settings: BotSettings, mock_bot: Bot
    ) -> None:
        """Test that users with accepted rules can access."""
        middleware = AccessControlMiddleware(
            bot_settings=mock_settings, bot=mock_bot
        )

        user_data = {
            "telegram_id": 123,
            "has_accepted_rules": True,
        }
        data = {
            "user": user_data,
            "settings": {
                "access_mode": "open",
                "rules_url": "https://example.com/rules",
            },
        }

        message = MagicMock(spec=Message)
        handler = AsyncMock(return_value="ok")

        result = await middleware(handler, message, data)

        assert result == "ok"
        assert handler.called

    async def test_admin_bypasses_rules_requirement(
        self, mock_settings: BotSettings, mock_bot: Bot
    ) -> None:
        """Test that admins bypass rules acceptance."""
        admin_id = mock_settings.admin_ids[0]

        middleware = AccessControlMiddleware(
            bot_settings=mock_settings, bot=mock_bot
        )

        user_data = {
            "telegram_id": admin_id,
            "has_accepted_rules": False,
        }
        data = {
            "user": user_data,
            "settings": {
                "access_mode": "open",
                "rules_url": "https://example.com/rules",
            },
        }

        message = MagicMock(spec=Message)
        handler = AsyncMock(return_value="ok")

        result = await middleware(handler, message, data)

        assert result == "ok"
        assert handler.called

    async def test_blocks_unsubscribed_user(
        self, mock_settings: BotSettings, mock_bot: Bot
    ) -> None:
        """Test that unsubscribed users are blocked."""
        middleware = AccessControlMiddleware(
            bot_settings=mock_settings, bot=mock_bot
        )

        # Mock bot.get_chat_member to return "left" status
        from aiogram.types import ChatMemberLeft

        mock_bot.get_chat_member = AsyncMock(
            return_value=ChatMemberLeft(
                user=User(id=123, is_bot=False, first_name="Test"),
                status="left",
            )
        )

        user_data = {"telegram_id": 123}
        data = {
            "user": user_data,
            "settings": {
                "access_mode": "open",
                "channel_id": "@test_channel",
            },
        }

        message = MagicMock(spec=Message)
        message.answer = AsyncMock()
        handler = AsyncMock()

        result = await middleware(handler, message, data)

        assert result is None
        assert not handler.called
        assert message.answer.called

    async def test_allows_subscribed_user(
        self, mock_settings: BotSettings, mock_bot: Bot
    ) -> None:
        """Test that subscribed users can access."""
        middleware = AccessControlMiddleware(
            bot_settings=mock_settings, bot=mock_bot
        )

        # Mock bot.get_chat_member to return "member" status
        mock_bot.get_chat_member = AsyncMock(
            return_value=ChatMemberMember(
                user=User(id=123, is_bot=False, first_name="Test"),
                status="member",
            )
        )

        user_data = {"telegram_id": 123}
        data = {
            "user": user_data,
            "settings": {
                "access_mode": "open",
                "channel_id": "@test_channel",
            },
        }

        message = MagicMock(spec=Message)
        handler = AsyncMock(return_value="ok")

        result = await middleware(handler, message, data)

        assert result == "ok"
        assert handler.called

    async def test_admin_bypasses_channel_subscription(
        self, mock_settings: BotSettings, mock_bot: Bot
    ) -> None:
        """Test that admins bypass channel subscription."""
        admin_id = mock_settings.admin_ids[0]

        middleware = AccessControlMiddleware(
            bot_settings=mock_settings, bot=mock_bot
        )

        user_data = {"telegram_id": admin_id}
        data = {
            "user": user_data,
            "settings": {
                "access_mode": "open",
                "channel_id": "@test_channel",
            },
        }

        message = MagicMock(spec=Message)
        handler = AsyncMock(return_value="ok")

        result = await middleware(handler, message, data)

        assert result == "ok"
        assert handler.called
        # get_chat_member should not be called for admin
        assert not mock_bot.get_chat_member.called

    async def test_channel_check_fails_open_on_error(
        self, mock_settings: BotSettings, mock_bot: Bot
    ) -> None:
        """Test that channel check fails open on error."""
        middleware = AccessControlMiddleware(
            bot_settings=mock_settings, bot=mock_bot
        )

        # Mock bot.get_chat_member to raise error
        mock_bot.get_chat_member = AsyncMock(
            side_effect=Exception("API error")
        )

        user_data = {"telegram_id": 123}
        data = {
            "user": user_data,
            "settings": {
                "access_mode": "open",
                "channel_id": "@test_channel",
            },
        }

        message = MagicMock(spec=Message)
        handler = AsyncMock(return_value="ok")

        result = await middleware(handler, message, data)

        # Should fail open and allow access
        assert result == "ok"
        assert handler.called

    async def test_handles_callback_query_events(
        self, mock_settings: BotSettings, mock_bot: Bot
    ) -> None:
        """Test handling callback query events."""
        middleware = AccessControlMiddleware(
            bot_settings=mock_settings, bot=mock_bot
        )

        user_data = {"telegram_id": 123}
        data = {
            "user": user_data,
            "settings": {"access_mode": "maintenance"},
        }

        callback = MagicMock(spec=CallbackQuery)
        callback.answer = AsyncMock()
        handler = AsyncMock()

        result = await middleware(handler, callback, data)

        # Should block and answer callback
        assert result is None
        assert not handler.called
        assert callback.answer.called

    async def test_handles_missing_user_data(
        self, mock_settings: BotSettings, mock_bot: Bot
    ) -> None:
        """Test handling when user data is missing."""
        middleware = AccessControlMiddleware(
            bot_settings=mock_settings, bot=mock_bot
        )

        data = {"settings": {}}  # No user data

        message = MagicMock(spec=Message)
        handler = AsyncMock(return_value="ok")

        result = await middleware(handler, message, data)

        # Should pass through
        assert result == "ok"
        assert handler.called

    async def test_handles_missing_settings(
        self, mock_settings: BotSettings, mock_bot: Bot
    ) -> None:
        """Test handling when settings are missing."""
        middleware = AccessControlMiddleware(
            bot_settings=mock_settings, bot=mock_bot
        )

        user_data = {"telegram_id": 123}
        data = {"user": user_data}  # No settings

        message = MagicMock(spec=Message)
        handler = AsyncMock(return_value="ok")

        result = await middleware(handler, message, data)

        # Should default to open mode
        assert result == "ok"
        assert handler.called

    async def test_multiple_checks_all_pass(
        self, mock_settings: BotSettings, mock_bot: Bot
    ) -> None:
        """Test that all checks must pass."""
        middleware = AccessControlMiddleware(
            bot_settings=mock_settings, bot=mock_bot
        )

        mock_bot.get_chat_member = AsyncMock(
            return_value=ChatMemberMember(
                user=User(id=123, is_bot=False, first_name="Test"),
                status="member",
            )
        )

        user_data = {
            "telegram_id": 123,
            "has_accepted_rules": True,
        }
        data = {
            "user": user_data,
            "settings": {
                "access_mode": "open",
                "rules_url": "https://example.com/rules",
                "channel_id": "@channel",
            },
        }

        message = MagicMock(spec=Message)
        handler = AsyncMock(return_value="ok")

        result = await middleware(handler, message, data)

        assert result == "ok"
        assert handler.called
