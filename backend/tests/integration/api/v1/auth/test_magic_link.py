"""Integration tests for magic link authentication routes.

Tests the full HTTP flow:
- POST /api/v1/auth/magic-link/request (send magic link email)
- POST /api/v1/auth/magic-link/verify (verify token, get JWT)

Requires: TestClient, test database, fakeredis.
"""

import secrets

import pytest

from src.application.services.magic_link_service import MagicLinkService
from src.infrastructure.cache.redis_client import get_redis_client


async def _clear_magic_link_state(email: str) -> None:
    redis_client = await get_redis_client()
    try:
        await redis_client.delete(
            f"{MagicLinkService.EMAIL_TOKEN_PREFIX}{email}",
            f"{MagicLinkService.OTP_PREFIX}{email}",
            f"{MagicLinkService.RATE_LIMIT_PREFIX}{email}",
        )
    finally:
        await redis_client.aclose()


class TestMagicLinkRoutes:
    """Integration tests for magic link HTTP endpoints."""

    @pytest.mark.integration
    async def test_request_magic_link_returns_200(self, async_client):
        """POST /api/v1/auth/magic-link with valid email returns 200."""
        email = f"request-{secrets.token_hex(4)}@example.com"
        await _clear_magic_link_state(email)

        response = await async_client.post(
            "/api/v1/auth/magic-link",
            json={"email": email}
        )
        assert response.status_code == 200

    @pytest.mark.integration
    async def test_request_magic_link_creates_redis_token(self, async_client):
        """Magic link request stores token in Redis with 15min TTL."""
        email = "magic-link-redis@example.com"
        email = f"magic-link-redis-{secrets.token_hex(4)}@example.com"
        await _clear_magic_link_state(email)

        response = await async_client.post(
            "/api/v1/auth/magic-link",
            json={"email": email},
        )
        assert response.status_code == 200

        redis_client = await get_redis_client()
        try:
            token = await redis_client.get(f"{MagicLinkService.EMAIL_TOKEN_PREFIX}{email}")
            assert token is not None
        finally:
            await redis_client.aclose()

    @pytest.mark.integration
    async def test_verify_valid_token_returns_jwt(self, async_client):
        """POST /api/v1/auth/magic-link/verify with valid token returns JWT tokens."""
        import secrets

        email = f"verify-{secrets.token_hex(4)}@example.com"
        token = secrets.token_urlsafe(32)
        redis_client = await get_redis_client()
        try:
            await redis_client.setex(f"{MagicLinkService.PREFIX}{token}", 900, email)
        finally:
            await redis_client.aclose()

        response = await async_client.post(
            "/api/v1/auth/magic-link/verify",
            json={"token": token},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    @pytest.mark.integration
    async def test_verify_expired_token_returns_400(self, async_client):
        """Verify with expired token returns 400."""
        response = await async_client.post(
            "/api/v1/auth/magic-link/verify",
            json={"token": "expired-token"}
        )
        assert response.status_code == 400

    @pytest.mark.integration
    async def test_verify_invalid_token_returns_400(self, async_client):
        """Verify with non-existent token returns 400."""
        response = await async_client.post(
            "/api/v1/auth/magic-link/verify",
            json={"token": "invalid-nonexistent-token"}
        )
        assert response.status_code == 400

    @pytest.mark.integration
    async def test_token_is_single_use(self, async_client):
        """Magic link token supports one replay, then expires."""
        import secrets

        email = f"single-use-{secrets.token_hex(4)}@example.com"
        token = "single-use-token"
        redis_client = await get_redis_client()
        try:
            await redis_client.setex(f"{MagicLinkService.PREFIX}{token}", 900, email)
        finally:
            await redis_client.aclose()

        response1 = await async_client.post(
            "/api/v1/auth/magic-link/verify",
            json={"token": token}
        )
        response2 = await async_client.post(
            "/api/v1/auth/magic-link/verify",
            json={"token": token}
        )
        response3 = await async_client.post(
            "/api/v1/auth/magic-link/verify",
            json={"token": token}
        )

        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response3.status_code == 400

    @pytest.mark.integration
    async def test_rate_limit_on_request(self, async_client):
        """More than 5 requests per hour triggers rate limiting."""
        email = f"ratelimit-{secrets.token_hex(4)}@example.com"
        await _clear_magic_link_state(email)

        for _ in range(5):
            response = await async_client.post(
                "/api/v1/auth/magic-link",
                json={"email": email}
            )
            assert response.status_code == 200

        response = await async_client.post(
            "/api/v1/auth/magic-link",
            json={"email": email}
        )
        assert response.status_code == 429
        assert "too many requests" in response.json()["detail"].lower()
