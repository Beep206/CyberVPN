import pytest
from pydantic import SecretStr, ValidationError

from src.config.settings import Settings

_JWT_SECRET = "xVanw-qakEZA0v_T5mJ9GSCJkTzoWYpHMJDX02lFg-B8"  # gitleaks:allow -- synthetic test-only JWT secret
_REMNAWAVE_TOKEN = "valid-remnawave-api-token-with-32-characters"
_DROP_HMAC_SECRET = "connection-drop-domain-key-9a4c7e2f1b8d6305"


def _settings(**overrides) -> Settings:
    values = {
        "_env_file": None,
        "environment": "development",
        "jwt_secret": SecretStr(_JWT_SECRET),
        "remnawave_token": SecretStr(_REMNAWAVE_TOKEN),
        "cryptobot_token": SecretStr("valid-cryptobot-token-with-32-characters"),
        "remnawave_connection_drop_hmac_secret": SecretStr(_DROP_HMAC_SECRET),
    }
    values.update(overrides)
    return Settings(**values)


@pytest.mark.unit
def test_connection_drop_secret_accepts_dedicated_stable_key() -> None:
    configured = _settings()

    assert configured.remnawave_connection_drop_hmac_secret.get_secret_value() == _DROP_HMAC_SECRET


@pytest.mark.unit
def test_connection_drop_secret_can_be_empty_only_for_fail_closed_unavailable_routes() -> None:
    configured = _settings(remnawave_connection_drop_hmac_secret=SecretStr(""))

    assert configured.remnawave_connection_drop_hmac_secret.get_secret_value() == ""


@pytest.mark.unit
@pytest.mark.parametrize(
    "secret",
    [
        "too-short",
        "replace-with-connection-drop-secret-000000000000",
        "test-connection-drop-domain-key-00000000000000",
    ],
)
def test_connection_drop_secret_rejects_weak_or_placeholder_values(secret: str) -> None:
    with pytest.raises(ValidationError, match="REMNAWAVE_CONNECTION_DROP_HMAC_SECRET"):
        _settings(remnawave_connection_drop_hmac_secret=SecretStr(secret))


@pytest.mark.unit
@pytest.mark.parametrize(
    ("other_field", "expected_label"),
    [
        ("jwt_secret", "JWT_SECRET"),
        ("remnawave_token", "REMNAWAVE_TOKEN"),
        ("remnawave_webhook_secret", "REMNAWAVE_WEBHOOK_SECRET"),
        ("webhook_log_fingerprint_secret", "REMNAWAVE_CONNECTION_DROP_HMAC_SECRET"),
        ("remnawave_stream_ip_hmac_secret", "REMNAWAVE_STREAM_IP_HMAC_SECRET"),
        ("remnawave_node_ssh_broker_secret", "REMNAWAVE_NODE_SSH_BROKER_SECRET"),
        ("backend_internal_secret", "BACKEND_INTERNAL_SECRET"),
        ("payment_settlement_worker_secret", "PAYMENT_SETTLEMENT_WORKER_SECRET"),
        ("oauth_token_encryption_key", "OAUTH_TOKEN_ENCRYPTION_KEY"),
        ("totp_encryption_key", "TOTP_ENCRYPTION_KEY"),
    ],
)
def test_connection_drop_secret_cannot_reuse_co_resident_credentials(
    other_field: str,
    expected_label: str,
) -> None:
    with pytest.raises(ValidationError, match=rf"must differ from {expected_label}"):
        _settings(**{other_field: SecretStr(_DROP_HMAC_SECRET)})


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
def test_connection_drop_secret_cannot_reuse_decoded_dsn_password(
    other_field: str,
    expected_label: str,
    credential_url: str,
) -> None:
    encoded_secret = _DROP_HMAC_SECRET.replace("-", "%2D")

    with pytest.raises(ValidationError, match=rf"must differ from {expected_label}"):
        _settings(**{other_field: credential_url.format(secret=encoded_secret)})


@pytest.mark.unit
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("remnawave_connection_drop_terminal_ttl_seconds", 299),
        ("remnawave_connection_drop_terminal_ttl_seconds", 604_801),
        ("remnawave_connection_drop_max_active_receipts", 999),
        ("remnawave_connection_drop_max_active_per_actor", 9),
        ("remnawave_connection_drop_max_pending_per_actor", 0),
        ("remnawave_connection_drop_cleanup_batch_size", 5_001),
    ],
)
def test_connection_drop_capacity_and_retention_settings_are_bounded(field: str, value: int) -> None:
    with pytest.raises(ValidationError, match="REMNAWAVE_CONNECTION_DROP"):
        _settings(**{field: value})
