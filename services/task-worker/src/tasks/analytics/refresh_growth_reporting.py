"""Scheduled refresh for persisted customer growth reporting rollups."""

from __future__ import annotations

from datetime import UTC, datetime
from time import perf_counter, time
from typing import Any

import structlog

from src.broker import broker
from src.config import get_settings
from src.metrics import (
    GROWTH_REPORTING_REFRESH_CONSECUTIVE_FAILURES,
    GROWTH_REPORTING_REFRESH_DURATION,
    GROWTH_REPORTING_REFRESH_LAST_ATTEMPT_UNIXTIME,
    GROWTH_REPORTING_REFRESH_LAST_ROWS_WRITTEN,
    GROWTH_REPORTING_REFRESH_LAST_SUCCESS_UNIXTIME,
    GROWTH_REPORTING_REFRESH_RUNS_TOTAL,
)
from src.services.backend_api_client import BackendAPIClient

logger = structlog.get_logger(__name__)

DEFAULT_GROWTH_REPORTING_WINDOW_DAYS = 30


def _record_success(*, rows_written: int, duration_seconds: float) -> None:
    now_unix = time()
    GROWTH_REPORTING_REFRESH_LAST_ATTEMPT_UNIXTIME.set(now_unix)
    GROWTH_REPORTING_REFRESH_LAST_SUCCESS_UNIXTIME.set(now_unix)
    GROWTH_REPORTING_REFRESH_CONSECUTIVE_FAILURES.set(0)
    GROWTH_REPORTING_REFRESH_LAST_ROWS_WRITTEN.set(max(rows_written, 0))
    GROWTH_REPORTING_REFRESH_DURATION.observe(duration_seconds)
    GROWTH_REPORTING_REFRESH_RUNS_TOTAL.labels(result="success").inc()


def _record_failure(*, duration_seconds: float) -> None:
    GROWTH_REPORTING_REFRESH_LAST_ATTEMPT_UNIXTIME.set(time())
    GROWTH_REPORTING_REFRESH_CONSECUTIVE_FAILURES.inc()
    GROWTH_REPORTING_REFRESH_DURATION.observe(duration_seconds)
    GROWTH_REPORTING_REFRESH_RUNS_TOTAL.labels(result="failure").inc()


@broker.task(task_name="refresh_growth_reporting_rollups", queue="analytics")
async def refresh_growth_reporting_rollups() -> dict[str, Any]:
    """Trigger backend-owned growth reporting refresh through the internal service API."""
    settings = get_settings()
    if not settings.backend_api_url or settings.backend_internal_secret is None:
        logger.info("growth_reporting_refresh_skipped", reason="backend_api_not_configured")
        return {"skipped": True, "reason": "backend_api_not_configured"}

    started = perf_counter()
    try:
        async with BackendAPIClient() as backend:
            if not backend.enabled:
                logger.info("growth_reporting_refresh_skipped", reason="backend_api_disabled")
                return {"skipped": True, "reason": "backend_api_disabled"}

            response = await backend.refresh_growth_reporting(
                {"window_days": DEFAULT_GROWTH_REPORTING_WINDOW_DAYS},
            )
    except Exception:
        _record_failure(duration_seconds=perf_counter() - started)
        raise

    rows_written = int(response.get("rows_written", 0) or 0)
    _record_success(rows_written=rows_written, duration_seconds=perf_counter() - started)

    result = {
        "window_start": response.get("window_start"),
        "window_end": response.get("window_end"),
        "latest_rollup_date": response.get("latest_rollup_date"),
        "refreshed_at": response.get("refreshed_at") or datetime.now(UTC).isoformat(),
        "rows_written": rows_written,
        "families_updated": list(response.get("families_updated") or []),
        "trigger_kind": response.get("trigger_kind") or "worker",
    }
    logger.info("growth_reporting_refresh_complete", **result)
    return result
