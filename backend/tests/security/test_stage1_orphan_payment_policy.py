"""S1-PAY-007 orphan payment policy checks."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.presentation.api.shared import (
    STAGE1_ORPHAN_ALERT_AFTER_MINUTES,
    STAGE1_ORPHAN_P0_AFTER_MINUTES,
    STAGE1_ORPHAN_P1_AFTER_MINUTES,
    Stage1OrphanPaymentAction,
    Stage1OrphanPaymentReason,
    Stage1OrphanPaymentSlaState,
    Stage1PaymentAccessSnapshot,
    Stage1WebhookSideEffect,
    evaluate_stage1_orphan_payment,
    summarize_stage1_orphan_payment_queue,
)
from src.presentation.api.shared.stage1_contract import (
    Stage1AccessState,
    Stage1PaymentState,
    Stage1ProvisioningState,
    Stage1SupportState,
)
from src.presentation.api.shared.stage1_payment_mapping import Stage1PaymentProvider

NOW = datetime(2026, 5, 4, 12, 0, tzinfo=UTC)


def _snapshot(**overrides: Any) -> Stage1PaymentAccessSnapshot:
    values = {
        "provider": Stage1PaymentProvider.CRYPTOBOT,
        "provider_payment_id": "provider-payment-raw-id",
        "payment_id": "internal-payment-raw-id",
        "detected_at": NOW - timedelta(minutes=5),
        "observed_at": NOW,
        "payment_state": Stage1PaymentState.PAID,
        "provisioning_state": Stage1ProvisioningState.PENDING,
        "user_found": True,
        "order_found": True,
        "amount_currency_match": True,
        "access_ready": False,
    }
    values.update(overrides)
    return Stage1PaymentAccessSnapshot(**values)


def test_stage1_paid_and_access_ready_does_not_require_manual_review() -> None:
    decision = evaluate_stage1_orphan_payment(
        _snapshot(
            access_ready=True,
            provisioning_state=Stage1ProvisioningState.READY,
        )
    )

    assert decision.reason == Stage1OrphanPaymentReason.NONE
    assert decision.sla_state == Stage1OrphanPaymentSlaState.OK
    assert decision.manual_review_required is False
    assert decision.support_escalation is False
    assert decision.launch_blocker is False
    assert decision.to_flow_status().access_state == Stage1AccessState.ACTIVE


@pytest.mark.parametrize(
    ("user_found", "order_found", "expected_reason"),
    [
        (False, True, Stage1OrphanPaymentReason.USER_NOT_FOUND),
        (True, False, Stage1OrphanPaymentReason.ORDER_NOT_FOUND),
    ],
)
def test_stage1_paid_without_user_or_order_becomes_orphan_review(
    user_found: bool,
    order_found: bool,
    expected_reason: Stage1OrphanPaymentReason,
) -> None:
    decision = evaluate_stage1_orphan_payment(
        _snapshot(
            user_found=user_found,
            order_found=order_found,
            detected_at=NOW - timedelta(minutes=20),
        )
    )

    assert decision.reason == expected_reason
    assert decision.payment_state == Stage1PaymentState.ORPHAN_REVIEW_REQUIRED
    assert decision.provisioning_state == Stage1ProvisioningState.NOT_REQUIRED
    assert decision.support_state == Stage1SupportState.SUPPORT_REVIEW
    assert decision.manual_review_required is True
    assert Stage1OrphanPaymentAction.CREATE_MANUAL_REVIEW_ITEM in decision.actions
    assert Stage1OrphanPaymentAction.DO_NOT_CREATE_ACCOUNT_SILENTLY in decision.actions
    assert Stage1OrphanPaymentAction.ALERT_SUPPORT_FINANCE in decision.actions


def test_stage1_paid_but_provisioning_failed_preserves_paid_and_queues_retry() -> None:
    decision = evaluate_stage1_orphan_payment(
        _snapshot(
            provisioning_state=Stage1ProvisioningState.FAILED,
            detected_at=NOW - timedelta(minutes=10),
        )
    )

    assert decision.reason == Stage1OrphanPaymentReason.PROVISIONING_FAILED
    assert decision.payment_state == Stage1PaymentState.PAID
    assert decision.provisioning_state == Stage1ProvisioningState.RETRYING
    assert decision.access_state == Stage1AccessState.PROVISIONING_PENDING
    assert Stage1OrphanPaymentAction.PRESERVE_PAID_STATE in decision.actions
    assert Stage1OrphanPaymentAction.QUEUE_PROVISIONING_RETRY in decision.actions


def test_stage1_paid_but_remnawave_unavailable_keeps_access_pending() -> None:
    decision = evaluate_stage1_orphan_payment(
        _snapshot(
            provisioning_state=Stage1ProvisioningState.REMNAWAVE_UNAVAILABLE,
            detected_at=NOW - timedelta(minutes=65),
        )
    )

    assert decision.reason == Stage1OrphanPaymentReason.REMNAWAVE_UNAVAILABLE
    assert decision.payment_state == Stage1PaymentState.PAID
    assert decision.provisioning_state == Stage1ProvisioningState.REMNAWAVE_UNAVAILABLE
    assert decision.sla_state == Stage1OrphanPaymentSlaState.P1_ESCALATION
    assert Stage1OrphanPaymentAction.P1_SUPPORT_OPS_ESCALATION in decision.actions


def test_stage1_amount_currency_mismatch_blocks_automatic_access() -> None:
    decision = evaluate_stage1_orphan_payment(
        _snapshot(
            amount_currency_match=False,
            detected_at=NOW - timedelta(minutes=15),
        )
    )

    assert decision.reason == Stage1OrphanPaymentReason.AMOUNT_CURRENCY_MISMATCH
    assert decision.payment_state == Stage1PaymentState.RECONCILIATION_REQUIRED
    assert decision.provisioning_state == Stage1ProvisioningState.RECONCILIATION_REQUIRED
    assert decision.access_state == Stage1AccessState.NO_ACCESS
    assert Stage1OrphanPaymentAction.BLOCK_AUTOMATIC_ACCESS in decision.actions


def test_stage1_provider_final_success_after_timeout_reopens_reconciliation() -> None:
    decision = evaluate_stage1_orphan_payment(
        _snapshot(
            provider_final_success_after_timeout=True,
            detected_at=NOW - timedelta(minutes=30),
        )
    )

    assert decision.reason == Stage1OrphanPaymentReason.PROVIDER_SUCCESS_AFTER_TIMEOUT
    assert decision.payment_state == Stage1PaymentState.PAID
    assert decision.provisioning_state == Stage1ProvisioningState.RECONCILIATION_REQUIRED
    assert Stage1OrphanPaymentAction.REOPEN_RECONCILIATION in decision.actions


def test_stage1_user_reported_debit_with_provider_pending_creates_support_ticket() -> None:
    decision = evaluate_stage1_orphan_payment(
        _snapshot(
            payment_state=Stage1PaymentState.PENDING,
            user_reported_debit_provider_pending=True,
        )
    )

    assert decision.reason == Stage1OrphanPaymentReason.USER_REPORTED_DEBIT_PROVIDER_PENDING
    assert decision.payment_state == Stage1PaymentState.PENDING
    assert decision.provisioning_state == Stage1ProvisioningState.NOT_REQUIRED
    assert Stage1OrphanPaymentAction.CREATE_SUPPORT_TICKET in decision.actions
    assert Stage1OrphanPaymentAction.RECONCILE_PROVIDER_DASHBOARD in decision.actions


@pytest.mark.parametrize(
    ("age_minutes", "expected_sla", "expected_action"),
    [
        (STAGE1_ORPHAN_ALERT_AFTER_MINUTES - 1, Stage1OrphanPaymentSlaState.MANUAL_REVIEW, None),
        (
            STAGE1_ORPHAN_ALERT_AFTER_MINUTES,
            Stage1OrphanPaymentSlaState.ALERT_15M,
            Stage1OrphanPaymentAction.SEND_PAID_WITHOUT_ACCESS_ALERT,
        ),
        (
            STAGE1_ORPHAN_P1_AFTER_MINUTES,
            Stage1OrphanPaymentSlaState.P1_ESCALATION,
            Stage1OrphanPaymentAction.P1_SUPPORT_OPS_ESCALATION,
        ),
        (
            STAGE1_ORPHAN_P0_AFTER_MINUTES,
            Stage1OrphanPaymentSlaState.P0_BLOCKER,
            Stage1OrphanPaymentAction.P0_LAUNCH_BLOCKER,
        ),
    ],
)
def test_stage1_orphan_payment_sla_thresholds_are_explicit(
    age_minutes: int,
    expected_sla: Stage1OrphanPaymentSlaState,
    expected_action: Stage1OrphanPaymentAction | None,
) -> None:
    decision = evaluate_stage1_orphan_payment(
        _snapshot(
            detected_at=NOW - timedelta(minutes=age_minutes),
            observed_at=NOW,
        )
    )

    assert decision.sla_state == expected_sla
    assert decision.launch_blocker is (expected_sla == Stage1OrphanPaymentSlaState.P0_BLOCKER)
    if expected_action is not None:
        assert expected_action in decision.actions


def test_stage1_orphan_payment_serialization_redacts_raw_payment_ids() -> None:
    decision = evaluate_stage1_orphan_payment(
        _snapshot(
            detected_at=NOW - timedelta(hours=25),
        )
    )
    payload = decision.to_api_dict()
    serialized = str(payload)

    assert payload["safe_reference"].startswith("s1:payment-review:")
    assert "provider-payment-raw-id" not in serialized
    assert "internal-payment-raw-id" not in serialized
    assert payload["launch_blocker"] is True
    assert payload["error_code"] == "provisioning_reconciliation_required"


@pytest.mark.asyncio
async def test_stage1_orphan_payment_policy_serializes_through_asgi_dashboard() -> None:
    app = FastAPI()

    @app.get("/s1/payments/orphan-dashboard")
    async def orphan_dashboard() -> dict[str, Any]:
        decisions = [
            evaluate_stage1_orphan_payment(
                _snapshot(
                    provider=Stage1PaymentProvider.NOWPAYMENTS,
                    provider_payment_id="nowpayments-raw-1",
                    detected_at=NOW - timedelta(hours=25),
                    observed_at=NOW,
                )
            ),
            evaluate_stage1_orphan_payment(
                _snapshot(
                    provider=Stage1PaymentProvider.PAYRAM,
                    provider_payment_id="payram-raw-2",
                    detected_at=NOW - timedelta(minutes=20),
                    observed_at=NOW,
                )
            ),
            evaluate_stage1_orphan_payment(
                _snapshot(
                    provider=Stage1PaymentProvider.CRYPTOBOT,
                    provider_payment_id="cryptobot-raw-3",
                    access_ready=True,
                    provisioning_state=Stage1ProvisioningState.READY,
                )
            ),
        ]
        summary = summarize_stage1_orphan_payment_queue(decisions)
        return {
            "summary": summary.to_api_dict(),
            "items": [decision.to_api_dict() for decision in decisions if decision.manual_review_required],
        }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://backend") as client:
        response = await client.get("/s1/payments/orphan-dashboard")

    assert response.status_code == 200
    body = response.json()
    assert body["summary"] == {
        "total_items": 3,
        "manual_review_items": 2,
        "alert_15m_items": 2,
        "p1_escalation_items": 1,
        "p0_blocker_items": 1,
        "max_age_minutes": 1500,
        "launch_blocked": True,
    }
    assert len(body["items"]) == 2
    assert "nowpayments-raw-1" not in str(body)
    assert "payram-raw-2" not in str(body)


def test_stage1_orphan_policy_keeps_support_escalation_separate_from_webhook_idempotency() -> None:
    assert Stage1WebhookSideEffect.SUPPORT_ESCALATION.value == "support_escalation"
