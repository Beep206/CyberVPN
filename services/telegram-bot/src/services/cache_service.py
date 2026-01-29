"""CyberVPN Telegram Bot — Redis cache service.

Provides typed cache operations for user data, subscription plans,
and bot configuration with TTL management and graceful error handling.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import orjson
import structlog
from redis.asyncio import Redis
from redis.exceptions import RedisError

if TYPE_CHECKING:
    from src.config import RedisSettings

logger = structlog.get_logger(__name__)


class CacheService:
    """Redis-backed cache layer with typed accessors and TTL management.

    All read operations return None on cache miss or Redis errors.
    All write operations log errors but don't raise exceptions.
    This ensures the bot continues operating even if Redis is unavailable.
    """

    def __init__(self, redis: Redis, key_prefix: str = "cybervpn:bot:") -> None:
        self._redis = redis
        self._prefix = key_prefix

    @classmethod
    async def from_settings(cls, settings: RedisSettings) -> CacheService:
        """Create CacheService from RedisSettings.

        Args:
            settings: Redis connection settings.

        Returns:
            Configured CacheService instance.
        """
        redis = Redis.from_url(
            settings.dsn,
            password=(
                settings.password.get_secret_value()
                if settings.password
                else None
            ),
            decode_responses=True,
        )
        return cls(redis=redis, key_prefix=settings.key_prefix)

    def _key(self, *parts: str) -> str:
        """Build a namespaced cache key."""
        return self._prefix + ":".join(parts)

    # ── Generic operations ───────────────────────────────────────────────

    async def get(self, key: str) -> str | None:
        """Get a raw string value from cache.

        Args:
            key: Cache key (will be prefixed).

        Returns:
            Cached value or None on miss/error.
        """
        try:
            return await self._redis.get(self._key(key))
        except RedisError:
            logger.exception("cache_get_error", key=key)
            return None

    async def set(
        self,
        key: str,
        value: str,
        ttl: int | None = None,
    ) -> None:
        """Set a raw string value in cache.

        Args:
            key: Cache key (will be prefixed).
            value: String value to store.
            ttl: Time-to-live in seconds (None = no expiry).
        """
        try:
            await self._redis.set(self._key(key), value, ex=ttl)
        except RedisError:
            logger.exception("cache_set_error", key=key)

    async def delete(self, key: str) -> None:
        """Delete a cache key.

        Args:
            key: Cache key to delete (will be prefixed).
        """
        try:
            await self._redis.delete(self._key(key))
        except RedisError:
            logger.exception("cache_delete_error", key=key)

    async def get_json(self, key: str) -> Any | None:
        """Get a JSON-deserialized value from cache.

        Args:
            key: Cache key.

        Returns:
            Deserialized Python object or None.
        """
        raw = await self.get(key)
        if raw is None:
            return None
        try:
            return orjson.loads(raw)
        except orjson.JSONDecodeError:
            logger.exception("cache_json_decode_error", key=key)
            return None

    async def set_json(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> None:
        """Set a JSON-serialized value in cache.

        Args:
            key: Cache key.
            value: Python object to serialize and store.
            ttl: Time-to-live in seconds.
        """
        try:
            raw = orjson.dumps(value).decode("utf-8")
            await self.set(key, raw, ttl=ttl)
        except (TypeError, orjson.JSONEncodeError):
            logger.exception("cache_json_encode_error", key=key)

    # ── User cache ───────────────────────────────────────────────────────

    async def get_user(self, telegram_id: int) -> dict[str, Any] | None:
        """Get cached user data.

        Args:
            telegram_id: User's Telegram ID.

        Returns:
            User data dict or None.
        """
        return await self.get_json(f"user:{telegram_id}")

    async def set_user(
        self,
        telegram_id: int,
        user_data: dict[str, Any],
        ttl: int = 300,
    ) -> None:
        """Cache user data.

        Args:
            telegram_id: User's Telegram ID.
            user_data: User data to cache.
            ttl: Cache TTL in seconds (default: 5 minutes).
        """
        await self.set_json(f"user:{telegram_id}", user_data, ttl=ttl)

    async def invalidate_user(self, telegram_id: int) -> None:
        """Remove user data from cache.

        Args:
            telegram_id: User's Telegram ID.
        """
        await self.delete(f"user:{telegram_id}")

    # ── Plans cache ──────────────────────────────────────────────────────

    async def get_plans(self) -> list[dict[str, Any]] | None:
        """Get cached subscription plans.

        Returns:
            List of plan dicts or None.
        """
        return await self.get_json("plans")

    async def set_plans(
        self,
        plans: list[dict[str, Any]],
        ttl: int = 600,
    ) -> None:
        """Cache subscription plans.

        Args:
            plans: Plan data to cache.
            ttl: Cache TTL in seconds (default: 10 minutes).
        """
        await self.set_json("plans", plans, ttl=ttl)

    async def invalidate_plans(self) -> None:
        """Remove plans from cache."""
        await self.delete("plans")

    # ── Bot config cache ─────────────────────────────────────────────────

    async def get_bot_config(self) -> dict[str, Any] | None:
        """Get cached bot configuration (access mode, conditions).

        Returns:
            Bot config dict or None.
        """
        return await self.get_json("bot_config")

    async def set_bot_config(
        self,
        config: dict[str, Any],
        ttl: int = 300,
    ) -> None:
        """Cache bot configuration.

        Args:
            config: Bot config data.
            ttl: Cache TTL in seconds (default: 5 minutes).
        """
        await self.set_json("bot_config", config, ttl=ttl)

    async def invalidate_bot_config(self) -> None:
        """Remove bot config from cache."""
        await self.delete("bot_config")

    # ── Lifecycle ────────────────────────────────────────────────────────

    async def ping(self) -> bool:
        """Check Redis connectivity.

        Returns:
            True if Redis is reachable.
        """
        try:
            return await self._redis.ping()
        except RedisError:
            return False

    async def close(self) -> None:
        """Close the Redis connection."""
        try:
            await self._redis.aclose()
        except RedisError:
            logger.exception("cache_close_error")
