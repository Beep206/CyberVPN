"""CyberVPN Telegram Bot — Entry point.

Supports two modes controlled by BOT_MODE environment variable:
- polling (default, development) — long-polling via dp.start_polling()
- webhook (production) — aiohttp web server with SimpleRequestHandler
"""

from __future__ import annotations

import asyncio
import sys

import structlog
from aiogram import Bot, Dispatcher

from src.bot import create_bot, create_dispatcher
from src.config import BotSettings, get_settings

logger = structlog.get_logger(__name__)


async def on_startup(bot: Bot, settings: BotSettings) -> None:
    """Execute startup tasks: log bot info, set webhook if needed."""
    bot_info = await bot.get_me()
    logger.info(
        "bot_started",
        username=bot_info.username,
        bot_id=bot_info.id,
        mode=settings.bot_mode,
        environment=settings.environment,
    )

    if settings.bot_mode == "webhook":
        webhook_url = f"{settings.webhook.url}{settings.webhook.path}"
        secret = (
            settings.webhook.secret_token.get_secret_value()
            if settings.webhook.secret_token
            else None
        )
        await bot.set_webhook(
            url=webhook_url,
            secret_token=secret,
            drop_pending_updates=True,
        )
        logger.info("webhook_set", url=webhook_url)


async def on_shutdown(bot: Bot) -> None:
    """Execute graceful shutdown tasks."""
    logger.info("bot_shutting_down")
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.session.close()
    logger.info("bot_shutdown_complete")


async def run_polling(bot: Bot, dp: Dispatcher) -> None:
    """Start the bot in long-polling mode (development)."""
    logger.info("starting_polling_mode")
    await dp.start_polling(
        bot,
        allowed_updates=dp.resolve_used_update_types(),
    )


def run_webhook(bot: Bot, dp: Dispatcher, settings: BotSettings) -> None:
    """Start the bot in webhook mode (production).

    Creates an aiohttp web application with SimpleRequestHandler,
    health check endpoint, and optional Prometheus metrics endpoint.
    """
    from aiohttp import web

    from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

    logger.info(
        "starting_webhook_mode",
        port=settings.webhook.port,
        path=settings.webhook.path,
    )

    app = web.Application()

    # Health check endpoint
    async def health_handler(_request: web.Request) -> web.Response:
        return web.json_response({"status": "ok", "mode": "webhook"})

    app.router.add_get("/health", health_handler)

    # Prometheus metrics endpoint
    if settings.prometheus.enabled:
        from prometheus_client import generate_latest

        async def metrics_handler(_request: web.Request) -> web.Response:
            metrics = generate_latest()
            return web.Response(body=metrics, content_type="text/plain; version=0.0.4")

        app.router.add_get(settings.prometheus.path, metrics_handler)
        logger.info("prometheus_metrics_enabled", path=settings.prometheus.path)

    secret = (
        settings.webhook.secret_token.get_secret_value()
        if settings.webhook.secret_token
        else None
    )
    webhook_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=secret,
    )
    webhook_handler.register(app, path=settings.webhook.path)
    setup_application(app, dp, bot=bot)

    web.run_app(
        app,
        host="0.0.0.0",  # noqa: S104 — bound inside container
        port=settings.webhook.port,
    )


async def _async_main() -> None:
    """Async entry point for polling mode."""
    settings = get_settings()
    bot = create_bot(settings)
    dp = create_dispatcher(settings)

    dp.startup.register(lambda bot: on_startup(bot, settings))
    dp.shutdown.register(on_shutdown)

    # Start Prometheus HTTP server in polling mode
    if settings.prometheus.enabled:
        from prometheus_client import start_http_server

        start_http_server(settings.prometheus.port)
        logger.info(
            "prometheus_http_server_started",
            port=settings.prometheus.port,
        )

    await run_polling(bot, dp)


def main() -> None:
    """Application entry point supporting both polling and webhook modes."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer()
            if not get_settings().logging.json_format
            else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            structlog.get_level_from_name(get_settings().logging.level),
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    settings = get_settings()

    if settings.bot_mode == "webhook":
        bot = create_bot(settings)
        dp = create_dispatcher(settings)
        dp.startup.register(lambda bot: on_startup(bot, settings))
        dp.shutdown.register(on_shutdown)
        run_webhook(bot, dp, settings)
    else:
        asyncio.run(_async_main())


if __name__ == "__main__":
    main()
