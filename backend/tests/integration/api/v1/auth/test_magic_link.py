"""Integration tests for magic link authentication routes.

Tests the full HTTP flow:
- POST /api/v1/auth/magic-link/request (send magic link email)
- POST /api/v1/auth/magic-link/verify (verify token, get JWT)

Requires: TestClient, test database, fakeredis.
"""

import pytest


class TestMagicLinkRoutes:
    """Integration tests for magic link HTTP endpoints."""

    @pytest.mark.integration
    @pytest.mark.skip(reason="Integration test infrastructure not yet available")
    async def test_request_magic_link_returns_200(self):
        """POST /api/v1/auth/magic-link/request with valid email returns 200."""
        pass

    @pytest.mark.integration
    @pytest.mark.skip(reason="Integration test infrastructure not yet available")
    async def test_request_magic_link_creates_redis_token(self):
        """Magic link request stores token in Redis with 15min TTL."""
        pass

    @pytest.mark.integration
    @pytest.mark.skip(reason="Integration test infrastructure not yet available")
    async def test_verify_valid_token_returns_jwt(self):
        """POST /api/v1/auth/magic-link/verify with valid token returns JWT tokens."""
        pass

    @pytest.mark.integration
    @pytest.mark.skip(reason="Integration test infrastructure not yet available")
    async def test_verify_expired_token_returns_400(self):
        """Verify with expired token returns 400."""
        pass

    @pytest.mark.integration
    @pytest.mark.skip(reason="Integration test infrastructure not yet available")
    async def test_verify_invalid_token_returns_400(self):
        """Verify with non-existent token returns 400."""
        pass

    @pytest.mark.integration
    @pytest.mark.skip(reason="Integration test infrastructure not yet available")
    async def test_token_is_single_use(self):
        """Magic link token is deleted after first successful verification."""
        pass

    @pytest.mark.integration
    @pytest.mark.skip(reason="Integration test infrastructure not yet available")
    async def test_rate_limit_on_request(self):
        """More than 5 requests per hour triggers rate limiting."""
        pass
