"""Stage 1 durable Remnawave provisioning retry worker."""

from __future__ import annotations

import socket
from typing import Any

import structlog

from src.broker import broker
from src.config import get_settings
from src.metrics import (
    STAGE1_PROVISIONING_RETRY_ACTIONS_TOTAL,
    STAGE1_PROVISIONING_RETRY_CLAIMS_TOTAL,
    STAGE1_PROVISIONING_RETRY_JOBS_CURRENT,
    STAGE1_PROVISIONING_RETRY_MAX_AGE_SECONDS,
    STAGE1_PROVISIONING_RETRY_REMNAWAVE_ERRORS_TOTAL,
    STAGE1_PROVISIONING_RETRY_RUNS_TOTAL,
)
from src.services.backend_api_client import BackendAPIClient

logger = structlog.get_logger(__name__)

STAGE1_PROVISIONING_RETRY_STATES = ("queued", "retrying", "dead_letter", "succeeded")


@broker.task(task_name="process_stage1_provisioning_retries", queue="payments")
async def process_stage1_provisioning_retries() -> dict[str, Any]:
    """Ask backend to claim and process due durable S1 provisioning retry jobs."""

    settings = get_settings()
    if not settings.stage1_provisioning_retry_claiming_enabled:
        STAGE1_PROVISIONING_RETRY_RUNS_TOTAL.labels(result="skipped").inc()
        STAGE1_PROVISIONING_RETRY_CLAIMS_TOTAL.labels(result="disabled").inc()
        logger.info("stage1_provisioning_retry_skipped", reason="claiming_disabled")
        return {"skipped": True, "reason": "claiming_disabled"}

    if not settings.backend_api_url or settings.backend_internal_secret is None:
        STAGE1_PROVISIONING_RETRY_RUNS_TOTAL.labels(result="skipped").inc()
        STAGE1_PROVISIONING_RETRY_CLAIMS_TOTAL.labels(result="backend_api_not_configured").inc()
        logger.info("stage1_provisioning_retry_skipped", reason="backend_api_not_configured")
        return {"skipped": True, "reason": "backend_api_not_configured"}

    try:
        async with BackendAPIClient() as backend:
            if not backend.enabled:
                STAGE1_PROVISIONING_RETRY_RUNS_TOTAL.labels(result="skipped").inc()
                STAGE1_PROVISIONING_RETRY_CLAIMS_TOTAL.labels(result="backend_api_disabled").inc()
                logger.info("stage1_provisioning_retry_skipped", reason="backend_api_disabled")
                return {"skipped": True, "reason": "backend_api_disabled"}

            report = await backend.run_stage1_provisioning_retries(
                {
                    "limit": settings.stage1_provisioning_retry_batch_limit,
                    "worker_id": f"{socket.gethostname()}:task-worker",
                }
            )
    except Exception:
        STAGE1_PROVISIONING_RETRY_RUNS_TOTAL.labels(result="failure").inc()
        raise

    _update_stage1_provisioning_retry_metrics(report)
    result_label = "skipped" if report.get("skipped") else "success"
    STAGE1_PROVISIONING_RETRY_RUNS_TOTAL.labels(result=result_label).inc()
    STAGE1_PROVISIONING_RETRY_CLAIMS_TOTAL.labels(
        result="skipped" if int(report.get("claimed") or 0) == 0 else "claimed"
    ).inc()
    logger.info(
        "stage1_provisioning_retry_complete",
        claimed=int(report.get("claimed") or 0),
        succeeded=int(report.get("succeeded") or 0),
        retrying=int(report.get("retrying") or 0),
        dead_letter=int(report.get("dead_letter") or 0),
    )
    return report


def _update_stage1_provisioning_retry_metrics(report: dict[str, Any]) -> None:
    metrics = dict(report.get("metrics") or {})
    counts_by_state = dict(metrics.get("counts_by_state") or {})
    for state in STAGE1_PROVISIONING_RETRY_STATES:
        STAGE1_PROVISIONING_RETRY_JOBS_CURRENT.labels(state=state).set(int(counts_by_state.get(state) or 0))
    STAGE1_PROVISIONING_RETRY_MAX_AGE_SECONDS.set(int(metrics.get("max_job_age_seconds") or 0))

    for action in ("claimed", "succeeded", "retrying", "dead_letter", "reconciliation_required"):
        value = int(report.get(action) or 0)
        if value:
            STAGE1_PROVISIONING_RETRY_ACTIONS_TOTAL.labels(action=action).inc(value)

    for error_type, count in dict(report.get("remnawave_dependency_errors") or {}).items():
        safe_error_type = str(error_type)[:80] or "RemnawaveProvisioningError"
        STAGE1_PROVISIONING_RETRY_REMNAWAVE_ERRORS_TOTAL.labels(error_type=safe_error_type).inc(int(count or 0))
