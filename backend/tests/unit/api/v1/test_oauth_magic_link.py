"""Unit tests for Telegram magic-link OAuth endpoints."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr

from src.application.use_cases.auth.telegram_account_linking import TelegramAccountLinkConflictError
from src.application.use_cases.auth_realms import RealmResolution
from src.config.settings import settings
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.remnawave.adapters import get_remnawave_adapter
from src.main import app
from src.presentation.dependencies.auth import get_current_active_user, optional_user
from src.presentation.dependencies.auth_realms import get_request_web_auth_realm
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.services import get_auth_service

_DEFAULT_AUTH_USER_ID = uuid4()


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

    async def delete(self, key: str) -> int:
        existed = key in self.values
        self.ttls.pop(key, None)
        self.values.pop(key, None)
        return int(existed)

    async def eval(self, script: str, numkeys: int, key: str, *args: str) -> int | list[object]:
        assert numkeys == 1
        current_status = self.values.get(key)

        if 'data["telegram"] = cjson.decode(ARGV[2])' in script:
            flow, telegram_payload = args
            if current_status is None:
                return 0
            data = json.loads(current_status)
            if data.get("flow") != flow:
                return 0
            if data.get("status") != "pending":
                return 1
            ttl_seconds = await self.ttl(key)
            if ttl_seconds <= 0:
                return 0
            data["status"] = "confirmed"
            data["telegram"] = json.loads(telegram_payload)
            self.values[key] = json.dumps(data)
            self.ttls[key] = ttl_seconds
            return 2

        if "return {5, current}" in script:
            flow, processing_token = args
            if current_status is None:
                return [0, ""]
            data = json.loads(current_status)
            if data.get("flow") != flow:
                return [0, ""]
            status_value = data.get("status")
            if status_value == "pending":
                return [1, current_status]
            if status_value == "processing":
                return [2, current_status]
            if status_value == "confirmed":
                ttl_seconds = await self.ttl(key)
                if ttl_seconds <= 0:
                    return [0, ""]
                data["status"] = "processing"
                data["processing_token"] = processing_token
                self.values[key] = json.dumps(data)
                self.ttls[key] = ttl_seconds
                return [3, current_status]
            if status_value == "linked":
                return [4, current_status]
            if status_value == "conflict":
                return [5, current_status]
            return [0, ""]

        if 'data["status"] = "confirmed"' in script and "processing_token" in script:
            flow, processing_token = args
            if current_status is None:
                return 0
            data = json.loads(current_status)
            if data.get("flow") != flow:
                return 0
            if data.get("status") != "processing" or data.get("processing_token") != processing_token:
                return 0
            ttl_seconds = await self.ttl(key)
            if ttl_seconds <= 0:
                return 0
            data["status"] = "confirmed"
            data.pop("processing_token", None)
            self.values[key] = json.dumps(data)
            self.ttls[key] = ttl_seconds
            return 1

        if 'data["status"] = ARGV[3]' in script:
            flow, processing_token, status_value, provider_user_id = args
            if current_status is None:
                return 0
            data = json.loads(current_status)
            if data.get("flow") != flow:
                return 0
            if data.get("status") == "processing" and data.get("processing_token") != processing_token:
                return 0
            ttl_seconds = await self.ttl(key)
            if ttl_seconds <= 0:
                return 0
            data["status"] = status_value
            data["provider_user_id"] = provider_user_id
            data.pop("processing_token", None)
            self.values[key] = json.dumps(data)
            self.ttls[key] = ttl_seconds
            return 1

        if "string.sub(current, 1, string.len(ARGV[2]))" in script:
            expected_status, processing_prefix, processing_token = args
            if current_status is None:
                return [0, ""]
            if current_status == expected_status:
                return [1, ""]
            if current_status.startswith(processing_prefix):
                return [2, ""]
            ttl_seconds = await self.ttl(key)
            if ttl_seconds <= 0:
                return [0, ""]
            self.values[key] = f"{processing_token}{current_status}"
            self.ttls[key] = ttl_seconds
            return [3, current_status]

        if 'redis.call("DEL", KEYS[1])' in script:
            (expected_processing_value,) = args
            if current_status != expected_processing_value:
                return 0
            self.ttls.pop(key, None)
            self.values.pop(key, None)
            return 1

        if "current ~= ARGV[1] then\n    return 0" in script and "ARGV[2]" in script:
            expected_processing_value, value = args
            if current_status != expected_processing_value:
                return 0
            ttl_seconds = await self.ttl(key)
            if ttl_seconds <= 0:
                return 0
            self.values[key] = value
            self.ttls[key] = ttl_seconds
            return 1

        expected_status, value = args
        if current_status is None:
            return 0
        if current_status != expected_status:
            return 1
        ttl_seconds = await self.ttl(key)
        if ttl_seconds <= 0:
            return 0
        self.values[key] = value
        self.ttls[key] = ttl_seconds
        return 2


class _MockAuthUser:
    def __init__(self, user_id: UUID | None = None) -> None:
        self.id = user_id or _DEFAULT_AUTH_USER_ID
        self.login = "bot-service"
        self.is_active = True


class _FakeDb:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


@pytest.fixture(autouse=True)
def _clean_overrides():
    yield
    app.dependency_overrides.clear()


def _override_dependencies(
    fake_redis: _FakeRedis,
    *,
    auth_user: _MockAuthUser | None = None,
    db: object | None = None,
) -> None:
    async def _redis_override():
        yield fake_redis

    async def _db_override():
        yield db or object()

    def _auth_override() -> _MockAuthUser:
        return auth_user or _MockAuthUser()

    auth_service = SimpleNamespace(
        decode_token=lambda _token: {
            "exp": int((datetime.now(UTC) + timedelta(days=7)).timestamp()),
        }
    )

    def _auth_service_override() -> object:
        return auth_service

    def _remnawave_override() -> object:
        return object()

    def _realm_override() -> RealmResolution:
        auth_realm = SimpleNamespace(
            id=uuid4(),
            realm_key="customer",
            realm_type="customer",
            audience="cybervpn:customer",
            cookie_namespace="customer",
        )
        return RealmResolution(auth_realm=auth_realm, source="test")

    app.dependency_overrides[get_redis] = _redis_override
    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[get_current_active_user] = _auth_override
    app.dependency_overrides[optional_user] = _auth_override
    app.dependency_overrides[get_request_web_auth_realm] = _realm_override
    app.dependency_overrides[get_auth_service] = _auth_service_override
    app.dependency_overrides[get_remnawave_adapter] = _remnawave_override


@pytest.mark.asyncio
async def test_complete_telegram_magic_link_accepts_pending_session_from_bot_secret(monkeypatch: pytest.MonkeyPatch):
    fake_redis = _FakeRedis()
    redis_key = "auth_magic_link:magic_token_123"
    fake_redis.values[redis_key] = "pending"
    fake_redis.ttls[redis_key] = 240
    _override_dependencies(fake_redis)
    monkeypatch.setattr(settings, "telegram_bot_internal_secret", SecretStr("test-bot-secret"))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/oauth/telegram/magic-link/complete",
            headers={"X-Telegram-Bot-Secret": "test-bot-secret"},
            json={
                "token": "magic_token_123",
                "id": "424242",
                "first_name": "Alice",
                "last_name": "Doe",
                "username": "alice",
                "language_code": "en",
            },
        )

    assert response.status_code == 200, response.text
    assert response.json() == {"status": "accepted"}
    assert fake_redis.ttls[redis_key] == 240
    stored_payload = json.loads(fake_redis.values[redis_key])
    assert stored_payload["id"] == "424242"
    assert stored_payload["username"] == "alice"


@pytest.mark.asyncio
async def test_complete_telegram_magic_link_rejects_web_session_without_bot_secret(monkeypatch: pytest.MonkeyPatch):
    fake_redis = _FakeRedis()
    redis_key = "auth_magic_link:magic_token_123"
    fake_redis.values[redis_key] = "pending"
    fake_redis.ttls[redis_key] = 240
    _override_dependencies(fake_redis)
    monkeypatch.setattr(settings, "telegram_bot_internal_secret", SecretStr("test-bot-secret"))

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

    assert response.status_code == 401
    assert fake_redis.values[redis_key] == "pending"
    assert fake_redis.ttls[redis_key] == 240


@pytest.mark.asyncio
async def test_complete_telegram_magic_link_rejects_expired_session_without_mutation(
    monkeypatch: pytest.MonkeyPatch,
):
    fake_redis = _FakeRedis()
    _override_dependencies(fake_redis)
    monkeypatch.setattr(settings, "telegram_bot_internal_secret", SecretStr("test-bot-secret"))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/oauth/telegram/magic-link/complete",
            headers={"X-Telegram-Bot-Secret": "test-bot-secret"},
            json={
                "token": "expired_token",
                "id": "424242",
                "first_name": "Alice",
                "username": "alice",
            },
        )

    assert response.status_code == 404
    assert "auth_magic_link:expired_token" not in fake_redis.values


@pytest.mark.asyncio
async def test_complete_telegram_magic_link_repeated_completion_keeps_first_payload(
    monkeypatch: pytest.MonkeyPatch,
):
    fake_redis = _FakeRedis()
    redis_key = "auth_magic_link:magic_token_123"
    fake_redis.values[redis_key] = "pending"
    fake_redis.ttls[redis_key] = 240
    _override_dependencies(fake_redis)
    monkeypatch.setattr(settings, "telegram_bot_internal_secret", SecretStr("test-bot-secret"))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        first_response = await client.post(
            "/api/v1/oauth/telegram/magic-link/complete",
            headers={"X-Telegram-Bot-Secret": "test-bot-secret"},
            json={
                "token": "magic_token_123",
                "id": "424242",
                "first_name": "Alice",
                "username": "alice",
            },
        )
        second_response = await client.post(
            "/api/v1/oauth/telegram/magic-link/complete",
            headers={"X-Telegram-Bot-Secret": "test-bot-secret"},
            json={
                "token": "magic_token_123",
                "id": "999999",
                "first_name": "Mallory",
                "username": "mallory",
            },
        )

    assert first_response.status_code == 200, first_response.text
    assert second_response.status_code == 409
    stored_payload = json.loads(fake_redis.values[redis_key])
    assert stored_payload["id"] == "424242"
    assert stored_payload["username"] == "alice"
    assert fake_redis.ttls[redis_key] == 240


@pytest.mark.asyncio
async def test_create_telegram_account_link_magic_link_stores_owner_session(monkeypatch: pytest.MonkeyPatch):
    fake_redis = _FakeRedis()
    auth_user = _MockAuthUser(_DEFAULT_AUTH_USER_ID)
    _override_dependencies(fake_redis, auth_user=auth_user)
    monkeypatch.setattr(settings, "telegram_bot_username", "CyberVPNBot")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/oauth/telegram/account-link/magic-link")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["token"]
    assert "start=link_" in body["bot_url"]
    assert "start=link_" in body["deep_link_url"]
    assert body["expires_in"] == 300

    redis_key = f"telegram_account_link:{body['token']}"
    stored_payload = json.loads(fake_redis.values[redis_key])
    assert stored_payload["flow"] == "telegram_account_link"
    assert stored_payload["status"] == "pending"
    assert stored_payload["user_id"] == str(auth_user.id)
    assert fake_redis.ttls[redis_key] == 300


@pytest.mark.asyncio
async def test_complete_telegram_account_link_accepts_pending_session_from_bot_secret(
    monkeypatch: pytest.MonkeyPatch,
):
    fake_redis = _FakeRedis()
    redis_key = "telegram_account_link:link_token_123"
    fake_redis.values[redis_key] = json.dumps(
        {
            "flow": "telegram_account_link",
            "status": "pending",
            "user_id": str(_DEFAULT_AUTH_USER_ID),
            "auth_realm_id": None,
            "created_at": "2026-06-18T00:00:00+00:00",
        }
    )
    fake_redis.ttls[redis_key] = 240
    _override_dependencies(fake_redis)
    monkeypatch.setattr(settings, "telegram_bot_internal_secret", SecretStr("test-bot-secret"))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/oauth/telegram/account-link/magic-link/complete",
            headers={"X-Telegram-Bot-Secret": "test-bot-secret"},
            json={
                "token": "link_token_123",
                "id": "424242",
                "first_name": "Alice",
                "last_name": "Doe",
                "username": "alice",
                "language_code": "en",
            },
        )

    assert response.status_code == 200, response.text
    assert response.json() == {"status": "accepted"}
    stored_payload = json.loads(fake_redis.values[redis_key])
    assert stored_payload["status"] == "confirmed"
    assert stored_payload["telegram"]["id"] == "424242"
    assert stored_payload["telegram"]["username"] == "alice"
    assert fake_redis.ttls[redis_key] == 240


@pytest.mark.asyncio
async def test_check_telegram_account_link_status_rejects_wrong_owner():
    fake_redis = _FakeRedis()
    token = "wrong_owner_link_token"
    redis_key = f"telegram_account_link:{token}"
    fake_redis.values[redis_key] = json.dumps(
        {
            "flow": "telegram_account_link",
            "status": "confirmed",
            "user_id": str(uuid4()),
            "auth_realm_id": None,
            "created_at": "2026-06-18T00:00:00+00:00",
            "telegram": {"id": "424242", "username": "alice"},
        }
    )
    fake_redis.ttls[redis_key] = 180
    _override_dependencies(fake_redis, auth_user=_MockAuthUser(_DEFAULT_AUTH_USER_ID), db=_FakeDb())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/v1/oauth/telegram/account-link/magic-link/{token}/status")

    assert response.status_code == 403
    stored_payload = json.loads(fake_redis.values[redis_key])
    assert stored_payload["status"] == "confirmed"
    assert "processing_token" not in stored_payload


@pytest.mark.asyncio
async def test_check_telegram_account_link_status_links_without_login_cookies():
    fake_redis = _FakeRedis()
    token = "confirmed_link_token"
    redis_key = f"telegram_account_link:{token}"
    fake_redis.values[redis_key] = json.dumps(
        {
            "flow": "telegram_account_link",
            "status": "confirmed",
            "user_id": str(_DEFAULT_AUTH_USER_ID),
            "auth_realm_id": None,
            "created_at": "2026-06-18T00:00:00+00:00",
            "telegram": {
                "id": "424242",
                "first_name": "Alice",
                "username": "alice",
                "language_code": "en",
            },
        }
    )
    fake_redis.ttls[redis_key] = 180
    fake_db = _FakeDb()
    _override_dependencies(fake_redis, auth_user=_MockAuthUser(_DEFAULT_AUTH_USER_ID), db=fake_db)

    with patch(
        "src.presentation.api.v1.oauth.routes.TelegramAccountLinkingUseCase.link_account",
        new=AsyncMock(return_value=SimpleNamespace()),
    ) as mock_link:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/api/v1/oauth/telegram/account-link/magic-link/{token}/status")

    assert response.status_code == 200, response.text
    assert response.json() == {
        "status": "linked",
        "provider": "telegram",
        "provider_user_id": "424242",
    }
    mock_link.assert_awaited_once()
    assert fake_db.commits == 1
    assert "set-cookie" not in response.headers
    stored_payload = json.loads(fake_redis.values[redis_key])
    assert stored_payload["status"] == "linked"
    assert stored_payload["provider_user_id"] == "424242"


@pytest.mark.asyncio
async def test_check_telegram_account_link_status_returns_conflict_without_losing_payload():
    fake_redis = _FakeRedis()
    token = "conflict_link_token"
    redis_key = f"telegram_account_link:{token}"
    fake_redis.values[redis_key] = json.dumps(
        {
            "flow": "telegram_account_link",
            "status": "confirmed",
            "user_id": str(_DEFAULT_AUTH_USER_ID),
            "auth_realm_id": None,
            "created_at": "2026-06-18T00:00:00+00:00",
            "telegram": {"id": "424242", "username": "alice"},
        }
    )
    fake_redis.ttls[redis_key] = 180
    fake_db = _FakeDb()
    _override_dependencies(fake_redis, auth_user=_MockAuthUser(_DEFAULT_AUTH_USER_ID), db=fake_db)

    with patch(
        "src.presentation.api.v1.oauth.routes.TelegramAccountLinkingUseCase.link_account",
        new=AsyncMock(
            side_effect=TelegramAccountLinkConflictError("Telegram account is already linked to another user.")
        ),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/api/v1/oauth/telegram/account-link/magic-link/{token}/status")

    assert response.status_code == 409
    assert fake_db.rollbacks == 1
    stored_payload = json.loads(fake_redis.values[redis_key])
    assert stored_payload["status"] == "conflict"
    assert stored_payload["provider_user_id"] == "424242"


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

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    login_result = body["login_result"]
    assert login_result["user"]["login"] == "alice"
    assert login_result["is_new_user"] is True
    assert login_result["requires_2fa"] is False
    assert login_result["tfa_token"] is None
    assert "access_token" not in login_result
    assert "refresh_token" not in login_result
    assert "token_type" not in login_result
    assert "expires_in" not in login_result
    assert f"auth_magic_link:{token}" not in fake_redis.values

    set_cookie_headers = response.headers.get_list("set-cookie")
    cookie_str = "; ".join(set_cookie_headers)
    assert "access_token=access_token_123" in cookie_str
    assert "refresh_token=refresh_token_456" in cookie_str


@pytest.mark.asyncio
async def test_check_telegram_magic_link_status_restores_payload_after_login_failure():
    fake_redis = _FakeRedis()
    token = "retryable_completed_token"
    redis_key = f"auth_magic_link:{token}"
    payload = json.dumps(
        {
            "id": "424242",
            "first_name": "Alice",
            "username": "alice",
            "language_code": "en",
        }
    )
    fake_redis.values[redis_key] = payload
    fake_redis.ttls[redis_key] = 180
    _override_dependencies(fake_redis)

    with patch(
        "src.presentation.api.v1.oauth.routes.OAuthLoginUseCase.execute",
        new=AsyncMock(side_effect=RuntimeError("synthetic auth backend failure")),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test",
        ) as client:
            first_response = await client.get(f"/api/v1/oauth/telegram/magic-link/{token}/status")

    assert first_response.status_code == 500
    assert fake_redis.values[redis_key] == payload
    assert fake_redis.ttls[redis_key] == 180

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
        is_new_user=False,
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
            second_response = await client.get(f"/api/v1/oauth/telegram/magic-link/{token}/status")

    assert second_response.status_code == 200
    assert second_response.json()["status"] == "completed"
    assert redis_key not in fake_redis.values


@pytest.mark.asyncio
async def test_check_telegram_magic_link_status_keeps_payload_after_transient_login_failure():
    fake_redis = _FakeRedis()
    token = "retry_token"
    redis_key = f"auth_magic_link:{token}"
    fake_redis.values[redis_key] = json.dumps(
        {
            "id": "424242",
            "first_name": "Alice",
            "username": "alice",
            "language_code": "en",
        }
    )
    fake_redis.ttls[redis_key] = 180
    _override_dependencies(fake_redis)

    transient_error = ValueError("Synthetic transient login failure")

    with patch(
        "src.presentation.api.v1.oauth.routes.OAuthLoginUseCase.execute",
        new=AsyncMock(side_effect=transient_error),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            failed_response = await client.get(f"/api/v1/oauth/telegram/magic-link/{token}/status")

    assert failed_response.status_code == 409
    assert redis_key in fake_redis.values
    assert fake_redis.ttls[redis_key] == 180

    result = SimpleNamespace(
        access_token="access_token_retry",
        refresh_token="refresh_token_retry",
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
        is_new_user=False,
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
            retry_response = await client.get(f"/api/v1/oauth/telegram/magic-link/{token}/status")

    assert retry_response.status_code == 200
    assert retry_response.json()["status"] == "completed"
    assert redis_key not in fake_redis.values
