"""Integration tests for subscription management flows (BM-5)."""

import secrets
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.auth_service import AuthService
from src.infrastructure.database.models.admin_user_model import AdminUserModel


async def _create_admin_user(db: AsyncSession) -> tuple[AdminUserModel, str]:
    password = "TestP@ssw0rd123!"
    auth_service = AuthService()
    user = AdminUserModel(
        login=f"subuser{secrets.token_hex(4)}",
        email=f"subscription{secrets.token_hex(4)}@example.com",
        password_hash=await auth_service.hash_password(password),
        role="viewer",
        is_active=True,
        is_email_verified=True,
        language="en",
        timezone="UTC",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user, password


async def _login(async_client: AsyncClient, user: AdminUserModel, password: str) -> str:
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"login_or_email": user.email, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def _remnawave_user_payload(
    user: AdminUserModel,
    **overrides,
):
    payload = {
        "uuid": str(user.id),
        "username": user.login,
        "status": "active",
        "shortUuid": "SUB12345",
        "createdAt": "2025-01-01T00:00:00+00:00",
        "updatedAt": "2025-01-01T00:00:00+00:00",
        "subscriptionUuid": "550e8400-e29b-41d4-a716-446655440000",
        "expireAt": "2027-12-31T23:59:59+00:00",
        "trafficLimitBytes": 10737418240,
        "usedTrafficBytes": 1073741824,
        "email": user.email,
    }
    payload.update(overrides)
    return payload


class TestActiveSubscriptionFlow:
    """Test getting active subscription information."""

    @pytest.mark.integration
    async def test_get_active_subscription(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        user, password = await _create_admin_user(db)
        access_token = await _login(async_client, user, password)

        with patch("src.infrastructure.remnawave.client.RemnawaveClient.get") as mock_get:
            mock_get.return_value = _remnawave_user_payload(user)

            sub_response = await async_client.get(
                "/api/v1/subscriptions/active",
                headers={"Authorization": f"Bearer {access_token}"},
            )

        assert sub_response.status_code == 200
        sub_data = sub_response.json()
        assert sub_data["status"] == "active"
        assert sub_data["plan_name"] == "VPN"
        assert sub_data["traffic_limit_bytes"] == 10737418240
        assert sub_data["used_traffic_bytes"] == 1073741824
        assert sub_data["auto_renew"] is False

    @pytest.mark.integration
    async def test_get_active_subscription_requires_authentication(
        self,
        async_client: AsyncClient,
    ):
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
        user, password = await _create_admin_user(db)
        access_token = await _login(async_client, user, password)

        with patch("src.infrastructure.remnawave.client.RemnawaveClient.get") as mock_get:
            with patch("src.infrastructure.remnawave.client.RemnawaveClient.patch") as mock_patch:
                mock_get.return_value = _remnawave_user_payload(user)
                mock_patch.return_value = _remnawave_user_payload(
                    user,
                    subRevokedAt="2026-04-11T12:00:00+00:00",
                    updatedAt="2026-04-11T12:00:00+00:00",
                )

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
        user, password = await _create_admin_user(db)
        access_token = await _login(async_client, user, password)

        with patch("src.infrastructure.remnawave.client.RemnawaveClient.get") as mock_get:
            mock_get.return_value = None

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
        user, password = await _create_admin_user(db)
        access_token = await _login(async_client, user, password)

        with patch("src.infrastructure.remnawave.client.RemnawaveClient.get") as mock_get:
            with patch("src.infrastructure.remnawave.client.RemnawaveClient.patch") as mock_patch:
                mock_get.return_value = _remnawave_user_payload(user)
                mock_patch.return_value = _remnawave_user_payload(
                    user,
                    subRevokedAt="2026-04-11T12:00:00+00:00",
                    updatedAt="2026-04-11T12:00:00+00:00",
                )

                for _ in range(3):
                    response = await async_client.post(
                        "/api/v1/subscriptions/cancel",
                        headers={"Authorization": f"Bearer {access_token}"},
                    )
                    assert response.status_code == 200

                rate_limited_response = await async_client.post(
                    "/api/v1/subscriptions/cancel",
                    headers={"Authorization": f"Bearer {access_token}"},
                )

        assert rate_limited_response.status_code == 429
        assert "Rate limit exceeded" in rate_limited_response.json()["detail"]
