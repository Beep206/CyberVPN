"""Redis/Valkey client for caching and session management."""

import asyncio
import logging
from collections.abc import AsyncGenerator

import redis.asyncio as redis

from src.config.settings import settings

logger = logging.getLogger(__name__)

# Redis connection pool
_redis_pool: redis.ConnectionPool | None = None
_redis_pool_loop: asyncio.AbstractEventLoop | None = None


def get_redis_pool() -> redis.ConnectionPool:
    """Get or create Redis connection pool."""
    global _redis_pool, _redis_pool_loop

    current_loop: asyncio.AbstractEventLoop | None = None
    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        current_loop = None

    if _redis_pool is None or (current_loop is not None and _redis_pool_loop is not current_loop):
        _redis_pool = redis.BlockingConnectionPool.from_url(
            settings.redis_url,
            max_connections=settings.redis_max_connections,
            timeout=settings.redis_pool_wait_seconds,
            decode_responses=True,
        )
        _redis_pool_loop = current_loop
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


async def get_redis_client() -> redis.Redis:
    """Create a short-lived Redis client bound to the shared connection pool."""
    return redis.Redis(connection_pool=get_redis_pool())


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
    except Exception as e:
        logger.warning("Redis health check ping failed: %s", e)
        return False, None
    finally:
        await client.aclose()


async def close_redis_pool() -> None:
    """Close Redis connection pool."""
    global _redis_pool, _redis_pool_loop
    if _redis_pool is not None:
        await _redis_pool.aclose()
        _redis_pool = None
        _redis_pool_loop = None
