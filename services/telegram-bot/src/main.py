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
import logging
import re
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

import structlog

from src.bot import create_bot, create_dispatcher
from src.config import BotSettings, get_settings
from src.stage1_surface import apply_stage1_telegram_surface

if TYPE_CHECKING:
    from aiogram import Bot, Dispatcher

logger = structlog.get_logger(__name__)
SERVICE_NAME = "cybervpn-telegram-bot"
RUNTIME_SURFACE = "telegram-bot"

SENSITIVE_HEADER_NAMES = {
    "authorization",
    "cookie",
    "set-cookie",
    "x-observability-secret",
    "x-telegram-bot-api-secret-token",
}
SENSITIVE_FIELD_MARKERS = (
    "token",
    "secret",
    "password",
    "cookie",
    "authorization",
    "jwt",
    "payload",
    "config",
    "wireguard",
    "vless",
    "vmess",
    "remnawave",
    "openbao",
    "opentofu",
    "nats",
    "payment",
    "oauth",
    "totp",
    "initdata",
    "init_data",
    "checkout",
    "invoice",
)
SENSITIVE_STRING_PATTERNS = (
    re.compile(r"\b(?:vless|vmess|trojan|wireguard|ss)://", re.IGNORECASE),
    re.compile(
        r"(?:access[_-]?token|refresh[_-]?token|id[_-]?token|auth[_-]?code|otp|totp|secret|password|telegram[_-]?init[_-]?data|initdata|tgWebAppData)=",
        re.IGNORECASE,
    ),
    re.compile(
        r"/api/v1/(?:vpn|xray|provisioning|subscriptions?)/(?:config|credentials|subscription)",
        re.IGNORECASE,
    ),
)


def build_webhook_url(base_url: object, path: str) -> str:
    """Join webhook base URL and path without duplicating slashes."""
    return f"{str(base_url).rstrip('/')}/{path.lstrip('/')}"


def _scrub_sensitive_value(value: Any) -> Any:
    if isinstance(value, str):
        if any(pattern.search(value) for pattern in SENSITIVE_STRING_PATTERNS):
            return "[Filtered]"
        return value

    if isinstance(value, dict):
        _scrub_sensitive_mapping(value)
        return value

    if isinstance(value, list):
        return [_scrub_sensitive_value(item) for item in value]

    return value


def _scrub_sensitive_mapping(payload: dict[str, Any]) -> None:
    for key, value in list(payload.items()):
        lowered_key = key.lower()
        if any(marker in lowered_key for marker in SENSITIVE_FIELD_MARKERS):
            payload[key] = "[Filtered]"
            continue

        payload[key] = _scrub_sensitive_value(value)


def _scrub_request_headers(headers: Any) -> None:
    if not isinstance(headers, dict):
        return

    for header_name in list(headers):
        if header_name.lower() in SENSITIVE_HEADER_NAMES:
            headers[header_name] = "[Filtered]"


def _strip_url_query(url: Any) -> Any:
    if not isinstance(url, str) or not url:
        return url

    parsed = urlparse(url)
    if not parsed.scheme and not parsed.netloc:
        return parsed.path or "/"

    return parsed._replace(query="", fragment="").geturl()


def _before_send(event: dict[str, Any], _hint: dict[str, Any]) -> dict[str, Any] | None:
    request = event.get("request")
    if isinstance(request, dict):
        _scrub_request_headers(request.get("headers"))
        request["url"] = _strip_url_query(request.get("url"))
        if "data" in request:
            request["data"] = "[Filtered]"
        if "cookies" in request:
            request["cookies"] = "[Filtered]"

    user = event.get("user")
    if isinstance(user, dict):
        for key in ("ip_address", "email", "username"):
            user.pop(key, None)

    for section_name in ("extra", "contexts"):
        section = event.get(section_name)
        if isinstance(section, dict):
            _scrub_sensitive_mapping(section)

    return event


def is_observability_authorized(
    configured_secret,
    provided_secret: str | None,
) -> bool:
    if configured_secret is None:
        return False

    configured = configured_secret.get_secret_value().strip()
    provided = (provided_secret or "").strip()
    if not configured or not provided:
        return False
    return hmac.compare_digest(configured, provided)


def setup_sentry(settings: BotSettings) -> bool:
    dsn = settings.sentry_dsn.strip()
    if not dsn:
        return False

    import sentry_sdk

    sentry_sdk.init(
        dsn=dsn,
        environment=settings.environment,
        release=settings.sentry_release or None,
        send_default_pii=False,
        max_request_body_size="never",
        include_local_variables=False,
        in_app_include=["src"],
        before_send=_before_send,
    )
    sentry_sdk.set_tag("runtime_surface", RUNTIME_SURFACE)
    sentry_sdk.set_tag("service.name", SERVICE_NAME)
    sentry_sdk.set_tag("bot_mode", settings.bot_mode)

    logger.info(
        "sentry_initialized",
        environment=settings.environment,
        release=settings.sentry_release or None,
        bot_mode=settings.bot_mode,
    )
    return True


