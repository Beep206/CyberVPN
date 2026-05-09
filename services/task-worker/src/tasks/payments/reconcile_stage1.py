"""Stage 1 payment mismatch reconciliation task."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import structlog

from src.broker import broker
from src.config import get_settings
from src.metrics import (
    STAGE1_PAYMENT_RECONCILIATION_ITEMS_CURRENT,
    STAGE1_PAYMENT_RECONCILIATION_LAUNCH_BLOCKED,
    STAGE1_PAYMENT_RECONCILIATION_MAX_AGE_MINUTES,
    STAGE1_PAYMENT_RECONCILIATION_RUNS_TOTAL,
)
from src.services.backend_api_client import BackendAPIClient

logger = structlog.get_logger(__name__)

STAGE1_RECONCILIATION_BATCH_LIMIT = 250
STAGE1_RECONCILIATION_SEVERITIES = (
    "manual_review",
    "alert_15m",
    "p1_escalation",
    "p0_blocker",
)


@broker.task(task_name="reconcile_stage1_payments", queue="payments")
async def reconcile_stage1_payments() -> dict[str, Any]:
    """Ask the backend to scan canonical S1 payment state for mismatches."""

    settings = get_settings()
    if not settings.backend_api_url or settings.backend_internal_secret is None:
        STAGE1_PAYMENT_RECONCILIATION_RUNS_TOTAL.labels(result="skipped").inc()
        logger.info("stage1_payment_reconciliation_skipped", reason="backend_api_not_configured")
        return {"skipped": True, "reason": "backend_api_not_configured"}

    try:
        async with BackendAPIClient() as backend:
            if not backend.enabled:
                STAGE1_PAYMENT_RECONCILIATION_RUNS_TOTAL.labels(result="skipped").inc()
                logger.info("stage1_payment_reconciliation_skipped", reason="backend_api_disabled")
                return {"skipped": True, "reason": "backend_api_disabled"}

            report = await backend.run_stage1_payment_reconciliation(
                {"limit": STAGE1_RECONCILIATION_BATCH_LIMIT}
            )
    except Exception:
        STAGE1_PAYMENT_RECONCILIATION_RUNS_TOTAL.labels(result="failure").inc()
        raise

    summary = dict(report.get("summary") or {})
    _update_stage1_payment_reconciliation_metrics(summary)
    STAGE1_PAYMENT_RECONCILIATION_RUNS_TOTAL.labels(result="success").inc()
    result = {
        "report_version": report.get("report_version"),
        "generated_at": report.get("generated_at") or datetime.now(UTC).isoformat(),
        "summary": summary,
        "items_count": len(report.get("items") or []),
    }
    logger.info(
        "stage1_payment_reconciliation_complete",
        total_items=summary.get("total_items", result["items_count"]),
        p0_blocker_items=summary.get("p0_blocker_items", 0),
        launch_blocked=summary.get("launch_blocked", False),
    )
    return result


def _update_stage1_payment_reconciliation_metrics(summary: dict[str, Any]) -> None:
    severity_values = {
        "manual_review": int(summary.get("manual_review_items") or 0),
        "alert_15m": int(summary.get("alert_15m_items") or 0),
        "p1_escalation": int(summary.get("p1_escalation_items") or 0),
        "p0_blocker": int(summary.get("p0_blocker_items") or 0),
    }
    for severity in STAGE1_RECONCILIATION_SEVERITIES:
        STAGE1_PAYMENT_RECONCILIATION_ITEMS_CURRENT.labels(severity=severity).set(
            severity_values[severity]
        )
    STAGE1_PAYMENT_RECONCILIATION_MAX_AGE_MINUTES.set(int(summary.get("max_age_minutes") or 0))
    STAGE1_PAYMENT_RECONCILIATION_LAUNCH_BLOCKED.set(
        1 if bool(summary.get("launch_blocked")) else 0
    )
