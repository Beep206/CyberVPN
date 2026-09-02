from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from pydantic import SecretStr
from sqlalchemy.dialects import postgresql

from src.application.services.remnawave_stream_gaps import (
    RemnawaveStreamGapError,
    RemnawaveStreamGapService,
    RemnawaveStreamGapTransitionError,
)
from src.config.settings import settings


def _scalar_result(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


@pytest.mark.unit
async def test_gap_registration_is_bounded_exact_sorted_and_redacted(monkeypatch) -> None:
    now = datetime(2026, 8, 30, 14, 0, tzinfo=UTC)
    monkeypatch.setattr(settings, "remnawave_stream_ip_hmac_secret", SecretStr("g" * 64))
    session = MagicMock()
    session.execute = AsyncMock(return_value=_scalar_result(uuid4()))
    session.flush = AsyncMock()

    result = await RemnawaveStreamGapService(session, clock=lambda: now).register(
        stream_name="node_connections",
        missing_message_ids=["1725024000001-0", "1725024000000-2"],
        detected_at=now,
    )

    statement = session.execute.await_args.args[0]
    compiled = statement.compile(dialect=postgresql.dialect())
    assert "ON CONFLICT ON CONSTRAINT uq_remnawave_stream_gap_fingerprint DO NOTHING" in str(compiled)
    assert compiled.params["missing_message_ids"] == ["1725024000000-2", "1725024000001-0"]
    assert compiled.params["missing_count"] == 2
    assert compiled.params["from_message_id"] == "1725024000000-2"
    assert compiled.params["to_message_id"] == "1725024000001-0"
    assert compiled.params["reconciliation_status"] == "pending"
    assert compiled.params["expires_at"] is None
    assert "raw_payload" not in compiled.params
    assert result.missing_message_ids == ("1725024000000-2", "1725024000001-0")


@pytest.mark.unit
async def test_gap_duplicate_registration_reuses_existing_row_without_extending_ttl(monkeypatch) -> None:
    now = datetime(2026, 8, 30, 14, 0, tzinfo=UTC)
    existing_id = uuid4()
    existing = SimpleNamespace(
        id=existing_id,
        stream_name="user_usage",
        loss_kind="exact_ids",
        missing_message_ids=["1725024000000-1"],
        missing_count=1,
        from_message_id="1725024000000-1",
        to_message_id="1725024000000-1",
        reconciliation_status="pending",
        detected_at=now,
    )
    conflict = _scalar_result(None)
    selected = MagicMock()
    selected.scalar_one.return_value = existing
    monkeypatch.setattr(settings, "remnawave_stream_ip_hmac_secret", SecretStr("g" * 64))
    session = MagicMock()
    session.execute = AsyncMock(side_effect=[conflict, selected])
    session.flush = AsyncMock()

    result = await RemnawaveStreamGapService(session, clock=lambda: now + timedelta(days=1)).register(
        stream_name="user_usage",
        missing_message_ids=["1725024000000-1"],
        detected_at=now,
    )

    assert result.gap_id == existing_id
    assert result.reused is True
    assert session.execute.await_count == 2


@pytest.mark.unit
async def test_subscription_gap_is_immediately_partial_and_never_fabricated(monkeypatch) -> None:
    now = datetime(2026, 8, 30, 14, 0, tzinfo=UTC)
    monkeypatch.setattr(settings, "remnawave_stream_ip_hmac_secret", SecretStr("g" * 64))
    session = MagicMock()
    session.execute = AsyncMock(return_value=_scalar_result(uuid4()))
    session.flush = AsyncMock()

    result = await RemnawaveStreamGapService(session, clock=lambda: now).register(
        stream_name="subscription_requests",
        missing_message_ids=["1725024000000-1"],
        detected_at=now,
    )

    compiled = session.execute.await_args.args[0].compile(dialect=postgresql.dialect())
    assert result.reconciliation_status == "partial"
    assert compiled.params["redacted_detail"] == "metadata_not_reconstructable"
    assert compiled.params["expires_at"] == now + timedelta(days=settings.remnawave_stream_receipt_retention_days)


@pytest.mark.unit
async def test_gap_rejects_far_future_detection_before_database_access(monkeypatch) -> None:
    now = datetime(2026, 8, 30, 14, 0, tzinfo=UTC)
    monkeypatch.setattr(settings, "remnawave_stream_ip_hmac_secret", SecretStr("g" * 64))
    session = MagicMock()
    session.execute = AsyncMock()

    with pytest.raises(RemnawaveStreamGapError, match="clock skew"):
        await RemnawaveStreamGapService(session, clock=lambda: now).register(
            stream_name="user_usage",
            missing_message_ids=["1725024000000-1"],
            detected_at=now + timedelta(minutes=5, microseconds=1),
        )

    session.execute.assert_not_awaited()


@pytest.mark.unit
async def test_usage_gap_cannot_complete_without_authoritative_read() -> None:
    now = datetime(2026, 8, 30, 14, 0, tzinfo=UTC)
    row = SimpleNamespace(
        id=uuid4(),
        stream_name="user_usage",
        loss_kind="exact_ids",
        missing_message_ids=["1725024000000-1"],
        missing_count=1,
        from_message_id="1725024000000-1",
        to_message_id="1725024000000-1",
        reconciliation_status="running",
        detected_at=now,
        redacted_detail=None,
        reconciled_at=None,
    )
    selected = MagicMock()
    selected.scalar_one_or_none.return_value = row
    session = MagicMock()
    session.execute = AsyncMock(return_value=selected)
    session.flush = AsyncMock()

    with pytest.raises(RemnawaveStreamGapTransitionError, match="authoritative Remnawave read"):
        await RemnawaveStreamGapService(session, clock=lambda: now).transition(
            gap_id=row.id,
            reconciliation_status="reconciled",
            redacted_detail="rest_snapshot_applied",
            authoritative_read_completed=False,
        )

    assert row.reconciliation_status == "running"
    session.flush.assert_not_awaited()


@pytest.mark.unit
async def test_usage_gap_completes_after_authoritative_read() -> None:
    now = datetime(2026, 8, 30, 14, 0, tzinfo=UTC)
    row = SimpleNamespace(
        id=uuid4(),
        stream_name="user_usage",
        loss_kind="exact_ids",
        missing_message_ids=["1725024000000-1"],
        missing_count=1,
        from_message_id="1725024000000-1",
        to_message_id="1725024000000-1",
        reconciliation_status="running",
        detected_at=now,
        redacted_detail=None,
        reconciled_at=None,
    )
    selected = MagicMock()
    selected.scalar_one_or_none.return_value = row
    session = MagicMock()
    session.execute = AsyncMock(return_value=selected)
    session.flush = AsyncMock()

    result = await RemnawaveStreamGapService(session, clock=lambda: now).transition(
        gap_id=row.id,
        reconciliation_status="reconciled",
        redacted_detail="rest_snapshot_applied",
        authoritative_read_completed=True,
    )

    assert result.reconciliation_status == "reconciled"
    assert row.reconciled_at == now
    assert row.expires_at == now + timedelta(days=settings.remnawave_stream_receipt_retention_days)
    session.flush.assert_awaited_once()


@pytest.mark.unit
async def test_terminal_gap_retry_does_not_extend_retention() -> None:
    now = datetime(2026, 8, 30, 14, 0, tzinfo=UTC)
    original_reconciled_at = now - timedelta(hours=1)
    original_expires_at = now + timedelta(days=13)
    row = SimpleNamespace(
        id=uuid4(),
        stream_name="node_connections",
        loss_kind="exact_ids",
        missing_message_ids=["1725024000000-1"],
        missing_count=1,
        from_message_id="1725024000000-1",
        to_message_id="1725024000000-1",
        reconciliation_status="partial",
        detected_at=now - timedelta(hours=2),
        redacted_detail="authoritative_presence_snapshot_partial",
        reconciled_at=original_reconciled_at,
        expires_at=original_expires_at,
    )
    selected = MagicMock()
    selected.scalar_one_or_none.return_value = row
    session = MagicMock()
    session.execute = AsyncMock(return_value=selected)
    session.flush = AsyncMock()

    result = await RemnawaveStreamGapService(session, clock=lambda: now).transition(
        gap_id=row.id,
        reconciliation_status="partial",
        redacted_detail="authoritative_presence_snapshot_partial",
        authoritative_read_completed=True,
    )

    assert result.reused is True
    assert row.reconciled_at == original_reconciled_at
    assert row.expires_at == original_expires_at
