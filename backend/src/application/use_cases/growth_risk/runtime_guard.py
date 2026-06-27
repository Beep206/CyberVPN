from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.growth_risk.evaluate import (
    RISK_SCHEMA_VERSION,
    GrowthRiskDecisionUseCase,
    GrowthRiskEvaluationCommand,
    GrowthRiskEvaluationResult,
    GrowthRiskModelMetadata,
    GrowthRiskPolicy,
    GrowthRiskPrediction,
)
from src.infrastructure.database.models.growth_risk_fx_model import RiskModelVersionModel
from src.infrastructure.database.models.policy_version_model import PolicyVersionModel
from src.infrastructure.database.models.risk_subject_model import RiskSubjectModel
from src.infrastructure.monitoring.metrics import growth_v6_runtime_risk_decisions_total

DEFAULT_RUNTIME_RISK_POLICY_KEY = "growth-v6-runtime-default"
DEFAULT_RUNTIME_RISK_MODEL_KEY = "growth-fraud"
DEFAULT_RUNTIME_RISK_MODEL_VERSION = "runtime-v6-deterministic"
DEFAULT_RUNTIME_RISK_MODEL_CHECKSUM = hashlib.sha256(b"cybervpn-growth-v6-runtime-risk-model").hexdigest()


class GrowthRiskRuntimeBlockedError(ValueError):
    def __init__(self, *, action: str, decision_id: UUID | None, reason_codes: tuple[str, ...]) -> None:
        super().__init__("GROWTH_RISK_REVIEW_REQUIRED")
        self.action = action
        self.decision_id = decision_id
        self.reason_codes = reason_codes


@dataclass(frozen=True, slots=True)
class GrowthRiskRuntimeGuardResult:
    decision: GrowthRiskEvaluationResult


class RuntimeGrowthRiskModelClient:
    async def score(self, *, features: Mapping[str, object]) -> GrowthRiskPrediction:
        score = Decimal("0.120000")
        reasons: list[str] = []
        if _bool_feature(features, "hard_deny"):
            score = Decimal("0.990000")
            reasons.append("HARD_DENY_SIGNAL")
        elif _bool_feature(features, "force_review") or _bool_feature(features, "model_review_signal"):
            score = Decimal("0.931000")
            reasons.extend(("DEVICE_MULTI_ACCOUNT_VELOCITY", "ZERO_GATEWAY_PRIVATE_PLAN"))
        elif _bool_feature(features, "zero_gateway") and _bool_feature(features, "private_catalog"):
            score = Decimal("0.320000")
            reasons.append("ZERO_GATEWAY_PRIVATE_PLAN")
        elif _int_feature(features, "stacking_count") > 1:
            score = Decimal("0.260000")
            reasons.append("MULTI_CODE_STACKING")

        return GrowthRiskPrediction(
            score=score,
            reason_codes=tuple(reasons),
            model=GrowthRiskModelMetadata(
                model_key=DEFAULT_RUNTIME_RISK_MODEL_KEY,
                version=DEFAULT_RUNTIME_RISK_MODEL_VERSION,
                artifact_checksum=DEFAULT_RUNTIME_RISK_MODEL_CHECKSUM,
                feature_schema_version=RISK_SCHEMA_VERSION,
                deployment_mode="champion",
            ),
        )


async def evaluate_growth_runtime_risk(
    *,
    session: AsyncSession,
    action_context: str,
    user_id: UUID | None,
    auth_realm_id: UUID | None = None,
    storefront_id: UUID | None = None,
    high_risk_context: bool,
    features: Mapping[str, object],
    private_grant_id: UUID | None = None,
    growth_code_id: UUID | None = None,
    code_set_id: UUID | None = None,
    quote_session_id: UUID | None = None,
    order_id: UUID | None = None,
    enforce: bool = True,
) -> GrowthRiskRuntimeGuardResult:
    subject = await _get_or_create_risk_subject(
        session=session,
        user_id=user_id,
        auth_realm_id=auth_realm_id,
        storefront_id=storefront_id,
    )
    policy = await _get_or_create_default_policy(session)
    model = await _get_or_create_runtime_model(session)
    decision = await GrowthRiskDecisionUseCase(RuntimeGrowthRiskModelClient(), session=session).execute(
        GrowthRiskEvaluationCommand(
            risk_subject_id=subject.id,
            action_context=action_context[:30],
            features={
                **dict(features),
                "runtime_model_id": str(model.id),
                "checkpoint": action_context,
            },
            policy=GrowthRiskPolicy(
                allow_threshold=Decimal("0.40"),
                challenge_threshold=Decimal("0.70"),
                review_threshold=Decimal("0.90"),
                deny_threshold=Decimal("0.98"),
                high_risk_model_unavailable_action="review",
                low_risk_model_unavailable_action="allow",
            ),
            rules_policy_version_id=policy.id,
            high_risk_context=high_risk_context,
            private_grant_id=private_grant_id,
            growth_code_id=growth_code_id,
            code_set_id=code_set_id,
            quote_session_id=quote_session_id,
            order_id=order_id,
            hard_deny_reason_codes=("RUNTIME_HARD_DENY",) if _bool_feature(features, "hard_deny") else (),
            generated_at=datetime.now(UTC),
        )
    )
    growth_v6_runtime_risk_decisions_total.labels(
        action_context=action_context[:30],
        final_action=decision.final_action,
    ).inc()
    if enforce and decision.final_action != "allow":
        raise GrowthRiskRuntimeBlockedError(
            action=decision.final_action,
            decision_id=decision.decision_id,
            reason_codes=decision.reason_codes,
        )
    return GrowthRiskRuntimeGuardResult(decision=decision)


