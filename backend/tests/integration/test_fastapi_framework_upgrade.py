"""Regression tests for the FastAPI 0.135.x / Starlette 1.0 upgrade."""

from datetime import datetime
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.integration
class TestFastAPIFrameworkUpgrade:
    @pytest.mark.asyncio
    async def test_metrics_endpoint_stays_on_exact_path(self) -> None:
        """The test-only metrics app should keep `/metrics` as a 200, not a redirect."""
        from src.main import metrics_app

        async with AsyncClient(transport=ASGITransport(app=metrics_app), base_url="http://test") as client:
            response = await client.get("/metrics")

        assert response.status_code == 200
        assert "text/plain" in response.headers.get("content-type", "").lower()
        assert "# HELP http_requests_total" in response.text

    @pytest.mark.asyncio
    async def test_private_network_preflight_is_allowed_for_configured_origins(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Starlette 0.51+ private-network preflight support should be enabled."""
        response = await async_client.options(
            "/api/v1/auth/login",
            headers={
                "origin": "http://localhost:3000",
                "access-control-request-method": "POST",
                "access-control-request-private-network": "true",
            },
        )

        assert response.status_code == 200
        assert response.headers.get("access-control-allow-private-network") == "true"

    @pytest.mark.asyncio
    async def test_http_metrics_keep_legacy_names_and_handler_labels(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Custom middleware should preserve the metric names our dashboards already use."""
        from src.main import metrics_app

        await async_client.post(
            "/api/v1/auth/login",
            content='{"login_or_email":"invalid","password":"invalid"}',
            headers={"content-type": "text/plain"},
        )

        async with AsyncClient(transport=ASGITransport(app=metrics_app), base_url="http://test") as client:
            response = await client.get("/metrics")

        assert response.status_code == 200
        body = response.text
        assert 'http_requests_total{handler="/api/v1/auth/login",method="POST",status="4xx"}' in body
        assert 'http_requests_in_progress{handler="/api/v1/auth/login",method="POST"}' in body
        assert 'http_request_duration_seconds_bucket{handler="/api/v1/auth/login",le="0.1",method="POST"}' in body

    @pytest.mark.asyncio
    async def test_readiness_response_includes_timestamp_services_and_queue_depth(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Readiness should expose orchestrator-friendly status plus queue depth diagnostics."""

        class FakeRedisClient:
            async def xlen(self, _name: str) -> int:
                return 7

            async def aclose(self) -> None:
                return None

        with (
            patch("src.main.check_db_connection", return_value=True),
            patch("src.main.check_redis_connection", return_value=(True, 1.2)),
            patch("src.main.get_redis_client", return_value=FakeRedisClient()),
        ):
            response = await async_client.get("/readiness")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "ready"
        assert data["services"] == {
            "database": "ok",
            "redis": "ok",
            "queue": "ok",
        }
        assert data["checks"]["queue_depth"] == 7
        assert data["checks"]["queue"] is True
        datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))

    @pytest.mark.asyncio
    async def test_readiness_returns_503_when_queue_depth_exceeds_threshold(
        self,
        async_client: AsyncClient,
    ) -> None:
        """A backed-up task queue should keep the service out of ready state."""

        class FakeRedisClient:
            async def xlen(self, _name: str) -> int:
                return 1000

            async def aclose(self) -> None:
                return None

        with (
            patch("src.main.check_db_connection", return_value=True),
            patch("src.main.check_redis_connection", return_value=(True, 1.2)),
            patch("src.main.get_redis_client", return_value=FakeRedisClient()),
        ):
            response = await async_client.get("/readiness")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["services"]["queue"] == "error"
        assert data["checks"]["queue_depth"] == 1000
        assert data["checks"]["queue"] is False
