"""Integration tests for notification preferences endpoints (BF2-5).

Tests GET and PATCH /api/v1/users/me/notifications endpoints:
- Get current user notification preferences
- Update notification preferences
- Partial updates (only provided fields are updated)
- Default preferences for new users
- Database persistence verification

Requires: AsyncClient, test database, authenticated user.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.admin_user_model import AdminUserModel


class TestNotificationPreferences:
    """Test notification preferences GET and PATCH endpoints."""

    @pytest.mark.integration
    async def test_get_notification_preferences_returns_defaults_for_new_user(
        self,
        async_client: AsyncClient,
        test_user_with_token: tuple[AdminUserModel, str],
    ):
        """Test GET /users/me/notifications returns default preferences."""
        _user, access_token = test_user_with_token

        # Act
        response = await async_client.get(
            "/api/v1/users/me/notifications",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        # Default preferences (from routes.py)
        assert data["email_security"] is True
        assert data["email_marketing"] is False
        assert data["push_connection"] is True
        assert data["push_payment"] is True
        assert data["push_subscription"] is True

    @pytest.mark.integration
    async def test_get_notification_preferences_unauthorized_without_token(
        self,
        async_client: AsyncClient,
    ):
        """Test GET /users/me/notifications returns 401 without token."""
        # Act
        response = await async_client.get("/api/v1/users/me/notifications")

        # Assert
        assert response.status_code == 401

    @pytest.mark.integration
    async def test_update_notification_preferences_email_security(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
        test_user_with_token: tuple[AdminUserModel, str],
    ):
        """Test PATCH /users/me/notifications updates email_security."""
        user, access_token = test_user_with_token

        # Act
        response = await async_client.patch(
            "/api/v1/users/me/notifications",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"email_security": False},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["email_security"] is False

        # Verify database persistence
        result = await db.execute(
            select(AdminUserModel).where(AdminUserModel.id == user.id)
        )
        updated_user = result.scalar_one()
        assert updated_user.notification_prefs is not None
        assert updated_user.notification_prefs.get("email_security") is False

    @pytest.mark.integration
    async def test_update_notification_preferences_email_marketing(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
        test_user_with_token: tuple[AdminUserModel, str],
    ):
        """Test PATCH /users/me/notifications updates email_marketing."""
        user, access_token = test_user_with_token

        # Act
        response = await async_client.patch(
            "/api/v1/users/me/notifications",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"email_marketing": True},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["email_marketing"] is True

        # Verify database persistence
        result = await db.execute(
            select(AdminUserModel).where(AdminUserModel.id == user.id)
        )
        updated_user = result.scalar_one()
        assert updated_user.notification_prefs.get("email_marketing") is True

    @pytest.mark.integration
    async def test_update_notification_preferences_push_notifications(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
        test_user_with_token: tuple[AdminUserModel, str],
    ):
        """Test PATCH /users/me/notifications updates push notification settings."""
        user, access_token = test_user_with_token

        # Act
        response = await async_client.patch(
            "/api/v1/users/me/notifications",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "push_connection": False,
                "push_payment": False,
                "push_subscription": False,
            },
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["push_connection"] is False
        assert data["push_payment"] is False
        assert data["push_subscription"] is False

        # Verify database persistence
        result = await db.execute(
            select(AdminUserModel).where(AdminUserModel.id == user.id)
        )
        updated_user = result.scalar_one()
        prefs = updated_user.notification_prefs
        assert prefs.get("push_connection") is False
        assert prefs.get("push_payment") is False
        assert prefs.get("push_subscription") is False

    @pytest.mark.integration
    async def test_update_notification_preferences_multiple_fields(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
        test_user_with_token: tuple[AdminUserModel, str],
    ):
        """Test PATCH /users/me/notifications updates multiple fields at once."""
        user, access_token = test_user_with_token

        # Act
        response = await async_client.patch(
            "/api/v1/users/me/notifications",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "email_security": False,
                "email_marketing": True,
                "push_connection": False,
            },
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["email_security"] is False
        assert data["email_marketing"] is True
        assert data["push_connection"] is False

        # Verify database persistence
        result = await db.execute(
            select(AdminUserModel).where(AdminUserModel.id == user.id)
        )
        updated_user = result.scalar_one()
        prefs = updated_user.notification_prefs
        assert prefs.get("email_security") is False
        assert prefs.get("email_marketing") is True
        assert prefs.get("push_connection") is False

    @pytest.mark.integration
    async def test_update_notification_preferences_partial_update_preserves_other_fields(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
        test_user_with_token: tuple[AdminUserModel, str],
    ):
        """Test PATCH /users/me/notifications only updates provided fields."""
        user, access_token = test_user_with_token

        # Set initial state
        await async_client.patch(
            "/api/v1/users/me/notifications",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "email_security": False,
                "email_marketing": True,
                "push_connection": False,
            },
        )

        # Act: Update only email_security
        response = await async_client.patch(
            "/api/v1/users/me/notifications",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"email_security": True},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["email_security"] is True  # Changed
        assert data["email_marketing"] is True  # Unchanged
        assert data["push_connection"] is False  # Unchanged

        # Verify database persistence
        result = await db.execute(
            select(AdminUserModel).where(AdminUserModel.id == user.id)
        )
        updated_user = result.scalar_one()
        prefs = updated_user.notification_prefs
        assert prefs.get("email_security") is True
        assert prefs.get("email_marketing") is True
        assert prefs.get("push_connection") is False

    @pytest.mark.integration
    async def test_update_notification_preferences_unauthorized_without_token(
        self,
        async_client: AsyncClient,
    ):
        """Test PATCH /users/me/notifications returns 401 without token."""
        # Act
        response = await async_client.patch(
            "/api/v1/users/me/notifications",
            json={"email_marketing": True},
        )

        # Assert
        assert response.status_code == 401

    @pytest.mark.integration
    async def test_update_notification_preferences_empty_request_returns_success(
        self,
        async_client: AsyncClient,
        test_user_with_token: tuple[AdminUserModel, str],
    ):
        """Test PATCH /users/me/notifications with empty body returns success (no-op)."""
        _user, access_token = test_user_with_token

        # Act
        response = await async_client.patch(
            "/api/v1/users/me/notifications",
            headers={"Authorization": f"Bearer {access_token}"},
            json={},
        )

        # Assert
        assert response.status_code == 200

    @pytest.mark.integration
    async def test_notification_preferences_persist_across_sessions(
        self,
        async_client: AsyncClient,
        test_user_with_token: tuple[AdminUserModel, str],
    ):
        """Test notification preferences persist across multiple GET requests."""
        _user, access_token = test_user_with_token

        # Set preferences
        await async_client.patch(
            "/api/v1/users/me/notifications",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "email_security": False,
                "push_payment": False,
            },
        )

        # Act: Get preferences multiple times
        response1 = await async_client.get(
            "/api/v1/users/me/notifications",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response2 = await async_client.get(
            "/api/v1/users/me/notifications",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Both requests return same persisted values
        assert response1.status_code == 200
        assert response2.status_code == 200
        data1 = response1.json()
        data2 = response2.json()
        assert data1 == data2
        assert data1["email_security"] is False
        assert data1["push_payment"] is False
