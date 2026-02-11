"""Integration tests for 2FA cycle (TE-4).

Tests the full end-to-end 2FA workflows:
- Complete cycle: reauth → setup → verify → login+TOTP → disable
- Rate limiting on verify/validate attempts
- Security requirements (reauth, password+TOTP for disable)
- Backup/recovery codes generation

Requires: AsyncClient, test database, Redis.
"""

import secrets

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.admin_user_model import AdminUserModel


class TestComplete2FACycle:
    """Test complete 2FA lifecycle from setup to disable."""

    @pytest.mark.integration
    async def test_complete_2fa_cycle(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """
        Test complete 2FA cycle:
        1. User re-authenticates with password
        2. User sets up 2FA (gets TOTP secret)
        3. User verifies TOTP code
        4. 2FA is enabled
        5. User checks status (enabled)
        6. User disables 2FA (with password + TOTP)
        7. Gets recovery codes
        """
        # Create user with password
        from src.application.services.auth_service import AuthService
        auth_service = AuthService()
        password = "SecureP@ss123!"
        password_hash = await auth_service.hash_password(password)

        user = AdminUserModel(
            login=f"2fauser{secrets.token_hex(4)}",
            email=f"2fauser{secrets.token_hex(4)}@example.com",
            password_hash=password_hash,
            role="viewer",
            is_active=True,
            is_email_verified=True,
            totp_enabled=False,
            totp_secret=None,
        )
        db.add(user)
        await db.commit()

        # Login to get access token
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={"login_or_email": user.email, "password": password},
        )
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # Step 1: Re-authenticate with password
        reauth_response = await async_client.post(
            "/api/v1/2fa/reauth",
            json={"password": password},
            headers=headers,
        )
        assert reauth_response.status_code == 200
        reauth_data = reauth_response.json()
        assert reauth_data["valid_for_minutes"] == 5

        # Step 2: Setup 2FA
        setup_response = await async_client.post(
            "/api/v1/2fa/setup",
            headers=headers,
        )
        assert setup_response.status_code == 200
        setup_data = setup_response.json()
        assert "secret" in setup_data
        assert "qr_uri" in setup_data
        totp_secret = setup_data["secret"]

        # Step 3: Generate valid TOTP code
        from src.infrastructure.totp.totp_service import TOTPService
        totp_service = TOTPService()
        valid_code = totp_service.get_current_code(totp_secret)

        # Step 4: Verify TOTP code
        verify_response = await async_client.post(
            "/api/v1/2fa/verify",
            json={"code": valid_code},
            headers=headers,
        )
        assert verify_response.status_code == 200
        verify_data = verify_response.json()
        assert verify_data["status"] == "enabled"

        # Step 5: Check 2FA status
        status_response = await async_client.get(
            "/api/v1/2fa/status",
            headers=headers,
        )
        assert status_response.status_code == 200
        status_data = status_response.json()
        assert status_data["status"] == "enabled"

        # Step 6: Generate new TOTP code for disable
        disable_code = totp_service.get_current_code(totp_secret)

        # Step 7: Disable 2FA (requires password + TOTP)
        disable_response = await async_client.delete(
            "/api/v1/2fa/disable",
            json={"password": password, "code": disable_code},  # type: ignore[call-arg]
            headers=headers,
        )
        assert disable_response.status_code == 200
        disable_data = disable_response.json()
        assert disable_data["status"] == "disabled"
        assert "recovery_codes" in disable_data
        assert len(disable_data["recovery_codes"]) == 8

        # Step 8: Verify 2FA is disabled
        final_status_response = await async_client.get(
            "/api/v1/2fa/status",
            headers=headers,
        )
        assert final_status_response.status_code == 200
        assert final_status_response.json()["status"] == "disabled"

    @pytest.mark.integration
    async def test_setup_without_reauth_fails(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """
        Test that 2FA setup fails without prior re-authentication.
        """
        # Create user
        from src.application.services.auth_service import AuthService
        auth_service = AuthService()
        password = "SecureP@ss123!"
        password_hash = await auth_service.hash_password(password)

        user = AdminUserModel(
            login=f"noreauth{secrets.token_hex(4)}",
            email=f"noreauth{secrets.token_hex(4)}@example.com",
            password_hash=password_hash,
            role="viewer",
            is_active=True,
            is_email_verified=True,
        )
        db.add(user)
        await db.commit()

        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={"login_or_email": user.email, "password": password},
        )
        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # Try to setup without reauth
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
        """
        Test that 2FA setup fails if 2FA is already enabled.
        """
        # Create user with 2FA already enabled
        from src.application.services.auth_service import AuthService
        auth_service = AuthService()
        password = "SecureP@ss123!"
        password_hash = await auth_service.hash_password(password)

        from src.infrastructure.totp.totp_service import TOTPService
        totp_service = TOTPService()
        existing_secret = totp_service.generate_secret()

        user = AdminUserModel(
            login=f"already2fa{secrets.token_hex(4)}",
            email=f"already2fa{secrets.token_hex(4)}@example.com",
            password_hash=password_hash,
            role="viewer",
            is_active=True,
            is_email_verified=True,
            totp_enabled=True,
            totp_secret=existing_secret,
        )
        db.add(user)
        await db.commit()

        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={"login_or_email": user.email, "password": password},
        )
        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # Re-auth
        await async_client.post(
            "/api/v1/2fa/reauth",
            json={"password": password},
            headers=headers,
        )

        # Try to setup when already enabled
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
        """
        Test that 2FA verification is rate limited after 5 failed attempts.
        """
        # Create user and setup 2FA
        from src.application.services.auth_service import AuthService
        auth_service = AuthService()
        password = "SecureP@ss123!"
        password_hash = await auth_service.hash_password(password)

        user = AdminUserModel(
            login=f"ratelimit{secrets.token_hex(4)}",
            email=f"ratelimit{secrets.token_hex(4)}@example.com",
            password_hash=password_hash,
            role="viewer",
            is_active=True,
            is_email_verified=True,
        )
        db.add(user)
        await db.commit()

        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={"login_or_email": user.email, "password": password},
        )
        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # Re-auth and setup 2FA
        await async_client.post(
            "/api/v1/2fa/reauth",
            json={"password": password},
            headers=headers,
        )

        await async_client.post(
            "/api/v1/2fa/setup",
            headers=headers,
        )
        # Note: TOTP secret not needed - testing rate limit with intentionally wrong codes

        # Make 5 failed verification attempts
        for _ in range(5):
            await async_client.post(
                "/api/v1/2fa/verify",
                json={"code": "000000"},  # Wrong code
                headers=headers,
            )

        # 6th attempt should be rate limited
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
        """
        Test that TOTP validation is rate limited.
        """
        # Create user with 2FA enabled
        from src.application.services.auth_service import AuthService
        auth_service = AuthService()
        password = "SecureP@ss123!"
        password_hash = await auth_service.hash_password(password)

        from src.infrastructure.totp.totp_service import TOTPService
        totp_service = TOTPService()
        totp_secret = totp_service.generate_secret()

        user = AdminUserModel(
            login=f"validatelimit{secrets.token_hex(4)}",
            email=f"validatelimit{secrets.token_hex(4)}@example.com",
            password_hash=password_hash,
            role="viewer",
            is_active=True,
            is_email_verified=True,
            totp_enabled=True,
            totp_secret=totp_secret,
        )
        db.add(user)
        await db.commit()

        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={"login_or_email": user.email, "password": password},
        )
        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # Make 5 failed validation attempts
        for _ in range(5):
            await async_client.post(
                "/api/v1/2fa/validate",
                json={"code": "000000"},
                headers=headers,
            )

        # 6th attempt should be rate limited
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
        """
        Test that disabling 2FA requires both password and current TOTP code.
        """
        # Create user with 2FA enabled
        from src.application.services.auth_service import AuthService
        auth_service = AuthService()
        password = "SecureP@ss123!"
        password_hash = await auth_service.hash_password(password)

        from src.infrastructure.totp.totp_service import TOTPService
        totp_service = TOTPService()
        totp_secret = totp_service.generate_secret()

        user = AdminUserModel(
            login=f"disabletest{secrets.token_hex(4)}",
            email=f"disabletest{secrets.token_hex(4)}@example.com",
            password_hash=password_hash,
            role="viewer",
            is_active=True,
            is_email_verified=True,
            totp_enabled=True,
            totp_secret=totp_secret,
        )
        db.add(user)
        await db.commit()

        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={"login_or_email": user.email, "password": password},
        )
        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # Try to disable with wrong password
        valid_code = totp_service.get_current_code(totp_secret)
        wrong_password_response = await async_client.delete(
            "/api/v1/2fa/disable",
            json={"password": "WrongPassword123!", "code": valid_code},  # type: ignore[call-arg]
            headers=headers,
        )
        assert wrong_password_response.status_code == 401
        assert "password" in wrong_password_response.json()["detail"].lower()

        # Try to disable with wrong TOTP
        wrong_totp_response = await async_client.delete(
            "/api/v1/2fa/disable",
            json={"password": password, "code": "000000"},  # type: ignore[call-arg]
            headers=headers,
        )
        assert wrong_totp_response.status_code == 401

        # Disable with both correct
        correct_code = totp_service.get_current_code(totp_secret)
        success_response = await async_client.delete(
            "/api/v1/2fa/disable",
            json={"password": password, "code": correct_code},  # type: ignore[call-arg]
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
        """
        Test that disabling 2FA fails if it's not enabled.
        """
        # Create user without 2FA
        from src.application.services.auth_service import AuthService
        auth_service = AuthService()
        password = "SecureP@ss123!"
        password_hash = await auth_service.hash_password(password)

        user = AdminUserModel(
            login=f"notenabled{secrets.token_hex(4)}",
            email=f"notenabled{secrets.token_hex(4)}@example.com",
            password_hash=password_hash,
            role="viewer",
            is_active=True,
            is_email_verified=True,
            totp_enabled=False,
        )
        db.add(user)
        await db.commit()

        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={"login_or_email": user.email, "password": password},
        )
        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # Try to disable when not enabled
        disable_response = await async_client.delete(
            "/api/v1/2fa/disable",
            json={"password": password, "code": "123456"},  # type: ignore[call-arg]
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
        """
        Test validating a correct TOTP code.
        """
        # Create user with 2FA enabled
        from src.application.services.auth_service import AuthService
        auth_service = AuthService()
        password = "SecureP@ss123!"
        password_hash = await auth_service.hash_password(password)

        from src.infrastructure.totp.totp_service import TOTPService
        totp_service = TOTPService()
        totp_secret = totp_service.generate_secret()

        user = AdminUserModel(
            login=f"validate{secrets.token_hex(4)}",
            email=f"validate{secrets.token_hex(4)}@example.com",
            password_hash=password_hash,
            role="viewer",
            is_active=True,
            is_email_verified=True,
            totp_enabled=True,
            totp_secret=totp_secret,
        )
        db.add(user)
        await db.commit()

        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={"login_or_email": user.email, "password": password},
        )
        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # Generate valid TOTP code
        valid_code = totp_service.get_current_code(totp_secret)

        # Validate correct code
        validate_response = await async_client.post(
            "/api/v1/2fa/validate",
            json={"code": valid_code},
            headers=headers,
        )

        assert validate_response.status_code == 200
        validate_data = validate_response.json()
        assert validate_data["valid"] is True

    @pytest.mark.integration
    async def test_validate_incorrect_code(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """
        Test validating an incorrect TOTP code returns valid=false.
        """
        # Create user with 2FA enabled
        from src.application.services.auth_service import AuthService
        auth_service = AuthService()
        password = "SecureP@ss123!"
        password_hash = await auth_service.hash_password(password)

        from src.infrastructure.totp.totp_service import TOTPService
        totp_service = TOTPService()
        totp_secret = totp_service.generate_secret()

        user = AdminUserModel(
            login=f"invalidcode{secrets.token_hex(4)}",
            email=f"invalidcode{secrets.token_hex(4)}@example.com",
            password_hash=password_hash,
            role="viewer",
            is_active=True,
            is_email_verified=True,
            totp_enabled=True,
            totp_secret=totp_secret,
        )
        db.add(user)
        await db.commit()

        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={"login_or_email": user.email, "password": password},
        )
        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # Validate incorrect code
        validate_response = await async_client.post(
            "/api/v1/2fa/validate",
            json={"code": "000000"},
            headers=headers,
        )

        assert validate_response.status_code == 200
        validate_data = validate_response.json()
        assert validate_data["valid"] is False


