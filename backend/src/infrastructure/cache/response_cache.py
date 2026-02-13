"""Redis-backed response cache for API endpoints."""

import json
import logging
from collections.abc import Callable, Coroutine
from typing import Any

import redis.asyncio as redis

from src.infrastructure.cache.redis_client import get_redis_pool

logger = logging.getLogger(__name__)


class ResponseCache:
    """Simple Redis cache with TTL for API response caching."""

    _PREFIX = "cache:"

    def __init__(self) -> None:
        self._redis: redis.Redis | None = None

    def _get_redis(self) -> redis.Redis:
        if self._redis is None:
            pool = get_redis_pool()
            self._redis = redis.Redis(connection_pool=pool)
        return self._redis

    async def get_or_fetch(
        self,
        key: str,
        ttl: int,
        fetch_fn: Callable[[], Coroutine[Any, Any, Any]],
    ) -> Any:
        """Return cached value or call fetch_fn, cache result, and return it."""
        full_key = f"{self._PREFIX}{key}"
        client = self._get_redis()
        try:
            cached = await client.get(full_key)
            if cached is not None:
                return json.loads(cached)
        except Exception:
            logger.warning("Cache read failed for %s, falling through", full_key)

        result = await fetch_fn()

        try:
            await client.setex(full_key, ttl, json.dumps(result, default=str))
        except Exception:
            logger.warning("Cache write failed for %s", full_key)

        return result

    async def invalidate(self, *keys: str) -> None:
        """Delete one or more cache keys."""
        client = self._get_redis()
        full_keys = [f"{self._PREFIX}{k}" for k in keys]
        try:
            await client.delete(*full_keys)
        except Exception:
            logger.warning("Cache invalidation failed for %s", full_keys)


# Module-level singleton
response_cache = ResponseCache()
