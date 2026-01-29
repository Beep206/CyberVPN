"""Sync user statistics summary to Redis cache."""

import json

import structlog

from src.broker import broker
from src.services.cache_service import CacheService
from src.services.redis_client import get_redis_client
from src.services.remnawave_client import RemnawaveClient
from src.utils.constants import USER_STATS_KEY

logger = structlog.get_logger(__name__)


@broker.task(task_name="sync_user_stats", queue="sync")
async def sync_user_stats() -> dict:
    """Sync user statistics summary to Redis cache.

    Fetches all users from Remnawave API and calculates aggregated statistics:
    - total: total user count
    - active: users with status=active
    - disabled: users with status=disabled
    - expired: users with expiration in the past
    - limited: users with data_limit reached
    - online: users currently connected

    Caches results in Redis under USER_STATS_KEY with 15-minute TTL.

    Returns:
        Dictionary with user stats
    """
    redis = get_redis_client()
    cache = CacheService(redis)
    stats = {
        "total": 0,
        "active": 0,
        "disabled": 0,
        "expired": 0,
        "limited": 0,
        "online": 0,
    }

    try:
        async with RemnawaveClient() as rw:
            users = await rw.get_users()

        stats["total"] = len(users)

        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)

        for user in users:
            status = user.get("status", "")
            is_online = user.get("isOnline", False)
            expire_at = user.get("expiresAt")
            data_limit = user.get("dataLimit", 0)
            data_used = user.get("dataUsed", 0)

            # Count by status
            if status == "active":
                stats["active"] += 1
            elif status == "disabled":
                stats["disabled"] += 1

            # Check expiration
            if expire_at:
                try:
                    exp_dt = datetime.fromisoformat(expire_at.replace("Z", "+00:00"))
                    if exp_dt < now:
                        stats["expired"] += 1
                except (ValueError, TypeError):
                    pass

            # Check data limit
            if data_limit > 0 and data_used >= data_limit:
                stats["limited"] += 1

            # Count online
            if is_online:
                stats["online"] += 1

        # Cache in Redis with 15-minute TTL
        await cache.set(USER_STATS_KEY, stats, ttl=900)

        logger.info("user_stats_synced", **stats)

    except Exception as e:
        logger.exception("user_stats_sync_failed", error=str(e))
        raise
    finally:
        await redis.aclose()

    return stats
