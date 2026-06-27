from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from src.application.use_cases.growth_risk import (
    GrowthRiskDecisionUseCase,
    GrowthRiskEvaluationCommand,
    GrowthRiskModelMetadata,
    GrowthRiskModelUnavailable,
    GrowthRiskPolicy,
    GrowthRiskPrediction,
)
from src.application.use_cases.growth_risk.evaluate import RISK_SCHEMA_VERSION
from src.application.use_cases.growth_risk.runtime_guard import (
    GrowthRiskRuntimeBlockedError,
    evaluate_growth_runtime_risk,
)
from src.infrastructure.database.models.growth_risk_fx_model import (
    GrowthRiskDecisionModel,
    RiskFeatureSnapshotModel,
    RiskModelVersionModel,
)
from src.infrastructure.database.models.policy_version_model import PolicyVersionModel
from src.infrastructure.database.models.risk_review_model import RiskReviewModel
from src.infrastructure.database.models.risk_subject_model import RiskSubjectModel


class StaticRiskModel:
    def __init__(self, prediction: GrowthRiskPrediction) -> None:
        self.prediction = prediction
        self.seen_features = None

    async def score(self, *, features):
        self.seen_features = features
        return self.prediction


class UnavailableRiskModel:
    async def score(self, *, features):
        _ = features
        raise GrowthRiskModelUnavailable("timeout")


async def _seed_risk_persistence(db, *, deployment_mode: str = "champion"):
    suffix = uuid4().hex
    subject = RiskSubjectModel(
        id=uuid4(),
        principal_class="customer",
        principal_subject=f"customer-{suffix}",
        status="active",
        risk_level="low",
        metadata_payload={},
    )
    policy = PolicyVersionModel(
        id=uuid4(),
        policy_family="growth_risk",
        policy_key=f"growth-risk-v6-{suffix}",
        subject_type="platform",
        subject_id=None,
        version_number=1,
        payload={"rules_policy_version": "growth-risk.v6.rules.v1"},
        approval_state="approved",
        version_status="active",
        effective_from=datetime.now(UTC),
    )
    model = RiskModelVersionModel(
        id=uuid4(),
        model_key="growth-fraud",
        version=f"v6-{suffix}",
        artifact_uri=f"s3://risk-models/growth-fraud/{suffix}/artifact.json",
        artifact_checksum=f"sha256:{suffix}",
        feature_schema_version=RISK_SCHEMA_VERSION,
        model_type="gradient_boosted_trees",
        metrics={"auc": "0.91"},
        calibration={"window": "2026q2"},
        deployment_mode=deployment_mode,
        approval_state="approved",
        status="active",
    )
    db.add_all([subject, policy, model])
    await db.flush()
    return subject, policy, model


def _command(**overrides) -> GrowthRiskEvaluationCommand:
    base = {
        "risk_subject_id": uuid4(),
        "action_context": "private_catalog_preflight",
        "features": {
            "account_age_hours": 1,
            "commercial": {"discount_percent": "100", "private_plan": True},
        },
        "high_risk_context": True,
        "private_grant_id": uuid4(),
        "policy": GrowthRiskPolicy(),
    }
    base.update(overrides)
    return GrowthRiskEvaluationCommand(**base)


@pytest.mark.asyncio
async def test_growth_risk_hard_deny_overrides_low_ml_score() -> None:
    use_case = GrowthRiskDecisionUseCase(
        StaticRiskModel(
            GrowthRiskPrediction(
                score=Decimal("0.01"),
                reason_codes=("MODEL_LOW_RISK",),
                model=GrowthRiskModelMetadata(
                    model_key="growth-fraud",
                    version="v6",
                    artifact_checksum="sha256:test",
                ),
            )
        )
    )

    result = await use_case.execute(
        _command(
            hard_deny_reason_codes=("REFERRAL_SELF_LINK",),
            high_risk_context=False,
        )
    )

    assert result.rules_outcome == "deny"
    assert result.final_action == "deny"
    assert result.risk_band == "low"
    assert result.reason_codes == ("REFERRAL_SELF_LINK", "MODEL_LOW_RISK")


@pytest.mark.asyncio
async def test_growth_risk_score_thresholds_choose_challenge_or_review() -> None:
    high = await GrowthRiskDecisionUseCase(
        StaticRiskModel(GrowthRiskPrediction(score=Decimal("0.72"), reason_codes=("DEVICE_VELOCITY",)))
    ).execute(_command(high_risk_context=False))
    critical = await GrowthRiskDecisionUseCase(
        StaticRiskModel(GrowthRiskPrediction(score=Decimal("0.94"), reason_codes=("ZERO_PAY_PRIVATE_PLAN",)))
    ).execute(_command(high_risk_context=False))

    assert high.risk_band == "high"
    assert high.final_action == "challenge"
    assert critical.risk_band == "critical"
    assert critical.final_action == "review"


