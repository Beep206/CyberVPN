"""CyberVPN Telegram Bot — Authentication middleware.

Extracts telegram_id, gets/registers user via API, caches in Redis,
and injects user data into handler context for downstream handlers.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable

import structlog
from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, User

from src.services.api_client import APIError, CyberVPNAPIClient
from src.services.cache_service import CacheService

logger = structlog.get_logger(__name__)

USER_CACHE_TTL = 300  # 5 minutes


class AuthMiddleware(BaseMiddleware):
    """Authentication middleware that loads/registers users.

    On each update:
    1. Extracts telegram_id and user info from update
    2. Tries to get user from Redis cache
    3. If cache miss, calls API to get or register user
    4. Caches user in Redis for subsequent requests
    5. Injects data['user'] for downstream handlers

    Args:
        api_client: CyberVPN API client for user operations.
        cache: Redis cache service for user data.
        default_language: Default language for new users.
    """

    def __init__(
        self,
        api_client: CyberVPNAPIClient,
        cache: CacheService,
        default_language: str = "ru",
    ) -> None:
        self._api = api_client
        self._cache = cache
        self._default_language = default_language

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Authenticate user and inject into handler context.

        Args:
            handler: Next handler in the chain.
            event: Telegram event (Message or CallbackQuery).
            data: Handler data dict (will be mutated with 'user' key).

        Returns:
            Result from the next handler.
        """
        telegram_user = self._get_telegram_user(event)
        if telegram_user is None:
            # No user info in event (rare, but possible for channel posts)
            logger.warning("no_telegram_user_in_event", event_type=type(event).__name__)
            return await handler(event, data)

        telegram_id = telegram_user.id
        user_data = None

        # Try cache first
        user_data = await self._cache.get_user(telegram_id)

        if user_data is not None:
            logger.debug("user_loaded_from_cache", telegram_id=telegram_id)
        else:
            # Cache miss: load or register via API
            user_data = await self._load_or_register_user(telegram_user)

            if user_data is not None:
                # Cache for future requests
                await self._cache.set_user(
                    telegram_id=telegram_id,
                    user_data=user_data,
                    ttl=USER_CACHE_TTL,
                )

        # Inject user into handler context
        data["user"] = user_data
        data["telegram_user"] = telegram_user  # Also provide raw Telegram user

        return await handler(event, data)

    async def _load_or_register_user(
        self,
        telegram_user: User,
    ) -> dict[str, Any] | None:
        """Load existing user or register a new one.

        Args:
            telegram_user: Telegram User object from update.

        Returns:
            User data dict or None if API error.
        """
        telegram_id = telegram_user.id

        try:
            # Try to get existing user
            user_data = await self._api.get_user(telegram_id)
            logger.info("user_loaded_from_api", telegram_id=telegram_id)
            return user_data

        except APIError as exc:
            if exc.status_code == 404:
                # User doesn't exist, register them
                return await self._register_new_user(telegram_user)

            # Other API errors
            logger.error(
                "user_api_error",
                telegram_id=telegram_id,
                status_code=exc.status_code,
                detail=exc.detail,
            )
            return None

    async def _register_new_user(
        self,
        telegram_user: User,
    ) -> dict[str, Any] | None:
        """Register a new user via API.

        Args:
            telegram_user: Telegram User object.

        Returns:
            Created user data dict or None if registration failed.
        """
        telegram_id = telegram_user.id
        username = telegram_user.username
        language = telegram_user.language_code or self._default_language

        # Extract referrer_id if present (from deep link in start parameter)
        # This would be set by a start command handler before this middleware
        # For now, we'll check if it's already in the update data
        referrer_id = None  # Could be extracted from start parameter

        try:
            user_data = await self._api.register_user(
                telegram_id=telegram_id,
                username=username,
                language=language,
                referrer_id=referrer_id,
            )
            logger.info(
                "user_registered",
                telegram_id=telegram_id,
                username=username,
            )
            return user_data

        except APIError as exc:
            logger.error(
                "user_registration_failed",
                telegram_id=telegram_id,
                status_code=exc.status_code,
                detail=exc.detail,
            )
            return None

    @staticmethod
    def _get_telegram_user(event: TelegramObject) -> User | None:
        """Extract Telegram User object from event.

        Args:
            event: Telegram event (Message, CallbackQuery, etc.).

        Returns:
            User object or None if not found.
        """
        if isinstance(event, Message):
            return event.from_user
        if isinstance(event, CallbackQuery):
            return event.from_user
        # Add other event types as needed
        return None
