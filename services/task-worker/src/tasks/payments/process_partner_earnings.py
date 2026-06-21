"""Process durable payment.completed partner earning outbox publications."""

from __future__ import annotations

import socket
from typing import Any

import structlog

from src.broker import broker
from src.config import get_settings
from src.metrics import (
    PAYMENT_COMPLETED_PARTNER_EARNINGS_ACTIONS_TOTAL,
    PAYMENT_COMPLETED_PARTNER_EARNINGS_RUNS_TOTAL,
)
from src.services.backend_api_client import BackendAPIClient, BackendAPIError

logger = structlog.get_logger(__name__)


@broker.task(task_name="process_partner_earning_from_payment", queue="payments", retry_policy="payments")
async def process_partner_earning_from_payment() -> dict[str, Any]:
    """Ask backend to claim and process due payment.completed partner earning work."""

    settings = get_settings()
    if not settings.payment_completed_partner_earnings_enabled:
        PAYMENT_COMPLETED_PARTNER_EARNINGS_RUNS_TOTAL.labels(result="skipped").inc()
        logger.info("payment_completed_partner_earnings_skipped", reason="disabled")
        return {"skipped": True, "reason": "disabled"}

    if (
        not settings.backend_api_url
        or settings.payment_settlement_worker_secret is None
        or not settings.payment_settlement_worker_secret.get_secret_value().strip()
    ):
        PAYMENT_COMPLETED_PARTNER_EARNINGS_RUNS_TOTAL.labels(result="failure").inc()
        logger.error("payment_completed_partner_earnings_misconfigured", reason="backend_api_not_configured")
        raise BackendAPIError("Payment completed partner earnings backend API is not configured")

    try:
        async with BackendAPIClient() as backend:
            if not backend.payment_settlement_enabled:
                PAYMENT_COMPLETED_PARTNER_EARNINGS_RUNS_TOTAL.labels(result="failure").inc()
                logger.error("payment_completed_partner_earnings_misconfigured", reason="backend_api_disabled")
                raise BackendAPIError("Payment completed partner earnings backend API is disabled")

            report = await backend.run_payment_completed_partner_earnings(
                {
                    "limit": settings.payment_completed_partner_earnings_batch_limit,
                    "worker_id": f"{socket.gethostname()}:partner-earning-worker",
                }
            )
    except Exception:
        PAYMENT_COMPLETED_PARTNER_EARNINGS_RUNS_TOTAL.labels(result="failure").inc()
        raise

    for action in ("claimed", "succeeded", "retrying", "dead_letter", "skipped"):
        value = int(report.get(action) or 0)
        if value:
            PAYMENT_COMPLETED_PARTNER_EARNINGS_ACTIONS_TOTAL.labels(action=action).inc(value)

    result_label = "success" if int(report.get("dead_letter") or 0) == 0 else "degraded"
    PAYMENT_COMPLETED_PARTNER_EARNINGS_RUNS_TOTAL.labels(result=result_label).inc()
    logger.info(
        "payment_completed_partner_earnings_complete",
        claimed=int(report.get("claimed") or 0),
        succeeded=int(report.get("succeeded") or 0),
        retrying=int(report.get("retrying") or 0),
        dead_letter=int(report.get("dead_letter") or 0),
    )
    return report
