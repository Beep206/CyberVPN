"""Configuration guards for the isolated Remnawave export Valkey."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import SecretStr, ValidationError

from src.config import Settings
from src.services.redis_client import create_remnawave_stream_redis_client


def _settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "remnawave_api_token": SecretStr("remnawave-token-for-stream-tests"),
        "telegram_bot_token": SecretStr("123456:telegram-token-for-stream-tests"),
        "cryptobot_token": SecretStr("cryptobot-token-for-stream-tests"),
        "backend_api_url": "https://backend.example.test/api/v1",
        "backend_internal_secret": SecretStr("BackendInternalCredentialForStreamTests"),
        "remnawave_stream_ip_hmac_secret": SecretStr("StreamIpHmacCredentialForTests-0000001"),
        "metrics_protect": False,
        "payment_completed_partner_earnings_enabled": False,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_enabled_stream_consumer_requires_dedicated_redis_url() -> None:
    with pytest.raises(ValidationError, match="REMNAWAVE_STREAM_REDIS_URL is required"):
        _settings(remnawave_stream_consumer_enabled=True, remnawave_stream_redis_url=None)


def test_enabled_stream_consumer_rejects_non_redis_url() -> None:
    with pytest.raises(ValidationError, match="valid redis:// or rediss:// URL"):
        _settings(
            remnawave_stream_consumer_enabled=True,
            remnawave_stream_redis_url=SecretStr("https://wrong-store.example.test"),
        )


def test_stream_consumer_defaults_to_stable_group() -> None:
    settings = _settings(
        remnawave_stream_consumer_enabled=True,
        remnawave_stream_redis_url=SecretStr("redis://remnawave-valkey.internal:6379/0"),
    )

    assert settings.remnawave_stream_consumer_group == "cybervpn-remnawave-v1"


def test_enabled_stream_consumer_rejects_noncanonical_group() -> None:
    with pytest.raises(ValidationError, match="must be exactly cybervpn-remnawave-v1"):
        _settings(
            remnawave_stream_consumer_enabled=True,
            remnawave_stream_redis_url=SecretStr("redis://remnawave-valkey.internal:6379/0"),
            remnawave_stream_consumer_group="secondary-analytics-group",
        )


def test_enabled_stream_consumer_requires_strong_hmac_secret() -> None:
    with pytest.raises(ValidationError, match="REMNAWAVE_STREAM_IP_HMAC_SECRET"):
        _settings(
            remnawave_stream_consumer_enabled=True,
            remnawave_stream_redis_url=SecretStr("redis://remnawave-valkey.internal:6379/0"),
            remnawave_stream_ip_hmac_secret=SecretStr("too-short"),
        )


@pytest.mark.parametrize(
    ("credential_field", "credential_label"),
    [
        ("remnawave_api_token", "REMNAWAVE_API_TOKEN"),
        ("backend_internal_secret", "BACKEND_INTERNAL_SECRET"),
        ("telegram_bot_internal_secret", "TELEGRAM_BOT_INTERNAL_SECRET"),
        ("payment_settlement_worker_secret", "PAYMENT_SETTLEMENT_WORKER_SECRET"),
        ("helix_adapter_token", "HELIX_ADAPTER_TOKEN"),
        ("telegram_bot_token", "TELEGRAM_BOT_TOKEN"),
        ("cryptobot_token", "CRYPTOBOT_TOKEN"),
        ("metrics_basic_auth_password", "METRICS_BASIC_AUTH_PASSWORD"),
        ("resend_api_key", "RESEND_API_KEY"),
        ("brevo_api_key", "BREVO_API_KEY"),
        ("smtp_auth_password", "SMTP_AUTH_PASSWORD"),
    ],
)
def test_stream_hmac_secret_cannot_reuse_worker_credentials(
    credential_field: str,
    credential_label: str,
) -> None:
    shared_value = "DedicatedStreamHmacDomainSecret-0000001"

    with pytest.raises(ValidationError, match=rf"must differ from {credential_label}"):
        _settings(
            remnawave_stream_consumer_enabled=True,
            remnawave_stream_redis_url=SecretStr("redis://remnawave-valkey.internal:6379/0"),
            remnawave_stream_ip_hmac_secret=SecretStr(shared_value),
            **{credential_field: SecretStr(shared_value)},
        )


@pytest.mark.parametrize(
    ("credential_field", "credential_label", "credential_url"),
    [
        (
            "database_url",
            "DATABASE_URL password",
            "postgresql+asyncpg://worker:{secret}@postgres.internal/cybervpn",
        ),
        ("redis_url", "REDIS_URL password", "redis://worker:{secret}@valkey.internal:6379/0"),
        (
            "remnawave_stream_redis_url",
            "REMNAWAVE_STREAM_REDIS_URL password",
            "redis://stream:{secret}@remnawave-valkey.internal:6379/0",
        ),
    ],
)
def test_stream_hmac_secret_cannot_reuse_url_passwords(
    credential_field: str,
    credential_label: str,
    credential_url: str,
) -> None:
    shared_value = "DedicatedStreamHmacDomainSecret-0000001"
    url_value = credential_url.format(secret=shared_value)
    override: object = SecretStr(url_value) if credential_field == "remnawave_stream_redis_url" else url_value
    values: dict[str, object] = {
        "remnawave_stream_consumer_enabled": True,
        "remnawave_stream_redis_url": SecretStr("redis://remnawave-valkey.internal:6379/0"),
        "remnawave_stream_ip_hmac_secret": SecretStr(shared_value),
        credential_field: override,
    }

    with pytest.raises(ValidationError, match=rf"must differ from {credential_label}"):
        _settings(**values)


def test_enabled_stream_retention_requires_backend_internal_boundary() -> None:
    with pytest.raises(ValidationError, match="required for Remnawave stream retention"):
        _settings(
            remnawave_stream_retention_enabled=True,
            backend_api_url=None,
            backend_internal_secret=None,
        )


def test_stream_retention_defaults_are_bounded() -> None:
    settings = _settings(remnawave_stream_retention_enabled=True)

    assert settings.remnawave_stream_retention_batch_limit == 1_000
    assert settings.remnawave_stream_retention_max_batches == 20


def test_stream_client_uses_dedicated_url_instead_of_taskiq_redis() -> None:
    settings = MagicMock()
    settings.redis_url = "redis://taskiq-valkey.internal:6379/0"
    settings.remnawave_stream_redis_url = SecretStr("redis://remnawave-valkey.internal:6379/0")
    expected_client = MagicMock()

    with (
        patch("src.services.redis_client.get_settings", return_value=settings),
        patch("src.services.redis_client.Redis.from_url", return_value=expected_client) as from_url,
    ):
        client = create_remnawave_stream_redis_client()

    assert client is expected_client
    from_url.assert_called_once_with(
        "redis://remnawave-valkey.internal:6379/0",
        max_connections=20,
        decode_responses=True,
        encoding="utf-8",
        socket_keepalive=True,
        socket_connect_timeout=5,
        retry_on_timeout=True,
    )
    assert settings.redis_url not in str(from_url.call_args)


@pytest.mark.asyncio
async def test_broker_lifecycle_uses_and_closes_dedicated_stream_client() -> None:
    from src import broker as broker_module

    class FakeBackendAPIClient:
        def __init__(self) -> None:
            self.entered = False
            self.exited = False

        async def __aenter__(self) -> FakeBackendAPIClient:
            self.entered = True
            return self

        async def __aexit__(self, *_args: object) -> None:
            self.exited = True

    class FakeTransport:
        def __init__(self, redis: object, *, payload_fingerprint_hmac_key: bytes) -> None:
            self.redis = redis
            self.payload_fingerprint_hmac_key = payload_fingerprint_hmac_key

    class FakeSink:
        def __init__(self, backend: object) -> None:
            self.backend = backend

    class FakeConsumer:
        def __init__(self, transport: object, sink: object, config: object) -> None:
            self.transport = transport
            self.sink = sink
            self.config = config
            self.initialized = False
            self.stopped = asyncio.Event()

        async def initialize(self) -> None:
            self.initialized = True

        async def run(self) -> None:
            await self.stopped.wait()

        def stop(self) -> None:
            self.stopped.set()

    settings = SimpleNamespace(
        remnawave_stream_consumer_group="cybervpn-remnawave-v1",
        remnawave_stream_read_count=50,
        remnawave_stream_block_ms=5_000,
        remnawave_stream_reclaim_count=50,
        remnawave_stream_reclaim_min_idle_ms=30_000,
        remnawave_stream_max_delivery_attempts=5,
        remnawave_stream_dlq_maxlen=3_000,
        remnawave_stream_receipt_retention_days=14,
        remnawave_stream_checkpoint_observe_interval_seconds=30.0,
        remnawave_stream_ip_hmac_secret=SecretStr("StreamIpHmacCredentialForTests-0000001"),
    )
    redis = AsyncMock()
    redis.aclose = AsyncMock()
    state = SimpleNamespace()

    with (
        patch.object(broker_module, "settings", settings),
        patch("src.services.backend_api_client.BackendAPIClient", FakeBackendAPIClient),
        patch(
            "src.services.redis_client.create_remnawave_stream_redis_client",
            return_value=redis,
        ) as create_stream_client,
        patch("src.services.remnawave_streams.RedisStreamTransport", FakeTransport),
        patch("src.services.remnawave_streams.BackendRemnawaveStreamSink", FakeSink),
        patch("src.services.remnawave_streams.RemnawaveStreamConsumer", FakeConsumer),
    ):
        await broker_module._start_remnawave_stream_consumer(state)

        assert state.remnawave_stream_consumer.initialized is True
        assert state.remnawave_stream_consumer.config.group_name == "cybervpn-remnawave-v1"
        assert state.remnawave_stream_consumer.transport.payload_fingerprint_hmac_key == (
            b"StreamIpHmacCredentialForTests-0000001"
        )
        assert state.remnawave_stream_backend.entered is True
        create_stream_client.assert_called_once_with()

        await broker_module._stop_remnawave_stream_consumer(state)

    assert state.remnawave_stream_consumer.stopped.is_set()
    assert state.remnawave_stream_backend.exited is True
    redis.aclose.assert_awaited_once_with()
