from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.config_service import (
    CUSTOMER_ONBOARDING_RUNTIME_CONFIG_KEY,
    ConfigService,
    CustomerOnboardingRuntimeConfig,
)
from src.application.use_cases.auth.permissions import Permission
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.customer_onboarding_model import (
    CustomerOnboardingCodeApplicationModel,
    CustomerOnboardingStateModel,
)
from src.infrastructure.database.repositories.system_config_repo import SystemConfigRepository
from src.presentation.api.v1.admin.audit import write_required_admin_audit_entry
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_permission

router = APIRouter(prefix="/admin/growth/onboarding", tags=["admin-growth-onboarding-v3"])


class AdminGrowthOnboardingRuntimeResponse(BaseModel):
    post_registration_code_prompt_enabled: bool
    web_otp_enabled: bool
    telegram_miniapp_enabled: bool
    state_store_ready: bool
    flow_key: str
    version: int
    allowed_code_types: list[str]
    allow_referral_input: bool
    allow_partner_input: bool
    available: bool
    config_updated_at: datetime | None
    updated_by_admin_user_id: UUID | None


class AdminGrowthOnboardingRuntimeUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    post_registration_code_prompt_enabled: bool | None = None
    web_otp_enabled: bool | None = None
    telegram_miniapp_enabled: bool | None = None
    state_store_ready: bool | None = None
    flow_key: str | None = Field(default=None, min_length=3, max_length=80)
    version: int | None = Field(default=None, ge=1, le=1000)
    allowed_code_types: list[Literal["promo", "invite", "gift"]] | None = Field(default=None, min_length=1)
    allow_referral_input: bool | None = None
    allow_partner_input: bool | None = None
    change_reason: str = Field(..., min_length=3, max_length=2000)


class AdminGrowthOnboardingStateResponse(BaseModel):
    id: UUID
    mobile_user_id: UUID
    flow_key: str
    flow_version: int
    source_channel: str
    status: str
    skippable: bool
    policy_version_id: UUID | None
    first_eligible_at: datetime
    first_shown_at: datetime | None
    last_shown_at: datetime | None
    display_count: int
    submitted_at: datetime | None
    completed_at: datetime | None
    skipped_at: datetime | None
    expires_at: datetime | None
    result_code_application_id: UUID | None
    signup_finalization_id: UUID | None
    referral_terminal_state: str | None
    canonical_identity_link_id: UUID | None
    auth_channel: str
    return_route_key: str | None
    result_payload: dict[str, Any]
    application_count: int
    created_at: datetime
    updated_at: datetime


class AdminGrowthOnboardingStateListResponse(BaseModel):
    items: list[AdminGrowthOnboardingStateResponse]
    total: int
    limit: int
    offset: int


class AdminGrowthOnboardingApplicationResponse(BaseModel):
    id: UUID
    onboarding_state_id: UUID
    mobile_user_id: UUID
    growth_code_id: UUID | None
    resolved_code_type: str | None
    action_context: str
    result: str
    reject_reason: str | None
    policy_version_id: UUID | None
    risk_decision_id: UUID | None
    redemption_id: UUID | None
    fulfillment_id: UUID | None
    code_intent_id: UUID | None
    idempotency_key_hash: str
    code_prefix: str
    safe_result_snapshot: dict[str, Any]
    signup_finalization_id: UUID | None
    referral_terminal_state: str | None
    auth_channel: str
    return_route_key: str | None
    created_at: datetime


class AdminGrowthOnboardingApplicationListResponse(BaseModel):
    items: list[AdminGrowthOnboardingApplicationResponse]
    total: int
    limit: int
    offset: int


class AdminGrowthOnboardingStateResetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(..., min_length=3, max_length=2000)
    expected_status: str | None = Field(default=None, max_length=24)


@router.get("/settings", response_model=AdminGrowthOnboardingRuntimeResponse)
async def get_growth_onboarding_settings(
    _current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_ONBOARDING_VIEW)),
    db: AsyncSession = Depends(get_db),
) -> AdminGrowthOnboardingRuntimeResponse:
    repo = SystemConfigRepository(db)
    service = ConfigService(repo)
    model = await repo.get_by_key(CUSTOMER_ONBOARDING_RUNTIME_CONFIG_KEY)
    runtime = await service.get_customer_onboarding_runtime_config()
    return _runtime_response(
        runtime, config_updated_at=model.updated_at if model else None, updated_by=model.updated_by if model else None
    )


