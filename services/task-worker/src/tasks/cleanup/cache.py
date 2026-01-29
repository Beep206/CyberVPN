"""Invalidate stale Redis cache keys using SCAN + UNLINK."""

from datetime import datetime, timedelta, timezone

import structlog

from src.broker import broker
from src.services.redis_client import get_redis_client
from src.utils.constants import REDIS_PREFIX

logger = structlog.get_logger(__name__)


@broker.task(task_name="cleanup_cache", queue="cleanup")
async def cleanup_cache() -> dict:
    """Invalidate stale Redis cache keys using SCAN + UNLINK (never KEYS).

    Removes cache entries based on retention policies:
    - cybervpn:cache:* - General cache (stale entries only)
    - cybervpn:stats:daily:* - Daily stats older than 90 days
    - cybervpn:health:*:history - Health history older than 7 days
    - cybervpn:bandwidth:* - Raw bandwidth data older than 48h, hourly older than 30 days

    Uses SCAN for iteration to avoid blocking Redis, and UNLINK for async deletion.
    """
    redis = get_redis_client()
    now = datetime.now(timezone.utc)
    total_deleted = 0

    try:
        # Pattern 1: Daily stats older than 90 days
        stats_cutoff = now - timedelta(days=90)
        stats_deleted = await _scan_and_delete_by_date(
            redis, f"{REDIS_PREFIX}stats:daily:*", stats_cutoff, date_format="%Y-%m-%d"
        )
        total_deleted += stats_deleted

        # Pattern 1.1: General cache entries
        cache_deleted = await _scan_and_delete_pattern(redis, f"{REDIS_PREFIX}cache:*")
        total_deleted += cache_deleted

        # Pattern 2: Health history older than 7 days
        health_cutoff = now - timedelta(days=7)
        health_deleted = await _cleanup_health_history(redis, health_cutoff)
        total_deleted += health_deleted

        # Pattern 3: Raw bandwidth data older than 48 hours
        bandwidth_raw_cutoff = now - timedelta(hours=48)
        bandwidth_raw_deleted = await _scan_and_delete_by_timestamp(
            redis,
            f"{REDIS_PREFIX}bandwidth:*",
            bandwidth_raw_cutoff,
            exclude_substring=":bandwidth:hourly:",
        )
        total_deleted += bandwidth_raw_deleted

        # Pattern 4: Hourly bandwidth aggregates older than 30 days
        bandwidth_hourly_cutoff = now - timedelta(days=30)
        bandwidth_hourly_deleted = await _scan_and_delete_by_timestamp(
            redis, f"{REDIS_PREFIX}bandwidth:hourly:*", bandwidth_hourly_cutoff
        )
        total_deleted += bandwidth_hourly_deleted

        logger.info(
            "cache_cleanup_complete",
            total_deleted=total_deleted,
            stats_deleted=stats_deleted,
            cache_deleted=cache_deleted,
            health_deleted=health_deleted,
            bandwidth_raw_deleted=bandwidth_raw_deleted,
            bandwidth_hourly_deleted=bandwidth_hourly_deleted,
        )
    finally:
        await redis.aclose()

    return {
        "total_deleted": total_deleted,
        "stats_deleted": stats_deleted,
        "cache_deleted": cache_deleted,
        "health_deleted": health_deleted,
        "bandwidth_raw_deleted": bandwidth_raw_deleted,
        "bandwidth_hourly_deleted": bandwidth_hourly_deleted,
    }


async def _scan_and_delete_pattern(redis, pattern: str) -> int:
    """Scan and delete all keys matching pattern."""
    deleted = 0
    cursor = 0

    while True:
        cursor, keys = await redis.scan(cursor, match=pattern, count=100)
        if keys:
            deleted += await redis.unlink(*keys)
        if cursor == 0:
            break

    return deleted


async def _scan_and_delete_by_date(redis, pattern: str, cutoff: datetime, date_format: str = "%Y-%m-%d") -> int:
    """Scan keys with date suffix and delete those older than cutoff."""
    deleted = 0
    cursor = 0

    while True:
        cursor, keys = await redis.scan(cursor, match=pattern, count=100)
        for key in keys:
            key_str = key.decode("utf-8") if isinstance(key, bytes) else key
            try:
                # Extract date from key (assumes format like "prefix:YYYY-MM-DD")
                date_part = key_str.split(":")[-1]
                key_date = datetime.strptime(date_part, date_format).replace(tzinfo=timezone.utc)
                if key_date < cutoff:
                    deleted += await redis.unlink(key)
            except (ValueError, IndexError):
                # Skip keys that don't match expected format
                continue
        if cursor == 0:
            break

    return deleted


async def _scan_and_delete_by_timestamp(
    redis, pattern: str, cutoff: datetime, exclude_substring: str | None = None
) -> int:
    """Scan keys with Unix timestamp suffix and delete those older than cutoff."""
    deleted = 0
    cursor = 0
    cutoff_ts = int(cutoff.timestamp())

    while True:
        cursor, keys = await redis.scan(cursor, match=pattern, count=100)
        for key in keys:
            key_str = key.decode("utf-8") if isinstance(key, bytes) else key
            if exclude_substring and exclude_substring in key_str:
                continue
            try:
                # Extract timestamp from key (assumes format like "prefix:node_uuid:1234567890")
                timestamp_part = key_str.split(":")[-1]
                key_ts = int(timestamp_part)
                if key_ts < cutoff_ts:
                    deleted += await redis.unlink(key)
            except (ValueError, IndexError):
                # Skip keys that don't match expected format
                continue
        if cursor == 0:
            break

    return deleted


async def _cleanup_health_history(redis, cutoff: datetime) -> int:
    """Remove health history entries older than cutoff from sorted sets."""
    deleted = 0
    cursor = 0
    cutoff_ts = int(cutoff.timestamp())

    while True:
        cursor, keys = await redis.scan(cursor, match=f"{REDIS_PREFIX}health:*:history", count=100)
        for key in keys:
            removed = await redis.zremrangebyscore(key, 0, cutoff_ts)
            deleted += removed
            if await redis.zcard(key) == 0:
                await redis.unlink(key)
        if cursor == 0:
            break

    return deleted
