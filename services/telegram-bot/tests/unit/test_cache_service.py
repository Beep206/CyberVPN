"""Unit tests for CacheService."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from redis.exceptions import RedisError

from src.services.cache_service import CacheService

if TYPE_CHECKING:
    import fakeredis.aioredis


@pytest.mark.asyncio
class TestCacheServiceBasicOperations:
    """Test basic cache operations."""

    async def test_get_set_string(self, fake_redis: fakeredis.aioredis.FakeRedis) -> None:
        """Test basic get/set operations."""
        cache = CacheService(redis=fake_redis, key_prefix="test:")

        await cache.set("mykey", "myvalue")
        result = await cache.get("mykey")

        assert result == "myvalue"

    async def test_get_nonexistent_returns_none(
        self, fake_redis: fakeredis.aioredis.FakeRedis
    ) -> None:
        """Test that getting non-existent key returns None."""
        cache = CacheService(redis=fake_redis)

        result = await cache.get("does_not_exist")
        assert result is None

    async def test_delete_key(self, fake_redis: fakeredis.aioredis.FakeRedis) -> None:
        """Test deleting a cache key."""
        cache = CacheService(redis=fake_redis)

        await cache.set("key_to_delete", "value")
        await cache.delete("key_to_delete")

        result = await cache.get("key_to_delete")
        assert result is None

    async def test_key_prefixing(self, fake_redis: fakeredis.aioredis.FakeRedis) -> None:
        """Test that keys are properly prefixed."""
        cache = CacheService(redis=fake_redis, key_prefix="app:")

        await cache.set("test", "value")

        # Direct Redis check with prefix
        raw_value = await fake_redis.get("app:test")
        assert raw_value == "value"


@pytest.mark.asyncio
class TestCacheServiceTTL:
    """Test TTL (time-to-live) behavior."""

    async def test_set_with_ttl(self, fake_redis: fakeredis.aioredis.FakeRedis) -> None:
        """Test setting value with TTL."""
        cache = CacheService(redis=fake_redis)

        await cache.set("temp_key", "temp_value", ttl=60)

        # Check that TTL is set
        ttl = await fake_redis.ttl(cache._key("temp_key"))
        assert ttl > 0
        assert ttl <= 60

    async def test_set_without_ttl_no_expiry(
        self, fake_redis: fakeredis.aioredis.FakeRedis
    ) -> None:
        """Test setting value without TTL doesn't expire."""
        cache = CacheService(redis=fake_redis)

        await cache.set("permanent_key", "value")

        # Check no TTL (-1 means no expiry)
        ttl = await fake_redis.ttl(cache._key("permanent_key"))
        assert ttl == -1


@pytest.mark.asyncio
class TestCacheServiceJSON:
    """Test JSON serialization operations."""

    async def test_set_get_json_dict(
        self, fake_redis: fakeredis.aioredis.FakeRedis
    ) -> None:
        """Test storing and retrieving JSON dict."""
        cache = CacheService(redis=fake_redis)

        data = {"user_id": 123, "name": "Test User", "active": True}
        await cache.set_json("user_data", data)

        result = await cache.get_json("user_data")
        assert result == data

    async def test_set_get_json_list(
        self, fake_redis: fakeredis.aioredis.FakeRedis
    ) -> None:
        """Test storing and retrieving JSON list."""
        cache = CacheService(redis=fake_redis)

        data = [1, 2, 3, "four", {"five": 5}]
        await cache.set_json("list_data", data)

        result = await cache.get_json("list_data")
        assert result == data

    async def test_get_json_nonexistent_returns_none(
        self, fake_redis: fakeredis.aioredis.FakeRedis
    ) -> None:
        """Test getting non-existent JSON key returns None."""
        cache = CacheService(redis=fake_redis)

        result = await cache.get_json("missing")
        assert result is None

    async def test_get_json_invalid_json_returns_none(
        self, fake_redis: fakeredis.aioredis.FakeRedis
    ) -> None:
        """Test that invalid JSON returns None."""
        cache = CacheService(redis=fake_redis)

        # Set invalid JSON directly
        await cache.set("bad_json", "{invalid json}")

        result = await cache.get_json("bad_json")
        assert result is None

    async def test_set_json_with_ttl(
        self, fake_redis: fakeredis.aioredis.FakeRedis
    ) -> None:
        """Test setting JSON with TTL."""
        cache = CacheService(redis=fake_redis)

        data = {"temp": True}
        await cache.set_json("temp_json", data, ttl=120)

        # Verify stored and has TTL
        result = await cache.get_json("temp_json")
        assert result == data

        ttl = await fake_redis.ttl(cache._key("temp_json"))
        assert ttl > 0


