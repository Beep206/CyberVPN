from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from aiogram import Bot, Dispatcher
from aiohttp.test_utils import TestClient, TestServer
from pydantic import SecretStr, ValidationError

from src.config import (
    BackendSettings,
    BotSettings,
    CryptoBotSettings,
    LoggingSettings,
    PrometheusSettings,
    RedisSettings,
    ReferralSettings,
    TelegramStarsSettings,
    TrialSettings,
    WebhookSettings,
    YooKassaSettings,
    get_settings,
)
from src.main import (
    _before_send,
    build_webhook_url,
    create_webhook_app,
    on_shutdown,
    on_startup,
    setup_sentry,
)


def build_settings(**overrides: Any) -> BotSettings:
    base = {
        "bot_token": SecretStr("1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"),
        "bot_mode": "polling",
        "skip_telegram_network_calls": False,
        "environment": "staging",
        "sentry_dsn": "https://telegram@example.com/1",
        "sentry_release": "telegram-bot@abc123",
        "observability_internal_secret": SecretStr("telegram-observability-secret"),
        "admin_ids": [123456789],
        "support_username": "TestSupport",
        "default_language": "ru",
        "available_languages": ["ru", "en"],
        "webhook": WebhookSettings(
            url=None,
            path="/webhook/telegram",
            port=8080,
            secret_token=None,
        ),
        "backend": BackendSettings(
            api_url="https://api.test.cybervpn.local",
            api_key=SecretStr("fixture"),
            timeout=30,
            max_retries=3,
            retry_backoff=0.5,
        ),
        "redis": RedisSettings(
            url="redis://localhost:6379",
            db=1,
            password=None,
            key_prefix="cybervpn:test:",
            ttl_seconds=3600,
        ),
        "cryptobot": CryptoBotSettings(
            enabled=True,
            token=SecretStr("test_cryptobot_token"),
            network="testnet",
        ),
        "yookassa": YooKassaSettings(enabled=False, shop_id=None, secret_key=None, test_mode=True),
        "telegram_stars": TelegramStarsSettings(enabled=True),
        "trial": TrialSettings(enabled=True, days=7, traffic_gb=0),
        "referral": ReferralSettings(enabled=True, bonus_days=3, max_referrals=100),
        "logging": LoggingSettings(level="INFO", json_format=True, show_locals=False),
        "prometheus": PrometheusSettings(enabled=False, protect=False, port=9090, path="/metrics"),
    }
    base.update(overrides)
    return BotSettings(**base)


def test_production_rejects_placeholder_cryptobot_token() -> None:
    with pytest.raises(ValidationError, match="CRYPTOBOT_TOKEN must not be a placeholder/test value"):
        build_settings(
            environment="production",
            bot_username="CyberVPNBot",
            production_bot_username="CyberVPNBot",
            cryptobot=CryptoBotSettings(
                enabled=True,
                token=SecretStr("your-cryptobot-token"),
                network="mainnet",
            ),
        )


def test_production_accepts_non_placeholder_cryptobot_token() -> None:
    settings = build_settings(
        environment="production",
        bot_username="CyberVPNBot",
        production_bot_username="CyberVPNBot",
        cryptobot=CryptoBotSettings(
            enabled=True,
            token=SecretStr("ValidProviderTokenValueForChecksOnly"),
            network="mainnet",
        ),
    )

    assert settings.cryptobot.token is not None
    assert settings.cryptobot.token.get_secret_value() == "ValidProviderTokenValueForChecksOnly"


def test_setup_sentry_skips_init_without_dsn() -> None:
    settings = build_settings(sentry_dsn="", sentry_release="")

    with patch("sentry_sdk.init") as mock_init:
        initialized = setup_sentry(settings)

    assert initialized is False
    mock_init.assert_not_called()


def test_build_webhook_url_normalizes_base_and_path_slashes() -> None:
    assert build_webhook_url("https://api.cyber-vpn.net/", "/webhook/telegram") == (
        "https://api.cyber-vpn.net/webhook/telegram"
    )
    assert build_webhook_url("https://api.cyber-vpn.net", "webhook/telegram") == (
        "https://api.cyber-vpn.net/webhook/telegram"
    )


def test_setup_sentry_uses_minimal_pii_contract() -> None:
    settings = build_settings()

    with (
        patch("sentry_sdk.init") as mock_init,
        patch("sentry_sdk.set_tag") as mock_set_tag,
    ):
        initialized = setup_sentry(settings)

    assert initialized is True
    mock_init.assert_called_once_with(
        dsn="https://telegram@example.com/1",
        environment="staging",
        release="telegram-bot@abc123",
        send_default_pii=False,
        max_request_body_size="never",
        include_local_variables=False,
        in_app_include=["src"],
        before_send=_before_send,
    )
    mock_set_tag.assert_any_call("runtime_surface", "telegram-bot")
    mock_set_tag.assert_any_call("service.name", "cybervpn-telegram-bot")
    mock_set_tag.assert_any_call("bot_mode", "polling")