@router.put("/settings", response_model=AdminGrowthOnboardingRuntimeResponse)
async def update_growth_onboarding_settings(
    payload: AdminGrowthOnboardingRuntimeUpdateRequest,
    request: Request,
    current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_ONBOARDING_MANAGE)),
    db: AsyncSession = Depends(get_db),
) -> AdminGrowthOnboardingRuntimeResponse:
    repo = SystemConfigRepository(db)
    service = ConfigService(repo)
    existing_model = await repo.get_by_key(CUSTOMER_ONBOARDING_RUNTIME_CONFIG_KEY)
    existing_runtime = await service.get_customer_onboarding_runtime_config()
    before = _runtime_audit_snapshot(existing_runtime)
    existing_updated_at = existing_model.updated_at if existing_model else None
    next_value = {
        **before,
        **payload.model_dump(exclude_none=True, exclude={"change_reason"}),
    }
    await service.set(
        CUSTOMER_ONBOARDING_RUNTIME_CONFIG_KEY,
        next_value,
        updated_by=current_user.id,
        description="Customer post-registration growth-code onboarding runtime",
    )
    updated_model = await repo.get_by_key(CUSTOMER_ONBOARDING_RUNTIME_CONFIG_KEY)
    if updated_model is not None:
        await db.refresh(updated_model)
    updated_runtime = await service.get_customer_onboarding_runtime_config()
    updated_at = updated_model.updated_at if updated_model else None
    updated_by = updated_model.updated_by if updated_model else None
    await write_required_admin_audit_entry(
        db=db,
        action="growth_onboarding_settings.updated",
        resource_type="customer_onboarding_runtime_config",
        resource_id=CUSTOMER_ONBOARDING_RUNTIME_CONFIG_KEY,
        actor=current_user,
        request=request,
        old_value={
            **before,
            "updated_at": existing_updated_at.isoformat() if existing_updated_at else None,
        },
        details={
            **_runtime_audit_snapshot(updated_runtime),
            "reason": payload.change_reason,
        },
    )
    return _runtime_response(
        updated_runtime,
        config_updated_at=updated_at,
        updated_by=updated_by,
    )


@router.get("/states", response_model=AdminGrowthOnboardingStateListResponse)
async def list_growth_onboarding_states(
    mobile_user_id: UUID | None = None,
    status_filter: str | None = Query(default=None, alias="status", max_length=24),
    flow_key: str | None = Query(default=None, max_length=80),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_ONBOARDING_VIEW)),
    db: AsyncSession = Depends(get_db),
) -> AdminGrowthOnboardingStateListResponse:
    statement = select(CustomerOnboardingStateModel)
    if mobile_user_id is not None:
        statement = statement.where(CustomerOnboardingStateModel.mobile_user_id == mobile_user_id)
    if status_filter is not None:
        statement = statement.where(CustomerOnboardingStateModel.status == status_filter)
    if flow_key is not None:
        statement = statement.where(CustomerOnboardingStateModel.flow_key == flow_key)
    total = await _count_for(statement, db)
    result = await db.execute(
        statement.order_by(CustomerOnboardingStateModel.updated_at.desc()).limit(limit).offset(offset)
    )
    states = list(result.scalars().all())
    application_counts = await _application_counts(db, states)
    return AdminGrowthOnboardingStateListResponse(
        items=[_state_response(state, application_count=application_counts.get(state.id, 0)) for state in states],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/states/{state_id}", response_model=AdminGrowthOnboardingStateResponse)
async def get_growth_onboarding_state(
    state_id: UUID,
    _current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_ONBOARDING_VIEW)),
    db: AsyncSession = Depends(get_db),
) -> AdminGrowthOnboardingStateResponse:
    state = await db.get(CustomerOnboardingStateModel, state_id)
    if state is None:
        raise _admin_growth_error(
            status.HTTP_404_NOT_FOUND,
            "ONBOARDING_STATE_NOT_FOUND",
            "admin.growth.onboarding.errors.stateNotFound",
            {"state_id": str(state_id)},
        )
    application_count = int(
        await db.scalar(
            select(func.count()).where(CustomerOnboardingCodeApplicationModel.onboarding_state_id == state.id)
        )
        or 0
    )
    return _state_response(state, application_count=application_count)


