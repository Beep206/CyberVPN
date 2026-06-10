"""Unit tests for Telegram magic-link OAuth endpoints."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr

from src.application.use_cases.auth_realms import RealmResolution
from src.config.settings import settings
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.remnawave.adapters import get_remnawave_adapter
from src.main import app
from src.presentation.dependencies.auth import get_current_active_user, optional_user
from src.presentation.dependencies.auth_realms import get_request_web_auth_realm
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.services import get_auth_service

_TELEGRAM_BOT_SECRET = "unit-telegram-bot-secret"
_TELEGRAM_BOT_HEADERS = {"X-Telegram-Bot-Secret": _TELEGRAM_BOT_SECRET}


class _FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.ttls: dict[str, int] = {}
        self._lock = asyncio.Lock()

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

    async def eval(self, _script: str, numkeys: int, *keys_and_args: object) -> str:
        assert numkeys == 1
        key = str(keys_and_args[0])
        expected_status = str(keys_and_args[1])
        payload_json = str(keys_and_args[2])

        async with self._lock:
            current = self.values.get(key)
            if current is None:
                return "missing"
            if current != expected_status:
                return "completed"

            ttl = self.ttls.get(key, -1)
            if ttl <= 0:
                return "missing"

            self.values[key] = payload_json
            self.ttls[key] = ttl
            return "stored"


class _MockAuthUser:
    id = uuid4()
    login = "bot-service"
    is_active = True


@pytest.fixture(autouse=True)
def _clean_overrides(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "telegram_bot_internal_secret", SecretStr(_TELEGRAM_BOT_SECRET))
    yield
    app.dependency_overrides.clear()


def _override_dependencies(fake_redis: _FakeRedis) -> None:
    async def _redis_override():
        yield fake_redis

    async def _db_override():
        yield object()

    def _auth_override() -> _MockAuthUser:
        return _MockAuthUser()

    auth_service = SimpleNamespace(
        decode_token=lambda _token: {
            "exp": int((datetime.now(UTC) + timedelta(days=7)).timestamp()),
        }
    )

    def _auth_service_override() -> object:
        return auth_service

    def _remnawave_override() -> object:
        return object()

    def _auth_realm_override() -> RealmResolution:
        return RealmResolution(
            auth_realm=SimpleNamespace(
                id=uuid4(),
                realm_key="customer",
                realm_type="customer",
                audience="cybervpn:customer",
                cookie_namespace="customer",
            ),
            source="test",
        )

    app.dependency_overrides[get_redis] = _redis_override
    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[get_current_active_user] = _auth_override
    app.dependency_overrides[optional_user] = _auth_override
    app.dependency_overrides[get_auth_service] = _auth_service_override
    app.dependency_overrides[get_remnawave_adapter] = _remnawave_override
    app.dependency_overrides[get_request_web_auth_realm] = _auth_realm_override


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
            headers=_TELEGRAM_BOT_HEADERS,
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
async def test_complete_telegram_magic_link_rejects_web_session_without_bot_secret():
    fake_redis = _FakeRedis()
    redis_key = "auth_magic_link:web_session_bypass"
    fake_redis.values[redis_key] = "pending"
    fake_redis.ttls[redis_key] = 240
    _override_dependencies(fake_redis)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/oauth/telegram/magic-link/complete",
            json={
                "token": "web_session_bypass",
                "id": "424242",
                "first_name": "Alice",
                "username": "alice",
                "language_code": "en",
            },
        )

    assert response.status_code == 401
    assert fake_redis.values[redis_key] == "pending"
    assert fake_redis.ttls[redis_key] == 240


@pytest.mark.asyncio
async def test_complete_telegram_magic_link_rejects_repeated_completion_without_overwrite():
    fake_redis = _FakeRedis()
    redis_key = "auth_magic_link:already_completed_token"
    fake_redis.values[redis_key] = "pending"
    fake_redis.ttls[redis_key] = 240
    _override_dependencies(fake_redis)

    payload = {
        "token": "already_completed_token",
        "id": "111111",
        "first_name": "First",
        "username": "first",
        "language_code": "en",
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        first_response = await client.post(
            "/api/v1/oauth/telegram/magic-link/complete",
            headers=_TELEGRAM_BOT_HEADERS,
            json=payload,
        )
        second_response = await client.post(
            "/api/v1/oauth/telegram/magic-link/complete",
            headers=_TELEGRAM_BOT_HEADERS,
            json={**payload, "id": "222222", "first_name": "Second", "username": "second"},
        )

    assert first_response.status_code == 200
    assert second_response.status_code == 409
    stored_payload = json.loads(fake_redis.values[redis_key])
    assert stored_payload["id"] == "111111"
    assert stored_payload["username"] == "first"


@pytest.mark.asyncio
async def test_complete_telegram_magic_link_allows_only_one_concurrent_completion():
    fake_redis = _FakeRedis()
    redis_key = "auth_magic_link:concurrent_token"
    fake_redis.values[redis_key] = "pending"
    fake_redis.ttls[redis_key] = 240
    _override_dependencies(fake_redis)

    first_payload = {
        "token": "concurrent_token",
        "id": "111111",
        "first_name": "First",
        "username": "first",
        "language_code": "en",
    }
    second_payload = {
        "token": "concurrent_token",
        "id": "222222",
        "first_name": "Second",
        "username": "second",
        "language_code": "en",
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        first_response, second_response = await asyncio.gather(
            client.post(
                "/api/v1/oauth/telegram/magic-link/complete",
                headers=_TELEGRAM_BOT_HEADERS,
                json=first_payload,
            ),
            client.post(
                "/api/v1/oauth/telegram/magic-link/complete",
                headers=_TELEGRAM_BOT_HEADERS,
                json=second_payload,
            ),
        )

    statuses = sorted([first_response.status_code, second_response.status_code])
    assert statuses == [200, 409]

    accepted_payload = first_payload if first_response.status_code == 200 else second_payload
    stored_payload = json.loads(fake_redis.values[redis_key])
    assert stored_payload["id"] == accepted_payload["id"]
    assert stored_payload["username"] == accepted_payload["username"]


@pytest.mark.asyncio
async def test_complete_telegram_magic_link_missing_token_returns_404():
    fake_redis = _FakeRedis()
    _override_dependencies(fake_redis)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/oauth/telegram/magic-link/complete",
            headers=_TELEGRAM_BOT_HEADERS,
            json={
                "token": "missing_token",
                "id": "424242",
                "first_name": "Alice",
                "language_code": "en",
            },
        )

    assert response.status_code == 404


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

    with (
        patch(
            "src.presentation.api.v1.oauth.routes.OAuthLoginUseCase.execute",
            new=AsyncMock(return_value=result),
        ),
        patch("src.presentation.api.v1.oauth.routes.sync_active_sessions", new=AsyncMock()),
        patch("src.presentation.api.v1.oauth.routes.sync_auth_security_posture", new=AsyncMock()),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/api/v1/oauth/telegram/magic-link/{token}/status")
            second_response = await client.get(f"/api/v1/oauth/telegram/magic-link/{token}/status")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["login_result"]["user"]["login"] == "alice"
    assert f"auth_magic_link:{token}" not in fake_redis.values
    assert second_response.status_code == 200
    assert second_response.json() == {"status": "expired", "login_result": None}

    set_cookie_headers = response.headers.get_list("set-cookie")
    cookie_str = "; ".join(set_cookie_headers)
    assert "customer_access_token=access_token_123" in cookie_str
    assert "customer_refresh_token=refresh_token_456" in cookie_str
