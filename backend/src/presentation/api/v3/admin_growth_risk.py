from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.auth.permissions import Permission
from src.application.use_cases.growth_risk.evaluate import RISK_SCHEMA_VERSION
from src.application.use_cases.risk import ResolveRiskReviewUseCase
from src.domain.enums import RiskReviewDecision, RiskReviewStatus
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.growth_risk_fx_model import (
    GrowthRiskDecisionModel,
    RiskFeatureSnapshotModel,
    RiskModelVersionModel,
)
from src.infrastructure.database.models.risk_review_model import RiskReviewModel
from src.presentation.api.v1.admin.audit import write_required_admin_audit_entry
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_permission

router = APIRouter(prefix="/admin/growth/risk", tags=["admin-growth-risk-v3"])

_MODEL_STATUSES = {"inactive", "active", "retired"}
_APPROVAL_STATES = {"draft", "approved", "rejected"}
_DEPLOYMENT_MODES = {"shadow", "challenger", "champion", "retired"}


class AdminGrowthRiskModelCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_key: str = Field(..., min_length=2, max_length=100)
    version: str = Field(..., min_length=1, max_length=80)
    artifact_uri: str = Field(..., min_length=1, max_length=2000)
    artifact_checksum: str = Field(..., min_length=16, max_length=128)
    feature_schema_version: str = Field(default=RISK_SCHEMA_VERSION, min_length=1, max_length=60)
    model_type: str = Field(default="gradient_boosted_trees", min_length=1, max_length=40)
    training_window_start: datetime | None = None
    training_window_end: datetime | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    calibration: dict[str, Any] = Field(default_factory=dict)
    deployment_mode: Literal["shadow", "challenger"] = "shadow"
    status: Literal["inactive", "active"] = "inactive"
    change_reason: str = Field(..., min_length=3, max_length=2000)

    @field_validator("model_key", "version", "model_type", "feature_schema_version")
    @classmethod
    def _strip_identifier(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("value must not be blank")
        return stripped


class AdminGrowthRiskModelActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    change_reason: str = Field(..., min_length=3, max_length=2000)
    expected_status: Literal["inactive", "active", "retired"] | None = None
    expected_approval_state: Literal["draft", "approved", "rejected"] | None = None
    expected_deployment_mode: Literal["shadow", "challenger", "champion", "retired"] | None = None
    target_model_id: UUID | None = None


class AdminGrowthRiskReviewResolveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: RiskReviewDecision
    resolution_status: RiskReviewStatus = RiskReviewStatus.RESOLVED
    resolution_reason: str = Field(..., min_length=3, max_length=2000)
    resolution_evidence: dict[str, Any] = Field(default_factory=dict)


class AdminGrowthRiskModelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    model_key: str
    version: str
    artifact_uri: str
    artifact_checksum: str
    feature_schema_version: str
    model_type: str
    training_window_start: datetime | None
    training_window_end: datetime | None
    metrics: dict[str, Any]
    calibration: dict[str, Any]
    deployment_mode: str
    approval_state: str
    status: str
    created_by: UUID | None
    approved_by: UUID | None
    created_at: datetime
    deployed_at: datetime | None
    retired_at: datetime | None


class AdminGrowthRiskModelListResponse(BaseModel):
    items: list[AdminGrowthRiskModelResponse]
    total: int
    limit: int
    offset: int


class AdminGrowthRiskDecisionSummaryResponse(BaseModel):
    id: UUID
    risk_subject_id: UUID
    code_set_id: UUID | None
    growth_code_id: UUID | None
    private_grant_id: UUID | None
    quote_session_id: UUID | None
    order_id: UUID | None
    action_context: str
    rules_policy_version_id: UUID
    model_version_id: UUID | None
    feature_snapshot_id: UUID | None
    rules_outcome: str
    ml_score: str | None
    risk_band: str
    final_action: str
    reason_codes: list[str]
    fallback_mode: str | None
    decided_at: datetime
    created_at: datetime


class AdminGrowthRiskDecisionListResponse(BaseModel):
    items: list[AdminGrowthRiskDecisionSummaryResponse]
    total: int
    limit: int
    offset: int


class AdminGrowthRiskDecisionDetailResponse(AdminGrowthRiskDecisionSummaryResponse):
    feature_snapshot: dict[str, Any] | None
    decision_trace: dict[str, Any]


class AdminGrowthRiskReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    risk_subject_id: UUID
    review_type: str
    status: str
    decision: str
    reason: str
    evidence: dict[str, Any]
    created_by_admin_user_id: UUID | None
    resolved_by_admin_user_id: UUID | None
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AdminGrowthRiskReviewListResponse(BaseModel):
    items: list[AdminGrowthRiskReviewResponse]
    total: int
    limit: int
    offset: int


@router.get(
    "/models",
    response_model=AdminGrowthRiskModelListResponse,
)
async def list_growth_risk_models(
    model_key: str | None = Query(default=None, min_length=1, max_length=100),
    status_filter: Literal["inactive", "active", "retired"] | None = Query(default=None, alias="status"),
    deployment_mode: Literal["shadow", "challenger", "champion", "retired"] | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_RISK_MODELS_MANAGE)),
    db: AsyncSession = Depends(get_db),
) -> AdminGrowthRiskModelListResponse:
    statement = select(RiskModelVersionModel)
    statement = _filter_risk_models(
        statement,
        model_key=model_key,
        status_filter=status_filter,
        deployment_mode=deployment_mode,
    )
    total = await _count_for(statement, db)
    result = await db.execute(statement.order_by(RiskModelVersionModel.created_at.desc()).limit(limit).offset(offset))
    return AdminGrowthRiskModelListResponse(
        items=[AdminGrowthRiskModelResponse.model_validate(item) for item in result.scalars().all()],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/models",
    response_model=AdminGrowthRiskModelResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_growth_risk_model(
    payload: AdminGrowthRiskModelCreateRequest,
    request: Request,
    current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_RISK_MODELS_MANAGE)),
    db: AsyncSession = Depends(get_db),
) -> AdminGrowthRiskModelResponse:
    duplicate = await db.scalar(
        select(RiskModelVersionModel.id).where(
            RiskModelVersionModel.model_key == payload.model_key,
            RiskModelVersionModel.version == payload.version,
        )
    )
    if duplicate is not None:
        raise _admin_growth_error(
            status.HTTP_409_CONFLICT,
            "RISK_MODEL_VERSION_EXISTS",
            "admin.growth.risk.errors.modelVersionExists",
            {"model_key": payload.model_key, "version": payload.version},
        )

    model = RiskModelVersionModel(
        model_key=payload.model_key,
        version=payload.version,
        artifact_uri=payload.artifact_uri,
        artifact_checksum=payload.artifact_checksum,
        feature_schema_version=payload.feature_schema_version,
        model_type=payload.model_type,
        training_window_start=payload.training_window_start,
        training_window_end=payload.training_window_end,
        metrics=payload.metrics,
        calibration=payload.calibration,
        deployment_mode=payload.deployment_mode,
        approval_state="draft",
        status=payload.status,
        created_by=current_user.id,
    )
    db.add(model)
    await db.flush()
    await write_required_admin_audit_entry(
        db=db,
        action="growth_risk_model.created",
        resource_type="risk_model_version",
        resource_id=model.id,
        actor=current_user,
        request=request,
        details={
            "model_key": model.model_key,
            "version": model.version,
            "deployment_mode": model.deployment_mode,
            "status": model.status,
            "change_reason": payload.change_reason,
        },
    )
    return AdminGrowthRiskModelResponse.model_validate(model)


