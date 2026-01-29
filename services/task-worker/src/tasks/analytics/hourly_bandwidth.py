"""Aggregate 5-minute bandwidth snapshots into hourly buckets."""

import json
from datetime import datetime, timedelta, timezone

import structlog
from redis.asyncio import Redis

from src.broker import broker
from src.services.redis_client import get_redis_client
from src.utils.constants import BANDWIDTH_KEY, REDIS_PREFIX

logger = structlog.get_logger(__name__)


@broker.task(task_name="aggregate_hourly_bandwidth", queue="analytics")
async def aggregate_hourly_bandwidth() -> dict:
    """Aggregate 5-minute bandwidth snapshots into hourly buckets.

    Reads raw bandwidth data from Redis sorted sets (5-minute snapshots),
    aggregates them into hourly buckets with sum/avg/max metrics,
    and sets appropriate TTLs (30 days for hourly, deletes raw > 48h).

    Returns:
        Dictionary with nodes_processed and snapshots_aggregated counts
    """
    redis: Redis = get_redis_client()
    nodes_processed = 0
    snapshots_aggregated = 0

    try:
        # Get current hour timestamp (aligned to hour boundary)
        now = datetime.now(timezone.utc)
        current_hour = now.replace(minute=0, second=0, microsecond=0)
        hour_timestamp = int(current_hour.timestamp())

        # Time range for last hour of 5-minute snapshots
        hour_start = current_hour - timedelta(hours=1)
        hour_end = current_hour

        # Get all node UUIDs from raw bandwidth key pattern
        cursor = 0
        node_uuids = set()

        while True:
            cursor, keys = await redis.scan(cursor, match=f"{REDIS_PREFIX}bandwidth:*", count=100)
            for key in keys:
                key_str = key.decode("utf-8") if isinstance(key, bytes) else key
                if ":bandwidth:hourly:" in key_str:
                    continue
                # Parse node UUID from key pattern: cybervpn:bandwidth:{node_uuid}:{timestamp}
                parts = key_str.split(":")
                if len(parts) >= 4:
                    node_uuids.add(parts[2])
            if cursor == 0:
                break

        # Aggregate for each node
        for node_uuid in node_uuids:
            bandwidth_values = []

            # Collect all 5-minute snapshots from the last hour
            timestamp = hour_start
            while timestamp < hour_end:
                ts = int(timestamp.timestamp())
                key = BANDWIDTH_KEY.format(node_uuid=node_uuid, timestamp=ts)
                value = await redis.get(key)

                if value:
                    try:
                        payload = json.loads(value)
                        total_value = payload.get("total")
                        if total_value is None:
                            total_value = (payload.get("up", 0) or 0) + (payload.get("down", 0) or 0)
                        bandwidth_values.append(int(total_value))
                    except (ValueError, TypeError, json.JSONDecodeError):
                        logger.warning("invalid_bandwidth_value", node=node_uuid, value=value)

                timestamp += timedelta(minutes=5)

            # Compute aggregates
            if bandwidth_values:
                total = sum(bandwidth_values)
                avg = total // len(bandwidth_values)
                max_val = max(bandwidth_values)
                min_val = min(bandwidth_values)

                # Store hourly aggregates
                hourly_key = f"{REDIS_PREFIX}bandwidth:hourly:{node_uuid}:{hour_timestamp}"
                await redis.hset(  # type: ignore[misc]
                    hourly_key,
                    mapping={
                        "sum": str(total),
                        "avg": str(avg),
                        "max": str(max_val),
                        "min": str(min_val),
                        "samples": str(len(bandwidth_values)),
                    },
                )
                # TTL: 30 days
                await redis.expire(hourly_key, 30 * 24 * 3600)  # type: ignore[misc]
                snapshots_aggregated += len(bandwidth_values)
                nodes_processed += 1

                logger.debug(
                    "hourly_bandwidth_aggregated",
                    node=node_uuid,
                    hour=current_hour.isoformat(),
                    sum=total,
                    avg=avg,
                    max=max_val,
                )

    except Exception as e:
        logger.exception("hourly_bandwidth_aggregation_failed", error=str(e))
        raise
    finally:
        await redis.aclose()

    logger.info("hourly_bandwidth_complete", nodes_processed=nodes_processed, snapshots_aggregated=snapshots_aggregated)
    return {"nodes_processed": nodes_processed, "snapshots_aggregated": snapshots_aggregated}
