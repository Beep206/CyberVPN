from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import Response
from starlette.requests import Request

from src.presentation.api.v1.auth import passkeys


def _request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/auth/passkeys/authentication/verify",
            "scheme": "http",
            "server": ("testserver", 80),
            "client": ("127.0.0.1", 51234),
            "headers": [
                (b"origin", b"http://localhost:3000"),
                (b"user-agent", b"pytest-passkey"),
            ],
        }
    )


def _user(*, totp_enabled: bool = False) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        role="admin",
        totp_enabled=totp_enabled,
        is_active=True,
    )


def _credential(user_id) -> SimpleNamespace:
    return SimpleNamespace(
        auth_realm_id=uuid4(),
        audience="cybervpn:web:customer",
        principal_class="customer",
        principal_subject=str(user_id),
        realm_key="customer",
    )


class _AuthService:
    def __init__(self) -> None:
        self.refresh_calls = 0

    def create_access_token(self, **kwargs):
        if kwargs.get("role") == "2fa_pending":
            return ("pending-2fa-token", "pending-jti", datetime.now(UTC) + timedelta(minutes=5))
        return ("browser-access-token", "access-jti", datetime.now(UTC) + timedelta(minutes=15))

    def create_refresh_token(self, **_kwargs):
        self.refresh_calls += 1
        return ("browser-refresh-token", "refresh-jti", datetime.now(UTC) + timedelta(days=7))


@pytest.mark.asyncio
async def test_passkey_session_success_returns_tokenless_json_and_http_only_cookies(monkeypatch) -> None:
    issued_session_requests: list[object] = []
    sync_calls: list[object] = []

    class AuthSessionIssuerStub:
        def __init__(self, *, auth_service, session) -> None:
            self.auth_service = auth_service
            self.session = session

        async def issue_auth_session(self, issue_request):
            issued_session_requests.append(issue_request)
            return SimpleNamespace(
                access_token="browser-access-token",
                refresh_token="browser-refresh-token",
            )

    async def sync_active_sessions_stub(db) -> None:
        sync_calls.append(db)

    monkeypatch.setattr(passkeys, "AuthSessionIssuer", AuthSessionIssuerStub)
    monkeypatch.setattr(passkeys, "sync_active_sessions", sync_active_sessions_stub)

    user = _user()
    response = Response()
    result = await passkeys._issue_session_for_passkey(
        request=_request(),
        response=response,
        db=object(),
        auth_service=_AuthService(),
        user=user,
        credential=_credential(user.id),
        cookie_namespace="customer",
    )

    body = result.model_dump(mode="json")
    assert "access_token" not in body
    assert "refresh_token" not in body
    assert "expires_in" not in body
    assert "token_type" not in body
    assert body["auth_realm_key"] == "customer"
    assert body["principal_type"] == "customer"
    assert body["scope_family"] == "customer"
    assert body["requires_2fa"] is False
    assert body["tfa_token"] is None

    set_cookie_headers = [
        value.decode("latin-1") for key, value in response.raw_headers if key.decode("latin-1").lower() == "set-cookie"
    ]
    joined_cookies = "\n".join(set_cookie_headers)
    assert "customer_access_token=browser-access-token" in joined_cookies
    assert "customer_refresh_token=browser-refresh-token" in joined_cookies
    assert "HttpOnly" in joined_cookies
    assert issued_session_requests[0].access_extra == {"auth_method": "passkey"}
    assert issued_session_requests[0].principal_class == "customer"
    assert sync_calls


@pytest.mark.asyncio
async def test_passkey_session_pending_2fa_returns_tokenless_json_and_pending_cookie(monkeypatch) -> None:
    class AuthSessionIssuerStub:
        def __init__(self, **_kwargs) -> None:
            raise AssertionError("2FA-pending passkey auth must not issue a refresh session")

    async def sync_active_sessions_stub(_db) -> None:
        raise AssertionError("2FA-pending passkey auth must not sync active sessions")

    monkeypatch.setattr(passkeys, "AuthSessionIssuer", AuthSessionIssuerStub)
    monkeypatch.setattr(passkeys, "sync_active_sessions", sync_active_sessions_stub)

    auth_service = _AuthService()
    user = _user(totp_enabled=True)
    response = Response()
    result = await passkeys._issue_session_for_passkey(
        request=_request(),
        response=response,
        db=object(),
        auth_service=auth_service,
        user=user,
        credential=_credential(user.id),
        cookie_namespace="customer",
    )

    body = result.model_dump(mode="json")
    assert "access_token" not in body
    assert "refresh_token" not in body
    assert "expires_in" not in body
    assert "token_type" not in body
    assert body["auth_realm_key"] == "customer"
    assert body["principal_type"] == "customer"
    assert body["scope_family"] == "customer"
    assert body["requires_2fa"] is True
    assert body["tfa_token"] == "pending-2fa-token"
    assert auth_service.refresh_calls == 0
    set_cookie_headers = [
        value.decode("latin-1") for key, value in response.raw_headers if key.decode("latin-1").lower() == "set-cookie"
    ]
    joined_cookies = "\n".join(set_cookie_headers)
    assert "customer_access_token=pending-2fa-token" in joined_cookies
    assert "customer_refresh_token=browser-refresh-token" not in joined_cookies
    assert "HttpOnly" in joined_cookies
