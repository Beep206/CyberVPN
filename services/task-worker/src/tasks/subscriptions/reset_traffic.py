"""Compatibility boundary for the retired monthly traffic-reset task."""

import structlog

from src.broker import broker

logger = structlog.get_logger(__name__)
_NOT_APPLICABLE_REASON = "backend_subscription_traffic_policy_is_no_reset"


@broker.task(task_name="reset_monthly_traffic", queue="subscriptions")
async def reset_monthly_traffic() -> dict:
    """Report the legacy task as not applicable without touching Remnawave.

    CyberVPN's authoritative paid, trial, manual and gift provisioning
    contracts all set ``trafficLimitStrategy`` to ``NO_RESET``.  Keep the
    historical TaskIQ name callable for compatibility, but never schedule or
    emulate a calendar reset in this worker.
    """

    logger.info("traffic_reset_task_not_applicable", reason=_NOT_APPLICABLE_REASON)
    return {
        "reset": 0,
        "not_applicable": True,
        "reason": _NOT_APPLICABLE_REASON,
    }
