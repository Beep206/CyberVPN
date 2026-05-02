"""Process queued partner bot provisioning jobs via backend internal APIs."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from time import perf_counter, time
from typing import Any

import structlog

from src.broker import broker
from src.config import get_settings
from src.metrics import (
    PARTNER_BOT_PROVISIONING_ACTIONS_TOTAL,
    PARTNER_BOT_PROVISIONING_CONSECUTIVE_FAILURES,
    PARTNER_BOT_PROVISIONING_DURATION,
    PARTNER_BOT_PROVISIONING_LAST_ATTEMPT_UNIXTIME,
    PARTNER_BOT_PROVISIONING_LAST_ERRORS,
    PARTNER_BOT_PROVISIONING_LAST_PROCESSED_JOBS,
    PARTNER_BOT_PROVISIONING_LAST_SUCCESS_UNIXTIME,
    PARTNER_BOT_PROVISIONING_RUNS_TOTAL,
)
from src.services.backend_api_client import BackendAPIClient

logger = structlog.get_logger(__name__)

MAX_PROVISIONING_JOBS_PER_RUN = 10
DEFAULT_PROCESSOR_ID = "task-worker:partner-bot-provisioning"


def _record_provisioning_success(
    *,
    processed: int,
    errors: int,
    actions_by_path: Counter[tuple[str, str]],
    duration_seconds: float,
) -> None:
    now_unix = time()
    PARTNER_BOT_PROVISIONING_LAST_ATTEMPT_UNIXTIME.set(now_unix)
    PARTNER_BOT_PROVISIONING_LAST_SUCCESS_UNIXTIME.set(now_unix)
    PARTNER_BOT_PROVISIONING_CONSECUTIVE_FAILURES.set(0)
    PARTNER_BOT_PROVISIONING_LAST_PROCESSED_JOBS.set(processed)
    PARTNER_BOT_PROVISIONING_LAST_ERRORS.set(errors)
    PARTNER_BOT_PROVISIONING_DURATION.observe(duration_seconds)
    PARTNER_BOT_PROVISIONING_RUNS_TOTAL.labels(result="success").inc()

    for (action, provisioning_path), count in actions_by_path.items():
        if count <= 0:
            continue
        PARTNER_BOT_PROVISIONING_ACTIONS_TOTAL.labels(
            action=action,
            provisioning_path=provisioning_path,
        ).inc(count)


def _record_provisioning_failure(*, duration_seconds: float) -> None:
    PARTNER_BOT_PROVISIONING_LAST_ATTEMPT_UNIXTIME.set(time())
    PARTNER_BOT_PROVISIONING_CONSECUTIVE_FAILURES.inc()
    PARTNER_BOT_PROVISIONING_DURATION.observe(duration_seconds)
    PARTNER_BOT_PROVISIONING_RUNS_TOTAL.labels(result="failure").inc()


@broker.task(task_name="process_partner_bot_provisioning_jobs", queue="sync")
async def process_partner_bot_provisioning_jobs() -> dict[str, Any]:
    """Process queued partner-bot provisioning jobs with honest fallback outcomes."""
    settings = get_settings()
    if not settings.backend_api_url or settings.backend_internal_secret is None:
        logger.info("partner_bot_provisioning_skipped", reason="backend_api_not_configured")
        return {"skipped": True, "reason": "backend_api_not_configured"}

    processed = 0
    errors = 0
    actions: Counter[str] = Counter()
    actions_by_path: Counter[tuple[str, str]] = Counter()
    started = perf_counter()

    try:
        async with BackendAPIClient() as backend:
            if not backend.enabled:
                logger.info("partner_bot_provisioning_skipped", reason="backend_api_disabled")
                return {"skipped": True, "reason": "backend_api_disabled"}

            for _ in range(MAX_PROVISIONING_JOBS_PER_RUN):
                claimed = await backend.claim_partner_bot_provisioning_job(
                    {
                        "processor_id": DEFAULT_PROCESSOR_ID,
                        "max_scan_count": 10,
                    }
                )
                bot = claimed.get("bot")
                if not isinstance(bot, dict):
                    break

                latest_job = bot.get("latest_provisioning_job")
                if not isinstance(latest_job, dict):
                    errors += 1
                    logger.warning(
                        "partner_bot_provisioning_missing_job",
                        partner_bot_id=bot.get("id"),
                    )
                    continue

                processed += 1
                job_id = str(latest_job.get("id") or "").strip()
                provisioning_path = str(bot.get("provisioning_path") or "managed_bot")
                if not job_id:
                    errors += 1
                    logger.warning(
                        "partner_bot_provisioning_missing_job_id",
                        partner_bot_id=bot.get("id"),
                    )
                    continue

                finalization_payload = _build_manual_intervention_payload(bot)
                try:
                    finalized = await backend.finalize_partner_bot_provisioning_job(
                        provisioning_job_id=job_id,
                        payload=finalization_payload,
                    )
                except Exception as exc:
                    errors += 1
                    logger.warning(
                        "partner_bot_provisioning_finalize_failed",
                        partner_bot_id=bot.get("id"),
                        provisioning_job_id=job_id,
                        error=str(exc),
                    )
                    continue

                finalized_job = finalized.get("latest_provisioning_job") if isinstance(finalized, dict) else None
                action = str((finalized_job or {}).get("job_status") or "unknown")
                actions[action] += 1
                actions_by_path[(action, provisioning_path)] += 1
    except Exception:
        _record_provisioning_failure(duration_seconds=perf_counter() - started)
        raise

    result = {
        "processed": processed,
        "errors": errors,
        "actions": dict(actions),
        "generated_at": datetime.now(UTC).isoformat(),
    }
    _record_provisioning_success(
        processed=processed,
        errors=errors,
        actions_by_path=actions_by_path,
        duration_seconds=perf_counter() - started,
    )
    logger.info("partner_bot_provisioning_complete", **result)
    return result


def _build_manual_intervention_payload(bot: dict[str, Any]) -> dict[str, Any]:
    provisioning_path = str(bot.get("provisioning_path") or "managed_bot")
    if provisioning_path == "manual_token":
        reason_code = "manual_token_required"
        operator_action = "collect_manual_bot_token_and_resume_provisioning"
        last_error = "Manual bot token onboarding is required before provisioning can continue"
    else:
        reason_code = "managed_bot_runtime_not_implemented"
        operator_action = "complete_managed_bot_binding_spike_and_resume_provisioning"
        last_error = "Managed bot provisioning is queued for operator completion"

    return {
        "processor_id": DEFAULT_PROCESSOR_ID,
        "job_status": "manual_intervention_required",
        "last_error": last_error,
        "result_payload": {
            "reason_code": reason_code,
            "operator_action": operator_action,
            "provisioning_path": provisioning_path,
            "bot_key": bot.get("bot_key"),
        },
    }
