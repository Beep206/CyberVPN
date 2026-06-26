from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from types import MappingProxyType
from typing import Protocol
from uuid import UUID

RISK_SCHEMA_VERSION = "growth-risk.v6.features.v1"
RISK_RULES_POLICY_VERSION = "growth-risk.v6.rules.v1"
SENSITIVE_FEATURE_KEY_PARTS = (
    "email",
    "phone",
    "telegram_username",
    "raw_code",
    "full_ip",
    "payment_credential",
    "card_pan",
    "cookie",
    "jwt",
    "token",
)
RISK_ACTION_ORDER = {"allow": 0, "challenge": 1, "review": 2, "deny": 3}


class GrowthRiskModelUnavailable(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class GrowthRiskPolicy:
    allow_threshold: Decimal = Decimal("0.40")
    challenge_threshold: Decimal = Decimal("0.70")
    review_threshold: Decimal = Decimal("0.90")
    high_risk_model_unavailable_action: str = "review"
    low_risk_model_unavailable_action: str = "allow"
    allow_hard_allow: bool = False


@dataclass(frozen=True, slots=True)
class GrowthRiskModelMetadata:
    model_key: str
    version: str
    artifact_checksum: str
    feature_schema_version: str = RISK_SCHEMA_VERSION
    deployment_mode: str = "champion"
    model_version_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class GrowthRiskPrediction:
    score: Decimal
    reason_codes: tuple[str, ...] = ()
    model: GrowthRiskModelMetadata | None = None


@dataclass(frozen=True, slots=True)
class GrowthRiskEvaluationCommand:
    risk_subject_id: UUID
    action_context: str
    features: Mapping[str, object]
    policy: GrowthRiskPolicy = field(default_factory=GrowthRiskPolicy)
    high_risk_context: bool = False
    private_grant_id: UUID | None = None
    growth_code_id: UUID | None = None
    code_set_id: UUID | None = None
    quote_session_id: UUID | None = None
    order_id: UUID | None = None
    hard_deny_reason_codes: tuple[str, ...] = ()
    hard_allow_reason_codes: tuple[str, ...] = ()
    generated_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class GrowthRiskEvaluationResult:
    risk_subject_id: UUID
    action_context: str
    rules_outcome: str
    ml_score: Decimal | None
    risk_band: str
    final_action: str
    reason_codes: tuple[str, ...]
    fallback_mode: str | None
    feature_snapshot: Mapping[str, object]
    feature_hash: str
    decision_trace: Mapping[str, object]
    model: GrowthRiskModelMetadata | None
    decided_at: datetime


class GrowthRiskModelClient(Protocol):
    async def score(self, *, features: Mapping[str, object]) -> GrowthRiskPrediction:
        raise NotImplementedError


class GrowthRiskDecisionUseCase:
    def __init__(self, model_client: GrowthRiskModelClient | None = None) -> None:
        self._model_client = model_client

    async def execute(self, command: GrowthRiskEvaluationCommand) -> GrowthRiskEvaluationResult:
        decided_at = command.generated_at or datetime.now(UTC)
        sanitized_features, dropped_feature_keys = sanitize_growth_risk_features(command.features)
        feature_hash = build_feature_hash(sanitized_features)

        rules_outcome, rule_reasons = _evaluate_hard_rules(command)
        prediction: GrowthRiskPrediction | None = None
        fallback_mode: str | None = None
        model_error_reason: str | None = None
        if self._model_client is not None:
            try:
                prediction = await self._model_client.score(features=sanitized_features)
            except GrowthRiskModelUnavailable:
                model_error_reason = "MODEL_UNAVAILABLE"
            except TimeoutError:
                model_error_reason = "MODEL_TIMEOUT"
        else:
            model_error_reason = "MODEL_UNAVAILABLE"

        if prediction is not None:
            try:
                _validate_prediction(prediction)
            except GrowthRiskModelUnavailable:
                prediction = None
                model_error_reason = "MODEL_INVALID_RESPONSE"

        if prediction is not None:
            risk_band = _risk_band(prediction.score, command.policy)
            ml_action = _action_for_band(risk_band)
            if prediction.model and prediction.model.deployment_mode == "shadow":
                final_action = rules_outcome
                fallback_mode = "shadow_model_no_effect"
            else:
                final_action = _max_action(rules_outcome, ml_action)
            ml_score: Decimal | None = prediction.score
            model = prediction.model
            model_reason_codes = prediction.reason_codes
        else:
            risk_band = "unknown"
            ml_score = None
            model = None
            model_reason_codes = ()
            if rules_outcome == "deny":
                final_action = "deny"
                fallback_mode = "hard_deny_without_model"
            elif command.high_risk_context:
                final_action = command.policy.high_risk_model_unavailable_action
                fallback_mode = "model_unavailable_fail_closed"
            else:
                final_action = command.policy.low_risk_model_unavailable_action
                fallback_mode = "model_unavailable_rules_only"

        reason_codes = _dedupe_reason_codes(
            (
                *rule_reasons,
                *model_reason_codes,
                *(("PRIVACY_FEATURES_DROPPED",) if dropped_feature_keys else ()),
                *((model_error_reason,) if model_error_reason else ()),
            )
        )
        decision_trace = MappingProxyType(
            {
                "schema_version": RISK_SCHEMA_VERSION,
                "rules_policy_version": RISK_RULES_POLICY_VERSION,
                "rules_outcome": rules_outcome,
                "model_deployment_mode": model.deployment_mode if model else None,
                "fallback_mode": fallback_mode,
                "high_risk_context": command.high_risk_context,
                "dropped_feature_keys": tuple(dropped_feature_keys),
            }
        )
        return GrowthRiskEvaluationResult(
            risk_subject_id=command.risk_subject_id,
            action_context=command.action_context,
            rules_outcome=rules_outcome,
            ml_score=ml_score,
            risk_band=risk_band,
            final_action=final_action,
            reason_codes=reason_codes,
            fallback_mode=fallback_mode,
            feature_snapshot=MappingProxyType(sanitized_features),
            feature_hash=feature_hash,
            decision_trace=decision_trace,
            model=model,
            decided_at=decided_at,
        )


def sanitize_growth_risk_features(features: Mapping[str, object]) -> tuple[dict[str, object], tuple[str, ...]]:
    sanitized: dict[str, object] = {}
    dropped: list[str] = []
    for key, value in sorted(features.items(), key=lambda item: item[0]):
        normalized_key = key.lower()
        if any(part in normalized_key for part in SENSITIVE_FEATURE_KEY_PARTS):
            dropped.append(key)
            continue
        if isinstance(value, Mapping):
            nested, nested_dropped = sanitize_growth_risk_features(value)
            sanitized[key] = nested
            dropped.extend(f"{key}.{item}" for item in nested_dropped)
        elif isinstance(value, (str, int, bool)) or value is None:
            sanitized[key] = value
        elif isinstance(value, Decimal):
            sanitized[key] = str(value)
        elif isinstance(value, float):
            sanitized[key] = str(Decimal(str(value)))
        elif isinstance(value, (list, tuple)):
            sanitized[key] = tuple(_safe_sequence_value(item) for item in value)
        else:
            sanitized[key] = str(value)
    return sanitized, tuple(dropped)


def build_feature_hash(features: Mapping[str, object]) -> str:
    encoded = json.dumps(features, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


def _safe_sequence_value(value: object) -> object:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    if isinstance(value, Mapping):
        nested, _ = sanitize_growth_risk_features(value)
        return nested
    return str(value)


def _evaluate_hard_rules(command: GrowthRiskEvaluationCommand) -> tuple[str, tuple[str, ...]]:
    if command.hard_deny_reason_codes:
        return "deny", command.hard_deny_reason_codes
    if command.hard_allow_reason_codes and command.policy.allow_hard_allow:
        return "allow", command.hard_allow_reason_codes
    if command.high_risk_context:
        return "challenge", ("HIGH_RISK_CONTEXT",)
    return "allow", command.hard_allow_reason_codes


def _validate_prediction(prediction: GrowthRiskPrediction) -> None:
    if prediction.score < 0 or prediction.score > 1:
        raise GrowthRiskModelUnavailable("invalid risk score")
    if prediction.model and prediction.model.feature_schema_version != RISK_SCHEMA_VERSION:
        raise GrowthRiskModelUnavailable("feature schema mismatch")


def _risk_band(score: Decimal, policy: GrowthRiskPolicy) -> str:
    if score >= policy.review_threshold:
        return "critical"
    if score >= policy.challenge_threshold:
        return "high"
    if score >= policy.allow_threshold:
        return "medium"
    return "low"


def _action_for_band(risk_band: str) -> str:
    if risk_band == "critical":
        return "review"
    if risk_band == "high":
        return "challenge"
    return "allow"


def _max_action(left: str, right: str) -> str:
    return left if RISK_ACTION_ORDER[left] >= RISK_ACTION_ORDER[right] else right


def _dedupe_reason_codes(reason_codes: tuple[str, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for code in reason_codes:
        if code in seen:
            continue
        seen.add(code)
        result.append(code)
    return tuple(result)
