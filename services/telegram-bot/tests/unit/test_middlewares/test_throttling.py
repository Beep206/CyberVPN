"""Unit tests for throttling middleware."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.types import CallbackQuery, Message, User

from src.middlewares import register_middlewares
from src.middlewares.throttling import ThrottlingMiddleware

if TYPE_CHECKING:
    import fakeredis.aioredis

    from src.config import BotSettings


@pytest.mark.asyncio
class TestThrottlingMiddleware:
    """Test rate limiting middleware."""

    async def test_allows_first_request(
        self,
        mock_settings: BotSettings,
        fake_redis: fakeredis.aioredis.FakeRedis,
    ) -> None:
        """Test that first request is always allowed."""
        middleware = ThrottlingMiddleware(
            settings=mock_settings,
            redis=fake_redis,
            message_limit=(10, 5),
        )

        user = User(id=123456, is_bot=False, first_name="Test")
        message = MagicMock(spec=Message)
        message.from_user = user

        handler = AsyncMock(return_value=None)
        data = {}

        result = await middleware(handler, message, data)

        assert handler.called
        assert result is None  # Handler returned None

    async def test_rate_limits_excessive_messages(
        self,
        mock_settings: BotSettings,
        fake_redis: fakeredis.aioredis.FakeRedis,
    ) -> None:
        """Test that excessive messages are rate limited."""
        middleware = ThrottlingMiddleware(
            settings=mock_settings,
            redis=fake_redis,
            message_limit=(10, 2),  # 2 messages per 10 seconds
        )

        user = User(id=123456, is_bot=False, first_name="Test")
        message = MagicMock(spec=Message)
        message.from_user = user

        handler = AsyncMock(return_value="ok")
        data = {}

        # First 2 messages should pass
        result1 = await middleware(handler, message, data)
        assert result1 == "ok"

        result2 = await middleware(handler, message, data)
        assert result2 == "ok"

        # Third message should be throttled
        result3 = await middleware(handler, message, data)
        assert result3 is None  # Throttled
        assert handler.call_count == 2  # Handler not called for 3rd

    async def test_uses_settings_backed_message_limit(
        self,
        mock_settings: BotSettings,
        fake_redis: fakeredis.aioredis.FakeRedis,
    ) -> None:
        """Test that default middleware limits come from BotSettings."""
        object.__setattr__(mock_settings, "telegram_message_rate_window_seconds", 10)
        object.__setattr__(mock_settings, "telegram_message_rate_max_requests", 1)

        middleware = ThrottlingMiddleware(settings=mock_settings, redis=fake_redis)

        user = User(id=123456, is_bot=False, first_name="Test")
        message = MagicMock(spec=Message)
        message.from_user = user

        handler = AsyncMock(return_value="ok")

        assert await middleware(handler, message, {}) == "ok"
        assert await middleware(handler, message, {}) is None
        assert handler.call_count == 1

    async def test_rate_limits_callbacks_separately(
        self,
        mock_settings: BotSettings,
        fake_redis: fakeredis.aioredis.FakeRedis,
    ) -> None:
        """Test that callbacks have separate rate limits."""
        middleware = ThrottlingMiddleware(
            settings=mock_settings,
            redis=fake_redis,
            message_limit=(10, 5),
            callback_limit=(3, 2),  # 2 callbacks per 3 seconds
        )

        user = User(id=123456, is_bot=False, first_name="Test")
        callback = MagicMock(spec=CallbackQuery)
        callback.from_user = user
        callback.answer = AsyncMock()

        handler = AsyncMock(return_value="ok")
        data = {}

        # First 2 callbacks should pass
        result1 = await middleware(handler, callback, data)
        assert result1 == "ok"

        result2 = await middleware(handler, callback, data)
        assert result2 == "ok"

        # Third should be throttled
        result3 = await middleware(handler, callback, data)
        assert result3 is None
        assert callback.answer.called  # Should answer with throttle message

    async def test_admin_bypass(
        self,
        mock_settings: BotSettings,
        fake_redis: fakeredis.aioredis.FakeRedis,
    ) -> None:
        """Test that admins bypass rate limiting."""
        admin_id = mock_settings.admin_ids[0]

        middleware = ThrottlingMiddleware(
            settings=mock_settings,
            redis=fake_redis,
            message_limit=(10, 1),  # 1 message per 10 seconds
        )

        user = User(id=admin_id, is_bot=False, first_name="Admin")
        message = MagicMock(spec=Message)
        message.from_user = user

        handler = AsyncMock(return_value="ok")
        data = {}

        # Admin should be able to send many messages
        for _ in range(10):
            result = await middleware(handler, message, data)
            assert result == "ok"

        assert handler.call_count == 10

    async def test_different_users_separate_limits(
        self,
        mock_settings: BotSettings,
        fake_redis: fakeredis.aioredis.FakeRedis,
    ) -> None:
        """Test that different users have separate rate limits."""
        middleware = ThrottlingMiddleware(
            settings=mock_settings,
            redis=fake_redis,
            message_limit=(10, 2),
        )

        user1 = User(id=111, is_bot=False, first_name="User1")
        user2 = User(id=222, is_bot=False, first_name="User2")

        message1 = MagicMock(spec=Message)
        message1.from_user = user1

        message2 = MagicMock(spec=Message)
        message2.from_user = user2

        handler = AsyncMock(return_value="ok")

        # User 1 sends 2 messages
        await middleware(handler, message1, {})
        await middleware(handler, message1, {})

        # User 2 should still be able to send messages
        result = await middleware(handler, message2, {})
        assert result == "ok"

    async def test_same_timestamp_events_still_count_separately(
        self,
        mock_settings: BotSettings,
        fake_redis: fakeredis.aioredis.FakeRedis,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that high-speed events with identical timestamps do not collapse in Redis ZSET."""
        monkeypatch.setattr("src.middlewares.throttling.time.time", lambda: 1_000.0)
        middleware = ThrottlingMiddleware(
            settings=mock_settings,
            redis=fake_redis,
            message_limit=(10, 2),
        )

        user = User(id=123456, is_bot=False, first_name="Test")
        message = MagicMock(spec=Message)
        message.from_user = user

        handler = AsyncMock(return_value="ok")

        assert await middleware(handler, message, {}) == "ok"
        assert await middleware(handler, message, {}) == "ok"
        assert await middleware(handler, message, {}) is None
        assert handler.call_count == 2

    async def test_handles_no_user(
        self,
        mock_settings: BotSettings,
        fake_redis: fakeredis.aioredis.FakeRedis,
    ) -> None:
        """Test handling events with no user."""
        middleware = ThrottlingMiddleware(
            settings=mock_settings, redis=fake_redis
        )

        # Event with no user
        event = MagicMock()
        # No from_user attribute

        handler = AsyncMock(return_value="ok")
        data = {}

        # Should not throttle, just pass through
        result = await middleware(handler, event, data)
        assert result == "ok"
        assert handler.called

    async def test_callback_throttle_message(
        self,
        mock_settings: BotSettings,
        fake_redis: fakeredis.aioredis.FakeRedis,
    ) -> None:
        """Test that throttled callbacks get a notification."""
        middleware = ThrottlingMiddleware(
            settings=mock_settings,
            redis=fake_redis,
            callback_limit=(3, 1),  # 1 callback per 3 seconds
        )

        user = User(id=123, is_bot=False, first_name="Test")
        callback = MagicMock(spec=CallbackQuery)
        callback.from_user = user
        callback.answer = AsyncMock()

        handler = AsyncMock()

        # First callback passes
        await middleware(handler, callback, {})

        # Second is throttled
        result = await middleware(handler, callback, {})

        assert result is None
        # Should call answer with throttle message
        callback.answer.assert_called_once()
        args = callback.answer.call_args
        assert "Подождите" in args[0][0] or "show_alert" in str(args)

    async def test_message_throttle_silent(
        self,
        mock_settings: BotSettings,
        fake_redis: fakeredis.aioredis.FakeRedis,
    ) -> None:
        """Test that throttled messages fail silently."""
        middleware = ThrottlingMiddleware(
            settings=mock_settings,
            redis=fake_redis,
            message_limit=(10, 1),
        )

        user = User(id=123, is_bot=False, first_name="Test")
        message = MagicMock(spec=Message)
        message.from_user = user
        message.answer = AsyncMock()

        handler = AsyncMock(return_value="ok")

        # First passes
        await middleware(handler, message, {})

        # Second is throttled silently
        result = await middleware(handler, message, {})

        assert result is None
        # Message should NOT have been answered (no spam)
        assert not message.answer.called

    async def test_redis_error_fails_open_when_configured(
        self,
        mock_settings: BotSettings,
        fake_redis: fakeredis.aioredis.FakeRedis,
    ) -> None:
        """Test that Redis errors can fail open when explicitly configured."""
        from typing import Any

        from redis.exceptions import RedisError

        object.__setattr__(mock_settings, "telegram_throttle_fail_open", True)
        middleware = ThrottlingMiddleware(
            settings=mock_settings, redis=fake_redis
        )

        user = User(id=123, is_bot=False, first_name="Test")
        message = MagicMock(spec=Message)
        message.from_user = user

        handler = AsyncMock(return_value="ok")

        # Mock Redis to raise error
        original_pipeline = fake_redis.pipeline

        def failing_pipeline(*args: Any, **kwargs: Any) -> None:
            raise RedisError("Connection lost")

        fake_redis.pipeline = failing_pipeline  # type: ignore[method-assign]

        # Should fail open and allow request
        result = await middleware(handler, message, {})
        assert result == "ok"
        assert handler.called

        # Restore
        fake_redis.pipeline = original_pipeline  # type: ignore[method-assign]

    async def test_redis_error_fails_closed_by_default(
        self,
        mock_settings: BotSettings,
        fake_redis: fakeredis.aioredis.FakeRedis,
    ) -> None:
        """Test that production default blocks user events if Redis throttling fails."""
        from typing import Any

        from redis.exceptions import RedisError

        middleware = ThrottlingMiddleware(settings=mock_settings, redis=fake_redis)

        user = User(id=123, is_bot=False, first_name="Test")
        callback = MagicMock(spec=CallbackQuery)
        callback.from_user = user
        callback.answer = AsyncMock()

        handler = AsyncMock(return_value="ok")
        original_pipeline = fake_redis.pipeline

        def failing_pipeline(*args: Any, **kwargs: Any) -> None:
            raise RedisError("Connection lost")

        fake_redis.pipeline = failing_pipeline  # type: ignore[method-assign]

        result = await middleware(handler, callback, {})

        assert result is None
        assert not handler.called
        callback.answer.assert_awaited_once()

        fake_redis.pipeline = original_pipeline  # type: ignore[method-assign]

    async def test_throttling_can_be_disabled_for_local_smoke(
        self,
        mock_settings: BotSettings,
        fake_redis: fakeredis.aioredis.FakeRedis,
    ) -> None:
        """Test that explicit local smoke override bypasses Redis throttling."""
        from typing import Any

        from redis.exceptions import RedisError

        object.__setattr__(mock_settings, "telegram_throttle_enabled", False)
        middleware = ThrottlingMiddleware(settings=mock_settings, redis=fake_redis)

        user = User(id=123, is_bot=False, first_name="Test")
        message = MagicMock(spec=Message)
        message.from_user = user

        handler = AsyncMock(return_value="ok")
        original_pipeline = fake_redis.pipeline

        def failing_pipeline(*args: Any, **kwargs: Any) -> None:
            raise RedisError("Connection lost")

        fake_redis.pipeline = failing_pipeline  # type: ignore[method-assign]

        result = await middleware(handler, message, {})

        assert result == "ok"
        handler.assert_awaited_once()

        fake_redis.pipeline = original_pipeline  # type: ignore[method-assign]

    async def test_sliding_window_cleanup(
        self,
        mock_settings: BotSettings,
        fake_redis: fakeredis.aioredis.FakeRedis,
    ) -> None:
        """Test that old entries are removed from sliding window."""
        middleware = ThrottlingMiddleware(
            settings=mock_settings,
            redis=fake_redis,
            message_limit=(1, 2),  # 2 messages per 1 second
        )

        user = User(id=123, is_bot=False, first_name="Test")
        message = MagicMock(spec=Message)
        message.from_user = user

        handler = AsyncMock(return_value="ok")

        # Send 2 messages
        await middleware(handler, message, {})
        await middleware(handler, message, {})

        # Third should be throttled
        result = await middleware(handler, message, {})
        assert result is None

        # Wait for window to expire
        await asyncio.sleep(1.1)

        # Should be able to send again
        result = await middleware(handler, message, {})
        assert result == "ok"


