"""Task-worker entry points for CyberVPN VPN Tester."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any
from uuid import uuid4

import structlog

from src.broker import broker
from src.config import get_settings
from src.metrics import (
    VPN_TESTER_WORKER_LOCK_SKIPS_TOTAL,
    VPN_TESTER_WORKER_QUEUE_RUNS_TOTAL,
    VPN_TESTER_WORKER_SCHEDULE_GATE_TOTAL,
)
from src.services.backend_api_client import BackendAPIClient
from src.services.redis_client import get_redis_client
from src.utils.constants import QUEUE_VPN_TESTING, VPN_TESTER_LOCK_KEY

logger = structlog.get_logger(__name__)


async def _with_redis_lock(task_key: str, operation: Callable[[], Awaitable[dict[str, Any]]]) -> dict[str, Any]:
    settings = get_settings()
    redis = get_redis_client()
    lock_key = VPN_TESTER_LOCK_KEY.format(task_key=task_key)
    lock_value = str(uuid4())
    try:
        acquired = await redis.set(lock_key, lock_value, ex=settings.vpn_tester_lock_ttl_seconds, nx=True)
        if not acquired:
            logger.info("vpn_tester_task_skipped", task_key=task_key, reason="lock_held")
            VPN_TESTER_WORKER_LOCK_SKIPS_TOTAL.labels(task_key=task_key).inc()
            return {"skipped": True, "reason": "lock_held", "task_key": task_key}
        return await operation()
    finally:
        try:
            current_value = await redis.get(lock_key)
            if current_value == lock_value:
                await redis.delete(lock_key)
        finally:
            await redis.aclose()


def _run_summary(response: dict[str, Any]) -> dict[str, Any]:
    run = response.get("run")
    if not isinstance(run, dict):
        return {"skipped": bool(response.get("skipped")), "reason": response.get("reason")}
    return {
        "run_id": run.get("id"),
        "suite_key": run.get("suite_key"),
        "mode": run.get("mode"),
        "status": run.get("status"),
        "pass_count": run.get("pass_count"),
        "fail_count": run.get("fail_count"),
        "degraded_count": run.get("degraded_count"),
    }


async def _call_scheduled_backend(
    *,
    task_key: str,
    schedule_key: str,
    trigger: str,
    idempotency_window: str = "minute",
) -> dict[str, Any]:
    settings = get_settings()
    if not settings.backend_api_url or settings.backend_internal_secret is None:
        return {"skipped": True, "reason": "backend_api_not_configured", "task_key": task_key}

    async def operation() -> dict[str, Any]:
        async with BackendAPIClient() as backend:
            if not backend.backend_internal_enabled:
                return {"skipped": True, "reason": "backend_internal_disabled", "task_key": task_key}
            response = await backend.run_vpn_tester_schedule(
                schedule_key,
                {
                    "trigger": trigger,
                    "execute_immediately": True,
                    "idempotency_window": idempotency_window,
                },
            )
            result = str(response.get("reason") or (response.get("run") or {}).get("status") or "accepted")
            VPN_TESTER_WORKER_SCHEDULE_GATE_TOTAL.labels(schedule_key=schedule_key, result=result).inc()
            logger.info("vpn_tester_scheduled_complete", task_key=task_key, **_run_summary(response))
            return response

    return await _with_redis_lock(task_key, operation)


@broker.task(task_name="process_vpn_tester_queue", queue=QUEUE_VPN_TESTING)
async def process_vpn_tester_queue() -> dict[str, Any]:
    settings = get_settings()
    if not settings.vpn_tester_enabled:
        return {"skipped": True, "reason": "vpn_tester_disabled"}

    async def operation() -> dict[str, Any]:
        processed = 0
        skipped_reason: str | None = None
        async with BackendAPIClient() as backend:
            if not backend.backend_internal_enabled:
                return {"skipped": True, "reason": "backend_internal_disabled"}
            for _ in range(max(1, settings.vpn_tester_queue_batch_limit)):
                response = await backend.execute_next_vpn_tester_run()
                if response.get("skipped"):
                    skipped_reason = str(response.get("reason") or "no_queued_runs")
                    break
                processed += 1
                result = str((response.get("run") or {}).get("status") or "processed")
                VPN_TESTER_WORKER_QUEUE_RUNS_TOTAL.labels(result=result).inc()
                logger.info("vpn_tester_queued_run_complete", **_run_summary(response))
        return {"processed": processed, "reason": skipped_reason}

    return await _with_redis_lock("queue", operation)


@broker.task(task_name="run_vpn_tester_lightweight", queue=QUEUE_VPN_TESTING)
async def run_vpn_tester_lightweight() -> dict[str, Any]:
    return await _call_scheduled_backend(
        task_key="lightweight",
        schedule_key="vpn-tester:lightweight",
        trigger="scheduled_lightweight",
    )


@broker.task(task_name="run_vpn_tester_all_tariffs", queue=QUEUE_VPN_TESTING)
async def run_vpn_tester_all_tariffs() -> dict[str, Any]:
    return await _call_scheduled_backend(
        task_key="all_tariffs",
        schedule_key="vpn-tester:all-tariffs",
        trigger="scheduled_all_tariffs",
        idempotency_window="hour",
    )


@broker.task(task_name="run_vpn_tester_deep", queue=QUEUE_VPN_TESTING)
async def run_vpn_tester_deep() -> dict[str, Any]:
    return await _call_scheduled_backend(
        task_key="deep",
        schedule_key="vpn-tester:deep",
        trigger="scheduled_deep",
        idempotency_window="day",
    )


@broker.task(task_name="run_vpn_tester_balancer_preview", queue=QUEUE_VPN_TESTING)
async def run_vpn_tester_balancer_preview() -> dict[str, Any]:
    return await _call_scheduled_backend(
        task_key="balancer_preview",
        schedule_key="vpn-tester:balancer-preview",
        trigger="scheduled_balancer_preview",
    )


@broker.task(task_name="cleanup_vpn_tester_artifacts", queue=QUEUE_VPN_TESTING)
async def cleanup_vpn_tester_artifacts() -> dict[str, Any]:
    settings = get_settings()
    if not settings.vpn_tester_enabled:
        return {"skipped": True, "reason": "vpn_tester_disabled"}

    async def operation() -> dict[str, Any]:
        async with BackendAPIClient() as backend:
            if not backend.backend_internal_enabled:
                return {"skipped": True, "reason": "backend_internal_disabled"}
            response = await backend.cleanup_vpn_tester()
            logger.info("vpn_tester_cleanup_complete", cleanup=response.get("cleanup"))
            return response

    return await _with_redis_lock("cleanup", operation)
