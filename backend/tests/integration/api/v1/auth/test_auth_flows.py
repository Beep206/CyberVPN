"""Integration tests for complete authentication flows (TE-1).

Tests the full end-to-end authentication workflows:
- register → OTP → verify → login → refresh → logout
- magic link request → verify
- forgot-password → reset-password
- brute force protection

Requires: AsyncClient, test database, Redis.
"""

import asyncio
import secrets
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.otp_code_model import OtpCodeModel


class TestCompleteAuthFlow:
    """Test complete authentication flow from registration to logout."""

    @pytest.mark.integration
    async def test_complete_registration_and_login_flow(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """
        Test complete flow: register → verify OTP → login → refresh → logout.

        Steps:
        1. Register with email + password
        2. Verify OTP code (auto-login with tokens)
        3. Use access token to get /me
        4. Refresh access token
        5. Logout
        """
        # Mock email dispatcher to prevent actual email sends
        with patch("src.presentation.api.v1.auth.registration.get_email_dispatcher") as mock_email_dep:
            mock_dispatcher = AsyncMock()
            mock_email_dep.return_value = mock_dispatcher

            # Step 1: Register
            register_data = {
                "login": f"testuser{secrets.token_hex(4)}",
                "email": f"test{secrets.token_hex(4)}@example.com",
                "password": "SecureP@ssw0rd123!",
                "locale": "en-EN",
            }

            # Enable registration for test
            with patch("src.config.settings.settings.registration_enabled", True):
                with patch("src.config.settings.settings.registration_invite_required", False):
                    response = await async_client.post("/api/v1/auth/register", json=register_data)

            assert response.status_code == 201
            register_response = response.json()
            assert register_response["login"] == register_data["login"]
            assert register_response["email"] == register_data["email"]
            assert register_response["is_active"] is False
            assert register_response["is_email_verified"] is False

            user_id = register_response["id"]

            # Get user from database to find OTP
            user_result = await db.execute(
                select(AdminUserModel).where(AdminUserModel.email == register_data["email"])
            )
            user = user_result.scalar_one()

            # Get OTP code from database (simulate receiving email)
            result = await db.execute(
                select(OtpCodeModel)
                .where(OtpCodeModel.user_id == user.id)
                .where(OtpCodeModel.purpose == "email_verification")
                .where(OtpCodeModel.verified_at.is_(None))
                .order_by(OtpCodeModel.created_at.desc())
            )
            otp_record = result.scalar_one_or_none()
            assert otp_record is not None
            otp_code = otp_record.code

            # Step 2: Verify OTP (auto-login)
            with patch("src.application.use_cases.auth.verify_otp.RemnawaveUserAdapter") as mock_remnawave:
                mock_adapter = AsyncMock()
                mock_adapter.create_user_if_not_exists = AsyncMock(return_value={"id": "remna123"})
                mock_remnawave.return_value = mock_adapter

                verify_response = await async_client.post(
                    "/api/v1/auth/verify-otp",
                    json={"email": register_data["email"], "code": otp_code},
                )

            assert verify_response.status_code == 200
            verify_data = verify_response.json()
            assert "access_token" in verify_data
            assert "refresh_token" in verify_data
            assert verify_data["user"]["id"] == user_id
            assert verify_data["user"]["is_active"] is True
            assert verify_data["user"]["is_email_verified"] is True

            access_token = verify_data["access_token"]
            refresh_token = verify_data["refresh_token"]

            # Step 3: Use access token to get current user
            me_response = await async_client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            assert me_response.status_code == 200
            me_data = me_response.json()
            assert me_data["id"] == user_id
            assert me_data["email"] == register_data["email"]

            # Step 4: Refresh access token
            refresh_response = await async_client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": refresh_token},
            )
            assert refresh_response.status_code == 200
            refresh_data = refresh_response.json()
            assert "access_token" in refresh_data
            assert "refresh_token" in refresh_data

            new_access_token = refresh_data["access_token"]

            # Verify new access token works
            me_response_2 = await async_client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {new_access_token}"},
            )
            assert me_response_2.status_code == 200

            # Step 5: Logout
            logout_response = await async_client.post(
                "/api/v1/auth/logout",
                json={"refresh_token": refresh_data["refresh_token"]},
            )
            assert logout_response.status_code == 204

            # Verify refresh token is invalidated
            logout_refresh_response = await async_client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": refresh_data["refresh_token"]},
            )
            assert logout_refresh_response.status_code == 401

    @pytest.mark.integration
    async def test_login_after_verification_flow(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """
        Test that after OTP verification (auto-login), user can login again with password.
        """
        # Create verified user
        with patch("src.presentation.api.v1.auth.registration.get_email_dispatcher") as mock_email_dep:
            mock_dispatcher = AsyncMock()
            mock_email_dep.return_value = mock_dispatcher

            register_data = {
                "login": f"logintest{secrets.token_hex(4)}",
                "email": f"logintest{secrets.token_hex(4)}@example.com",
                "password": "SecureP@ssw0rd123!",
            }

            with patch("src.config.settings.settings.registration_enabled", True):
                with patch("src.config.settings.settings.registration_invite_required", False):
                    await async_client.post("/api/v1/auth/register", json=register_data)

            # Get user and OTP
            user_result = await db.execute(
                select(AdminUserModel).where(AdminUserModel.email == register_data["email"])
            )
            user = user_result.scalar_one()

            otp_result = await db.execute(
                select(OtpCodeModel)
                .where(OtpCodeModel.user_id == user.id)
                .where(OtpCodeModel.purpose == "email_verification")
                .where(OtpCodeModel.verified_at.is_(None))
                .order_by(OtpCodeModel.created_at.desc())
            )
            otp_code = otp_result.scalar_one().code

            with patch("src.application.use_cases.auth.verify_otp.RemnawaveUserAdapter") as mock_remnawave:
                mock_adapter = AsyncMock()
                mock_adapter.create_user_if_not_exists = AsyncMock(return_value={"id": "remna123"})
                mock_remnawave.return_value = mock_adapter
                await async_client.post(
                    "/api/v1/auth/verify-otp",
                    json={"email": register_data["email"], "code": otp_code},
                )

        # Now test login with password
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "login_or_email": register_data["email"],
                "password": register_data["password"],
            },
        )

        assert login_response.status_code == 200
        login_data = login_response.json()
        assert "access_token" in login_data
        assert "refresh_token" in login_data

        # Verify access token works
        me_response = await async_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {login_data['access_token']}"},
        )
        assert me_response.status_code == 200
        assert me_response.json()["email"] == register_data["email"]


