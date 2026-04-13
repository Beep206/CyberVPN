from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.application.use_cases.monitoring.system_recap import SystemRecapUseCase


@pytest.mark.unit
async def test_execute_maps_recap_payload():
    client = AsyncMock()
    client.get_validated.return_value = SimpleNamespace(
        version="2.7.4",
        init_date=datetime(2026, 1, 1, 0, 0, tzinfo=UTC),
        total=SimpleNamespace(
            users=100,
            nodes=10,
            traffic=999999,
            nodes_ram="64 GB",
            nodes_cpu_cores=32,
            distinct_countries=5,
        ),
        this_month=SimpleNamespace(users=12, traffic=12345),
    )

    result = await SystemRecapUseCase(client).execute()

    assert result["version"] == "2.7.4"
    assert result["total"]["nodes"] == 10
    assert result["total"]["traffic_bytes"] == 999999
    assert result["this_month"]["traffic_bytes"] == 12345
