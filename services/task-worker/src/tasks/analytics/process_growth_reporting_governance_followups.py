"""Scheduled governance follow-up automation for customer growth reporting."""

from __future__ import annotations

from time import perf_counter, time
from typing import Any

import structlog

from src.broker import broker
from src.config import get_settings
from src.metrics import (
    GROWTH_REPORTING_GOVERNANCE_FOLLOWUP_CONSECUTIVE_FAILURES,
    GROWTH_REPORTING_GOVERNANCE_FOLLOWUP_DURATION,
    GROWTH_REPORTING_GOVERNANCE_FOLLOWUP_LAST_ATTEMPT_UNIXTIME,
    GROWTH_REPORTING_GOVERNANCE_FOLLOWUP_LAST_OPEN,
    GROWTH_REPORTING_GOVERNANCE_FOLLOWUP_LAST_OVERDUE,
    GROWTH_REPORTING_GOVERNANCE_FOLLOWUP_LAST_SCANNED,
    GROWTH_REPORTING_GOVERNANCE_FOLLOWUP_LAST_SUCCESS_UNIXTIME,
    GROWTH_REPORTING_GOVERNANCE_FOLLOWUP_RUNS_TOTAL,
)
from src.services.backend_api_client import BackendAPIClient

logger = structlog.get_logger(__name__)


def _record_followup_result(
    *,
    result: str,
    scanned_count: int,
    open_count: int,
    overdue_count: int,
    duration_seconds: float,
) -> None:
    now_unix = time()
    GROWTH_REPORTING_GOVERNANCE_FOLLOWUP_LAST_ATTEMPT_UNIXTIME.set(now_unix)
    GROWTH_REPORTING_GOVERNANCE_FOLLOWUP_LAST_SCANNED.set(max(scanned_count, 0))
    GROWTH_REPORTING_GOVERNANCE_FOLLOWUP_LAST_OPEN.set(max(open_count, 0))
    GROWTH_REPORTING_GOVERNANCE_FOLLOWUP_LAST_OVERDUE.set(max(overdue_count, 0))
    GROWTH_REPORTING_GOVERNANCE_FOLLOWUP_DURATION.observe(duration_seconds)
    GROWTH_REPORTING_GOVERNANCE_FOLLOWUP_RUNS_TOTAL.labels(result=result).inc()
    if result == "failure":
        GROWTH_REPORTING_GOVERNANCE_FOLLOWUP_CONSECUTIVE_FAILURES.inc()
    else:
        GROWTH_REPORTING_GOVERNANCE_FOLLOWUP_CONSECUTIVE_FAILURES.set(0)
        GROWTH_REPORTING_GOVERNANCE_FOLLOWUP_LAST_SUCCESS_UNIXTIME.set(now_unix)


@broker.task(task_name="process_growth_reporting_governance_followups", queue="analytics")
async def process_growth_reporting_governance_followups() -> dict[str, Any]:
    """Trigger backend-owned governance follow-up automation through the internal service API."""
    settings = get_settings()
    if not settings.backend_api_url or settings.backend_internal_secret is None:
        logger.info("growth_reporting_governance_followups_skipped", reason="backend_api_not_configured")
        _record_followup_result(
            result="skipped",
            scanned_count=0,
            open_count=0,
            overdue_count=0,
            duration_seconds=0,
        )
        return {"skipped": True, "reason": "backend_api_not_configured"}

    started = perf_counter()
    async with BackendAPIClient() as backend:
        if not backend.enabled:
            logger.info("growth_reporting_governance_followups_skipped", reason="backend_api_disabled")
            _record_followup_result(
                result="skipped",
                scanned_count=0,
                open_count=0,
                overdue_count=0,
                duration_seconds=0,
            )
            return {"skipped": True, "reason": "backend_api_disabled"}

        try:
            response = await backend.process_growth_reporting_governance_followups()
        except Exception:
            _record_followup_result(
                result="failure",
                scanned_count=0,
                open_count=0,
                overdue_count=0,
                duration_seconds=perf_counter() - started,
            )
            raise

    result = {
        "processed_at": response.get("processed_at"),
        "scanned_count": int(response.get("scanned_count", 0) or 0),
        "opened_count": int(response.get("opened_count", 0) or 0),
        "reopened_count": int(response.get("reopened_count", 0) or 0),
        "auto_resolved_count": int(response.get("auto_resolved_count", 0) or 0),
        "reminded_count": int(response.get("reminded_count", 0) or 0),
        "open_count": int(response.get("open_count", 0) or 0),
        "overdue_count": int(response.get("overdue_count", 0) or 0),
    }
    _record_followup_result(
        result="success",
        scanned_count=result["scanned_count"],
        open_count=result["open_count"],
        overdue_count=result["overdue_count"],
        duration_seconds=perf_counter() - started,
    )
    logger.info("growth_reporting_governance_followups_complete", **result)
    return result
