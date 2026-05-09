"""S1-PAY-016 YooKassa readiness guardrails."""

from __future__ import annotations

import json
from pathlib import Path

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


def _load_yookassa_documentation_samples() -> list[Stage1ProviderEvidenceSample]:
    raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    samples = [parse_stage1_provider_evidence_sample(item) for item in raw["samples"]]
    return [sample for sample in samples if sample.provider is Stage1PaymentProvider.YOOKASSA]


def test_stage1_yookassa_documentation_only_samples_do_not_enable_paid_rail() -> None:
    samples = _load_yookassa_documentation_samples()

    validations = [validate_stage1_provider_evidence_sample(sample) for sample in samples]
    decision = decide_stage1_provider_enablement(Stage1PaymentProvider.YOOKASSA, samples)

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


def test_stage1_yookassa_succeeded_is_the_only_normal_paid_access_status() -> None:
    pending = resolve_stage1_provider_payment_status(Stage1PaymentProvider.YOOKASSA, "pending")
    waiting_for_capture = resolve_stage1_provider_payment_status(
        Stage1PaymentProvider.YOOKASSA,
        "waiting_for_capture",
    )
    payment_waiting_for_capture = resolve_stage1_provider_payment_status(
        Stage1PaymentProvider.YOOKASSA,
        "payment.waiting_for_capture",
    )
    succeeded = resolve_stage1_provider_payment_status(Stage1PaymentProvider.YOOKASSA, "succeeded")
    webhook_succeeded = resolve_stage1_provider_payment_status(Stage1PaymentProvider.YOOKASSA, "payment.succeeded")
    canceled = resolve_stage1_provider_payment_status(Stage1PaymentProvider.YOOKASSA, "payment.canceled")

    assert pending.payment_state is Stage1PaymentState.PENDING
    assert pending.final is False
    assert pending.automatic_paid_access_allowed is False

    assert waiting_for_capture.payment_state is Stage1PaymentState.PROCESSING
    assert waiting_for_capture.final is False
    assert waiting_for_capture.automatic_paid_access_allowed is False
    assert waiting_for_capture.manual_review_required is True
    assert waiting_for_capture.support_state is Stage1SupportState.SUPPORT_REVIEW

    assert payment_waiting_for_capture.payment_state is Stage1PaymentState.PROCESSING
    assert payment_waiting_for_capture.automatic_paid_access_allowed is False
    assert payment_waiting_for_capture.manual_review_required is True

    assert succeeded.payment_state is Stage1PaymentState.PAID
    assert succeeded.final is True
    assert succeeded.automatic_paid_access_allowed is True
    assert succeeded.manual_review_required is False

    assert webhook_succeeded.payment_state is Stage1PaymentState.PAID
    assert webhook_succeeded.final is True
    assert webhook_succeeded.automatic_paid_access_allowed is True
    assert webhook_succeeded.manual_review_required is False

    assert canceled.payment_state is Stage1PaymentState.CANCELLED
    assert canceled.final is True
    assert canceled.automatic_paid_access_allowed is False


def test_stage1_yookassa_refund_succeeded_requires_support_review_by_default() -> None:
    refunded = resolve_stage1_provider_payment_status(Stage1PaymentProvider.YOOKASSA, "refund.succeeded")

    assert refunded.payment_state is Stage1PaymentState.REFUNDED
    assert refunded.final is True
    assert refunded.automatic_paid_access_allowed is False
    assert refunded.manual_review_required is True
    assert refunded.support_state is Stage1SupportState.SUPPORT_REVIEW


def test_stage1_yookassa_webhook_requires_provider_status_recheck_before_side_effects() -> None:
    pending = verify_stage1_webhook_signature(Stage1PaymentProvider.YOOKASSA)
    confirmed = verify_stage1_webhook_signature(
        Stage1PaymentProvider.YOOKASSA,
        provider_recheck_confirmed=True,
    )

    assert pending.accepted is False
    assert pending.status is Stage1WebhookSignatureStatus.REQUIRES_PROVIDER_RECHECK
    assert pending.to_safe_dict()["provider_recheck_required"] is True

    assert confirmed.accepted is True
    assert confirmed.status is Stage1WebhookSignatureStatus.VALID
    assert confirmed.to_safe_dict()["provider_recheck_confirmed"] is True

    serialized = str(confirmed.to_safe_dict())
    assert "redacted-yookassa-payment" not in serialized
    assert "shop-secret" not in serialized


def test_stage1_yookassa_identity_supports_webhook_and_status_poll_shapes() -> None:
    webhook_identity = extract_stage1_webhook_identity(
        Stage1PaymentProvider.YOOKASSA,
        {
            "type": "notification",
            "event": "payment.succeeded",
            "notification_id": "redacted-notification",
            "object": {
                "id": "redacted-yookassa-payment",
                "status": "succeeded",
                "amount": {"value": "100.00", "currency": "RUB"},
                "metadata": {"order_id": "redacted-order"},
            },
        },
    )
    status_poll_identity = extract_stage1_webhook_identity(
        Stage1PaymentProvider.YOOKASSA,
        {
            "id": "redacted-yookassa-payment",
            "status": "succeeded",
            "amount": {"value": "100.00", "currency": "RUB"},
            "metadata": {"order_id": "redacted-order"},
        },
    )

    assert webhook_identity.normalized_status == "payment_succeeded"
    assert webhook_identity.event_type == "payment.succeeded"
    assert status_poll_identity.normalized_status == "succeeded"
    assert webhook_identity.provider_payment_id == status_poll_identity.provider_payment_id
    assert "redacted-yookassa-payment" not in webhook_identity.idempotency_key


