"""CyberVPN Telegram Bot — Prometheus metrics middleware.

Collects counters and histograms for all Telegram updates.
Exposes metrics for scraping by Prometheus.
"""

from __future__ import annotations

import time
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update
from prometheus_client import Counter, Histogram

# ── Metrics ──────────────────────────────────────────────────────────────

UPDATES_TOTAL = Counter(
    "bot_updates_total",
    "Total number of Telegram updates processed",
    ["update_type", "status"],
)

UPDATE_DURATION_SECONDS = Histogram(
    "bot_update_duration_seconds",
    "Time spent processing Telegram updates",
    ["update_type"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

COMMANDS_TOTAL = Counter(
    "bot_commands_total",
    "Total number of bot commands executed",
    ["command"],
)

CALLBACK_QUERIES_TOTAL = Counter(
    "bot_callback_queries_total",
    "Total callback queries processed",
    ["action"],
)

ACTIVE_USERS_TOTAL = Counter(
    "bot_active_users_total",
    "Total unique user interactions",
)

ERRORS_TOTAL = Counter(
    "bot_errors_total",
    "Total errors during update processing",
    ["error_type"],
)


class MetricsMiddleware(BaseMiddleware):
    """Prometheus metrics collection middleware.

    Tracks update counts, processing duration, commands, and errors.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Collect metrics for the update processing pipeline.

        Args:
            handler: Next handler in the middleware chain.
            event: Telegram update event.
            data: Handler data dict.

        Returns:
            Result from the next handler.
        """
        if not isinstance(event, Update):
            return await handler(event, data)

        update_type = self._get_update_type(event)
        self._track_specific_metrics(event)

        start_time = time.perf_counter()

        try:
            result = await handler(event, data)
            elapsed = time.perf_counter() - start_time

            UPDATES_TOTAL.labels(update_type=update_type, status="success").inc()
            UPDATE_DURATION_SECONDS.labels(update_type=update_type).observe(elapsed)

            return result

        except Exception as exc:
            elapsed = time.perf_counter() - start_time

            UPDATES_TOTAL.labels(update_type=update_type, status="error").inc()
            UPDATE_DURATION_SECONDS.labels(update_type=update_type).observe(elapsed)
            ERRORS_TOTAL.labels(error_type=type(exc).__name__).inc()

            raise

    @staticmethod
    def _get_update_type(update: Update) -> str:
        """Extract update type for metric labels."""
        if update.message:
            return "message"
        if update.callback_query:
            return "callback_query"
        if update.inline_query:
            return "inline_query"
        if update.my_chat_member:
            return "my_chat_member"
        return "other"

    @staticmethod
    def _track_specific_metrics(update: Update) -> None:
        """Track command and callback-specific counters."""
        ACTIVE_USERS_TOTAL.inc()

        if update.message and update.message.text:
            text = update.message.text
            if text.startswith("/"):
                command = text.split()[0].split("@")[0]
                COMMANDS_TOTAL.labels(command=command).inc()

        if update.callback_query and update.callback_query.data:
            action = update.callback_query.data.split(":")[0]
            CALLBACK_QUERIES_TOTAL.labels(action=action).inc()
