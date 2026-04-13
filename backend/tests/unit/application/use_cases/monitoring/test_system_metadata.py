from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.application.use_cases.monitoring.system_metadata import SystemMetadataUseCase


@pytest.mark.unit
async def test_execute_maps_metadata_payload():
    client = AsyncMock()
    client.get_validated.return_value = SimpleNamespace(
        version="2.7.4",
        build=SimpleNamespace(model_dump=lambda **_kwargs: {"time": "2026-03-30T00:00:00Z", "number": "274"}),
        git=SimpleNamespace(
            model_dump=lambda **_kwargs: {
                "backend": {
                    "commit_sha": "backendsha",
                    "branch": "main",
                    "commit_url": "https://example.com/backend",
                },
                "frontend": {
                    "commit_sha": "frontendsha",
                    "commit_url": "https://example.com/frontend",
                },
            }
        ),
    )

    result = await SystemMetadataUseCase(client).execute()

    assert result["version"] == "2.7.4"
    assert result["build"]["number"] == "274"
    assert result["git"]["backend"]["branch"] == "main"
