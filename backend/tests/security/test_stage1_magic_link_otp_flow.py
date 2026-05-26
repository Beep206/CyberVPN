"""S1-AUTH-003 magic link / OTP authentication flow coverage."""

from __future__ import annotations

import secrets
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.auth_service import AuthService
from src.application.services.magic_link_service import MagicLinkService
from src.config.settings import settings
from src.infrastructure.cache.redis_client import get_redis_client
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.tasks.email_task_dispatcher import get_email_dispatcher
from src.main import app


class _RecordingEmailDispatcher:
    def __init__(self) -> None:
        self.magic_link_emails: list[dict] = []
        self.otp_emails: list[dict] = []

    async def dispatch_magic_link_email(
        self,
        *,
        email: str,
        token: str,
        otp_code: str = "",
        locale: str = "en-EN",
        is_resend: bool = False,
        channel: str = "web",
    ) -> str:
        self.magic_link_emails.append(
            {
                "email": email,
                "token": token,
                "otp_code": otp_code,
                "locale": locale,
                "is_resend": is_resend,
                "channel": channel,
            }
        )
        return f"magic-email-{len(self.magic_link_emails)}"

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


def _pipeline(execute_return: list) -> MagicMock:
    pipe = MagicMock()
    pipe.execute = AsyncMock(return_value=execute_return)
    pipe.incr = MagicMock(return_value=pipe)
    pipe.ttl = MagicMock(return_value=pipe)
    pipe.setex = MagicMock(return_value=pipe)
    return pipe


async def _clear_magic_link_state(email: str) -> None:
    redis_client = await get_redis_client()
    try:
        token = await redis_client.get(f"{MagicLinkService.EMAIL_TOKEN_PREFIX}{email}")
        keys = [
            f"{MagicLinkService.EMAIL_TOKEN_PREFIX}{email}",
            f"{MagicLinkService.OTP_PREFIX}{email}",
            f"{MagicLinkService.RATE_LIMIT_PREFIX}{email}",
        ]
        if token:
            token = token.decode() if isinstance(token, bytes) else token
            keys.extend(
                [
                    f"{MagicLinkService.PREFIX}{token}",
                    f"{MagicLinkService.CONSUMED_PREFIX}{token}",
                    f"{MagicLinkService.CONSUMED_REPLAY_PREFIX}{token}",
                ]
            )
        await redis_client.delete(*keys)
    finally:
        await redis_client.aclose()


async def _clear_auth_rate_limit_state() -> None:
    redis_client = await get_redis_client()
    try:
        keys = [key async for key in redis_client.scan_iter("cybervpn:rate_limit:*:s1_auth_sensitive")]
        if keys:
            await redis_client.delete(*keys)
    finally:
        await redis_client.aclose()


