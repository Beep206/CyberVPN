"""Integration tests for usage statistics flows (BT-2).

Tests the usage endpoint:
- get usage success (with mocked Remnawave)
- get usage with no subscription
- usage requires auth

Requires: AsyncClient, test database, Redis.
"""

import secrets
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.auth_service import AuthService
from src.application.use_cases.usage.get_user_usage import UsageData
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from tests.integration.conftest import admin_auth_headers, get_default_test_realm, issue_realm_access_token


async def _create_verified_user(db: AsyncSession) -> tuple[AdminUserModel, str]:
    """Helper: create a verified user and return (user, access_token)."""
    password = "TestP@ssw0rd123!"
    email = f"usage{secrets.token_hex(4)}@example.com"
    auth_service = AuthService()
    password_hash = await auth_service.hash_password(password)
    admin_realm = await get_default_test_realm(db, "admin")

    user = AdminUserModel(
        auth_realm_id=admin_realm.id,
        login=f"usageuser{secrets.token_hex(4)}",
        email=email,
        password_hash=password_hash,
        role="viewer",
        is_active=True,
        is_email_verified=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    access_token = await issue_realm_access_token(
        db,
        subject=str(user.id),
        role=user.role,
        realm_type="admin",
    )
    return user, access_token


class TestUsageEndpoint:
    """Test usage statistics endpoint."""

    @pytest.mark.integration
    async def test_get_usage_success(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """
        Test GET /api/v1/users/me/usage with valid auth -> 200 + usage data.

        Mocks Remnawave API via GetUserUsageUseCase to return synthetic usage data.
        """
        _user, access_token = await _create_verified_user(db)

        mock_usage = UsageData(
            bandwidth_used_bytes=1_073_741_824,  # 1 GB
            bandwidth_limit_bytes=10_737_418_240,  # 10 GB
            connections_active=1,
            connections_limit=5,
            period_start=datetime(2024, 1, 1, tzinfo=UTC),
            period_end=datetime(2024, 2, 1, tzinfo=UTC),
            last_connection_at=datetime(2024, 1, 15, 10, 30, tzinfo=UTC),
        )

        with patch("src.presentation.api.v1.usage.routes.GetUserUsageUseCase") as mock_uc_class:
            mock_uc = AsyncMock()
            mock_uc.execute.return_value = mock_usage
            mock_uc_class.return_value = mock_uc

            response = await async_client.get(
                "/api/v1/users/me/usage",
                headers=admin_auth_headers(access_token),
            )

        assert response.status_code == 200
        data = response.json()
        assert data["usage_available"] is True
        assert data["usage_source"] == "remnawave"
        assert data["usage_unavailable_reason"] is None
        assert data["bandwidth_used_bytes"] == 1_073_741_824
        assert data["bandwidth_limit_bytes"] == 10_737_418_240
        assert data["connections_active"] == 1
        assert data["connections_limit"] == 5
        assert data["last_connection_at"] is not None
        assert data["generated_at"] is not None

    @pytest.mark.integration
    async def test_get_usage_no_subscription(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """
        Test GET /api/v1/users/me/usage falls back to empty usage when upstream has no record.

        The current route contract keeps the dashboard alive by returning an empty
        snapshot instead of surfacing upstream lookup failures to the client.
        """
        _user, access_token = await _create_verified_user(db)

        with patch("src.presentation.api.v1.usage.routes.GetUserUsageUseCase") as mock_uc_class:
            mock_uc = AsyncMock()
            mock_uc.execute.side_effect = ValueError("User not found in VPN backend")
            mock_uc_class.return_value = mock_uc

            response = await async_client.get(
                "/api/v1/users/me/usage",
                headers=admin_auth_headers(access_token),
            )

        assert response.status_code == 200
        data = response.json()
        assert data["usage_available"] is False
        assert data["usage_source"] == "unavailable"
        assert data["usage_unavailable_reason"] == "upstream_user_not_found"
        assert data["bandwidth_used_bytes"] == 0
        assert data["bandwidth_limit_bytes"] == 0
        assert data["connections_active"] == 0
        assert data["connections_limit"] == 0
        assert data["last_connection_at"] is None
        assert data["generated_at"] is not None

    @pytest.mark.integration
    async def test_usage_requires_auth(
        self,
        async_client: AsyncClient,
    ):
        """
        Test GET /api/v1/users/me/usage without auth -> 401.
        """
        response = await async_client.get("/api/v1/users/me/usage")
        assert response.status_code in (401, 403)