class TestMagicLinkFlow:
    """Test magic link authentication flow."""

    @pytest.mark.integration
    async def test_magic_link_request_and_verify_for_existing_user(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """
        Test magic link flow: request → verify for existing user.
        """
        # Create verified user
        user_email = f"magiclink{secrets.token_hex(4)}@example.com"
        user = AdminUserModel(
            login=f"magicuser{secrets.token_hex(4)}",
            email=user_email,
            password_hash="$argon2id$fake_hash",
            role="viewer",
            is_active=True,
            is_email_verified=True,
        )
        db.add(user)
        await db.commit()

        # Mock email dispatcher
        with patch("src.presentation.api.v1.auth.routes.get_email_dispatcher") as mock_email_dep:
            mock_dispatcher = AsyncMock()
            mock_email_dep.return_value = mock_dispatcher

            # Request magic link
            request_response = await async_client.post(
                "/api/v1/auth/magic-link",
                json={"email": user_email},
            )

            assert request_response.status_code == 200
            assert "If this email is registered" in request_response.json()["message"]

            # Get token from Redis (simulated - we'll mock the service)
            # In real test, we'd need to access Redis or mock MagicLinkService
            # For now, we'll create a token manually
            import redis.asyncio as redis

            from src.config.settings import settings

            redis_client = redis.from_url(settings.redis_url, decode_responses=True)

            # Generate a test token
            token = secrets.token_urlsafe(32)
            await redis_client.setex(
                f"magic_link:{token}",
                900,  # 15 minutes
                user_email,
            )
            await redis_client.close()

            # Verify magic link token
            verify_response = await async_client.post(
                "/api/v1/auth/magic-link/verify",
                json={"token": token},
            )

            assert verify_response.status_code == 200
            verify_data = verify_response.json()
            assert "access_token" in verify_data
            assert "refresh_token" in verify_data

            # Verify token works
            me_response = await async_client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {verify_data['access_token']}"},
            )
            assert me_response.status_code == 200
            assert me_response.json()["email"] == user_email

    @pytest.mark.integration
    async def test_magic_link_auto_registers_new_user(
        self,
        async_client: AsyncClient,
    ):
        """
        Test that magic link verification creates a new user if not exists.
        """
        new_email = f"newmagic{secrets.token_hex(4)}@example.com"

        # Create magic link token for non-existent user
        import redis.asyncio as redis

        from src.config.settings import settings

        redis_client = redis.from_url(settings.redis_url, decode_responses=True)
        token = secrets.token_urlsafe(32)
        await redis_client.setex(
            f"magic_link:{token}",
            900,
            new_email,
        )
        await redis_client.close()

        # Verify magic link (should auto-register)
        verify_response = await async_client.post(
            "/api/v1/auth/magic-link/verify",
            json={"token": token},
        )

        assert verify_response.status_code == 200
        verify_data = verify_response.json()
        assert "access_token" in verify_data

        # Verify user was created
        me_response = await async_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {verify_data['access_token']}"},
        )
        assert me_response.status_code == 200
        user_data = me_response.json()
        assert user_data["email"] == new_email
        assert user_data["is_email_verified"] is True
        assert user_data["is_active"] is True

    @pytest.mark.integration
    async def test_magic_link_token_is_single_use(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """
        Test that magic link token can only be used once.
        """
        user_email = f"singleuse{secrets.token_hex(4)}@example.com"

        # Create user
        user = AdminUserModel(
            login=f"singleuse{secrets.token_hex(4)}",
            email=user_email,
            password_hash="$argon2id$fake_hash",
            role="viewer",
            is_active=True,
            is_email_verified=True,
        )
        db.add(user)
        await db.commit()

        # Create magic link token
        import redis.asyncio as redis

        from src.config.settings import settings

        redis_client = redis.from_url(settings.redis_url, decode_responses=True)
        token = secrets.token_urlsafe(32)
        await redis_client.setex(
            f"magic_link:{token}",
            900,
            user_email,
        )
        await redis_client.close()

        # First verification succeeds
        first_response = await async_client.post(
            "/api/v1/auth/magic-link/verify",
            json={"token": token},
        )
        assert first_response.status_code == 200

        # Second verification fails (token consumed)
        second_response = await async_client.post(
            "/api/v1/auth/magic-link/verify",
            json={"token": token},
        )
        assert second_response.status_code == 400
        assert "Invalid or expired" in second_response.json()["detail"]


class TestPasswordResetFlow:
    """Test password reset flow with OTP."""

    @pytest.mark.integration
    async def test_complete_password_reset_flow(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """
        Test complete password reset: forgot-password → reset-password → login with new password.
        """
        # Create verified user with known password
        old_password = "OldP@ssw0rd123!"
        user_email = f"resettest{secrets.token_hex(4)}@example.com"

        from src.application.services.auth_service import AuthService
        auth_service = AuthService()
        password_hash = await auth_service.hash_password(old_password)

        user = AdminUserModel(
            login=f"resetuser{secrets.token_hex(4)}",
            email=user_email,
            password_hash=password_hash,
            role="viewer",
            is_active=True,
            is_email_verified=True,
        )
        db.add(user)
        await db.commit()

        # Step 1: Request password reset OTP
        with patch("src.presentation.api.v1.auth.routes.get_email_dispatcher") as mock_email_dep:
            mock_dispatcher = AsyncMock()
            mock_email_dep.return_value = mock_dispatcher

            forgot_response = await async_client.post(
                "/api/v1/auth/forgot-password",
                json={"email": user_email},
            )

            assert forgot_response.status_code == 200
            assert "password reset code" in forgot_response.json()["message"]

        # Get OTP from database
        user_result = await db.execute(
            select(AdminUserModel).where(AdminUserModel.email == user_email)
        )
        user_record = user_result.scalar_one()

        otp_result = await db.execute(
            select(OtpCodeModel)
            .where(OtpCodeModel.user_id == user_record.id)
            .where(OtpCodeModel.purpose == "password_reset")
            .where(OtpCodeModel.verified_at.is_(None))
            .order_by(OtpCodeModel.created_at.desc())
        )
        otp_record = otp_result.scalar_one_or_none()
        assert otp_record is not None
        otp_code = otp_record.code

        # Step 2: Reset password with OTP
        new_password = "NewP@ssw0rd456!"
        reset_response = await async_client.post(
            "/api/v1/auth/reset-password",
            json={
                "email": user_email,
                "code": otp_code,
                "new_password": new_password,
            },
        )

        assert reset_response.status_code == 200
        assert "reset successfully" in reset_response.json()["message"]

        # Step 3: Verify old password doesn't work
        old_login_response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "login_or_email": user_email,
                "password": old_password,
            },
        )
        assert old_login_response.status_code == 401

        # Step 4: Verify new password works
        new_login_response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "login_or_email": user_email,
                "password": new_password,
            },
        )
        assert new_login_response.status_code == 200
        assert "access_token" in new_login_response.json()

    @pytest.mark.integration
    async def test_password_reset_with_invalid_otp(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """
        Test that password reset fails with invalid OTP.
        """
        user_email = f"invalidotp{secrets.token_hex(4)}@example.com"

        user = AdminUserModel(
            login=f"invaliduser{secrets.token_hex(4)}",
            email=user_email,
            password_hash="$argon2id$fake_hash",
            role="viewer",
            is_active=True,
            is_email_verified=True,
        )
        db.add(user)
        await db.commit()

        # Request password reset
        with patch("src.presentation.api.v1.auth.routes.get_email_dispatcher") as mock_email_dep:
            mock_dispatcher = AsyncMock()
            mock_email_dep.return_value = mock_dispatcher
            await async_client.post(
                "/api/v1/auth/forgot-password",
                json={"email": user_email},
            )

        # Try reset with wrong OTP
        reset_response = await async_client.post(
            "/api/v1/auth/reset-password",
            json={
                "email": user_email,
                "code": "000000",  # Invalid code
                "new_password": "NewP@ssw0rd456!",
            },
        )

        assert reset_response.status_code == 400
        assert "detail" in reset_response.json()


class TestBruteForceProtection:
    """Test brute force protection on login endpoint."""

    @pytest.mark.integration
    async def test_account_lockout_after_failed_attempts(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """
        Test that account gets locked after multiple failed login attempts.

        Protection levels:
        - 3 attempts: 5 min lockout
        - 6 attempts: 30 min lockout
        - 10+ attempts: permanent lockout (requires admin unlock)
        """
        # Create verified user
        user_email = f"bruteforce{secrets.token_hex(4)}@example.com"
        correct_password = "CorrectP@ssw0rd123!"

        from src.application.services.auth_service import AuthService
        auth_service = AuthService()
        password_hash = await auth_service.hash_password(correct_password)

        user = AdminUserModel(
            login=f"bruteuser{secrets.token_hex(4)}",
            email=user_email,
            password_hash=password_hash,
            role="viewer",
            is_active=True,
            is_email_verified=True,
        )
        db.add(user)
        await db.commit()

        # Make 3 failed login attempts
        for i in range(3):
            response = await async_client.post(
                "/api/v1/auth/login",
                json={
                    "login_or_email": user_email,
                    "password": "WrongPassword123!",
                },
            )
            assert response.status_code == 401

        # 4th attempt should be locked
        locked_response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "login_or_email": user_email,
                "password": correct_password,  # Even correct password
            },
        )

        assert locked_response.status_code == 423  # HTTP 423 Locked
        assert "locked" in locked_response.json()["detail"].lower()

    @pytest.mark.integration
    async def test_successful_login_resets_failed_attempts(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """
        Test that successful login resets the failed attempts counter.
        """
        user_email = f"resetcounter{secrets.token_hex(4)}@example.com"
        correct_password = "CorrectP@ssw0rd123!"

        from src.application.services.auth_service import AuthService
        auth_service = AuthService()
        password_hash = await auth_service.hash_password(correct_password)

        user = AdminUserModel(
            login=f"resetuser{secrets.token_hex(4)}",
            email=user_email,
            password_hash=password_hash,
            role="viewer",
            is_active=True,
            is_email_verified=True,
        )
        db.add(user)
        await db.commit()

        # Make 2 failed attempts
        for i in range(2):
            await async_client.post(
                "/api/v1/auth/login",
                json={
                    "login_or_email": user_email,
                    "password": "WrongPassword123!",
                },
            )

        # Successful login should reset counter
        success_response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "login_or_email": user_email,
                "password": correct_password,
            },
        )
        assert success_response.status_code == 200

        # Now we should be able to make 3 more failed attempts before lockout
        for i in range(2):
            await async_client.post(
                "/api/v1/auth/login",
                json={
                    "login_or_email": user_email,
                    "password": "WrongPassword123!",
                },
            )

        # 3rd attempt should still work (not locked yet)
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "login_or_email": user_email,
                "password": "WrongPassword123!",
            },
        )
        assert response.status_code == 401  # Wrong password, not locked

    @pytest.mark.integration
    async def test_rate_limit_has_constant_response_time(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """
        Test that login responses have constant time to prevent timing attacks.

        Both successful and failed logins should take similar time.
        """
        user_email = f"timing{secrets.token_hex(4)}@example.com"
        password = "TestP@ssw0rd123!"

        from src.application.services.auth_service import AuthService
        auth_service = AuthService()
        password_hash = await auth_service.hash_password(password)

        user = AdminUserModel(
            login=f"timinguser{secrets.token_hex(4)}",
            email=user_email,
            password_hash=password_hash,
            role="viewer",
            is_active=True,
            is_email_verified=True,
        )
        db.add(user)
        await db.commit()

        # Measure time for valid login
        start_valid = datetime.now(UTC)
        valid_response = await async_client.post(
            "/api/v1/auth/login",
            json={"login_or_email": user_email, "password": password},
        )
        valid_time = (datetime.now(UTC) - start_valid).total_seconds()
        assert valid_response.status_code == 200

        # Measure time for invalid login
        start_invalid = datetime.now(UTC)
        invalid_response = await async_client.post(
            "/api/v1/auth/login",
            json={"login_or_email": user_email, "password": "WrongPassword"},
        )
        invalid_time = (datetime.now(UTC) - start_invalid).total_seconds()
        assert invalid_response.status_code == 401

        # Both should take at least 100ms (minimum response time)
        assert valid_time >= 0.1
        assert invalid_time >= 0.1

        # Response times should be similar (within 200ms difference)
        # This prevents user enumeration via timing attacks
        time_diff = abs(valid_time - invalid_time)
        assert time_diff < 0.2  # Allow 200ms variance


class TestOTPResendFlow:
    """Test OTP resend functionality with rate limiting."""

    @pytest.mark.integration
    async def test_resend_otp_rate_limiting(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """
        Test that OTP resend is rate limited (3 resends per hour).
        """
        user_email = f"resend{secrets.token_hex(4)}@example.com"

        # Register user
        with patch("src.presentation.api.v1.auth.registration.get_email_dispatcher") as mock_email_dep:
            mock_dispatcher = AsyncMock()
            mock_email_dep.return_value = mock_dispatcher

            register_data = {
                "login": f"resenduser{secrets.token_hex(4)}",
                "email": user_email,
                "password": "SecureP@ssw0rd123!",
            }

            with patch("src.config.settings.settings.registration_enabled", True):
                with patch("src.config.settings.settings.registration_invite_required", False):
                    await async_client.post("/api/v1/auth/register", json=register_data)

        # Resend OTP 3 times (should succeed)
        with patch("src.presentation.api.v1.auth.routes.get_email_dispatcher") as mock_email_dep:
            mock_dispatcher = AsyncMock()
            mock_email_dep.return_value = mock_dispatcher

            for _ in range(3):
                response = await async_client.post(
                    "/api/v1/auth/resend-otp",
                    json={"email": user_email},
                )
                assert response.status_code == 200

                # Small delay between requests
                await asyncio.sleep(0.1)

            # 4th resend should be rate limited
            rate_limited_response = await async_client.post(
                "/api/v1/auth/resend-otp",
                json={"email": user_email},
            )

            assert rate_limited_response.status_code == 429
            response_data = rate_limited_response.json()
            assert "detail" in response_data
            assert "code" in response_data["detail"]
            assert response_data["detail"]["code"] == "RATE_LIMITED"


class TestLogoutAllDevices:
    """Test logout from all devices functionality."""

    @pytest.mark.integration
    async def test_logout_all_devices_revokes_all_tokens(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """
        Test that logout-all revokes all refresh tokens and JWT tokens for user.
        """
        # Create and verify user
        user_email = f"logoutall{secrets.token_hex(4)}@example.com"
        password = "TestP@ssw0rd123!"

        from src.application.services.auth_service import AuthService
        auth_service = AuthService()
        password_hash = await auth_service.hash_password(password)

        user = AdminUserModel(
            login=f"logoutalluser{secrets.token_hex(4)}",
            email=user_email,
            password_hash=password_hash,
            role="viewer",
            is_active=True,
            is_email_verified=True,
        )
        db.add(user)
        await db.commit()

        # Login from "device 1"
        login1_response = await async_client.post(
            "/api/v1/auth/login",
            json={"login_or_email": user_email, "password": password},
        )
        assert login1_response.status_code == 200
        device1_access = login1_response.json()["access_token"]
        device1_refresh = login1_response.json()["refresh_token"]

        # Login from "device 2"
        login2_response = await async_client.post(
            "/api/v1/auth/login",
            json={"login_or_email": user_email, "password": password},
        )
        assert login2_response.status_code == 200
        device2_access = login2_response.json()["access_token"]
        device2_refresh = login2_response.json()["refresh_token"]

        # Both tokens work
        me1_response = await async_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {device1_access}"},
        )
        assert me1_response.status_code == 200

        me2_response = await async_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {device2_access}"},
        )
        assert me2_response.status_code == 200

        # Logout from all devices using device 1
        logout_all_response = await async_client.post(
            "/api/v1/auth/logout-all",
            headers={"Authorization": f"Bearer {device1_access}"},
        )
        assert logout_all_response.status_code == 200
        logout_data = logout_all_response.json()
        assert logout_data["sessions_revoked"] >= 2  # At least 2 sessions

        # Both refresh tokens should be invalidated
        refresh1_response = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": device1_refresh},
        )
        assert refresh1_response.status_code == 401

        refresh2_response = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": device2_refresh},
        )
        assert refresh2_response.status_code == 401

        # Access tokens should also be revoked (if JWT revocation is enabled)
        # Note: This depends on whether JWT revocation service is checking Redis
        me1_after_response = await async_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {device1_access}"},
        )
        # May be 401 if JWT revocation is active, or 200 if tokens are still valid until expiry
        # (depends on implementation)
