from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from pydantic import SecretStr

from src.application.services.remnawave_stream_checkpoints import RemnawaveStreamCheckpointService
from src.application.services.remnawave_stream_ingestion import payload_fingerprint
from src.config.settings import settings


def _scalar_result(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _checkpoint(*, stream_name: str, now: datetime) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        stream_name=stream_name,
        last_committed_message_id="1725024000000-5",
        last_committed_ms=1725024000000,
        last_committed_sequence=5,
        observed_identity_hmac=payload_fingerprint("cybervpn/remnawave-stream-epoch/v1\0old-run"),
        observed_first_message_id="1725023999000-0",
        observed_last_message_id="1725024000000-5",
        observed_group_last_delivered_id="1725024000000-5",
        observed_group_pending_count=0,
        observed_group_pending_min_id=None,
        observed_group_pending_max_id=None,
        observed_group_lag=None,
        stream_exists=True,
        group_exists=True,
        observed_at=now,
        updated_at=now,
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    "stream_name,expected_status",
    [
        ("user_usage", "pending"),
        ("node_connections", "pending"),
        ("subscription_requests", "partial"),
    ],
)
async def test_full_flush_creates_durable_unknown_loss_gap(
    monkeypatch,
    stream_name: str,
    expected_status: str,
) -> None:
    now = datetime(2026, 8, 30, 14, 0, tzinfo=UTC)
    monkeypatch.setattr(settings, "remnawave_stream_ip_hmac_secret", SecretStr("q" * 64))
    row = _checkpoint(stream_name=stream_name, now=now)
    session = MagicMock()
    session.execute = AsyncMock(side_effect=[_scalar_result(row), _scalar_result(None), _scalar_result(uuid4())])
    session.flush = AsyncMock()

    result = await RemnawaveStreamCheckpointService(session, clock=lambda: now).observe_startup(
        stream_name=stream_name,
        observed_stream_identity="new-run",
        stream_exists=False,
        group_exists=False,
        first_message_id=None,
        last_message_id=None,
        group_last_delivered_id=None,
        group_pending_count=0,
        group_pending_min_id=None,
        group_pending_max_id=None,
        observed_at=now,
    )

    assert result.loss_detected is True
    assert result.loss_reason == "stream_missing"
    assert result.gap is not None
    assert result.gap.loss_kind == "unknown_range"
    assert result.gap.missing_count == 0
    assert result.gap.from_message_id == "1725024000000-5"
    assert result.gap.reconciliation_status == expected_status
    assert row.stream_exists is False
    assert row.group_exists is False
    session.flush.assert_awaited()


@pytest.mark.unit
async def test_restart_with_persisted_nonregressed_stream_does_not_report_loss(monkeypatch) -> None:
    now = datetime(2026, 8, 30, 14, 0, tzinfo=UTC)
    monkeypatch.setattr(settings, "remnawave_stream_ip_hmac_secret", SecretStr("q" * 64))
    row = _checkpoint(stream_name="user_usage", now=now)
    session = MagicMock()
    session.execute = AsyncMock(side_effect=[_scalar_result(row), _scalar_result(None)])
    session.flush = AsyncMock()

    result = await RemnawaveStreamCheckpointService(session, clock=lambda: now).observe_startup(
        stream_name="user_usage",
        observed_stream_identity="new-run",
        stream_exists=True,
        group_exists=True,
        first_message_id="1725023999000-0",
        last_message_id="1725024000001-0",
        group_last_delivered_id="1725024000000-5",
        group_pending_count=0,
        group_pending_min_id=None,
        group_pending_max_id=None,
        observed_at=now,
        group_lag=7,
    )

    assert result.loss_detected is False
    assert result.gap is None
    assert row.observed_group_lag == 7
    assert session.execute.await_count == 2


@pytest.mark.unit
async def test_recreated_group_is_detected_even_when_stream_still_exists(monkeypatch) -> None:
    now = datetime(2026, 8, 30, 14, 0, tzinfo=UTC)
    monkeypatch.setattr(settings, "remnawave_stream_ip_hmac_secret", SecretStr("q" * 64))
    row = _checkpoint(stream_name="node_connections", now=now)
    session = MagicMock()
    session.execute = AsyncMock(side_effect=[_scalar_result(row), _scalar_result(None), _scalar_result(uuid4())])
    session.flush = AsyncMock()

    result = await RemnawaveStreamCheckpointService(session, clock=lambda: now).observe_startup(
        stream_name="node_connections",
        observed_stream_identity="same-run",
        stream_exists=True,
        group_exists=False,
        first_message_id="1725023999000-0",
        last_message_id="1725024000001-0",
        group_last_delivered_id=None,
        group_pending_count=0,
        group_pending_min_id=None,
        group_pending_max_id=None,
        observed_at=now,
    )

    assert result.loss_detected is True
    assert result.loss_reason == "group_missing"
    assert result.gap is not None


