"""S1-AUTH-002 email/password authentication flow coverage."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime
from hashlib import sha256
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import Request, Response
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.auth_service import AuthService
from src.application.use_cases.auth.login import LoginUseCase
from src.application.use_cases.auth.logout import LogoutUseCase
from src.application.use_cases.auth.refresh_token import RefreshTokenUseCase
from src.config.settings import settings
from src.domain.exceptions import InvalidCredentialsError
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.otp_code_model import OtpCodeModel
from src.infrastructure.database.models.refresh_token_model import RefreshToken
from src.infrastructure.remnawave.adapters import get_remnawave_adapter
from src.infrastructure.tasks.email_task_dispatcher import get_email_dispatcher
from src.main import app
from src.presentation.api.v1.auth.cookies import (
    clear_auth_cookies,
    get_or_create_web_device_cookie_value,
    set_auth_cookies,
    set_web_device_cookie,
)


class _ScalarResult:
    def __init__(self, value: Any) -> None:
        self._value = value

    def scalar_one_or_none(self) -> Any:
        return self._value


class _RowCountResult:
    rowcount = 1


class _FakeSession:
    def __init__(
        self,
        *,
        user: AdminUserModel | None = None,
        token_record: RefreshToken | None = None,
        principal_session: Any = None,
    ) -> None:
        self.user = user
        self.token_record = token_record
        self.principal_session = principal_session
        self.added: list[Any] = []
        self.flush_count = 0
        self.execute_count = 0

    def add(self, model: Any) -> None:
        if isinstance(model, RefreshToken) and model.id is None:
            model.id = uuid4()
        self.added.append(model)

    async def flush(self) -> None:
        self.flush_count += 1

    async def get(self, model: type[Any], id: UUID) -> Any:
        if model is AdminUserModel and self.user and self.user.id == id:
            return self.user
        return None

    async def execute(self, _statement: Any) -> _ScalarResult:
        self.execute_count += 1
        if self.execute_count == 1:
            return _ScalarResult(self.token_record)
        if self.execute_count == 2:
            return _ScalarResult(self.principal_session)
        if self.token_record is not None and self.token_record.revoked_at is None:
            self.token_record.revoked_at = datetime.now(UTC)
            self.token_record.revoked_reason = "logout"
        return _RowCountResult()


class _FakeUserRepo:
    def __init__(self, user: AdminUserModel | None) -> None:
        self.user = user

    async def get_by_login_or_email(
        self,
        login_or_email: str,
        *,
        realm_id: UUID | None = None,
        include_legacy_default: bool = False,
    ) -> AdminUserModel | None:
        del realm_id, include_legacy_default
        if not self.user:
            return None
        normalized = login_or_email.lower()
        if self.user.login == login_or_email or (self.user.email and self.user.email.lower() == normalized):
            return self.user
        return None


class _RecordingEmailDispatcher:
    def __init__(self) -> None:
        self.otp_emails: list[dict[str, Any]] = []

    async def dispatch_otp_email(
        self,
        *,
        email: str,
        otp_code: str,
        locale: str = "en-EN",
        is_resend: bool = False,
        channel: str = "web",
    ) -> str:
        self.otp_emails.append(
            {
                "email": email,
                "otp_code": otp_code,
                "locale": locale,
                "is_resend": is_resend,
                "channel": channel,
            }
        )
        return f"otp-email-{len(self.otp_emails)}"


def _build_cookie_request(
    *,
    host: str,
    scheme: str = "http",
    forwarded_host: str | None = None,
    forwarded_proto: str | None = None,
    origin: str | None = None,
) -> Request:
    headers = [(b"host", host.encode())]
    if forwarded_host is not None:
        headers.append((b"x-forwarded-host", forwarded_host.encode()))
    if forwarded_proto is not None:
        headers.append((b"x-forwarded-proto", forwarded_proto.encode()))
    if origin is not None:
        headers.append((b"origin", origin.encode()))

    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/auth/login",
            "scheme": scheme,
            "server": ("127.0.0.1", 13000),
            "headers": headers,
            "client": ("127.0.0.1", 54321),
        }
    )


def _cookie_headers(response: Response) -> list[str]:
    return [value.decode() for key, value in response.raw_headers if key == b"set-cookie"]


def _has_secure_cookie_attribute(header: str) -> bool:
    return any(part.strip().lower() == "secure" for part in header.split(";")[1:])


def _has_domain_cookie_attribute(header: str) -> bool:
    return any(part.strip().lower().startswith("domain=") for part in header.split(";")[1:])


async def _stage1_user(*, active: bool = True, verified: bool = True) -> AdminUserModel:
    password_hash = await AuthService.hash_password("Stage1StrongPassword123!")
    return AdminUserModel(
        id=uuid4(),
        login=f"stage1user{secrets.token_hex(4)}",
        email=f"stage1user{secrets.token_hex(4)}@example.com",
        password_hash=password_hash,
        role="viewer",
        is_active=active,
        is_email_verified=verified,
        failed_login_attempts=0,
        sign_in_count=0,
        language="en-EN",
        timezone="UTC",
    )


@pytest.mark.asyncio
async def test_stage1_login_rejects_unverified_email_user_before_session_creation() -> None:
    user = await _stage1_user(active=False, verified=False)
    session = _FakeSession()
    use_case = LoginUseCase(
        user_repo=_FakeUserRepo(user),  # type: ignore[arg-type]
        auth_service=AuthService(),
        session=session,  # type: ignore[arg-type]
    )

    with pytest.raises(InvalidCredentialsError):
        await use_case.execute(login_or_email=user.email or user.login, password="Stage1StrongPassword123!")

    assert session.added == []
    assert session.flush_count == 0


@pytest.mark.asyncio
async def test_stage1_verified_user_can_login_by_email_and_username_with_persistent_sessions() -> None:
    user = await _stage1_user()
    auth_service = AuthService()
    session = _FakeSession(user=user)
    realm_id = uuid4()
    use_case = LoginUseCase(
        user_repo=_FakeUserRepo(user),  # type: ignore[arg-type]
        auth_service=auth_service,
        session=session,  # type: ignore[arg-type]
    )

    email_result = await use_case.execute(
        login_or_email=user.email or user.login,
        password="Stage1StrongPassword123!",
        client_fingerprint="stage1-device",
        client_ip="203.0.113.10",
        user_agent="stage1-auth-test",
        auth_realm_id=realm_id,
        auth_realm_key="admin",
        audience="cybervpn:admin",
        principal_type="admin",
        scope_family="admin",
    )
    username_result = await use_case.execute(
        login_or_email=user.login,
        password="Stage1StrongPassword123!",
        client_fingerprint="stage1-device-2",
        client_ip="203.0.113.11",
        user_agent="stage1-auth-test",
        auth_realm_id=realm_id,
        auth_realm_key="admin",
        audience="cybervpn:admin",
        principal_type="admin",
        scope_family="admin",
    )

    assert email_result["access_token"]
    assert email_result["refresh_token"]
    assert username_result["access_token"]
    assert username_result["refresh_token"]
    assert auth_service.decode_token(email_result["access_token"], audience="cybervpn:admin")["type"] == "access"
    assert auth_service.decode_token(email_result["refresh_token"], audience="cybervpn:admin")["type"] == "refresh"
    assert user.sign_in_count == 2
    assert sum(isinstance(model, RefreshToken) for model in session.added) == 2


@pytest.mark.asyncio
async def test_stage1_refresh_rotation_and_logout_revoke_refresh_tokens() -> None:
    user = await _stage1_user()
    auth_service = AuthService()
    realm_id = uuid4()
    user.auth_realm_id = realm_id
    old_refresh, _old_jti, old_expires_at = auth_service.create_refresh_token(
        subject=str(user.id),
        fingerprint="stage1-device",
        audience="cybervpn:admin",
        principal_type="admin",
        realm_id=str(realm_id),
        realm_key="admin",
        scope_family="admin",
    )
    old_record = RefreshToken(
        id=uuid4(),
        user_id=user.id,
        auth_realm_id=realm_id,
        principal_class="admin",
        principal_subject=str(user.id),
        audience="cybervpn:admin",
        scope_family="admin",
        token_hash=sha256(old_refresh.encode()).hexdigest(),
        expires_at=old_expires_at,
        device_id="stage1-device",
        ip_address="203.0.113.20",
        user_agent="stage1-auth-test",
    )
    principal_session = SimpleNamespace(
        id=uuid4(),
        auth_realm_id=realm_id,
        principal_subject=str(user.id),
        principal_class="admin",
        audience="cybervpn:admin",
        scope_family="admin",
        current_refresh_token_id=old_record.id,
        refresh_token_id=old_record.id,
        user_device_id=None,
        access_token_jti="old-access-jti",
        status="active",
        expires_at=old_expires_at,
        revoked_at=None,
        last_seen_at=None,
    )
    old_record.principal_session_id = principal_session.id
    refresh_session = _FakeSession(user=user, token_record=old_record, principal_session=principal_session)
    refresh_use_case = RefreshTokenUseCase(auth_service=auth_service, session=refresh_session)  # type: ignore[arg-type]

    result = await refresh_use_case.execute(
        refresh_token=old_refresh,
        client_fingerprint="stage1-device",
        client_ip="203.0.113.21",
        user_agent="stage1-auth-test-refresh",
        auth_realm_id=realm_id,
        auth_realm_key="admin",
        audience="cybervpn:admin",
        principal_type="admin",
        scope_family="admin",
    )

    assert result["access_token"]
    assert result["refresh_token"]
    assert result["refresh_token"] != old_refresh
    assert old_record.revoked_at is not None

    new_record = next(model for model in refresh_session.added if isinstance(model, RefreshToken))
    logout_session = _FakeSession(token_record=new_record, principal_session=principal_session)
    await LogoutUseCase(session=logout_session).execute(result["refresh_token"])  # type: ignore[arg-type]

    assert new_record.revoked_at is not None

    replay_session = _FakeSession(user=user, token_record=old_record, principal_session=principal_session)
    replay_use_case = RefreshTokenUseCase(auth_service=auth_service, session=replay_session)  # type: ignore[arg-type]
    with pytest.raises(InvalidCredentialsError):
        await replay_use_case.execute(
            refresh_token=old_refresh,
            client_fingerprint="stage1-device",
            audience="cybervpn:admin",
        )


def test_stage1_auth_cookies_are_http_only_lax_secure_and_clearable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.presentation.api.v1.auth.cookies.settings.cookie_secure", True)
    monkeypatch.setattr("src.presentation.api.v1.auth.cookies.settings.cookie_domain", "cyber-vpn.net")
    monkeypatch.setattr("src.presentation.api.v1.auth.cookies.settings.access_token_expire_minutes", 15)
    monkeypatch.setattr("src.presentation.api.v1.auth.cookies.settings.refresh_token_expire_days", 7)

    response = Response()
    set_auth_cookies(response, "access-token-value", "refresh-token-value")
    cookie_headers = [value.decode() for key, value in response.raw_headers if key == b"set-cookie"]
    normalized = "\n".join(header.lower() for header in cookie_headers)

    assert "access_token=access-token-value" in normalized
    assert "refresh_token=refresh-token-value" in normalized
    assert "httponly" in normalized
    assert "secure" in normalized
    assert "samesite=lax" in normalized
    assert "domain=cyber-vpn.net" in normalized
    assert "path=/api" in normalized
    assert "max-age=900" in normalized
    assert "max-age=604800" in normalized

    clear_response = Response()
    clear_auth_cookies(clear_response)
    clear_headers = [value.decode().lower() for key, value in clear_response.raw_headers if key == b"set-cookie"]

    assert any("access_token=" in header and "max-age=0" in header for header in clear_headers)
    assert any("refresh_token=" in header and "max-age=0" in header for header in clear_headers)


def test_stage1_web_device_cookie_is_opaque_host_only_and_http_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.presentation.api.v1.auth.cookies.settings.environment", "production")
    monkeypatch.setattr("src.presentation.api.v1.auth.cookies.settings.cookie_secure", True)
    monkeypatch.setattr("src.presentation.api.v1.auth.cookies.settings.cookie_domain", "cyber-vpn.net")

    response = Response()
    request = _build_cookie_request(host="admin.cyber-vpn.net", scheme="https")
    device_cookie, should_set = get_or_create_web_device_cookie_value(request.cookies)

    assert should_set is True
    assert len(device_cookie) >= 32

    set_web_device_cookie(response, device_cookie, request=request)
    headers = [header.lower() for header in _cookie_headers(response)]

    assert any("__host-cvpn_device_id=" in header for header in headers)
    assert any("httponly" in header for header in headers)
    assert any("secure" in header for header in headers)
    assert any("samesite=lax" in header for header in headers)
    assert any("path=/" in header for header in headers)
    assert not any("domain=" in header for header in headers)


def test_stage1_auth_cookies_allow_insecure_only_for_local_http_loopback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("src.presentation.api.v1.auth.cookies.settings.environment", "development")
    monkeypatch.setattr("src.presentation.api.v1.auth.cookies.settings.cookie_secure", True)
    monkeypatch.setattr("src.presentation.api.v1.auth.cookies.settings.cookie_domain", "")

    response = Response()
    request = _build_cookie_request(host="127.0.0.1:13000", scheme="http")

    set_auth_cookies(response, "access-token-value", "refresh-token-value", request=request)

    assert _cookie_headers(response)
    assert not any(_has_secure_cookie_attribute(header) for header in _cookie_headers(response))


def test_stage1_auth_cookies_keep_secure_for_spoofed_forwarded_local_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("src.presentation.api.v1.auth.cookies.settings.environment", "local-stage")
    monkeypatch.setattr("src.presentation.api.v1.auth.cookies.settings.cookie_secure", True)
    monkeypatch.setattr("src.presentation.api.v1.auth.cookies.settings.cookie_domain", "")

    response = Response()
    request = _build_cookie_request(
        host="stage.cyber-vpn.net",
        scheme="http",
        forwarded_host="127.0.0.1:13000",
        forwarded_proto="http",
    )

    set_auth_cookies(response, "access-token-value", "refresh-token-value", request=request)

    assert _cookie_headers(response)
    assert all(_has_secure_cookie_attribute(header) for header in _cookie_headers(response))


def test_stage1_auth_cookies_force_secure_in_production_even_on_loopback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("src.presentation.api.v1.auth.cookies.settings.environment", "production")
    monkeypatch.setattr("src.presentation.api.v1.auth.cookies.settings.cookie_secure", False)
    monkeypatch.setattr("src.presentation.api.v1.auth.cookies.settings.cookie_domain", "")

    response = Response()
    request = _build_cookie_request(host="127.0.0.1:13000", scheme="http")

    set_auth_cookies(response, "access-token-value", "refresh-token-value", request=request)

    assert _cookie_headers(response)
    assert all(_has_secure_cookie_attribute(header) for header in _cookie_headers(response))


def test_stage1_customer_cookies_allow_local_http_origin_in_production_without_domain(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("src.presentation.api.v1.auth.cookies.settings.environment", "production")
    monkeypatch.setattr("src.presentation.api.v1.auth.cookies.settings.cookie_secure", True)
    monkeypatch.setattr("src.presentation.api.v1.auth.cookies.settings.cookie_domain", "cyber-vpn.net")

    response = Response()
    request = _build_cookie_request(
        host="127.0.0.1:13000",
        scheme="http",
        origin="http://127.0.0.1:13000",
    )

    set_auth_cookies(
        response,
        "access-token-value",
        "refresh-token-value",
        request=request,
        cookie_namespace="customer",
    )

    assert _cookie_headers(response)
    assert not any(_has_secure_cookie_attribute(header) for header in _cookie_headers(response))
    assert not any(_has_domain_cookie_attribute(header) for header in _cookie_headers(response))


def test_stage1_customer_cookies_keep_secure_domain_for_spoofed_local_origin_on_public_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("src.presentation.api.v1.auth.cookies.settings.environment", "production")
    monkeypatch.setattr("src.presentation.api.v1.auth.cookies.settings.cookie_secure", True)
    monkeypatch.setattr("src.presentation.api.v1.auth.cookies.settings.cookie_domain", "cyber-vpn.net")

    response = Response()
    request = _build_cookie_request(
        host="cyber-vpn.net",
        scheme="https",
        origin="http://127.0.0.1:13000",
    )

    set_auth_cookies(
        response,
        "access-token-value",
        "refresh-token-value",
        request=request,
        cookie_namespace="customer",
    )

    assert _cookie_headers(response)
    assert all(_has_secure_cookie_attribute(header) for header in _cookie_headers(response))
    assert all(_has_domain_cookie_attribute(header) for header in _cookie_headers(response))


@pytest.mark.parametrize(
    "origin",
    [
        "http://127.0.0.1:not-a-port",
        "http://[::1:13000",
    ],
)
def test_stage1_customer_cookies_keep_secure_domain_for_malformed_local_origin(
    monkeypatch: pytest.MonkeyPatch,
    origin: str,
) -> None:
    monkeypatch.setattr("src.presentation.api.v1.auth.cookies.settings.environment", "production")
    monkeypatch.setattr("src.presentation.api.v1.auth.cookies.settings.cookie_secure", True)
    monkeypatch.setattr("src.presentation.api.v1.auth.cookies.settings.cookie_domain", "cyber-vpn.net")

    response = Response()
    request = _build_cookie_request(
        host="127.0.0.1:13000",
        scheme="http",
        origin=origin,
    )

    set_auth_cookies(
        response,
        "access-token-value",
        "refresh-token-value",
        request=request,
        cookie_namespace="customer",
    )

    assert _cookie_headers(response)
    assert all(_has_secure_cookie_attribute(header) for header in _cookie_headers(response))
    assert all(_has_domain_cookie_attribute(header) for header in _cookie_headers(response))


@pytest.mark.parametrize(
    "origin",
    [
        "http://evil.example@127.0.0.1:13000",
        "http://127.0.0.1:13000/path",
        "http://127.0.0.1:13000?query=1",
        "http://127.0.0.1:13000#fragment",
    ],
)
def test_stage1_customer_cookies_keep_secure_domain_for_origin_with_extra_url_parts(
    monkeypatch: pytest.MonkeyPatch,
    origin: str,
) -> None:
    monkeypatch.setattr("src.presentation.api.v1.auth.cookies.settings.environment", "production")
    monkeypatch.setattr("src.presentation.api.v1.auth.cookies.settings.cookie_secure", True)
    monkeypatch.setattr("src.presentation.api.v1.auth.cookies.settings.cookie_domain", "cyber-vpn.net")

    response = Response()
    request = _build_cookie_request(
        host="127.0.0.1:13000",
        scheme="http",
        origin=origin,
    )

    set_auth_cookies(
        response,
        "access-token-value",
        "refresh-token-value",
        request=request,
        cookie_namespace="customer",
    )

    assert _cookie_headers(response)
    assert all(_has_secure_cookie_attribute(header) for header in _cookie_headers(response))
    assert all(_has_domain_cookie_attribute(header) for header in _cookie_headers(response))


def test_stage1_non_customer_cookies_keep_secure_domain_for_local_origin_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("src.presentation.api.v1.auth.cookies.settings.environment", "production")
    monkeypatch.setattr("src.presentation.api.v1.auth.cookies.settings.cookie_secure", True)
    monkeypatch.setattr("src.presentation.api.v1.auth.cookies.settings.cookie_domain", "cyber-vpn.net")

    response = Response()
    request = _build_cookie_request(
        host="127.0.0.1:13000",
        scheme="http",
        origin="http://127.0.0.1:13000",
    )

    set_auth_cookies(response, "access-token-value", "refresh-token-value", request=request, cookie_namespace="admin")

    assert _cookie_headers(response)
    assert all(_has_secure_cookie_attribute(header) for header in _cookie_headers(response))
    assert all(_has_domain_cookie_attribute(header) for header in _cookie_headers(response))


def test_stage1_auth_cookies_allow_ipv6_loopback_local_http_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("src.presentation.api.v1.auth.cookies.settings.environment", "development")
    monkeypatch.setattr("src.presentation.api.v1.auth.cookies.settings.cookie_secure", True)
    monkeypatch.setattr("src.presentation.api.v1.auth.cookies.settings.cookie_domain", "")

    response = Response()
    request = _build_cookie_request(host="[::1]:13000", scheme="http")

    set_auth_cookies(response, "access-token-value", "refresh-token-value", request=request)

    assert _cookie_headers(response)
    assert not any(_has_secure_cookie_attribute(header) for header in _cookie_headers(response))


@pytest.mark.integration
async def test_stage1_email_password_http_flow_register_verify_login_refresh_logout(
    async_client: AsyncClient,
    db: AsyncSession,
) -> None:
    register_data = {
        "login": f"s1auth{secrets.token_hex(4)}",
        "email": f"s1auth{secrets.token_hex(4)}@example.com",
        "password": "Stage1StrongPassword123!",
        "locale": "en-EN",
        "tos_accepted": True,
    }

    with patch("src.presentation.api.v1.auth.registration.get_email_dispatcher") as mock_email_dep:
        mock_email_dep.return_value = AsyncMock()
        with patch("src.config.settings.settings.registration_enabled", True):
            with patch("src.config.settings.settings.registration_invite_required", False):
                register_response = await async_client.post("/api/v1/auth/register", json=register_data)

    assert register_response.status_code == 201
    assert register_response.json()["is_active"] is False
    assert register_response.json()["is_email_verified"] is False
    assert not register_response.headers.get_list("set-cookie")

    unverified_login = await async_client.post(
        "/api/v1/auth/login",
        json={"login_or_email": register_data["email"], "password": register_data["password"]},
    )
    assert unverified_login.status_code == 401

    user = (await db.execute(select(AdminUserModel).where(AdminUserModel.email == register_data["email"]))).scalar_one()
    otp_record = (
        await db.execute(
            select(OtpCodeModel)
            .where(OtpCodeModel.user_id == user.id)
            .where(OtpCodeModel.purpose == "email_verification")
            .where(OtpCodeModel.verified_at.is_(None))
            .order_by(OtpCodeModel.created_at.desc())
        )
    ).scalar_one()

    mock_adapter = AsyncMock()
    mock_adapter.create_user = AsyncMock(return_value={"uuid": "stage1-remnawave-user"})
    app.dependency_overrides[get_remnawave_adapter] = lambda: mock_adapter
    try:
        verify_response = await async_client.post(
            "/api/v1/auth/verify-otp",
            json={"email": register_data["email"], "code": otp_record.code},
        )
    finally:
        app.dependency_overrides.pop(get_remnawave_adapter, None)

    assert verify_response.status_code == 200
    verify_body = verify_response.json()
    assert "access_token" not in verify_body
    assert "refresh_token" not in verify_body
    assert "token_type" not in verify_body
    assert "expires_in" not in verify_body
    assert verify_body["user"]["is_active"] is True
    assert verify_body["user"]["is_email_verified"] is True
    assert "httponly" in "\n".join(verify_response.headers.get_list("set-cookie")).lower()

    email_login = await async_client.post(
        "/api/v1/auth/login",
        json={"login_or_email": register_data["email"], "password": register_data["password"]},
    )
    username_login = await async_client.post(
        "/api/v1/auth/login",
        json={"login_or_email": register_data["login"], "password": register_data["password"]},
    )
    assert email_login.status_code == 200
    assert username_login.status_code == 200
    assert "httponly" in "\n".join(email_login.headers.get_list("set-cookie")).lower()

    async_client.cookies.update(username_login.cookies)
    refresh_response = await async_client.post("/api/v1/auth/refresh", json={})
    assert refresh_response.status_code == 200
    refresh_payload = refresh_response.json()
    assert "access_token" not in refresh_payload
    assert "refresh_token" not in refresh_payload
    assert "token_type" not in refresh_payload
    assert "expires_in" not in refresh_payload

    refreshed_token = refresh_response.cookies.get("customer_refresh_token")
    assert refreshed_token
    assert refreshed_token != username_login.cookies["customer_refresh_token"]

    logout_response = await async_client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refreshed_token},
    )
    assert logout_response.status_code == 204
    assert "max-age=0" in "\n".join(logout_response.headers.get_list("set-cookie")).lower()

    replay_response = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refreshed_token},
    )
    assert replay_response.status_code == 401


@pytest.mark.integration
async def test_stage1_register_existing_unverified_email_resends_code_without_duplicate_error(
    async_client: AsyncClient,
    db: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    email = f"s1resume{secrets.token_hex(4)}@example.com"
    register_data = {
        "login": f"s1resume{secrets.token_hex(4)}",
        "email": email,
        "password": "Stage1StrongPassword123!",
        "locale": "ru-RU",
        "tos_accepted": True,
    }
    dispatcher = _RecordingEmailDispatcher()
    app.dependency_overrides[get_email_dispatcher] = lambda: dispatcher

    try:
        with monkeypatch.context() as registration_patch:
            registration_patch.setattr(settings, "registration_enabled", True)
            registration_patch.setattr(settings, "registration_invite_required", False)
            first_response = await async_client.post("/api/v1/auth/register", json=register_data)
            second_response = await async_client.post("/api/v1/auth/register", json=register_data)

        assert first_response.status_code == 201
        assert second_response.status_code == 201
        assert second_response.json()["id"] == first_response.json()["id"]
        assert second_response.json()["is_active"] is False
        assert second_response.json()["is_email_verified"] is False
        assert (
            second_response.json()["message"] == "Verification code sent. Please check your email and enter the code."
        )

        users = (await db.execute(select(AdminUserModel).where(AdminUserModel.email == email))).scalars().all()
        assert len(users) == 1
        assert len(dispatcher.otp_emails) == 2
        assert dispatcher.otp_emails[0]["is_resend"] is False
        assert dispatcher.otp_emails[1]["is_resend"] is True
        assert dispatcher.otp_emails[1]["email"] == email
        assert dispatcher.otp_emails[1]["locale"] == "ru-RU"
        assert len(dispatcher.otp_emails[1]["otp_code"]) == 6
        assert dispatcher.otp_emails[1]["otp_code"].isdigit()
    finally:
        app.dependency_overrides.pop(get_email_dispatcher, None)
