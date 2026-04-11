"""Integration tests for the current 2FA cycle (TE-4)."""

import secrets

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.auth_service import AuthService
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.totp.totp_service import TOTPService


async def _create_admin_user(
    db: AsyncSession,
    *,
    totp_enabled: bool = False,
    totp_secret: str | None = None,
) -> tuple[AdminUserModel, str]:
    auth_service = AuthService()
    password = "SecureP@ss123!"
    user = AdminUserModel(
        login=f"twofa{secrets.token_hex(4)}",
        email=f"twofa{secrets.token_hex(4)}@example.com",
        password_hash=await auth_service.hash_password(password),
        role="viewer",
        is_active=True,
        is_email_verified=True,
        totp_enabled=totp_enabled,
        totp_secret=totp_secret,
        language="en",
        timezone="UTC",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user, password


def _access_headers(user: AdminUserModel) -> dict[str, str]:
    token = AuthService().create_access_token_simple(
        subject=str(user.id),
        role=user.role,
    )
    return {"Authorization": f"Bearer {token}"}


async def _login(async_client: AsyncClient, user: AdminUserModel, password: str):
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"login_or_email": user.email, "password": password},
    )
    assert response.status_code == 200
    return response


async def _reauth(async_client: AsyncClient, headers: dict[str, str], password: str):
    response = await async_client.post(
        "/api/v1/2fa/reauth",
        json={"password": password},
        headers=headers,
    )
    assert response.status_code == 200
    return response


