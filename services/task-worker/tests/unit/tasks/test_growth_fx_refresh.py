"""Unit tests for scheduled Growth Codes FX refresh task."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from src.services.backend_api_client import BackendAPIClient, BackendAPIError
from src.tasks.analytics.refresh_growth_fx import refresh_growth_fx_rates
from src.utils.constants import SCHEDULE_GROWTH_FX_REFRESH


@pytest.mark.asyncio
async def test_refresh_growth_fx_rates_calls_internal_backend_refresh(mock_settings) -> None:
    mock_backend = AsyncMock()
    mock_backend.enabled = True
    mock_backend.refresh_growth_fx_rates = AsyncMock(
        return_value={
            "triggered_at": "2026-06-27T04:15:00Z",
            "run_count": 2,
            "created_snapshot_count": 3,
            "run_statuses": {"succeeded": 1, "partial": 1},
            "skipped": False,
            "reason": None,
        }
    )

    with (
        patch(
            "src.tasks.analytics.refresh_growth_fx.get_settings",
            return_value=mock_settings,
        ),
        patch(
            "src.tasks.analytics.refresh_growth_fx.BackendAPIClient",
        ) as mock_backend_cls,
    ):
        mock_backend_cls.return_value.__aenter__ = AsyncMock(return_value=mock_backend)
        mock_backend_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await refresh_growth_fx_rates()

    assert result == {
        "refreshed_at": "2026-06-27T04:15:00Z",
        "run_count": 2,
        "created_snapshot_count": 3,
        "run_statuses": {"succeeded": 1, "partial": 1},
        "skipped": False,
        "reason": None,
    }
    mock_backend.refresh_growth_fx_rates.assert_awaited_once()
    payload = mock_backend.refresh_growth_fx_rates.await_args.args[0]
    assert payload["idempotency_key"].startswith("scheduled:")


@pytest.mark.asyncio
async def test_backend_client_refresh_growth_fx_rates_sends_internal_refresh_contract(mock_settings) -> None:
    mock_settings.backend_api_url = "https://backend.example.test/api/v1"
    mock_settings.backend_internal_secret.get_secret_value.return_value = "InternalBackendCredentialForChecksOnly"
    captured_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(
            200,
            json={
                "triggered_at": "2026-06-27T04:15:00Z",
                "run_count": 1,
                "created_snapshot_count": 1,
                "run_statuses": {"succeeded": 1},
            },
        )

    transport = httpx.MockTransport(handler)
    real_async_client = httpx.AsyncClient

    def client_with_transport(*args, **kwargs):
        kwargs["transport"] = transport
        return real_async_client(*args, **kwargs)

    with (
        patch("src.services.backend_api_client.get_settings", return_value=mock_settings),
        patch("src.services.backend_api_client.httpx.AsyncClient", side_effect=client_with_transport),
    ):
        async with BackendAPIClient() as backend:
            response = await backend.refresh_growth_fx_rates({"idempotency_key": "scheduled:202606270415"})

    assert response["run_statuses"] == {"succeeded": 1}
    assert len(captured_requests) == 1
    request = captured_requests[0]
    assert request.method == "POST"
    assert request.url.path == "/api/v1/admin/growth-fx/internal/refresh"
    assert request.url.params["idempotency_key"] == "scheduled:202606270415"
    assert request.headers["X-Backend-Internal-Secret"] == "InternalBackendCredentialForChecksOnly"
    assert "X-Telegram-Bot-Secret" not in request.headers
    assert request.content == b""


@pytest.mark.asyncio
async def test_backend_client_refresh_growth_fx_rates_redacts_error_body(mock_settings) -> None:
    mock_settings.backend_api_url = "https://backend.example.test/api/v1"
    mock_settings.backend_internal_secret.get_secret_value.return_value = "InternalBackendCredentialForChecksOnly"
    leaked_body = "provider_secret=InternalBackendCredentialForChecksOnly"

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text=leaked_body)

    transport = httpx.MockTransport(handler)
    real_async_client = httpx.AsyncClient

    def client_with_transport(*args, **kwargs):
        kwargs["transport"] = transport
        return real_async_client(*args, **kwargs)

    with (
        patch("src.services.backend_api_client.get_settings", return_value=mock_settings),
        patch("src.services.backend_api_client.httpx.AsyncClient", side_effect=client_with_transport),
    ):
        async with BackendAPIClient() as backend:
            with pytest.raises(BackendAPIError) as exc:
                await backend.refresh_growth_fx_rates({"idempotency_key": "scheduled:202606270415"})

    assert str(exc.value) == "Growth FX refresh failed: 500"
    assert "InternalBackendCredentialForChecksOnly" not in str(exc.value)
    assert leaked_body not in str(exc.value)


@pytest.mark.asyncio
async def test_refresh_growth_fx_rates_skips_when_backend_not_configured(mock_settings) -> None:
    mock_settings.backend_api_url = None

    with patch(
        "src.tasks.analytics.refresh_growth_fx.get_settings",
        return_value=mock_settings,
    ):
        result = await refresh_growth_fx_rates()

    assert result == {"skipped": True, "reason": "backend_api_not_configured"}


def test_refresh_growth_fx_rates_is_registered_with_schedule() -> None:
    from src.schedules.definitions import refresh_growth_fx_rates as scheduled_task

    assert scheduled_task.labels["schedule"] == [{"cron": SCHEDULE_GROWTH_FX_REFRESH}]
