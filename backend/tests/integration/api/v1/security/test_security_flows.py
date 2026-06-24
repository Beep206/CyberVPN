"""Integration tests for security management flows (BM-5).

Tests anti-phishing code management:
- set anti-phishing code
- get anti-phishing code
- delete anti-phishing code
- rate limiting on set/delete

Requires: AsyncClient, test database, Redis.
"""

import secrets

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.auth_service import AuthService
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from tests.integration.conftest import admin_auth_headers, get_default_test_realm, issue_admin_access_token


async def _create_verified_admin(db: AsyncSession, *, prefix: str) -> tuple[AdminUserModel, str]:
    password = "TestP@ssw0rd123!"
    auth_service = AuthService()
    admin_realm = await get_default_test_realm(db, "admin")
    user = AdminUserModel(
        auth_realm_id=admin_realm.id,
        login=f"{prefix}user{secrets.token_hex(4)}",
        email=f"{prefix}{secrets.token_hex(4)}@example.com",
        password_hash=await auth_service.hash_password(password),
        role="viewer",
        is_active=True,
        is_email_verified=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user, await issue_admin_access_token(db, user)


class TestAntiPhishingFlow:
    """Test anti-phishing code management flow."""

    @pytest.mark.integration
    async def test_set_and_get_antiphishing_code(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """
        Test setting and retrieving anti-phishing code.

        Steps:
        1. Create verified user
        2. Set anti-phishing code
        3. Verify code was set
        4. Get code and verify it matches
        """
        _user, access_token = await _create_verified_admin(db, prefix="antiphishing")

        # Set anti-phishing code
        antiphishing_code = "SECURE123"
        set_response = await async_client.post(
            "/api/v1/security/antiphishing",
            json={"code": antiphishing_code},
            headers=admin_auth_headers(access_token),
        )

        assert set_response.status_code == 200
        assert set_response.json()["code"] == antiphishing_code

        # Get anti-phishing code
        get_response = await async_client.get(
            "/api/v1/security/antiphishing",
            headers=admin_auth_headers(access_token),
        )

        assert get_response.status_code == 200
        assert get_response.json()["code"] == antiphishing_code

    @pytest.mark.integration
    async def test_update_antiphishing_code(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """
        Test updating an existing anti-phishing code.
        """
        _user, access_token = await _create_verified_admin(db, prefix="updatecode")

        # Set initial code
        initial_code = "INITIAL123"
        await async_client.post(
            "/api/v1/security/antiphishing",
            json={"code": initial_code},
            headers=admin_auth_headers(access_token),
        )

        # Update code
        updated_code = "UPDATED456"
        update_response = await async_client.post(
            "/api/v1/security/antiphishing",
            json={"code": updated_code},
            headers=admin_auth_headers(access_token),
        )

        assert update_response.status_code == 200
        assert update_response.json()["code"] == updated_code

        # Verify updated code
        get_response = await async_client.get(
            "/api/v1/security/antiphishing",
            headers=admin_auth_headers(access_token),
        )
        assert get_response.json()["code"] == updated_code

    @pytest.mark.integration
    async def test_delete_antiphishing_code(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """
        Test deleting anti-phishing code.

        Steps:
        1. Set code
        2. Delete code
        3. Verify code is null after deletion
        """
        _user, access_token = await _create_verified_admin(db, prefix="deletecode")

        # Set code
        antiphishing_code = "DELETE123"
        await async_client.post(
            "/api/v1/security/antiphishing",
            json={"code": antiphishing_code},
            headers=admin_auth_headers(access_token),
        )

        # Delete code
        delete_response = await async_client.delete(
            "/api/v1/security/antiphishing",
            headers=admin_auth_headers(access_token),
        )

        assert delete_response.status_code == 200

        # Verify code is null
        get_response = await async_client.get(
            "/api/v1/security/antiphishing",
            headers=admin_auth_headers(access_token),
        )
        assert get_response.status_code == 200
        assert get_response.json()["code"] is None

    @pytest.mark.integration
    async def test_get_antiphishing_code_returns_null_when_not_set(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """
        Test that GET returns null when no code has been set.
        """
        _user, access_token = await _create_verified_admin(db, prefix="nocode")

        # Get code without setting
        get_response = await async_client.get(
            "/api/v1/security/antiphishing",
            headers=admin_auth_headers(access_token),
        )

        assert get_response.status_code == 200
        assert get_response.json()["code"] is None

    @pytest.mark.integration
    async def test_antiphishing_code_requires_authentication(
        self,
        async_client: AsyncClient,
    ):
        """
        Test that all anti-phishing endpoints require authentication.
        """
        # Try to set code without auth
        set_response = await async_client.post(
            "/api/v1/security/antiphishing",
            json={"code": "TEST123"},
        )
        assert set_response.status_code == 401

        # Try to get code without auth
        get_response = await async_client.get("/api/v1/security/antiphishing")
        assert get_response.status_code == 401

        # Try to delete code without auth
        delete_response = await async_client.delete("/api/v1/security/antiphishing")
        assert delete_response.status_code == 401


class TestAntiPhishingRateLimiting:
    """Test rate limiting on anti-phishing endpoints."""

    @pytest.mark.integration
    async def test_set_antiphishing_rate_limit(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """
        Test that setting anti-phishing code is rate limited to 10 requests per hour.
        """
        _user, access_token = await _create_verified_admin(db, prefix="ratelimit")

        # Make 10 requests (should succeed)
        for i in range(10):
            response = await async_client.post(
                "/api/v1/security/antiphishing",
                json={"code": f"CODE{i}"},
                headers=admin_auth_headers(access_token),
            )
            assert response.status_code == 200

        # 11th request should be rate limited
        rate_limited_response = await async_client.post(
            "/api/v1/security/antiphishing",
            json={"code": "CODE11"},
            headers=admin_auth_headers(access_token),
        )

        assert rate_limited_response.status_code == 429
        assert "Rate limit exceeded" in rate_limited_response.json()["detail"]

    @pytest.mark.integration
    async def test_delete_antiphishing_rate_limit(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """
        Test that deleting anti-phishing code is rate limited to 5 requests per hour.
        """
        _user, access_token = await _create_verified_admin(db, prefix="delratelimit")

        # Make 5 delete requests (should succeed)
        for _ in range(5):
            response = await async_client.delete(
                "/api/v1/security/antiphishing",
                headers=admin_auth_headers(access_token),
            )
            assert response.status_code == 200

        # 6th request should be rate limited
        rate_limited_response = await async_client.delete(
            "/api/v1/security/antiphishing",
            headers=admin_auth_headers(access_token),
        )

        assert rate_limited_response.status_code == 429
        assert "Rate limit exceeded" in rate_limited_response.json()["detail"]