async def _setup_2fa(
    async_client: AsyncClient,
    headers: dict[str, str],
) -> dict[str, str]:
    response = await async_client.post("/api/v1/2fa/setup", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert "secret" in payload
    assert "qr_uri" in payload
    return payload


class TestComplete2FACycle:
    """Test complete 2FA lifecycle from setup to login completion to disable."""

    @pytest.mark.integration
    async def test_complete_2fa_cycle(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        user, password = await _create_admin_user(db)

        login_response = await _login(async_client, user, password)
        initial_access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {initial_access_token}"}

        reauth_response = await _reauth(async_client, headers, password)
        assert reauth_response.json()["valid_for_minutes"] == 5

        setup_data = await _setup_2fa(async_client, headers)
        totp_secret = setup_data["secret"]
        totp_service = TOTPService()

        verify_response = await async_client.post(
            "/api/v1/2fa/verify",
            json={"code": totp_service.get_current_code(totp_secret)},
            headers=headers,
        )
        assert verify_response.status_code == 200
        assert verify_response.json()["status"] == "enabled"

        second_login_response = await _login(async_client, user, password)
        second_login_data = second_login_response.json()
        assert second_login_data["requires_2fa"] is True
        assert second_login_data["tfa_token"]

        complete_response = await async_client.post(
            "/api/v1/2fa/complete",
            json={"code": totp_service.get_current_code(totp_secret)},
            headers={"Authorization": f"Bearer {second_login_data['tfa_token']}"},
        )
        assert complete_response.status_code == 200
        completed_access_token = complete_response.json()["access_token"]
        completed_headers = {"Authorization": f"Bearer {completed_access_token}"}

        status_response = await async_client.get(
            "/api/v1/2fa/status",
            headers=completed_headers,
        )
        assert status_response.status_code == 200
        assert status_response.json()["status"] == "enabled"

        disable_response = await async_client.request(
            "DELETE",
            "/api/v1/2fa/disable",
            json={"password": password, "code": totp_service.get_current_code(totp_secret)},
            headers=completed_headers,
        )
        assert disable_response.status_code == 200
        disable_data = disable_response.json()
        assert disable_data["status"] == "disabled"
        assert "recovery_codes" in disable_data
        assert len(disable_data["recovery_codes"]) == 8

        final_status_response = await async_client.get(
            "/api/v1/2fa/status",
            headers=completed_headers,
        )
        assert final_status_response.status_code == 200
        assert final_status_response.json()["status"] == "disabled"

    @pytest.mark.integration
    async def test_setup_without_reauth_fails(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        user, _password = await _create_admin_user(db)
        headers = _access_headers(user)

        setup_response = await async_client.post(
            "/api/v1/2fa/setup",
            headers=headers,
        )

        assert setup_response.status_code == 401
        assert "re-authentication required" in setup_response.json()["detail"].lower()

    @pytest.mark.integration
    async def test_setup_when_already_enabled_fails(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        totp_service = TOTPService()
        user, password = await _create_admin_user(
            db,
            totp_enabled=True,
            totp_secret=totp_service.generate_secret(),
        )
        headers = _access_headers(user)

        await _reauth(async_client, headers, password)
        setup_response = await async_client.post(
            "/api/v1/2fa/setup",
            headers=headers,
        )

        assert setup_response.status_code == 400
        assert "already enabled" in setup_response.json()["detail"].lower()


class Test2FARateLimiting:
    """Test rate limiting on 2FA verification attempts."""

    @pytest.mark.integration
    async def test_verify_rate_limiting(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        user, password = await _create_admin_user(db)
        headers = _access_headers(user)

        await _reauth(async_client, headers, password)
        await _setup_2fa(async_client, headers)

        for _ in range(5):
            await async_client.post(
                "/api/v1/2fa/verify",
                json={"code": "000000"},
                headers=headers,
            )

        rate_limited_response = await async_client.post(
            "/api/v1/2fa/verify",
            json={"code": "000000"},
            headers=headers,
        )

        assert rate_limited_response.status_code == 429
        assert "too many" in rate_limited_response.json()["detail"].lower()

    @pytest.mark.integration
    async def test_validate_rate_limiting(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        totp_service = TOTPService()
        user, _password = await _create_admin_user(
            db,
            totp_enabled=True,
            totp_secret=totp_service.generate_secret(),
        )
        headers = _access_headers(user)

        for _ in range(5):
            await async_client.post(
                "/api/v1/2fa/validate",
                json={"code": "000000"},
                headers=headers,
            )

        rate_limited_response = await async_client.post(
            "/api/v1/2fa/validate",
            json={"code": "000000"},
            headers=headers,
        )

        assert rate_limited_response.status_code == 429


class Test2FADisableRequirements:
    """Test 2FA disable security requirements."""

    @pytest.mark.integration
    async def test_disable_requires_password_and_totp(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        totp_service = TOTPService()
        totp_secret = totp_service.generate_secret()
        user, password = await _create_admin_user(
            db,
            totp_enabled=True,
            totp_secret=totp_secret,
        )
        headers = _access_headers(user)

        wrong_password_response = await async_client.request(
            "DELETE",
            "/api/v1/2fa/disable",
            json={"password": "WrongPassword123!", "code": totp_service.get_current_code(totp_secret)},
            headers=headers,
        )
        assert wrong_password_response.status_code == 401
        assert "password" in wrong_password_response.json()["detail"].lower()

        wrong_totp_response = await async_client.request(
            "DELETE",
            "/api/v1/2fa/disable",
            json={"password": password, "code": "000000"},
            headers=headers,
        )
        assert wrong_totp_response.status_code == 401

        success_response = await async_client.request(
            "DELETE",
            "/api/v1/2fa/disable",
            json={"password": password, "code": totp_service.get_current_code(totp_secret)},
            headers=headers,
        )
        assert success_response.status_code == 200
        assert success_response.json()["status"] == "disabled"

    @pytest.mark.integration
    async def test_disable_when_not_enabled_fails(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        user, password = await _create_admin_user(db, totp_enabled=False)
        headers = _access_headers(user)

        disable_response = await async_client.request(
            "DELETE",
            "/api/v1/2fa/disable",
            json={"password": password, "code": "123456"},
            headers=headers,
        )

        assert disable_response.status_code == 400
        assert "not enabled" in disable_response.json()["detail"].lower()


class Test2FAValidation:
    """Test TOTP code validation."""

    @pytest.mark.integration
    async def test_validate_correct_code(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        totp_service = TOTPService()
        totp_secret = totp_service.generate_secret()
        user, _password = await _create_admin_user(
            db,
            totp_enabled=True,
            totp_secret=totp_secret,
        )
        headers = _access_headers(user)

        validate_response = await async_client.post(
            "/api/v1/2fa/validate",
            json={"code": totp_service.get_current_code(totp_secret)},
            headers=headers,
        )

        assert validate_response.status_code == 200
        assert validate_response.json()["valid"] is True

    @pytest.mark.integration
    async def test_validate_incorrect_code(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        totp_service = TOTPService()
        user, _password = await _create_admin_user(
            db,
            totp_enabled=True,
            totp_secret=totp_service.generate_secret(),
        )
        headers = _access_headers(user)

        validate_response = await async_client.post(
            "/api/v1/2fa/validate",
            json={"code": "000000"},
            headers=headers,
        )

        assert validate_response.status_code == 200
        assert validate_response.json()["valid"] is False


class Test2FAStatus:
    """Test 2FA status endpoint."""

    @pytest.mark.integration
    async def test_status_when_enabled(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        totp_service = TOTPService()
        user, _password = await _create_admin_user(
            db,
            totp_enabled=True,
            totp_secret=totp_service.generate_secret(),
        )
        headers = _access_headers(user)

        status_response = await async_client.get(
            "/api/v1/2fa/status",
            headers=headers,
        )

        assert status_response.status_code == 200
        assert status_response.json()["status"] == "enabled"

    @pytest.mark.integration
    async def test_status_when_disabled(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        user, _password = await _create_admin_user(db, totp_enabled=False)
        headers = _access_headers(user)

        status_response = await async_client.get(
            "/api/v1/2fa/status",
            headers=headers,
        )

        assert status_response.status_code == 200
        assert status_response.json()["status"] == "disabled"


class Test2FARecoveryCodes:
    """Test recovery codes generation on 2FA disable."""

    @pytest.mark.integration
    async def test_recovery_codes_generated_on_disable(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        totp_service = TOTPService()
        totp_secret = totp_service.generate_secret()
        user, password = await _create_admin_user(
            db,
            totp_enabled=True,
            totp_secret=totp_secret,
        )
        headers = _access_headers(user)

        disable_response = await async_client.request(
            "DELETE",
            "/api/v1/2fa/disable",
            json={"password": password, "code": totp_service.get_current_code(totp_secret)},
            headers=headers,
        )

        assert disable_response.status_code == 200
        recovery_codes = disable_response.json()["recovery_codes"]
        assert len(recovery_codes) == 8
        assert all(isinstance(code, str) for code in recovery_codes)
        assert all(len(code) == 8 for code in recovery_codes)
        assert all(code == code.upper() for code in recovery_codes)
