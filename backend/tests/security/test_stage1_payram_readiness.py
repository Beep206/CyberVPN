"""S1-PAY-013 PayRam readiness guardrails."""

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


def _load_payram_documentation_samples() -> list[Stage1ProviderEvidenceSample]:
    raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    samples = [parse_stage1_provider_evidence_sample(item) for item in raw["samples"]]
    return [sample for sample in samples if sample.provider is Stage1PaymentProvider.PAYRAM]


def test_stage1_payram_documentation_only_samples_do_not_enable_paid_rail() -> None:
    samples = _load_payram_documentation_samples()

    validations = [validate_stage1_provider_evidence_sample(sample) for sample in samples]
    decision = decide_stage1_provider_enablement(Stage1PaymentProvider.PAYRAM, samples)

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


def test_stage1_payram_filled_is_the_only_normal_paid_access_status() -> None:
    pending = resolve_stage1_provider_payment_status(Stage1PaymentProvider.PAYRAM, "OPEN")
    paid = resolve_stage1_provider_payment_status(Stage1PaymentProvider.PAYRAM, "FILLED")
    underpaid = resolve_stage1_provider_payment_status(Stage1PaymentProvider.PAYRAM, "PARTIALLY_FILLED")
    expired = resolve_stage1_provider_payment_status(Stage1PaymentProvider.PAYRAM, "CANCELLED")

    assert pending.payment_state is Stage1PaymentState.PENDING
    assert pending.automatic_paid_access_allowed is False
    assert pending.final is False

    assert paid.payment_state is Stage1PaymentState.PAID
    assert paid.automatic_paid_access_allowed is True
    assert paid.final is True
    assert paid.manual_review_required is False

    assert underpaid.payment_state is Stage1PaymentState.RECONCILIATION_REQUIRED
    assert underpaid.automatic_paid_access_allowed is False
    assert underpaid.manual_review_required is True
    assert underpaid.support_state is Stage1SupportState.SUPPORT_REVIEW

    assert expired.payment_state is Stage1PaymentState.EXPIRED
    assert expired.automatic_paid_access_allowed is False
    assert expired.final is True


def test_stage1_payram_overfilled_is_manual_review_by_default() -> None:
    default_decision = resolve_stage1_provider_payment_status(
        Stage1PaymentProvider.PAYRAM,
        "OVER_FILLED",
        amount_expected="10.00",
        amount_received="12.00",
    )
    explicit_policy = resolve_stage1_provider_payment_status(
        Stage1PaymentProvider.PAYRAM,
        "OVER_FILLED",
        amount_expected="10.00",
        amount_received="12.00",
        allow_overpaid_auto_access=True,
    )
    bad_evidence = resolve_stage1_provider_payment_status(
        Stage1PaymentProvider.PAYRAM,
        "OVER_FILLED",
        amount_expected="10.00",
        amount_received="not-a-number",
        allow_overpaid_auto_access=True,
    )

    assert default_decision.payment_state is Stage1PaymentState.RECONCILIATION_REQUIRED
    assert default_decision.automatic_paid_access_allowed is False
    assert default_decision.manual_review_required is True
    assert default_decision.support_state is Stage1SupportState.SUPPORT_REVIEW

    assert explicit_policy.payment_state is Stage1PaymentState.PAID
    assert explicit_policy.automatic_paid_access_allowed is True
    assert explicit_policy.manual_review_required is True

    assert bad_evidence.payment_state is Stage1PaymentState.RECONCILIATION_REQUIRED
    assert bad_evidence.automatic_paid_access_allowed is False


def test_stage1_payram_webhook_requires_api_key_header_and_safe_output() -> None:
    secret = "redacted-payram-project-key"

    valid = verify_stage1_webhook_signature(
        Stage1PaymentProvider.PAYRAM,
        headers={"API-Key": secret},
        secret=secret,
    )
    lowercase_header = verify_stage1_webhook_signature(
        Stage1PaymentProvider.PAYRAM,
        headers={"api-key": secret},
        secret=secret,
    )
    invalid = verify_stage1_webhook_signature(
        Stage1PaymentProvider.PAYRAM,
        headers={"API-Key": "wrong-key"},
        secret=secret,
    )
    missing = verify_stage1_webhook_signature(
        Stage1PaymentProvider.PAYRAM,
        headers={},
        secret=secret,
    )

    assert valid.accepted is True
    assert lowercase_header.accepted is True
    assert invalid.accepted is False
    assert invalid.status is Stage1WebhookSignatureStatus.INVALID
    assert missing.accepted is False
    assert missing.status is Stage1WebhookSignatureStatus.MISSING_SIGNATURE

    serialized = str(valid.to_safe_dict())
    assert secret not in serialized
    assert "signature_present" in serialized


