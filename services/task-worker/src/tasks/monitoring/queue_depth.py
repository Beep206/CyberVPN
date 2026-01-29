"""Queue depth monitoring task.

Periodically measures Redis stream queue depths and updates Prometheus metrics.
This provides visibility into task backlog and helps identify processing bottlenecks.
"""

import structlog
from redis.asyncio import Redis
from taskiq import TaskiqDepends

from src.broker import broker
from src.config import get_settings
from src.metrics import QUEUE_DEPTH

logger = structlog.get_logger(__name__)


async def get_redis_client() -> Redis:
    """Get Redis client from settings.

    Returns:
        Redis async client instance
    """
    settings = get_settings()
    return Redis.from_url(settings.redis_url, decode_responses=True)


@broker.task(task_name="monitor_queue_depth")
async def monitor_queue_depth(redis: Redis = TaskiqDepends(get_redis_client)) -> dict[str, int]:
    """Monitor Redis stream queue depths and update Prometheus metrics.

    Reads the length of all TaskIQ-related Redis streams and updates the
    cybervpn_queue_depth gauge metric for monitoring and alerting.

    Args:
        redis: Redis async client (injected via TaskiqDepends)

    Returns:
        Dictionary mapping queue names to their current depths
    """
    try:
        queue_depths = {}

        # Get all stream keys (TaskIQ uses 'taskiq:stream:*' pattern)
        stream_keys = []
        cursor = 0
        while True:
            cursor, keys = await redis.scan(cursor=cursor, match="taskiq:stream:*", count=100)
            stream_keys.extend(keys)
            if cursor == 0:
                break

        for stream_key in stream_keys:
            try:
                # Get stream length using XLEN command
                length = await redis.xlen(stream_key)

                # Extract queue name from Redis key
                stream_key_str = stream_key.decode("utf-8") if isinstance(stream_key, bytes) else stream_key
                queue_name = stream_key_str.replace("taskiq:stream:", "")

                # Update Prometheus metric
                QUEUE_DEPTH.labels(queue=queue_name).set(length)

                queue_depths[queue_name] = length

                if length > 0:
                    logger.debug(
                        "queue_depth_measured",
                        queue=queue_name,
                        depth=length,
                    )

            except Exception as exc:
                logger.warning(
                    "queue_depth_measurement_failed",
                    stream_key=stream_key,
                    error=str(exc),
                )
                continue

        # Also monitor the result backend list (pending results)
        try:
            result_keys = []
            cursor = 0
            while True:
                cursor, keys = await redis.scan(cursor=cursor, match="taskiq:result:*", count=200)
                result_keys.extend(keys)
                if cursor == 0:
                    break
            QUEUE_DEPTH.labels(queue="result_backend").set(len(result_keys))
            queue_depths["result_backend"] = len(result_keys)
        except Exception as exc:
            logger.warning(
                "result_backend_measurement_failed",
                error=str(exc),
            )

        total_items = sum(queue_depths.values())
        await redis.set("cybervpn:metrics:queue_depth", total_items, ex=300)

        logger.info(
            "queue_depth_monitoring_complete",
            total_queues=len(queue_depths),
            total_items=total_items,
        )

        return queue_depths

    except Exception as exc:
        logger.exception("queue_depth_monitoring_failed", error=str(exc))
        raise

    finally:
        await redis.aclose()