def test_stage1_yookassa_duplicate_webhooks_do_not_repeat_side_effects() -> None:
    guard = Stage1InMemoryWebhookIdempotencyGuard()
    first_identity = extract_stage1_webhook_identity(
        Stage1PaymentProvider.YOOKASSA,
        {
            "type": "notification",
            "event": "payment.succeeded",
            "notification_id": "first-notification",
            "object": {"id": "redacted-yookassa-payment", "status": "succeeded"},
        },
    )
    second_identity = extract_stage1_webhook_identity(
        Stage1PaymentProvider.YOOKASSA,
        {
            "type": "notification",
            "event": "payment.succeeded",
            "notification_id": "provider-retry-with-new-id",
            "object": {"id": "redacted-yookassa-payment", "status": "succeeded"},
        },
    )

    first = guard.record(first_identity)
    second = guard.record(second_identity)

    assert first.result is Stage1WebhookIdempotencyResult.ACCEPTED_NEW
    assert first.side_effects_allowed == DEFAULT_STAGE1_WEBHOOK_SIDE_EFFECTS
    assert second.result is Stage1WebhookIdempotencyResult.ACCEPTED_ALREADY_APPLIED
    assert second.side_effects_allowed == ()
    assert set(second.side_effects_already_applied) == set(DEFAULT_STAGE1_WEBHOOK_SIDE_EFFECTS)


def test_stage1_yookassa_provider_enablement_requires_full_real_evidence_set() -> None:
    incomplete_samples = [
        _yookassa_sample(
            sample_id="yookassa-real-payment-succeeded-webhook",
            evidence_kind=Stage1ProviderEvidenceKind.CALLBACK_SAMPLE,
            provider_status="payment.succeeded",
            expected_payment_state=Stage1PaymentState.PAID,
            automatic_paid_access_allowed=True,
        ),
        _yookassa_sample(
            sample_id="yookassa-real-payment-canceled-webhook",
            evidence_kind=Stage1ProviderEvidenceKind.CALLBACK_SAMPLE,
            provider_status="payment.canceled",
            expected_payment_state=Stage1PaymentState.CANCELLED,
            automatic_paid_access_allowed=False,
        ),
        _yookassa_sample(
            sample_id="yookassa-real-status-poll",
            evidence_kind=Stage1ProviderEvidenceKind.STATUS_POLL_SAMPLE,
            provider_status="succeeded",
            expected_payment_state=Stage1PaymentState.PAID,
            automatic_paid_access_allowed=True,
        ),
        _yookassa_sample(
            sample_id="yookassa-real-provider-recheck",
            evidence_kind=Stage1ProviderEvidenceKind.SIGNATURE_VERIFICATION,
            provider_status="payment.succeeded",
            expected_payment_state=Stage1PaymentState.PAID,
            automatic_paid_access_allowed=True,
            payload_shape={"authenticity": "provider_status_recheck_or_ip_allowlist", "recheck": True},
        ),
    ]
    complete_samples = [
        *incomplete_samples,
        _yookassa_sample(
            sample_id="yookassa-real-refund-succeeded",
            evidence_kind=Stage1ProviderEvidenceKind.REFUND_SAMPLE,
            provider_status="refund.succeeded",
            expected_payment_state=Stage1PaymentState.REFUNDED,
            automatic_paid_access_allowed=False,
            payload_shape={"event": "refund.succeeded", "object": {"payment_id": "redacted-payment"}},
        ),
    ]

    incomplete = decide_stage1_provider_enablement(Stage1PaymentProvider.YOOKASSA, incomplete_samples)
    complete = decide_stage1_provider_enablement(Stage1PaymentProvider.YOOKASSA, complete_samples)

    assert incomplete.allowed is False
    assert "refund_or_reconciliation_evidence_missing" in incomplete.blockers
    assert complete.allowed is True
    assert complete.blockers == ()
    assert complete.provider_account_sample_count == 5


def _yookassa_sample(
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
        provider=Stage1PaymentProvider.YOOKASSA,
        evidence_kind=evidence_kind,
        environment=Stage1ProviderEvidenceEnvironment.SANDBOX,
        source=Stage1ProviderEvidenceSource.PROVIDER_ACCOUNT,
        captured_at="2026-05-07T00:00:00Z",
        official_source_url="https://yookassa.ru/developers/using-api/webhooks",
        tech_debt_id="TD-S1-PAY-011",
        provider_status=provider_status,
        expected_payment_state=expected_payment_state,
        automatic_paid_access_allowed=automatic_paid_access_allowed,
        payload_shape=payload_shape
        or {
            "type": "notification",
            "event": provider_status,
            "object": {
                "id": "redacted-payment",
                "status": provider_status.removeprefix("payment."),
                "amount": {"value": "100.00", "currency": "RUB"},
                "metadata": {"order_id": "redacted-order"},
            },
        },
    )
