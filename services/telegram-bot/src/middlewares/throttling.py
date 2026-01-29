"""CyberVPN Telegram Bot — Throttling middleware.

Redis-based distributed rate limiting using sliding window algorithm.
Prevents abuse with different limits for messages vs callbacks. Admin bypass.
"""

from __future__ import annotations

import time
from typing import Any, Awaitable, Callable

import structlog
from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from redis.asyncio import Redis
from redis.exceptions import RedisError

from src.config import BotSettings

logger = structlog.get_logger(__name__)

# Rate limits: (window_seconds, max_requests)
MESSAGE_RATE_LIMIT = (10, 5)  # 5 messages per 10 seconds
CALLBACK_RATE_LIMIT = (3, 3)  # 3 callbacks per 3 seconds


class ThrottlingMiddleware(BaseMiddleware):
    """Per-user distributed rate limiting using Redis sliding window.

    Uses Redis sorted sets to track request timestamps within a sliding
    window. Different limits for messages vs callbacks. Admins bypass.

    Args:
        settings: Bot settings for admin bypass.
        redis: Redis client for distributed state.
        message_limit: (window_seconds, max_requests) for messages.
        callback_limit: (window_seconds, max_requests) for callbacks.
    """

    def __init__(
        self,
        settings: BotSettings,
        redis: Redis,
        message_limit: tuple[int, int] = MESSAGE_RATE_LIMIT,
        callback_limit: tuple[int, int] = CALLBACK_RATE_LIMIT,
    ) -> None:
        self._settings = settings
        self._redis = redis
        self._message_limit = message_limit
        self._callback_limit = callback_limit
        self._key_prefix = "throttle:"

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Apply sliding window rate limiting per user.

        Admin users bypass rate limiting.

        Args:
            handler: Next handler in the chain.
            event: Telegram event (Message or CallbackQuery).
            data: Handler data dict.

        Returns:
            Result from the next handler, or None if throttled.
        """
        user_id = self._get_user_id(event)
        if user_id is None:
            return await handler(event, data)

        # Admin bypass
        if self._settings.is_admin(user_id):
            return await handler(event, data)

        # Choose limit based on event type
        if isinstance(event, CallbackQuery):
            window_seconds, max_requests = self._callback_limit
            event_type = "callback"
        else:
            window_seconds, max_requests = self._message_limit
            event_type = "message"

        # Check rate limit using Redis sliding window
        is_allowed = await self._check_rate_limit(
            user_id=user_id,
            event_type=event_type,
            window_seconds=window_seconds,
            max_requests=max_requests,
        )

        if not is_allowed:
            logger.debug(
                "user_throttled",
                user_id=user_id,
                event_type=event_type,
            )
            if isinstance(event, CallbackQuery):
                await event.answer("⏳ Подождите немного...", show_alert=False)
            # For messages, silently drop (no notification spam)
            return None

        return await handler(event, data)

    async def _check_rate_limit(
        self,
        user_id: int,
        event_type: str,
        window_seconds: int,
        max_requests: int,
    ) -> bool:
        """Check if user is within rate limit using sliding window.

        Uses Redis sorted set with timestamps as scores. Removes old
        entries outside the window and counts remaining entries.

        Args:
            user_id: User's Telegram ID.
            event_type: "message" or "callback".
            window_seconds: Time window in seconds.
            max_requests: Maximum requests allowed in window.

        Returns:
            True if request is allowed, False if rate limited.
        """
        key = f"{self._key_prefix}{user_id}:{event_type}"
        now = time.time()
        window_start = now - window_seconds

        try:
            # Redis pipeline for atomic operations
            async with self._redis.pipeline(transaction=True) as pipe:
                # Remove expired entries outside window
                pipe.zremrangebyscore(key, "-inf", window_start)
                # Count current requests in window
                pipe.zcard(key)
                # Add current request with timestamp as score
                pipe.zadd(key, {str(now): now})
                # Set TTL to window size (auto-cleanup)
                pipe.expire(key, window_seconds)
                results = await pipe.execute()

            # results[1] is the count before adding current request
            current_count = results[1]
            return current_count < max_requests

        except RedisError:
            logger.exception(
                "throttle_redis_error",
                user_id=user_id,
                event_type=event_type,
            )
            # Fail open: allow request if Redis is down
            return True

    @staticmethod
    def _get_user_id(event: TelegramObject) -> int | None:
        """Extract user ID from event."""
        if isinstance(event, Message) and event.from_user:
            return event.from_user.id
        if isinstance(event, CallbackQuery) and event.from_user:
            return event.from_user.id
        return None
