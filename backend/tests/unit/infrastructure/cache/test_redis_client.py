import pytest

from src.config.settings import settings
from src.infrastructure.cache import redis_client


@pytest.mark.asyncio
async def test_get_redis_pool_uses_blocking_pool_with_configured_budget():
    original_max_connections = settings.redis_max_connections
    original_wait_seconds = settings.redis_pool_wait_seconds

    await redis_client.close_redis_pool()
    object.__setattr__(settings, "redis_max_connections", 123)
    object.__setattr__(settings, "redis_pool_wait_seconds", 7.0)

    try:
        pool = redis_client.get_redis_pool()

        assert type(pool).__name__ == "BlockingConnectionPool"
        assert pool.max_connections == 123
        assert pool.timeout == 7.0
    finally:
        await redis_client.close_redis_pool()
        object.__setattr__(settings, "redis_max_connections", original_max_connections)
        object.__setattr__(settings, "redis_pool_wait_seconds", original_wait_seconds)
