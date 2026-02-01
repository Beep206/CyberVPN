"""CyberVPN Telegram Bot — Entry point.

Supports two modes controlled by BOT_MODE environment variable:
- polling (default, development) — long-polling via dp.start_polling()
- webhook (production) — aiohttp web server with SimpleRequestHandler
"""

from __future__ import annotations

import asyncio
import base64
import hmac
import ipaddress
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
        secret = settings.webhook.secret_token.get_secret_value() if settings.webhook.secret_token else None
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


def _build_allowed_networks(allowed_ips: list[str]) -> list[ipaddress._BaseNetwork]:
    networks: list[ipaddress._BaseNetwork] = []
    for raw in allowed_ips:
        try:
            networks.append(ipaddress.ip_network(raw, strict=False))
        except ValueError:
            logger.warning("invalid_prometheus_allowlist", entry=raw)
    return networks


def _get_client_ip(
    request,
    *,
    trust_proxy: bool,
    trusted_proxy_networks: list[ipaddress._BaseNetwork],
) -> str | None:
    remote = request.remote
    if not trust_proxy:
        return remote

    if not remote:
        return None

    try:
        remote_ip = ipaddress.ip_address(remote)
    except ValueError:
        return None

    if not any(remote_ip in network for network in trusted_proxy_networks):
        return remote

    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    return remote


def _get_request_scheme(
    request,
    *,
    trust_proxy: bool,
    trusted_proxy_networks: list[ipaddress._BaseNetwork],
) -> str:
    scheme = request.scheme
    if not trust_proxy:
        return scheme

    remote = request.remote
    if not remote:
        return scheme

    try:
        remote_ip = ipaddress.ip_address(remote)
    except ValueError:
        return scheme

    if not any(remote_ip in network for network in trusted_proxy_networks):
        return scheme

    forwarded_proto = request.headers.get("X-Forwarded-Proto")
    if forwarded_proto:
        return forwarded_proto.split(",")[0].strip()
    return scheme


def _parse_basic_auth(auth_header: str) -> tuple[str, str] | None:
    if not auth_header.startswith("Basic "):
        return None
    try:
        decoded = base64.b64decode(auth_header[6:]).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None
    if ":" not in decoded:
        return None
    username, password = decoded.split(":", 1)
    return username, password


def _build_metrics_handler(settings: BotSettings):
    from aiohttp import web
    from prometheus_client import generate_latest

    allowed_networks = _build_allowed_networks(settings.prometheus.allowed_ips)
    trusted_proxy_networks = _build_allowed_networks(settings.prometheus.trusted_proxy_ips)
    trust_proxy = settings.prometheus.trust_proxy
    require_tls = settings.prometheus.require_tls
    auth_user = settings.prometheus.basic_auth_user
    auth_password = (
        settings.prometheus.basic_auth_password.get_secret_value() if settings.prometheus.basic_auth_password else None
    )
    protect = settings.prometheus.protect

    async def metrics_handler(request: web.Request) -> web.Response:
        if protect:
            if require_tls:
                scheme = _get_request_scheme(
                    request,
                    trust_proxy=trust_proxy,
                    trusted_proxy_networks=trusted_proxy_networks,
                )
                if scheme != "https":
                    raise web.HTTPForbidden(text="TLS required")

            if allowed_networks:
                client_ip = _get_client_ip(
                    request,
                    trust_proxy=trust_proxy,
                    trusted_proxy_networks=trusted_proxy_networks,
                )
                if client_ip is None:
                    raise web.HTTPForbidden(text="Forbidden")
                try:
                    ip = ipaddress.ip_address(client_ip)
                except ValueError:
                    raise web.HTTPForbidden(text="Forbidden") from None
                if not any(ip in network for network in allowed_networks):
                    raise web.HTTPForbidden(text="Forbidden")

            if auth_user and auth_password:
                auth_header = request.headers.get("Authorization", "")
                creds = _parse_basic_auth(auth_header)
                if (
                    creds is None
                    or not hmac.compare_digest(creds[0], auth_user)
                    or not hmac.compare_digest(creds[1], auth_password)
                ):
                    raise web.HTTPUnauthorized(headers={"WWW-Authenticate": 'Basic realm="metrics"'})

        metrics = generate_latest()
        return web.Response(body=metrics, content_type="text/plain; version=0.0.4")

    return metrics_handler


async def _start_metrics_server(settings: BotSettings):
    from aiohttp import web

    app = web.Application()
    app.router.add_get(settings.prometheus.path, _build_metrics_handler(settings))

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=settings.prometheus.port)
    await site.start()

    logger.info(
        "prometheus_http_server_started",
        port=settings.prometheus.port,
        path=settings.prometheus.path,
        protect=settings.prometheus.protect,
    )
    return runner


async def _stop_metrics_server(runner) -> None:
    if runner is None:
        return
    await runner.cleanup()


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
        app.router.add_get(settings.prometheus.path, _build_metrics_handler(settings))
        logger.info(
            "prometheus_metrics_enabled",
            path=settings.prometheus.path,
            protect=settings.prometheus.protect,
        )

    secret = settings.webhook.secret_token.get_secret_value() if settings.webhook.secret_token else None
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
    dp = create_dispatcher(settings, bot)

    dp.startup.register(lambda bot: on_startup(bot, settings))
    dp.shutdown.register(on_shutdown)

    metrics_runner = None
    if settings.prometheus.enabled:
        metrics_runner = await _start_metrics_server(settings)
        dp.shutdown.register(lambda _: _stop_metrics_server(metrics_runner))

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
        dp = create_dispatcher(settings, bot)
        dp.startup.register(lambda bot: on_startup(bot, settings))
        dp.shutdown.register(on_shutdown)
        run_webhook(bot, dp, settings)
    else:
        asyncio.run(_async_main())


if __name__ == "__main__":
    main()
