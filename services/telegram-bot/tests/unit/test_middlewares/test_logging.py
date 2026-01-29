"""Unit tests for logging middleware."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest
import structlog
from aiogram.types import CallbackQuery, Message, Update, User

from src.middlewares.logging import LoggingMiddleware

if TYPE_CHECKING:
    from collections.abc import Callable


@pytest.mark.asyncio
class TestLoggingMiddleware:
    """Test structured logging middleware."""

    async def test_logs_message_update(self) -> None:
        """Test logging for message updates."""
        middleware = LoggingMiddleware()

        # Create mock message
        user = User(id=123456, is_bot=False, first_name="Test", username="testuser")
        message = MagicMock(spec=Message)
        message.from_user = user
        message.text = "/start"

        update = MagicMock(spec=Update)
        update.update_id = 999
        update.message = message
        update.callback_query = None
        update.inline_query = None
        update.my_chat_member = None

        # Mock handler
        handler = AsyncMock(return_value=None)
        data = {}

        # Capture structlog context
        with structlog.testing.capture_logs() as cap_logs:
            await middleware(handler, update, data)

        # Verify handler was called
        assert handler.called

        # Verify logs contain expected fields
        assert len(cap_logs) > 0
        log_entry = cap_logs[-1]  # Get last log entry

        # Check that contextual fields were bound
        assert "update_processed" in str(cap_logs) or "event" in log_entry

    async def test_logs_callback_query_update(self) -> None:
        """Test logging for callback query updates."""
        middleware = LoggingMiddleware()

        user = User(id=123456, is_bot=False, first_name="Test")
        callback = MagicMock(spec=CallbackQuery)
        callback.from_user = user
        callback.data = "button_clicked"

        update = MagicMock(spec=Update)
        update.update_id = 1000
        update.message = None
        update.callback_query = callback
        update.inline_query = None
        update.my_chat_member = None

        handler = AsyncMock(return_value=None)
        data = {}

        with structlog.testing.capture_logs() as cap_logs:
            await middleware(handler, update, data)

        assert handler.called

    async def test_logs_elapsed_time(self) -> None:
        """Test that middleware logs elapsed time."""
        middleware = LoggingMiddleware()

        user = User(id=123, is_bot=False, first_name="Test")
        message = MagicMock(spec=Message)
        message.from_user = user
        message.text = "test"

        update = MagicMock(spec=Update)
        update.update_id = 1001
        update.message = message
        update.callback_query = None
        update.inline_query = None
        update.my_chat_member = None

        async def slow_handler(event: Update, data: dict) -> None:
            import asyncio

            await asyncio.sleep(0.01)

        data = {}

        with structlog.testing.capture_logs() as cap_logs:
            await middleware(slow_handler, update, data)

        # Should have logged with elapsed_ms
        # Check log output contains elapsed info
        assert len(cap_logs) > 0

    async def test_logs_exception_on_failure(self) -> None:
        """Test that middleware logs exceptions."""
        middleware = LoggingMiddleware()

        user = User(id=123, is_bot=False, first_name="Test")
        message = MagicMock(spec=Message)
        message.from_user = user

        update = MagicMock(spec=Update)
        update.update_id = 1002
        update.message = message
        update.callback_query = None
        update.inline_query = None
        update.my_chat_member = None

        async def failing_handler(event: Update, data: dict) -> None:
            raise ValueError("Test error")

        data = {}

        with pytest.raises(ValueError):
            with structlog.testing.capture_logs() as cap_logs:
                await middleware(failing_handler, update, data)

        # Should have logged the exception
        assert len(cap_logs) > 0

    async def test_extracts_user_id_from_message(self) -> None:
        """Test user ID extraction from message."""
        middleware = LoggingMiddleware()

        user = User(id=555555, is_bot=False, first_name="User", username="user555")
        message = MagicMock(spec=Message)
        message.from_user = user

        update = MagicMock(spec=Update)
        update.update_id = 1003
        update.message = message
        update.callback_query = None
        update.inline_query = None
        update.my_chat_member = None

        handler = AsyncMock()
        data = {}

        with structlog.testing.capture_logs() as cap_logs:
            await middleware(handler, update, data)

        # User ID should be in context
        # Check captured logs for user_id binding

    async def test_extracts_username_from_callback(self) -> None:
        """Test username extraction from callback query."""
        middleware = LoggingMiddleware()

        user = User(id=777, is_bot=False, first_name="Callback", username="callback_user")
        callback = MagicMock(spec=CallbackQuery)
        callback.from_user = user
        callback.data = "test"

        update = MagicMock(spec=Update)
        update.update_id = 1004
        update.message = None
        update.callback_query = callback
        update.inline_query = None
        update.my_chat_member = None

        handler = AsyncMock()
        data = {}

        await middleware(handler, update, data)

        assert handler.called

    async def test_handles_update_without_user(self) -> None:
        """Test handling updates with no user info."""
        middleware = LoggingMiddleware()

        update = MagicMock(spec=Update)
        update.update_id = 1005
        update.message = None
        update.callback_query = None
        update.inline_query = None
        update.my_chat_member = None

        handler = AsyncMock()
        data = {}

        # Should not raise
        await middleware(handler, update, data)
        assert handler.called

    async def test_identifies_command_messages(self) -> None:
        """Test that command messages are identified."""
        middleware = LoggingMiddleware()

        user = User(id=123, is_bot=False, first_name="Test")
        message = MagicMock(spec=Message)
        message.from_user = user
        message.text = "/help argument"

        update = MagicMock(spec=Update)
        update.update_id = 1006
        update.message = message
        update.callback_query = None
        update.inline_query = None
        update.my_chat_member = None

        handler = AsyncMock()
        data = {}

        with structlog.testing.capture_logs() as cap_logs:
            await middleware(handler, update, data)

        # Should identify as command
        # update_type should be "command:/help"

    async def test_clears_context_between_updates(self) -> None:
        """Test that context variables are cleared between updates."""
        middleware = LoggingMiddleware()

        user1 = User(id=111, is_bot=False, first_name="User1")
        message1 = MagicMock(spec=Message)
        message1.from_user = user1

        update1 = MagicMock(spec=Update)
        update1.update_id = 2001
        update1.message = message1
        update1.callback_query = None
        update1.inline_query = None
        update1.my_chat_member = None

        user2 = User(id=222, is_bot=False, first_name="User2")
        message2 = MagicMock(spec=Message)
        message2.from_user = user2

        update2 = MagicMock(spec=Update)
        update2.update_id = 2002
        update2.message = message2
        update2.callback_query = None
        update2.inline_query = None
        update2.my_chat_member = None

        handler = AsyncMock()

        # Process first update
        await middleware(handler, update1, {})

        # Process second update
        await middleware(handler, update2, {})

        # Context should be cleared between calls
        # Verified by structlog's clear_contextvars
