import pytest
from pydantic import SecretStr, ValidationError

from src.config.settings import Settings

_JWT_SECRET = "xVanw-qakEZA0v_T5mJ9GSCJkTzoWYpHMJDX02lFg-B8"  # gitleaks:allow -- synthetic test-only JWT secret
_REMNAWAVE_TOKEN = "valid-remnawave-api-token-with-32-characters"
_STREAM_HMAC_SECRET = "stream-hmac-domain-secret-with-32-characters"


def _settings(**overrides) -> Settings:
    values = {
        "_env_file": None,
        "environment": "development",
        "jwt_secret": SecretStr(_JWT_SECRET),
        "remnawave_token": SecretStr(_REMNAWAVE_TOKEN),
        "cryptobot_token": SecretStr("valid-cryptobot-token-with-32-characters"),
        "remnawave_stream_ingestion_enabled": True,
        "remnawave_stream_ip_hmac_secret": SecretStr(_STREAM_HMAC_SECRET),
    }
    values.update(overrides)
    return Settings(**values)


@pytest.mark.unit
def test_stream_hmac_secret_accepts_dedicated_domain_key() -> None:
    configured = _settings()

    assert configured.remnawave_stream_ip_hmac_secret.get_secret_value() == _STREAM_HMAC_SECRET
    assert configured.remnawave_stream_receipt_max_idle_seconds == 300


@pytest.mark.unit
@pytest.mark.parametrize("max_idle_seconds", [30, 3600])
def test_stream_receipt_max_idle_accepts_bounded_values(max_idle_seconds: int) -> None:
    configured = _settings(remnawave_stream_receipt_max_idle_seconds=max_idle_seconds)

    assert configured.remnawave_stream_receipt_max_idle_seconds == max_idle_seconds


@pytest.mark.unit
@pytest.mark.parametrize("max_idle_seconds", [29, 3601])
def test_stream_receipt_max_idle_rejects_out_of_bounds(max_idle_seconds: int) -> None:
    with pytest.raises(ValidationError, match="REMNAWAVE_STREAM_RECEIPT_MAX_IDLE_SECONDS"):
        _settings(remnawave_stream_receipt_max_idle_seconds=max_idle_seconds)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("other_field", "expected_label"),
    [
        ("jwt_secret", "JWT_SECRET"),
        ("remnawave_token", "REMNAWAVE_TOKEN"),
        ("remnawave_webhook_secret", "REMNAWAVE_WEBHOOK_SECRET"),
        ("remnawave_node_ssh_broker_secret", "REMNAWAVE_NODE_SSH_BROKER_SECRET"),
        ("vpn_tester_task2_xray_webhook_secret", "VPN_TESTER_TASK2_XRAY_WEBHOOK_SECRET"),
        ("vpn_test_agent_secret", "VPN_TEST_AGENT_SECRET"),
        ("vpn_test_agent_moscow_secret", "VPN_TEST_AGENT_MOSCOW_SECRET"),
        ("vpn_test_agent_spb_secret", "VPN_TEST_AGENT_SPB_SECRET"),
        ("helix_adapter_token", "HELIX_ADAPTER_TOKEN"),
        ("oauth_token_encryption_key", "OAUTH_TOKEN_ENCRYPTION_KEY"),
        ("github_client_secret", "GITHUB_CLIENT_SECRET"),
        ("telegram_bot_token", "TELEGRAM_BOT_TOKEN"),
        ("telegram_oidc_client_secret", "TELEGRAM_OIDC_CLIENT_SECRET"),
        ("telegram_bot_internal_secret", "TELEGRAM_BOT_INTERNAL_SECRET"),
        ("backend_internal_secret", "BACKEND_INTERNAL_SECRET"),
        ("frontend_observability_internal_secret", "FRONTEND_OBSERVABILITY_INTERNAL_SECRET"),
        ("payment_settlement_worker_secret", "PAYMENT_SETTLEMENT_WORKER_SECRET"),
        ("google_client_secret", "GOOGLE_CLIENT_SECRET"),
        ("discord_client_secret", "DISCORD_CLIENT_SECRET"),
        ("facebook_client_secret", "FACEBOOK_CLIENT_SECRET"),
        ("apple_private_key", "APPLE_PRIVATE_KEY"),
        ("microsoft_client_secret", "MICROSOFT_CLIENT_SECRET"),
        ("twitter_client_secret", "TWITTER_CLIENT_SECRET"),
        ("cryptobot_token", "CRYPTOBOT_TOKEN"),
        ("growth_code_hash_secret", "GROWTH_CODE_HASH_SECRET"),
        ("totp_encryption_key", "TOTP_ENCRYPTION_KEY"),
        ("posthog_project_api_key", "POSTHOG_PROJECT_API_KEY"),
    ],
)
def test_stream_hmac_secret_cannot_reuse_co_resident_credentials(
    other_field: str,
    expected_label: str,
) -> None:
    shared_secret = _STREAM_HMAC_SECRET

    with pytest.raises(ValidationError, match=rf"must differ from {expected_label}"):
        _settings(**{other_field: SecretStr(shared_secret)})


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
def test_stream_hmac_secret_cannot_reuse_decoded_url_password(
    other_field: str,
    expected_label: str,
    credential_url: str,
) -> None:
    encoded_secret = _STREAM_HMAC_SECRET.replace("-", "%2D")

    with pytest.raises(ValidationError, match=rf"must differ from {expected_label}"):
        _settings(**{other_field: credential_url.format(secret=encoded_secret)})