async def _create_verified_user(db: AsyncSession, *, email: str) -> AdminUserModel:
    user = AdminUserModel(
        login=f"s1magic{secrets.token_hex(4)}",
        email=email,
        password_hash=await AuthService.hash_password("Stage1StrongPassword123!"),
        role="viewer",
        is_active=True,
        is_email_verified=True,
        language="en-EN",
        timezone="UTC",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.mark.asyncio
async def test_stage1_magic_link_otp_generation_uses_secrets_randbelow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pipe = _pipeline([1, -2])
    mock_redis = AsyncMock()
    mock_redis.pipeline = MagicMock(return_value=pipe)
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.exists = AsyncMock(return_value=False)
    mock_redis.expire = AsyncMock()

    monkeypatch.setattr("src.application.services.magic_link_service.secrets.token_urlsafe", lambda _size: "t" * 64)
    monkeypatch.setattr("src.application.services.magic_link_service.secrets.randbelow", lambda upper: 0)

    token, otp_code = await MagicLinkService(mock_redis).generate("stage1@example.com")

    assert token == "t" * 64
    assert otp_code == "100000"
    assert pipe.setex.call_args_list[2].args == (
        "magic_link_otp:stage1@example.com",
        MagicLinkService.TTL_SECONDS,
        "100000",
    )


@pytest.mark.integration
async def test_stage1_magic_link_request_dispatches_link_and_token_login_sets_session(
    async_client: AsyncClient,
    db: AsyncSession,
) -> None:
    email = f"s1-magic-link-{secrets.token_hex(4)}@example.com"
    await _clear_auth_rate_limit_state()
    await _clear_magic_link_state(email)
    await _create_verified_user(db, email=email)
    dispatcher = _RecordingEmailDispatcher()
    app.dependency_overrides[get_email_dispatcher] = lambda: dispatcher

    try:
        request_response = await async_client.post(
            "/api/v1/auth/magic-link",
            json={"email": email.upper(), "locale": "ru-RU"},
        )
        assert request_response.status_code == 200
        assert request_response.json() == {
            "message": "If this email is registered, a login link has been sent."
        }
        assert len(dispatcher.magic_link_emails) == 1
        email_payload = dispatcher.magic_link_emails[0]
        assert email_payload["email"] == email
        assert email_payload["locale"] == "ru-RU"
        assert email_payload["is_resend"] is False
        assert email_payload["channel"] == "web"
        assert len(email_payload["token"]) >= 64
        assert len(email_payload["otp_code"]) == 6
        assert email_payload["otp_code"].isdigit()

        redis_client = await get_redis_client()
        try:
            stored_token = await redis_client.get(f"{MagicLinkService.EMAIL_TOKEN_PREFIX}{email}")
            stored_otp = await redis_client.get(f"{MagicLinkService.OTP_PREFIX}{email}")
        finally:
            await redis_client.aclose()

        assert stored_token == email_payload["token"]
        assert stored_otp == email_payload["otp_code"]

        verify_response = await async_client.post(
            "/api/v1/auth/magic-link/verify",
            json={"token": email_payload["token"]},
        )
        assert verify_response.status_code == 200
        verify_body = verify_response.json()
        assert verify_body["access_token"]
        assert verify_body["refresh_token"]
        assert verify_body["user"]["email"] == email
        assert "httponly" in "\n".join(verify_response.headers.get_list("set-cookie")).lower()

        me_response = await async_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {verify_body['access_token']}"},
        )
        assert me_response.status_code == 200
        assert me_response.json()["email"] == email
    finally:
        app.dependency_overrides.pop(get_email_dispatcher, None)
        await _clear_magic_link_state(email)


@pytest.mark.integration
async def test_stage1_magic_link_otp_login_consumes_code_and_blocks_replay(
    async_client: AsyncClient,
    db: AsyncSession,
) -> None:
    email = f"s1-magic-otp-{secrets.token_hex(4)}@example.com"
    await _clear_auth_rate_limit_state()
    await _clear_magic_link_state(email)
    await _create_verified_user(db, email=email)
    dispatcher = _RecordingEmailDispatcher()
    app.dependency_overrides[get_email_dispatcher] = lambda: dispatcher

    try:
        request_response = await async_client.post(
            "/api/v1/auth/magic-link",
            json={"email": email, "locale": "en-EN"},
        )
        assert request_response.status_code == 200
        otp_code = dispatcher.magic_link_emails[0]["otp_code"]

        otp_response = await async_client.post(
            "/api/v1/auth/magic-link/verify-otp",
            json={"email": email.upper(), "code": otp_code},
        )
        assert otp_response.status_code == 200
        otp_body = otp_response.json()
        assert otp_body["access_token"]
        assert otp_body["refresh_token"]
        assert otp_body["user"]["email"] == email
        assert "httponly" in "\n".join(otp_response.headers.get_list("set-cookie")).lower()

        replay_response = await async_client.post(
            "/api/v1/auth/magic-link/verify-otp",
            json={"email": email, "code": otp_code},
        )
        assert replay_response.status_code == 400
        assert "Invalid or expired OTP" in replay_response.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_email_dispatcher, None)
        await _clear_magic_link_state(email)


