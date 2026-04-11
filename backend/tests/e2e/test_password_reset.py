"""End-to-end tests for the password reset flow."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.auth_service import AuthService
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.otp_code_model import OtpCodeModel
from src.infrastructure.tasks.email_task_dispatcher import get_email_dispatcher
from src.main import app

pytestmark = [pytest.mark.e2e]

FORGOT_PASSWORD_URL = "/api/v1/auth/forgot-password"
RESET_PASSWORD_URL = "/api/v1/auth/reset-password"
LOGIN_URL = "/api/v1/auth/login"

ANTI_ENUMERATION_MESSAGE = "If this email is registered, a password reset code has been sent."
STRONG_PASSWORD = "N3wSecure!Pass99"


@pytest.fixture(autouse=True)
def _override_email_dispatcher():
    dispatcher = AsyncMock()

    async def _override():
        return dispatcher

    app.dependency_overrides[get_email_dispatcher] = _override
    yield dispatcher
    app.dependency_overrides.pop(get_email_dispatcher, None)


async def _create_user(
    db: AsyncSession,
    *,
    email: str | None = None,
    password: str = "OldP@ssw0rd123!",
) -> tuple[AdminUserModel, str]:
    auth_service = AuthService()
    password_hash = await auth_service.hash_password(password)
    suffix = secrets.token_hex(4)
    user = AdminUserModel(
        login=f"resetuser-{suffix}",
        email=email or f"reset-{suffix}@example.com",
        password_hash=password_hash,
        role="viewer",
        is_active=True,
        is_email_verified=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user, password


async def _create_reset_otp(
    db: AsyncSession,
    *,
    user: AdminUserModel,
    code: str = "123456",
    expires_at: datetime | None = None,
    attempts_used: int = 0,
    max_attempts: int = 5,
    verified_at: datetime | None = None,
) -> OtpCodeModel:
    otp = OtpCodeModel(
        user_id=user.id,
        code=code,
        purpose="password_reset",
        attempts_used=attempts_used,
        max_attempts=max_attempts,
        expires_at=expires_at or (datetime.now(UTC) + timedelta(hours=1)),
        verified_at=verified_at,
    )
    db.add(otp)
    await db.commit()
    await db.refresh(otp)
    return otp


async def _latest_reset_otp(db: AsyncSession, *, user_id) -> OtpCodeModel:
    result = await db.execute(
        select(OtpCodeModel)
        .where(OtpCodeModel.user_id == user_id)
        .where(OtpCodeModel.purpose == "password_reset")
        .order_by(OtpCodeModel.created_at.desc())
    )
    otp = result.scalar_one()
    return otp


class TestForgotPassword:
    async def test_forgot_password_returns_success_for_unknown_email(
        self,
        async_client: AsyncClient,
        _override_email_dispatcher,
    ):
        response = await async_client.post(
            FORGOT_PASSWORD_URL,
            json={"email": "nonexistent-user-abc@example.com"},
        )

        assert response.status_code == 200
        assert response.json()["message"] == ANTI_ENUMERATION_MESSAGE
        _override_email_dispatcher.send_password_reset_email.assert_not_called()

    async def test_forgot_password_returns_success_for_known_email(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
        _override_email_dispatcher,
    ):
        user, _ = await _create_user(db)

        response = await async_client.post(
            FORGOT_PASSWORD_URL,
            json={"email": user.email},
        )

        assert response.status_code == 200
        assert response.json()["message"] == ANTI_ENUMERATION_MESSAGE

        otp = await _latest_reset_otp(db, user_id=user.id)
        assert otp.code.isdigit()
        assert otp.verified_at is None
        _override_email_dispatcher.dispatch_password_reset_email.assert_called_once()

    async def test_forgot_password_invalid_email_format_returns_422(self, async_client: AsyncClient):
        response = await async_client.post(FORGOT_PASSWORD_URL, json={"email": "not-an-email"})
        assert response.status_code == 422

    async def test_forgot_password_empty_body_returns_422(self, async_client: AsyncClient):
        response = await async_client.post(FORGOT_PASSWORD_URL, json={})
        assert response.status_code == 422


class TestResetPasswordErrors:
    async def test_reset_password_invalid_code_returns_400(self, async_client: AsyncClient, db: AsyncSession):
        user, _ = await _create_user(db)
        await _create_reset_otp(db, user=user, code="123456")

        response = await async_client.post(
            RESET_PASSWORD_URL,
            json={
                "email": user.email,
                "code": "000000",
                "new_password": STRONG_PASSWORD,
            },
        )

        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "OTP_INVALID"

    async def test_reset_password_expired_code_returns_400(self, async_client: AsyncClient, db: AsyncSession):
        user, _ = await _create_user(db)
        await _create_reset_otp(
            db,
            user=user,
            code="123456",
            expires_at=datetime.now(UTC) - timedelta(minutes=1),
        )

        response = await async_client.post(
            RESET_PASSWORD_URL,
            json={
                "email": user.email,
                "code": "123456",
                "new_password": STRONG_PASSWORD,
            },
        )

        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "OTP_EXPIRED"

    async def test_reset_password_exhausted_attempts_returns_429(self, async_client: AsyncClient, db: AsyncSession):
        user, _ = await _create_user(db)
        await _create_reset_otp(
            db,
            user=user,
            code="123456",
            attempts_used=5,
            max_attempts=5,
        )

        response = await async_client.post(
            RESET_PASSWORD_URL,
            json={
                "email": user.email,
                "code": "123456",
                "new_password": STRONG_PASSWORD,
            },
        )

        assert response.status_code == 429
        assert response.json()["detail"]["code"] == "OTP_EXHAUSTED"

    async def test_reset_password_weak_password_returns_422(self, async_client: AsyncClient):
        response = await async_client.post(
            RESET_PASSWORD_URL,
            json={
                "email": "registered-user@example.com",
                "code": "123456",
                "new_password": "short",
            },
        )
        assert response.status_code == 422

    async def test_reset_password_common_password_returns_422(self, async_client: AsyncClient):
        response = await async_client.post(
            RESET_PASSWORD_URL,
            json={
                "email": "registered-user@example.com",
                "code": "123456",
                "new_password": "Password123!x",
            },
        )
        assert response.status_code in (400, 422)

    async def test_reset_password_no_uppercase_returns_422(self, async_client: AsyncClient):
        response = await async_client.post(
            RESET_PASSWORD_URL,
            json={
                "email": "registered-user@example.com",
                "code": "123456",
                "new_password": "n3wsecure!pass99",
            },
        )
        assert response.status_code == 422

    async def test_reset_password_no_special_char_returns_422(self, async_client: AsyncClient):
        response = await async_client.post(
            RESET_PASSWORD_URL,
            json={
                "email": "registered-user@example.com",
                "code": "123456",
                "new_password": "N3wSecurePass99",
            },
        )
        assert response.status_code == 422

    async def test_reset_password_invalid_code_format_returns_422(self, async_client: AsyncClient):
        response = await async_client.post(
            RESET_PASSWORD_URL,
            json={
                "email": "registered-user@example.com",
                "code": "abc",
                "new_password": STRONG_PASSWORD,
            },
        )
        assert response.status_code == 422

    async def test_reset_password_missing_fields_returns_422(self, async_client: AsyncClient):
        response = await async_client.post(RESET_PASSWORD_URL, json={})
        assert response.status_code == 422


class TestResetPasswordSuccess:
    async def test_reset_password_success_returns_200(self, async_client: AsyncClient, db: AsyncSession):
        user, _ = await _create_user(db)
        await _create_reset_otp(db, user=user, code="123456")

        response = await async_client.post(
            RESET_PASSWORD_URL,
            json={
                "email": user.email,
                "code": "123456",
                "new_password": STRONG_PASSWORD,
            },
        )

        assert response.status_code == 200
        assert "successfully" in response.json()["message"].lower()

    async def test_reset_password_then_login_with_new_password(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        user, old_password = await _create_user(db)

        forgot_response = await async_client.post(
            FORGOT_PASSWORD_URL,
            json={"email": user.email},
        )
        assert forgot_response.status_code == 200

        otp = await _latest_reset_otp(db, user_id=user.id)

        reset_response = await async_client.post(
            RESET_PASSWORD_URL,
            json={
                "email": user.email,
                "code": otp.code,
                "new_password": STRONG_PASSWORD,
            },
        )
        assert reset_response.status_code == 200

        old_login_response = await async_client.post(
            LOGIN_URL,
            json={"login_or_email": user.email, "password": old_password},
        )
        assert old_login_response.status_code == 401

        new_login_response = await async_client.post(
            LOGIN_URL,
            json={"login_or_email": user.email, "password": STRONG_PASSWORD},
        )
        assert new_login_response.status_code == 200
        assert "access_token" in new_login_response.json()
        assert "refresh_token" in new_login_response.json()

    async def test_reset_password_invalidates_otp_after_use(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        user, _ = await _create_user(db)
        await _create_reset_otp(db, user=user, code="123456")

        payload = {
            "email": user.email,
            "code": "123456",
            "new_password": STRONG_PASSWORD,
        }

        first_response = await async_client.post(RESET_PASSWORD_URL, json=payload)
        assert first_response.status_code == 200

        second_response = await async_client.post(RESET_PASSWORD_URL, json=payload)
        assert second_response.status_code == 400
        assert second_response.json()["detail"]["code"] in {"OTP_INVALID", "OTP_NOT_FOUND"}
