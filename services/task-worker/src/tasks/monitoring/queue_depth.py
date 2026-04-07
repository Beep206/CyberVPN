"""Queue depth monitoring task.

Periodically measures Redis stream queue depths and updates Prometheus metrics.
This provides visibility into task backlog and helps identify processing bottlenecks.
"""

import asyncio
import json

import structlog
from redis.asyncio import Redis
from taskiq import TaskiqDepends

from src.broker import broker
from src.config import get_settings
from src.metrics import QUEUE_DEPTH

logger = structlog.get_logger(__name__)

TASKIQ_STREAM_KEY = "taskiq"
TASKIQ_GROUP_NAME = "taskiq"
EMAIL_QUEUE_NAME = "email"
QUEUE_DEPTH_POLL_INTERVAL_SECONDS = 15


async def get_redis_client() -> Redis:
    """Get Redis client from settings.

    Returns:
        Redis async client instance
    """
    settings = get_settings()
    return Redis.from_url(settings.redis_url, decode_responses=True)


REDIS_DEPENDENCY = TaskiqDepends(get_redis_client)


def _extract_queue_name(fields: dict[str, str]) -> str | None:
    """Extract the TaskIQ queue label from a Redis stream entry payload."""
    raw_payload = fields.get("data")
    if not raw_payload:
        return None

    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError:
        logger.warning("queue_depth_invalid_taskiq_payload")
        return None

    labels = payload.get("labels")
    if not isinstance(labels, dict):
        return None

    queue_name = labels.get("queue")
    if not isinstance(queue_name, str) or not queue_name:
        return None

    return queue_name


async def _count_entries_for_queue(
    redis: Redis,
    *,
    stream_key: str,
    entry_ids: list[str],
    queue_name: str,
) -> int:
    """Count stream entries whose TaskIQ payload belongs to the target queue."""
    count = 0

    for entry_id in entry_ids:
        entries = await redis.xrange(stream_key, min=entry_id, max=entry_id, count=1)
        if not entries:
            continue

        _, fields = entries[0]
        if _extract_queue_name(fields) == queue_name:
            count += 1

    return count


async def _measure_email_queue_backlog(redis: Redis) -> int:
    """Measure outstanding backlog for TaskIQ tasks labeled with queue=email."""
    try:
        groups = await redis.xinfo_groups(TASKIQ_STREAM_KEY)
    except Exception as exc:
        logger.debug("queue_depth_group_info_unavailable", error=str(exc))
        return 0

    group_info = next((group for group in groups if group.get("name") == TASKIQ_GROUP_NAME), None)
    if group_info is None:
        return 0

    pending_total = int(group_info.get("pending", 0) or 0)
    lag_total = int(group_info.get("lag", 0) or 0)
    backlog = 0

    if pending_total:
        pending_entries = await redis.xpending_range(
            TASKIQ_STREAM_KEY,
            TASKIQ_GROUP_NAME,
            "-",
            "+",
            pending_total,
        )
        pending_ids = [entry["message_id"] for entry in pending_entries if entry.get("message_id")]
        backlog += await _count_entries_for_queue(
            redis,
            stream_key=TASKIQ_STREAM_KEY,
            entry_ids=pending_ids,
            queue_name=EMAIL_QUEUE_NAME,
        )

    if lag_total:
        last_delivered_id = group_info.get("last-delivered-id") or "0-0"
        unread_entries = await redis.xrange(
            TASKIQ_STREAM_KEY,
            min=f"({last_delivered_id}",
            max="+",
            count=lag_total,
        )
        backlog += sum(1 for _, fields in unread_entries if _extract_queue_name(fields) == EMAIL_QUEUE_NAME)

    return backlog


async def refresh_queue_depth_metrics(redis: Redis | None = None) -> dict[str, int]:
    """Refresh queue depth gauges using the live TaskIQ Redis stream state."""
    owns_client = redis is None
    if redis is None:
        redis = await get_redis_client()

    try:
        email_depth = await _measure_email_queue_backlog(redis)
        QUEUE_DEPTH.labels(queue=EMAIL_QUEUE_NAME).set(email_depth)

        result_keys = []
        cursor = 0
        while True:
            cursor, keys = await redis.scan(cursor=cursor, match="taskiq:result:*", count=200)
            result_keys.extend(keys)
            if cursor == 0:
                break

        result_backend_depth = len(result_keys)
        QUEUE_DEPTH.labels(queue="result_backend").set(result_backend_depth)

        queue_depths = {
            EMAIL_QUEUE_NAME: email_depth,
            "result_backend": result_backend_depth,
        }
        total_items = sum(queue_depths.values())
        await redis.set("cybervpn:metrics:queue_depth", total_items, ex=300)

        logger.info(
            "queue_depth_monitoring_complete",
            email_depth=email_depth,
            result_backend_depth=result_backend_depth,
            total_items=total_items,
        )
        return queue_depths
    finally:
        if owns_client:
            await redis.aclose()


async def queue_depth_metrics_loop(poll_interval_seconds: int = QUEUE_DEPTH_POLL_INTERVAL_SECONDS) -> None:
    """Continuously refresh queue depth gauges in the background."""
    redis = await get_redis_client()
    try:
        while True:
            await refresh_queue_depth_metrics(redis)
            await asyncio.sleep(poll_interval_seconds)
    except asyncio.CancelledError:
        logger.info("queue_depth_metrics_loop_stopped")
        raise
    finally:
        await redis.aclose()


@broker.task(task_name="monitor_queue_depth")
async def monitor_queue_depth(redis: Redis = REDIS_DEPENDENCY) -> dict[str, int]:
    """Monitor Redis stream queue depths and update Prometheus metrics.

    Reads the length of all TaskIQ-related Redis streams and updates the
    cybervpn_queue_depth gauge metric for monitoring and alerting.

    Args:
        redis: Redis async client (injected via TaskiqDepends)

    Returns:
        Dictionary mapping queue names to their current depths
    """
    try:
        return await refresh_queue_depth_metrics(redis)
    except Exception as exc:
        logger.exception("queue_depth_monitoring_failed", error=str(exc))
        raise
