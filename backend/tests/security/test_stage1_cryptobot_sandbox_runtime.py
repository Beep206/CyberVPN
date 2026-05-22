# ruff: noqa: S101

"""S1-PAY-002 CryptoBot sandbox/testnet runtime guards."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import SecretStr, ValidationError

from src.config.settings import S1_PRODUCTION_CORS_ORIGINS, Settings
from src.infrastructure.payments.cryptobot.client import CryptoBotClient

STRONG_SECRET = "qHj9mV8sW3zR6tY1nP4cL7dF2gK5bX0aQ9wE6rT3yU8iO1pA"  # gitleaks:allow


def _settings(**overrides: object) -> Settings:
    values = {
        "remnawave_token": SecretStr("remnawave-token-for-s1-pay-002"),
        "jwt_secret": SecretStr(STRONG_SECRET),
        "cryptobot_token": SecretStr("cryptobot-token-redacted-for-s1-pay-002"),
    }
    values.update(overrides)
    return Settings(**values)


def _production_settings(**overrides: object) -> Settings:
    values = {
        "environment": "production",
        "cors_origins": list(S1_PRODUCTION_CORS_ORIGINS),
        "admin_2fa_required": True,
        "cookie_secure": True,
        "totp_encryption_key": SecretStr(STRONG_SECRET),
        "oauth_token_encryption_key": SecretStr(STRONG_SECRET),
        "oauth_enabled_login_providers": [],
    }
    values.update(overrides)
    return _settings(**values)


def test_cryptobot_testnet_endpoint_is_selectable_outside_production() -> None:
    _settings(environment="staging", cryptobot_network="testnet")

    client = CryptoBotClient(
        token=SecretStr("cryptobot-token-redacted-for-s1-pay-002"),
        network="testnet",
    )

    assert client.network == "testnet"
    assert client.base_url == "https://testnet-pay.crypt.bot/api"


def test_cryptobot_defaults_to_mainnet_endpoint() -> None:
    client = CryptoBotClient(
        token=SecretStr("cryptobot-token-redacted-for-s1-pay-002"),
        network="mainnet",
    )

    assert client.network == "mainnet"
    assert client.base_url == "https://pay.crypt.bot/api"


def test_cryptobot_production_rejects_testnet_network() -> None:
    with pytest.raises(ValidationError, match="CRYPTOBOT_NETWORK=testnet is not allowed in production"):
        _production_settings(cryptobot_network="testnet")


def test_cryptobot_client_rejects_unknown_network() -> None:
    with pytest.raises(ValueError, match="Unsupported CryptoBot network"):
        CryptoBotClient(
            token=SecretStr("cryptobot-token-redacted-for-s1-pay-002"),
            network="sandbox",  # type: ignore[arg-type]
        )


def test_cryptobot_production_rejects_placeholder_token() -> None:
    with pytest.raises(ValidationError, match="CRYPTOBOT_TOKEN must not be a placeholder/test value"):
        _production_settings(cryptobot_token=SecretStr("_REPLACE_IN_PRODUCTION_cryptobot_token"))


def test_cryptobot_production_accepts_non_placeholder_provider_shaped_token() -> None:
    settings = _production_settings(cryptobot_token=SecretStr("ValidProviderTokenValueForChecksOnly"))

    assert settings.cryptobot_token.get_secret_value() == "ValidProviderTokenValueForChecksOnly"


@pytest.mark.asyncio
async def test_cryptobot_create_invoice_uses_fiat_contract_for_usd() -> None:
    with patch("src.infrastructure.payments.cryptobot.client.AsyncClient") as client_cls:
        http_client = MagicMock()
        http_client.is_closed = False
        response = MagicMock()
        response.json.return_value = {"ok": True, "result": {"invoice_id": 123}}
        http_client.post = AsyncMock(return_value=response)
        client_cls.return_value = http_client

        client = CryptoBotClient(token=SecretStr("cryptobot-token-redacted"), network="mainnet")
        await client.create_invoice(
            amount="9.99",
            currency="USD",
            description="CyberVPN Basic",
            payload="user:plan",
        )

    _, kwargs = http_client.post.call_args
    assert kwargs["json"]["currency_type"] == "fiat"
    assert kwargs["json"]["fiat"] == "USD"
    assert "asset" not in kwargs["json"]


@pytest.mark.asyncio
async def test_cryptobot_create_invoice_uses_crypto_contract_for_usdt() -> None:
    with patch("src.infrastructure.payments.cryptobot.client.AsyncClient") as client_cls:
        http_client = MagicMock()
        http_client.is_closed = False
        response = MagicMock()
        response.json.return_value = {"ok": True, "result": {"invoice_id": 123}}
        http_client.post = AsyncMock(return_value=response)
        client_cls.return_value = http_client

        client = CryptoBotClient(token=SecretStr("cryptobot-token-redacted"), network="mainnet")
        await client.create_invoice(
            amount="9.99",
            currency="USDT",
            description="CyberVPN Basic",
            payload="user:plan",
        )

    _, kwargs = http_client.post.call_args
    assert kwargs["json"]["currency_type"] == "crypto"
    assert kwargs["json"]["asset"] == "USDT"
    assert "fiat" not in kwargs["json"]
