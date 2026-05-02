"""Unit tests for scheduled growth reporting refresh task."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from src.tasks.analytics.refresh_growth_reporting import refresh_growth_reporting_rollups


@pytest.mark.asyncio
async def test_refresh_growth_reporting_rollups_calls_internal_backend_refresh(
    mock_settings,
) -> None:
    mock_backend = AsyncMock()
    mock_backend.enabled = True
    mock_backend.refresh_growth_reporting = AsyncMock(
        return_value={
            "trigger_kind": "worker",
            "window_start": "2026-03-24",
            "window_end": "2026-04-22",
            "latest_rollup_date": "2026-04-22",
            "refreshed_at": "2026-04-22T14:00:00Z",
            "rows_written": 18,
            "families_updated": ["gift", "invite", "promo", "referral"],
        }
    )

    with (
        patch(
            "src.tasks.analytics.refresh_growth_reporting.get_settings",
            return_value=mock_settings,
        ),
        patch(
            "src.tasks.analytics.refresh_growth_reporting.BackendAPIClient",
        ) as mock_backend_cls,
    ):
        mock_backend_cls.return_value.__aenter__ = AsyncMock(return_value=mock_backend)
        mock_backend_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await refresh_growth_reporting_rollups()

    assert result["trigger_kind"] == "worker"
    assert result["rows_written"] == 18
    mock_backend.refresh_growth_reporting.assert_awaited_once_with({"window_days": 30})


@pytest.mark.asyncio
async def test_refresh_growth_reporting_rollups_skips_when_backend_not_configured(
    mock_settings,
) -> None:
    mock_settings.backend_api_url = None

    with patch(
        "src.tasks.analytics.refresh_growth_reporting.get_settings",
        return_value=mock_settings,
    ):
        result = await refresh_growth_reporting_rollups()

    assert result == {"skipped": True, "reason": "backend_api_not_configured"}
