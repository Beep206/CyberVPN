"""Redis cache service with key prefixing and JSON serialization.

Provides a high-level wrapper around Redis operations with automatic key prefixing,
JSON serialization using orjson, and structured logging for all cache operations.
"""

from typing import Any

import orjson
import structlog
from redis.asyncio import Redis
from redis.exceptions import RedisError

from src.utils.constants import REDIS_PREFIX

logger = structlog.get_logger(__name__)


class CacheService:
    """Redis cache service with automatic key prefixing and JSON serialization.

    All keys are automatically prefixed with REDIS_PREFIX ("cybervpn:") to namespace
    cache entries. Values are serialized/deserialized using orjson for performance.

    Args:
        redis: AsyncIO Redis client instance
    """

    def __init__(self, redis: Redis) -> None:
        """Initialize cache service with Redis client."""
        self._redis = redis
        self._prefix = REDIS_PREFIX

    def _make_key(self, key: str) -> str:
        """Prepend Redis prefix to key.

        Args:
            key: Base key name

        Returns:
            Prefixed key name
        """
        if key.startswith(self._prefix):
            return key
        return f"{self._prefix}{key}"

    def _serialize(self, value: dict | list) -> bytes:
        """Serialize value to JSON bytes using orjson.

        Args:
            value: Dictionary or list to serialize

        Returns:
            JSON bytes
        """
        return orjson.dumps(value)

    def _deserialize(self, data: bytes | str | None) -> dict | None:
        """Deserialize JSON bytes to dict using orjson.

        Args:
            data: JSON bytes or string

        Returns:
            Deserialized dictionary or None if data is None
        """
        if data is None:
            return None
        return orjson.loads(data)

    async def get(self, key: str) -> dict | None:
        """Get value from cache with JSON deserialization.

        Args:
            key: Cache key (will be prefixed)

        Returns:
            Deserialized dictionary or None if key doesn't exist

        Raises:
            RedisError: On Redis operation failure
        """
        prefixed_key = self._make_key(key)
        try:
            data = await self._redis.get(prefixed_key)
            result = self._deserialize(data)
            logger.debug("cache.get", key=key, hit=result is not None)
            return result
        except RedisError as e:
            logger.error("cache.get.failed", key=key, error=str(e))
            raise

    async def set(self, key: str, value: dict | list, ttl: int | None = None) -> None:
        """Set value in cache with JSON serialization.

        Args:
            key: Cache key (will be prefixed)
            value: Dictionary or list to cache
            ttl: Optional TTL in seconds

        Raises:
            RedisError: On Redis operation failure
        """
        prefixed_key = self._make_key(key)
        try:
            serialized = self._serialize(value)
            await self._redis.set(prefixed_key, serialized, ex=ttl)
            logger.debug("cache.set", key=key, ttl=ttl)
        except RedisError as e:
            logger.error("cache.set.failed", key=key, error=str(e))
            raise

    async def delete(self, key: str) -> bool:
        """Delete key from cache.

        Args:
            key: Cache key (will be prefixed)

        Returns:
            True if key was deleted, False if key didn't exist

        Raises:
            RedisError: On Redis operation failure
        """
        prefixed_key = self._make_key(key)
        try:
            result = await self._redis.delete(prefixed_key)
            deleted = result > 0
            logger.debug("cache.delete", key=key, deleted=deleted)
            return deleted
        except RedisError as e:
            logger.error("cache.delete.failed", key=key, error=str(e))
            raise

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache.

        Args:
            key: Cache key (will be prefixed)

        Returns:
            True if key exists, False otherwise

        Raises:
            RedisError: On Redis operation failure
        """
        prefixed_key = self._make_key(key)
        try:
            result = await self._redis.exists(prefixed_key)
            exists = result > 0
            logger.debug("cache.exists", key=key, exists=exists)
            return exists
        except RedisError as e:
            logger.error("cache.exists.failed", key=key, error=str(e))
            raise

    async def get_many(self, keys: list[str]) -> list[dict | None]:
        """Get multiple values from cache with JSON deserialization.

        Args:
            keys: List of cache keys (will be prefixed)

        Returns:
            List of deserialized dictionaries (None for missing keys)

        Raises:
            RedisError: On Redis operation failure
        """
        if not keys:
            return []

        prefixed_keys = [self._make_key(key) for key in keys]
        try:
            data_list = await self._redis.mget(prefixed_keys)
            results = [self._deserialize(data) for data in data_list]
            hits = sum(1 for r in results if r is not None)
            logger.debug("cache.get_many", count=len(keys), hits=hits)
            return results
        except RedisError as e:
            logger.error("cache.get_many.failed", count=len(keys), error=str(e))
            raise

    async def set_many(self, mapping: dict[str, dict], ttl: int | None = None) -> None:
        """Set multiple values in cache with JSON serialization.

        Uses Redis pipeline for atomic batch operations. If TTL is provided,
        each key gets the same expiration time.

        Args:
            mapping: Dictionary of key-value pairs to cache
            ttl: Optional TTL in seconds for all keys

        Raises:
            RedisError: On Redis operation failure
        """
        if not mapping:
            return

        try:
            async with self._redis.pipeline(transaction=False) as pipe:
                for key, value in mapping.items():
                    prefixed_key = self._make_key(key)
                    serialized = self._serialize(value)
                    pipe.set(prefixed_key, serialized, ex=ttl)
                await pipe.execute()
            logger.debug("cache.set_many", count=len(mapping), ttl=ttl)
        except RedisError as e:
            logger.error("cache.set_many.failed", count=len(mapping), error=str(e))
            raise

    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment numeric value in cache.

        Args:
            key: Cache key (will be prefixed)
            amount: Amount to increment by (default: 1)

        Returns:
            New value after increment

        Raises:
            RedisError: On Redis operation failure
        """
        prefixed_key = self._make_key(key)
        try:
            result = await self._redis.incrby(prefixed_key, amount)
            logger.debug("cache.increment", key=key, amount=amount, new_value=result)
            return result
        except RedisError as e:
            logger.error("cache.increment.failed", key=key, error=str(e))
            raise

    async def add_to_sorted_set(self, key: str, mapping: dict[str, float]) -> int:
        """Add members to sorted set with scores.

        Args:
            key: Sorted set key (will be prefixed)
            mapping: Dictionary of member names to scores

        Returns:
            Number of new members added (not updated)

        Raises:
            RedisError: On Redis operation failure
        """
        prefixed_key = self._make_key(key)
        try:
            result = await self._redis.zadd(prefixed_key, mapping)
            logger.debug("cache.zadd", key=key, added=result, total_members=len(mapping))
            return result
        except RedisError as e:
            logger.error("cache.zadd.failed", key=key, error=str(e))
            raise

    async def get_sorted_set_range(
        self, key: str, start: int = 0, end: int = -1, withscores: bool = False
    ) -> list[Any]:
        """Get range of members from sorted set.

        Args:
            key: Sorted set key (will be prefixed)
            start: Start index (default: 0)
            end: End index (default: -1 for all)
            withscores: Include scores in result (default: False)

        Returns:
            List of members, or list of (member, score) tuples if withscores=True

        Raises:
            RedisError: On Redis operation failure
        """
        prefixed_key = self._make_key(key)
        try:
            result = await self._redis.zrange(prefixed_key, start, end, withscores=withscores)
            logger.debug("cache.zrange", key=key, count=len(result), withscores=withscores)
            return result
        except RedisError as e:
            logger.error("cache.zrange.failed", key=key, error=str(e))
            raise

    async def scan_keys(self, pattern: str) -> list[str]:
        """Scan for keys matching pattern using SCAN command.

        Uses SCAN instead of KEYS for production safety. Pattern is automatically
        prefixed with REDIS_PREFIX. Returns keys with prefix removed.

        Args:
            pattern: Key pattern (will be prefixed, supports * and ? wildcards)

        Returns:
            List of matching keys (with prefix removed)

        Raises:
            RedisError: On Redis operation failure
        """
        prefixed_pattern = self._make_key(pattern)
        keys = []

        try:
            cursor = 0
            while True:
                cursor, batch = await self._redis.scan(cursor=cursor, match=prefixed_pattern, count=100)
                # Remove prefix from returned keys
                for key in batch:
                    decoded = key.decode("utf-8") if isinstance(key, bytes) else key
                    keys.append(decoded.removeprefix(self._prefix))
                if cursor == 0:
                    break
            logger.debug("cache.scan", pattern=pattern, found=len(keys))
            return keys
        except RedisError as e:
            logger.error("cache.scan.failed", pattern=pattern, error=str(e))
            raise

    async def set_if_not_exists(self, key: str, value: dict, ttl: int | None = None) -> bool:
        """Set value only if key doesn't exist (SET NX).

        Args:
            key: Cache key (will be prefixed)
            value: Dictionary to cache
            ttl: Optional TTL in seconds

        Returns:
            True if key was set, False if key already existed

        Raises:
            RedisError: On Redis operation failure
        """
        prefixed_key = self._make_key(key)
        try:
            serialized = self._serialize(value)
            result = await self._redis.set(prefixed_key, serialized, ex=ttl, nx=True)
            success = result is not None
            logger.debug("cache.setnx", key=key, set=success, ttl=ttl)
            return success
        except RedisError as e:
            logger.error("cache.setnx.failed", key=key, error=str(e))
            raise
