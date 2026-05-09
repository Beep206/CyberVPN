"""S1 provider evidence registry for payment-provider enablement gates."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from src.presentation.api.shared.stage1_contract import Stage1PaymentState
from src.presentation.api.shared.stage1_payment_mapping import (
    Stage1PaymentProvider,
    resolve_stage1_provider_payment_status,
)


class Stage1ProviderEvidenceEnvironment(StrEnum):
    """Environment where a provider evidence sample was captured."""

    OFFICIAL_DOCS = "official_docs"
    SANDBOX = "sandbox"
    PRODUCTION = "production"


class Stage1ProviderEvidenceSource(StrEnum):
    """Evidence source class used to separate docs placeholders from provider-account proof."""

    OFFICIAL_DOCUMENTATION = "official_documentation"
    PROVIDER_ACCOUNT = "provider_account"


class Stage1ProviderEvidenceKind(StrEnum):
    """Provider evidence category required before enabling a paid rail."""

    CALLBACK_SAMPLE = "callback_sample"
    STATUS_POLL_SAMPLE = "status_poll_sample"
    SIGNATURE_VERIFICATION = "signature_verification"
    REFUND_SAMPLE = "refund_sample"
    RECONCILIATION_SAMPLE = "reconciliation_sample"


@dataclass(frozen=True, slots=True)
class Stage1ProviderEvidenceSample:
    """Single redacted provider evidence sample.

    This class intentionally stores payload shape only. Real provider IDs,
    signatures, checkout URLs, API keys and request snapshots must stay out of
    committed evidence.
    """

    sample_id: str
    provider: Stage1PaymentProvider
    evidence_kind: Stage1ProviderEvidenceKind
    environment: Stage1ProviderEvidenceEnvironment
    source: Stage1ProviderEvidenceSource
    captured_at: str
    official_source_url: str
    tech_debt_id: str
    provider_status: str
    expected_payment_state: Stage1PaymentState
    automatic_paid_access_allowed: bool
    payload_shape: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class Stage1ProviderEvidenceValidation:
    """Validation result for a provider evidence sample."""

    sample_id: str
    provider: Stage1PaymentProvider
    valid: bool
    errors: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Stage1ProviderEnablementDecision:
    """Provider enablement decision from currently attached evidence."""

    provider: Stage1PaymentProvider
    allowed: bool
    blockers: tuple[str, ...]
    provider_account_sample_count: int

    def to_api_dict(self) -> dict[str, str | bool | int | list[str]]:
        return {
            "provider": self.provider.value,
            "allowed": self.allowed,
            "blockers": list(self.blockers),
            "provider_account_sample_count": self.provider_account_sample_count,
        }


_FORBIDDEN_EVIDENCE_KEYS = frozenset(
    {
        "api_key",
        "authorization",
        "checkout_url",
        "idempotency_key",
        "password",
        "payment_url",
        "provider_snapshot",
        "request_snapshot",
        "secret",
        "token",
    }
)


def parse_stage1_provider_evidence_sample(raw: Mapping[str, Any]) -> Stage1ProviderEvidenceSample:
    """Parse a raw JSON evidence row into a typed sample."""

    return Stage1ProviderEvidenceSample(
        sample_id=str(raw["sample_id"]),
        provider=Stage1PaymentProvider(str(raw["provider"])),
        evidence_kind=Stage1ProviderEvidenceKind(str(raw["evidence_kind"])),
        environment=Stage1ProviderEvidenceEnvironment(str(raw["environment"])),
        source=Stage1ProviderEvidenceSource(str(raw["source"])),
        captured_at=str(raw["captured_at"]),
        official_source_url=str(raw["official_source_url"]),
        tech_debt_id=str(raw["tech_debt_id"]),
        provider_status=str(raw["provider_status"]),
        expected_payment_state=Stage1PaymentState(str(raw["expected_payment_state"])),
        automatic_paid_access_allowed=bool(raw["automatic_paid_access_allowed"]),
        payload_shape=_mapping_or_empty(raw.get("payload_shape")),
    )


def validate_stage1_provider_evidence_sample(
    sample: Stage1ProviderEvidenceSample,
) -> Stage1ProviderEvidenceValidation:
    """Validate that a provider sample is redacted and matches the S1 status mapping."""

    errors: list[str] = []
    if not sample.sample_id.strip():
        errors.append("sample_id_missing")
    if not sample.official_source_url.startswith("https://"):
        errors.append("official_source_url_must_be_https")
    if not sample.tech_debt_id.startswith("TD-S1-PAY-"):
        errors.append("payment_tech_debt_id_required")
    if sample.source is Stage1ProviderEvidenceSource.OFFICIAL_DOCUMENTATION:
        if sample.environment is not Stage1ProviderEvidenceEnvironment.OFFICIAL_DOCS:
            errors.append("official_documentation_requires_official_docs_environment")
    elif sample.environment is Stage1ProviderEvidenceEnvironment.OFFICIAL_DOCS:
        errors.append("provider_account_sample_requires_sandbox_or_production_environment")

    decision = resolve_stage1_provider_payment_status(sample.provider, sample.provider_status)
    if decision.payment_state is not sample.expected_payment_state:
        errors.append("expected_payment_state_mismatch")
    if decision.automatic_paid_access_allowed is not sample.automatic_paid_access_allowed:
        errors.append("automatic_paid_access_decision_mismatch")

    if leaked_key := _first_forbidden_key(sample.payload_shape):
        errors.append(f"forbidden_payload_key:{leaked_key}")

    return Stage1ProviderEvidenceValidation(
        sample_id=sample.sample_id,
        provider=sample.provider,
        valid=not errors,
        errors=tuple(errors),
    )


def decide_stage1_provider_enablement(
    provider: Stage1PaymentProvider | str,
    samples: Sequence[Stage1ProviderEvidenceSample],
) -> Stage1ProviderEnablementDecision:
    """Decide whether a provider has enough real evidence to be enabled for paid S1."""

    provider_enum = Stage1PaymentProvider(str(provider))
    provider_account_samples = [
        sample
        for sample in samples
        if sample.provider is provider_enum and sample.source is Stage1ProviderEvidenceSource.PROVIDER_ACCOUNT
    ]
    blockers: list[str] = []
    if not provider_account_samples:
        blockers.append("real_provider_account_samples_missing")

    invalid_sample_ids = [
        validation.sample_id
        for validation in (validate_stage1_provider_evidence_sample(sample) for sample in provider_account_samples)
        if not validation.valid
    ]
    if invalid_sample_ids:
        blockers.append("invalid_provider_account_samples:" + ",".join(sorted(invalid_sample_ids)))

    if not _has_provider_account_kind(provider_account_samples, Stage1ProviderEvidenceKind.CALLBACK_SAMPLE):
        blockers.append("real_callback_sample_missing")
    if not any(
        sample.evidence_kind is Stage1ProviderEvidenceKind.CALLBACK_SAMPLE
        and sample.expected_payment_state is Stage1PaymentState.PAID
        and sample.automatic_paid_access_allowed
        for sample in provider_account_samples
    ):
        blockers.append("real_paid_success_callback_missing")
    if not any(
        sample.evidence_kind is Stage1ProviderEvidenceKind.CALLBACK_SAMPLE
        and sample.expected_payment_state is not Stage1PaymentState.PAID
        for sample in provider_account_samples
    ):
        blockers.append("real_non_success_callback_missing")
    if not _has_provider_account_kind(provider_account_samples, Stage1ProviderEvidenceKind.STATUS_POLL_SAMPLE):
        blockers.append("real_status_poll_sample_missing")
    if not _has_provider_account_kind(provider_account_samples, Stage1ProviderEvidenceKind.SIGNATURE_VERIFICATION):
        blockers.append("signature_verification_evidence_missing")
    if not (
        _has_provider_account_kind(provider_account_samples, Stage1ProviderEvidenceKind.REFUND_SAMPLE)
        or _has_provider_account_kind(provider_account_samples, Stage1ProviderEvidenceKind.RECONCILIATION_SAMPLE)
    ):
        blockers.append("refund_or_reconciliation_evidence_missing")

    return Stage1ProviderEnablementDecision(
        provider=provider_enum,
        allowed=not blockers,
        blockers=tuple(blockers),
        provider_account_sample_count=len(provider_account_samples),
    )


def summarize_stage1_provider_evidence(
    samples: Sequence[Stage1ProviderEvidenceSample],
) -> dict[str, dict[str, str | int | bool | list[str]]]:
    """Build a provider matrix suitable for docs/evidence output."""

    return {
        provider.value: decide_stage1_provider_enablement(provider, samples).to_api_dict()
        for provider in Stage1PaymentProvider
    }


def _mapping_or_empty(value: object) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _has_provider_account_kind(
    samples: Sequence[Stage1ProviderEvidenceSample],
    evidence_kind: Stage1ProviderEvidenceKind,
) -> bool:
    return any(sample.evidence_kind is evidence_kind for sample in samples)


def _first_forbidden_key(value: object) -> str | None:
    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            normalized = str(key).strip().lower()
            if (
                normalized in _FORBIDDEN_EVIDENCE_KEYS
                or normalized.endswith("_secret")
                or normalized.endswith("_token")
                or normalized.endswith("_api_key")
            ):
                return str(key)
            nested_forbidden = _first_forbidden_key(nested_value)
            if nested_forbidden is not None:
                return nested_forbidden
    elif isinstance(value, list | tuple):
        for item in value:
            nested_forbidden = _first_forbidden_key(item)
            if nested_forbidden is not None:
                return nested_forbidden
    return None


__all__ = [
    "Stage1ProviderEnablementDecision",
    "Stage1ProviderEvidenceEnvironment",
    "Stage1ProviderEvidenceKind",
    "Stage1ProviderEvidenceSample",
    "Stage1ProviderEvidenceSource",
    "Stage1ProviderEvidenceValidation",
    "decide_stage1_provider_enablement",
    "parse_stage1_provider_evidence_sample",
    "summarize_stage1_provider_evidence",
    "validate_stage1_provider_evidence_sample",
]
