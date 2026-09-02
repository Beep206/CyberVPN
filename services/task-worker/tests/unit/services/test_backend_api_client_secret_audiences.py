from __future__ import annotations

import hashlib
from collections.abc import Awaitable, Callable
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from src.services.backend_api_client import (
    BackendAPIAutoRenewPermanentError,
    BackendAPIAutoRenewTransientError,
    BackendAPIClient,
    BackendAPIError,
    BackendAPIRemnawaveMaintenancePermanentError,
    BackendAPIRemnawaveMaintenanceTransientError,
    BackendAPIStreamPermanentError,
    BackendAPIStreamTransientError,
    auto_renew_idempotency_key,
    canonical_auto_renew_expiry,
)

TelegramAudienceCall = Callable[[BackendAPIClient], Awaitable[dict]]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status_code", "expected_error"),
    [
        (204, None),
        (409, BackendAPIStreamPermanentError),
        (422, BackendAPIStreamPermanentError),
        (401, BackendAPIStreamPermanentError),
        (200, BackendAPIStreamPermanentError),
        (429, BackendAPIStreamTransientError),
        (503, BackendAPIStreamTransientError),
        (500, BackendAPIStreamTransientError),
    ],
)
async def test_stream_ingestion_status_and_durable_commit_semantics(
    mock_settings,
    status_code: int,
    expected_error: type[Exception] | None,
) -> None:
    mock_settings.backend_api_url = "https://backend.example.test/api/v1"
    mock_settings.backend_internal_secret.get_secret_value.return_value = "backend-internal-secret"
    payload = {
        "event_type": "user_usage",
        "schema_version": "1",
        "node_id": 17,
        "observed_at": "2026-08-30T11:59:00+00:00",
        "records": [{"user_id": 42, "total_bytes": 1024}],
    }
    key = "remnawave:user_usage:1000-1"

    with (
        patch("src.services.backend_api_client.get_settings", return_value=mock_settings),
        patch("src.services.backend_api_client.httpx.AsyncClient") as client_cls,
    ):
        response = MagicMock(status_code=status_code)
        http_client = AsyncMock()
        http_client.post.return_value = response
        client_cls.return_value = http_client

        async with BackendAPIClient() as backend:
            if expected_error is None:
                await backend.persist_remnawave_stream_event(payload, idempotency_key=key)
            else:
                with pytest.raises(expected_error):
                    await backend.persist_remnawave_stream_event(payload, idempotency_key=key)

    http_client.post.assert_awaited_once_with(
        "internal/remnawave/streams/events",
        json=payload,
        headers={
            "X-Backend-Internal-Secret": "backend-internal-secret",
            "Idempotency-Key": key,
        },
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status_code", "expected_error"),
    [
        (204, None),
        (422, BackendAPIRemnawaveMaintenancePermanentError),
        (401, BackendAPIRemnawaveMaintenancePermanentError),
        (200, BackendAPIRemnawaveMaintenancePermanentError),
        (429, BackendAPIRemnawaveMaintenanceTransientError),
        (503, BackendAPIRemnawaveMaintenanceTransientError),
    ],
)
async def test_dead_letter_metadata_must_commit_before_redis_ack(
    mock_settings,
    status_code: int,
    expected_error: type[Exception] | None,
) -> None:
    mock_settings.backend_api_url = "https://backend.example.test/api/v1"
    mock_settings.backend_internal_secret.get_secret_value.return_value = "backend-internal-secret"
    payload = {
        "stream_name": "subscription_requests",
        "message_id": "1000-4",
        "schema_version": "1",
        "error_type": "StreamContractError",
        "redacted_reason": "invalid_payload",
        "payload_fingerprint": "a" * 64,
        "attempts": 3,
    }

    with (
        patch("src.services.backend_api_client.get_settings", return_value=mock_settings),
        patch("src.services.backend_api_client.httpx.AsyncClient") as client_cls,
    ):
        http_client = AsyncMock()
        http_client.post.return_value = MagicMock(status_code=status_code)
        client_cls.return_value = http_client

        async with BackendAPIClient() as backend:
            if expected_error is None:
                await backend.persist_remnawave_dead_letter(payload)
            else:
                with pytest.raises(expected_error):
                    await backend.persist_remnawave_dead_letter(payload)

    http_client.post.assert_awaited_once_with(
        "internal/remnawave/dead-letters",
        json=payload,
        headers={"X-Backend-Internal-Secret": "backend-internal-secret"},
    )