@pytest.mark.integration
async def test_stage1_magic_link_existing_totp_user_requires_2fa_without_session_cookie(
    async_client: AsyncClient,
    db: AsyncSession,
) -> None:
    email = f"s1-magic-2fa-{secrets.token_hex(4)}@example.com"
    await _clear_auth_rate_limit_state()
    await _clear_magic_link_state(email)
    user = await _create_verified_user(db, email=email)
    user.totp_enabled = True
    user.totp_secret = "JBSWY3DPEHPK3PXP"
    await db.commit()
    dispatcher = _RecordingEmailDispatcher()
    app.dependency_overrides[get_email_dispatcher] = lambda: dispatcher

    try:
        request_response = await async_client.post(
            "/api/v1/auth/magic-link",
            json={"email": email, "locale": "en-EN"},
        )
        assert request_response.status_code == 200

        verify_response = await async_client.post(
            "/api/v1/auth/magic-link/verify",
            json={"token": dispatcher.magic_link_emails[0]["token"]},
        )
        assert verify_response.status_code == 200
        verify_body = verify_response.json()
        assert verify_body["requires_2fa"] is True
        assert verify_body["tfa_token"]
        assert verify_body["access_token"] == ""
        assert verify_body["refresh_token"] == ""
        assert "set-cookie" not in verify_response.headers

        request_otp_response = await async_client.post(
            "/api/v1/auth/magic-link",
            json={"email": email, "locale": "en-EN"},
        )
        assert request_otp_response.status_code == 200
        otp_code = dispatcher.magic_link_emails[-1]["otp_code"]
        otp_response = await async_client.post(
            "/api/v1/auth/magic-link/verify-otp",
            json={"email": email, "code": otp_code},
        )
        assert otp_response.status_code == 200
        otp_body = otp_response.json()
        assert otp_body["requires_2fa"] is True
        assert otp_body["tfa_token"]
        assert otp_body["access_token"] == ""
        assert otp_body["refresh_token"] == ""
        assert "set-cookie" not in otp_response.headers
    finally:
        app.dependency_overrides.pop(get_email_dispatcher, None)
        await _clear_magic_link_state(email)


@pytest.mark.integration
async def test_stage1_magic_link_request_rate_limit_is_enforced_without_extra_dispatch(
    async_client: AsyncClient,
) -> None:
    email = f"s1-magic-rate-{secrets.token_hex(4)}@example.com"
    await _clear_auth_rate_limit_state()
    await _clear_magic_link_state(email)
    dispatcher = _RecordingEmailDispatcher()
    app.dependency_overrides[get_email_dispatcher] = lambda: dispatcher

    try:
        for index in range(MagicLinkService.MAX_REQUESTS_PER_HOUR):
            response = await async_client.post(
                "/api/v1/auth/magic-link",
                json={"email": email, "locale": "en-EN"},
            )
            assert response.status_code == 200, index
            assert response.json() == {
                "message": "If this email is registered, a login link has been sent."
            }

        rate_limited_response = await async_client.post(
            "/api/v1/auth/magic-link",
            json={"email": email, "locale": "en-EN"},
        )
        assert rate_limited_response.status_code == 429
        assert "too many requests" in rate_limited_response.json()["detail"].lower()
        assert len(dispatcher.magic_link_emails) == MagicLinkService.MAX_REQUESTS_PER_HOUR
    finally:
        app.dependency_overrides.pop(get_email_dispatcher, None)
        await _clear_magic_link_state(email)


@pytest.mark.integration
async def test_stage1_email_verification_otp_resend_rate_limit_dispatches_resend_email(
    async_client: AsyncClient,
    db: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    email = f"s1-otp-resend-{secrets.token_hex(4)}@example.com"
    login = f"s1otpresend{secrets.token_hex(4)}"
    await _clear_auth_rate_limit_state()
    dispatcher = _RecordingEmailDispatcher()
    app.dependency_overrides[get_email_dispatcher] = lambda: dispatcher
    monkeypatch.setattr(settings, "otp_resend_cooldown_seconds", 0)

    try:
        with monkeypatch.context() as registration_patch:
            registration_patch.setattr(settings, "registration_enabled", True)
            registration_patch.setattr(settings, "registration_invite_required", False)
            register_response = await async_client.post(
                "/api/v1/auth/register",
                json={
                    "login": login,
                    "email": email,
                    "password": "Stage1StrongPassword123!",
                    "locale": "en-EN",
                    "tos_accepted": True,
                },
            )
        assert register_response.status_code == 201

        for _ in range(3):
            resend_response = await async_client.post(
                "/api/v1/auth/resend-otp",
                json={"email": email, "locale": "en-EN"},
            )
            assert resend_response.status_code == 200

        rate_limited_response = await async_client.post(
            "/api/v1/auth/resend-otp",
            json={"email": email, "locale": "en-EN"},
        )
        assert rate_limited_response.status_code == 429
        assert rate_limited_response.json()["detail"]["code"] == "RATE_LIMITED"

        resend_payloads = [
            payload for payload in dispatcher.otp_emails if payload["email"] == email and payload["is_resend"] is True
        ]
        assert len(resend_payloads) == 3
        assert all(payload["is_resend"] is True for payload in resend_payloads)
        assert all(len(payload["otp_code"]) == 6 and payload["otp_code"].isdigit() for payload in resend_payloads)
    finally:
        app.dependency_overrides.pop(get_email_dispatcher, None)
        await db.rollback()
