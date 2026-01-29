import json
from typing import Any

import redis.asyncio as redis


class CacheService:
    PREFIX = "cybervpn:"

    def __init__(self, redis_client: redis.Redis) -> None:
        self._redis = redis_client

    def _key(self, key: str) -> str:
        return f"{self.PREFIX}{key}"

    async def get(self, key: str) -> Any | None:
        data = await self._redis.get(self._key(key))
        if data is None:
            return None
        return json.loads(data)

    async def set(self, key: str, value: Any, ttl: int = 300) -> None:
        await self._redis.set(self._key(key), json.dumps(value, default=str), ex=ttl)

    async def delete(self, key: str) -> None:
        await self._redis.delete(self._key(key))

    async def exists(self, key: str) -> bool:
        return bool(await self._redis.exists(self._key(key)))

    async def increment(self, key: str, amount: int = 1) -> int:
        return await self._redis.incrby(self._key(key), amount)

    async def set_hash(self, key: str, mapping: dict, ttl: int = 300) -> None:
        k = self._key(key)
        await self._redis.hset(k, mapping=mapping)
        await self._redis.expire(k, ttl)

    async def get_hash(self, key: str) -> dict:
        return await self._redis.hgetall(self._key(key))

    async def invalidate_pattern(self, pattern: str) -> int:
        keys = []
        async for key in self._redis.scan_iter(match=self._key(pattern)):
            keys.append(key)
        if keys:
            return await self._redis.delete(*keys)
        return 0
