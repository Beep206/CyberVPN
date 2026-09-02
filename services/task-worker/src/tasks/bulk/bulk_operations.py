"""Bulk Remnawave mutations disabled until durable receipts are available."""

import structlog

from src.broker import broker

logger = structlog.get_logger(__name__)

_SAFETY_REASON = "bulk Remnawave mutations require backend-owned durable receipts before at-least-once delivery"


def _safety_disabled_result(user_ids: list[int]) -> dict[str, int | bool | str]:
    return {
        "total": len(user_ids),
        "processed": 0,
        "failed": 0,
        "safety_disabled": True,
        "reason": _SAFETY_REASON,
    }


@broker.task(task_name="bulk_disable_users", queue="bulk")
async def bulk_disable_users(
    user_ids: list[int],
    initiated_by: str = "system",
) -> dict[str, int | bool | str]:
    """Fail closed instead of replaying a non-idempotent provider mutation."""

    logger.error(
        "bulk_disable_users_safety_disabled",
        total=len(user_ids),
        initiated_by_present=bool(initiated_by),
        reason=_SAFETY_REASON,
    )
    return _safety_disabled_result(user_ids)


@broker.task(task_name="bulk_enable_users", queue="bulk")
async def bulk_enable_users(
    user_ids: list[int],
    initiated_by: str = "system",
) -> dict[str, int | bool | str]:
    """Fail closed instead of replaying a non-idempotent provider mutation."""

    logger.error(
        "bulk_enable_users_safety_disabled",
        total=len(user_ids),
        initiated_by_present=bool(initiated_by),
        reason=_SAFETY_REASON,
    )
    return _safety_disabled_result(user_ids)