@router.post(
    "/models/{model_id}/approve",
    response_model=AdminGrowthRiskModelResponse,
)
async def approve_growth_risk_model(
    model_id: UUID,
    payload: AdminGrowthRiskModelActionRequest,
    request: Request,
    current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_RISK_MODELS_APPROVE)),
    db: AsyncSession = Depends(get_db),
) -> AdminGrowthRiskModelResponse:
    model = await _get_model_or_404(model_id, db)
    _assert_expected_model_state(model, payload)
    if model.status == "retired":
        raise _admin_growth_error(
            status.HTTP_409_CONFLICT,
            "RISK_MODEL_RETIRED",
            "admin.growth.risk.errors.modelRetired",
            {"model_id": str(model.id)},
        )
    _assert_model_maker_checker(model, current_user, action="approve")

    old_value = _model_state(model)
    model.approval_state = "approved"
    model.approved_by = current_user.id
    if model.status == "inactive":
        model.status = "active"
    await db.flush()
    await write_required_admin_audit_entry(
        db=db,
        action="growth_risk_model.approved",
        resource_type="risk_model_version",
        resource_id=model.id,
        actor=current_user,
        request=request,
        old_value=old_value,
        details={**_model_state(model), "change_reason": payload.change_reason},
    )
    return AdminGrowthRiskModelResponse.model_validate(model)


