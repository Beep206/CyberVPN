from __future__ import annotations

from collections.abc import Awaitable, Callable
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.backend_api_client import BackendAPIClient, BackendAPIError

TelegramAudienceCall = Callable[[BackendAPIClient], Awaitable[dict]]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("client_method", "http_method"),
    [
        (
            lambda client: client.reconcile_telegram_stars_refund({"telegram_payment_charge_id": "charge-safe-ref"}),
            "post",
        ),
        (lambda client: client.get_public_network_regions(), "get"),
        (lambda client: client.publish_public_network_dpi_score({"countries": []}), "post"),
        (lambda client: client.claim_partner_bot_provisioning_job({"processor_id": "unit"}), "post"),
        (
            lambda client: client.finalize_partner_bot_provisioning_job(
                provisioning_job_id="job-safe-ref",
                payload={"status": "succeeded"},
            ),
            "post",
        ),
        (lambda client: client.refresh_growth_reporting({"window_days": 14}), "post"),
        (lambda client: client.claim_growth_reporting_deliveries({"limit": 10}), "post"),
        (
            lambda client: client.complete_growth_reporting_delivery(
                delivery_id="delivery-safe-ref",
                payload={"status": "sent"},
            ),
            "post",
        ),
        (lambda client: client.cleanup_growth_reporting_artifacts(), "post"),
        (lambda client: client.process_growth_reporting_governance_followups(), "post"),
    ],
)
async def test_telegram_audience_methods_use_telegram_bot_internal_secret(
    mock_settings,
    client_method: TelegramAudienceCall,
    http_method: str,
) -> None:
    mock_settings.backend_api_url = "https://backend.example.test/api/v1"
    mock_settings.backend_internal_secret.get_secret_value.return_value = "backend-internal-secret"
    mock_settings.telegram_bot_internal_secret.get_secret_value.return_value = "telegram-bot-internal-secret"

    with (
        patch("src.services.backend_api_client.get_settings", return_value=mock_settings),
        patch("src.services.backend_api_client.httpx.AsyncClient") as client_cls,
    ):
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"ok": True}
        http_client = AsyncMock()
        http_client.get.return_value = response
        http_client.post.return_value = response
        client_cls.return_value = http_client

        async with BackendAPIClient() as backend:
            result = await client_method(backend)

    assert result == {"ok": True}
    awaited = getattr(http_client, http_method).await_args
    request_headers = awaited.kwargs["headers"]
    assert request_headers == {"X-Telegram-Bot-Secret": "telegram-bot-internal-secret"}
    assert "X-Backend-Internal-Secret" not in request_headers


@pytest.mark.asyncio
async def test_backend_audience_methods_do_not_use_telegram_bot_secret(mock_settings) -> None:
    mock_settings.backend_api_url = "https://backend.example.test/api/v1"
    mock_settings.backend_internal_secret.get_secret_value.return_value = "backend-internal-secret"
    mock_settings.telegram_bot_internal_secret.get_secret_value.return_value = "telegram-bot-internal-secret"

    with (
        patch("src.services.backend_api_client.get_settings", return_value=mock_settings),
        patch("src.services.backend_api_client.httpx.AsyncClient") as client_cls,
    ):
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"ok": True}
        http_client = AsyncMock()
        http_client.post.return_value = response
        client_cls.return_value = http_client

        async with BackendAPIClient() as backend:
            await backend.run_stage1_payment_reconciliation({"limit": 3})
            await backend.run_stage1_provisioning_retries({"limit": 3})
            await backend.refresh_growth_fx_rates({"idempotency_key": "unit"})

    for awaited in http_client.post.await_args_list:
        request_headers = awaited.kwargs["headers"]
        assert request_headers == {"X-Backend-Internal-Secret": "backend-internal-secret"}
        assert "X-Telegram-Bot-Secret" not in request_headers


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("client_method", "http_method"),
    [
        (
            lambda client: client.reconcile_telegram_stars_refund({"telegram_payment_charge_id": "charge-safe-ref"}),
            "post",
        ),
        (lambda client: client.get_public_network_regions(), "get"),
        (lambda client: client.publish_public_network_dpi_score({"countries": []}), "post"),
        (lambda client: client.claim_partner_bot_provisioning_job({"processor_id": "unit"}), "post"),
        (
            lambda client: client.finalize_partner_bot_provisioning_job(
                provisioning_job_id="job-safe-ref",
                payload={"status": "succeeded"},
            ),
            "post",
        ),
        (lambda client: client.refresh_growth_reporting({"window_days": 14}), "post"),
        (lambda client: client.claim_growth_reporting_deliveries({"limit": 10}), "post"),
        (
            lambda client: client.complete_growth_reporting_delivery(
                delivery_id="delivery-safe-ref",
                payload={"status": "sent"},
            ),
            "post",
        ),
        (lambda client: client.cleanup_growth_reporting_artifacts(), "post"),
        (lambda client: client.process_growth_reporting_governance_followups(), "post"),
    ],
)
async def test_internal_backend_failures_do_not_log_or_raise_response_body(
    mock_settings,
    client_method: TelegramAudienceCall,
    http_method: str,
) -> None:
    mock_settings.backend_api_url = "https://backend.example.test/api/v1"
    mock_settings.backend_internal_secret.get_secret_value.return_value = "backend-internal-secret"
    mock_settings.telegram_bot_internal_secret.get_secret_value.return_value = "telegram-bot-internal-secret"

    with (
        patch("src.services.backend_api_client.get_settings", return_value=mock_settings),
        patch("src.services.backend_api_client.httpx.AsyncClient") as client_cls,
        patch("src.services.backend_api_client.logger") as logger_mock,
    ):
        response = MagicMock()
        response.status_code = 500
        response.text = "secret-subscription-url raw-token customer@example.invalid"
        http_client = AsyncMock()
        http_client.get.return_value = response
        http_client.post.return_value = response
        client_cls.return_value = http_client

        async with BackendAPIClient() as backend:
            with pytest.raises(BackendAPIError) as exc_info:
                await client_method(backend)

    assert str(response.status_code) in str(exc_info.value)
    assert response.text not in str(exc_info.value)
    assert getattr(http_client, http_method).await_count == 1
    assert logger_mock.error.call_count == 1
    log_kwargs = logger_mock.error.call_args.kwargs
    assert log_kwargs["status_code"] == 500
    assert "response" not in log_kwargs
