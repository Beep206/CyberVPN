"""Integration tests for user registration routes.

Tests:
- POST /api/v1/auth/register (email + password)
- POST /api/v1/auth/register (username-only, no email)

Requires: TestClient, test database, fakeredis.
"""

import pytest


class TestRegisterRoutes:
    """Integration tests for registration HTTP endpoints."""

    @pytest.mark.integration
    @pytest.mark.skip(reason="Integration test infrastructure not yet available")
    async def test_register_with_email_returns_201(self):
        """POST /api/v1/auth/register with email creates inactive user."""
        pass

    @pytest.mark.integration
    @pytest.mark.skip(reason="Integration test infrastructure not yet available")
    async def test_register_without_email_returns_201_active(self):
        """POST /api/v1/auth/register without email creates active user with tokens."""
        pass

    @pytest.mark.integration
    @pytest.mark.skip(reason="Integration test infrastructure not yet available")
    async def test_register_duplicate_email_returns_409(self):
        """Duplicate email registration returns 409 Conflict."""
        pass

    @pytest.mark.integration
    @pytest.mark.skip(reason="Integration test infrastructure not yet available")
    async def test_register_weak_password_returns_422(self):
        """Registration with weak password returns 422."""
        pass

    @pytest.mark.integration
    @pytest.mark.skip(reason="Integration test infrastructure not yet available")
    async def test_rate_limit_on_register(self):
        """Rapid registration requests trigger rate limiting."""
        pass