async def _get_or_create_risk_subject(
    *,
    session: AsyncSession,
    user_id: UUID | None,
    auth_realm_id: UUID | None,
    storefront_id: UUID | None,
) -> RiskSubjectModel:
    principal_class = "customer" if user_id is not None else "anonymous_customer"
    principal_subject = str(user_id) if user_id is not None else f"anonymous:{auth_realm_id or 'global'}"
    statement = select(RiskSubjectModel).where(
        RiskSubjectModel.principal_class == principal_class,
        RiskSubjectModel.principal_subject == principal_subject,
    )
    if auth_realm_id is None:
        statement = statement.where(RiskSubjectModel.auth_realm_id.is_(None))
    else:
        statement = statement.where(RiskSubjectModel.auth_realm_id == auth_realm_id)
    existing = (await session.execute(statement)).scalars().first()
    if existing is not None:
        return existing

    subject = RiskSubjectModel(
        principal_class=principal_class,
        principal_subject=principal_subject,
        auth_realm_id=auth_realm_id,
        storefront_id=storefront_id,
        status="active",
        risk_level="low",
        metadata_payload={"source": "growth_v6_runtime_guard"},
    )
    session.add(subject)
    await session.flush()
    return subject


async def _get_or_create_default_policy(session: AsyncSession) -> PolicyVersionModel:
    existing = (
        (
            await session.execute(
                select(PolicyVersionModel).where(
                    PolicyVersionModel.policy_family == "growth_risk",
                    PolicyVersionModel.policy_key == DEFAULT_RUNTIME_RISK_POLICY_KEY,
                    PolicyVersionModel.version_number == 1,
                )
            )
        )
        .scalars()
        .first()
    )
    if existing is not None:
        return existing
    policy = PolicyVersionModel(
        policy_family="growth_risk",
        policy_key=DEFAULT_RUNTIME_RISK_POLICY_KEY,
        subject_type="global",
        version_number=1,
        payload={
            "thresholds": {"allow": "0.40", "challenge": "0.70", "review": "0.90", "deny": "0.98"},
            "model_key": DEFAULT_RUNTIME_RISK_MODEL_KEY,
        },
        approval_state="approved",
        version_status="active",
        effective_from=datetime.now(UTC),
        approved_at=datetime.now(UTC),
    )
    session.add(policy)
    await session.flush()
    return policy


async def _get_or_create_runtime_model(session: AsyncSession) -> RiskModelVersionModel:
    existing = (
        (
            await session.execute(
                select(RiskModelVersionModel).where(
                    RiskModelVersionModel.model_key == DEFAULT_RUNTIME_RISK_MODEL_KEY,
                    RiskModelVersionModel.version == DEFAULT_RUNTIME_RISK_MODEL_VERSION,
                )
            )
        )
        .scalars()
        .first()
    )
    if existing is not None:
        return existing
    model = RiskModelVersionModel(
        model_key=DEFAULT_RUNTIME_RISK_MODEL_KEY,
        version=DEFAULT_RUNTIME_RISK_MODEL_VERSION,
        artifact_uri="internal://growth-risk/runtime-v6-deterministic",
        artifact_checksum=DEFAULT_RUNTIME_RISK_MODEL_CHECKSUM,
        feature_schema_version=RISK_SCHEMA_VERSION,
        model_type="deterministic_runtime_guard",
        metrics={"source": "runtime_guard"},
        calibration={"source": "runtime_guard"},
        deployment_mode="champion",
        approval_state="approved",
        status="active",
        deployed_at=datetime.now(UTC),
    )
    session.add(model)
    await session.flush()
    return model


def _bool_feature(features: Mapping[str, object], key: str) -> bool:
    return features.get(key) is True


def _int_feature(features: Mapping[str, object], key: str) -> int:
    value = features.get(key)
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if not isinstance(value, str):
        return 0
    try:
        return int(value or "0")
    except ValueError:
        return 0
