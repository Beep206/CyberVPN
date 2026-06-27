from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from types import MappingProxyType
from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.infrastructure.database.models.growth_risk_fx_model import (
    GrowthRiskDecisionModel,
    RiskFeatureSnapshotModel,
    RiskModelVersionModel,
)
from src.infrastructure.database.models.policy_version_model import PolicyVersionModel
from src.infrastructure.database.models.risk_review_model import RiskReviewModel
from src.infrastructure.database.models.risk_subject_model import RiskSubjectModel

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
_EMAIL_VALUE_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_CARD_OR_TOKEN_RE = re.compile(r"^\d{12,19}$")
_CODE_LIKE_VALUE_RE = re.compile(r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z0-9][A-Za-z0-9_-]{5,}$")
_HEX_HASH_RE = re.compile(r"^[a-fA-F0-9]{32,128}$")


class GrowthRiskModelUnavailable(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class GrowthRiskPolicy:
    allow_threshold: Decimal = Decimal("0.40")
    challenge_threshold: Decimal = Decimal("0.70")
    review_threshold: Decimal = Decimal("0.90")
    deny_threshold: Decimal = Decimal("0.98")
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
    rules_policy_version_id: UUID | None = None
    high_risk_context: bool = False
    private_grant_id: UUID | None = None
    growth_code_id: UUID | None = None
    code_set_id: UUID | None = None
    quote_session_id: UUID | None = None
    order_id: UUID | None = None
    hard_deny_reason_codes: tuple[str, ...] = ()
    hard_allow_reason_codes: tuple[str, ...] = ()
    source_freshness: Mapping[str, object] = field(default_factory=dict)
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
    feature_snapshot_id: UUID | None = None
    decision_id: UUID | None = None
    risk_review_id: UUID | None = None


class GrowthRiskModelClient(Protocol):
    async def score(self, *, features: Mapping[str, object]) -> GrowthRiskPrediction:
        raise NotImplementedError


class GrowthRiskDecisionUseCase:
    def __init__(
        self,
        model_client: GrowthRiskModelClient | None = None,
        *,
        session: AsyncSession | None = None,
    ) -> None:
        self._model_client = model_client
        self._session = session

    async def execute(self, command: GrowthRiskEvaluationCommand) -> GrowthRiskEvaluationResult:
        decided_at = command.generated_at or datetime.now(UTC)
        sanitized_features, dropped_feature_keys = sanitize_growth_risk_features(command.features)
        feature_hash = build_feature_hash(sanitized_features)
        fail_closed_context = _requires_fail_closed_model_fallback(command, sanitized_features)

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
            prediction, registry_error_reason = await self._prepare_registered_prediction(prediction)
            if registry_error_reason is not None:
                prediction = None
                model_error_reason = registry_error_reason

        if prediction is not None:
            risk_band = _risk_band(prediction.score, command.policy)
            ml_action = _action_for_score(prediction.score, command.policy)
            if prediction.model and prediction.model.deployment_mode in {"shadow", "challenger"}:
                final_action = rules_outcome
                fallback_mode = f"{prediction.model.deployment_mode}_model_no_effect"
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
            elif fail_closed_context:
                final_action, escalated = _fail_closed_model_unavailable_action(command.policy)
                fallback_mode = "model_unavailable_fail_closed"
                if escalated:
                    model_error_reason = "MODEL_UNAVAILABLE_POLICY_ESCALATED"
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
                "model_candidate_action": _action_for_score(prediction.score, command.policy)
                if prediction is not None
                else None,
                "fallback_mode": fallback_mode,
                "high_risk_context": fail_closed_context,
                "dropped_feature_keys": tuple(dropped_feature_keys),
            }
        )
        result = GrowthRiskEvaluationResult(
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
        if self._session is None:
            return result
        return await self._persist_result(command=command, result=result)

    async def _prepare_registered_prediction(
        self,
        prediction: GrowthRiskPrediction,
    ) -> tuple[GrowthRiskPrediction, str | None]:
        try:
            _validate_prediction(prediction)
        except GrowthRiskModelUnavailable:
            return prediction, "MODEL_INVALID_RESPONSE"

        if self._session is None:
            return prediction, None

        if prediction.model is None:
            return prediction, "MODEL_REGISTRY_MISSING"

        registered_model = await self._load_registered_model(prediction.model)
        if registered_model is None:
            return prediction, "MODEL_REGISTRY_MISSING"
        if registered_model.artifact_checksum != prediction.model.artifact_checksum:
            return prediction, "MODEL_REGISTRY_CHECKSUM_MISMATCH"
        if registered_model.feature_schema_version != RISK_SCHEMA_VERSION:
            return prediction, "MODEL_REGISTRY_SCHEMA_MISMATCH"
        if registered_model.approval_state != "approved" or registered_model.status != "active":
            return prediction, "MODEL_REGISTRY_NOT_ACTIVE"
        if registered_model.deployment_mode not in {"champion", "shadow", "challenger"}:
            return prediction, "MODEL_REGISTRY_MODE_UNSUPPORTED"

        return (
            replace(
                prediction,
                model=GrowthRiskModelMetadata(
                    model_key=registered_model.model_key,
                    version=registered_model.version,
                    artifact_checksum=registered_model.artifact_checksum,
                    feature_schema_version=registered_model.feature_schema_version,
                    deployment_mode=registered_model.deployment_mode,
                    model_version_id=registered_model.id,
                ),
            ),
            None,
        )

    async def _load_registered_model(self, model: GrowthRiskModelMetadata) -> RiskModelVersionModel | None:
        if self._session is None:
            return None
        if model.model_version_id is not None:
            registered_model = await self._session.get(RiskModelVersionModel, model.model_version_id)
            if registered_model is None:
                return None
            if registered_model.model_key != model.model_key or registered_model.version != model.version:
                return None
            return registered_model

        result = await self._session.execute(
            select(RiskModelVersionModel).where(
                RiskModelVersionModel.model_key == model.model_key,
                RiskModelVersionModel.version == model.version,
            )
        )
        return result.scalar_one_or_none()

    async def _persist_result(
        self,
        *,
        command: GrowthRiskEvaluationCommand,
        result: GrowthRiskEvaluationResult,
    ) -> GrowthRiskEvaluationResult:
        if self._session is None:
            return result
        if command.rules_policy_version_id is None:
            raise ValueError("rules_policy_version_id is required to persist growth risk decisions")
        if await self._session.get(RiskSubjectModel, command.risk_subject_id) is None:
            raise ValueError("Risk subject not found")
        if await self._session.get(PolicyVersionModel, command.rules_policy_version_id) is None:
            raise ValueError("Rules policy version not found")

        feature_snapshot = await self._get_or_create_feature_snapshot(command=command, result=result)

        model_version_id = result.model.model_version_id if result.model else None
        decision_trace = {
            **_json_payload(result.decision_trace),
            "feature_snapshot_id": str(feature_snapshot.id),
            "feature_hash": result.feature_hash,
            "model_version_id": str(model_version_id) if model_version_id else None,
        }
        decision = GrowthRiskDecisionModel(
            risk_subject_id=command.risk_subject_id,
            code_set_id=command.code_set_id,
            growth_code_id=command.growth_code_id,
            private_grant_id=command.private_grant_id,
            quote_session_id=command.quote_session_id,
            order_id=command.order_id,
            action_context=command.action_context,
            rules_policy_version_id=command.rules_policy_version_id,
            model_version_id=model_version_id,
            feature_snapshot_id=feature_snapshot.id,
            rules_outcome=result.rules_outcome,
            ml_score=result.ml_score,
            risk_band=result.risk_band,
            final_action=result.final_action,
            reason_codes=list(result.reason_codes),
            fallback_mode=result.fallback_mode,
            decision_trace=decision_trace,
            decided_at=result.decided_at,
        )
        self._session.add(decision)
        await self._session.flush()
        await self._session.refresh(decision)

        review_id: UUID | None = None
        if result.final_action == "review":
            review = RiskReviewModel(
                risk_subject_id=command.risk_subject_id,
                review_type="growth_risk_manual_review",
                status="open",
                decision="pending",
                reason="Growth risk decision requires manual review",
                evidence=_review_evidence_payload(
                    command=command,
                    result=result,
                    decision_id=decision.id,
                    feature_snapshot_id=feature_snapshot.id,
                    model_version_id=model_version_id,
                ),
                created_by_admin_user_id=None,
            )
            self._session.add(review)
            await self._session.flush()
            await self._session.refresh(review)
            review_id = review.id

        return replace(
            result,
            feature_snapshot_id=feature_snapshot.id,
            decision_id=decision.id,
            risk_review_id=review_id,
        )

    async def _get_or_create_feature_snapshot(
        self,
        *,
        command: GrowthRiskEvaluationCommand,
        result: GrowthRiskEvaluationResult,
    ) -> RiskFeatureSnapshotModel:
        if self._session is None:
            raise RuntimeError("session is required")
        existing_snapshot = (
            await self._session.execute(
                select(RiskFeatureSnapshotModel).where(RiskFeatureSnapshotModel.feature_hash == result.feature_hash)
            )
        ).scalar_one_or_none()
        if existing_snapshot is not None:
            return existing_snapshot

        insert_result = await self._session.execute(
            pg_insert(RiskFeatureSnapshotModel)
            .values(
                risk_subject_id=command.risk_subject_id,
                feature_schema_version=RISK_SCHEMA_VERSION,
                features_payload=_json_payload(result.feature_snapshot),
                feature_hash=result.feature_hash,
                source_freshness=_source_freshness_payload(command.source_freshness),
                generated_at=result.decided_at,
            )
            .on_conflict_do_nothing(index_elements=[RiskFeatureSnapshotModel.feature_hash])
            .returning(RiskFeatureSnapshotModel.id)
        )
        inserted_id = insert_result.scalar_one_or_none()
        snapshot_result = await self._session.execute(
            select(RiskFeatureSnapshotModel).where(
                RiskFeatureSnapshotModel.id == inserted_id
                if inserted_id is not None
                else RiskFeatureSnapshotModel.feature_hash == result.feature_hash
            )
        )
        return snapshot_result.scalar_one()


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
        elif isinstance(value, str):
            sanitized[key] = _safe_string_value(value)
        elif isinstance(value, (int, bool)) or value is None:
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
    if isinstance(value, str):
        return _safe_string_value(value)
    if isinstance(value, (int, bool)) or value is None:
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
        return "allow", ("HIGH_RISK_CONTEXT",)
    return "allow", command.hard_allow_reason_codes


def _validate_prediction(prediction: GrowthRiskPrediction) -> None:
    if prediction.score < 0 or prediction.score > 1:
        raise GrowthRiskModelUnavailable("invalid risk score")
    if prediction.model and prediction.model.feature_schema_version != RISK_SCHEMA_VERSION:
        raise GrowthRiskModelUnavailable("feature schema mismatch")
    if prediction.model and not prediction.model.artifact_checksum.strip():
        raise GrowthRiskModelUnavailable("missing artifact checksum")


def _risk_band(score: Decimal, policy: GrowthRiskPolicy) -> str:
    if score >= policy.review_threshold:
        return "critical"
    if score >= policy.challenge_threshold:
        return "high"
    if score >= policy.allow_threshold:
        return "medium"
    return "low"


def _action_for_score(score: Decimal, policy: GrowthRiskPolicy) -> str:
    if score >= policy.deny_threshold:
        return "deny"
    if score >= policy.review_threshold:
        return "review"
    if score >= policy.challenge_threshold:
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


def _safe_string_value(value: str) -> str | dict[str, str]:
    stripped = value.strip()
    if not stripped:
        return value
    lowered = stripped.lower()
    if _HEX_HASH_RE.fullmatch(stripped) or lowered in {
        "true",
        "false",
        "low",
        "medium",
        "high",
        "critical",
        "miniapp",
        "web",
        "admin",
        "partner",
    }:
        return stripped
    if _EMAIL_VALUE_RE.fullmatch(stripped):
        return _hashed_redaction("email_hash", stripped.lower())
    if _looks_like_ip_address(stripped):
        return _hashed_redaction("ip_hash", stripped)
    if _CARD_OR_TOKEN_RE.fullmatch(stripped):
        return _hashed_redaction("payment_credential_hash", stripped)
    if _CODE_LIKE_VALUE_RE.fullmatch(stripped):
        return _hashed_redaction("code_or_token_hash", stripped)
    return stripped


def _looks_like_ip_address(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
    except ValueError:
        return False
    return True


def _hashed_redaction(kind: str, value: str) -> dict[str, str]:
    secret = settings.jwt_secret.get_secret_value().encode("utf-8")
    digest = hmac.new(secret, value.encode("utf-8"), hashlib.sha256).hexdigest()
    return {"redacted": kind, "value_hash": digest}


def _requires_fail_closed_model_fallback(
    command: GrowthRiskEvaluationCommand,
    features: Mapping[str, object],
) -> bool:
    return (
        command.high_risk_context
        or command.private_grant_id is not None
        or _feature_truthy(features, "private_plan")
        or _feature_at_least(features, {"discount_percent", "discount_percentage"}, Decimal("100"))
    )


def _feature_truthy(features: Mapping[str, object], key_part: str) -> bool:
    for key, value in _walk_feature_items(features):
        if key_part in key.lower() and value is True:
            return True
    return False


def _feature_at_least(features: Mapping[str, object], key_parts: set[str], threshold: Decimal) -> bool:
    for key, value in _walk_feature_items(features):
        normalized_key = key.lower()
        if not any(key_part in normalized_key for key_part in key_parts):
            continue
        try:
            if Decimal(str(value)) >= threshold:
                return True
        except (InvalidOperation, TypeError, ValueError):
            continue
    return False


def _walk_feature_items(features: Mapping[str, object], *, prefix: str = ""):
    for key, value in features.items():
        path = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, Mapping):
            yield from _walk_feature_items(value, prefix=path)
        else:
            yield path, value


def _fail_closed_model_unavailable_action(policy: GrowthRiskPolicy) -> tuple[str, bool]:
    requested_action = policy.high_risk_model_unavailable_action
    if requested_action not in RISK_ACTION_ORDER:
        return "review", True
    if RISK_ACTION_ORDER[requested_action] < RISK_ACTION_ORDER["challenge"]:
        return "review", True
    return requested_action, False


def _json_payload(value: Mapping[str, object]) -> dict[str, object]:
    return json.loads(json.dumps(dict(value), sort_keys=True, default=str))


def _source_freshness_payload(source_freshness: Mapping[str, object]) -> dict[str, object]:
    payload = _json_payload(source_freshness) if source_freshness else {}
    payload.setdefault("producer", "GrowthRiskDecisionUseCase")
    payload.setdefault("feature_schema_version", RISK_SCHEMA_VERSION)
    return payload


def _review_evidence_payload(
    *,
    command: GrowthRiskEvaluationCommand,
    result: GrowthRiskEvaluationResult,
    decision_id: UUID,
    feature_snapshot_id: UUID,
    model_version_id: UUID | None,
) -> dict[str, object]:
    return {
        "source": "growth_risk_decision",
        "growth_risk_decision_id": str(decision_id),
        "feature_snapshot_id": str(feature_snapshot_id),
        "feature_hash": result.feature_hash,
        "risk_subject_id": str(command.risk_subject_id),
        "action_context": command.action_context,
        "rules_policy_version_id": str(command.rules_policy_version_id),
        "model_version_id": str(model_version_id) if model_version_id else None,
        "rules_outcome": result.rules_outcome,
        "risk_band": result.risk_band,
        "final_action": result.final_action,
        "reason_codes": list(result.reason_codes),
        "fallback_mode": result.fallback_mode,
        "related_refs": {
            "code_set_id": str(command.code_set_id) if command.code_set_id else None,
            "growth_code_id": str(command.growth_code_id) if command.growth_code_id else None,
            "private_grant_id": str(command.private_grant_id) if command.private_grant_id else None,
            "quote_session_id": str(command.quote_session_id) if command.quote_session_id else None,
            "order_id": str(command.order_id) if command.order_id else None,
        },
    }