@pytest.mark.asyncio
async def test_stream_gap_requires_exact_committed_backend_receipt(mock_settings) -> None:
    mock_settings.backend_api_url = "https://backend.example.test/api/v1"
    mock_settings.backend_internal_secret.get_secret_value.return_value = "backend-internal-secret"
    detected_at = datetime.fromisoformat("2026-08-30T12:00:00+00:00")
    response_payload = {
        "gap_id": "11111111-1111-4111-8111-111111111111",
        "stream_name": "user_usage",
        "loss_kind": "exact_ids",
        "missing_message_ids": ["1000-1", "1000-2"],
        "missing_count": 2,
        "from_message_id": "1000-1",
        "to_message_id": "1000-2",
        "reconciliation_status": "pending",
        "detected_at": "2026-08-30T12:00:00Z",
        "reused": False,
    }

    with (
        patch("src.services.backend_api_client.get_settings", return_value=mock_settings),
        patch("src.services.backend_api_client.httpx.AsyncClient") as client_cls,
    ):
        response = MagicMock(status_code=201)
        response.json.return_value = response_payload
        http_client = AsyncMock()
        http_client.post.return_value = response
        client_cls.return_value = http_client

        async with BackendAPIClient() as backend:
            gap = await backend.create_remnawave_stream_gap(
                stream_name="user_usage",
                missing_message_ids=("1000-1", "1000-2"),
                detected_at=detected_at,
            )

    assert str(gap.gap_id) == response_payload["gap_id"]
    assert gap.stream_name == "user_usage"
    assert gap.reconciliation_status == "pending"

    http_client.post.assert_awaited_once_with(
        "internal/remnawave/stream-gaps",
        json={
            "stream_name": "user_usage",
            "missing_message_ids": ["1000-1", "1000-2"],
            "detected_at": "2026-08-30T12:00:00+00:00",
        },
        headers={"X-Backend-Internal-Secret": "backend-internal-secret"},
    )


@pytest.mark.asyncio
async def test_stream_gap_reconcile_requires_terminal_authoritative_receipt(mock_settings) -> None:
    mock_settings.backend_api_url = "https://backend.example.test/api/v1"
    mock_settings.backend_internal_secret.get_secret_value.return_value = "backend-internal-secret"
    gap_id = UUID("11111111-1111-4111-8111-111111111111")
    response_payload = {
        "gap_id": str(gap_id),
        "stream_name": "node_connections",
        "loss_kind": "exact_ids",
        "missing_message_ids": ["1000-1"],
        "missing_count": 1,
        "from_message_id": "1000-1",
        "to_message_id": "1000-1",
        "reconciliation_status": "partial",
        "detected_at": "2026-08-30T12:00:00Z",
        "reused": False,
    }

    with (
        patch("src.services.backend_api_client.get_settings", return_value=mock_settings),
        patch("src.services.backend_api_client.httpx.AsyncClient") as client_cls,
    ):
        response = MagicMock(status_code=200)
        response.json.return_value = response_payload
        http_client = AsyncMock()
        http_client.post.return_value = response
        client_cls.return_value = http_client

        async with BackendAPIClient() as backend:
            gap = await backend.reconcile_remnawave_stream_gap(
                gap_id=gap_id,
                stream_name="node_connections",
            )

    assert gap.reconciliation_status == "partial"
    http_client.post.assert_awaited_once_with(
        f"internal/remnawave/stream-gaps/{gap_id}/reconcile",
        headers={"X-Backend-Internal-Secret": "backend-internal-secret"},
    )


