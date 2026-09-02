"""Fail-closed boundary for the legacy worker-owned completion flow."""

from typing import Any, cast

import structlog

from src.broker import broker

logger = structlog.get_logger(__name__)
_SAFETY_REASON = "backend_payment_completion_saga_required"


def _attach_task_labels(task: Any, **labels: str) -> Any:
    """Attach labels compatibly across TaskIQ versions."""
    task_obj = cast(Any, task)
    if hasattr(task_obj, "with_labels"):
        return task_obj.with_labels(**labels)

    existing = getattr(task_obj, "labels", None)
    if isinstance(existing, dict):
        existing.update(labels)
    else:
        task_obj.labels = labels
    return task_obj


@broker.task(task_name="process_payment_completion", queue="payments")
async def process_payment_completion(payment_id: str) -> dict:
    """Leave the payment pending until an atomic backend saga owns all effects."""

    logger.error(
        "payment_completion_task_safety_disabled",
        payment_id=payment_id,
        reason=_SAFETY_REASON,
    )
    return {
        "payment_id": payment_id,
        "payment_updated": False,
        "user_enabled": False,
        "subscription_extended": False,
        "notification_queued": False,
        "pending_reconciliation": True,
        "safety_disabled": True,
        "reason": _SAFETY_REASON,
    }


process_payment_completion = _attach_task_labels(
    process_payment_completion,
    retry_policy="payments_webhook",
)
