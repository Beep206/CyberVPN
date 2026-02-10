"""Unit tests for the usage statistics endpoint.

Tests use httpx AsyncClient with ASGITransport and mock the
authentication dependency via FastAPI dependency overrides.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app
from src.presentation.dependencies.auth import get_current_active_user


class _MockUser:
    """Lightweight mock that satisfies AdminUserModel interface for routes."""

    def __init__(self) -> None:
        self.id = uuid4()
        self.login = "testuser"
        self.email = "test@cybervpn.dev"
        self.is_active = True
        self.updated_at = datetime.now(UTC)


def _mock_current_active_user() -> _MockUser:
    return _MockUser()


@pytest.fixture(autouse=True)
def _override_auth():
    """Override authentication for all tests in this module."""
    app.dependency_overrides[get_current_active_user] = _mock_current_active_user
    yield
    app.dependency_overrides.pop(get_current_active_user, None)


@pytest.mark.asyncio
async def test_get_usage_success() -> None:
    """GET /api/v1/users/me/usage returns 200 with expected fields."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/users/me/usage")

    assert response.status_code == 200
    data = response.json()
    assert "bandwidth_used_bytes" in data
    assert "bandwidth_limit_bytes" in data
    assert "connections_active" in data
    assert "connections_limit" in data
    assert "period_start" in data
    assert "period_end" in data
    assert isinstance(data["bandwidth_used_bytes"], int)
    assert isinstance(data["connections_active"], int)


@pytest.mark.asyncio
async def test_get_usage_requires_auth() -> None:
    """GET /api/v1/users/me/usage returns 401/403 without auth."""
    # Remove override so real auth dependency runs
    app.dependency_overrides.pop(get_current_active_user, None)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/users/me/usage")

        # Without a Bearer token the HTTPBearer dependency returns 403
        assert response.status_code in (401, 403)
    finally:
        # Restore override for remaining tests
        app.dependency_overrides[get_current_active_user] = _mock_current_active_user
