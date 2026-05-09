"""S1-PAY-006 payment webhook idempotency checks."""

from __future__ import annotations

from collections import Counter
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.presentation.api.shared import Stage1WebhookSideEffect
from src.presentation.api.shared.stage1_payment_mapping import Stage1PaymentProvider
from src.presentation.api.shared.stage1_webhook_idempotency import (
    DEFAULT_STAGE1_WEBHOOK_SIDE_EFFECTS,
    Stage1InMemoryWebhookIdempotencyGuard,
    Stage1WebhookIdempotencyResult,
    extract_stage1_webhook_identity,
)

PROVIDER_FIXTURES: dict[Stage1PaymentProvider, dict[str, Any]] = {
    Stage1PaymentProvider.PAYRAM: {
        "referenceID": "payram-ref-1",
        "payment_state": "FILLED",
        "event_id": "payram-event-1",
    },
    Stage1PaymentProvider.NOWPAYMENTS: {
        "payment_id": 123456,
        "payment_status": "finished",
        "order_id": "order-now-1",
        "ipn_id": "now-ipn-1",
    },
    Stage1PaymentProvider.CRYPTOBOT: {
        "update_id": 777,
        "update_type": "invoice_paid",
        "payload": {
            "invoice_id": 999999,
            "status": "paid",
            "hash": "invoice-hash-1",
        },
    },
    Stage1PaymentProvider.TELEGRAM_STARS: {
        "update_id": 444,
        "message": {
            "message_id": 55,
            "successful_payment": {
                "currency": "XTR",
                "telegram_payment_charge_id": "tg-stars-charge-1",
                "provider_payment_charge_id": "",
            },
        },
    },
    Stage1PaymentProvider.DIGISELLER: {
        "invoice_id": "digiseller-invoice-1",
        "status": "paid",
        "notification_id": "digiseller-notice-1",
    },
    Stage1PaymentProvider.YOOKASSA: {
        "type": "notification",
        "event": "payment.succeeded",
        "object": {
            "id": "22e18a2f-000f-5000-a000-1db6312b7767",
            "status": "succeeded",
            "paid": True,
        },
    },
}


@pytest.mark.parametrize(
    ("provider", "expected_status"),
    [
        (Stage1PaymentProvider.PAYRAM, "filled"),
        (Stage1PaymentProvider.NOWPAYMENTS, "finished"),
        (Stage1PaymentProvider.CRYPTOBOT, "invoice_paid"),
        (Stage1PaymentProvider.TELEGRAM_STARS, "successful_payment"),
        (Stage1PaymentProvider.DIGISELLER, "paid"),
        (Stage1PaymentProvider.YOOKASSA, "payment_succeeded"),
    ],
)
def test_stage1_extracts_webhook_identity_from_provider_fixtures(
    provider: Stage1PaymentProvider,
    expected_status: str,
) -> None:
    identity = extract_stage1_webhook_identity(provider, PROVIDER_FIXTURES[provider])

    assert identity.provider == provider
    assert identity.normalized_status == expected_status
    assert identity.idempotency_key.startswith("s1:webhook:event:")
    assert identity.operation_key.startswith("s1:webhook:operation:")
    assert identity.idempotency_key != identity.operation_key


def test_stage1_webhook_idempotency_key_is_stable_without_payload_order() -> None:
    identity = extract_stage1_webhook_identity(
        Stage1PaymentProvider.NOWPAYMENTS,
        {
            "ipn_id": "now-ipn-1",
            "order_id": "order-now-1",
            "payment_status": "finished",
            "payment_id": 123456,
        },
    )
    same_identity = extract_stage1_webhook_identity(
        "nowpayments",
        {
            "payment_id": 123456,
            "payment_status": "finished",
            "order_id": "order-now-1",
            "ipn_id": "now-ipn-1",
        },
    )

    assert same_identity.idempotency_key == identity.idempotency_key
    assert same_identity.operation_key == identity.operation_key


def test_stage1_webhook_identity_ignores_unknown_secret_like_payload_fields() -> None:
    clean_identity = extract_stage1_webhook_identity(
        Stage1PaymentProvider.CRYPTOBOT,
        PROVIDER_FIXTURES[Stage1PaymentProvider.CRYPTOBOT],
    )
    noisy_payload = {
        **PROVIDER_FIXTURES[Stage1PaymentProvider.CRYPTOBOT],
        "crypto-pay-api-signature": "not-used-by-idempotency",
        "password": "not-used-by-idempotency",
        "token": "not-used-by-idempotency",
        "secret": "not-used-by-idempotency",
    }
    noisy_identity = extract_stage1_webhook_identity(Stage1PaymentProvider.CRYPTOBOT, noisy_payload)

    assert noisy_identity.idempotency_key == clean_identity.idempotency_key
    assert noisy_identity.operation_key == clean_identity.operation_key

    decision = Stage1InMemoryWebhookIdempotencyGuard().record(noisy_identity)
    serialized = str(decision.to_api_dict()).lower()
    assert "not-used-by-idempotency" not in serialized
    assert "password" not in serialized
    assert "token" not in serialized
    assert "secret" not in serialized
    assert "signature" not in serialized


