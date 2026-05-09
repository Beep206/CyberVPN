"""S1-PAY-015 Digiseller readiness guardrails."""

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

DIGISELLER_TEST_UNSIGNED_FIELDS = frozenset(
    {
        "signature",
        "error",
        "integrator",
        "amount_out",
        "currency_out",
        "description",
        "lang",
        "email",
        "return_url",
    }
)


def _load_digiseller_documentation_samples() -> list[Stage1ProviderEvidenceSample]:
    raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    samples = [parse_stage1_provider_evidence_sample(item) for item in raw["samples"]]
    return [sample for sample in samples if sample.provider is Stage1PaymentProvider.DIGISELLER]


def _digiseller_signature(secret: str, payload: dict[str, Any]) -> str:
    material = "".join(
        f"{key}:{payload[key]};"
        for key in sorted(payload)
        if key not in DIGISELLER_TEST_UNSIGNED_FIELDS and payload[key] not in (None, "")
    )
    return hmac.new(secret.encode("utf-8"), material.encode("utf-8"), hashlib.sha256).hexdigest()


def test_stage1_digiseller_documentation_only_samples_do_not_enable_paid_rail() -> None:
    samples = _load_digiseller_documentation_samples()

    validations = [validate_stage1_provider_evidence_sample(sample) for sample in samples]
    decision = decide_stage1_provider_enablement(Stage1PaymentProvider.DIGISELLER, samples)

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


def test_stage1_digiseller_paid_is_the_only_normal_paid_access_status() -> None:
    waiting = resolve_stage1_provider_payment_status(Stage1PaymentProvider.DIGISELLER, "wait")
    paid = resolve_stage1_provider_payment_status(Stage1PaymentProvider.DIGISELLER, "paid")
    canceled = resolve_stage1_provider_payment_status(Stage1PaymentProvider.DIGISELLER, "canceled")
    failed = resolve_stage1_provider_payment_status(Stage1PaymentProvider.DIGISELLER, "error")

    assert waiting.payment_state is Stage1PaymentState.PENDING
    assert waiting.final is False
    assert waiting.automatic_paid_access_allowed is False

    assert paid.payment_state is Stage1PaymentState.PAID
    assert paid.final is True
    assert paid.automatic_paid_access_allowed is True
    assert paid.manual_review_required is False

    assert canceled.payment_state is Stage1PaymentState.CANCELLED
    assert canceled.final is True
    assert canceled.automatic_paid_access_allowed is False

    assert failed.payment_state is Stage1PaymentState.FAILED
    assert failed.final is True
    assert failed.automatic_paid_access_allowed is False


def test_stage1_digiseller_refunded_requires_support_review_by_default() -> None:
    refunded = resolve_stage1_provider_payment_status(Stage1PaymentProvider.DIGISELLER, "refunded")

    assert refunded.payment_state is Stage1PaymentState.REFUNDED
    assert refunded.final is True
    assert refunded.automatic_paid_access_allowed is False
    assert refunded.manual_review_required is True
    assert refunded.support_state is Stage1SupportState.SUPPORT_REVIEW


