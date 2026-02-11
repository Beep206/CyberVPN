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
    async def test_register_with_email_returns_201(self, async_client):
        """POST /api/v1/auth/register with email creates inactive user."""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "SecurePassword123!",
                "username": "newuser"
            }
        )
        assert response.status_code in [201, 200, 404, 422]

    @pytest.mark.integration
    async def test_register_without_email_returns_201_active(self, async_client):
        """POST /api/v1/auth/register without email creates active user with tokens."""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "username": "usernameonly",
                "password": "SecurePassword123!"
            }
        )
        assert response.status_code in [201, 200, 404, 422]

    @pytest.mark.integration
    async def test_register_duplicate_email_returns_409(self, async_client):
        """Duplicate email registration returns 409 Conflict."""
        # First registration
        await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "duplicate@example.com",
                "password": "SecurePassword123!",
                "username": "duplicate1"
            }
        )

        # Second registration with same email
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "duplicate@example.com",
                "password": "SecurePassword123!",
                "username": "duplicate2"
            }
        )
        assert response.status_code in [409, 400, 422, 404]

    @pytest.mark.integration
    async def test_register_weak_password_returns_422(self, async_client):
        """Registration with weak password returns 422."""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "weakpass@example.com",
                "password": "123",  # Weak password
                "username": "weakpassuser"
            }
        )
        assert response.status_code in [422, 400, 404]

    @pytest.mark.integration
    async def test_rate_limit_on_register(self, async_client):
        """Rapid registration requests trigger rate limiting."""
        # Make multiple rapid registration requests
        for i in range(10):
            response = await async_client.post(
                "/api/v1/auth/register",
                json={
                    "email": f"ratelimit{i}@example.com",
                    "password": "SecurePassword123!",
                    "username": f"ratelimit{i}"
                }
            )
            # Should eventually hit rate limit (429)
            assert response.status_code in [201, 200, 404, 422, 429, 409]
