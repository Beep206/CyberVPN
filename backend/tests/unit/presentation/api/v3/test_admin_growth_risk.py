from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from src.domain.enums import AdminRole, RiskReviewDecision, RiskReviewStatus
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.audit_log_model import AuditLog
from src.infrastructure.database.models.growth_risk_fx_model import (
    GrowthRiskDecisionModel,
    RiskFeatureSnapshotModel,
)
from src.infrastructure.database.models.outbox_event_model import OutboxEventModel
from src.infrastructure.database.models.policy_version_model import PolicyVersionModel
from src.infrastructure.database.models.risk_review_model import RiskReviewModel
from src.infrastructure.database.models.risk_subject_model import RiskSubjectModel
from src.presentation.api.v3.admin_growth_risk import (
    AdminGrowthRiskModelActionRequest,
    AdminGrowthRiskModelCreateRequest,
    AdminGrowthRiskReviewResolveRequest,
    approve_growth_risk_model,
    create_growth_risk_model,
    deploy_shadow_growth_risk_model,
    get_growth_risk_decision,
    list_growth_risk_decisions,
    list_growth_risk_models,
    list_growth_risk_reviews,
    promote_growth_risk_model,
    resolve_growth_risk_review,
    rollback_growth_risk_model,
)

pytestmark = [pytest.mark.asyncio]


def _request(path: str) -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": path,
            "headers": [
                (b"host", b"admin.cyber-vpn.net"),
                (b"user-agent", b"pytest"),
                (b"x-request-id", b"growth-risk-test"),
            ],
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 80),
        }
    )


async def _admin_user(db: AsyncSession, *, login: str | None = None) -> AdminUserModel:
    suffix = login or f"growth-risk-admin-{uuid4().hex[:8]}"
    user = AdminUserModel(
        id=uuid4(),
        login=suffix,
        email=f"{suffix}@example.test",
        role=AdminRole.ADMIN.value,
        is_active=True,
        is_email_verified=True,
        language="en",
        timezone="UTC",
    )
    db.add(user)
    await db.flush()
    return user


async def _risk_decision_fixture(
    db: AsyncSession, admin: AdminUserModel
) -> tuple[GrowthRiskDecisionModel, RiskReviewModel]:
    now = datetime.now(UTC)
    subject = RiskSubjectModel(
        id=uuid4(),
        principal_class="customer",
        principal_subject=f"growth-risk-customer-{uuid4()}",
        status="active",
        risk_level="medium",
        metadata_payload={"test": "admin_growth_risk"},
    )
    policy = PolicyVersionModel(
        id=uuid4(),
        policy_family="growth_risk",
        policy_key=f"risk-policy-{uuid4().hex[:8]}",
        subject_type="global",
        version_number=1,
        payload={"thresholds": {"review": "0.8"}},
        approval_state="approved",
        version_status="active",
        effective_from=now - timedelta(minutes=1),
        created_by_admin_user_id=admin.id,
        approved_by_admin_user_id=admin.id,
        approved_at=now,
    )
    feature_payload = {
        "order_count_24h": 4,
        "shared_payment_fingerprint_count": 2,
        "test_nonce": uuid4().hex,
    }
    feature_hash = hashlib.sha256(repr(sorted(feature_payload.items())).encode("utf-8")).hexdigest()
    db.add_all([subject, policy])
    await db.flush()

    snapshot = RiskFeatureSnapshotModel(
        id=uuid4(),
        risk_subject_id=subject.id,
        feature_schema_version="growth-risk.v6.features.v1",
        features_payload=feature_payload,
        feature_hash=feature_hash,
        source_freshness={"orders": "fresh"},
        generated_at=now,
        expires_at=now + timedelta(minutes=5),
    )
    db.add(snapshot)
    await db.flush()

    decision = GrowthRiskDecisionModel(
        id=uuid4(),
        risk_subject_id=subject.id,
        action_context="checkout",
        rules_policy_version_id=policy.id,
        model_version_id=None,
        feature_snapshot_id=snapshot.id,
        rules_outcome="review",
        ml_score=Decimal("0.840000"),
        risk_band="high",
        final_action="review",
        reason_codes=["SHARED_PAYMENT_FINGERPRINT"],
        fallback_mode=None,
        decision_trace={"rules_outcome": "review", "schema_version": "growth-risk.v6.features.v1"},
        decided_at=now,
    )
    review = RiskReviewModel(
        id=uuid4(),
        risk_subject_id=subject.id,
        review_type="growth_risk_manual_review",
        status=RiskReviewStatus.OPEN.value,
        decision=RiskReviewDecision.PENDING.value,
        reason="high risk checkout decision",
        evidence={"growth_risk_decision_id": str(decision.id)},
        created_by_admin_user_id=admin.id,
    )
    db.add_all([decision, review])
    await db.flush()
    return decision, review