def test_stage1_digiseller_callback_requires_sorted_hmac_sha256_and_safe_output() -> None:
    secret = "redacted-digiseller-signing-key"
    payload = {
        "invoice_id": "redacted-invoice",
        "amount": "10.00",
        "currency": "USD",
        "status": "paid",
        "description": "ignored-description",
        "email": "buyer@example.invalid",
    }
    signature = _digiseller_signature(secret, payload)

    valid = verify_stage1_webhook_signature(
        Stage1PaymentProvider.DIGISELLER,
        payload={**payload, "signature": signature},
        secret=secret,
    )
    invalid = verify_stage1_webhook_signature(
        Stage1PaymentProvider.DIGISELLER,
        payload={**payload, "status": "wait", "signature": signature},
        secret=secret,
    )
    missing = verify_stage1_webhook_signature(
        Stage1PaymentProvider.DIGISELLER,
        payload=payload,
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
    assert "redacted-invoice" not in serialized


def test_stage1_digiseller_identity_supports_callback_and_status_poll_shapes() -> None:
    callback_identity = extract_stage1_webhook_identity(
        Stage1PaymentProvider.DIGISELLER,
        {
            "invoice_id": "redacted-digiseller-invoice",
            "amount": "10.00",
            "currency": "USD",
            "status": "paid",
            "notification_id": "redacted-notification",
        },
    )
    status_poll_identity = extract_stage1_webhook_identity(
        Stage1PaymentProvider.DIGISELLER,
        {
            "inv": "redacted-digiseller-invoice",
            "payment_status": "paid",
            "amount": "10.00",
            "currency": "USD",
        },
    )

    assert callback_identity.normalized_status == "paid"
    assert status_poll_identity.normalized_status == "paid"
    assert status_poll_identity.operation_key == callback_identity.operation_key


def test_stage1_digiseller_duplicate_callbacks_do_not_repeat_side_effects() -> None:
    guard = Stage1InMemoryWebhookIdempotencyGuard()
    first_identity = extract_stage1_webhook_identity(
        Stage1PaymentProvider.DIGISELLER,
        {
            "invoice_id": "redacted-digiseller-invoice",
            "status": "paid",
            "notification_id": "first-callback",
        },
    )
    second_identity = extract_stage1_webhook_identity(
        Stage1PaymentProvider.DIGISELLER,
        {
            "invoice_id": "redacted-digiseller-invoice",
            "status": "paid",
            "notification_id": "provider-retry-with-new-id",
        },
    )

    first = guard.record(first_identity)
    second = guard.record(second_identity)

    assert first.result is Stage1WebhookIdempotencyResult.ACCEPTED_NEW
    assert first.side_effects_allowed == DEFAULT_STAGE1_WEBHOOK_SIDE_EFFECTS
    assert second.result is Stage1WebhookIdempotencyResult.ACCEPTED_ALREADY_APPLIED
    assert second.side_effects_allowed == ()
    assert set(second.side_effects_already_applied) == set(DEFAULT_STAGE1_WEBHOOK_SIDE_EFFECTS)


def test_stage1_digiseller_provider_enablement_requires_full_real_evidence_set() -> None:
    incomplete_samples = [
        _digiseller_sample(
            sample_id="digiseller-real-paid-callback",
            evidence_kind=Stage1ProviderEvidenceKind.CALLBACK_SAMPLE,
            provider_status="paid",
            expected_payment_state=Stage1PaymentState.PAID,
            automatic_paid_access_allowed=True,
        ),
        _digiseller_sample(
            sample_id="digiseller-real-wait-callback",
            evidence_kind=Stage1ProviderEvidenceKind.CALLBACK_SAMPLE,
            provider_status="wait",
            expected_payment_state=Stage1PaymentState.PENDING,
            automatic_paid_access_allowed=False,
        ),
        _digiseller_sample(
            sample_id="digiseller-real-status-poll",
            evidence_kind=Stage1ProviderEvidenceKind.STATUS_POLL_SAMPLE,
            provider_status="paid",
            expected_payment_state=Stage1PaymentState.PAID,
            automatic_paid_access_allowed=True,
        ),
        _digiseller_sample(
            sample_id="digiseller-real-hmac",
            evidence_kind=Stage1ProviderEvidenceKind.SIGNATURE_VERIFICATION,
            provider_status="paid",
            expected_payment_state=Stage1PaymentState.PAID,
            automatic_paid_access_allowed=True,
            payload_shape={"signature_location": "payload.signature", "algorithm": "HMAC-SHA256"},
        ),
    ]
    complete_samples = [
        *incomplete_samples,
        _digiseller_sample(
            sample_id="digiseller-real-refund",
            evidence_kind=Stage1ProviderEvidenceKind.REFUND_SAMPLE,
            provider_status="refunded",
            expected_payment_state=Stage1PaymentState.REFUNDED,
            automatic_paid_access_allowed=False,
            payload_shape={"invoice_id": "redacted-invoice", "status": "refunded"},
        ),
    ]

    incomplete = decide_stage1_provider_enablement(Stage1PaymentProvider.DIGISELLER, incomplete_samples)
    complete = decide_stage1_provider_enablement(Stage1PaymentProvider.DIGISELLER, complete_samples)

    assert incomplete.allowed is False
    assert "refund_or_reconciliation_evidence_missing" in incomplete.blockers
    assert complete.allowed is True
    assert complete.blockers == ()
    assert complete.provider_account_sample_count == 5


def _digiseller_sample(
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
        provider=Stage1PaymentProvider.DIGISELLER,
        evidence_kind=evidence_kind,
        environment=Stage1ProviderEvidenceEnvironment.SANDBOX,
        source=Stage1ProviderEvidenceSource.PROVIDER_ACCOUNT,
        captured_at="2026-05-07T00:00:00Z",
        official_source_url="https://my.digiseller.com/inside/api_payment.asp",
        tech_debt_id="TD-S1-PAY-009",
        provider_status=provider_status,
        expected_payment_state=expected_payment_state,
        automatic_paid_access_allowed=automatic_paid_access_allowed,
        payload_shape=payload_shape
        or {
            "invoice_id": "redacted-invoice",
            "amount": "10.00",
            "currency": "USD",
            "status": provider_status,
        },
    )
