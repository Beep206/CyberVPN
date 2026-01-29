"""Update real-time dashboard metrics cached in Redis."""

import structlog

from src.broker import broker
from src.services.redis_client import get_redis_client
from src.services.remnawave_client import RemnawaveClient
from src.utils.constants import DASHBOARD_REALTIME_KEY

logger = structlog.get_logger(__name__)


@broker.task(task_name="update_realtime_metrics", queue="analytics")
async def update_realtime_metrics() -> dict:
    """Update real-time dashboard metrics cached in Redis.

    Fetches current system state every 30 seconds:
    - Online users count
    - Active servers count
    - Current bandwidth usage
    - Latest events/alerts

    Caches results in Redis under DASHBOARD_REALTIME_KEY.

    Returns:
        Dictionary with online_users, active_servers, and updated status
    """
    redis = get_redis_client()
    metrics = {}

    try:
        async with RemnawaveClient() as rw:
            # Get users and count online
            users = await rw.get_users()
            online_users = sum(1 for u in users if u.get("status") == "active" and u.get("isOnline", False))

            # Get nodes and count active/connected
            nodes = await rw.get_nodes()
            active_servers = sum(1 for n in nodes if n.get("isConnected", False))

            # Calculate current bandwidth (sum of all active nodes)
            current_bandwidth = 0
            for node in nodes:
                if node.get("isConnected"):
                    # Assume bandwidth in bytes/sec from node stats
                    current_bandwidth += node.get("currentBandwidth", 0)

            # Prepare metrics payload
            metrics = {
                "online_users": online_users,
                "active_servers": active_servers,
                "total_servers": len(nodes),
                "total_users": len(users),
                "current_bandwidth": current_bandwidth,
                "last_updated": int(__import__("time").time()),
            }

        # Store in Redis as JSON with 60 second TTL (updated every 30s)
        import json

        await redis.set(DASHBOARD_REALTIME_KEY, json.dumps(metrics), ex=60)

        logger.info(
            "realtime_metrics_updated",
            online_users=online_users,
            active_servers=active_servers,
            bandwidth=current_bandwidth,
        )

    except Exception as e:
        logger.exception("realtime_metrics_failed", error=str(e))
        raise
    finally:
        await redis.aclose()

    return metrics
