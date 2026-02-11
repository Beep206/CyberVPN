"""Integration tests for profile endpoints (BF2-3).

Tests GET and PATCH /api/v1/users/me/profile endpoints:
- Get current user profile
- Update profile fields (display_name, language, timezone)
- Partial updates (only provided fields are updated)
- Database persistence verification

Requires: AsyncClient, test database, authenticated user.
"""

import secrets

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.admin_user_model import AdminUserModel


class TestProfileEndpoints:
    """Test profile GET and PATCH endpoints."""

    @pytest.mark.integration
    async def test_get_profile_returns_user_data(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
        test_user_with_token: tuple[AdminUserModel, str],
    ):
        """Test GET /users/me/profile returns current user profile."""
        user, access_token = test_user_with_token

        # Act
        response = await async_client.get(
            "/api/v1/users/me/profile",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(user.id)
        assert data["email"] == user.email
        assert data["display_name"] == user.display_name or user.login
        assert data["language"] == user.language
        assert data["timezone"] == user.timezone
        assert "updated_at" in data

    @pytest.mark.integration
    async def test_get_profile_unauthorized_without_token(
        self,
        async_client: AsyncClient,
    ):
        """Test GET /users/me/profile returns 401 without token."""
        # Act
        response = await async_client.get("/api/v1/users/me/profile")

        # Assert
        assert response.status_code == 401

    @pytest.mark.integration
    async def test_update_profile_display_name(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
        test_user_with_token: tuple[AdminUserModel, str],
    ):
        """Test PATCH /users/me/profile updates display_name."""
        user, access_token = test_user_with_token
        new_display_name = f"Test User {secrets.token_hex(4)}"

        # Act
        response = await async_client.patch(
            "/api/v1/users/me/profile",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"display_name": new_display_name},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["display_name"] == new_display_name

        # Verify database persistence
        result = await db.execute(
            select(AdminUserModel).where(AdminUserModel.id == user.id)
        )
        updated_user = result.scalar_one()
        assert updated_user.display_name == new_display_name

    @pytest.mark.integration
    async def test_update_profile_language(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
        test_user_with_token: tuple[AdminUserModel, str],
    ):
        """Test PATCH /users/me/profile updates language."""
        user, access_token = test_user_with_token

        # Act
        response = await async_client.patch(
            "/api/v1/users/me/profile",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"language": "fr-FR"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["language"] == "fr-FR"

        # Verify database persistence
        result = await db.execute(
            select(AdminUserModel).where(AdminUserModel.id == user.id)
        )
        updated_user = result.scalar_one()
        assert updated_user.language == "fr-FR"

    @pytest.mark.integration
    async def test_update_profile_timezone(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
        test_user_with_token: tuple[AdminUserModel, str],
    ):
        """Test PATCH /users/me/profile updates timezone."""
        user, access_token = test_user_with_token

        # Act
        response = await async_client.patch(
            "/api/v1/users/me/profile",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"timezone": "America/New_York"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["timezone"] == "America/New_York"

        # Verify database persistence
        result = await db.execute(
            select(AdminUserModel).where(AdminUserModel.id == user.id)
        )
        updated_user = result.scalar_one()
        assert updated_user.timezone == "America/New_York"

    @pytest.mark.integration
    async def test_update_profile_multiple_fields(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
        test_user_with_token: tuple[AdminUserModel, str],
    ):
        """Test PATCH /users/me/profile updates multiple fields at once."""
        user, access_token = test_user_with_token
        new_display_name = f"Multi Update {secrets.token_hex(4)}"

        # Act
        response = await async_client.patch(
            "/api/v1/users/me/profile",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "display_name": new_display_name,
                "language": "de-DE",
                "timezone": "Europe/Berlin",
            },
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["display_name"] == new_display_name
        assert data["language"] == "de-DE"
        assert data["timezone"] == "Europe/Berlin"

        # Verify database persistence
        result = await db.execute(
            select(AdminUserModel).where(AdminUserModel.id == user.id)
        )
        updated_user = result.scalar_one()
        assert updated_user.display_name == new_display_name
        assert updated_user.language == "de-DE"
        assert updated_user.timezone == "Europe/Berlin"

    @pytest.mark.integration
    async def test_update_profile_partial_update_only_changes_provided_fields(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
        test_user_with_token: tuple[AdminUserModel, str],
    ):
        """Test PATCH /users/me/profile only updates provided fields."""
        user, access_token = test_user_with_token

        # Set initial state
        initial_name = f"Initial {secrets.token_hex(4)}"
        await async_client.patch(
            "/api/v1/users/me/profile",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "display_name": initial_name,
                "language": "en-EN",
                "timezone": "UTC",
            },
        )

        # Act: Update only language
        response = await async_client.patch(
            "/api/v1/users/me/profile",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"language": "es-ES"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["display_name"] == initial_name  # Unchanged
        assert data["language"] == "es-ES"  # Changed
        assert data["timezone"] == "UTC"  # Unchanged

    @pytest.mark.integration
    async def test_update_profile_unauthorized_without_token(
        self,
        async_client: AsyncClient,
    ):
        """Test PATCH /users/me/profile returns 401 without token."""
        # Act
        response = await async_client.patch(
            "/api/v1/users/me/profile",
            json={"display_name": "Should Fail"},
        )

        # Assert
        assert response.status_code == 401

    @pytest.mark.integration
    async def test_update_profile_empty_request_returns_success(
        self,
        async_client: AsyncClient,
        test_user_with_token: tuple[AdminUserModel, str],
    ):
        """Test PATCH /users/me/profile with empty body returns success (no-op)."""
        _user, access_token = test_user_with_token

        # Act
        response = await async_client.patch(
            "/api/v1/users/me/profile",
            headers={"Authorization": f"Bearer {access_token}"},
            json={},
        )

        # Assert
        assert response.status_code == 200