@router.post(
    "/models/{model_id}/deploy-shadow",
    response_model=AdminGrowthRiskModelResponse,
)
async def deploy_shadow_growth_risk_model(
    model_id: UUID,
    payload: AdminGrowthRiskModelActionRequest,
    request: Request,
    current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_RISK_MODELS_MANAGE)),
    db: AsyncSession = Depends(get_db),
) -> AdminGrowthRiskModelResponse:
    model = await _get_model_or_404(model_id, db)
    _assert_expected_model_state(model, payload)
    _assert_approved_model(model)
    _assert_model_maker_checker(model, current_user, action="promote")

    old_value = _model_state(model)
    model.deployment_mode = "shadow"
    model.status = "active"
    model.deployed_at = datetime.now(UTC)
    model.retired_at = None
    await db.flush()
    await write_required_admin_audit_entry(
        db=db,
        action="growth_risk_model.deployed_shadow",
        resource_type="risk_model_version",
        resource_id=model.id,
        actor=current_user,
        request=request,
        old_value=old_value,
        details={**_model_state(model), "change_reason": payload.change_reason},
    )
    return AdminGrowthRiskModelResponse.model_validate(model)


@router.post(
    "/models/{model_id}/promote",
    response_model=AdminGrowthRiskModelResponse,
)
async def promote_growth_risk_model(
    model_id: UUID,
    payload: AdminGrowthRiskModelActionRequest,
    request: Request,
    current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_RISK_MODELS_APPROVE)),
    db: AsyncSession = Depends(get_db),
) -> AdminGrowthRiskModelResponse:
    model = await _get_model_or_404(model_id, db)
    _assert_expected_model_state(model, payload)
    _assert_approved_model(model)
    _assert_model_maker_checker(model, current_user, action="promote")

    old_value = _model_state(model)
    demoted_ids = await _demote_existing_champions(db, model_key=model.model_key, except_model_id=model.id)
    model.deployment_mode = "champion"
    model.status = "active"
    model.deployed_at = datetime.now(UTC)
    model.retired_at = None
    await db.flush()
    await write_required_admin_audit_entry(
        db=db,
        action="growth_risk_model.promoted",
        resource_type="risk_model_version",
        resource_id=model.id,
        actor=current_user,
        request=request,
        old_value=old_value,
        details={
            **_model_state(model),
            "demoted_model_ids": [str(item) for item in demoted_ids],
            "change_reason": payload.change_reason,
        },
    )
    return AdminGrowthRiskModelResponse.model_validate(model)


