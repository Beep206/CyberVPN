"""CyberVPN Telegram Bot — Middleware stack."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aiogram import Bot, Dispatcher
    from redis.asyncio import Redis

    from src.config import BotSettings
    from src.services.api_client import CyberVPNAPIClient
    from src.services.cache_service import CacheService


def register_middlewares(
    dp: Dispatcher,
    settings: BotSettings,
    *,
    bot: Bot,
    api_client: CyberVPNAPIClient,
    cache: CacheService,
    redis: Redis,
) -> None:
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
    from src.middlewares.access_control import AccessControlMiddleware
    from src.middlewares.auth import AuthMiddleware
    from src.middlewares.i18n import I18nMiddleware, I18nManager
    from src.middlewares.logging import LoggingMiddleware
    from src.middlewares.metrics import MetricsMiddleware
    from src.middlewares.throttling import ThrottlingMiddleware

    # Outer middleware (applied to all update types)
    dp.update.outer_middleware(LoggingMiddleware())
    dp.update.outer_middleware(MetricsMiddleware())

    # Inner middleware (applied to messages and callbacks)
    dp.message.middleware(ThrottlingMiddleware(settings=settings, redis=redis))
    dp.callback_query.middleware(ThrottlingMiddleware(settings=settings, redis=redis))

    dp.message.middleware(
        AuthMiddleware(api_client=api_client, cache=cache, default_language=settings.default_language)
    )
    dp.callback_query.middleware(
        AuthMiddleware(api_client=api_client, cache=cache, default_language=settings.default_language)
    )

    dp.message.middleware(
        AccessControlMiddleware(
            bot_settings=settings,
            bot=bot,
            api_client=api_client,
            cache=cache,
        )
    )
    dp.callback_query.middleware(
        AccessControlMiddleware(
            bot_settings=settings,
            bot=bot,
            api_client=api_client,
            cache=cache,
        )
    )

    i18n_manager = I18nManager(
        locales=settings.available_languages,
        default_locale=settings.default_language,
    )
    dp.message.middleware(I18nMiddleware(i18n_manager=i18n_manager))
    dp.callback_query.middleware(I18nMiddleware(i18n_manager=i18n_manager))
