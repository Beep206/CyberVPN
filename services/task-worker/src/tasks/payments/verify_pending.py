"""Fail-closed boundary for legacy worker-owned payment verification."""

import structlog

from src.broker import broker

logger = structlog.get_logger(__name__)
_SAFETY_REASON = "backend_payment_completion_saga_required"


@broker.task(task_name="verify_pending_payments", queue="payments")
async def verify_pending_payments() -> dict:
    """Refuse verification that could dispatch the non-atomic legacy flow."""

    logger.error("verify_pending_payments_safety_disabled", reason=_SAFETY_REASON)
    return {
        "checked": 0,
        "completed": 0,
        "expired": 0,
        "pending_reconciliation": True,
        "safety_disabled": True,
        "reason": _SAFETY_REASON,
    }