@router.post(
    "/models/{model_id}/rollback",
    response_model=AdminGrowthRiskModelResponse,
)
async def rollback_growth_risk_model(
    model_id: UUID,
    payload: AdminGrowthRiskModelActionRequest,
    request: Request,
    current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_RISK_MODELS_APPROVE)),
    db: AsyncSession = Depends(get_db),
) -> AdminGrowthRiskModelResponse:
    model = await _get_model_or_404(model_id, db)
    _assert_expected_model_state(model, payload)
    old_value = _model_state(model)

    model.status = "retired"
    model.deployment_mode = "retired"
    model.retired_at = datetime.now(UTC)
    target_model: RiskModelVersionModel | None = None
    demoted_ids: list[UUID] = []
    if payload.target_model_id is not None:
        if payload.target_model_id == model.id:
            raise _admin_growth_error(
                status.HTTP_409_CONFLICT,
                "RISK_MODEL_ROLLBACK_TARGET_INVALID",
                "admin.growth.risk.errors.rollbackTargetInvalid",
                {"model_id": str(model.id)},
            )
        target_model = await _get_model_or_404(payload.target_model_id, db)
        if target_model.model_key != model.model_key:
            raise _admin_growth_error(
                status.HTTP_409_CONFLICT,
                "RISK_MODEL_ROLLBACK_KEY_MISMATCH",
                "admin.growth.risk.errors.rollbackKeyMismatch",
                {"model_id": str(model.id), "target_model_id": str(target_model.id)},
            )
        _assert_approved_model(target_model)
        _assert_model_maker_checker(target_model, current_user, action="rollback_target")
        demoted_ids = await _demote_existing_champions(
            db,
            model_key=model.model_key,
            except_model_id=target_model.id,
        )
        target_model.deployment_mode = "champion"
        target_model.status = "active"
        target_model.deployed_at = datetime.now(UTC)
        target_model.retired_at = None
    await db.flush()
    await write_required_admin_audit_entry(
        db=db,
        action="growth_risk_model.rolled_back",
        resource_type="risk_model_version",
        resource_id=model.id,
        actor=current_user,
        request=request,
        old_value=old_value,
        details={
            **_model_state(model),
            "target_model_id": str(target_model.id) if target_model is not None else None,
            "demoted_model_ids": [str(item) for item in demoted_ids],
            "change_reason": payload.change_reason,
        },
    )
    return AdminGrowthRiskModelResponse.model_validate(target_model or model)


@router.get(
    "/decisions",
    response_model=AdminGrowthRiskDecisionListResponse,
)
async def list_growth_risk_decisions(
    risk_subject_id: UUID | None = None,
    final_action: Literal["allow", "challenge", "review", "deny"] | None = None,
    model_version_id: UUID | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_RISK_DECISIONS_VIEW)),
    db: AsyncSession = Depends(get_db),
) -> AdminGrowthRiskDecisionListResponse:
    statement = select(GrowthRiskDecisionModel)
    if risk_subject_id is not None:
        statement = statement.where(GrowthRiskDecisionModel.risk_subject_id == risk_subject_id)
    if final_action is not None:
        statement = statement.where(GrowthRiskDecisionModel.final_action == final_action)
    if model_version_id is not None:
        statement = statement.where(GrowthRiskDecisionModel.model_version_id == model_version_id)
    total = await _count_for(statement, db)
    result = await db.execute(statement.order_by(GrowthRiskDecisionModel.decided_at.desc()).limit(limit).offset(offset))
    return AdminGrowthRiskDecisionListResponse(
        items=[_decision_summary_response(item) for item in result.scalars().all()],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/decisions/{decision_id}",
    response_model=AdminGrowthRiskDecisionDetailResponse,
)
async def get_growth_risk_decision(
    decision_id: UUID,
    _current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_RISK_DECISIONS_VIEW)),
    db: AsyncSession = Depends(get_db),
) -> AdminGrowthRiskDecisionDetailResponse:
    decision = await db.get(GrowthRiskDecisionModel, decision_id)
    if decision is None:
        raise _admin_growth_error(
            status.HTTP_404_NOT_FOUND,
            "RISK_DECISION_NOT_FOUND",
            "admin.growth.risk.errors.decisionNotFound",
            {"decision_id": str(decision_id)},
        )
    feature_snapshot = None
    if decision.feature_snapshot_id is not None:
        snapshot = await db.get(RiskFeatureSnapshotModel, decision.feature_snapshot_id)
        if snapshot is not None:
            feature_snapshot = {
                "id": str(snapshot.id),
                "risk_subject_id": str(snapshot.risk_subject_id),
                "feature_schema_version": snapshot.feature_schema_version,
                "features_payload": snapshot.features_payload,
                "feature_hash": snapshot.feature_hash,
                "source_freshness": snapshot.source_freshness,
                "generated_at": snapshot.generated_at.isoformat(),
                "expires_at": snapshot.expires_at.isoformat() if snapshot.expires_at else None,
            }
    return AdminGrowthRiskDecisionDetailResponse(
        **_decision_summary_response(decision).model_dump(),
        feature_snapshot=feature_snapshot,
        decision_trace=dict(decision.decision_trace or {}),
    )