def test_stage1_duplicate_webhook_allows_no_second_side_effects() -> None:
    guard = Stage1InMemoryWebhookIdempotencyGuard()
    identity = extract_stage1_webhook_identity(
        Stage1PaymentProvider.CRYPTOBOT,
        PROVIDER_FIXTURES[Stage1PaymentProvider.CRYPTOBOT],
    )

    first = guard.record(identity)
    second = guard.record(identity)

    assert first.result == Stage1WebhookIdempotencyResult.ACCEPTED_NEW
    assert first.side_effects_allowed == DEFAULT_STAGE1_WEBHOOK_SIDE_EFFECTS
    assert second.result == Stage1WebhookIdempotencyResult.DUPLICATE_ACCEPTED
    assert second.duplicate is True
    assert second.side_effects_allowed == ()
    assert set(second.side_effects_already_applied) == set(DEFAULT_STAGE1_WEBHOOK_SIDE_EFFECTS)


def test_stage1_new_event_same_payment_status_does_not_repeat_side_effects() -> None:
    guard = Stage1InMemoryWebhookIdempotencyGuard()
    first_identity = extract_stage1_webhook_identity(
        Stage1PaymentProvider.CRYPTOBOT,
        PROVIDER_FIXTURES[Stage1PaymentProvider.CRYPTOBOT],
    )
    retry_with_different_event_id = {
        **PROVIDER_FIXTURES[Stage1PaymentProvider.CRYPTOBOT],
        "update_id": 778,
    }
    second_identity = extract_stage1_webhook_identity(Stage1PaymentProvider.CRYPTOBOT, retry_with_different_event_id)

    first = guard.record(first_identity)
    second = guard.record(second_identity)

    assert first.result == Stage1WebhookIdempotencyResult.ACCEPTED_NEW
    assert second.result == Stage1WebhookIdempotencyResult.ACCEPTED_ALREADY_APPLIED
    assert second.duplicate is False
    assert second.side_effects_allowed == ()
    assert set(second.side_effects_already_applied) == set(DEFAULT_STAGE1_WEBHOOK_SIDE_EFFECTS)


@pytest.mark.asyncio
async def test_stage1_webhook_idempotency_serializes_through_asgi_feature_route() -> None:
    app = FastAPI()
    guard = Stage1InMemoryWebhookIdempotencyGuard()
    counters: Counter[str] = Counter()

    @app.post("/s1/webhooks/{provider}")
    async def provider_webhook(provider: str, payload: dict[str, Any]) -> dict[str, Any]:
        identity = extract_stage1_webhook_identity(provider, payload)
        decision = guard.record(identity)
        for side_effect in decision.side_effects_allowed:
            counters[side_effect.value] += 1
        return {
            **decision.to_api_dict(),
            "counters": dict(counters),
        }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://backend") as client:
        first = await client.post(
            "/s1/webhooks/cryptobot",
            json=PROVIDER_FIXTURES[Stage1PaymentProvider.CRYPTOBOT],
        )
        second = await client.post(
            "/s1/webhooks/cryptobot",
            json=PROVIDER_FIXTURES[Stage1PaymentProvider.CRYPTOBOT],
        )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["result"] == "accepted_new"
    assert first.json()["side_effects_allowed"] == [effect.value for effect in DEFAULT_STAGE1_WEBHOOK_SIDE_EFFECTS]
    assert first.json()["counters"] == {effect.value: 1 for effect in DEFAULT_STAGE1_WEBHOOK_SIDE_EFFECTS}
    assert second.json()["result"] == "duplicate_accepted"
    assert second.json()["side_effects_allowed"] == []
    assert second.json()["counters"] == {effect.value: 1 for effect in DEFAULT_STAGE1_WEBHOOK_SIDE_EFFECTS}


def test_stage1_missing_payment_identity_is_rejected_without_echoing_payload_values() -> None:
    with pytest.raises(ValueError) as exc_info:
        extract_stage1_webhook_identity(
            Stage1PaymentProvider.CRYPTOBOT,
            {
                "update_type": "invoice_paid",
                "payload": {"status": "paid", "hash": "sensitive-provider-hash"},
            },
        )

    message = str(exc_info.value)
    assert "Missing provider_payment_id" in message
    assert "sensitive-provider-hash" not in message


def test_stage1_shared_package_exports_webhook_idempotency_contract() -> None:
    assert Stage1WebhookSideEffect.PROVISIONING_JOB.value == "provisioning_job"
