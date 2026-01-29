"""CyberVPN Telegram Bot — Registered user filter.

Filter that checks if a user exists in the system (has been registered).
Uses data['user'] injected by AuthMiddleware.
"""

from __future__ import annotations

from typing import Any

import structlog
from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

logger = structlog.get_logger(__name__)


class RegisteredUserFilter(BaseFilter):
    """Filter that passes only if user is registered in the system.

    Checks for presence and validity of data['user'] which should be
    injected by AuthMiddleware. If user is None or registration failed,
    this filter will not pass.

    Usage:
        @router.message(RegisteredUserFilter())
        async def handler(message: Message, user: dict[str, Any]) -> None:
            # user is guaranteed to be present and valid
            pass

        @router.callback_query(RegisteredUserFilter(), F.data == "some_action")
        async def callback_handler(callback: CallbackQuery, user: dict[str, Any]) -> None:
            # user is available here too
            pass
    """

    async def __call__(
        self,
        event: Message | CallbackQuery,
        **kwargs: Any,
    ) -> bool:
        """Check if user is registered.

        Args:
            event: Message or CallbackQuery event.
            **kwargs: Handler kwargs (includes data from middleware).

        Returns:
            True if user is registered, False otherwise.
        """
        user = kwargs.get("user")

        if user is None:
            # No user data (auth failed or user not registered)
            telegram_id = self._get_telegram_id(event)
            logger.debug(
                "registered_filter_failed_no_user",
                telegram_id=telegram_id,
            )
            return False

        # Additional validation: check user has required fields
        if not isinstance(user, dict):
            logger.warning(
                "registered_filter_invalid_user_type",
                user_type=type(user).__name__,
            )
            return False

        # Verify user has essential fields
        telegram_id = user.get("telegram_id")
        if telegram_id is None:
            logger.warning("registered_filter_user_missing_telegram_id")
            return False

        # User is valid and registered
        return True

    @staticmethod
    def _get_telegram_id(event: Message | CallbackQuery) -> int | None:
        """Extract telegram_id for logging.

        Args:
            event: Message or CallbackQuery event.

        Returns:
            Telegram ID or None.
        """
        if isinstance(event, Message) and event.from_user:
            return event.from_user.id
        if isinstance(event, CallbackQuery) and event.from_user:
            return event.from_user.id
        return None


class UnregisteredUserFilter(BaseFilter):
    """Filter that passes only if user is NOT registered.

    Inverse of RegisteredUserFilter. Useful for showing registration
    prompts or onboarding flows.

    Usage:
        @router.message(UnregisteredUserFilter(), Command("start"))
        async def start_unregistered(message: Message) -> None:
            await message.answer("Welcome! Let's get you registered...")
    """

    async def __call__(
        self,
        event: Message | CallbackQuery,
        **kwargs: Any,
    ) -> bool:
        """Check if user is NOT registered.

        Args:
            event: Message or CallbackQuery event.
            **kwargs: Handler kwargs.

        Returns:
            True if user is not registered, False if registered.
        """
        user = kwargs.get("user")
        return user is None or not isinstance(user, dict)


# Convenience aliases
IsRegistered = RegisteredUserFilter
IsNotRegistered = UnregisteredUserFilter
