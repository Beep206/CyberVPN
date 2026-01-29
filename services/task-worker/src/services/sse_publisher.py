"""Server-Sent Events (SSE) publisher via Redis pub/sub.

Publishes real-time events to a Redis channel that SSE endpoints can subscribe to.
Used for pushing updates to admin dashboard and client applications.
"""

import json

import structlog

from src.services.redis_client import get_redis_client

logger = structlog.get_logger(__name__)

# Redis pub/sub channel for SSE events
SSE_CHANNEL = "cybervpn:sse:events"


async def publish_event(event_type: str, data: dict) -> None:
    """Publish SSE event to Redis pub/sub channel.

    Args:
        event_type: Type of event (e.g., "user_created", "server_updated", "payment_received")
        data: Event payload data

    Raises:
        Exception: If Redis publish fails
    """
    redis = get_redis_client()
    try:
        payload = json.dumps({
            "type": event_type,
            "data": data,
        })
        subscribers = await redis.publish(SSE_CHANNEL, payload)
        logger.debug(
            "sse_event_published",
            event_type=event_type,
            subscribers=subscribers,
            channel=SSE_CHANNEL,
        )
    except Exception as e:
        logger.error(
            "sse_event_publish_failed",
            event_type=event_type,
            error=str(e),
        )
        raise
    finally:
        await redis.aclose()