@pytest.mark.asyncio
class TestCacheServiceUserOperations:
    """Test user-specific cache operations."""

    async def test_set_get_user(self, fake_redis: fakeredis.aioredis.FakeRedis) -> None:
        """Test caching user data."""
        cache = CacheService(redis=fake_redis)

        user_data = {
            "telegram_id": 123456,
            "username": "testuser",
            "language": "ru",
            "status": "active",
        }

        await cache.set_user(123456, user_data, ttl=300)
        result = await cache.get_user(123456)

        assert result == user_data

    async def test_get_user_cache_miss(
        self, fake_redis: fakeredis.aioredis.FakeRedis
    ) -> None:
        """Test cache miss for user data."""
        cache = CacheService(redis=fake_redis)

        result = await cache.get_user(999999)
        assert result is None

    async def test_invalidate_user(
        self, fake_redis: fakeredis.aioredis.FakeRedis
    ) -> None:
        """Test invalidating user cache."""
        cache = CacheService(redis=fake_redis)

        user_data = {"telegram_id": 123456}
        await cache.set_user(123456, user_data)

        # Verify it's cached
        assert await cache.get_user(123456) is not None

        # Invalidate
        await cache.invalidate_user(123456)

        # Should be gone
        assert await cache.get_user(123456) is None

    async def test_user_cache_ttl(self, fake_redis: fakeredis.aioredis.FakeRedis) -> None:
        """Test user cache respects TTL."""
        cache = CacheService(redis=fake_redis)

        user_data = {"telegram_id": 123456}
        await cache.set_user(123456, user_data, ttl=600)

        # Check TTL is set
        ttl = await fake_redis.ttl(cache._key("user:123456"))
        assert ttl > 0
        assert ttl <= 600


@pytest.mark.asyncio
class TestCacheServicePlansOperations:
    """Test subscription plans cache operations."""

    async def test_set_get_plans(self, fake_redis: fakeredis.aioredis.FakeRedis) -> None:
        """Test caching subscription plans."""
        cache = CacheService(redis=fake_redis)

        plans = [
            {"id": "basic", "name": "Basic Plan", "price": 9.99},
            {"id": "pro", "name": "Pro Plan", "price": 19.99},
        ]

        await cache.set_plans(plans, ttl=600)
        result = await cache.get_plans()

        assert result == plans

    async def test_get_plans_cache_miss(
        self, fake_redis: fakeredis.aioredis.FakeRedis
    ) -> None:
        """Test cache miss for plans."""
        cache = CacheService(redis=fake_redis)

        result = await cache.get_plans()
        assert result is None

    async def test_invalidate_plans(
        self, fake_redis: fakeredis.aioredis.FakeRedis
    ) -> None:
        """Test invalidating plans cache."""
        cache = CacheService(redis=fake_redis)

        plans = [{"id": "test"}]
        await cache.set_plans(plans)

        # Verify cached
        assert await cache.get_plans() is not None

        # Invalidate
        await cache.invalidate_plans()

        # Should be gone
        assert await cache.get_plans() is None


@pytest.mark.asyncio
class TestCacheServiceBotConfig:
    """Test bot configuration cache operations."""

    async def test_set_get_bot_config(
        self, fake_redis: fakeredis.aioredis.FakeRedis
    ) -> None:
        """Test caching bot configuration."""
        cache = CacheService(redis=fake_redis)

        config = {
            "maintenance_mode": False,
            "allowed_users": [123, 456],
            "features": {"trial": True, "referral": True},
        }

        await cache.set_bot_config(config, ttl=300)
        result = await cache.get_bot_config()

        assert result == config

    async def test_invalidate_bot_config(
        self, fake_redis: fakeredis.aioredis.FakeRedis
    ) -> None:
        """Test invalidating bot config."""
        cache = CacheService(redis=fake_redis)

        config = {"test": True}
        await cache.set_bot_config(config)

        await cache.invalidate_bot_config()

        assert await cache.get_bot_config() is None


