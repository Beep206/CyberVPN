from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest

from src.application.use_cases.growth_risk import (
    GrowthRiskDecisionUseCase,
    GrowthRiskEvaluationCommand,
    GrowthRiskModelMetadata,
    GrowthRiskModelUnavailable,
    GrowthRiskPolicy,
    GrowthRiskPrediction,
)


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
async def test_growth_risk_model_unavailable_allows_rules_only_for_low_risk_context() -> None:
    result = await GrowthRiskDecisionUseCase(UnavailableRiskModel()).execute(
        _command(
            high_risk_context=False,
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
