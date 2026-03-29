"""Unit tests for Facebook OAuth account-linking endpoints."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.infrastructure.cache.redis_client import get_redis
from src.main import app
from src.presentation.dependencies.auth import get_current_active_user
from src.presentation.dependencies.database import get_db


class _MockAuthUser:
    id = uuid4()
    login = "test-user"
    is_active = True


class _FakeRateLimitRedisClient:
    def __init__(self, *args, **kwargs) -> None:
        self._commands: list[tuple[str, tuple, dict]] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    def pipeline(self, transaction: bool = True):
        return self

    def zremrangebyscore(self, *args, **kwargs):
        self._commands.append(("zremrangebyscore", args, kwargs))

    def zadd(self, *args, **kwargs):
        self._commands.append(("zadd", args, kwargs))

    def zcard(self, *args, **kwargs):
        self._commands.append(("zcard", args, kwargs))

    def expire(self, *args, **kwargs):
        self._commands.append(("expire", args, kwargs))

    async def execute(self):
        return [0, 1, 1, True]

    async def aclose(self):
        return None


@pytest.fixture(autouse=True)
def _clean_overrides():
    yield
    app.dependency_overrides.clear()


def _override_dependencies() -> None:
    async def _redis_override():
        yield object()

    async def _db_override():
        yield object()

    def _auth_override() -> _MockAuthUser:
        return _MockAuthUser()

    app.dependency_overrides[get_redis] = _redis_override
    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[get_current_active_user] = _auth_override


@pytest.mark.asyncio
async def test_facebook_authorize_returns_authorize_url_and_state():
    _override_dependencies()

    with (
        patch("src.presentation.middleware.rate_limit.redis.Redis", _FakeRateLimitRedisClient),
        patch(
            "src.presentation.api.v1.oauth.routes.OAuthStateService.generate",
            new=AsyncMock(return_value=("facebook_state", None)),
        ),
        patch(
            "src.presentation.api.v1.oauth.routes.FacebookOAuthProvider.authorize_url",
            return_value="https://facebook.example/auth?state=facebook_state",
        ),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/v1/oauth/facebook/authorize",
                params={"redirect_uri": "cybervpn://oauth/callback?provider=facebook"},
            )

    assert response.status_code == 200
    assert response.json() == {
        "authorize_url": "https://facebook.example/auth?state=facebook_state",
        "state": "facebook_state",
    }


@pytest.mark.asyncio
async def test_facebook_callback_links_account_on_success():
    _override_dependencies()

    with (
        patch("src.presentation.middleware.rate_limit.redis.Redis", _FakeRateLimitRedisClient),
        patch(
            "src.presentation.api.v1.oauth.routes.OAuthStateService.validate_and_consume",
            new=AsyncMock(return_value=True),
        ),
        patch(
            "src.presentation.api.v1.oauth.routes.FacebookOAuthProvider.exchange_code",
            new=AsyncMock(
                return_value={
                    "id": "facebook_user_123",
                    "email": "fb@example.com",
                    "username": "fbuser",
                    "access_token": "facebook_access_token",
                    "refresh_token": None,
                }
            ),
        ),
        patch(
            "src.presentation.api.v1.oauth.routes.AccountLinkingUseCase.link_account",
            new=AsyncMock(return_value=SimpleNamespace()),
        ) as mock_link,
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/oauth/facebook/callback",
                json={
                    "code": "facebook_code",
                    "state": "facebook_state",
                    "redirect_uri": "cybervpn://oauth/callback?provider=facebook",
                },
            )

    assert response.status_code == 200
    assert response.json() == {
        "status": "linked",
        "provider": "facebook",
        "provider_user_id": "facebook_user_123",
    }
    mock_link.assert_awaited_once()


@pytest.mark.asyncio
async def test_facebook_callback_rejects_invalid_state():
    _override_dependencies()

    with (
        patch(
            "src.presentation.middleware.rate_limit.redis.Redis",
            _FakeRateLimitRedisClient,
        ),
        patch(
            "src.presentation.api.v1.oauth.routes.OAuthStateService.validate_and_consume",
            new=AsyncMock(return_value=False),
        ),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/oauth/facebook/callback",
                json={
                    "code": "facebook_code",
                    "state": "bad_state",
                    "redirect_uri": "cybervpn://oauth/callback?provider=facebook",
                },
            )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired OAuth state."