@router.get("/applications", response_model=AdminGrowthOnboardingApplicationListResponse)
async def list_growth_onboarding_applications(
    onboarding_state_id: UUID | None = None,
    mobile_user_id: UUID | None = None,
    result_filter: str | None = Query(default=None, alias="result", max_length=30),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_ONBOARDING_VIEW)),
    db: AsyncSession = Depends(get_db),
) -> AdminGrowthOnboardingApplicationListResponse:
    statement = select(CustomerOnboardingCodeApplicationModel)
    if onboarding_state_id is not None:
        statement = statement.where(CustomerOnboardingCodeApplicationModel.onboarding_state_id == onboarding_state_id)
    if mobile_user_id is not None:
        statement = statement.where(CustomerOnboardingCodeApplicationModel.mobile_user_id == mobile_user_id)
    if result_filter is not None:
        statement = statement.where(CustomerOnboardingCodeApplicationModel.result == result_filter)
    total = await _count_for(statement, db)
    result = await db.execute(
        statement.order_by(CustomerOnboardingCodeApplicationModel.created_at.desc()).limit(limit).offset(offset)
    )
    return AdminGrowthOnboardingApplicationListResponse(
        items=[_application_response(item) for item in result.scalars().all()],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/states/{state_id}/reset", response_model=AdminGrowthOnboardingStateResponse)
async def reset_growth_onboarding_state(
    state_id: UUID,
    payload: AdminGrowthOnboardingStateResetRequest,
    request: Request,
    current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_ONBOARDING_RESET)),
    db: AsyncSession = Depends(get_db),
) -> AdminGrowthOnboardingStateResponse:
    result = await db.execute(
        select(CustomerOnboardingStateModel).where(CustomerOnboardingStateModel.id == state_id).with_for_update()
    )
    state = result.scalar_one_or_none()
    if state is None:
        raise _admin_growth_error(
            status.HTTP_404_NOT_FOUND,
            "ONBOARDING_STATE_NOT_FOUND",
            "admin.growth.onboarding.errors.stateNotFound",
            {"state_id": str(state_id)},
        )
    if payload.expected_status is not None and state.status != payload.expected_status:
        raise _admin_growth_error(
            status.HTTP_409_CONFLICT,
            "ONBOARDING_STATE_CONFLICT",
            "admin.growth.onboarding.errors.stateConflict",
            {"state_id": str(state.id), "expected": payload.expected_status, "actual": state.status},
        )

    old_value = _state_audit_snapshot(state)
    now = datetime.now(UTC)
    state.status = "pending"
    state.first_shown_at = None
    state.last_shown_at = None
    state.display_count = 0
    state.submitted_at = None
    state.completed_at = None
    state.skipped_at = None
    state.result_code_application_id = None
    state.result_payload = {
        "message_key": "onboarding.reset_by_admin",
        "reset_at": now.isoformat(),
    }
    await db.flush()
    application_count = int(
        await db.scalar(
            select(func.count()).where(CustomerOnboardingCodeApplicationModel.onboarding_state_id == state.id)
        )
        or 0
    )
    await write_required_admin_audit_entry(
        db=db,
        action="growth_onboarding_state.reset",
        resource_type="customer_onboarding_state",
        resource_id=state.id,
        actor=current_user,
        request=request,
        old_value=old_value,
        details={
            **_state_audit_snapshot(state),
            "reason": payload.reason,
        },
    )
    return _state_response(state, application_count=application_count)


def _runtime_response(
    runtime: CustomerOnboardingRuntimeConfig,
    *,
    config_updated_at: datetime | None,
    updated_by: UUID | None,
) -> AdminGrowthOnboardingRuntimeResponse:
    return AdminGrowthOnboardingRuntimeResponse(
        post_registration_code_prompt_enabled=runtime.post_registration_code_prompt_enabled,
        web_otp_enabled=runtime.web_otp_enabled,
        telegram_miniapp_enabled=runtime.telegram_miniapp_enabled,
        state_store_ready=runtime.state_store_ready,
        flow_key=runtime.flow_key,
        version=runtime.version,
        allowed_code_types=list(runtime.allowed_code_types),
        allow_referral_input=runtime.allow_referral_input,
        allow_partner_input=runtime.allow_partner_input,
        available=runtime.available,
        config_updated_at=config_updated_at,
        updated_by_admin_user_id=updated_by,
    )


def _runtime_audit_snapshot(runtime: CustomerOnboardingRuntimeConfig) -> dict[str, Any]:
    return {
        "post_registration_code_prompt_enabled": runtime.post_registration_code_prompt_enabled,
        "web_otp_enabled": runtime.web_otp_enabled,
        "telegram_miniapp_enabled": runtime.telegram_miniapp_enabled,
        "state_store_ready": runtime.state_store_ready,
        "flow_key": runtime.flow_key,
        "version": runtime.version,
        "allowed_code_types": list(runtime.allowed_code_types),
        "allow_referral_input": runtime.allow_referral_input,
        "allow_partner_input": runtime.allow_partner_input,
    }


