from __future__ import annotations

import pytest
from pydantic import SecretStr, ValidationError

from src.config.settings import Settings

_JWT_SECRET = "xVanw-qakEZA0v_T5mJ9GSCJkTzoWYpHMJDX02lFg-B8"  # gitleaks:allow -- synthetic test-only JWT secret
_REMNAWAVE_TOKEN = "valid-remnawave-api-token-with-32-characters"
_CRYPTOBOT_TOKEN = "valid-cryptobot-token-with-32-characters"
_FINGERPRINT_SECRET = "webhook-fingerprint-key-8f1c7d9a2e6b4f03"


def _settings(**overrides) -> Settings:
    values = {
        "_env_file": None,
        "environment": "development",
        "jwt_secret": SecretStr(_JWT_SECRET),
        "remnawave_token": SecretStr(_REMNAWAVE_TOKEN),
        "cryptobot_token": SecretStr(_CRYPTOBOT_TOKEN),
        "webhook_log_fingerprint_secret": SecretStr(_FINGERPRINT_SECRET),
    }
    values.update(overrides)
    return Settings(**values)


@pytest.mark.unit
def test_webhook_log_fingerprint_secret_is_optional_for_privacy_closed_runtime() -> None:
    configured = _settings(webhook_log_fingerprint_secret=SecretStr(""))

    assert configured.webhook_log_fingerprint_secret.get_secret_value() == ""


@pytest.mark.unit
@pytest.mark.parametrize(
    "secret",
    [
        "too-short",
        "replace-with-webhook-log-fingerprint-secret",
        "test-webhook-fingerprint-key-12345678901234567890",
    ],
)
def test_webhook_log_fingerprint_secret_rejects_weak_or_placeholder_values(secret: str) -> None:
    with pytest.raises(ValidationError, match="WEBHOOK_LOG_FINGERPRINT_SECRET"):
        _settings(webhook_log_fingerprint_secret=SecretStr(secret))


@pytest.mark.unit
@pytest.mark.parametrize(
    ("other_field", "expected_label"),
    [
        ("jwt_secret", "JWT_SECRET"),
        ("remnawave_token", "REMNAWAVE_TOKEN"),
        ("remnawave_webhook_secret", "REMNAWAVE_WEBHOOK_SECRET"),
        ("remnawave_stream_ip_hmac_secret", "REMNAWAVE_STREAM_IP_HMAC_SECRET"),
        ("remnawave_node_ssh_broker_secret", "REMNAWAVE_NODE_SSH_BROKER_SECRET"),
        ("cryptobot_token", "CRYPTOBOT_TOKEN"),
        ("telegram_bot_token", "TELEGRAM_BOT_TOKEN"),
        ("backend_internal_secret", "BACKEND_INTERNAL_SECRET"),
        ("payment_settlement_worker_secret", "PAYMENT_SETTLEMENT_WORKER_SECRET"),
        ("totp_encryption_key", "TOTP_ENCRYPTION_KEY"),
        ("oauth_token_encryption_key", "OAUTH_TOKEN_ENCRYPTION_KEY"),
    ],
)
def test_webhook_log_fingerprint_secret_cannot_reuse_co_resident_credentials(
    other_field: str,
    expected_label: str,
) -> None:
    with pytest.raises(ValidationError, match=rf"must differ from {expected_label}"):
        _settings(**{other_field: SecretStr(_FINGERPRINT_SECRET)})


@pytest.mark.unit
@pytest.mark.parametrize(
    ("other_field", "expected_label", "credential_url"),
    [
        (
            "database_url",
            "DATABASE_URL password",
            "postgresql+asyncpg://backend:{secret}@postgres.internal/cybervpn",
        ),
        ("redis_url", "REDIS_URL password", "redis://backend:{secret}@valkey.internal:6379/0"),
    ],
)
def test_webhook_log_fingerprint_secret_cannot_reuse_decoded_dsn_password(
    other_field: str,
    expected_label: str,
    credential_url: str,
) -> None:
    encoded_secret = _FINGERPRINT_SECRET.replace("-", "%2D")

    with pytest.raises(ValidationError, match=rf"must differ from {expected_label}"):
        _settings(**{other_field: credential_url.format(secret=encoded_secret)})
