import hashlib
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import SecretStr
from sqlalchemy.dialects import postgresql

from src.application.services.remnawave_stream_ingestion import (
    ConnectionIp,
    ConnectionUser,
    RemnawaveStreamIngestionError,
    RemnawaveStreamIngestionService,
    UsageRecord,
    payload_fingerprint,
)
from src.config.settings import settings


def _scalar_result(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


@pytest.mark.asyncio
async def test_usage_accepts_clock_skew_boundary_but_caps_expiry_from_ingestion_time(
    monkeypatch,
) -> None:
    received_at = datetime(2026, 8, 30, 14, 0, tzinfo=UTC)
    producer_at = received_at + timedelta(minutes=5)
    monkeypatch.setattr(settings, "remnawave_user_usage_retention_days", 180)
    session = MagicMock()
    session.execute = AsyncMock(side_effect=[_scalar_result(None), MagicMock(), MagicMock()])
    session.flush = AsyncMock()

    persisted = await RemnawaveStreamIngestionService(
        session,
        clock=lambda: received_at,
    ).persist_user_usage(
        idempotency_key="remnawave:user_usage:1725024000000-7",
        payload_sha256="f" * 64,
        schema_version="1",
        node_id=7,
        observed_at=producer_at,
        records=[UsageRecord(user_id=41, total_bytes=25)],
    )

    assert persisted is True
    compiled = session.execute.await_args_list[1].args[0].compile(dialect=postgresql.dialect())
    assert compiled.params["expires_at"] == received_at + timedelta(days=180)
    assert compiled.params["expires_at"] != producer_at + timedelta(days=180)


@pytest.mark.asyncio
async def test_usage_rejects_far_future_timestamp_before_database_access() -> None:
    received_at = datetime(2026, 8, 30, 14, 0, tzinfo=UTC)
    session = MagicMock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()

    with pytest.raises(RemnawaveStreamIngestionError, match="clock skew"):
        await RemnawaveStreamIngestionService(
            session,
            clock=lambda: received_at,
        ).persist_user_usage(
            idempotency_key="remnawave:user_usage:1725024000000-8",
            payload_sha256="f" * 64,
            schema_version="1",
            node_id=7,
            observed_at=received_at + timedelta(minutes=5, microseconds=1),
            records=[UsageRecord(user_id=41, total_bytes=25)],
        )

    session.execute.assert_not_awaited()
    session.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_subscription_retention_uses_ingestion_time_not_producer_time(monkeypatch) -> None:
    received_at = datetime(2026, 8, 30, 14, 0, tzinfo=UTC)
    requested_at = received_at - timedelta(days=20)
    monkeypatch.setattr(settings, "remnawave_subscription_request_retention_days", 30)
    session = MagicMock()
    session.execute = AsyncMock(return_value=_scalar_result(None))
    session.flush = AsyncMock()

    persisted = await RemnawaveStreamIngestionService(
        session,
        clock=lambda: received_at,
    ).persist_subscription_request(
        idempotency_key="remnawave:subscription_requests:1725024000000-3",
        payload_sha256="e" * 64,
        schema_version="1",
        user_id=41,
        requested_at=requested_at,
        request_ip=None,
        user_agent=None,
        srr_rule_name=None,
        srr_response_type="base64",
    )

    assert persisted is True
    event = session.add.call_args_list[0].args[0]
    assert event.requested_at == requested_at
    assert event.expires_at == received_at + timedelta(days=30)


@pytest.mark.asyncio
async def test_node_connections_serializes_replicas_and_atomically_increments_hourly_counts(
    monkeypatch,
) -> None:
    received_at = datetime(2026, 8, 30, 14, 10, tzinfo=UTC)
    observed_at = datetime(2026, 8, 30, 14, 5, tzinfo=UTC)
    monkeypatch.setattr(settings, "remnawave_stream_ip_hmac_secret", SecretStr("s" * 64))
    session = MagicMock()
    session.execute = AsyncMock(
        side_effect=[
            _scalar_result(None),
            MagicMock(),
            _scalar_result(observed_at - timedelta(minutes=1)),
            MagicMock(),
            MagicMock(),
            MagicMock(),
        ]
    )
    session.flush = AsyncMock()

    persisted = await RemnawaveStreamIngestionService(
        session,
        clock=lambda: received_at,
    ).persist_node_connections(
        idempotency_key="remnawave:node_connections:1725024000000-4",
        payload_sha256="d" * 64,
        schema_version="1",
        node_id=7,
        observed_at=observed_at,
        users=[
            ConnectionUser(
                user_id=41,
                ips=(ConnectionIp(ip="203.0.113.4", last_seen=observed_at),),
            )
        ],
    )

    assert persisted is True
    statements = [call.args[0] for call in session.execute.await_args_list]
    assert "pg_advisory_xact_lock" in str(statements[1])
    hourly = statements[4].compile(dialect=postgresql.dialect())
    sql = str(hourly)
    assert "ON CONFLICT ON CONSTRAINT uq_remnawave_node_connections_hour DO UPDATE" in sql
    assert "connection_count = (remnawave_node_connections_hourly.connection_count + excluded.connection_count)" in sql
    assert hourly.params["connection_count"] == 1


@pytest.mark.asyncio
async def test_node_connections_stale_snapshot_cannot_replace_newer_presence(monkeypatch) -> None:
    received_at = datetime(2026, 8, 30, 14, 10, tzinfo=UTC)
    observed_at = datetime(2026, 8, 30, 14, 5, tzinfo=UTC)
    monkeypatch.setattr(settings, "remnawave_stream_ip_hmac_secret", SecretStr("s" * 64))
    session = MagicMock()
    session.execute = AsyncMock(
        side_effect=[
            _scalar_result(None),
            MagicMock(),
            _scalar_result(observed_at + timedelta(minutes=1)),
            MagicMock(),
            MagicMock(),
        ]
    )
    session.flush = AsyncMock()

    persisted = await RemnawaveStreamIngestionService(
        session,
        clock=lambda: received_at,
    ).persist_node_connections(
        idempotency_key="remnawave:node_connections:1725024000000-5",
        payload_sha256="c" * 64,
        schema_version="1",
        node_id=7,
        observed_at=observed_at,
        users=[
            ConnectionUser(
                user_id=41,
                ips=(ConnectionIp(ip="203.0.113.5", last_seen=observed_at),),
            )
        ],
    )

    assert persisted is True
    statements = [str(call.args[0]) for call in session.execute.await_args_list]
    assert not any(statement.startswith("DELETE FROM remnawave_node_user_presence") for statement in statements)
    added_models = [call.args[0] for call in session.add.call_args_list]
    assert not any(model.__class__.__name__ == "RemnawaveNodePresenceModel" for model in added_models)


@pytest.mark.asyncio
async def test_rest_reconciliation_replaces_only_current_presence_without_hourly_fabrication(monkeypatch) -> None:
    now = datetime(2026, 8, 30, 14, 10, tzinfo=UTC)
    monkeypatch.setattr(settings, "remnawave_stream_ip_hmac_secret", SecretStr("s" * 64))
    session = MagicMock()
    session.execute = AsyncMock(
        side_effect=[
            MagicMock(),
            _scalar_result(now - timedelta(minutes=1)),
            MagicMock(),
        ]
    )
    session.flush = AsyncMock()

    replaced = await RemnawaveStreamIngestionService(
        session,
        clock=lambda: now,
    ).reconcile_current_node_presence(
        node_id=7,
        observed_at=now,
        users=[
            ConnectionUser(
                user_id=41,
                ips=(ConnectionIp(ip="203.0.113.8", last_seen=now),),
            )
        ],
    )

    assert replaced is True
    statements = [str(call.args[0]) for call in session.execute.await_args_list]
    assert any(statement.startswith("DELETE FROM remnawave_node_user_presence") for statement in statements)
    assert not any("remnawave_node_connections_hourly" in statement for statement in statements)
    added_models = [call.args[0] for call in session.add.call_args_list]
    assert len(added_models) == 1
    assert added_models[0].__class__.__name__ == "RemnawaveNodePresenceModel"


@pytest.mark.asyncio
async def test_user_usage_uses_atomic_sum_of_per_message_deltas() -> None:
    session = MagicMock()
    session.execute = AsyncMock(side_effect=[_scalar_result(None), MagicMock(), MagicMock()])
    session.flush = AsyncMock()

    persisted = await RemnawaveStreamIngestionService(session).persist_user_usage(
        idempotency_key="remnawave:user_usage:1725024000000-0",
        payload_sha256="a" * 64,
        schema_version="1",
        node_id=7,
        observed_at=datetime(2026, 8, 30, 14, 15, tzinfo=UTC),
        records=[UsageRecord(user_id=41, total_bytes=25)],
    )

    assert persisted is True
    upsert = session.execute.await_args_list[1].args[0]
    compiled = upsert.compile(dialect=postgresql.dialect())
    sql = str(compiled)
    assert "ON CONFLICT ON CONSTRAINT uq_remnawave_user_usage_hour DO UPDATE" in sql
    assert "total_bytes = (remnawave_user_usage_hourly.total_bytes + excluded.total_bytes)" in sql
    assert compiled.params["total_bytes"] == 25
    checkpoint = session.execute.await_args_list[2].args[0].compile(dialect=postgresql.dialect())
    assert "ON CONFLICT ON CONSTRAINT uq_remnawave_stream_checkpoint DO UPDATE" in str(checkpoint)
    assert checkpoint.params["last_committed_message_id"] == "1725024000000-0"
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_user_usage_receipt_prevents_reapplying_same_delta() -> None:
    receipt = MagicMock(payload_sha256="b" * 64, processing_status="committed")
    session = MagicMock()
    session.execute = AsyncMock(return_value=_scalar_result(receipt))
    session.flush = AsyncMock()

    persisted = await RemnawaveStreamIngestionService(session).persist_user_usage(
        idempotency_key="remnawave:user_usage:1725024000000-1",
        payload_sha256="b" * 64,
        schema_version="1",
        node_id=7,
        observed_at=datetime(2026, 8, 30, 14, 30, tzinfo=UTC),
        records=[UsageRecord(user_id=41, total_bytes=25)],
    )

    assert persisted is False
    assert session.execute.await_count == 1
    session.flush.assert_not_awaited()


@pytest.mark.unit
def test_payload_fingerprint_is_keyed_and_not_raw_sha256(monkeypatch) -> None:
    payload = '{"request_ip":"203.0.113.44","user_agent":"Sensitive Client"}'
    raw_sha256 = hashlib.sha256(payload.encode()).hexdigest()
    monkeypatch.setattr(settings, "remnawave_stream_ip_hmac_secret", SecretStr("a" * 64))

    first = payload_fingerprint(payload)
    monkeypatch.setattr(settings, "remnawave_stream_ip_hmac_secret", SecretStr("b" * 64))
    second = payload_fingerprint(payload)

    assert first != raw_sha256
    assert second != raw_sha256
    assert first != second
    assert len(first) == 64


@pytest.mark.unit
async def test_dead_letter_upsert_is_idempotent_redacted_and_rekeyed(monkeypatch) -> None:
    monkeypatch.setattr(settings, "remnawave_stream_ip_hmac_secret", SecretStr("k" * 64))
    session = MagicMock()
    session.execute = AsyncMock(return_value=MagicMock())
    session.flush = AsyncMock()
    service = RemnawaveStreamIngestionService(session)
    source_fingerprint = "a" * 64

    for attempts in (3, 4):
        await service.upsert_dead_letter(
            stream_name="user_usage",
            message_id="1725024000000-9",
            schema_version="1",
            error_type="schema_validation",
            redacted_reason="invalid_record",
            source_fingerprint=source_fingerprint,
            attempts=attempts,
        )

    statements = [call.args[0] for call in session.execute.await_args_list]
    compiled = [statement.compile(dialect=postgresql.dialect()) for statement in statements]
    assert all("ON CONFLICT ON CONSTRAINT uq_remnawave_stream_dlq DO UPDATE" in str(item) for item in compiled)
    assert compiled[0].params["payload_sha256"] != source_fingerprint
    assert compiled[0].params["payload_sha256"] == compiled[1].params["payload_sha256"]
    assert compiled[0].params["attempts"] == 3
    assert compiled[1].params["attempts"] == 4
    persisted_fields = set(compiled[0].params)
    assert "raw_payload" not in persisted_fields
    assert "request_ip" not in persisted_fields
    assert "user_agent" not in persisted_fields
    assert session.flush.await_count == 2
