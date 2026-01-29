"""Bandwidth snapshot collection task."""

import time

import structlog

from src.broker import broker
from src.services.cache_service import CacheService
from src.services.redis_client import get_redis_client
from src.services.remnawave_client import RemnawaveClient
from src.utils.constants import BANDWIDTH_KEY, DASHBOARD_REALTIME_KEY

logger = structlog.get_logger(__name__)


@broker.task(task_name="collect_bandwidth_snapshot", queue="monitoring")
async def collect_bandwidth_snapshot() -> dict:
    """Collect bandwidth data from all VPN nodes and store in Redis.

    Queries bandwidth statistics (upload/download bytes) from each VPN node via the
    Remnawave API, stores individual snapshots in Redis with timestamps, and updates
    the real-time dashboard cache with aggregated totals.

    Returns:
        Dictionary with nodes count, total_up bytes, and total_down bytes
    """
    redis = get_redis_client()
    cache = CacheService(redis)
    timestamp = int(time.time())
    nodes_collected = 0
    total_bytes_up = 0
    total_bytes_down = 0

    try:
        async with RemnawaveClient() as client:
            nodes = await client.get_nodes()

        for node in nodes:
            node_uuid = node.get("uuid", "")
            bytes_up = node.get("trafficUp", 0) or 0
            bytes_down = node.get("trafficDown", 0) or 0
            total_bytes = bytes_up + bytes_down

            bw_key = BANDWIDTH_KEY.format(node_uuid=node_uuid, timestamp=timestamp)
            await cache.set(
                bw_key,
                {"up": bytes_up, "down": bytes_down, "total": total_bytes, "ts": timestamp},
                ttl=48 * 3600,
            )

            total_bytes_up += bytes_up
            total_bytes_down += bytes_down
            nodes_collected += 1

        # Update realtime dashboard cache
        await cache.set(
            DASHBOARD_REALTIME_KEY,
            {
                "total_up": total_bytes_up,
                "total_down": total_bytes_down,
                "nodes_count": nodes_collected,
                "timestamp": timestamp,
            },
            ttl=120,
        )
    finally:
        await redis.aclose()

    logger.info("bandwidth_collected", nodes=nodes_collected, up=total_bytes_up, down=total_bytes_down)
    return {"nodes": nodes_collected, "total_up": total_bytes_up, "total_down": total_bytes_down}
