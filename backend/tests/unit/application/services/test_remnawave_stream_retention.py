from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.application.services.remnawave_stream_retention import RemnawaveStreamRetentionService


def _returning_rows(*ids):
    result = MagicMock()
    result.scalars.return_value.all.return_value = list(ids)
    return result


def _single_row(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


@pytest.mark.unit
async def test_retention_purge_enforces_global_batch_and_fairly_reaches_later_tables() -> None:
    session = MagicMock()
    session.execute = AsyncMock(
        side_effect=[
            *[_returning_rows(uuid4()) for _table in range(8)],
            _single_row(uuid4()),
        ]
    )
    session.flush = AsyncMock()
    cutoff = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)

    result = await RemnawaveStreamRetentionService(session).purge_expired(
        batch_limit=8,
        cutoff=cutoff,
    )

    assert result.total_deleted == 8
    assert result.deleted_by_table["remnawave_connection_drop_receipts"] == 1
    assert result.deleted_by_table["remnawave_stream_receipts"] == 1
    assert result.deleted_by_table["remnawave_stream_dead_letters"] == 1
    assert result.deleted_by_table["remnawave_stream_gaps"] == 1
    assert sum(result.deleted_by_table.values()) == 8
    assert result.has_more is True
    assert result.purged_at == cutoff
    assert session.execute.await_count == 9
    first_delete = str(session.execute.await_args_list[0].args[0])
    second_delete = str(session.execute.await_args_list[1].args[0])
    assert (
        "ORDER BY remnawave_connection_drop_receipts.expires_at, remnawave_connection_drop_receipts.id" in first_delete
    )
    assert "ORDER BY remnawave_stream_receipts.expires_at, remnawave_stream_receipts.id" in second_delete
    session.flush.assert_awaited_once()


@pytest.mark.unit
async def test_retention_purge_is_idempotent_when_no_expired_rows_remain() -> None:
    session = MagicMock()
    # Eight DELETE...RETURNING queries followed by eight bounded existence probes,
    # repeated for the second call.
    side_effect = []
    for _call in range(2):
        side_effect.extend(_returning_rows() for _table in range(8))
        side_effect.extend(_single_row(None) for _table in range(8))
    session.execute = AsyncMock(side_effect=side_effect)
    session.flush = AsyncMock()
    service = RemnawaveStreamRetentionService(session)
    cutoff = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)

    first = await service.purge_expired(batch_limit=1000, cutoff=cutoff)
    second = await service.purge_expired(batch_limit=1000, cutoff=cutoff)

    assert first.total_deleted == second.total_deleted == 0
    assert first.has_more is second.has_more is False
    assert all(count == 0 for count in first.deleted_by_table.values())
    assert session.execute.await_count == 32
    assert session.flush.await_count == 2


@pytest.mark.unit
async def test_retention_purge_rejects_unbounded_limit() -> None:
    session = MagicMock()

    with pytest.raises(ValueError, match="batch_limit"):
        await RemnawaveStreamRetentionService(session).purge_expired(batch_limit=5001)

    session.execute.assert_not_called()