def test_stage1_payram_identity_supports_webhook_and_status_poll_payload_shapes() -> None:
    webhook_identity = extract_stage1_webhook_identity(
        Stage1PaymentProvider.PAYRAM,
        {
            "reference_id": "redacted-payram-reference",
            "status": "FILLED",
            "invoice_id": "redacted-payram-invoice",
            "amount": "10.00",
            "currency": "USDT",
        },
    )
    status_poll_identity = extract_stage1_webhook_identity(
        Stage1PaymentProvider.PAYRAM,
        {
            "referenceID": "redacted-payram-reference",
            "paymentState": "FILLED",
            "invoiceID": "redacted-payram-invoice",
            "amountInUSD": "10.00",
        },
    )

    assert webhook_identity.normalized_status == "filled"
    assert status_poll_identity.normalized_status == "filled"
    assert status_poll_identity.operation_key == webhook_identity.operation_key


def test_stage1_payram_duplicate_callbacks_do_not_repeat_side_effects() -> None:
    guard = Stage1InMemoryWebhookIdempotencyGuard()
    first_identity = extract_stage1_webhook_identity(
        Stage1PaymentProvider.PAYRAM,
        {
            "reference_id": "redacted-payram-reference",
            "status": "FILLED",
            "webhook_id": "first-callback",
        },
    )
    second_identity = extract_stage1_webhook_identity(
        Stage1PaymentProvider.PAYRAM,
        {
            "reference_id": "redacted-payram-reference",
            "status": "FILLED",
            "webhook_id": "provider-retry-with-new-id",
        },
    )

    first = guard.record(first_identity)
    second = guard.record(second_identity)

    assert first.result is Stage1WebhookIdempotencyResult.ACCEPTED_NEW
    assert first.side_effects_allowed == DEFAULT_STAGE1_WEBHOOK_SIDE_EFFECTS
    assert second.result is Stage1WebhookIdempotencyResult.ACCEPTED_ALREADY_APPLIED
    assert second.side_effects_allowed == ()
    assert set(second.side_effects_already_applied) == set(DEFAULT_STAGE1_WEBHOOK_SIDE_EFFECTS)


def test_stage1_payram_provider_enablement_requires_full_real_evidence_set() -> None:
    incomplete_samples = [
        _payram_sample(
            sample_id="payram-real-paid-callback",
            evidence_kind=Stage1ProviderEvidenceKind.CALLBACK_SAMPLE,
            provider_status="FILLED",
            expected_payment_state=Stage1PaymentState.PAID,
            automatic_paid_access_allowed=True,
        ),
        _payram_sample(
            sample_id="payram-real-underpaid-callback",
            evidence_kind=Stage1ProviderEvidenceKind.CALLBACK_SAMPLE,
            provider_status="PARTIALLY_FILLED",
            expected_payment_state=Stage1PaymentState.RECONCILIATION_REQUIRED,
            automatic_paid_access_allowed=False,
        ),
        _payram_sample(
            sample_id="payram-real-status-poll",
            evidence_kind=Stage1ProviderEvidenceKind.STATUS_POLL_SAMPLE,
            provider_status="FILLED",
            expected_payment_state=Stage1PaymentState.PAID,
            automatic_paid_access_allowed=True,
        ),
        _payram_sample(
            sample_id="payram-real-api-key-header",
            evidence_kind=Stage1ProviderEvidenceKind.SIGNATURE_VERIFICATION,
            provider_status="FILLED",
            expected_payment_state=Stage1PaymentState.PAID,
            automatic_paid_access_allowed=True,
            payload_shape={"signature_location": "API-Key", "header_present": True},
        ),
    ]
    complete_samples = [
        *incomplete_samples,
        _payram_sample(
            sample_id="payram-real-reconciliation",
            evidence_kind=Stage1ProviderEvidenceKind.RECONCILIATION_SAMPLE,
            provider_status="PARTIALLY_FILLED",
            expected_payment_state=Stage1PaymentState.RECONCILIATION_REQUIRED,
            automatic_paid_access_allowed=False,
            payload_shape={"reference_id": "redacted-reference", "status": "PARTIALLY_FILLED"},
        ),
    ]

    incomplete = decide_stage1_provider_enablement(Stage1PaymentProvider.PAYRAM, incomplete_samples)
    complete = decide_stage1_provider_enablement(Stage1PaymentProvider.PAYRAM, complete_samples)

    assert incomplete.allowed is False
    assert "refund_or_reconciliation_evidence_missing" in incomplete.blockers
    assert complete.allowed is True
    assert complete.blockers == ()
    assert complete.provider_account_sample_count == 5


def _payram_sample(
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
        provider=Stage1PaymentProvider.PAYRAM,
        evidence_kind=evidence_kind,
        environment=Stage1ProviderEvidenceEnvironment.SANDBOX,
        source=Stage1ProviderEvidenceSource.PROVIDER_ACCOUNT,
        captured_at="2026-05-07T00:00:00Z",
        official_source_url="https://docs.payram.com/api-integration/payments-api/webhook",
        tech_debt_id="TD-S1-PAY-001",
        provider_status=provider_status,
        expected_payment_state=expected_payment_state,
        automatic_paid_access_allowed=automatic_paid_access_allowed,
        payload_shape=payload_shape
        or {
            "reference_id": "redacted-reference",
            "status": provider_status,
            "amount": "10.00",
            "currency": "USDT",
        },
    )
