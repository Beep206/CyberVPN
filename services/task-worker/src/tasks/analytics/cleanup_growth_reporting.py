"""Scheduled cleanup for retained customer growth reporting artifacts."""

from __future__ import annotations

from time import perf_counter, time
from typing import Any

import structlog

from src.broker import broker
from src.config import get_settings
from src.metrics import (
    GROWTH_REPORTING_CLEANUP_CONSECUTIVE_FAILURES,
    GROWTH_REPORTING_CLEANUP_DURATION,
    GROWTH_REPORTING_CLEANUP_LAST_ATTEMPT_UNIXTIME,
    GROWTH_REPORTING_CLEANUP_LAST_DELETED,
    GROWTH_REPORTING_CLEANUP_LAST_SUCCESS_UNIXTIME,
    GROWTH_REPORTING_CLEANUP_RUNS_TOTAL,
)
from src.services.backend_api_client import BackendAPIClient

logger = structlog.get_logger(__name__)


def _record_cleanup_result(
    *,
    result: str,
    rollups_deleted: int,
    refresh_runs_deleted: int,
    deliveries_deleted: int,
    duration_seconds: float,
) -> None:
    now_unix = time()
    GROWTH_REPORTING_CLEANUP_LAST_ATTEMPT_UNIXTIME.set(now_unix)
    GROWTH_REPORTING_CLEANUP_LAST_DELETED.labels(artifact_kind="rollups").set(max(rollups_deleted, 0))
    GROWTH_REPORTING_CLEANUP_LAST_DELETED.labels(artifact_kind="refresh_runs").set(
        max(refresh_runs_deleted, 0)
    )
    GROWTH_REPORTING_CLEANUP_LAST_DELETED.labels(artifact_kind="deliveries").set(
        max(deliveries_deleted, 0)
    )
    GROWTH_REPORTING_CLEANUP_DURATION.observe(duration_seconds)
    GROWTH_REPORTING_CLEANUP_RUNS_TOTAL.labels(result=result).inc()
    if result == "failure":
        GROWTH_REPORTING_CLEANUP_CONSECUTIVE_FAILURES.inc()
    else:
        GROWTH_REPORTING_CLEANUP_CONSECUTIVE_FAILURES.set(0)
        GROWTH_REPORTING_CLEANUP_LAST_SUCCESS_UNIXTIME.set(now_unix)


@broker.task(task_name="cleanup_growth_reporting_artifacts", queue="cleanup")
async def cleanup_growth_reporting_artifacts() -> dict[str, Any]:
    """Trigger backend-owned cleanup of retained growth reporting artifacts."""
    settings = get_settings()
    if not settings.backend_api_url or settings.backend_internal_secret is None:
        logger.info("growth_reporting_cleanup_skipped", reason="backend_api_not_configured")
        _record_cleanup_result(
            result="skipped",
            rollups_deleted=0,
            refresh_runs_deleted=0,
            deliveries_deleted=0,
            duration_seconds=0,
        )
        return {"skipped": True, "reason": "backend_api_not_configured"}

    started = perf_counter()
    async with BackendAPIClient() as backend:
        if not backend.enabled:
            logger.info("growth_reporting_cleanup_skipped", reason="backend_api_disabled")
            _record_cleanup_result(
                result="skipped",
                rollups_deleted=0,
                refresh_runs_deleted=0,
                deliveries_deleted=0,
                duration_seconds=0,
            )
            return {"skipped": True, "reason": "backend_api_disabled"}

        try:
            response = await backend.cleanup_growth_reporting_artifacts()
        except Exception:
            _record_cleanup_result(
                result="failure",
                rollups_deleted=0,
                refresh_runs_deleted=0,
                deliveries_deleted=0,
                duration_seconds=perf_counter() - started,
            )
            raise

    result = {
        "rollups_deleted": int(response.get("rollups_deleted", 0) or 0),
        "refresh_runs_deleted": int(response.get("refresh_runs_deleted", 0) or 0),
        "deliveries_deleted": int(response.get("deliveries_deleted", 0) or 0),
        "executed_at": response.get("executed_at"),
    }
    _record_cleanup_result(
        result="success",
        rollups_deleted=result["rollups_deleted"],
        refresh_runs_deleted=result["refresh_runs_deleted"],
        deliveries_deleted=result["deliveries_deleted"],
        duration_seconds=perf_counter() - started,
    )
    logger.info("growth_reporting_cleanup_complete", **result)
    return result
