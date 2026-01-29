"""Sync VPN node configurations from Remnawave to Redis cache."""

import structlog

from src.broker import broker
from src.services.cache_service import CacheService
from src.services.redis_client import get_redis_client
from src.services.remnawave_client import RemnawaveClient
from src.utils.constants import NODE_CONFIG_KEY

logger = structlog.get_logger(__name__)


@broker.task(task_name="sync_node_configurations", queue="sync")
async def sync_node_configurations() -> dict:
    """Fetch all node configurations from Remnawave and cache them in Redis.

    Retrieves all VPN node configurations from the Remnawave API and stores
    them in Redis with a 35-minute TTL. This ensures the admin dashboard
    always has fresh node configuration data available.

    Cache key format: cybervpn:nodes:config:{node_uuid}
    TTL: 2100 seconds (35 minutes)
    """
    redis = get_redis_client()
    cache = CacheService(redis)
    synced = 0

    try:
        async with RemnawaveClient() as rw:
            nodes = await rw.get_nodes()

        for node in nodes:
            node_uuid = node.get("uuid", "")
            if not node_uuid:
                continue
            key = NODE_CONFIG_KEY.format(node_uuid=node_uuid)
            await cache.set(key, node, ttl=2100)  # 35 minutes
            synced += 1
    finally:
        await redis.aclose()

    logger.info("node_configs_synced", count=synced)
    return {"synced": synced}
