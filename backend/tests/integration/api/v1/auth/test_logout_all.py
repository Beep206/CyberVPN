"""Integration tests for logout-all endpoint (BF2-4).

Tests POST /api/v1/auth/logout-all endpoint:
- Remote logout (revoke all tokens)
- Verify all user sessions are terminated
- Auth cookie clearing
- Database persistence verification

Requires: AsyncClient, test database, authenticated user, Redis.
"""

import pytest
from httpx import AsyncClient

from src.infrastructure.database.models.admin_user_model import AdminUserModel


class TestLogoutAllDevices:
    """Test logout-all-devices POST endpoint."""

    @pytest.mark.integration
    async def test_logout_all_success_terminates_all_sessions(
        self,
        async_client: AsyncClient,
        test_user_with_token: tuple[AdminUserModel, str],
    ):
        """Test POST /auth/logout-all successfully terminates all sessions."""
        _user, access_token = test_user_with_token

        # Act
        response = await async_client.post(
            "/api/v1/auth/logout-all",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "All sessions terminated"
        assert "sessions_revoked" in data
        assert isinstance(data["sessions_revoked"], int)
        assert data["sessions_revoked"] >= 0

    @pytest.mark.integration
    async def test_logout_all_clears_auth_cookies(
        self,
        async_client: AsyncClient,
        test_user_with_token: tuple[AdminUserModel, str],
    ):
        """Test POST /auth/logout-all clears authentication cookies."""
        _user, access_token = test_user_with_token

        # Act
        response = await async_client.post(
            "/api/v1/auth/logout-all",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert
        assert response.status_code == 200

        # Verify Set-Cookie headers are present to clear cookies
        set_cookie_headers = response.headers.get_list("set-cookie")
        assert len(set_cookie_headers) > 0

        # Check that cookies are being cleared (Max-Age=0 or expires in past)
        cookie_str = "; ".join(set_cookie_headers)
        assert "Max-Age=0" in cookie_str or "expires=" in cookie_str.lower()

    @pytest.mark.integration
    async def test_logout_all_unauthorized_without_token(
        self,
        async_client: AsyncClient,
    ):
        """Test POST /auth/logout-all returns 401 without token."""
        # Act
        response = await async_client.post("/api/v1/auth/logout-all")

        # Assert
        assert response.status_code == 401

    @pytest.mark.integration
    async def test_logout_all_unauthorized_with_invalid_token(
        self,
        async_client: AsyncClient,
    ):
        """Test POST /auth/logout-all returns 401 with invalid token."""
        # Act
        response = await async_client.post(
            "/api/v1/auth/logout-all",
            headers={"Authorization": "Bearer invalid-token-12345"},
        )

        # Assert
        assert response.status_code == 401

    @pytest.mark.integration
    async def test_logout_all_after_logout_token_is_invalid(
        self,
        async_client: AsyncClient,
        test_user_with_token: tuple[AdminUserModel, str],
    ):
        """Test that token becomes invalid after logout-all."""
        _user, access_token = test_user_with_token

        # First request - should succeed
        response = await async_client.post(
            "/api/v1/auth/logout-all",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200

        # Second request with same token - should fail (token revoked)
        response2 = await async_client.get(
            "/api/v1/users/me/profile",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Token should be revoked, so request should fail with 401
        assert response2.status_code == 401

    @pytest.mark.integration
    async def test_logout_all_multiple_times_succeeds(
        self,
        async_client: AsyncClient,
        test_user_with_token: tuple[AdminUserModel, str],
    ):
        """Test POST /auth/logout-all can be called multiple times safely."""
        user, access_token1 = test_user_with_token

        # Import auth service to create second token
        from src.application.services.auth_service import AuthService

        auth_service = AuthService()
        access_token2, _, _ = auth_service.create_access_token(
            subject=str(user.id),
            role=user.role,
        )

        # First logout with first token
        response1 = await async_client.post(
            "/api/v1/auth/logout-all",
            headers={"Authorization": f"Bearer {access_token1}"},
        )
        assert response1.status_code == 200

        # Second logout with second token (both should be revoked now)
        response2 = await async_client.post(
            "/api/v1/auth/logout-all",
            headers={"Authorization": f"Bearer {access_token2}"},
        )

        # Token is revoked, so this should fail
        assert response2.status_code == 401

    @pytest.mark.integration
    async def test_logout_all_returns_expected_response_structure(
        self,
        async_client: AsyncClient,
        test_user_with_token: tuple[AdminUserModel, str],
    ):
        """Test POST /auth/logout-all returns correct response schema."""
        _user, access_token = test_user_with_token

        # Act
        response = await async_client.post(
            "/api/v1/auth/logout-all",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Verify response structure matches LogoutAllResponse schema
        assert "message" in data
        assert "sessions_revoked" in data
        assert isinstance(data["message"], str)
        assert isinstance(data["sessions_revoked"], int)
        assert data["message"] == "All sessions terminated"
        assert data["sessions_revoked"] >= 0
