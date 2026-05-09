"""S1-PAY-004 provider status mapping checks."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.presentation.api.shared.stage1_contract import Stage1PaymentState, Stage1SupportState
from src.presentation.api.shared.stage1_payment_mapping import (
    STAGE1_PROVIDER_STATUS_SOURCES,
    Stage1PaymentProvider,
    normalize_provider_status,
    resolve_stage1_provider_payment_status,
    stage1_provider_status_values,
)


@pytest.mark.parametrize(
    ("raw_status", "expected"),
    [
        ("FILLED", "filled"),
        (" payment.succeeded ", "payment_succeeded"),
        ("PARTIALLY-FILLED", "partially_filled"),
        ("wrong asset confirmed", "wrong_asset_confirmed"),
    ],
)
def test_stage1_provider_status_normalization(raw_status: str, expected: str) -> None:
    assert normalize_provider_status(raw_status) == expected


def test_stage1_payment_provider_sources_cover_owner_approved_set() -> None:
    assert set(STAGE1_PROVIDER_STATUS_SOURCES) == set(Stage1PaymentProvider)
    for source in STAGE1_PROVIDER_STATUS_SOURCES.values():
        assert source.url.startswith("https://")
        assert source.retrieved_on == "2026-05-08"


@pytest.mark.parametrize(
    ("provider", "expected_statuses"),
    [
        (
            Stage1PaymentProvider.PAYRAM,
            {"open", "filled", "over_filled", "partially_filled", "cancelled", "canceled"},
        ),
        (
            Stage1PaymentProvider.NOWPAYMENTS,
            {
                "waiting",
                "confirming",
                "confirmed",
                "sending",
                "finished",
                "partially_paid",
                "wrong_asset_confirmed",
                "failed",
                "expired",
                "cancelled",
                "canceled",
                "refunded",
            },
        ),
        (Stage1PaymentProvider.CRYPTOBOT, {"active", "paid", "invoice_paid", "expired"}),
        (
            Stage1PaymentProvider.TELEGRAM_STARS,
            {"invoice_sent", "pre_checkout_query", "successful_payment", "payment_timeout", "refund_succeeded"},
        ),
        (Stage1PaymentProvider.DIGISELLER, {"wait", "paid", "canceled", "refunded", "error"}),
        (
            Stage1PaymentProvider.YOOKASSA,
            {
                "pending",
                "waiting_for_capture",
                "payment_waiting_for_capture",
                "succeeded",
                "payment_succeeded",
                "canceled",
                "payment_canceled",
                "refund_succeeded",
            },
        ),
    ],
)
def test_stage1_provider_status_maps_cover_documented_statuses(
    provider: Stage1PaymentProvider,
    expected_statuses: set[str],
) -> None:
    assert stage1_provider_status_values(provider) == expected_statuses


@pytest.mark.parametrize(
    ("provider", "raw_status"),
    [
        (Stage1PaymentProvider.PAYRAM, "FILLED"),
        (Stage1PaymentProvider.NOWPAYMENTS, "finished"),
        (Stage1PaymentProvider.CRYPTOBOT, "paid"),
        (Stage1PaymentProvider.CRYPTOBOT, "invoice_paid"),
        (Stage1PaymentProvider.TELEGRAM_STARS, "successful_payment"),
        (Stage1PaymentProvider.DIGISELLER, "paid"),
        (Stage1PaymentProvider.YOOKASSA, "succeeded"),
        (Stage1PaymentProvider.YOOKASSA, "payment.succeeded"),
    ],
)
def test_stage1_only_provider_proven_paid_statuses_allow_paid_access(
    provider: Stage1PaymentProvider,
    raw_status: str,
) -> None:
    decision = resolve_stage1_provider_payment_status(provider, raw_status)

    assert decision.payment_state == Stage1PaymentState.PAID
    assert decision.final is True
    assert decision.automatic_paid_access_allowed is True
    assert decision.manual_review_required is False


@pytest.mark.parametrize(
    ("provider", "raw_status", "expected_state"),
    [
        (Stage1PaymentProvider.PAYRAM, "OPEN", Stage1PaymentState.PENDING),
        (Stage1PaymentProvider.PAYRAM, "PARTIALLY_FILLED", Stage1PaymentState.RECONCILIATION_REQUIRED),
        (Stage1PaymentProvider.NOWPAYMENTS, "confirmed", Stage1PaymentState.PENDING),
        (Stage1PaymentProvider.NOWPAYMENTS, "partially_paid", Stage1PaymentState.RECONCILIATION_REQUIRED),
        (Stage1PaymentProvider.NOWPAYMENTS, "wrong_asset_confirmed", Stage1PaymentState.RECONCILIATION_REQUIRED),
        (Stage1PaymentProvider.CRYPTOBOT, "active", Stage1PaymentState.PENDING),
        (Stage1PaymentProvider.TELEGRAM_STARS, "pre_checkout_query", Stage1PaymentState.PROCESSING),
        (Stage1PaymentProvider.DIGISELLER, "wait", Stage1PaymentState.PENDING),
        (Stage1PaymentProvider.YOOKASSA, "waiting_for_capture", Stage1PaymentState.PROCESSING),
        (Stage1PaymentProvider.YOOKASSA, "payment.waiting_for_capture", Stage1PaymentState.PROCESSING),
        (Stage1PaymentProvider.YOOKASSA, "refund.succeeded", Stage1PaymentState.REFUNDED),
    ],
)
def test_stage1_non_paid_statuses_do_not_allow_paid_access(
    provider: Stage1PaymentProvider,
    raw_status: str,
    expected_state: Stage1PaymentState,
) -> None:
    decision = resolve_stage1_provider_payment_status(provider, raw_status)

    assert decision.payment_state == expected_state
    assert decision.automatic_paid_access_allowed is False


def test_stage1_payram_overfilled_is_blocked_by_default_even_when_final() -> None:
    decision = resolve_stage1_provider_payment_status(
        Stage1PaymentProvider.PAYRAM,
        "OVER_FILLED",
        amount_expected="10.00",
        amount_received="12.00",
    )

    assert decision.final is True
    assert decision.payment_state == Stage1PaymentState.RECONCILIATION_REQUIRED
    assert decision.automatic_paid_access_allowed is False
    assert decision.manual_review_required is True
    assert decision.support_state == Stage1SupportState.SUPPORT_REVIEW


def test_stage1_payram_overfilled_can_be_explicitly_accepted_with_amount_evidence() -> None:
    decision = resolve_stage1_provider_payment_status(
        Stage1PaymentProvider.PAYRAM,
        "OVER_FILLED",
        amount_expected="10.00",
        amount_received="12.00",
        allow_overpaid_auto_access=True,
    )

    assert decision.payment_state == Stage1PaymentState.PAID
    assert decision.automatic_paid_access_allowed is True
    assert decision.manual_review_required is True
    assert decision.support_state == Stage1SupportState.SUPPORT_REVIEW


def test_stage1_payram_overfilled_policy_still_requires_valid_amount_evidence() -> None:
    decision = resolve_stage1_provider_payment_status(
        Stage1PaymentProvider.PAYRAM,
        "OVER_FILLED",
        amount_expected="10.00",
        amount_received="not-a-decimal",
        allow_overpaid_auto_access=True,
    )

    assert decision.payment_state == Stage1PaymentState.RECONCILIATION_REQUIRED
    assert decision.automatic_paid_access_allowed is False


@pytest.mark.parametrize(
    ("provider", "raw_status"),
    [
        (Stage1PaymentProvider.PAYRAM, "FUTURE_STATUS"),
        (Stage1PaymentProvider.NOWPAYMENTS, "settled_but_new"),
        (Stage1PaymentProvider.CRYPTOBOT, "confirmed"),
        (Stage1PaymentProvider.TELEGRAM_STARS, "chargeback"),
        (Stage1PaymentProvider.DIGISELLER, "pending_review"),
        (Stage1PaymentProvider.YOOKASSA, "refunded"),
    ],
)
def test_stage1_unknown_provider_statuses_require_ops_reconciliation(
    provider: Stage1PaymentProvider,
    raw_status: str,
) -> None:
    decision = resolve_stage1_provider_payment_status(provider, raw_status)

    assert decision.payment_state == Stage1PaymentState.RECONCILIATION_REQUIRED
    assert decision.final is False
    assert decision.automatic_paid_access_allowed is False
    assert decision.manual_review_required is True
    assert decision.support_state == Stage1SupportState.OPS_ESCALATION


@pytest.mark.asyncio
async def test_stage1_provider_mapping_serializes_for_payment_status_api() -> None:
    app = FastAPI()

    @app.get("/s1/payments/{provider}/{status}")
    async def payment_status(provider: str, status: str) -> dict[str, str | bool]:
        decision = resolve_stage1_provider_payment_status(provider, status)
        return decision.to_api_dict()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://backend") as client:
        paid_response = await client.get("/s1/payments/nowpayments/finished")
        review_response = await client.get("/s1/payments/payram/PARTIALLY_FILLED")

    assert paid_response.status_code == 200
    assert paid_response.json() == {
        "provider": "nowpayments",
        "provider_status": "finished",
        "normalized_status": "finished",
        "payment_state": "paid",
        "final": True,
        "automatic_paid_access_allowed": True,
        "manual_review_required": False,
        "support_state": "none",
        "behavior": "Verify IPN signature, amount and currency; then paid access may be provisioned.",
        "evidence_level": "official_docs",
    }
    assert review_response.status_code == 200
    assert review_response.json()["payment_state"] == "reconciliation_required"
    assert review_response.json()["automatic_paid_access_allowed"] is False
    assert review_response.json()["support_state"] == "support_review"