@pytest.mark.asyncio
async def test_stream_checkpoint_binds_pending_range_and_loss_decision(mock_settings) -> None:
    mock_settings.backend_api_url = "https://backend.example.test/api/v1"
    mock_settings.backend_internal_secret.get_secret_value.return_value = "backend-internal-secret"
    observed_at = datetime.fromisoformat("2026-08-30T12:00:00+00:00")
    response_payload = {
        "stream_name": "node_connections",
        "last_committed_message_id": "1000-2",
        "stream_exists": True,
        "group_exists": True,
        "loss_detected": True,
        "loss_reason": "group_skipped_range",
        "gap": {
            "gap_id": "11111111-1111-4111-8111-111111111111",
            "stream_name": "node_connections",
            "loss_kind": "unknown_range",
            "missing_message_ids": [],
            "missing_count": 0,
            "from_message_id": "1000-2",
            "to_message_id": "1000-5",
            "reconciliation_status": "pending",
            "detected_at": "2026-08-30T12:00:00Z",
            "reused": False,
        },
        "observed_at": "2026-08-30T12:00:00Z",
    }

    with (
        patch("src.services.backend_api_client.get_settings", return_value=mock_settings),
        patch("src.services.backend_api_client.httpx.AsyncClient") as client_cls,
    ):
        response = MagicMock(status_code=200)
        response.json.return_value = response_payload
        http_client = AsyncMock()
        http_client.post.return_value = response
        client_cls.return_value = http_client

        async with BackendAPIClient() as backend:
            result = await backend.observe_remnawave_stream_checkpoint(
                stream_name="node_connections",
                observed_stream_identity="redis-run-1",
                stream_exists=True,
                group_exists=True,
                first_message_id="1000-1",
                last_message_id="1000-5",
                group_last_delivered_id="1000-5",
                group_pending_count=0,
                group_pending_min_id=None,
                group_pending_max_id=None,
                observed_at=observed_at,
                group_lag=4,
            )

    assert result.loss_detected is True
    assert result.loss_reason == "group_skipped_range"
    assert str(result.gap_id) == response_payload["gap"]["gap_id"]
    assert result.reconciliation_status == "pending"
    http_client.post.assert_awaited_once_with(
        "internal/remnawave/stream-checkpoints/node_connections/observe",
        json={
            "observed_stream_identity": "redis-run-1",
            "stream_exists": True,
            "group_exists": True,
            "first_message_id": "1000-1",
            "last_message_id": "1000-5",
            "group_last_delivered_id": "1000-5",
            "group_pending_count": 0,
            "group_pending_min_id": None,
            "group_pending_max_id": None,
            "group_lag": 4,
            "observed_at": "2026-08-30T12:00:00+00:00",
        },
        headers={"X-Backend-Internal-Secret": "backend-internal-secret"},
    )


@pytest.mark.asyncio
async def test_retention_purge_validates_exact_backend_receipt(mock_settings) -> None:
    mock_settings.backend_api_url = "https://backend.example.test/api/v1"
    mock_settings.backend_internal_secret.get_secret_value.return_value = "backend-internal-secret"
    deleted_by_table = {
        "remnawave_stream_receipts": 2,
        "remnawave_stream_dead_letters": 1,
        "remnawave_user_usage_hourly": 0,
        "remnawave_subscription_request_events": 0,
        "remnawave_node_user_presence": 0,
        "remnawave_node_connections_hourly": 0,
    }

    with (
        patch("src.services.backend_api_client.get_settings", return_value=mock_settings),
        patch("src.services.backend_api_client.httpx.AsyncClient") as client_cls,
    ):
        response = MagicMock(status_code=200)
        response.json.return_value = {
            "deleted_by_table": deleted_by_table,
            "total_deleted": 3,
            "has_more": True,
            "purged_at": "2026-08-30T12:00:00Z",
        }
        http_client = AsyncMock()
        http_client.post.return_value = response
        client_cls.return_value = http_client

        async with BackendAPIClient() as backend:
            receipt = await backend.purge_remnawave_stream_retention(batch_limit=1000)

    assert receipt.deleted_by_table == deleted_by_table
    assert receipt.total_deleted == 3
    assert receipt.has_more is True
    assert receipt.purged_at.isoformat() == "2026-08-30T12:00:00+00:00"
    http_client.post.assert_awaited_once_with(
        "internal/remnawave/retention/purge",
        json={"batch_limit": 1000},
        headers={"X-Backend-Internal-Secret": "backend-internal-secret"},
    )


@pytest.mark.asyncio
async def test_retention_purge_rejects_inconsistent_or_extra_receipt(mock_settings) -> None:
    mock_settings.backend_api_url = "https://backend.example.test/api/v1"
    mock_settings.backend_internal_secret.get_secret_value.return_value = "backend-internal-secret"

    with (
        patch("src.services.backend_api_client.get_settings", return_value=mock_settings),
        patch("src.services.backend_api_client.httpx.AsyncClient") as client_cls,
    ):
        response = MagicMock(status_code=200)
        response.json.return_value = {
            "deleted_by_table": {"remnawave_stream_receipts": 1},
            "total_deleted": 999,
            "has_more": False,
            "purged_at": "2026-08-30T12:00:00Z",
            "raw_payload": "must-not-be-accepted",
        }
        http_client = AsyncMock()
        http_client.post.return_value = response
        client_cls.return_value = http_client

        async with BackendAPIClient() as backend:
            with pytest.raises(BackendAPIRemnawaveMaintenancePermanentError):
                await backend.purge_remnawave_stream_retention(batch_limit=1000)