async def _application_counts(
    db: AsyncSession,
    states: Sequence[CustomerOnboardingStateModel],
) -> dict[UUID, int]:
    state_ids = [state.id for state in states]
    if not state_ids:
        return {}
    result = await db.execute(
        select(
            CustomerOnboardingCodeApplicationModel.onboarding_state_id,
            func.count(),
        )
        .where(CustomerOnboardingCodeApplicationModel.onboarding_state_id.in_(state_ids))
        .group_by(CustomerOnboardingCodeApplicationModel.onboarding_state_id)
    )
    return {row[0]: int(row[1]) for row in result.all()}


def _state_response(
    state: CustomerOnboardingStateModel,
    *,
    application_count: int,
) -> AdminGrowthOnboardingStateResponse:
    return AdminGrowthOnboardingStateResponse(
        id=state.id,
        mobile_user_id=state.mobile_user_id,
        flow_key=state.flow_key,
        flow_version=state.flow_version,
        source_channel=state.source_channel,
        status=state.status,
        skippable=state.skippable,
        policy_version_id=state.policy_version_id,
        first_eligible_at=state.first_eligible_at,
        first_shown_at=state.first_shown_at,
        last_shown_at=state.last_shown_at,
        display_count=state.display_count,
        submitted_at=state.submitted_at,
        completed_at=state.completed_at,
        skipped_at=state.skipped_at,
        expires_at=state.expires_at,
        result_code_application_id=state.result_code_application_id,
        signup_finalization_id=state.signup_finalization_id,
        referral_terminal_state=state.referral_terminal_state,
        canonical_identity_link_id=state.canonical_identity_link_id,
        auth_channel=state.auth_channel,
        return_route_key=state.return_route_key,
        result_payload=_scrub_support_payload(state.result_payload or {}),
        application_count=application_count,
        created_at=state.created_at,
        updated_at=state.updated_at,
    )


def _application_response(
    application: CustomerOnboardingCodeApplicationModel,
) -> AdminGrowthOnboardingApplicationResponse:
    return AdminGrowthOnboardingApplicationResponse(
        id=application.id,
        onboarding_state_id=application.onboarding_state_id,
        mobile_user_id=application.mobile_user_id,
        growth_code_id=application.growth_code_id,
        resolved_code_type=application.resolved_code_type,
        action_context=application.action_context,
        result=application.result,
        reject_reason=application.reject_reason,
        policy_version_id=application.policy_version_id,
        risk_decision_id=application.risk_decision_id,
        redemption_id=application.redemption_id,
        fulfillment_id=application.fulfillment_id,
        code_intent_id=application.code_intent_id,
        idempotency_key_hash=_hash_public_identifier(application.idempotency_key),
        code_prefix=application.code_prefix,
        safe_result_snapshot=_scrub_support_payload(application.safe_result_snapshot or {}),
        signup_finalization_id=application.signup_finalization_id,
        referral_terminal_state=application.referral_terminal_state,
        auth_channel=application.auth_channel,
        return_route_key=application.return_route_key,
        created_at=application.created_at,
    )


def _state_audit_snapshot(state: CustomerOnboardingStateModel) -> dict[str, Any]:
    return {
        "status": state.status,
        "mobile_user_id": str(state.mobile_user_id),
        "flow_key": state.flow_key,
        "flow_version": state.flow_version,
        "display_count": state.display_count,
        "result_code_application_id": (
            str(state.result_code_application_id) if state.result_code_application_id else None
        ),
    }


def _hash_public_identifier(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _scrub_support_payload(value: Any) -> Any:
    if isinstance(value, Mapping):
        scrubbed: dict[str, Any] = {}
        for key, item in value.items():
            if key in {"idempotency_key", "raw_idempotency_key"}:
                prefix = "raw_idempotency_key" if key == "raw_idempotency_key" else "idempotency_key"
                raw_value = str(item) if item not in (None, "") else None
                scrubbed[f"{prefix}_present"] = raw_value is not None
                if raw_value is not None:
                    scrubbed[f"{prefix}_hash"] = _hash_public_identifier(raw_value)
                continue
            scrubbed[str(key)] = _scrub_support_payload(item)
        return scrubbed
    if isinstance(value, list):
        return [_scrub_support_payload(item) for item in value]
    if isinstance(value, tuple):
        return [_scrub_support_payload(item) for item in value]
    return value


async def _count_for(statement: Select[tuple[Any]], db: AsyncSession) -> int:
    count_statement = select(func.count()).select_from(statement.order_by(None).limit(None).offset(None).subquery())
    return int(await db.scalar(count_statement) or 0)


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
