"""Integration tests for trial period flows on mobile users."""

import secrets
from datetime import UTC, datetime, timedelta

import pytest
import redis.asyncio as aioredis
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.auth_service import AuthService
from src.config.settings import settings
from src.infrastructure.database.models.mobile_user_model import MobileUserModel


async def _create_mobile_user(
    db: AsyncSession,
    *,
    trial_activated_at: datetime | None = None,
    trial_expires_at: datetime | None = None,
) -> tuple[str, str]:
    """Create an active mobile user and return ``(user_id, access_token)``."""
    auth_service = AuthService()
    suffix = secrets.token_hex(4)
    user = MobileUserModel(
        email=f"trial-{suffix}@example.com",
        password_hash=await auth_service.hash_password("MobileTrialPassword123!"),
        username=f"trial-{suffix}",
        is_active=True,
        status="active",
        trial_activated_at=trial_activated_at,
        trial_expires_at=trial_expires_at,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return str(user.id), auth_service.create_access_token_simple(str(user.id), "user")


class TestTrialActivation:
    """Test trial activation flow."""

    @pytest.mark.integration
    async def test_activate_trial_success(
        self,
        async_client: AsyncClient,
        db: AsyncSession,
    ):
        """POST /api/v1/trial/activate activates trial for a mobile user."""
        _user_id, access_token = await _create_mobile_user(db)

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
        """POST /api/v1/trial/activate rejects users who already spent trial."""
        _user_id, access_token = await _create_mobile_user(
            db,
            trial_activated_at=datetime.now(UTC) - timedelta(days=10),
            trial_expires_at=datetime.now(UTC) - timedelta(days=3),
        )

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
        """POST /api/v1/trial/activate enforces Redis rate limiting."""
        user_id, access_token = await _create_mobile_user(db)

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
        """GET /api/v1/trial/status returns the current mobile-user status."""
        _user_id, access_token = await _create_mobile_user(db)

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