@pytest.mark.asyncio
class TestCacheServiceErrorHandling:
    """Test graceful error handling when Redis fails."""

    async def test_get_error_returns_none(
        self, fake_redis: fakeredis.aioredis.FakeRedis
    ) -> None:
        """Test that Redis errors on get return None."""
        cache = CacheService(redis=fake_redis)

        # Mock Redis error
        original_get = fake_redis.get

        async def failing_get(*args: Any, **kwargs: Any) -> None:
            raise RedisError("Connection failed")

        fake_redis.get = failing_get  # type: ignore[method-assign]

        # Should return None instead of raising
        result = await cache.get("any_key")
        assert result is None

        # Restore
        fake_redis.get = original_get  # type: ignore[method-assign]

    async def test_set_error_silent_fail(
        self, fake_redis: fakeredis.aioredis.FakeRedis
    ) -> None:
        """Test that Redis errors on set fail silently."""
        cache = CacheService(redis=fake_redis)

        original_set = fake_redis.set

        async def failing_set(*args: Any, **kwargs: Any) -> None:
            raise RedisError("Connection failed")

        fake_redis.set = failing_set  # type: ignore[method-assign]

        # Should not raise exception
        await cache.set("key", "value")

        # Restore
        fake_redis.set = original_set  # type: ignore[method-assign]

    async def test_delete_error_silent_fail(
        self, fake_redis: fakeredis.aioredis.FakeRedis
    ) -> None:
        """Test that Redis errors on delete fail silently."""
        cache = CacheService(redis=fake_redis)

        original_delete = fake_redis.delete

        async def failing_delete(*args: Any, **kwargs: Any) -> None:
            raise RedisError("Connection failed")

        fake_redis.delete = failing_delete  # type: ignore[method-assign]

        # Should not raise
        await cache.delete("key")

        # Restore
        fake_redis.delete = original_delete  # type: ignore[method-assign]


@pytest.mark.asyncio
class TestCacheServiceConnectivity:
    """Test cache service connectivity checks."""

    async def test_ping_success(self, fake_redis: fakeredis.aioredis.FakeRedis) -> None:
        """Test successful ping."""
        cache = CacheService(redis=fake_redis)

        result = await cache.ping()
        assert result is True

    async def test_ping_failure(self, fake_redis: fakeredis.aioredis.FakeRedis) -> None:
        """Test ping returns False on Redis error."""
        cache = CacheService(redis=fake_redis)

        original_ping = fake_redis.ping

        async def failing_ping(*args: Any, **kwargs: Any) -> None:
            raise RedisError("Connection lost")

        fake_redis.ping = failing_ping  # type: ignore[method-assign]

        result = await cache.ping()
        assert result is False

        # Restore
        fake_redis.ping = original_ping  # type: ignore[method-assign]

    async def test_close(self, fake_redis: fakeredis.aioredis.FakeRedis) -> None:
        """Test closing cache service."""
        cache = CacheService(redis=fake_redis)

        # Should not raise
        await cache.close()


@pytest.mark.asyncio
class TestCacheServiceIntegration:
    """Integration tests for cache service workflows."""

    async def test_user_workflow(self, fake_redis: fakeredis.aioredis.FakeRedis) -> None:
        """Test complete user caching workflow."""
        cache = CacheService(redis=fake_redis)

        user_id = 123456
        user_data = {
            "telegram_id": user_id,
            "username": "integration_test",
            "language": "en",
        }

        # Cache miss
        assert await cache.get_user(user_id) is None

        # Set user
        await cache.set_user(user_id, user_data)

        # Cache hit
        cached = await cache.get_user(user_id)
        assert cached == user_data

        # Update user (overwrite)
        user_data["language"] = "ru"
        await cache.set_user(user_id, user_data)

        updated = await cache.get_user(user_id)
        assert updated["language"] == "ru"

        # Invalidate
        await cache.invalidate_user(user_id)
        assert await cache.get_user(user_id) is None

    async def test_plans_workflow(self, fake_redis: fakeredis.aioredis.FakeRedis) -> None:
        """Test complete plans caching workflow."""
        cache = CacheService(redis=fake_redis)

        # Initial miss
        assert await cache.get_plans() is None

        # Cache plans
        plans = [{"id": "plan1"}, {"id": "plan2"}]
        await cache.set_plans(plans)

        # Retrieve
        cached_plans = await cache.get_plans()
        assert cached_plans == plans

        # Update plans
        new_plans = [{"id": "plan3"}]
        await cache.set_plans(new_plans)

        assert await cache.get_plans() == new_plans

        # Invalidate
        await cache.invalidate_plans()
        assert await cache.get_plans() is None

    async def test_multiple_cache_instances_share_data(
        self, fake_redis: fakeredis.aioredis.FakeRedis
    ) -> None:
        """Test that multiple cache instances share the same Redis."""
        cache1 = CacheService(redis=fake_redis, key_prefix="shared:")
        cache2 = CacheService(redis=fake_redis, key_prefix="shared:")

        # Set with cache1
        await cache1.set("key", "value")

        # Get with cache2
        result = await cache2.get("key")
        assert result == "value"