class _Observer:
    def __init__(self) -> None:
        self.middlewares: list[object] = []

    def middleware(self, middleware: object) -> None:
        self.middlewares.append(middleware)

    def outer_middleware(self, middleware: object) -> None:
        self.middlewares.append(middleware)


class _DispatcherStub:
    def __init__(self) -> None:
        self.update = _Observer()
        self.message = _Observer()
        self.callback_query = _Observer()


def test_register_middlewares_attaches_throttling_to_messages_and_callbacks(
    mock_settings: BotSettings,
    fake_redis: fakeredis.aioredis.FakeRedis,
) -> None:
    """Feature-level proof that dispatcher wiring includes Telegram throttling."""
    object.__setattr__(mock_settings, "telegram_message_rate_window_seconds", 11)
    object.__setattr__(mock_settings, "telegram_message_rate_max_requests", 6)
    object.__setattr__(mock_settings, "telegram_callback_rate_window_seconds", 4)
    object.__setattr__(mock_settings, "telegram_callback_rate_max_requests", 2)

    dispatcher = _DispatcherStub()

    register_middlewares(
        dispatcher,  # type: ignore[arg-type]
        mock_settings,
        bot=MagicMock(),
        api_client=MagicMock(),
        cache=MagicMock(),
        redis=fake_redis,
    )

    message_throttles = [m for m in dispatcher.message.middlewares if isinstance(m, ThrottlingMiddleware)]
    callback_throttles = [m for m in dispatcher.callback_query.middlewares if isinstance(m, ThrottlingMiddleware)]

    assert len(message_throttles) == 1
    assert len(callback_throttles) == 1
    assert message_throttles[0]._message_limit == (11, 6)
    assert callback_throttles[0]._callback_limit == (4, 2)
