"""S1-PAY-002 CryptoBot sandbox/testnet config guards for task-worker."""

from __future__ import annotations

import pytest
from pydantic import SecretStr, ValidationError

from src.config import Settings


def _settings(**overrides: object) -> Settings:
    values = {
        "remnawave_api_token": SecretStr("remnawave-token-for-s1-pay-002"),
        "telegram_bot_token": SecretStr("123456:telegram-token-for-s1-pay-002"),
        "cryptobot_token": SecretStr("cryptobot-token-for-s1-pay-002"),
        "metrics_protect": False,
    }
    values.update(overrides)
    return Settings(**values)


def test_task_worker_allows_cryptobot_testnet_outside_production() -> None:
    settings = _settings(environment="staging", cryptobot_network="testnet")

    assert settings.cryptobot_network == "testnet"


def test_task_worker_production_rejects_cryptobot_testnet() -> None:
    with pytest.raises(ValidationError, match="CRYPTOBOT_NETWORK=testnet is not allowed in production"):
        _settings(environment="production", cryptobot_network="testnet")


def test_task_worker_production_rejects_placeholder_cryptobot_token() -> None:
    with pytest.raises(ValidationError, match="CRYPTOBOT_TOKEN must not be a placeholder/test value"):
        _settings(
            environment="production",
            cryptobot_token=SecretStr("your_cryptobot_api_token_here"),
        )


def test_task_worker_production_accepts_non_placeholder_provider_shaped_token() -> None:
    settings = _settings(
        environment="production",
        cryptobot_token=SecretStr("ValidProviderTokenValueForChecksOnly"),
    )

    assert settings.cryptobot_token.get_secret_value() == "ValidProviderTokenValueForChecksOnly"