@pytest.mark.asyncio
async def test_growth_risk_score_can_choose_deny() -> None:
    result = await GrowthRiskDecisionUseCase(
        StaticRiskModel(GrowthRiskPrediction(score=Decimal("0.991"), reason_codes=("MODEL_DENY_SIGNAL",)))
    ).execute(_command(high_risk_context=False))

    assert result.risk_band == "critical"
    assert result.final_action == "deny"
    assert "MODEL_DENY_SIGNAL" in result.reason_codes
    assert result.decision_trace["model_candidate_action"] == "deny"


@pytest.mark.asyncio
async def test_growth_risk_model_unavailable_fails_closed_for_high_risk_private_context() -> None:
    result = await GrowthRiskDecisionUseCase(UnavailableRiskModel()).execute(
        _command(
            high_risk_context=True,
            policy=GrowthRiskPolicy(high_risk_model_unavailable_action="review"),
        )
    )

    assert result.final_action == "review"
    assert result.fallback_mode == "model_unavailable_fail_closed"
    assert "MODEL_UNAVAILABLE" in result.reason_codes
    assert result.feature_snapshot["commercial"] == {"discount_percent": "100", "private_plan": True}


@pytest.mark.asyncio
async def test_growth_risk_model_unavailable_fails_closed_for_private_or_full_discount_even_if_policy_allows() -> None:
    result = await GrowthRiskDecisionUseCase(UnavailableRiskModel()).execute(
        _command(
            high_risk_context=False,
            private_grant_id=None,
            features={"commercial": {"discount_percent": "100", "private_plan": True}},
            policy=GrowthRiskPolicy(high_risk_model_unavailable_action="allow"),
        )
    )

    assert result.final_action == "review"
    assert result.fallback_mode == "model_unavailable_fail_closed"
    assert result.decision_trace["high_risk_context"] is True
    assert "MODEL_UNAVAILABLE_POLICY_ESCALATED" in result.reason_codes


@pytest.mark.asyncio
async def test_growth_risk_model_unavailable_allows_rules_only_for_low_risk_context() -> None:
    result = await GrowthRiskDecisionUseCase(UnavailableRiskModel()).execute(
        _command(
            high_risk_context=False,
            private_grant_id=None,
            features={"account_age_hours": 720, "commercial": {"discount_percent": "10"}},
        )
    )

    assert result.final_action == "allow"
    assert result.fallback_mode == "model_unavailable_rules_only"
    assert "MODEL_UNAVAILABLE" in result.reason_codes


@pytest.mark.asyncio
async def test_growth_risk_shadow_model_does_not_affect_rules_decision() -> None:
    result = await GrowthRiskDecisionUseCase(
        StaticRiskModel(
            GrowthRiskPrediction(
                score=Decimal("0.98"),
                reason_codes=("SHADOW_DENY_SIGNAL",),
                model=GrowthRiskModelMetadata(
                    model_key="growth-fraud",
                    version="challenger",
                    artifact_checksum="sha256:shadow",
                    deployment_mode="shadow",
                ),
            )
        )
    ).execute(_command(high_risk_context=False))

    assert result.rules_outcome == "allow"
    assert result.final_action == "allow"
    assert result.fallback_mode == "shadow_model_no_effect"
    assert result.decision_trace["model_deployment_mode"] == "shadow"
    assert "SHADOW_DENY_SIGNAL" in result.reason_codes


@pytest.mark.asyncio
async def test_growth_risk_challenger_model_does_not_affect_rules_decision() -> None:
    result = await GrowthRiskDecisionUseCase(
        StaticRiskModel(
            GrowthRiskPrediction(
                score=Decimal("0.991"),
                reason_codes=("CHALLENGER_DENY_SIGNAL",),
                model=GrowthRiskModelMetadata(
                    model_key="growth-fraud",
                    version="challenger",
                    artifact_checksum="sha256:challenger",
                    deployment_mode="challenger",
                ),
            )
        )
    ).execute(
        _command(high_risk_context=False, private_grant_id=None, features={"commercial": {"discount_percent": "5"}})
    )

    assert result.rules_outcome == "allow"
    assert result.final_action == "allow"
    assert result.fallback_mode == "challenger_model_no_effect"
    assert result.decision_trace["model_candidate_action"] == "deny"
    assert "CHALLENGER_DENY_SIGNAL" in result.reason_codes


