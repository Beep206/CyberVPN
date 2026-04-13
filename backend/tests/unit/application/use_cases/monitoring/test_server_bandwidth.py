from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.application.use_cases.monitoring.server_bandwidth import ServerBandwidthUseCase


@pytest.mark.unit
async def test_execute_uses_validated_stats_and_recap():
    client = AsyncMock()
    client.get_validated.side_effect = [
        SimpleNamespace(
            users=SimpleNamespace(total_users=150),
            online_stats=SimpleNamespace(online_now=12),
            nodes=SimpleNamespace(total_online=8, total_bytes_lifetime=999),
        ),
        SimpleNamespace(
            total=SimpleNamespace(nodes=10, traffic=123456),
        ),
    ]

    result = await ServerBandwidthUseCase(client).execute()

    assert result == {
        "total_users": 150,
        "active_users": 12,
        "total_servers": 10,
        "online_servers": 8,
        "total_traffic_bytes": 123456,
    }


@pytest.mark.unit
async def test_execute_falls_back_to_node_lifetime_traffic_when_recap_is_zero():
    client = AsyncMock()
    client.get_validated.side_effect = [
        SimpleNamespace(
            users=SimpleNamespace(total_users=5),
            online_stats=SimpleNamespace(online_now=2),
            nodes=SimpleNamespace(total_online=1, total_bytes_lifetime=777),
        ),
        SimpleNamespace(
            total=SimpleNamespace(nodes=1, traffic=0),
        ),
    ]

    result = await ServerBandwidthUseCase(client).execute()

    assert result["total_traffic_bytes"] == 777
