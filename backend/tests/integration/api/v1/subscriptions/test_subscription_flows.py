"""Integration tests for subscription management flows (BM-5).

Tests subscription workflows:
- get active subscription
- cancel subscription
- rate limiting on cancel

Requires: AsyncClient, test database, Redis, Remnawave mock.
"""

import secrets
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.admin_user_model import AdminUserModel


class TestActiveSubscriptionFlow:
    """Test getting active subscription information."""

    @pytest.mark.integration
    async def test_get_active_subscription(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """
        Test retrieving active subscription for authenticated user.

        Mocks Remnawave API response with subscription data.
        """
        # Create verified user
        user_email = f"subscription{secrets.token_hex(4)}@example.com"
        password = "TestP@ssw0rd123!"

        from src.application.services.auth_service import AuthService
        auth_service = AuthService()
        password_hash = await auth_service.hash_password(password)

        user = AdminUserModel(
            login=f"subuser{secrets.token_hex(4)}",
            email=user_email,
            password_hash=password_hash,
            role="viewer",
            is_active=True,
            is_email_verified=True,
        )
        db.add(user)
        await db.commit()

        # Login
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={"login_or_email": user_email, "password": password},
        )
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]

        # Mock Remnawave subscription response
        with patch("src.infrastructure.remnawave.client.RemnawaveClient.get") as mock_get:
            mock_get.return_value = {
                "status": "active",
                "plan_name": "monthly",
                "expires_at": "2025-12-31T23:59:59Z",
                "traffic_limit_bytes": 10737418240,  # 10 GB
                "used_traffic_bytes": 1073741824,  # 1 GB
                "auto_renew": True,
            }

            # Get active subscription
            sub_response = await async_client.get(
                "/api/v1/subscriptions/active",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            assert sub_response.status_code == 200
            sub_data = sub_response.json()
            assert sub_data["status"] == "active"
            assert sub_data["plan_name"] == "monthly"
            assert sub_data["traffic_limit_bytes"] == 10737418240
            assert sub_data["used_traffic_bytes"] == 1073741824
            assert sub_data["auto_renew"] is True

    @pytest.mark.integration
    async def test_get_active_subscription_requires_authentication(
        self,
        async_client: AsyncClient,
    ):
        """
        Test that getting active subscription requires authentication.
        """
        response = await async_client.get("/api/v1/subscriptions/active")
        assert response.status_code == 401


class TestCancelSubscriptionFlow:
    """Test subscription cancellation flow."""

    @pytest.mark.integration
    async def test_cancel_subscription(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """
        Test canceling an active subscription.

        Mocks Remnawave API calls for user and subscription management.
        """
        # Create verified user
        user_email = f"cancel{secrets.token_hex(4)}@example.com"
        password = "TestP@ssw0rd123!"

        from src.application.services.auth_service import AuthService
        auth_service = AuthService()
        password_hash = await auth_service.hash_password(password)

        user = AdminUserModel(
            login=f"canceluser{secrets.token_hex(4)}",
            email=user_email,
            password_hash=password_hash,
            role="viewer",
            is_active=True,
            is_email_verified=True,
        )
        db.add(user)
        await db.commit()

        # Login
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={"login_or_email": user_email, "password": password},
        )
        access_token = login_response.json()["access_token"]

        # Mock Remnawave API calls
        with patch("src.infrastructure.remnawave.client.RemnawaveClient.get") as mock_get:
            with patch("src.infrastructure.remnawave.client.RemnawaveClient.post") as mock_post:
                # Mock user exists check
                mock_get.return_value = {
                    "uuid": str(user.id),
                    "login": user.login,
                    "email": user.email,
                }

                # Mock revoke subscription call
                mock_post.return_value = {"message": "Subscription revoked"}

                # Cancel subscription
                cancel_response = await async_client.post(
                    "/api/v1/subscriptions/cancel",
                    headers={"Authorization": f"Bearer {access_token}"},
                )

                assert cancel_response.status_code == 200
                cancel_data = cancel_response.json()
                assert "canceled_at" in cancel_data

    @pytest.mark.integration
    async def test_cancel_subscription_for_nonexistent_user(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """
        Test that canceling subscription fails if user not found in VPN backend.
        """
        # Create verified user
        user_email = f"notfound{secrets.token_hex(4)}@example.com"
        password = "TestP@ssw0rd123!"

        from src.application.services.auth_service import AuthService
        auth_service = AuthService()
        password_hash = await auth_service.hash_password(password)

        user = AdminUserModel(
            login=f"notfounduser{secrets.token_hex(4)}",
            email=user_email,
            password_hash=password_hash,
            role="viewer",
            is_active=True,
            is_email_verified=True,
        )
        db.add(user)
        await db.commit()

        # Login
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={"login_or_email": user_email, "password": password},
        )
        access_token = login_response.json()["access_token"]

        # Mock Remnawave API to return user not found
        with patch("src.infrastructure.remnawave.client.RemnawaveClient.get") as mock_get:
            mock_get.return_value = None

            # Try to cancel subscription
            cancel_response = await async_client.post(
                "/api/v1/subscriptions/cancel",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            assert cancel_response.status_code == 404

    @pytest.mark.integration
    async def test_cancel_subscription_requires_authentication(
        self,
        async_client: AsyncClient,
    ):
        """
        Test that canceling subscription requires authentication.
        """
        response = await async_client.post("/api/v1/subscriptions/cancel")
        assert response.status_code == 401


class TestCancelSubscriptionRateLimiting:
    """Test rate limiting on subscription cancellation."""

    @pytest.mark.integration
    async def test_cancel_subscription_rate_limit(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """
        Test that subscription cancellation is rate limited to 3 requests per hour.
        """
        # Create verified user
        user_email = f"cancelrate{secrets.token_hex(4)}@example.com"
        password = "TestP@ssw0rd123!"

        from src.application.services.auth_service import AuthService
        auth_service = AuthService()
        password_hash = await auth_service.hash_password(password)

        user = AdminUserModel(
            login=f"cancelrateuser{secrets.token_hex(4)}",
            email=user_email,
            password_hash=password_hash,
            role="viewer",
            is_active=True,
            is_email_verified=True,
        )
        db.add(user)
        await db.commit()

        # Login
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={"login_or_email": user_email, "password": password},
        )
        access_token = login_response.json()["access_token"]

        # Mock Remnawave API
        with patch("src.infrastructure.remnawave.client.RemnawaveClient.get") as mock_get:
            with patch("src.infrastructure.remnawave.client.RemnawaveClient.post") as mock_post:
                mock_get.return_value = {
                    "uuid": str(user.id),
                    "login": user.login,
                    "email": user.email,
                }
                mock_post.return_value = {"message": "Subscription revoked"}

                # Make 3 cancel requests (should succeed)
                for i in range(3):
                    response = await async_client.post(
                        "/api/v1/subscriptions/cancel",
                        headers={"Authorization": f"Bearer {access_token}"},
                    )
                    assert response.status_code == 200

                # 4th request should be rate limited
                rate_limited_response = await async_client.post(
                    "/api/v1/subscriptions/cancel",
                    headers={"Authorization": f"Bearer {access_token}"},
                )

                assert rate_limited_response.status_code == 429
                assert "Rate limit exceeded" in rate_limited_response.json()["detail"]
