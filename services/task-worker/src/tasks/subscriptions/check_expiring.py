"""Fail-closed boundary for legacy Remnawave expiry reminders."""

import structlog

from src.broker import broker

logger = structlog.get_logger(__name__)
_SAFETY_REASON = "backend_remnawave_expiry_reminder_saga_required"


@broker.task(task_name="check_expiring_subscriptions", queue="subscriptions")
async def check_expiring_subscriptions() -> dict:
    """Refuse provider-owned recipient scans until the backend saga exists."""

    logger.error("expiring_subscription_task_safety_disabled", reason=_SAFETY_REASON)
    return {"reminders_sent": 0, "safety_disabled": True, "reason": _SAFETY_REASON}