@pytest.mark.asyncio
async def test_growth_risk_feature_snapshot_drops_raw_pii_before_model_call() -> None:
    model = StaticRiskModel(GrowthRiskPrediction(score=Decimal("0.10")))

    result = await GrowthRiskDecisionUseCase(model).execute(
        _command(
            high_risk_context=False,
            features={
                "account_email": "customer@example.test",
                "full_ip": "203.0.113.10",
                "raw_code": "PR-PRO100-INV10",
                "account_age_hours": 1,
                "commercial": {"private_plan": True, "raw_code": "PR-RU90-ACCESS"},
            },
        )
    )

    assert "account_email" not in result.feature_snapshot
    assert "full_ip" not in result.feature_snapshot
    assert "raw_code" not in result.feature_snapshot
    assert result.feature_snapshot["commercial"] == {"private_plan": True}
    assert "PR-PRO100-INV10" not in str(result.feature_snapshot)
    assert "PR-RU90-ACCESS" not in str(model.seen_features)
    assert "PRIVACY_FEATURES_DROPPED" in result.reason_codes


@pytest.mark.asyncio
async def test_growth_risk_invalid_model_response_fails_closed() -> None:
    result = await GrowthRiskDecisionUseCase(StaticRiskModel(GrowthRiskPrediction(score=Decimal("1.50")))).execute(
        _command(high_risk_context=True)
    )

    assert result.final_action == "review"
    assert result.fallback_mode == "model_unavailable_fail_closed"
    assert "MODEL_INVALID_RESPONSE" in result.reason_codes


@pytest.mark.asyncio
async def test_growth_risk_persists_registered_model_snapshot_decision_and_manual_review(db) -> None:
    subject, policy, model = await _seed_risk_persistence(db)
    static_model = StaticRiskModel(
        GrowthRiskPrediction(
            score=Decimal("0.931"),
            reason_codes=("DEVICE_MULTI_ACCOUNT_VELOCITY", "ZERO_GATEWAY_PRIVATE_PLAN"),
            model=GrowthRiskModelMetadata(
                model_key=model.model_key,
                version=model.version,
                artifact_checksum=model.artifact_checksum,
                model_version_id=model.id,
            ),
        )
    )

    result = await GrowthRiskDecisionUseCase(static_model, session=db).execute(
        _command(
            risk_subject_id=subject.id,
            rules_policy_version_id=policy.id,
            private_grant_id=None,
            high_risk_context=False,
            features={
                "account_age_hours": 1,
                "customer_contact": "customer@example.test",
                "source_ip": "203.0.113.10",
                "entered_code": "PRIVATE100",
                "commercial": {"discount_percent": "100", "private_plan": True},
            },
            source_freshness={"account": "fresh", "velocity": "cached_30s"},
        )
    )

    assert result.final_action == "review"
    assert result.model is not None
    assert result.model.model_version_id == model.id
    assert result.feature_snapshot_id is not None
    assert result.decision_id is not None
    assert result.risk_review_id is not None

    snapshot = await db.get(RiskFeatureSnapshotModel, result.feature_snapshot_id)
    decision = await db.get(GrowthRiskDecisionModel, result.decision_id)
    review = await db.get(RiskReviewModel, result.risk_review_id)
    assert snapshot is not None
    assert decision is not None
    assert review is not None
    assert snapshot.feature_hash == result.feature_hash
    assert snapshot.feature_schema_version == RISK_SCHEMA_VERSION
    assert snapshot.source_freshness["producer"] == "GrowthRiskDecisionUseCase"
    assert snapshot.source_freshness["account"] == "fresh"
    assert snapshot.features_payload["customer_contact"]["redacted"] == "email_hash"
    assert snapshot.features_payload["source_ip"]["redacted"] == "ip_hash"
    assert snapshot.features_payload["entered_code"]["redacted"] == "code_or_token_hash"

    persisted_payload = json.dumps(
        {
            "features": snapshot.features_payload,
            "decision_trace": decision.decision_trace,
            "review_evidence": review.evidence,
        },
        sort_keys=True,
        default=str,
    )
    assert "customer@example.test" not in persisted_payload
    assert "203.0.113.10" not in persisted_payload
    assert "PRIVATE100" not in persisted_payload
    assert "customer@example.test" not in str(static_model.seen_features)
    assert "PRIVATE100" not in str(static_model.seen_features)

    assert decision.risk_subject_id == subject.id
    assert decision.rules_policy_version_id == policy.id
    assert decision.model_version_id == model.id
    assert decision.feature_snapshot_id == snapshot.id
    assert decision.ml_score == Decimal("0.931000")
    assert decision.final_action == "review"
    assert decision.reason_codes == ["DEVICE_MULTI_ACCOUNT_VELOCITY", "ZERO_GATEWAY_PRIVATE_PLAN"]
    assert decision.decision_trace["feature_snapshot_id"] == str(snapshot.id)
    assert decision.decision_trace["model_version_id"] == str(model.id)

    assert review.status == "open"
    assert review.decision == "pending"
    assert review.review_type == "growth_risk_manual_review"
    assert review.evidence["growth_risk_decision_id"] == str(decision.id)
    assert review.evidence["feature_hash"] == result.feature_hash
    assert review.evidence["reason_codes"] == list(result.reason_codes)


