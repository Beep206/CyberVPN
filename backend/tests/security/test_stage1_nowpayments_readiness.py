"""S1-PAY-014 NOWPayments readiness guardrails."""

from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path
from typing import Any

from src.presentation.api.shared.stage1_contract import Stage1PaymentState, Stage1SupportState
from src.presentation.api.shared.stage1_payment_mapping import (
    Stage1PaymentProvider,
    resolve_stage1_provider_payment_status,
)
from src.presentation.api.shared.stage1_provider_evidence import (
    Stage1ProviderEvidenceEnvironment,
    Stage1ProviderEvidenceKind,
    Stage1ProviderEvidenceSample,
    Stage1ProviderEvidenceSource,
    decide_stage1_provider_enablement,
    parse_stage1_provider_evidence_sample,
    validate_stage1_provider_evidence_sample,
)
from src.presentation.api.shared.stage1_webhook_idempotency import (
    DEFAULT_STAGE1_WEBHOOK_SIDE_EFFECTS,
    Stage1InMemoryWebhookIdempotencyGuard,
    Stage1WebhookIdempotencyResult,
    extract_stage1_webhook_identity,
)
from src.presentation.api.shared.stage1_webhook_signature import (
    Stage1WebhookSignatureStatus,
    verify_stage1_webhook_signature,
)

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "stage1_provider_evidence"
    / "provider_documentation_placeholders.json"
)


def _load_nowpayments_documentation_samples() -> list[Stage1ProviderEvidenceSample]:
    raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    samples = [parse_stage1_provider_evidence_sample(item) for item in raw["samples"]]
    return [sample for sample in samples if sample.provider is Stage1PaymentProvider.NOWPAYMENTS]


def _nowpayments_signature(secret: str, payload: dict[str, Any]) -> str:
    canonical = json.dumps(_sort_json(payload), ensure_ascii=False, separators=(",", ":"))
    return hmac.new(secret.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha512).hexdigest()


def _sort_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _sort_json(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_sort_json(item) for item in value]
    return value


def test_stage1_nowpayments_documentation_only_samples_do_not_enable_paid_rail() -> None:
    samples = _load_nowpayments_documentation_samples()

    validations = [validate_stage1_provider_evidence_sample(sample) for sample in samples]
    decision = decide_stage1_provider_enablement(Stage1PaymentProvider.NOWPAYMENTS, samples)

    assert samples
    assert all(validation.valid for validation in validations), {
        validation.sample_id: validation.errors for validation in validations if not validation.valid
    }
    assert decision.allowed is False
    assert decision.provider_account_sample_count == 0
    assert "real_provider_account_samples_missing" in decision.blockers
    assert "real_callback_sample_missing" in decision.blockers
    assert "signature_verification_evidence_missing" in decision.blockers
    assert "refund_or_reconciliation_evidence_missing" in decision.blockers


def test_stage1_nowpayments_finished_is_the_only_normal_paid_access_status() -> None:
    waiting = resolve_stage1_provider_payment_status(Stage1PaymentProvider.NOWPAYMENTS, "waiting")
    confirmed = resolve_stage1_provider_payment_status(Stage1PaymentProvider.NOWPAYMENTS, "confirmed")
    sending = resolve_stage1_provider_payment_status(Stage1PaymentProvider.NOWPAYMENTS, "sending")
    finished = resolve_stage1_provider_payment_status(Stage1PaymentProvider.NOWPAYMENTS, "finished")

    assert waiting.payment_state is Stage1PaymentState.PENDING
    assert waiting.final is False
    assert waiting.automatic_paid_access_allowed is False

    assert confirmed.payment_state is Stage1PaymentState.PENDING
    assert confirmed.final is False
    assert confirmed.automatic_paid_access_allowed is False

    assert sending.payment_state is Stage1PaymentState.PROCESSING
    assert sending.final is False
    assert sending.automatic_paid_access_allowed is False

    assert finished.payment_state is Stage1PaymentState.PAID
    assert finished.final is True
    assert finished.automatic_paid_access_allowed is True
    assert finished.manual_review_required is False