@pytest.mark.unit
async def test_group_skipped_range_without_pel_is_detected(monkeypatch) -> None:
    now = datetime(2026, 8, 30, 14, 0, tzinfo=UTC)
    monkeypatch.setattr(settings, "remnawave_stream_ip_hmac_secret", SecretStr("q" * 64))
    row = _checkpoint(stream_name="user_usage", now=now)
    session = MagicMock()
    session.execute = AsyncMock(side_effect=[_scalar_result(row), _scalar_result(None), _scalar_result(uuid4())])
    session.flush = AsyncMock()

    result = await RemnawaveStreamCheckpointService(session, clock=lambda: now).observe_startup(
        stream_name="user_usage",
        observed_stream_identity="same-run",
        stream_exists=True,
        group_exists=True,
        first_message_id="1725023999000-0",
        last_message_id="1725024000002-0",
        group_last_delivered_id="1725024000002-0",
        group_pending_count=0,
        group_pending_min_id=None,
        group_pending_max_id=None,
        observed_at=now,
    )

    assert result.loss_detected is True
    assert result.loss_reason == "group_skipped_range"
    assert result.gap is not None


@pytest.mark.unit
async def test_group_skipped_range_before_newer_pel_is_detected(monkeypatch) -> None:
    now = datetime(2026, 8, 30, 14, 0, tzinfo=UTC)
    monkeypatch.setattr(settings, "remnawave_stream_ip_hmac_secret", SecretStr("q" * 64))
    row = _checkpoint(stream_name="node_connections", now=now)
    session = MagicMock()
    session.execute = AsyncMock(side_effect=[_scalar_result(row), _scalar_result(None), _scalar_result(uuid4())])
    session.flush = AsyncMock()

    result = await RemnawaveStreamCheckpointService(session, clock=lambda: now).observe_startup(
        stream_name="node_connections",
        observed_stream_identity="same-run",
        stream_exists=True,
        group_exists=True,
        first_message_id="1725023999000-0",
        last_message_id="1725024000003-0",
        group_last_delivered_id="1725024000003-0",
        group_pending_count=1,
        group_pending_min_id="1725024000003-0",
        group_pending_max_id="1725024000003-0",
        observed_at=now,
    )

    assert result.loss_detected is True
    assert result.loss_reason == "group_skipped_range"
    assert result.gap is not None


@pytest.mark.unit
async def test_pending_gap_latches_loss_across_repeated_observations(monkeypatch) -> None:
    now = datetime(2026, 8, 30, 14, 0, tzinfo=UTC)
    monkeypatch.setattr(settings, "remnawave_stream_ip_hmac_secret", SecretStr("q" * 64))
    row = _checkpoint(stream_name="user_usage", now=now)
    active_gap = SimpleNamespace(
        id=uuid4(),
        stream_name="user_usage",
        loss_kind="unknown_range",
        missing_message_ids=[],
        missing_count=0,
        from_message_id="1725024000000-5",
        to_message_id=None,
        reconciliation_status="pending",
        detected_at=now,
    )
    session = MagicMock()
    session.execute = AsyncMock(
        side_effect=[
            _scalar_result(row),
            _scalar_result(None),
            _scalar_result(uuid4()),
            _scalar_result(row),
            _scalar_result(active_gap),
        ]
    )
    session.flush = AsyncMock()
    service = RemnawaveStreamCheckpointService(session, clock=lambda: now)

    first = await service.observe_startup(
        stream_name="user_usage",
        observed_stream_identity="new-run",
        stream_exists=False,
        group_exists=False,
        first_message_id=None,
        last_message_id=None,
        group_last_delivered_id=None,
        group_pending_count=0,
        group_pending_min_id=None,
        group_pending_max_id=None,
        observed_at=now,
    )
    second = await service.observe_startup(
        stream_name="user_usage",
        observed_stream_identity="new-run",
        stream_exists=True,
        group_exists=True,
        first_message_id="1725024000001-0",
        last_message_id="1725024000002-0",
        group_last_delivered_id="1725024000000-5",
        group_pending_count=0,
        group_pending_min_id=None,
        group_pending_max_id=None,
        observed_at=now,
    )

    assert first.loss_reason == "stream_missing"
    assert second.loss_detected is True
    assert second.loss_reason == "gap_pending_reconciliation"
    assert second.gap is not None
    assert second.gap.gap_id == active_gap.id
    assert session.execute.await_count == 5
