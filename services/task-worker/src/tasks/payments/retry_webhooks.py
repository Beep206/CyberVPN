"""Fail-closed boundary for legacy payment-completion webhook retries."""

import structlog

from src.broker import broker

logger = structlog.get_logger(__name__)
_SAFETY_REASON = "backend_payment_completion_saga_required"


@broker.task(task_name="retry_failed_webhooks", queue="payments")
async def retry_failed_webhooks() -> dict:
    """Leave webhook rows untouched until the backend completion saga owns them."""

    logger.error("retry_payment_webhooks_safety_disabled", reason=_SAFETY_REASON)
    return {
        "retried": 0,
        "pending_reconciliation": True,
        "safety_disabled": True,
        "reason": _SAFETY_REASON,
    }