def test_stage1_nowpayments_partial_wrong_asset_and_refund_states_require_review() -> None:
    partial = resolve_stage1_provider_payment_status(Stage1PaymentProvider.NOWPAYMENTS, "partially_paid")
    wrong_asset = resolve_stage1_provider_payment_status(Stage1PaymentProvider.NOWPAYMENTS, "wrong_asset_confirmed")
    cancelled = resolve_stage1_provider_payment_status(Stage1PaymentProvider.NOWPAYMENTS, "cancelled")
    refunded = resolve_stage1_provider_payment_status(Stage1PaymentProvider.NOWPAYMENTS, "refunded")

    assert partial.payment_state is Stage1PaymentState.RECONCILIATION_REQUIRED
    assert partial.automatic_paid_access_allowed is False
    assert partial.manual_review_required is True
    assert partial.support_state is Stage1SupportState.SUPPORT_REVIEW

    assert wrong_asset.payment_state is Stage1PaymentState.RECONCILIATION_REQUIRED
    assert wrong_asset.automatic_paid_access_allowed is False
    assert wrong_asset.manual_review_required is True
    assert wrong_asset.support_state is Stage1SupportState.SUPPORT_REVIEW

    assert cancelled.payment_state is Stage1PaymentState.CANCELLED
    assert cancelled.automatic_paid_access_allowed is False
    assert cancelled.final is True

    assert refunded.payment_state is Stage1PaymentState.REFUNDED
    assert refunded.automatic_paid_access_allowed is False
    assert refunded.manual_review_required is True
    assert refunded.support_state is Stage1SupportState.SUPPORT_REVIEW


def test_stage1_nowpayments_ipn_requires_sorted_json_hmac_sha512_and_safe_output() -> None:
    secret = "redacted-nowpayments-ipn-secret"
    payload = {
        "payment_status": "finished",
        "payment_id": 123456,
        "order_id": "redacted-order",
        "nested": {"z": 1, "a": "first"},
    }
    signature = _nowpayments_signature(secret, payload)
    unsorted_body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

    valid = verify_stage1_webhook_signature(
        Stage1PaymentProvider.NOWPAYMENTS,
        body=unsorted_body,
        headers={"x-nowpayments-sig": signature},
        secret=secret,
    )
    invalid = verify_stage1_webhook_signature(
        Stage1PaymentProvider.NOWPAYMENTS,
        body=unsorted_body,
        headers={"x-nowpayments-sig": "00" * 64},
        secret=secret,
    )
    missing = verify_stage1_webhook_signature(
        Stage1PaymentProvider.NOWPAYMENTS,
        body=unsorted_body,
        headers={},
        secret=secret,
    )

    assert valid.accepted is True
    assert invalid.accepted is False
    assert invalid.status is Stage1WebhookSignatureStatus.INVALID
    assert missing.accepted is False
    assert missing.status is Stage1WebhookSignatureStatus.MISSING_SIGNATURE

    serialized = str(valid.to_safe_dict())
    assert secret not in serialized
    assert signature not in serialized


def test_stage1_nowpayments_identity_supports_ipn_and_status_poll_shapes() -> None:
    ipn_identity = extract_stage1_webhook_identity(
        Stage1PaymentProvider.NOWPAYMENTS,
        {
            "payment_id": 123456,
            "payment_status": "finished",
            "order_id": "redacted-order",
            "ipn_id": "redacted-ipn",
        },
    )
    status_poll_identity = extract_stage1_webhook_identity(
        Stage1PaymentProvider.NOWPAYMENTS,
        {
            "paymentId": 123456,
            "paymentStatus": "finished",
            "order_id": "redacted-order",
        },
    )

    assert ipn_identity.normalized_status == "finished"
    assert status_poll_identity.normalized_status == "finished"
    assert status_poll_identity.operation_key == ipn_identity.operation_key


def test_stage1_nowpayments_duplicate_ipn_does_not_repeat_side_effects() -> None:
    guard = Stage1InMemoryWebhookIdempotencyGuard()
    first_identity = extract_stage1_webhook_identity(
        Stage1PaymentProvider.NOWPAYMENTS,
        {
            "payment_id": 123456,
            "payment_status": "finished",
            "order_id": "redacted-order",
            "ipn_id": "first-ipn",
        },
    )
    second_identity = extract_stage1_webhook_identity(
        Stage1PaymentProvider.NOWPAYMENTS,
        {
            "payment_id": 123456,
            "payment_status": "finished",
            "order_id": "redacted-order",
            "ipn_id": "provider-retry-with-new-id",
        },
    )

    first = guard.record(first_identity)
    second = guard.record(second_identity)

    assert first.result is Stage1WebhookIdempotencyResult.ACCEPTED_NEW
    assert first.side_effects_allowed == DEFAULT_STAGE1_WEBHOOK_SIDE_EFFECTS
    assert second.result is Stage1WebhookIdempotencyResult.ACCEPTED_ALREADY_APPLIED
    assert second.side_effects_allowed == ()
    assert set(second.side_effects_already_applied) == set(DEFAULT_STAGE1_WEBHOOK_SIDE_EFFECTS)


