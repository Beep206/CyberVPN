"""S1-AUTH-002 email/password authentication flow coverage."""

from __future__ import annotations

import secrets
from hashlib import sha256
from typing import Any
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import Response
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
from src.presentation.api.v1.auth.cookies import clear_auth_cookies, set_auth_cookies


class _ScalarResult:
    def __init__(self, value: Any) -> None:
        self._value = value

    def scalar_one_or_none(self) -> Any:
        return self._value


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
        return _ScalarResult(self.principal_session)


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
    old_refresh, _old_jti, old_expires_at = auth_service.create_refresh_token(
        subject=str(user.id),
        fingerprint="stage1-device",
        audience="cybervpn:admin",
        principal_type="admin",
        realm_id=str(uuid4()),
        realm_key="admin",
        scope_family="admin",
    )
    old_record = RefreshToken(
        id=uuid4(),
        user_id=user.id,
        token_hash=sha256(old_refresh.encode()).hexdigest(),
        expires_at=old_expires_at,
        device_id="stage1-device",
        ip_address="203.0.113.20",
        user_agent="stage1-auth-test",
    )
    refresh_session = _FakeSession(user=user, token_record=old_record)
    refresh_use_case = RefreshTokenUseCase(auth_service=auth_service, session=refresh_session)  # type: ignore[arg-type]

    result = await refresh_use_case.execute(
        refresh_token=old_refresh,
        client_fingerprint="stage1-device",
        client_ip="203.0.113.21",
        user_agent="stage1-auth-test-refresh",
        audience="cybervpn:admin",
        principal_type="admin",
        scope_family="admin",
    )

    assert result["access_token"]
    assert result["refresh_token"]
    assert result["refresh_token"] != old_refresh
    assert old_record.revoked_at is not None

    new_record = next(model for model in refresh_session.added if isinstance(model, RefreshToken))
    logout_session = _FakeSession(token_record=new_record)
    await LogoutUseCase(session=logout_session).execute(result["refresh_token"])  # type: ignore[arg-type]

    assert new_record.revoked_at is not None

    replay_session = _FakeSession(user=user, token_record=old_record)
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

    user = (
        await db.execute(select(AdminUserModel).where(AdminUserModel.email == register_data["email"]))
    ).scalar_one()
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
    assert verify_body["access_token"]
    assert verify_body["refresh_token"]
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

    refresh_response = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": email_login.json()["refresh_token"]},
    )
    assert refresh_response.status_code == 200
    assert refresh_response.json()["refresh_token"] != email_login.json()["refresh_token"]

    logout_response = await async_client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_response.json()["refresh_token"]},
    )
    assert logout_response.status_code == 204
    assert "max-age=0" in "\n".join(logout_response.headers.get_list("set-cookie")).lower()

    replay_response = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_response.json()["refresh_token"]},
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
            second_response.json()["message"]
            == "Verification code sent. Please check your email and enter the code."
        )

        users = (
            await db.execute(select(AdminUserModel).where(AdminUserModel.email == email))
        ).scalars().all()
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