async def test_admin_growth_risk_model_lifecycle_has_audit_and_conflict_guards(db: AsyncSession) -> None:
    admin = await _admin_user(db)
    approver = await _admin_user(db, login=f"growth-risk-approver-{uuid4().hex[:8]}")
    model_key = f"growth-checkout-{uuid4().hex[:8]}"

    created = await create_growth_risk_model(
        AdminGrowthRiskModelCreateRequest(
            model_key=model_key,
            version="2026.06.shadow",
            artifact_uri="s3://risk-models/growth-checkout/2026.06.shadow/model.json",
            artifact_checksum="a" * 64,
            deployment_mode="shadow",
            status="inactive",
            change_reason="register shadow candidate",
        ),
        _request("/api/v3/admin/growth/risk/models"),
        current_user=admin,
        db=db,
    )
    assert created.approval_state == "draft"
    assert created.status == "inactive"

    with pytest.raises(HTTPException) as conflict:
        await approve_growth_risk_model(
            created.id,
            AdminGrowthRiskModelActionRequest(
                expected_status="active",
                change_reason="should reject stale admin state",
            ),
            _request(f"/api/v3/admin/growth/risk/models/{created.id}/approve"),
            current_user=approver,
            db=db,
        )
    assert conflict.value.status_code == 409
    assert conflict.value.detail["code"] == "RISK_MODEL_VERSION_CONFLICT"

    approved = await approve_growth_risk_model(
        created.id,
        AdminGrowthRiskModelActionRequest(
            expected_status="inactive",
            expected_approval_state="draft",
            change_reason="approve candidate after offline validation",
        ),
        _request(f"/api/v3/admin/growth/risk/models/{created.id}/approve"),
        current_user=approver,
        db=db,
    )
    assert approved.approval_state == "approved"
    assert approved.status == "active"

    shadow = await deploy_shadow_growth_risk_model(
        created.id,
        AdminGrowthRiskModelActionRequest(
            expected_approval_state="approved",
            change_reason="deploy in shadow mode",
        ),
        _request(f"/api/v3/admin/growth/risk/models/{created.id}/deploy-shadow"),
        current_user=approver,
        db=db,
    )
    assert shadow.deployment_mode == "shadow"
    assert shadow.deployed_at is not None

    replacement = await create_growth_risk_model(
        AdminGrowthRiskModelCreateRequest(
            model_key=model_key,
            version="2026.06.champion",
            artifact_uri="s3://risk-models/growth-checkout/2026.06.champion/model.json",
            artifact_checksum="b" * 64,
            deployment_mode="challenger",
            status="inactive",
            change_reason="register champion candidate",
        ),
        _request("/api/v3/admin/growth/risk/models"),
        current_user=admin,
        db=db,
    )
    await approve_growth_risk_model(
        replacement.id,
        AdminGrowthRiskModelActionRequest(
            expected_status="inactive",
            expected_approval_state="draft",
            change_reason="approve replacement candidate",
        ),
        _request(f"/api/v3/admin/growth/risk/models/{replacement.id}/approve"),
        current_user=approver,
        db=db,
    )
    promoted = await promote_growth_risk_model(
        replacement.id,
        AdminGrowthRiskModelActionRequest(
            expected_approval_state="approved",
            change_reason="promote validated candidate",
        ),
        _request(f"/api/v3/admin/growth/risk/models/{replacement.id}/promote"),
        current_user=approver,
        db=db,
    )
    assert promoted.deployment_mode == "champion"

    rolled_back = await rollback_growth_risk_model(
        replacement.id,
        AdminGrowthRiskModelActionRequest(
            expected_deployment_mode="champion",
            target_model_id=created.id,
            change_reason="rollback after degraded precision signal",
        ),
        _request(f"/api/v3/admin/growth/risk/models/{replacement.id}/rollback"),
        current_user=approver,
        db=db,
    )
    assert rolled_back.id == created.id
    assert rolled_back.deployment_mode == "champion"

    models = await list_growth_risk_models(
        model_key=model_key,
        status_filter=None,
        deployment_mode=None,
        limit=50,
        offset=0,
        _current_user=admin,
        db=db,
    )
    assert models.total == 2
    assert {item.version for item in models.items} == {"2026.06.shadow", "2026.06.champion"}

    creator_actions = (
        (
            await db.execute(
                select(AuditLog.action).where(
                    AuditLog.admin_id == admin.id,
                    AuditLog.entity_type == "risk_model_version",
                )
            )
        )
        .scalars()
        .all()
    )
    approver_actions = (
        (
            await db.execute(
                select(AuditLog.action).where(
                    AuditLog.admin_id == approver.id,
                    AuditLog.entity_type == "risk_model_version",
                )
            )
        )
        .scalars()
        .all()
    )
    assert "growth_risk_model.created" in creator_actions
    assert "growth_risk_model.approved" in approver_actions
    assert "growth_risk_model.deployed_shadow" in approver_actions
    assert "growth_risk_model.promoted" in approver_actions
    assert "growth_risk_model.rolled_back" in approver_actions