def test_stage1_nowpayments_provider_enablement_requires_full_real_evidence_set() -> None:
    incomplete_samples = [
        _nowpayments_sample(
            sample_id="nowpayments-real-finished-ipn",
            evidence_kind=Stage1ProviderEvidenceKind.CALLBACK_SAMPLE,
            provider_status="finished",
            expected_payment_state=Stage1PaymentState.PAID,
            automatic_paid_access_allowed=True,
        ),
        _nowpayments_sample(
            sample_id="nowpayments-real-partial-ipn",
            evidence_kind=Stage1ProviderEvidenceKind.CALLBACK_SAMPLE,
            provider_status="partially_paid",
            expected_payment_state=Stage1PaymentState.RECONCILIATION_REQUIRED,
            automatic_paid_access_allowed=False,
        ),
        _nowpayments_sample(
            sample_id="nowpayments-real-status-poll",
            evidence_kind=Stage1ProviderEvidenceKind.STATUS_POLL_SAMPLE,
            provider_status="finished",
            expected_payment_state=Stage1PaymentState.PAID,
            automatic_paid_access_allowed=True,
        ),
        _nowpayments_sample(
            sample_id="nowpayments-real-hmac",
            evidence_kind=Stage1ProviderEvidenceKind.SIGNATURE_VERIFICATION,
            provider_status="finished",
            expected_payment_state=Stage1PaymentState.PAID,
            automatic_paid_access_allowed=True,
            payload_shape={"signature_location": "x-nowpayments-sig", "header_present": True},
        ),
    ]
    complete_samples = [
        *incomplete_samples,
        _nowpayments_sample(
            sample_id="nowpayments-real-reconciliation",
            evidence_kind=Stage1ProviderEvidenceKind.RECONCILIATION_SAMPLE,
            provider_status="wrong_asset_confirmed",
            expected_payment_state=Stage1PaymentState.RECONCILIATION_REQUIRED,
            automatic_paid_access_allowed=False,
            payload_shape={"payment_id": "redacted-payment", "payment_status": "wrong_asset_confirmed"},
        ),
    ]

    incomplete = decide_stage1_provider_enablement(Stage1PaymentProvider.NOWPAYMENTS, incomplete_samples)
    complete = decide_stage1_provider_enablement(Stage1PaymentProvider.NOWPAYMENTS, complete_samples)

    assert incomplete.allowed is False
    assert "refund_or_reconciliation_evidence_missing" in incomplete.blockers
    assert complete.allowed is True
    assert complete.blockers == ()
    assert complete.provider_account_sample_count == 5


def _nowpayments_sample(
    *,
    sample_id: str,
    evidence_kind: Stage1ProviderEvidenceKind,
    provider_status: str,
    expected_payment_state: Stage1PaymentState,
    automatic_paid_access_allowed: bool,
    payload_shape: dict[str, object] | None = None,
) -> Stage1ProviderEvidenceSample:
    return Stage1ProviderEvidenceSample(
        sample_id=sample_id,
        provider=Stage1PaymentProvider.NOWPAYMENTS,
        evidence_kind=evidence_kind,
        environment=Stage1ProviderEvidenceEnvironment.SANDBOX,
        source=Stage1ProviderEvidenceSource.PROVIDER_ACCOUNT,
        captured_at="2026-05-07T00:00:00Z",
        official_source_url="https://nowpayments.zendesk.com/hc/en-us/articles/18395434917149-Payment-statuses",
        tech_debt_id="TD-S1-PAY-003",
        provider_status=provider_status,
        expected_payment_state=expected_payment_state,
        automatic_paid_access_allowed=automatic_paid_access_allowed,
        payload_shape=payload_shape
        or {
            "payment_id": "redacted-payment",
            "payment_status": provider_status,
            "price_amount": "10.00",
            "price_currency": "USD",
            "pay_amount": "10.00",
            "pay_currency": "USDT",
            "order_id": "redacted-order",
        },
    )
