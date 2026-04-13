from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.application.use_cases.monitoring.bandwidth_analytics import BandwidthAnalyticsUseCase


def _analytics_payload() -> SimpleNamespace:
    return SimpleNamespace(
        bandwidth_last_two_days=SimpleNamespace(current=101),
        bandwidth_last_seven_days=SimpleNamespace(current=202),
        bandwidth_calendar_month=SimpleNamespace(current=303),
    )


@pytest.mark.unit
async def test_execute_uses_validated_bandwidth_payload():
    client = AsyncMock()
    client.get_validated.return_value = _analytics_payload()

    result = await BandwidthAnalyticsUseCase(client).execute(period="week")

    client.get_validated.assert_awaited_once()
    assert result == {"bytes_in": 0, "bytes_out": 202}


@pytest.mark.unit
async def test_execute_defaults_to_today_window_for_unknown_period():
    client = AsyncMock()
    client.get_validated.return_value = _analytics_payload()

    result = await BandwidthAnalyticsUseCase(client).execute(period="unexpected")

    assert result == {"bytes_in": 0, "bytes_out": 101}