async def test_admin_growth_risk_model_rejects_self_approval_and_promotion(db: AsyncSession) -> None:
    admin = await _admin_user(db)
    checker = await _admin_user(db, login=f"growth-risk-checker-{uuid4().hex[:8]}")
    model_key = f"growth-self-check-{uuid4().hex[:8]}"
    created = await create_growth_risk_model(
        AdminGrowthRiskModelCreateRequest(
            model_key=model_key,
            version="2026.06.self-check",
            artifact_uri="s3://risk-models/growth/self-check/model.json",
            artifact_checksum="c" * 64,
            deployment_mode="shadow",
            status="inactive",
            change_reason="register candidate for maker checker test",
        ),
        _request("/api/v3/admin/growth/risk/models"),
        current_user=admin,
        db=db,
    )

    with pytest.raises(HTTPException) as self_approval:
        await approve_growth_risk_model(
            created.id,
            AdminGrowthRiskModelActionRequest(
                expected_status="inactive",
                expected_approval_state="draft",
                change_reason="self approval must fail",
            ),
            _request(f"/api/v3/admin/growth/risk/models/{created.id}/approve"),
            current_user=admin,
            db=db,
        )
    assert self_approval.value.status_code == 409
    assert self_approval.value.detail["code"] == "RISK_MODEL_MAKER_CHECKER_REQUIRED"

    await approve_growth_risk_model(
        created.id,
        AdminGrowthRiskModelActionRequest(
            expected_status="inactive",
            expected_approval_state="draft",
            change_reason="checker approval",
        ),
        _request(f"/api/v3/admin/growth/risk/models/{created.id}/approve"),
        current_user=checker,
        db=db,
    )
    with pytest.raises(HTTPException) as self_promotion:
        await promote_growth_risk_model(
            created.id,
            AdminGrowthRiskModelActionRequest(
                expected_approval_state="approved",
                change_reason="creator promotion must fail",
            ),
            _request(f"/api/v3/admin/growth/risk/models/{created.id}/promote"),
            current_user=admin,
            db=db,
        )
    assert self_promotion.value.status_code == 409
    assert self_promotion.value.detail["code"] == "RISK_MODEL_MAKER_CHECKER_REQUIRED"


async def test_admin_growth_risk_decision_and_review_facade_resolves_with_outbox_and_audit(
    db: AsyncSession,
) -> None:
    admin = await _admin_user(db)
    decision, review = await _risk_decision_fixture(db, admin)

    decisions = await list_growth_risk_decisions(
        risk_subject_id=decision.risk_subject_id,
        final_action="review",
        model_version_id=None,
        limit=50,
        offset=0,
        _current_user=admin,
        db=db,
    )
    assert decisions.total == 1
    assert decisions.items[0].id == decision.id
    assert decisions.items[0].reason_codes == ["SHARED_PAYMENT_FINGERPRINT"]
    assert decisions.items[0].ml_score == "0.840000"

    detail = await get_growth_risk_decision(decision.id, _current_user=admin, db=db)
    assert detail.feature_snapshot is not None
    assert detail.feature_snapshot["features_payload"]["order_count_24h"] == 4
    assert detail.feature_snapshot["features_payload"]["shared_payment_fingerprint_count"] == 2
    assert "test_nonce" in detail.feature_snapshot["features_payload"]
    assert detail.decision_trace["rules_outcome"] == "review"

    reviews = await list_growth_risk_reviews(
        status_filter="open",
        decision=None,
        risk_subject_id=decision.risk_subject_id,
        review_type="growth_risk_manual_review",
        limit=50,
        offset=0,
        _current_user=admin,
        db=db,
    )
    assert reviews.total == 1
    assert reviews.items[0].id == review.id

    resolved = await resolve_growth_risk_review(
        review.id,
        AdminGrowthRiskReviewResolveRequest(
            decision=RiskReviewDecision.MONITOR,
            resolution_status=RiskReviewStatus.RESOLVED,
            resolution_reason="manual review found no confirmed abuse",
            resolution_evidence={"ticket_id": "RISK-42"},
        ),
        _request(f"/api/v3/admin/growth/risk/reviews/{review.id}/resolve"),
        current_user=admin,
        db=db,
    )
    assert resolved.status == RiskReviewStatus.RESOLVED.value
    assert resolved.decision == RiskReviewDecision.MONITOR.value
    assert resolved.resolved_by_admin_user_id == admin.id
    assert resolved.evidence["resolution_evidence"] == {"ticket_id": "RISK-42"}

    audit_actions = (
        (
            await db.execute(
                select(AuditLog.action).where(
                    AuditLog.admin_id == admin.id,
                    AuditLog.entity_type == "risk_review",
                )
            )
        )
        .scalars()
        .all()
    )
    assert audit_actions == ["growth_risk_review.resolved"]

    outbox_events = (
        (
            await db.execute(
                select(OutboxEventModel.event_name)
                .where(OutboxEventModel.aggregate_id == str(review.id))
                .order_by(OutboxEventModel.created_at.asc())
            )
        )
        .scalars()
        .all()
    )
    assert "risk.decision.recorded" in outbox_events
    assert "risk.review.resolved" in outbox_events
