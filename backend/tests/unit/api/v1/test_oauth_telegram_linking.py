"""Unit tests for Telegram OAuth account-linking endpoints."""

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


def _telegram_callback_payload() -> dict[str, str]:
    return {
        "id": "424242",
        "first_name": "Alice",
        "username": "alice",
        "auth_date": "1760000000",
        "hash": "valid_hash",
        "state": "telegram_state",
    }


@pytest.mark.asyncio
async def test_telegram_callback_links_account_on_success():
    _override_dependencies()

    with (
        patch("src.presentation.middleware.rate_limit.redis.Redis", _FakeRateLimitRedisClient),
        patch(
            "src.presentation.api.v1.oauth.routes.OAuthStateService.validate_and_consume",
            new=AsyncMock(return_value=True),
        ),
        patch(
            "src.presentation.api.v1.oauth.routes.TelegramOAuthProvider.exchange_code",
            new=AsyncMock(return_value={"id": "424242", "username": "alice"}),
        ),
        patch(
            "src.presentation.api.v1.oauth.routes.AccountLinkingUseCase.link_account",
            new=AsyncMock(return_value=SimpleNamespace()),
        ) as mock_link,
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/oauth/telegram/callback",
                json=_telegram_callback_payload(),
            )

    assert response.status_code == 200
    assert response.json() == {
        "status": "linked",
        "provider": "telegram",
        "provider_user_id": "424242",
    }
    mock_link.assert_awaited_once()


@pytest.mark.asyncio
async def test_telegram_callback_returns_409_when_identity_is_linked_elsewhere():
    _override_dependencies()

    with (
        patch("src.presentation.middleware.rate_limit.redis.Redis", _FakeRateLimitRedisClient),
        patch(
            "src.presentation.api.v1.oauth.routes.OAuthStateService.validate_and_consume",
            new=AsyncMock(return_value=True),
        ),
        patch(
            "src.presentation.api.v1.oauth.routes.TelegramOAuthProvider.exchange_code",
            new=AsyncMock(return_value={"id": "424242", "username": "alice"}),
        ),
        patch(
            "src.presentation.api.v1.oauth.routes.AccountLinkingUseCase.link_account",
            new=AsyncMock(side_effect=ValueError("Provider account is already linked to another user.")),
        ),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/oauth/telegram/callback",
                json=_telegram_callback_payload(),
            )

    assert response.status_code == 409
    assert response.json()["detail"] == "Provider account is already linked to another user."
