"""Fail-closed boundary for legacy Remnawave expiry mutations."""

import structlog

from src.broker import broker

logger = structlog.get_logger(__name__)
_SAFETY_REASON = "backend_remnawave_expiry_disable_saga_required"


@broker.task(task_name="disable_expired_users", queue="subscriptions")
async def disable_expired_users() -> dict:
    """Refuse mutations until exact identity and reconciliation are backend-owned."""

    logger.error("disable_expired_task_safety_disabled", reason=_SAFETY_REASON)
    return {"disabled": 0, "safety_disabled": True, "reason": _SAFETY_REASON}
