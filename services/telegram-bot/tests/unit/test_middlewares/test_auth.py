"""Unit tests for authentication middleware."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.types import CallbackQuery, Message, User

from src.middlewares.auth import AuthMiddleware
from src.services.api_client import APIError, NotFoundError

if TYPE_CHECKING:
    import fakeredis.aioredis

    from src.config import BotSettings
    from src.services.api_client import CyberVPNAPIClient
    from src.services.cache_service import CacheService


@pytest.mark.asyncio
class TestAuthMiddleware:
    """Test authentication middleware."""

    async def test_cache_hit_loads_user(
        self,
        mock_api_client: CyberVPNAPIClient,
        fake_redis: fakeredis.aioredis.FakeRedis,
    ) -> None:
        """Test that cached user is loaded without API call."""
        from src.services.cache_service import CacheService

        cache = CacheService(redis=fake_redis)
        middleware = AuthMiddleware(
            api_client=mock_api_client, cache=cache, default_language="ru"
        )

        user_data = {"telegram_id": 123456, "username": "cached_user"}
        await cache.set_user(123456, user_data)

        user = User(id=123456, is_bot=False, first_name="Test")
        message = MagicMock(spec=Message)
        message.from_user = user

        handler = AsyncMock(return_value=None)
        data = {}

        await middleware(handler, message, data)

        # User should be injected
        assert data["user"] == user_data
        assert data["telegram_user"] == user
        assert handler.called

    async def test_cache_miss_loads_from_api(
        self,
        mock_api_client: CyberVPNAPIClient,
        fake_redis: fakeredis.aioredis.FakeRedis,
    ) -> None:
        """Test that cache miss triggers API load."""
        import respx
        from src.services.cache_service import CacheService

        cache = CacheService(redis=fake_redis)
        middleware = AuthMiddleware(
            api_client=mock_api_client, cache=cache
        )

        user_data = {"telegram_id": 123456, "username": "api_user"}

        with respx.mock:
            respx.get(
                "https://api.test.cybervpn.local/telegram/users/123456"
            ).mock(return_value=respx.MockResponse(200, json=user_data))

            user = User(id=123456, is_bot=False, first_name="Test")
            message = MagicMock(spec=Message)
            message.from_user = user

            handler = AsyncMock()
            data = {}

            await middleware(handler, message, data)

            # User should be loaded and cached
            assert data["user"] == user_data

            # Check it was cached
            cached = await cache.get_user(123456)
            assert cached == user_data

    async def test_api_404_triggers_registration(
        self,
        mock_api_client: CyberVPNAPIClient,
        fake_redis: fakeredis.aioredis.FakeRedis,
    ) -> None:
        """Test that 404 from API triggers user registration."""
        import respx
        from src.services.cache_service import CacheService

        cache = CacheService(redis=fake_redis)
        middleware = AuthMiddleware(
            api_client=mock_api_client, cache=cache
        )

        new_user_data = {"telegram_id": 999999, "username": "newuser"}

        with respx.mock:
            # First call returns 404
            respx.get(
                "https://api.test.cybervpn.local/telegram/users/999999"
            ).mock(
                return_value=respx.MockResponse(
                    404, json={"detail": "Not found"}
                )
            )

            # Registration succeeds
            respx.post(
                "https://api.test.cybervpn.local/telegram/users"
            ).mock(return_value=respx.MockResponse(200, json=new_user_data))

            user = User(
                id=999999,
                is_bot=False,
                first_name="New",
                username="newuser",
                language_code="en",
            )
            message = MagicMock(spec=Message)
            message.from_user = user

            handler = AsyncMock()
            data = {}

            await middleware(handler, message, data)

            # New user should be registered and injected
            assert data["user"] == new_user_data

    async def test_registration_uses_telegram_language(
        self,
        mock_api_client: CyberVPNAPIClient,
        fake_redis: fakeredis.aioredis.FakeRedis,
    ) -> None:
        """Test that user language_code is used in registration."""
        import respx
        from src.services.cache_service import CacheService

        cache = CacheService(redis=fake_redis)
        middleware = AuthMiddleware(
            api_client=mock_api_client,
            cache=cache,
            default_language="ru",
        )

        with respx.mock:
            respx.get(
                "https://api.test.cybervpn.local/telegram/users/555"
            ).mock(return_value=respx.MockResponse(404))

            registration_route = respx.post(
                "https://api.test.cybervpn.local/telegram/users"
            ).mock(
                return_value=respx.MockResponse(
                    200, json={"telegram_id": 555}
                )
            )

            user = User(
                id=555,
                is_bot=False,
                first_name="Test",
                language_code="fr",  # French
            )
            message = MagicMock(spec=Message)
            message.from_user = user

            handler = AsyncMock()
            data = {}

            await middleware(handler, message, data)

            # Verify registration was called
            assert registration_route.called

    async def test_registration_uses_default_language_if_none(
        self,
        mock_api_client: CyberVPNAPIClient,
        fake_redis: fakeredis.aioredis.FakeRedis,
    ) -> None:
        """Test default language used when user has no language_code."""
        import respx
        from src.services.cache_service import CacheService

        cache = CacheService(redis=fake_redis)
        middleware = AuthMiddleware(
            api_client=mock_api_client,
            cache=cache,
            default_language="ru",
        )

        with respx.mock:
            respx.get(
                "https://api.test.cybervpn.local/telegram/users/666"
            ).mock(return_value=respx.MockResponse(404))

            respx.post(
                "https://api.test.cybervpn.local/telegram/users"
            ).mock(
                return_value=respx.MockResponse(
                    200, json={"telegram_id": 666, "language": "ru"}
                )
            )

            user = User(
                id=666,
                is_bot=False,
                first_name="Test",
                language_code=None,  # No language
            )
            message = MagicMock(spec=Message)
            message.from_user = user

            handler = AsyncMock()
            data = {}

            await middleware(handler, message, data)

            # Should have registered with default language
            assert data["user"] is not None

    async def test_api_error_non_404_returns_none(
        self,
        mock_api_client: CyberVPNAPIClient,
        fake_redis: fakeredis.aioredis.FakeRedis,
    ) -> None:
        """Test that non-404 API errors result in None user."""
        import respx
        from src.services.cache_service import CacheService

        cache = CacheService(redis=fake_redis)
        middleware = AuthMiddleware(
            api_client=mock_api_client, cache=cache
        )

        with respx.mock:
            respx.get(
                "https://api.test.cybervpn.local/telegram/users/123"
            ).mock(
                return_value=respx.MockResponse(
                    500, json={"detail": "Server error"}
                )
            )

            user = User(id=123, is_bot=False, first_name="Test")
            message = MagicMock(spec=Message)
            message.from_user = user

            handler = AsyncMock()
            data = {}

            await middleware(handler, message, data)

            # User should be None due to API error
            assert data["user"] is None

    async def test_registration_failure_returns_none(
        self,
        mock_api_client: CyberVPNAPIClient,
        fake_redis: fakeredis.aioredis.FakeRedis,
    ) -> None:
        """Test that registration failure results in None user."""
        import respx
        from src.services.cache_service import CacheService

        cache = CacheService(redis=fake_redis)
        middleware = AuthMiddleware(
            api_client=mock_api_client, cache=cache
        )

        with respx.mock:
            # Get returns 404
            respx.get(
                "https://api.test.cybervpn.local/telegram/users/777"
            ).mock(return_value=respx.MockResponse(404))

            # Registration fails
            respx.post(
                "https://api.test.cybervpn.local/telegram/users"
            ).mock(
                return_value=respx.MockResponse(
                    500, json={"detail": "Registration failed"}
                )
            )

            user = User(id=777, is_bot=False, first_name="Test")
            message = MagicMock(spec=Message)
            message.from_user = user

            handler = AsyncMock()
            data = {}

            await middleware(handler, message, data)

            assert data["user"] is None

    async def test_extracts_user_from_callback_query(
        self,
        mock_api_client: CyberVPNAPIClient,
        fake_redis: fakeredis.aioredis.FakeRedis,
    ) -> None:
        """Test user extraction from callback query."""
        import respx
        from src.services.cache_service import CacheService

        cache = CacheService(redis=fake_redis)
        middleware = AuthMiddleware(
            api_client=mock_api_client, cache=cache
        )

        user_data = {"telegram_id": 888, "username": "callback_user"}

        with respx.mock:
            respx.get(
                "https://api.test.cybervpn.local/telegram/users/888"
            ).mock(return_value=respx.MockResponse(200, json=user_data))

            user = User(id=888, is_bot=False, first_name="Test")
            callback = MagicMock(spec=CallbackQuery)
            callback.from_user = user

            handler = AsyncMock()
            data = {}

            await middleware(handler, callback, data)

            assert data["user"] == user_data
            assert data["telegram_user"] == user

    async def test_handles_event_with_no_user(
        self,
        mock_api_client: CyberVPNAPIClient,
        fake_redis: fakeredis.aioredis.FakeRedis,
    ) -> None:
        """Test handling events with no user."""
        from src.services.cache_service import CacheService

        cache = CacheService(redis=fake_redis)
        middleware = AuthMiddleware(
            api_client=mock_api_client, cache=cache
        )

        # Event with no user
        event = MagicMock()

        handler = AsyncMock()
        data = {}

        await middleware(handler, event, data)

        # Should pass through without error
        assert handler.called
        assert "user" not in data

    async def test_caches_user_after_api_load(
        self,
        mock_api_client: CyberVPNAPIClient,
        fake_redis: fakeredis.aioredis.FakeRedis,
    ) -> None:
        """Test that user is cached after API load."""
        import respx
        from src.services.cache_service import CacheService

        cache = CacheService(redis=fake_redis)
        middleware = AuthMiddleware(
            api_client=mock_api_client, cache=cache
        )

        user_data = {"telegram_id": 111, "username": "to_cache"}

        with respx.mock:
            api_route = respx.get(
                "https://api.test.cybervpn.local/telegram/users/111"
            ).mock(return_value=respx.MockResponse(200, json=user_data))

            user = User(id=111, is_bot=False, first_name="Test")
            message = MagicMock(spec=Message)
            message.from_user = user

            handler = AsyncMock()

            # First call - should hit API
            await middleware(handler, message, {})
            assert api_route.call_count == 1

            # Second call - should use cache
            await middleware(handler, message, {})
            assert api_route.call_count == 1  # Not called again

    async def test_respects_cache_ttl(
        self,
        mock_api_client: CyberVPNAPIClient,
        fake_redis: fakeredis.aioredis.FakeRedis,
    ) -> None:
        """Test that cached user has TTL set."""
        import respx
        from src.services.cache_service import CacheService

        cache = CacheService(redis=fake_redis, key_prefix="test:")
        middleware = AuthMiddleware(
            api_client=mock_api_client, cache=cache
        )

        user_data = {"telegram_id": 222, "username": "ttl_test"}

        with respx.mock:
            respx.get(
                "https://api.test.cybervpn.local/telegram/users/222"
            ).mock(return_value=respx.MockResponse(200, json=user_data))

            user = User(id=222, is_bot=False, first_name="Test")
            message = MagicMock(spec=Message)
            message.from_user = user

            handler = AsyncMock()
            data = {}

            await middleware(handler, message, data)

            # Check TTL is set in Redis
            ttl = await fake_redis.ttl("test:user:222")
            assert ttl > 0
            assert ttl <= 300  # USER_CACHE_TTL
