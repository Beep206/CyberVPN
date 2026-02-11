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


async def _create_verified_user(db: AsyncSession) -> tuple[str, str]:
    """Helper: create a verified user and return (password, email)."""
    password = "TestP@ssw0rd123!"
    email = f"usage{secrets.token_hex(4)}@example.com"
    auth_service = AuthService()
    password_hash = await auth_service.hash_password(password)

    user = AdminUserModel(
        login=f"usageuser{secrets.token_hex(4)}",
        email=email,
        password_hash=password_hash,
        role="viewer",
        is_active=True,
        is_email_verified=True,
    )
    db.add(user)
    await db.commit()
    return password, email


async def _login(async_client: AsyncClient, email: str, password: str) -> str:
    """Helper: login and return access token."""
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"login_or_email": email, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


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
        password, email = await _create_verified_user(db)
        access_token = await _login(async_client, email, password)

        mock_usage = UsageData(
            bandwidth_used_bytes=1_073_741_824,  # 1 GB
            bandwidth_limit_bytes=10_737_418_240,  # 10 GB
            connections_active=1,
            connections_limit=5,
            period_start=datetime(2024, 1, 1, tzinfo=UTC),
            period_end=datetime(2024, 2, 1, tzinfo=UTC),
            last_connection_at=datetime(2024, 1, 15, 10, 30, tzinfo=UTC),
        )

        with patch(
            "src.presentation.api.v1.usage.routes.GetUserUsageUseCase"
        ) as mock_uc_class:
            mock_uc = AsyncMock()
            mock_uc.execute.return_value = mock_usage
            mock_uc_class.return_value = mock_uc

            response = await async_client.get(
                "/api/v1/users/me/usage",
                headers={"Authorization": f"Bearer {access_token}"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["bandwidth_used_bytes"] == 1_073_741_824
        assert data["bandwidth_limit_bytes"] == 10_737_418_240
        assert data["connections_active"] == 1
        assert data["connections_limit"] == 5
        assert data["last_connection_at"] is not None

    @pytest.mark.integration
    async def test_get_usage_no_subscription(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """
        Test GET /api/v1/users/me/usage when user has no subscription -> 404.

        Mocks Remnawave to raise ValueError (user not found in VPN backend).
        """
        password, email = await _create_verified_user(db)
        access_token = await _login(async_client, email, password)

        with patch(
            "src.presentation.api.v1.usage.routes.GetUserUsageUseCase"
        ) as mock_uc_class:
            mock_uc = AsyncMock()
            mock_uc.execute.side_effect = ValueError("User not found in VPN backend")
            mock_uc_class.return_value = mock_uc

            response = await async_client.get(
                "/api/v1/users/me/usage",
                headers={"Authorization": f"Bearer {access_token}"},
            )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

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
