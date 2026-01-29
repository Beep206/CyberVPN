import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.mark.asyncio
async def test_health_check_flow():
    """E2E test: verify the application starts and health endpoint works."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200

        response = await client.get("/docs")
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_unauthenticated_access_blocked():
    """E2E test: verify protected endpoints require authentication."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/auth/me")
        assert response.status_code in (401, 403, 404)
