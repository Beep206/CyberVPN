"""Scheduled refresh for Growth Codes FX provider snapshots."""

from __future__ import annotations

from datetime import UTC, datetime
from time import perf_counter
from typing import Any

import structlog

from src.broker import broker
from src.config import get_settings
from src.services.backend_api_client import BackendAPIClient

logger = structlog.get_logger(__name__)


def _scheduled_growth_fx_refresh_idempotency_key(triggered_at: datetime) -> str:
    bucket_minute = (triggered_at.minute // 15) * 15
    bucket = triggered_at.astimezone(UTC).replace(minute=bucket_minute, second=0, microsecond=0)
    return f"scheduled:{bucket:%Y%m%d%H%M}"


@broker.task(task_name="refresh_growth_fx_rates", queue="analytics")
async def refresh_growth_fx_rates() -> dict[str, Any]:
    """Trigger backend-owned FX provider refresh through the internal service API."""
    settings = get_settings()
    if not settings.backend_api_url or settings.backend_internal_secret is None:
        logger.info("growth_fx_refresh_skipped", reason="backend_api_not_configured")
        return {"skipped": True, "reason": "backend_api_not_configured"}

    started = perf_counter()
    idempotency_key = _scheduled_growth_fx_refresh_idempotency_key(datetime.now(UTC))
    try:
        async with BackendAPIClient() as backend:
            if not backend.backend_internal_enabled:
                logger.info("growth_fx_refresh_skipped", reason="backend_api_disabled")
                return {"skipped": True, "reason": "backend_api_disabled"}

            response = await backend.refresh_growth_fx_rates({"idempotency_key": idempotency_key})
    except Exception:
        logger.exception(
            "growth_fx_refresh_failed",
            duration_seconds=round(perf_counter() - started, 6),
        )
        raise

    result = {
        "refreshed_at": response.get("triggered_at") or datetime.now(UTC).isoformat(),
        "run_count": int(response.get("run_count", 0) or 0),
        "created_snapshot_count": int(response.get("created_snapshot_count", 0) or 0),
        "run_statuses": dict(response.get("run_statuses") or {}),
        "skipped": bool(response.get("skipped", False)),
        "reason": response.get("reason"),
    }
    logger.info("growth_fx_refresh_complete", **result)
    return result
