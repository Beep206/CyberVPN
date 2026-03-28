"""Unit tests for Telegram magic-link OAuth endpoints."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.remnawave.adapters import get_remnawave_adapter
from src.main import app
from src.presentation.dependencies.auth import get_current_active_user
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.services import get_auth_service


class _FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.ttls: dict[str, int] = {}

    async def get(self, key: str) -> str | None:
        return self.values.get(key)

    async def setex(self, key: str, ttl_seconds: int, value: str) -> bool:
        self.values[key] = value
        self.ttls[key] = ttl_seconds
        return True

    async def ttl(self, key: str) -> int:
        if key not in self.values:
            return -2
        return self.ttls.get(key, -1)

    async def set(self, key: str, value: str, ex: int | None = None, xx: bool = False) -> bool:
        if xx and key not in self.values:
            return False

        self.values[key] = value
        if ex is not None:
            self.ttls[key] = ex
        return True

    async def getdel(self, key: str) -> str | None:
        self.ttls.pop(key, None)
        return self.values.pop(key, None)


class _MockAuthUser:
    id = uuid4()
    login = "bot-service"
    is_active = True


@pytest.fixture(autouse=True)
def _clean_overrides():
    yield
    app.dependency_overrides.clear()


def _override_dependencies(fake_redis: _FakeRedis) -> None:
    async def _redis_override():
        yield fake_redis

    async def _db_override():
        yield object()

    def _auth_override() -> _MockAuthUser:
        return _MockAuthUser()

    def _auth_service_override() -> object:
        return object()

    def _remnawave_override() -> object:
        return object()

    app.dependency_overrides[get_redis] = _redis_override
    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[get_current_active_user] = _auth_override
    app.dependency_overrides[get_auth_service] = _auth_service_override
    app.dependency_overrides[get_remnawave_adapter] = _remnawave_override


@pytest.mark.asyncio
async def test_complete_telegram_magic_link_accepts_pending_session():
    fake_redis = _FakeRedis()
    redis_key = "auth_magic_link:magic_token_123"
    fake_redis.values[redis_key] = "pending"
    fake_redis.ttls[redis_key] = 240
    _override_dependencies(fake_redis)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/oauth/telegram/magic-link/complete",
            json={
                "token": "magic_token_123",
                "id": "424242",
                "first_name": "Alice",
                "last_name": "Doe",
                "username": "alice",
                "language_code": "en",
            },
        )

    assert response.status_code == 200
    assert response.json() == {"status": "accepted"}
    assert fake_redis.ttls[redis_key] == 240
    stored_payload = json.loads(fake_redis.values[redis_key])
    assert stored_payload["id"] == "424242"
    assert stored_payload["username"] == "alice"


@pytest.mark.asyncio
async def test_check_telegram_magic_link_status_returns_pending_for_open_session():
    fake_redis = _FakeRedis()
    fake_redis.values["auth_magic_link:pending_token"] = "pending"
    fake_redis.ttls["auth_magic_link:pending_token"] = 300
    _override_dependencies(fake_redis)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/oauth/telegram/magic-link/pending_token/status")

    assert response.status_code == 200
    assert response.json() == {"status": "pending", "login_result": None}


@pytest.mark.asyncio
async def test_check_telegram_magic_link_status_sets_auth_cookies_and_consumes_token():
    fake_redis = _FakeRedis()
    token = "completed_token"
    fake_redis.values[f"auth_magic_link:{token}"] = json.dumps(
        {
            "id": "424242",
            "first_name": "Alice",
            "username": "alice",
            "language_code": "en",
        }
    )
    fake_redis.ttls[f"auth_magic_link:{token}"] = 180
    _override_dependencies(fake_redis)

    result = SimpleNamespace(
        access_token="access_token_123",
        refresh_token="refresh_token_456",
        token_type="bearer",
        expires_in=900,
        user=SimpleNamespace(
            id=uuid4(),
            login="alice",
            email=None,
            is_active=True,
            is_email_verified=True,
            created_at=datetime.now(UTC),
        ),
        is_new_user=True,
        requires_2fa=False,
        tfa_token=None,
    )

    with patch(
        "src.presentation.api.v1.oauth.routes.OAuthLoginUseCase.execute",
        new=AsyncMock(return_value=result),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/api/v1/oauth/telegram/magic-link/{token}/status")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["login_result"]["user"]["login"] == "alice"
    assert f"auth_magic_link:{token}" not in fake_redis.values

    set_cookie_headers = response.headers.get_list("set-cookie")
    cookie_str = "; ".join(set_cookie_headers)
    assert "access_token=access_token_123" in cookie_str
    assert "refresh_token=refresh_token_456" in cookie_str
