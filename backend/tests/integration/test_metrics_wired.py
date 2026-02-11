"""Smoke tests for Prometheus metrics integration.

Tests that custom metrics are properly wired into route handlers
and increment correctly after API calls.

Tests:
- POST /auth/login → auth_attempts_total counter increases
- POST /auth/register → registrations_total counter increases
- POST /trial/activate → trials_activated_total counter increases
"""

import secrets
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from prometheus_client import REGISTRY
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.admin_user_model import AdminUserModel


class TestMetricsWired:
    """Test that Prometheus metrics are wired into route handlers."""

    @pytest.mark.integration
    async def test_auth_login_increments_auth_attempts_metric(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """Test that successful login increments auth_attempts_total counter."""
        # Create verified user with known password
        password = "TestP@ssw0rd123!"
        user_email = f"metricstest{secrets.token_hex(4)}@example.com"

        from src.application.services.auth_service import AuthService
        auth_service = AuthService()
        password_hash = await auth_service.hash_password(password)

        user = AdminUserModel(
            login=f"metricsuser{secrets.token_hex(4)}",
            email=user_email,
            password_hash=password_hash,
            role="viewer",
            is_active=True,
            is_email_verified=True,
        )
        db.add(user)
        await db.commit()

        # Get metric value before login
        before = REGISTRY.get_sample_value(
            'auth_attempts_total',
            {'method': 'password', 'status': 'success'}
        ) or 0

        # Call login endpoint
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "login_or_email": user_email,
                "password": password,
            },
        )

        assert response.status_code == 200

        # Get metric value after login
        after = REGISTRY.get_sample_value(
            'auth_attempts_total',
            {'method': 'password', 'status': 'success'}
        ) or 0

        # Verify metric incremented
        assert after > before, f"auth_attempts_total should increase from {before} to {after}"

    @pytest.mark.integration
    async def test_auth_register_increments_registrations_metric(
        self,
        async_client: AsyncClient,
    ):
        """Test that user registration increments registrations_total counter."""
        # Mock email dispatcher to prevent actual email sends
        with patch("src.presentation.api.v1.auth.registration.get_email_dispatcher") as mock_email_dep:
            mock_dispatcher = AsyncMock()
            mock_email_dep.return_value = mock_dispatcher

            # Get metric value before registration
            before = REGISTRY.get_sample_value(
                'registrations_total',
                {'method': 'email'}
            ) or 0

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

            # Get metric value after registration
            after = REGISTRY.get_sample_value(
                'registrations_total',
                {'method': 'email'}
            ) or 0

            # Verify metric incremented
            assert after > before, f"registrations_total should increase from {before} to {after}"

    @pytest.mark.integration
    async def test_trial_activate_increments_trial_metric(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """Test that trial activation increments trials_activated_total counter."""
        # Create verified user
        password = "TestP@ssw0rd123!"
        user_email = f"trialtest{secrets.token_hex(4)}@example.com"

        from src.application.services.auth_service import AuthService
        auth_service = AuthService()
        password_hash = await auth_service.hash_password(password)

        user = AdminUserModel(
            login=f"trialuser{secrets.token_hex(4)}",
            email=user_email,
            password_hash=password_hash,
            role="viewer",
            is_active=True,
            is_email_verified=True,
        )
        db.add(user)
        await db.commit()

        # Login to get access token
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "login_or_email": user_email,
                "password": password,
            },
        )
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]

        # Get metric value before trial activation
        before = REGISTRY.get_sample_value('trials_activated_total') or 0

        # Call trial activate endpoint
        trial_response = await async_client.post(
            "/api/v1/trial/activate",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert trial_response.status_code == 200

        # Get metric value after trial activation
        after = REGISTRY.get_sample_value('trials_activated_total') or 0

        # Verify metric incremented
        assert after > before, f"trials_activated_total should increase from {before} to {after}"
