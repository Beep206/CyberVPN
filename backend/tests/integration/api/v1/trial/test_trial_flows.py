"""Integration tests for trial period flows (BT-1).

Tests the trial activation and status endpoints:
- activate trial success
- activate trial already used
- activate trial rate limited
- get trial status
- trial endpoints require auth

Requires: AsyncClient, test database, Redis.
"""

import secrets
from datetime import UTC, datetime, timedelta

import pytest
import redis.asyncio as aioredis
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.auth_service import AuthService
from src.config.settings import settings
from src.infrastructure.database.models.admin_user_model import AdminUserModel


async def _create_verified_user(
    db: AsyncSession, *, role: str = "viewer",
) -> tuple[str, str, str]:
    """Helper: create a verified user and return (user_id, password, email)."""
    password = "TestP@ssw0rd123!"
    email = f"trial{secrets.token_hex(4)}@example.com"
    auth_service = AuthService()
    password_hash = await auth_service.hash_password(password)

    user = AdminUserModel(
        login=f"trialuser{secrets.token_hex(4)}",
        email=email,
        password_hash=password_hash,
        role=role,
        is_active=True,
        is_email_verified=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return str(user.id), password, email


async def _login(async_client: AsyncClient, email: str, password: str) -> str:
    """Helper: login and return access token."""
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"login_or_email": email, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


class TestTrialActivation:
    """Test trial activation flow."""

    @pytest.mark.integration
    async def test_activate_trial_success(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """
        Test POST /api/v1/trial/activate with valid auth -> 200 + trial activated.

        Steps:
        1. Create verified user (no prior trial)
        2. Login to get access token
        3. POST /trial/activate -> 200
        4. Verify response contains activated=True, trial_end, message
        """
        _user_id, password, email = await _create_verified_user(db)
        access_token = await _login(async_client, email, password)

        response = await async_client.post(
            "/api/v1/trial/activate",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["activated"] is True
        assert "trial_end" in data
        assert "message" in data
        assert "7 days" in data["message"]

    @pytest.mark.integration
    async def test_activate_trial_already_used(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """
        Test POST /api/v1/trial/activate when trial already claimed -> 400.

        Steps:
        1. Create user who already activated trial (trial_activated_at set)
        2. Login
        3. POST /trial/activate -> 400 (already activated)
        """
        password = "TestP@ssw0rd123!"
        email = f"trialused{secrets.token_hex(4)}@example.com"
        auth_service = AuthService()
        password_hash = await auth_service.hash_password(password)

        user = AdminUserModel(
            login=f"trialused{secrets.token_hex(4)}",
            email=email,
            password_hash=password_hash,
            role="viewer",
            is_active=True,
            is_email_verified=True,
            trial_activated_at=datetime.now(UTC) - timedelta(days=10),
            trial_expires_at=datetime.now(UTC) - timedelta(days=3),
        )
        db.add(user)
        await db.commit()

        access_token = await _login(async_client, email, password)

        response = await async_client.post(
            "/api/v1/trial/activate",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 400
        assert "already activated" in response.json()["detail"].lower()

    @pytest.mark.integration
    async def test_activate_trial_rate_limited(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """
        Test POST /api/v1/trial/activate when rate limit reached -> 429.

        Rate limit: 3 requests per hour per user.
        Pre-sets the Redis rate limit counter to 3 before making a request.
        """
        user_id, password, email = await _create_verified_user(db)
        access_token = await _login(async_client, email, password)

        # Pre-set the Redis rate limit key to 3 (already at limit)
        redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
        rate_limit_key = f"trial_activate:{user_id}"
        await redis_client.setex(rate_limit_key, 3600, "3")

        try:
            response = await async_client.post(
                "/api/v1/trial/activate",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            assert response.status_code == 429
            assert "Rate limit exceeded" in response.json()["detail"]
        finally:
            await redis_client.delete(rate_limit_key)
            await redis_client.aclose()


class TestTrialStatus:
    """Test trial status retrieval."""

    @pytest.mark.integration
    async def test_get_trial_status(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """
        Test GET /api/v1/trial/status with valid auth -> 200 + status payload.

        Steps:
        1. Create verified user (no trial yet)
        2. Login
        3. GET /trial/status -> 200 with is_eligible=True
        """
        _user_id, password, email = await _create_verified_user(db)
        access_token = await _login(async_client, email, password)

        response = await async_client.get(
            "/api/v1/trial/status",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_trial_active"] is False
        assert data["is_eligible"] is True
        assert data["days_remaining"] == 0
        assert data["trial_start"] is None
        assert data["trial_end"] is None


class TestTrialAuth:
    """Test that trial endpoints require authentication."""

    @pytest.mark.integration
    async def test_trial_endpoints_require_auth(
        self,
        async_client: AsyncClient,
    ):
        """
        Test that both trial endpoints return 401/403 without auth.
        """
        # POST /trial/activate without auth
        activate_response = await async_client.post("/api/v1/trial/activate")
        assert activate_response.status_code in (401, 403)

        # GET /trial/status without auth
        status_response = await async_client.get("/api/v1/trial/status")
        assert status_response.status_code in (401, 403)
