"""Unit tests for the trial period endpoints.

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
async def test_get_trial_status_success() -> None:
    """GET /api/v1/trial/status returns 200 with expected fields."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/trial/status")

    assert response.status_code == 200
    data = response.json()
    assert data["is_trial_active"] is False
    assert data["is_eligible"] is True
    assert data["days_remaining"] == 0
    assert data["trial_start"] is None
    assert data["trial_end"] is None


@pytest.mark.asyncio
async def test_activate_trial_success() -> None:
    """POST /api/v1/trial/activate returns 200 with activated=True and future trial_end."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post("/api/v1/trial/activate")

    assert response.status_code == 200
    data = response.json()
    assert data["activated"] is True
    assert "trial_end" in data
    assert "message" in data

    # trial_end should be in the future
    trial_end = datetime.fromisoformat(data["trial_end"])
    assert trial_end > datetime.now(UTC)


@pytest.mark.asyncio
async def test_activate_trial_idempotency() -> None:
    """POST /api/v1/trial/activate called twice should both succeed (placeholder behavior)."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        first = await client.post("/api/v1/trial/activate")
        second = await client.post("/api/v1/trial/activate")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["activated"] is True
    assert second.json()["activated"] is True


@pytest.mark.asyncio
async def test_trial_status_requires_auth() -> None:
    """GET /api/v1/trial/status returns 401/403 without auth."""
    app.dependency_overrides.pop(get_current_active_user, None)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/trial/status")

        assert response.status_code in (401, 403)
    finally:
        app.dependency_overrides[get_current_active_user] = _mock_current_active_user


@pytest.mark.asyncio
async def test_activate_trial_requires_auth() -> None:
    """POST /api/v1/trial/activate returns 401/403 without auth."""
    app.dependency_overrides.pop(get_current_active_user, None)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post("/api/v1/trial/activate")

        assert response.status_code in (401, 403)
    finally:
        app.dependency_overrides[get_current_active_user] = _mock_current_active_user