@router.get(
    "/reviews",
    response_model=AdminGrowthRiskReviewListResponse,
)
async def list_growth_risk_reviews(
    status_filter: Literal["open", "resolved", "dismissed"] | None = Query(default=None, alias="status"),
    decision: Literal["pending", "allow", "block", "monitor", "hold"] | None = None,
    risk_subject_id: UUID | None = None,
    review_type: str | None = Query(default=None, min_length=1, max_length=40),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_RISK_DECISIONS_VIEW)),
    db: AsyncSession = Depends(get_db),
) -> AdminGrowthRiskReviewListResponse:
    statement = select(RiskReviewModel)
    if status_filter is not None:
        statement = statement.where(RiskReviewModel.status == status_filter)
    if decision is not None:
        statement = statement.where(RiskReviewModel.decision == decision)
    if risk_subject_id is not None:
        statement = statement.where(RiskReviewModel.risk_subject_id == risk_subject_id)
    if review_type is not None:
        statement = statement.where(RiskReviewModel.review_type == review_type)
    total = await _count_for(statement, db)
    result = await db.execute(statement.order_by(RiskReviewModel.created_at.desc()).limit(limit).offset(offset))
    return AdminGrowthRiskReviewListResponse(
        items=[AdminGrowthRiskReviewResponse.model_validate(item) for item in result.scalars().all()],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/reviews/{risk_review_id}/resolve",
    response_model=AdminGrowthRiskReviewResponse,
)
async def resolve_growth_risk_review(
    risk_review_id: UUID,
    payload: AdminGrowthRiskReviewResolveRequest,
    request: Request,
    current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_RISK_REVIEWS_MANAGE)),
    db: AsyncSession = Depends(get_db),
) -> AdminGrowthRiskReviewResponse:
    use_case = ResolveRiskReviewUseCase(db)
    try:
        review = await use_case.execute(
            risk_review_id=risk_review_id,
            decision=payload.decision,
            resolution_status=payload.resolution_status,
            resolution_reason=payload.resolution_reason,
            resolution_evidence=payload.resolution_evidence,
            resolved_by_admin_user_id=current_user.id,
        )
    except ValueError as exc:
        raise _admin_growth_error(
            status.HTTP_400_BAD_REQUEST,
            "RISK_REVIEW_RESOLVE_FAILED",
            "admin.growth.risk.errors.reviewResolveFailed",
            {"reason": str(exc)},
        ) from exc

    await write_required_admin_audit_entry(
        db=db,
        action="growth_risk_review.resolved",
        resource_type="risk_review",
        resource_id=review.id,
        actor=current_user,
        request=request,
        details={
            "risk_subject_id": str(review.risk_subject_id),
            "decision": review.decision,
            "status": review.status,
            "resolution_reason": payload.resolution_reason,
        },
    )
    return AdminGrowthRiskReviewResponse.model_validate(review)


def _filter_risk_models(
    statement: Select[tuple[RiskModelVersionModel]],
    *,
    model_key: str | None,
    status_filter: str | None,
    deployment_mode: str | None,
) -> Select[tuple[RiskModelVersionModel]]:
    if model_key is not None:
        statement = statement.where(RiskModelVersionModel.model_key == model_key)
    if status_filter is not None:
        statement = statement.where(RiskModelVersionModel.status == status_filter)
    if deployment_mode is not None:
        statement = statement.where(RiskModelVersionModel.deployment_mode == deployment_mode)
    return statement


async def _count_for(statement: Select[tuple[Any]], db: AsyncSession) -> int:
    count_statement = select(func.count()).select_from(statement.order_by(None).limit(None).offset(None).subquery())
    return int(await db.scalar(count_statement) or 0)


async def _get_model_or_404(model_id: UUID, db: AsyncSession) -> RiskModelVersionModel:
    model = await db.get(RiskModelVersionModel, model_id)
    if model is None:
        raise _admin_growth_error(
            status.HTTP_404_NOT_FOUND,
            "RISK_MODEL_NOT_FOUND",
            "admin.growth.risk.errors.modelNotFound",
            {"model_id": str(model_id)},
        )
    return model


