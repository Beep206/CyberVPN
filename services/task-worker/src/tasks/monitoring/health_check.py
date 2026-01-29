"""VPN node health check task."""

import json
from datetime import datetime, timezone

import structlog

from src.broker import broker
from src.services.cache_service import CacheService
from src.services.redis_client import get_redis_client
from src.services.remnawave_client import RemnawaveClient
from src.services.sse_publisher import publish_event
from src.services.telegram_client import TelegramClient
from src.utils.constants import HEALTH_HISTORY_KEY, HEALTH_KEY
from src.utils.formatting import server_down, server_recovered

logger = structlog.get_logger(__name__)


@broker.task(task_name="check_server_health", queue="monitoring")
async def check_server_health() -> dict:
    """Check health of all VPN nodes via Remnawave API.

    Queries all nodes from the Remnawave API, compares their online/offline status
    to the previous state stored in Redis, and sends Telegram alerts when nodes
    go down or come back online.

    Returns:
        Dictionary with nodes_checked and alerts_sent counts
    """
    redis = get_redis_client()
    cache = CacheService(redis)
    alerts_sent = 0
    nodes_checked = 0

    try:
        async with RemnawaveClient() as client:
            nodes = await client.get_nodes()

        now_ts = int(datetime.now(timezone.utc).timestamp())
        async with TelegramClient() as tg:
            for node in nodes:
                node_uuid = node.get("uuid", "")
                node_name = node.get("name", "unknown")
                is_connected = node.get("isConnected", False)
                is_disabled = node.get("isDisabled", False)
                is_connecting = node.get("isConnecting", False)
                country = node.get("countryCode", "??")
                nodes_checked += 1

                if is_disabled:
                    status = "maintenance"
                elif is_connected:
                    status = "online"
                elif is_connecting:
                    status = "warning"
                else:
                    status = "offline"

                # Get previous state
                health_key = HEALTH_KEY.format(node_uuid=node_uuid)
                prev = await cache.get(health_key)
                prev_data = prev if isinstance(prev, dict) else {}
                prev_status = prev_data.get("status", "online")
                last_seen = prev_data.get("last_seen", now_ts)
                offline_since = prev_data.get("offline_since")

                if status == "online":
                    last_seen = now_ts
                    offline_since = None
                elif status == "offline":
                    if prev_status != "offline":
                        offline_since = now_ts
                    else:
                        offline_since = prev_data.get("offline_since", now_ts)

                # Save current state
                await cache.set(
                    health_key,
                    {
                        "status": status,
                        "is_online": status == "online",
                        "name": node_name,
                        "country": country,
                        "last_seen": last_seen,
                        "offline_since": offline_since,
                        "updated_at": now_ts,
                    },
                    ttl=300,
                )

                # Detect state change
                if prev_status != status:
                    history_key = HEALTH_HISTORY_KEY.format(node_uuid=node_uuid)
                    history_entry = json.dumps(
                        {
                            "status": status,
                            "timestamp": now_ts,
                            "name": node_name,
                            "country": country,
                        }
                    )
                    await cache.add_to_sorted_set(history_key, {history_entry: float(now_ts)})

                    try:
                        await publish_event(
                            "server.status_changed",
                            {
                                "node_uuid": node_uuid,
                                "name": node_name,
                                "country": country,
                                "status": status,
                                "previous_status": prev_status,
                                "timestamp": now_ts,
                            },
                        )
                    except Exception:
                        logger.warning("health_sse_publish_failed", node_uuid=node_uuid)

                if prev_status == "online" and status == "offline":
                    alert = server_down(node_name, country)
                    await tg.send_admin_alert(alert, severity="critical")
                    alerts_sent += 1
                    logger.warning("server_went_offline", node=node_name, country=country)
                elif prev_status == "offline" and status == "online":
                    alert = server_recovered(node_name, country)
                    await tg.send_admin_alert(alert, severity="resolved")
                    alerts_sent += 1
                    logger.info("server_recovered", node=node_name, country=country)
    finally:
        await redis.aclose()

    logger.info("health_check_complete", nodes_checked=nodes_checked, alerts_sent=alerts_sent)
    return {"nodes_checked": nodes_checked, "alerts_sent": alerts_sent}
