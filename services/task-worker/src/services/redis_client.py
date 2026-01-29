"""Redis async client management for task-worker microservice.

Provides Redis connectivity with lazy initialization:
- Connection pool with max_connections=20 and decode_responses=True
- Redis client factory using from_pool for proper ownership/cleanup
- Singleton pattern using lru_cache for performance
- Health check functionality via PING
"""

from functools import lru_cache

import structlog
from redis.asyncio import ConnectionPool, Redis

from src.config import get_settings

logger = structlog.get_logger(__name__)


@lru_cache
def get_redis_pool() -> ConnectionPool:
    """Create and cache the async Redis connection pool.

    Lazy initialization ensures the pool is only created when first needed,
    not at module import time. Uses connection pooling for production performance.
    """
    settings = get_settings()
    return ConnectionPool.from_url(
        settings.redis_url,
        max_connections=20,
        decode_responses=True,
        encoding="utf-8",
        socket_keepalive=True,
        socket_connect_timeout=5,
        retry_on_timeout=True,
    )


def get_redis_client() -> Redis:
    """Create Redis client from the connection pool.

    Returns a new Redis instance bound to the cached pool. Each call creates
    a new client instance but shares the underlying pool for efficient connection reuse.
    Use this for dependency injection or context managers.
    """
    return Redis.from_pool(get_redis_pool())


async def check_redis() -> bool:
    """Check Redis connectivity by executing PING.

    Returns True if Redis is accessible and responsive, False otherwise.
    """
    client = get_redis_client()
    try:
        await client.ping()
        return True
    except Exception as exc:
        logger.warning("redis_health_check_failed", error=str(exc))
        return False
    finally:
        await client.aclose()


async def shutdown_redis_pool() -> None:
    """Close the Redis connection pool during application shutdown.

    Call this during graceful shutdown to release all connections and resources.
    """
    try:
        pool = get_redis_pool()
        await pool.aclose()
        logger.info("redis_pool_closed")
    except Exception as exc:
        logger.error("redis_pool_shutdown_error", error=str(exc))