@pytest.mark.asyncio
async def test_auto_renew_invoice_uses_exact_canonical_expiry_and_backend_contract(mock_settings) -> None:
    mock_settings.backend_api_url = "https://backend.example.test/api/v1"
    mock_settings.backend_internal_secret.get_secret_value.return_value = "backend-internal-secret"
    expiry = datetime.fromisoformat("2026-08-30T12:00:00+05:00")
    canonical_expiry = "2026-08-30T07:00:00Z"
    digest = hashlib.sha256(canonical_expiry.encode("utf-8")).hexdigest()

    with (
        patch("src.services.backend_api_client.get_settings", return_value=mock_settings),
        patch("src.services.backend_api_client.httpx.AsyncClient") as client_cls,
    ):
        response = MagicMock(status_code=200)
        response.json.return_value = {
            "payment_id": "550e8400-e29b-41d4-a716-446655440010",
            "reused": False,
            "notification_status": "queued",
        }
        http_client = AsyncMock()
        http_client.post.return_value = response
        client_cls.return_value = http_client

        async with BackendAPIClient() as backend:
            invoice = await backend.create_remnawave_auto_renew_invoice(
                remnawave_user_id=42,
                expected_expire_at=expiry,
            )

    assert canonical_auto_renew_expiry(expiry) == canonical_expiry
    assert auto_renew_idempotency_key(42, expiry) == f"remnawave:auto-renew:42:{digest}"
    assert invoice.reused is False
    assert invoice.notification_status == "queued"
    assert not hasattr(invoice, "pay_url")
    http_client.post.assert_awaited_once_with(
        "internal/remnawave/users/42/auto-renew-invoice",
        json={"expected_expire_at": canonical_expiry},
        headers={
            "X-Backend-Internal-Secret": "backend-internal-secret",
            "Idempotency-Key": f"remnawave:auto-renew:42:{digest}",
        },
    )


@pytest.mark.asyncio
async def test_auto_renew_eligibility_uses_bounded_backend_owned_filter(mock_settings) -> None:
    mock_settings.backend_api_url = "https://backend.example.test/api/v1"
    mock_settings.backend_internal_secret.get_secret_value.return_value = "backend-internal-secret"

    with (
        patch("src.services.backend_api_client.get_settings", return_value=mock_settings),
        patch("src.services.backend_api_client.httpx.AsyncClient") as client_cls,
    ):
        response = MagicMock(status_code=200)
        response.json.return_value = {"eligible_user_ids": [42]}
        http_client = AsyncMock()
        http_client.post.return_value = response
        client_cls.return_value = http_client

        async with BackendAPIClient() as backend:
            eligible = await backend.filter_remnawave_auto_renew_eligible([42, 43])

    assert eligible == frozenset({42})
    http_client.post.assert_awaited_once_with(
        "internal/remnawave/auto-renew/eligible",
        json={"user_ids": [42, 43]},
        headers={"X-Backend-Internal-Secret": "backend-internal-secret"},
    )