async def on_startup(bot: Bot, settings: BotSettings) -> None:
    """Execute startup tasks: log bot info, set webhook if needed."""
    if settings.skip_telegram_network_calls:
        logger.info(
            "bot_startup_network_skipped",
            mode=settings.bot_mode,
            environment=settings.environment,
        )
        return

    bot_info = await bot.get_me()
    logger.info(
        "bot_started",
        username=bot_info.username,
        bot_id=bot_info.id,
        mode=settings.bot_mode,
        environment=settings.environment,
    )
    await apply_stage1_telegram_surface(bot, settings)

    if settings.bot_mode == "webhook":
        webhook_url = build_webhook_url(settings.webhook.url, settings.webhook.path)
        secret = settings.webhook.secret_token.get_secret_value() if settings.webhook.secret_token else None
        await bot.set_webhook(
            url=webhook_url,
            secret_token=secret,
            drop_pending_updates=True,
        )
        logger.info("webhook_set", url=webhook_url)


async def on_shutdown(bot: Bot, settings: BotSettings) -> None:
    """Execute graceful shutdown tasks."""
    logger.info("bot_shutting_down")
    if not settings.skip_telegram_network_calls:
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
    site = web.TCPSite(runner, host="0.0.0.0", port=settings.prometheus.port)  # noqa: S104
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

    logger.info(
        "starting_webhook_mode",
        port=settings.webhook.port,
        path=settings.webhook.path,
    )

    app = create_webhook_app(bot, dp, settings)
    web.run_app(
        app,
        host="0.0.0.0",  # noqa: S104 — bound inside container
        port=settings.webhook.port,
    )


def create_webhook_app(bot: Bot, dp: Dispatcher, settings: BotSettings):
    from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
    from aiohttp import web

    app = web.Application()

    async def health_handler(_request: web.Request) -> web.Response:
        return web.json_response(
            {
                "status": "ok",
                "mode": "webhook",
                "service": SERVICE_NAME,
                "environment": settings.environment,
            }
        )

    async def sentry_contract_handler(request: web.Request) -> web.Response:
        provided_secret = request.headers.get("x-observability-secret")
        if not is_observability_authorized(
            settings.observability_internal_secret,
            provided_secret,
        ):
            raise web.HTTPForbidden(text="Forbidden")

        return web.json_response(
            {
                "runtime_surface": RUNTIME_SURFACE,
                "service": SERVICE_NAME,
                "environment": settings.environment,
                "release": settings.sentry_release,
                "dsn_configured": bool(settings.sentry_dsn.strip()),
                "bot_mode": settings.bot_mode,
            }
        )

    app.router.add_get("/health", health_handler)
    app.router.add_get("/observability/sentry-contract", sentry_contract_handler)

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
    return app


async def _async_main(settings: BotSettings) -> None:
    """Async entry point for polling mode."""
    bot = create_bot(settings)
    dp = create_dispatcher(settings, bot)

    async def _on_startup(bot: Bot, **_: object) -> None:
        await on_startup(bot, settings)

    async def _on_shutdown(bot: Bot, **_: object) -> None:
        await on_shutdown(bot, settings)

    dp.shutdown.register(_on_shutdown)
    dp.startup.register(_on_startup)

    metrics_runner = None
    if settings.prometheus.enabled:
        metrics_runner = await _start_metrics_server(settings)

        async def _on_shutdown_metrics(*_: object, **__: object) -> None:
            await _stop_metrics_server(metrics_runner)

        dp.shutdown.register(_on_shutdown_metrics)

    await run_polling(bot, dp)


def main() -> None:
    """Application entry point supporting both polling and webhook modes."""
    settings = get_settings()

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer()
            if not settings.logging.json_format
            else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(settings.logging.level),
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    setup_sentry(settings)

    if settings.bot_mode == "webhook":
        bot = create_bot(settings)
        dp = create_dispatcher(settings, bot)

        async def _on_startup(bot: Bot, **_: object) -> None:
            await on_startup(bot, settings)

        async def _on_shutdown(bot: Bot, **_: object) -> None:
            await on_shutdown(bot, settings)

        dp.shutdown.register(_on_shutdown)
        dp.startup.register(_on_startup)
        run_webhook(bot, dp, settings)
    else:
        asyncio.run(_async_main(settings))


if __name__ == "__main__":
    main()