class Test2FAStatus:
    """Test 2FA status endpoint."""

    @pytest.mark.integration
    async def test_status_when_enabled(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """
        Test status returns 'enabled' when 2FA is enabled.
        """
        # Create user with 2FA enabled
        from src.application.services.auth_service import AuthService
        auth_service = AuthService()
        password = "SecureP@ss123!"
        password_hash = await auth_service.hash_password(password)

        from src.infrastructure.totp.totp_service import TOTPService
        totp_service = TOTPService()
        totp_secret = totp_service.generate_secret()

        user = AdminUserModel(
            login=f"statusenabled{secrets.token_hex(4)}",
            email=f"statusenabled{secrets.token_hex(4)}@example.com",
            password_hash=password_hash,
            role="viewer",
            is_active=True,
            is_email_verified=True,
            totp_enabled=True,
            totp_secret=totp_secret,
        )
        db.add(user)
        await db.commit()

        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={"login_or_email": user.email, "password": password},
        )
        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

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
        """
        Test status returns 'disabled' when 2FA is not enabled.
        """
        # Create user without 2FA
        from src.application.services.auth_service import AuthService
        auth_service = AuthService()
        password = "SecureP@ss123!"
        password_hash = await auth_service.hash_password(password)

        user = AdminUserModel(
            login=f"statusdisabled{secrets.token_hex(4)}",
            email=f"statusdisabled{secrets.token_hex(4)}@example.com",
            password_hash=password_hash,
            role="viewer",
            is_active=True,
            is_email_verified=True,
            totp_enabled=False,
        )
        db.add(user)
        await db.commit()

        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={"login_or_email": user.email, "password": password},
        )
        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

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
        """
        Test that 8 recovery codes are generated when disabling 2FA.
        """
        # Create user with 2FA enabled
        from src.application.services.auth_service import AuthService
        auth_service = AuthService()
        password = "SecureP@ss123!"
        password_hash = await auth_service.hash_password(password)

        from src.infrastructure.totp.totp_service import TOTPService
        totp_service = TOTPService()
        totp_secret = totp_service.generate_secret()

        user = AdminUserModel(
            login=f"recovery{secrets.token_hex(4)}",
            email=f"recovery{secrets.token_hex(4)}@example.com",
            password_hash=password_hash,
            role="viewer",
            is_active=True,
            is_email_verified=True,
            totp_enabled=True,
            totp_secret=totp_secret,
        )
        db.add(user)
        await db.commit()

        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={"login_or_email": user.email, "password": password},
        )
        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # Disable 2FA
        valid_code = totp_service.get_current_code(totp_secret)
        disable_response = await async_client.delete(
            "/api/v1/2fa/disable",
            json={"password": password, "code": valid_code},  # type: ignore[call-arg]
            headers=headers,
        )

        assert disable_response.status_code == 200
        disable_data = disable_response.json()

        # Check recovery codes
        assert "recovery_codes" in disable_data
        recovery_codes = disable_data["recovery_codes"]
        assert len(recovery_codes) == 8
        assert all(isinstance(code, str) for code in recovery_codes)
        assert all(len(code) == 8 for code in recovery_codes)  # 4-byte hex = 8 chars
        assert all(code.isupper() for code in recovery_codes)
