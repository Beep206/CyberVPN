"""Bounded scheduled enforcement of backend-owned Remnawave telemetry TTLs."""

from __future__ import annotations

import structlog

from src.broker import broker
from src.config import get_settings
from src.metrics import REMNAWAVE_STREAM_RETENTION_BACKLOG, REMNAWAVE_STREAM_RETENTION_PURGED_TOTAL
from src.services.backend_api_client import BackendAPIClient, BackendAPIError

logger = structlog.get_logger(__name__)


@broker.task(
    task_name="purge_remnawave_stream_retention",
    queue="cleanup",
    retry_policy="cleanup",
)
async def purge_remnawave_stream_retention() -> dict[str, object]:
    """Drain a bounded number of PostgreSQL TTL batches without raw payloads."""

    settings = get_settings()
    if not settings.remnawave_stream_retention_enabled:
        return {"enabled": False, "total_deleted": 0, "batches": 0, "has_more": False}

    deleted_by_table: dict[str, int] = {}
    total_deleted = 0
    batches = 0
    has_more = False
    last_purged_at: str | None = None

    async with BackendAPIClient() as backend:
        for _ in range(settings.remnawave_stream_retention_max_batches):
            receipt = await backend.purge_remnawave_stream_retention(
                batch_limit=settings.remnawave_stream_retention_batch_limit
            )
            batches += 1
            total_deleted += receipt.total_deleted
            for table, count in receipt.deleted_by_table.items():
                deleted_by_table[table] = deleted_by_table.get(table, 0) + count
            last_purged_at = receipt.purged_at.isoformat()
            has_more = receipt.has_more
            if has_more and receipt.total_deleted == 0:
                REMNAWAVE_STREAM_RETENTION_BACKLOG.set(1)
                raise BackendAPIError("Remnawave retention reported a non-progressing backlog")
            if not has_more:
                break

    REMNAWAVE_STREAM_RETENTION_PURGED_TOTAL.labels(stream="all", store="postgres").inc(total_deleted)
    REMNAWAVE_STREAM_RETENTION_BACKLOG.set(1 if has_more else 0)
    log_method = logger.warning if has_more else logger.info
    log_method(
        "remnawave_stream_retention_completed",
        total_deleted=total_deleted,
        batches=batches,
        has_more=has_more,
    )
    return {
        "enabled": True,
        "total_deleted": total_deleted,
        "deleted_by_table": deleted_by_table,
        "batches": batches,
        "has_more": has_more,
        "purged_at": last_purged_at,
    }
