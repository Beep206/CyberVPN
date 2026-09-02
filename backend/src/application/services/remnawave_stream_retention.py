"""Bounded PostgreSQL retention for Remnawave stream and terminal receipt metadata."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast

from sqlalchemy import Table, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.remnawave_upgrade_model import (
    RemnawaveConnectionDropReceiptModel,
    RemnawaveNodeConnectionsHourlyModel,
    RemnawaveNodePresenceModel,
    RemnawaveStreamDeadLetterModel,
    RemnawaveStreamGapModel,
    RemnawaveStreamReceiptModel,
    RemnawaveSubscriptionRequestEventModel,
    RemnawaveUserUsageHourlyModel,
)

_RETENTION_TABLES: tuple[Table, ...] = (
    cast(Table, RemnawaveConnectionDropReceiptModel.__table__),
    cast(Table, RemnawaveStreamReceiptModel.__table__),
    cast(Table, RemnawaveStreamDeadLetterModel.__table__),
    cast(Table, RemnawaveUserUsageHourlyModel.__table__),
    cast(Table, RemnawaveSubscriptionRequestEventModel.__table__),
    cast(Table, RemnawaveNodePresenceModel.__table__),
    cast(Table, RemnawaveNodeConnectionsHourlyModel.__table__),
    cast(Table, RemnawaveStreamGapModel.__table__),
)


@dataclass(frozen=True, slots=True)
class RemnawaveRetentionPurgeResult:
    deleted_by_table: dict[str, int]
    total_deleted: int
    has_more: bool
    purged_at: datetime


class RemnawaveStreamRetentionService:
    """Delete one globally bounded batch using a fair per-table quota."""

    MAX_BATCH_LIMIT = 5_000

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def purge_expired(
        self,
        *,
        batch_limit: int,
        cutoff: datetime | None = None,
    ) -> RemnawaveRetentionPurgeResult:
        if isinstance(batch_limit, bool) or not 1 <= batch_limit <= self.MAX_BATCH_LIMIT:
            raise ValueError(f"batch_limit must be between 1 and {self.MAX_BATCH_LIMIT}")
        purged_at = cutoff or datetime.now(UTC)
        if purged_at.tzinfo is None:
            raise ValueError("retention cutoff must include timezone")
        purged_at = purged_at.astimezone(UTC)

        table_count = len(_RETENTION_TABLES)
        base_quota, extra_slots = divmod(batch_limit, table_count)
        quotas = [base_quota + int(index < extra_slots) for index in range(table_count)]
        deleted_by_table = {table.name: 0 for table in _RETENTION_TABLES}
        for table, quota in zip(_RETENTION_TABLES, quotas, strict=True):
            if quota == 0:
                continue
            expired_ids = (
                select(table.c.id)
                .where(table.c.expires_at <= purged_at)
                .order_by(table.c.expires_at, table.c.id)
                .limit(quota)
            )
            result = await self._session.execute(delete(table).where(table.c.id.in_(expired_ids)).returning(table.c.id))
            deleted = len(result.scalars().all())
            deleted_by_table[table.name] = deleted

        has_more = False
        for table in _RETENTION_TABLES:
            remaining_result = await self._session.execute(
                select(table.c.id)
                .where(table.c.expires_at <= purged_at)
                .order_by(table.c.expires_at, table.c.id)
                .limit(1)
            )
            if remaining_result.scalar_one_or_none() is not None:
                has_more = True
                break

        await self._session.flush()
        total_deleted = sum(deleted_by_table.values())
        return RemnawaveRetentionPurgeResult(
            deleted_by_table=deleted_by_table,
            total_deleted=total_deleted,
            has_more=has_more,
            purged_at=purged_at,
        )
