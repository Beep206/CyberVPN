"""CyberVPN Telegram Bot — Logging middleware.

Logs every incoming update with structured context using structlog.
Captures update type, user info, processing time, and outcome.
"""

from __future__ import annotations

import time
from typing import Any, Awaitable, Callable

import structlog
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

logger = structlog.get_logger(__name__)


class LoggingMiddleware(BaseMiddleware):
    """Structured logging middleware for all Telegram updates.

    Logs request start, completion, and errors with timing information.
    Binds user context to structlog for downstream log calls.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Process update with structured logging context.

        Args:
            handler: Next handler in the middleware chain.
            event: Telegram update event.
            data: Handler data dict.

        Returns:
            Result from the next handler.
        """
        if not isinstance(event, Update):
            return await handler(event, data)

        update_type = _get_update_type(event)
        user_id = _get_user_id(event)
        username = _get_username(event)

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            update_id=event.update_id,
            update_type=update_type,
            user_id=user_id,
            username=username,
        )

        start_time = time.perf_counter()

        try:
            result = await handler(event, data)
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            logger.info(
                "update_processed",
                elapsed_ms=round(elapsed_ms, 2),
            )
            return result

        except Exception:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.exception(
                "update_failed",
                elapsed_ms=round(elapsed_ms, 2),
            )
            raise


def _get_update_type(update: Update) -> str:
    """Extract human-readable update type."""
    if update.message:
        if update.message.text and update.message.text.startswith("/"):
            return f"command:{update.message.text.split()[0]}"
        return "message"
    if update.callback_query:
        return f"callback:{update.callback_query.data or 'unknown'}"
    if update.inline_query:
        return "inline_query"
    if update.my_chat_member:
        return "my_chat_member"
    return "other"


def _get_user_id(update: Update) -> int | None:
    """Extract user ID from any update type."""
    if update.message and update.message.from_user:
        return update.message.from_user.id
    if update.callback_query and update.callback_query.from_user:
        return update.callback_query.from_user.id
    if update.inline_query and update.inline_query.from_user:
        return update.inline_query.from_user.id
    return None


def _get_username(update: Update) -> str | None:
    """Extract username from any update type."""
    if update.message and update.message.from_user:
        return update.message.from_user.username
    if update.callback_query and update.callback_query.from_user:
        return update.callback_query.from_user.username
    if update.inline_query and update.inline_query.from_user:
        return update.inline_query.from_user.username
    return None
