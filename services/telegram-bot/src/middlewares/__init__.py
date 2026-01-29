"""CyberVPN Telegram Bot — Middleware stack."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aiogram import Bot, Dispatcher

    from src.config import BotSettings


def register_middlewares(dp: Dispatcher, settings: BotSettings) -> None:
    """Register all middleware in correct execution order.

    Order matters — middleware executes top-to-bottom on request,
    bottom-to-top on response:

    1. Logging — logs every update before processing
    2. Metrics — tracks Prometheus counters
    3. Throttling — rate-limits before expensive operations
    4. Auth — identifies/registers user, injects data['user']
    5. Access control — checks maintenance mode, rules, channel sub
    6. i18n — resolves locale for downstream handlers

    Args:
        dp: Dispatcher to register middleware on.
        settings: Bot settings for middleware configuration.
    """
    from src.middlewares.logging import LoggingMiddleware
    from src.middlewares.metrics import MetricsMiddleware
    from src.middlewares.throttling import ThrottlingMiddleware

    # Outer middleware (applied to all update types)
    dp.update.outer_middleware(LoggingMiddleware())
    dp.update.outer_middleware(MetricsMiddleware())

    # Inner middleware (applied to messages and callbacks)
    dp.message.middleware(ThrottlingMiddleware(settings=settings))
    dp.callback_query.middleware(ThrottlingMiddleware(settings=settings))
