"""Integration tests for subscription management flows (BM-5)."""

import secrets
import uuid
from unittest.mock import patch

import pytest
from httpx import AsyncClient, HTTPStatusError, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.auth_service import AuthService
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.remnawave_upgrade_model import RemnawaveIdentityReconciliationModel
from src.infrastructure.remnawave.contracts import RemnawaveUserResponse
from tests.integration.conftest import (
    customer_auth_headers,
    get_default_test_realm,
    issue_customer_access_token,
)


async def _create_admin_user(db: AsyncSession) -> tuple[AdminUserModel, str]:
    password = "TestP@ssw0rd123!"
    auth_service = AuthService()
    admin_realm = await get_default_test_realm(db, "admin")
    user = AdminUserModel(
        auth_realm_id=admin_realm.id,
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


async def _create_mobile_user(db: AsyncSession) -> tuple[MobileUserModel, str]:
    auth_service = AuthService()
    suffix = secrets.token_hex(4)
    customer_realm = await get_default_test_realm(db, "customer")
    legacy_uuid = uuid.uuid4()
    user = MobileUserModel(
        auth_realm_id=customer_realm.id,
        email=f"subscription-customer-{suffix}@example.com",
        password_hash=await auth_service.hash_password("CustomerSubscriptionPassword123!"),
        username=f"subscription-customer-{suffix}",
        is_active=True,
        status="active",
        remnawave_user_id=secrets.randbelow(2_000_000_000) + 1,
        remnawave_uuid=str(legacy_uuid),
    )
    db.add(user)
    await db.flush()
    db.add(
        RemnawaveIdentityReconciliationModel(
            subject_type="mobile_user",
            subject_id=user.id,
            legacy_uuid=str(legacy_uuid),
            numeric_user_id=user.remnawave_user_id,
            reconciliation_state="mapped",
            evidence={"source": "integration-test"},
        )
    )
    await db.commit()
    await db.refresh(user)
    return user, await issue_customer_access_token(db, user)


def _remnawave_user_payload(
    user: AdminUserModel | MobileUserModel,
    **overrides,
):
    username = user.login if isinstance(user, AdminUserModel) else user.username
    remnawave_uuid = user.remnawave_uuid if isinstance(user, MobileUserModel) else str(user.id)
    payload = {
        "id": user.remnawave_user_id if isinstance(user, MobileUserModel) else None,
        "uuid": remnawave_uuid,
        "username": username,
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


def _remnawave_not_found() -> HTTPStatusError:
    request = Request("GET", "https://remnawave.test/api/users/1")
    response = Response(404, request=request)
    return HTTPStatusError("Remnawave user not found", request=request, response=response)


class TestActiveSubscriptionFlow:
    """Test getting active subscription information."""

    @pytest.mark.integration
    async def test_get_active_subscription(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        user, access_token = await _create_mobile_user(db)

        with patch("src.infrastructure.remnawave.client.RemnawaveClient.get") as mock_get:
            mock_get.return_value = _remnawave_user_payload(user)

            sub_response = await async_client.get(
                "/api/v1/subscriptions/active",
                headers=customer_auth_headers(access_token),
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
        user, access_token = await _create_mobile_user(db)

        with patch("src.infrastructure.remnawave.client.RemnawaveClient.get") as mock_get:
            with patch("src.infrastructure.remnawave.client.RemnawaveClient.post_validated") as mock_post:
                mock_get.return_value = _remnawave_user_payload(user)
                mock_post.return_value = RemnawaveUserResponse.model_validate(
                    _remnawave_user_payload(
                        user,
                        subRevokedAt="2026-04-11T12:00:00+00:00",
                        updatedAt="2026-04-11T12:00:00+00:00",
                    )
                )

                cancel_response = await async_client.post(
                    "/api/v1/subscriptions/cancel",
                    headers=customer_auth_headers(access_token),
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
        user, access_token = await _create_mobile_user(db)

        with patch("src.infrastructure.remnawave.client.RemnawaveClient.get") as mock_get:
            mock_get.side_effect = _remnawave_not_found()

            cancel_response = await async_client.post(
                "/api/v1/subscriptions/cancel",
                headers=customer_auth_headers(access_token),
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
        user, access_token = await _create_mobile_user(db)

        with patch("src.infrastructure.remnawave.client.RemnawaveClient.get") as mock_get:
            with patch("src.infrastructure.remnawave.client.RemnawaveClient.post_validated") as mock_post:
                mock_get.return_value = _remnawave_user_payload(user)
                mock_post.return_value = RemnawaveUserResponse.model_validate(
                    _remnawave_user_payload(
                        user,
                        subRevokedAt="2026-04-11T12:00:00+00:00",
                        updatedAt="2026-04-11T12:00:00+00:00",
                    )
                )

                for _ in range(3):
                    response = await async_client.post(
                        "/api/v1/subscriptions/cancel",
                        headers=customer_auth_headers(access_token),
                    )
                    assert response.status_code == 200

                rate_limited_response = await async_client.post(
                    "/api/v1/subscriptions/cancel",
                    headers=customer_auth_headers(access_token),
                )

        assert rate_limited_response.status_code == 429
        assert "Rate limit exceeded" in rate_limited_response.json()["detail"]