def test_before_send_scrubs_sensitive_fields() -> None:
    event = {
        "request": {
            "url": "https://bot.cyber-vpn.net/webhook/telegram?token=secret#hash",
            "headers": {
                "Authorization": "Bearer secret",
                "X-Observability-Secret": "internal-secret",
                "X-Telegram-Bot-Api-Secret-Token": "telegram-secret",
                "X-Request-Id": "req-1",
            },
            "data": {"telegram_update": {"message": "secret"}},
            "cookies": {"session": "secret-cookie"},
        },
        "user": {
            "id": "123",
            "email": "user@example.com",
            "username": "telegram-user",
            "ip_address": "127.0.0.1",
        },
        "extra": {
            "telegram_payload": {"message": "secret"},
            "payment_provider_id": "pay_123",
            "provider_name": "cryptobot",
            "wireguard_config": "sensitive-config",
            "support_excerpt": "user pasted vless://sensitive-config",
        },
        "contexts": {
            "bot": {
                "bot_token": "secret-token",
                "flow_step": "checkout",
            }
        },
    }

    scrubbed = _before_send(event, {})

    assert scrubbed is event
    assert event["request"]["headers"]["Authorization"] == "[Filtered]"
    assert event["request"]["headers"]["X-Observability-Secret"] == "[Filtered]"
    assert event["request"]["headers"]["X-Telegram-Bot-Api-Secret-Token"] == "[Filtered]"
    assert event["request"]["headers"]["X-Request-Id"] == "req-1"
    assert event["request"]["url"] == "https://bot.cyber-vpn.net/webhook/telegram"
    assert event["request"]["data"] == "[Filtered]"
    assert event["request"]["cookies"] == "[Filtered]"
    assert "email" not in event["user"]
    assert "username" not in event["user"]
    assert "ip_address" not in event["user"]
    assert event["extra"]["telegram_payload"] == "[Filtered]"
    assert event["extra"]["payment_provider_id"] == "[Filtered]"
    assert event["extra"]["provider_name"] == "cryptobot"
    assert event["extra"]["wireguard_config"] == "[Filtered]"
    assert event["extra"]["support_excerpt"] == "[Filtered]"
    assert event["contexts"]["bot"]["bot_token"] == "[Filtered]"
    assert event["contexts"]["bot"]["flow_step"] == "checkout"


def test_get_settings_loads_sentry_contract_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("BOT_TOKEN", "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz")
    monkeypatch.setenv("BOT_MODE", "polling")
    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.setenv("SENTRY_DSN", "https://telegram@example.com/1")
    monkeypatch.setenv("SENTRY_RELEASE", "telegram-bot@testsha")
    monkeypatch.setenv("TELEGRAM_BOT_SKIP_NETWORK_CALLS", "true")
    monkeypatch.setenv("TELEGRAM_BOT_OBSERVABILITY_INTERNAL_SECRET", "telegram-observability-secret")
    monkeypatch.setenv("TELEGRAM_THROTTLE_ENABLED", "true")
    monkeypatch.setenv("TELEGRAM_THROTTLE_FAIL_OPEN", "false")
    monkeypatch.setenv("TELEGRAM_MESSAGE_RATE_WINDOW_SECONDS", "12")
    monkeypatch.setenv("TELEGRAM_MESSAGE_RATE_MAX_REQUESTS", "4")
    monkeypatch.setenv("TELEGRAM_CALLBACK_RATE_WINDOW_SECONDS", "5")
    monkeypatch.setenv("TELEGRAM_CALLBACK_RATE_MAX_REQUESTS", "2")
    monkeypatch.setenv("BACKEND_API_URL", "https://api.test.cybervpn.local")
    monkeypatch.setenv("BACKEND_API_KEY", "fixture")
    monkeypatch.setenv("CRYPTOBOT_TOKEN", "test_cryptobot_token")
    monkeypatch.setenv("PROMETHEUS_ENABLED", "false")
    monkeypatch.setenv("PROMETHEUS_PROTECT", "false")
    monkeypatch.setenv("AVAILABLE_LANGUAGES", '["ru", "en"]')

    get_settings.cache_clear()
    settings = get_settings()

    assert settings.environment == "staging"
    assert settings.sentry_dsn == "https://telegram@example.com/1"
    assert settings.sentry_release == "telegram-bot@testsha"
    assert settings.skip_telegram_network_calls is True
    assert settings.observability_internal_secret is not None
    assert settings.observability_internal_secret.get_secret_value() == "telegram-observability-secret"
    assert settings.telegram_throttle_enabled is True
    assert settings.telegram_throttle_fail_open is False
    assert settings.telegram_message_rate_window_seconds == 12
    assert settings.telegram_message_rate_max_requests == 4
    assert settings.telegram_callback_rate_window_seconds == 5
    assert settings.telegram_callback_rate_max_requests == 2

    get_settings.cache_clear()