@pytest.mark.asyncio
async def test_growth_risk_registry_checksum_mismatch_persists_fail_closed_fallback_without_model_link(db) -> None:
    subject, policy, model = await _seed_risk_persistence(db)

    result = await GrowthRiskDecisionUseCase(
        StaticRiskModel(
            GrowthRiskPrediction(
                score=Decimal("0.12"),
                reason_codes=("MODEL_LOW_RISK",),
                model=GrowthRiskModelMetadata(
                    model_key=model.model_key,
                    version=model.version,
                    artifact_checksum="sha256:tampered",
                    model_version_id=model.id,
                ),
            )
        ),
        session=db,
    ).execute(
        _command(
            risk_subject_id=subject.id,
            rules_policy_version_id=policy.id,
            private_grant_id=None,
            high_risk_context=False,
            features={"commercial": {"discount_percent": "100", "private_plan": True}},
        )
    )

    assert result.final_action == "review"
    assert result.ml_score is None
    assert result.model is None
    assert result.decision_id is not None
    assert result.risk_review_id is not None
    assert "MODEL_REGISTRY_CHECKSUM_MISMATCH" in result.reason_codes

    decision = await db.get(GrowthRiskDecisionModel, result.decision_id)
    review = await db.get(RiskReviewModel, result.risk_review_id)
    assert decision is not None
    assert review is not None
    assert decision.model_version_id is None
    assert decision.final_action == "review"
    assert decision.fallback_mode == "model_unavailable_fail_closed"
    assert review.evidence["growth_risk_decision_id"] == str(decision.id)

    decisions = (
        (await db.execute(select(GrowthRiskDecisionModel).where(GrowthRiskDecisionModel.risk_subject_id == subject.id)))
        .scalars()
        .all()
    )
    assert [item.id for item in decisions] == [decision.id]


@pytest.mark.asyncio
async def test_growth_runtime_guard_persists_allow_decision_for_checkout_checkpoint(db) -> None:
    user_id = uuid4()

    result = await evaluate_growth_runtime_risk(
        session=db,
        action_context="checkout_eval",
        user_id=user_id,
        high_risk_context=False,
        features={
            "zero_gateway": False,
            "private_catalog": False,
            "stacking_count": 1,
        },
        enforce=True,
    )

    assert result.decision.final_action == "allow"
    assert result.decision.decision_id is not None
    assert result.decision.feature_snapshot_id is not None
    decision = await db.get(GrowthRiskDecisionModel, result.decision.decision_id)
    snapshot = await db.get(RiskFeatureSnapshotModel, result.decision.feature_snapshot_id)
    subject = await db.get(RiskSubjectModel, result.decision.risk_subject_id)
    assert decision is not None
    assert snapshot is not None
    assert subject is not None
    assert subject.principal_class == "customer"
    assert subject.principal_subject == str(user_id)
    assert decision.action_context == "checkout_eval"
    assert decision.final_action == "allow"
    assert snapshot.features_payload["checkpoint"] == "checkout_eval"
    assert snapshot.features_payload["runtime_model_id"]


@pytest.mark.asyncio
async def test_growth_runtime_guard_blocks_high_risk_checkpoint_and_persists_review(db) -> None:
    with pytest.raises(GrowthRiskRuntimeBlockedError) as blocked:
        await evaluate_growth_runtime_risk(
            session=db,
            action_context="zero_settlement",
            user_id=uuid4(),
            high_risk_context=True,
            features={
                "zero_gateway": True,
                "private_catalog": True,
                "force_review": True,
                "stacking_count": 2,
            },
            enforce=True,
        )

    assert blocked.value.action == "review"
    assert blocked.value.decision_id is not None
    assert "DEVICE_MULTI_ACCOUNT_VELOCITY" in blocked.value.reason_codes
    decision = await db.get(GrowthRiskDecisionModel, blocked.value.decision_id)
    assert decision is not None
    assert decision.action_context == "zero_settlement"
    assert decision.final_action == "review"
    assert decision.risk_band == "critical"