@pytest.mark.asyncio
async def test_auto_renew_eligibility_rejects_unrequested_user_id(mock_settings) -> None:
    mock_settings.backend_api_url = "https://backend.example.test/api/v1"
    mock_settings.backend_internal_secret.get_secret_value.return_value = "backend-internal-secret"

    with (
        patch("src.services.backend_api_client.get_settings", return_value=mock_settings),
        patch("src.services.backend_api_client.httpx.AsyncClient") as client_cls,
    ):
        response = MagicMock(status_code=200)
        response.json.return_value = {"eligible_user_ids": [999]}
        http_client = AsyncMock()
        http_client.post.return_value = response
        client_cls.return_value = http_client

        async with BackendAPIClient() as backend:
            with pytest.raises(BackendAPIAutoRenewPermanentError):
                await backend.filter_remnawave_auto_renew_eligible([42])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status_code", "expected_error"),
    [
        (401, BackendAPIAutoRenewPermanentError),
        (404, BackendAPIAutoRenewPermanentError),
        (409, BackendAPIAutoRenewPermanentError),
        (422, BackendAPIAutoRenewPermanentError),
        (429, BackendAPIAutoRenewTransientError),
        (500, BackendAPIAutoRenewTransientError),
        (502, BackendAPIAutoRenewTransientError),
        (503, BackendAPIAutoRenewTransientError),
        (504, BackendAPIAutoRenewTransientError),
    ],
)
async def test_auto_renew_invoice_classifies_backend_statuses(
    mock_settings,
    status_code: int,
    expected_error: type[Exception],
) -> None:
    mock_settings.backend_api_url = "https://backend.example.test/api/v1"
    mock_settings.backend_internal_secret.get_secret_value.return_value = "backend-internal-secret"

    with (
        patch("src.services.backend_api_client.get_settings", return_value=mock_settings),
        patch("src.services.backend_api_client.httpx.AsyncClient") as client_cls,
    ):
        http_client = AsyncMock()
        http_client.post.return_value = MagicMock(status_code=status_code)
        client_cls.return_value = http_client

        async with BackendAPIClient() as backend:
            with pytest.raises(expected_error):
                await backend.create_remnawave_auto_renew_invoice(
                    remnawave_user_id=42,
                    expected_expire_at=datetime.fromisoformat("2026-08-30T07:00:00Z"),
                )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "invalid_payload",
    [
        {"payment_id": "not-a-uuid"},
        {
            "payment_id": "550e8400-e29b-41d4-a716-446655440010",
            "reused": False,
            "notification_status": "sent",
        },
        {
            "payment_id": "550e8400-e29b-41d4-a716-446655440010",
            "pay_url": "https://pay.example.test/invoices/123",
            "reused": False,
            "notification_status": "queued",
        },
    ],
)
async def test_auto_renew_invoice_rejects_malformed_success_payload(mock_settings, invalid_payload: dict) -> None:
    mock_settings.backend_api_url = "https://backend.example.test/api/v1"
    mock_settings.backend_internal_secret.get_secret_value.return_value = "backend-internal-secret"

    with (
        patch("src.services.backend_api_client.get_settings", return_value=mock_settings),
        patch("src.services.backend_api_client.httpx.AsyncClient") as client_cls,
    ):
        response = MagicMock(status_code=200)
        response.json.return_value = invalid_payload
        http_client = AsyncMock()
        http_client.post.return_value = response
        client_cls.return_value = http_client

        async with BackendAPIClient() as backend:
            with pytest.raises(BackendAPIAutoRenewPermanentError):
                await backend.create_remnawave_auto_renew_invoice(
                    remnawave_user_id=42,
                    expected_expire_at=datetime.fromisoformat("2026-08-30T07:00:00Z"),
                )


@pytest.mark.asyncio
async def test_remnawave_identity_resolver_returns_strict_numeric_id_with_backend_audience(mock_settings) -> None:
    customer_id = "550e8400-e29b-41d4-a716-446655440010"
    mock_settings.backend_api_url = "https://backend.example.test/api/v1"
    mock_settings.backend_internal_secret.get_secret_value.return_value = "backend-internal-secret"

    with (
        patch("src.services.backend_api_client.get_settings", return_value=mock_settings),
        patch("src.services.backend_api_client.httpx.AsyncClient") as client_cls,
    ):
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {
            "customer_id": customer_id,
            "remnawave_user_id": 42,
            "reconciliation_state": "mapped",
        }
        http_client = AsyncMock()
        http_client.get.return_value = response
        client_cls.return_value = http_client

        async with BackendAPIClient() as backend:
            result = await backend.resolve_remnawave_user_id(customer_id)

    assert result == 42
    http_client.get.assert_awaited_once_with(
        f"internal/remnawave/users/by-customer/{customer_id}",
        headers={"X-Backend-Internal-Secret": "backend-internal-secret"},
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status_code", "payload"),
    [
        (409, {}),
        (
            200,
            {
                "customer_id": "550e8400-e29b-41d4-a716-446655440010",
                "remnawave_user_id": "legacy-uuid",
                "reconciliation_state": "mapped",
            },
        ),
        (
            200,
            {
                "customer_id": "550e8400-e29b-41d4-a716-446655440010",
                "remnawave_user_id": 42,
                "reconciliation_state": "pending",
            },
        ),
    ],
)
async def test_remnawave_identity_resolver_never_falls_back_to_uuid(
    mock_settings,
    status_code: int,
    payload: dict,
) -> None:
    customer_id = "550e8400-e29b-41d4-a716-446655440010"
    mock_settings.backend_api_url = "https://backend.example.test/api/v1"
    mock_settings.backend_internal_secret.get_secret_value.return_value = "backend-internal-secret"

    with (
        patch("src.services.backend_api_client.get_settings", return_value=mock_settings),
        patch("src.services.backend_api_client.httpx.AsyncClient") as client_cls,
    ):
        response = MagicMock(status_code=status_code)
        response.json.return_value = payload
        http_client = AsyncMock()
        http_client.get.return_value = response
        client_cls.return_value = http_client

        async with BackendAPIClient() as backend:
            with pytest.raises(BackendAPIError):
                await backend.resolve_remnawave_user_id(customer_id)


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
