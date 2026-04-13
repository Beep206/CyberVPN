from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


class TestMonitoringOps:
    @pytest.mark.integration
    async def test_get_metadata(self, async_client: AsyncClient, auth_headers: dict[str, str]):
        with patch(
            "src.application.use_cases.monitoring.system_metadata.SystemMetadataUseCase.execute",
            AsyncMock(
                return_value={
                    "version": "2.7.4",
                    "build": {"time": "2026-03-30T00:00:00Z", "number": "274"},
                    "git": {
                        "backend": {
                            "commit_sha": "backendsha",
                            "branch": "main",
                            "commit_url": "https://example.com/backend",
                        },
                        "frontend": {
                            "commit_sha": "frontendsha",
                            "commit_url": "https://example.com/frontend",
                        },
                    },
                }
            ),
        ):
            response = await async_client.get("/api/v1/monitoring/metadata", headers=auth_headers)

        assert response.status_code == 200
        payload = response.json()
        assert payload["version"] == "2.7.4"
        assert payload["build"]["number"] == "274"
        assert payload["git"]["backend"]["branch"] == "main"
        assert "timestamp" in payload

    @pytest.mark.integration
    async def test_get_recap(self, async_client: AsyncClient, auth_headers: dict[str, str]):
        with patch(
            "src.application.use_cases.monitoring.system_recap.SystemRecapUseCase.execute",
            AsyncMock(
                return_value={
                    "version": "2.7.4",
                    "init_date": "2026-01-01T00:00:00+00:00",
                    "total": {
                        "users": 100,
                        "nodes": 10,
                        "traffic_bytes": 999999,
                        "nodes_ram": "64 GB",
                        "nodes_cpu_cores": 32,
                        "distinct_countries": 5,
                    },
                    "this_month": {
                        "users": 12,
                        "traffic_bytes": 12345,
                    },
                }
            ),
        ):
            response = await async_client.get("/api/v1/monitoring/recap", headers=auth_headers)

        assert response.status_code == 200
        payload = response.json()
        assert payload["version"] == "2.7.4"
        assert payload["total"]["nodes"] == 10
        assert payload["this_month"]["traffic_bytes"] == 12345
        assert "timestamp" in payload
