"""S1-PAY-017 provider evidence replacement guardrails."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.presentation.api.shared.stage1_contract import Stage1PaymentState
from src.presentation.api.shared.stage1_payment_mapping import Stage1PaymentProvider
from src.presentation.api.shared.stage1_provider_evidence import (
    Stage1ProviderEvidenceEnvironment,
    Stage1ProviderEvidenceKind,
    Stage1ProviderEvidenceSample,
    Stage1ProviderEvidenceSource,
    decide_stage1_provider_enablement,
    parse_stage1_provider_evidence_sample,
    summarize_stage1_provider_evidence,
    validate_stage1_provider_evidence_sample,
)

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "stage1_provider_evidence"
    / "provider_documentation_placeholders.json"
)


def _load_documentation_placeholders() -> list[Stage1ProviderEvidenceSample]:
    raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return [parse_stage1_provider_evidence_sample(item) for item in raw["samples"]]


def test_stage1_provider_documentation_placeholder_fixture_covers_all_approved_providers() -> None:
    samples = _load_documentation_placeholders()

    assert {sample.provider for sample in samples} == set(Stage1PaymentProvider)
    assert all(sample.source is Stage1ProviderEvidenceSource.OFFICIAL_DOCUMENTATION for sample in samples)
    assert all(sample.environment is Stage1ProviderEvidenceEnvironment.OFFICIAL_DOCS for sample in samples)


def test_stage1_provider_documentation_placeholders_match_status_mapping_and_are_redacted() -> None:
    samples = _load_documentation_placeholders()

    validations = [validate_stage1_provider_evidence_sample(sample) for sample in samples]

    assert all(validation.valid for validation in validations), {
        validation.sample_id: validation.errors for validation in validations if not validation.valid
    }


@pytest.mark.parametrize("provider", list(Stage1PaymentProvider))
def test_stage1_provider_documentation_placeholders_never_enable_paid_rail(
    provider: Stage1PaymentProvider,
) -> None:
    samples = _load_documentation_placeholders()

    decision = decide_stage1_provider_enablement(provider, samples)

    assert decision.allowed is False
    assert decision.provider_account_sample_count == 0
    assert "real_provider_account_samples_missing" in decision.blockers
    assert "real_callback_sample_missing" in decision.blockers


def test_stage1_provider_evidence_summary_marks_all_documentation_only_providers_blocked() -> None:
    summary = summarize_stage1_provider_evidence(_load_documentation_placeholders())

    assert set(summary) == {provider.value for provider in Stage1PaymentProvider}
    assert all(row["allowed"] is False for row in summary.values())
    assert all(row["provider_account_sample_count"] == 0 for row in summary.values())


def test_stage1_provider_account_evidence_can_unlock_provider_only_when_required_samples_exist() -> None:
    samples = [
        _sample(
            sample_id="cryptobot-real-paid-callback",
            evidence_kind=Stage1ProviderEvidenceKind.CALLBACK_SAMPLE,
            provider_status="invoice_paid",
            expected_payment_state=Stage1PaymentState.PAID,
            automatic_paid_access_allowed=True,
        ),
        _sample(
            sample_id="cryptobot-real-expired-callback",
            evidence_kind=Stage1ProviderEvidenceKind.CALLBACK_SAMPLE,
            provider_status="expired",
            expected_payment_state=Stage1PaymentState.EXPIRED,
            automatic_paid_access_allowed=False,
        ),
        _sample(
            sample_id="cryptobot-real-status-poll",
            evidence_kind=Stage1ProviderEvidenceKind.STATUS_POLL_SAMPLE,
            provider_status="paid",
            expected_payment_state=Stage1PaymentState.PAID,
            automatic_paid_access_allowed=True,
        ),
        _sample(
            sample_id="cryptobot-real-signature",
            evidence_kind=Stage1ProviderEvidenceKind.SIGNATURE_VERIFICATION,
            provider_status="paid",
            expected_payment_state=Stage1PaymentState.PAID,
            automatic_paid_access_allowed=True,
        ),
        _sample(
            sample_id="cryptobot-real-reconciliation",
            evidence_kind=Stage1ProviderEvidenceKind.RECONCILIATION_SAMPLE,
            provider_status="paid",
            expected_payment_state=Stage1PaymentState.PAID,
            automatic_paid_access_allowed=True,
        ),
    ]

    decision = decide_stage1_provider_enablement(Stage1PaymentProvider.CRYPTOBOT, samples)

    assert decision.allowed is True
    assert decision.blockers == ()
    assert decision.provider_account_sample_count == 5


def test_stage1_provider_account_sample_rejects_official_docs_environment() -> None:
    sample = _sample(
        sample_id="cryptobot-bad-environment",
        evidence_kind=Stage1ProviderEvidenceKind.CALLBACK_SAMPLE,
        provider_status="paid",
        expected_payment_state=Stage1PaymentState.PAID,
        automatic_paid_access_allowed=True,
        environment=Stage1ProviderEvidenceEnvironment.OFFICIAL_DOCS,
    )

    validation = validate_stage1_provider_evidence_sample(sample)

    assert validation.valid is False
    assert "provider_account_sample_requires_sandbox_or_production_environment" in validation.errors


def test_stage1_provider_account_sample_rejects_sensitive_payload_keys() -> None:
    sample = _sample(
        sample_id="cryptobot-bad-secret-payload",
        evidence_kind=Stage1ProviderEvidenceKind.CALLBACK_SAMPLE,
        provider_status="paid",
        expected_payment_state=Stage1PaymentState.PAID,
        automatic_paid_access_allowed=True,
        payload_shape={"invoice_id": "redacted-invoice", "api_key": "must-not-appear"},
    )

    validation = validate_stage1_provider_evidence_sample(sample)

    assert validation.valid is False
    assert "forbidden_payload_key:api_key" in validation.errors


def _sample(
    *,
    sample_id: str,
    evidence_kind: Stage1ProviderEvidenceKind,
    provider_status: str,
    expected_payment_state: Stage1PaymentState,
    automatic_paid_access_allowed: bool,
    environment: Stage1ProviderEvidenceEnvironment = Stage1ProviderEvidenceEnvironment.SANDBOX,
    payload_shape: dict[str, object] | None = None,
) -> Stage1ProviderEvidenceSample:
    return Stage1ProviderEvidenceSample(
        sample_id=sample_id,
        provider=Stage1PaymentProvider.CRYPTOBOT,
        evidence_kind=evidence_kind,
        environment=environment,
        source=Stage1ProviderEvidenceSource.PROVIDER_ACCOUNT,
        captured_at="2026-05-05T00:00:00Z",
        official_source_url="https://help.send.tg/en/articles/10279948-crypto-pay-api",
        tech_debt_id="TD-S1-PAY-005",
        provider_status=provider_status,
        expected_payment_state=expected_payment_state,
        automatic_paid_access_allowed=automatic_paid_access_allowed,
        payload_shape=payload_shape or {"invoice_id": "redacted-invoice", "status": provider_status},
    )
