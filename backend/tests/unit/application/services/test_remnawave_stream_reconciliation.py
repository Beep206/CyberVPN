from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.application.services import remnawave_stream_reconciliation as reconciliation_module
from src.application.services.remnawave_stream_ingestion import ConnectionIp, ConnectionUser
from src.application.services.remnawave_stream_reconciliation import (
    AuthoritativeNodePresenceSnapshot,
    RemnawaveStreamGapReconciliationService,
)


def _scalar_result(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _gap(*, stream_name: str, status: str, now: datetime) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        stream_name=stream_name,
        loss_kind="exact_ids",
        missing_message_ids=["1725024000000-1"],
        missing_count=1,
        from_message_id="1725024000000-1",
        to_message_id="1725024000000-1",
        reconciliation_status=status,
        detected_at=now,
        redacted_detail=None,
        reconciled_at=None,
    )


@pytest.mark.unit
async def test_usage_reconciliation_commits_running_then_truthful_partial() -> None:
    now = datetime(2026, 8, 30, 14, 0, tzinfo=UTC)
    row = _gap(stream_name="user_usage", status="pending", now=now)
    session = MagicMock()
    session.execute = AsyncMock(side_effect=[_scalar_result(row), _scalar_result(row), _scalar_result(row)])
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    reader = SimpleNamespace(
        read_user_usage_inventory=AsyncMock(return_value=42),
        read_node_presence_snapshots=AsyncMock(),
    )

    result = await RemnawaveStreamGapReconciliationService(session, reader=reader).execute(row.id)

    assert result.reconciliation_status == "partial"
    assert row.redacted_detail == "authoritative_usage_inventory_partial"
    assert session.commit.await_count == 2
    reader.read_user_usage_inventory.assert_awaited_once()
    reader.read_node_presence_snapshots.assert_not_awaited()


@pytest.mark.unit
async def test_node_reconciliation_applies_current_presence_without_claiming_history(monkeypatch) -> None:
    now = datetime(2026, 8, 30, 14, 0, tzinfo=UTC)
    row = _gap(stream_name="node_connections", status="pending", now=now)
    session = MagicMock()
    session.execute = AsyncMock(side_effect=[_scalar_result(row), _scalar_result(row), _scalar_result(row)])
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    snapshot = AuthoritativeNodePresenceSnapshot(
        node_id=7,
        observed_at=now,
        users=(
            ConnectionUser(
                user_id=11,
                ips=(ConnectionIp(ip="203.0.113.1", last_seen=now),),
            ),
        ),
    )
    reader = SimpleNamespace(
        read_user_usage_inventory=AsyncMock(),
        read_node_presence_snapshots=AsyncMock(return_value=(snapshot,)),
    )
    reconcile_presence = AsyncMock(return_value=True)
    monkeypatch.setattr(
        reconciliation_module,
        "RemnawaveStreamIngestionService",
        lambda _session: SimpleNamespace(reconcile_current_node_presence=reconcile_presence),
    )

    result = await RemnawaveStreamGapReconciliationService(session, reader=reader).execute(row.id)

    assert result.reconciliation_status == "partial"
    reconcile_presence.assert_awaited_once_with(
        node_id=7,
        observed_at=now,
        users=snapshot.users,
    )
    assert session.commit.await_count == 2


@pytest.mark.unit
async def test_terminal_partial_reconciliation_is_idempotent_without_new_rest_read() -> None:
    now = datetime(2026, 8, 30, 14, 0, tzinfo=UTC)
    row = _gap(stream_name="subscription_requests", status="partial", now=now)
    session = MagicMock()
    session.execute = AsyncMock(return_value=_scalar_result(row))
    session.commit = AsyncMock()
    reader = SimpleNamespace(
        read_user_usage_inventory=AsyncMock(),
        read_node_presence_snapshots=AsyncMock(),
    )

    result = await RemnawaveStreamGapReconciliationService(session, reader=reader).execute(row.id)

    assert result.reconciliation_status == "partial"
    session.commit.assert_not_awaited()
    reader.read_user_usage_inventory.assert_not_awaited()
    reader.read_node_presence_snapshots.assert_not_awaited()