def test_get_settings_accepts_comma_separated_list_envs(monkeypatch) -> None:
    monkeypatch.setenv("BOT_TOKEN", "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz")
    monkeypatch.setenv("BOT_MODE", "polling")
    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.setenv("BACKEND_API_URL", "https://api.test.cybervpn.local")
    monkeypatch.setenv("BACKEND_API_KEY", "fixture")
    monkeypatch.setenv("CRYPTOBOT_TOKEN", "test_cryptobot_token")
    monkeypatch.setenv("PROMETHEUS_ENABLED", "false")
    monkeypatch.setenv("PROMETHEUS_PROTECT", "false")
    monkeypatch.setenv("AVAILABLE_LANGUAGES", "ru,en")
    monkeypatch.setenv("ADMIN_IDS", "123,456")

    get_settings.cache_clear()
    settings = get_settings()

    assert settings.available_languages == ["ru", "en"]
    assert settings.admin_ids == [123, 456]

    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_on_startup_skips_telegram_calls_when_configured() -> None:
    settings = build_settings(
        bot_mode="webhook",
        skip_telegram_network_calls=True,
        webhook=WebhookSettings(
            url="https://bot.test.cybervpn.local",
            path="/webhook/telegram",
            port=8080,
            secret_token=SecretStr("webhook-secret"),
        ),
    )
    bot = AsyncMock()

    await on_startup(bot, settings)

    bot.get_me.assert_not_awaited()
    bot.set_webhook.assert_not_awaited()


@pytest.mark.asyncio
async def test_on_startup_configures_stage1_commands_and_menu() -> None:
    settings = build_settings(skip_telegram_network_calls=False)
    bot = AsyncMock()
    bot.get_me = AsyncMock(return_value=type("BotInfo", (), {"username": "CyberVPNStageBot", "id": 12345})())
    bot.set_my_commands = AsyncMock()
    bot.set_chat_menu_button = AsyncMock()

    await on_startup(bot, settings)

    bot.get_me.assert_awaited_once()
    bot.set_my_commands.assert_awaited_once()
    command_names = [command.command for command in bot.set_my_commands.await_args.kwargs["commands"]]
    assert command_names == ["start", "menu", "connect", "plans", "trial", "support", "paysupport"]
    bot.set_chat_menu_button.assert_awaited_once()
    assert bot.set_chat_menu_button.await_args.kwargs["menu_button"].type.value == "commands"


@pytest.mark.asyncio
async def test_on_shutdown_skips_delete_webhook_when_configured() -> None:
    settings = build_settings(skip_telegram_network_calls=True)
    bot = AsyncMock()
    bot.session.close = AsyncMock()

    await on_shutdown(bot, settings)

    bot.delete_webhook.assert_not_awaited()
    bot.session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_webhook_app_exposes_observability_contract() -> None:
    settings = build_settings(
        bot_mode="webhook",
        skip_telegram_network_calls=True,
        webhook=WebhookSettings(
            url="https://bot.test.cybervpn.local",
            path="/webhook/telegram",
            port=8080,
            secret_token=SecretStr("webhook-secret"),
        ),
    )
    bot = Bot(token="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz")
    app = create_webhook_app(bot, Dispatcher(), settings)

    async with TestServer(app) as server, TestClient(server) as client:
        forbidden = await client.get("/observability/sentry-contract")
        assert forbidden.status == 403

        response = await client.get(
            "/observability/sentry-contract",
            headers={"x-observability-secret": "telegram-observability-secret"},
        )
        assert response.status == 200
        assert await response.json() == {
            "runtime_surface": "telegram-bot",
            "service": "cybervpn-telegram-bot",
            "environment": "staging",
            "release": "telegram-bot@abc123",
            "dsn_configured": True,
            "bot_mode": "webhook",
        }

        health = await client.get("/health")
        assert health.status == 200
        assert await health.json() == {
            "status": "ok",
            "mode": "webhook",
            "service": "cybervpn-telegram-bot",
            "environment": "staging",
        }

    await bot.session.close()
