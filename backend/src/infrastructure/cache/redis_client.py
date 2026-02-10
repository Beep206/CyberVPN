"""Redis/Valkey client for caching and session management."""

from collections.abc import AsyncGenerator

import redis.asyncio as redis

from src.config.settings import settings

# Redis connection pool
_redis_pool: redis.ConnectionPool | None = None


def get_redis_pool() -> redis.ConnectionPool:
    """Get or create Redis connection pool."""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = redis.ConnectionPool.from_url(
            settings.redis_url,
            max_connections=10,
            decode_responses=True,
        )
    return _redis_pool


async def get_redis() -> AsyncGenerator[redis.Redis]:
    """
    Dependency injection function for Redis client.

    Yields:
        redis.Redis: Async Redis client with 'cybervpn:' key prefix
    """
    pool = get_redis_pool()
    client = redis.Redis(connection_pool=pool)

    try:
        yield client
    finally:
        await client.aclose()


async def check_redis_connection() -> tuple[bool, float | None]:
    """
    Health check for Redis connection.

    Returns:
        tuple: (is_connected, response_time_ms)
    """
    import time

    pool = get_redis_pool()
    client = redis.Redis(connection_pool=pool)

    try:
        start = time.time()
        await client.ping()
        response_time = (time.time() - start) * 1000  # Convert to ms
        return True, response_time
    except Exception:
        return False, None
    finally:
        await client.aclose()


async def close_redis_pool() -> None:
    """Close Redis connection pool."""
    global _redis_pool
    if _redis_pool is not None:
        await _redis_pool.aclose()
        _redis_pool = None
