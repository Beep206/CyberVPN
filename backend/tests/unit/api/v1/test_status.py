"""Unit tests for the public status endpoint.

Tests cover:
- GET /api/v1/status  (unauthenticated health/version check)
"""

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app
from src.version import __version__

BASE_URL = "/api/v1/status"

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clean_overrides():
    """Ensure dependency overrides are removed after every test."""
    yield
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# GET /api/v1/status
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_status_returns_200():
    """GET /api/v1/status returns HTTP 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(BASE_URL)

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_status_contains_required_fields():
    """Response body contains status, version, timestamp, and services."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(BASE_URL)

    body = response.json()
    assert "status" in body
    assert "version" in body
    assert "timestamp" in body
    assert "services" in body


@pytest.mark.asyncio
async def test_status_value_is_ok():
    """The status field equals 'ok'."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(BASE_URL)

    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_status_version_matches_source():
    """The version field matches src.version.__version__."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(BASE_URL)

    assert response.json()["version"] == __version__


@pytest.mark.asyncio
async def test_status_services_structure():
    """The services object contains database and redis sub-fields."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(BASE_URL)

    services = response.json()["services"]
    assert "database" in services
    assert "redis" in services
    assert services["database"] == "ok"
    assert services["redis"] == "ok"


@pytest.mark.asyncio
async def test_status_timestamp_is_iso_format():
    """The timestamp field is a parseable ISO 8601 datetime string."""
    from datetime import datetime

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(BASE_URL)

    ts = response.json()["timestamp"]
    # Should not raise -- confirms valid ISO 8601
    parsed = datetime.fromisoformat(ts)
    assert parsed.year >= 2025


@pytest.mark.asyncio
async def test_status_no_auth_required():
    """The endpoint is accessible without any Authorization header."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Explicitly send NO auth headers
        response = await client.get(BASE_URL, headers={})

    assert response.status_code == 200