def _assert_expected_model_state(
    model: RiskModelVersionModel,
    payload: AdminGrowthRiskModelActionRequest,
) -> None:
    if payload.expected_status is not None and model.status != payload.expected_status:
        raise _model_state_conflict(model, "status", payload.expected_status, model.status)
    if payload.expected_approval_state is not None and model.approval_state != payload.expected_approval_state:
        raise _model_state_conflict(model, "approval_state", payload.expected_approval_state, model.approval_state)
    if payload.expected_deployment_mode is not None and model.deployment_mode != payload.expected_deployment_mode:
        raise _model_state_conflict(model, "deployment_mode", payload.expected_deployment_mode, model.deployment_mode)


def _assert_approved_model(model: RiskModelVersionModel) -> None:
    if model.approval_state != "approved" or model.status == "retired":
        raise _admin_growth_error(
            status.HTTP_409_CONFLICT,
            "RISK_MODEL_NOT_APPROVED",
            "admin.growth.risk.errors.modelNotApproved",
            {
                "model_id": str(model.id),
                "approval_state": model.approval_state,
                "status": model.status,
            },
        )


def _assert_model_maker_checker(
    model: RiskModelVersionModel,
    current_user: AdminUserModel,
    *,
    action: str,
) -> None:
    if model.created_by == current_user.id:
        raise _admin_growth_error(
            status.HTTP_409_CONFLICT,
            "RISK_MODEL_MAKER_CHECKER_REQUIRED",
            "admin.growth.risk.errors.makerCheckerRequired",
            {"model_id": str(model.id), "action": action},
        )


def _model_state_conflict(
    model: RiskModelVersionModel,
    field: str,
    expected: str,
    actual: str,
) -> HTTPException:
    return _admin_growth_error(
        status.HTTP_409_CONFLICT,
        "RISK_MODEL_VERSION_CONFLICT",
        "admin.growth.risk.errors.modelVersionConflict",
        {
            "model_id": str(model.id),
            "field": field,
            "expected": expected,
            "actual": actual,
        },
    )


async def _demote_existing_champions(
    db: AsyncSession,
    *,
    model_key: str,
    except_model_id: UUID,
) -> list[UUID]:
    result = await db.execute(
        select(RiskModelVersionModel).where(
            RiskModelVersionModel.model_key == model_key,
            RiskModelVersionModel.deployment_mode == "champion",
            RiskModelVersionModel.id != except_model_id,
            RiskModelVersionModel.status == "active",
        )
    )
    demoted_ids: list[UUID] = []
    for champion in result.scalars().all():
        champion.deployment_mode = "challenger"
        demoted_ids.append(champion.id)
    return demoted_ids


def _model_state(model: RiskModelVersionModel) -> dict[str, Any]:
    return {
        "model_key": model.model_key,
        "version": model.version,
        "deployment_mode": model.deployment_mode,
        "approval_state": model.approval_state,
        "status": model.status,
    }


def _decision_summary_response(decision: GrowthRiskDecisionModel) -> AdminGrowthRiskDecisionSummaryResponse:
    return AdminGrowthRiskDecisionSummaryResponse(
        id=decision.id,
        risk_subject_id=decision.risk_subject_id,
        code_set_id=decision.code_set_id,
        growth_code_id=decision.growth_code_id,
        private_grant_id=decision.private_grant_id,
        quote_session_id=decision.quote_session_id,
        order_id=decision.order_id,
        action_context=decision.action_context,
        rules_policy_version_id=decision.rules_policy_version_id,
        model_version_id=decision.model_version_id,
        feature_snapshot_id=decision.feature_snapshot_id,
        rules_outcome=decision.rules_outcome,
        ml_score=_decimal_to_string(decision.ml_score),
        risk_band=decision.risk_band,
        final_action=decision.final_action,
        reason_codes=list(decision.reason_codes or []),
        fallback_mode=decision.fallback_mode,
        decided_at=decision.decided_at,
        created_at=decision.created_at,
    )


def _decimal_to_string(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return format(value, "f")


def _admin_growth_error(
    status_code: int,
    code: str,
    message_key: str,
    debug_context: Mapping[str, Any] | None = None,
) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={
            "code": code,
            "message_key": message_key,
            "retryable": False,
            "debug_context": dict(debug_context or {}),
        },
    )
