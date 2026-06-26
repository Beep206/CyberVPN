from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.auth.permissions import Permission
from src.application.use_cases.growth_campaigns.admin_lifecycle import (
    CampaignTransitionError,
    CampaignValidationError,
    CampaignVersionConflictError,
    DuplicateCampaignKeyError,
    GrowthCampaignLifecycleUseCase,
    GrowthCampaignNotFoundError,
    GrowthCampaignRecord,
    campaign_audit_snapshot,
)
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.repositories.growth_campaign_repo import SqlAlchemyGrowthCampaignRepository
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_permission

from .audit import write_required_admin_audit_entry

router = APIRouter(prefix="/admin/growth/campaigns", tags=["admin", "growth-campaigns"])


class AdminGrowthCampaignScheduleRequest(BaseModel):
    starts_at: datetime | None = None
    expires_at: datetime | None = None


class AdminGrowthCampaignStackingRequest(BaseModel):
    mode: Literal["exclusive", "allow_with_same_campaign", "benefits_only_append", "max_discount"] = "exclusive"
    group: str | None = Field(default=None, max_length=80)


class AdminGrowthCampaignCreateRequest(BaseModel):
    campaign_key: str = Field(min_length=3, max_length=80)
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=2_000)
    schedule: AdminGrowthCampaignScheduleRequest = Field(default_factory=AdminGrowthCampaignScheduleRequest)
    priority: int = Field(default=0, ge=0)
    stacking: AdminGrowthCampaignStackingRequest = Field(default_factory=AdminGrowthCampaignStackingRequest)


class AdminGrowthCampaignPatchRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=2_000)
    schedule: AdminGrowthCampaignScheduleRequest | None = None
    priority: int | None = Field(default=None, ge=0)
    stacking: AdminGrowthCampaignStackingRequest | None = None
    expected_version: int | None = Field(default=None, ge=1)
    reason_code: str = Field(min_length=1, max_length=120)

    @model_validator(mode="after")
    def _require_change(self) -> AdminGrowthCampaignPatchRequest:
        if self.model_fields_set <= {"expected_version", "reason_code"}:
            raise ValueError("at least one campaign field must be changed")
        return self


class AdminGrowthCampaignActionRequest(BaseModel):
    expected_version: int | None = Field(default=None, ge=1)
    reason_code: str = Field(min_length=1, max_length=120)


class AdminGrowthCampaignResponse(BaseModel):
    id: UUID
    campaign_key: str
    name: str
    description: str | None
    status: str
    priority: int
    starts_at: datetime | None
    expires_at: datetime | None
    stacking_mode: str
    stacking_group: str | None
    current_version: int
    created_by_admin_id: UUID
    updated_by_admin_id: UUID | None
    published_at: datetime | None
    paused_at: datetime | None
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AdminGrowthCampaignListResponse(BaseModel):
    items: list[AdminGrowthCampaignResponse]
    total: int
    offset: int
    limit: int


@router.post("", response_model=AdminGrowthCampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_admin_growth_campaign(
    payload: AdminGrowthCampaignCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_CAMPAIGNS_WRITE)),
) -> AdminGrowthCampaignResponse:
    use_case = _use_case(db)
    try:
        campaign = await use_case.create_campaign(
            campaign_key=payload.campaign_key,
            name=payload.name,
            description=payload.description,
            priority=payload.priority,
            starts_at=payload.schedule.starts_at,
            expires_at=payload.schedule.expires_at,
            stacking_mode=payload.stacking.mode,
            stacking_group=payload.stacking.group,
            created_by_admin_id=current_user.id,
        )
    except (CampaignValidationError, DuplicateCampaignKeyError) as exc:
        raise _http_error(exc) from exc
    await _write_campaign_audit(
        db=db,
        request=request,
        actor=current_user,
        action="growth_campaign.created",
        campaign=campaign,
        reason_code="campaign_created",
    )
    return _serialize_campaign(campaign)


@router.get("", response_model=AdminGrowthCampaignListResponse)
async def list_admin_growth_campaigns(
    status_filter: str | None = Query(default=None, alias="status"),
    campaign_key: str | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    sort: str = Query(default="-created_at", pattern="^-?created_at$"),
    db: AsyncSession = Depends(get_db),
    _current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_CAMPAIGNS_READ)),
) -> AdminGrowthCampaignListResponse:
    try:
        result = await _use_case(db).list_campaigns(
            status=status_filter,
            campaign_key=campaign_key,
            offset=offset,
            limit=limit,
            sort=sort,
        )
    except CampaignValidationError as exc:
        raise _http_error(exc) from exc
    return AdminGrowthCampaignListResponse(
        items=[_serialize_campaign(item) for item in result.items],
        total=result.total,
        offset=result.offset,
        limit=result.limit,
    )


@router.get("/{campaign_id}", response_model=AdminGrowthCampaignResponse)
async def get_admin_growth_campaign(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_CAMPAIGNS_READ)),
) -> AdminGrowthCampaignResponse:
    try:
        return _serialize_campaign(await _use_case(db).get_campaign(campaign_id))
    except GrowthCampaignNotFoundError as exc:
        raise _http_error(exc) from exc


@router.patch("/{campaign_id}", response_model=AdminGrowthCampaignResponse)
async def update_admin_growth_campaign(
    campaign_id: UUID,
    payload: AdminGrowthCampaignPatchRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_CAMPAIGNS_WRITE)),
) -> AdminGrowthCampaignResponse:
    use_case = _use_case(db)
    try:
        before = await use_case.get_campaign(campaign_id)
        campaign = await use_case.update_draft_campaign(
            campaign_id=campaign_id,
            changes=_patch_changes(payload),
            actor_admin_id=current_user.id,
            expected_version=payload.expected_version,
        )
    except (
        CampaignValidationError,
        CampaignTransitionError,
        CampaignVersionConflictError,
        GrowthCampaignNotFoundError,
    ) as exc:
        raise _http_error(exc) from exc
    await _write_campaign_audit(
        db=db,
        request=request,
        actor=current_user,
        action="growth_campaign.updated",
        campaign=campaign,
        reason_code=payload.reason_code,
        before=before,
    )
    return _serialize_campaign(campaign)


@router.post("/{campaign_id}/publish", response_model=AdminGrowthCampaignResponse)
async def publish_admin_growth_campaign(
    campaign_id: UUID,
    payload: AdminGrowthCampaignActionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_CAMPAIGNS_PUBLISH)),
) -> AdminGrowthCampaignResponse:
    return await _transition_campaign(
        campaign_id=campaign_id,
        payload=payload,
        request=request,
        db=db,
        current_user=current_user,
        use_case_action="publish_campaign",
        audit_action="growth_campaign.published",
    )


@router.post("/{campaign_id}/pause", response_model=AdminGrowthCampaignResponse)
async def pause_admin_growth_campaign(
    campaign_id: UUID,
    payload: AdminGrowthCampaignActionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_CAMPAIGNS_PAUSE)),
) -> AdminGrowthCampaignResponse:
    return await _transition_campaign(
        campaign_id=campaign_id,
        payload=payload,
        request=request,
        db=db,
        current_user=current_user,
        use_case_action="pause_campaign",
        audit_action="growth_campaign.paused",
    )


@router.post("/{campaign_id}/resume", response_model=AdminGrowthCampaignResponse)
async def resume_admin_growth_campaign(
    campaign_id: UUID,
    payload: AdminGrowthCampaignActionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_CAMPAIGNS_PAUSE)),
) -> AdminGrowthCampaignResponse:
    return await _transition_campaign(
        campaign_id=campaign_id,
        payload=payload,
        request=request,
        db=db,
        current_user=current_user,
        use_case_action="resume_campaign",
        audit_action="growth_campaign.resumed",
    )


@router.post("/{campaign_id}/archive", response_model=AdminGrowthCampaignResponse)
async def archive_admin_growth_campaign(
    campaign_id: UUID,
    payload: AdminGrowthCampaignActionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_CAMPAIGNS_REVOKE)),
) -> AdminGrowthCampaignResponse:
    return await _transition_campaign(
        campaign_id=campaign_id,
        payload=payload,
        request=request,
        db=db,
        current_user=current_user,
        use_case_action="archive_campaign",
        audit_action="growth_campaign.archived",
    )


@router.post("/{campaign_id}/revoke", response_model=AdminGrowthCampaignResponse)
async def revoke_admin_growth_campaign(
    campaign_id: UUID,
    payload: AdminGrowthCampaignActionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_CAMPAIGNS_REVOKE)),
) -> AdminGrowthCampaignResponse:
    return await _transition_campaign(
        campaign_id=campaign_id,
        payload=payload,
        request=request,
        db=db,
        current_user=current_user,
        use_case_action="revoke_campaign",
        audit_action="growth_campaign.revoked",
    )


async def _transition_campaign(
    *,
    campaign_id: UUID,
    payload: AdminGrowthCampaignActionRequest,
    request: Request,
    db: AsyncSession,
    current_user: AdminUserModel,
    use_case_action: str,
    audit_action: str,
) -> AdminGrowthCampaignResponse:
    use_case = _use_case(db)
    try:
        before = await use_case.get_campaign(campaign_id)
        action = getattr(use_case, use_case_action)
        campaign = await action(
            campaign_id=campaign_id,
            actor_admin_id=current_user.id,
            expected_version=payload.expected_version,
        )
    except (
        CampaignValidationError,
        CampaignTransitionError,
        CampaignVersionConflictError,
        GrowthCampaignNotFoundError,
    ) as exc:
        raise _http_error(exc) from exc
    await _write_campaign_audit(
        db=db,
        request=request,
        actor=current_user,
        action=audit_action,
        campaign=campaign,
        reason_code=payload.reason_code,
        before=before,
    )
    return _serialize_campaign(campaign)


def _use_case(db: AsyncSession) -> GrowthCampaignLifecycleUseCase:
    return GrowthCampaignLifecycleUseCase(SqlAlchemyGrowthCampaignRepository(db))


def _patch_changes(payload: AdminGrowthCampaignPatchRequest) -> dict[str, Any]:
    changes: dict[str, Any] = {}
    if "name" in payload.model_fields_set:
        changes["name"] = payload.name
    if "description" in payload.model_fields_set:
        changes["description"] = payload.description
    if payload.schedule is not None:
        if "starts_at" in payload.schedule.model_fields_set:
            changes["starts_at"] = payload.schedule.starts_at
        if "expires_at" in payload.schedule.model_fields_set:
            changes["expires_at"] = payload.schedule.expires_at
    if payload.priority is not None:
        changes["priority"] = payload.priority
    if payload.stacking is not None:
        changes["stacking_mode"] = payload.stacking.mode
        changes["stacking_group"] = payload.stacking.group
    return changes


async def _write_campaign_audit(
    *,
    db: AsyncSession,
    request: Request,
    actor: AdminUserModel,
    action: str,
    campaign: GrowthCampaignRecord,
    reason_code: str,
    before: GrowthCampaignRecord | None = None,
) -> None:
    details = campaign_audit_snapshot(campaign)
    details["reason_code"] = reason_code
    await write_required_admin_audit_entry(
        db=db,
        action=action,
        resource_type="growth_campaign",
        resource_id=campaign.id,
        actor=actor,
        request=request,
        details=details,
        old_value=campaign_audit_snapshot(before) if before else None,
    )


def _serialize_campaign(campaign: GrowthCampaignRecord) -> AdminGrowthCampaignResponse:
    return AdminGrowthCampaignResponse(
        id=campaign.id,
        campaign_key=campaign.campaign_key,
        name=campaign.name,
        description=campaign.description,
        status=campaign.status,
        priority=campaign.priority,
        starts_at=campaign.starts_at,
        expires_at=campaign.expires_at,
        stacking_mode=campaign.stacking_mode,
        stacking_group=campaign.stacking_group,
        current_version=campaign.current_version,
        created_by_admin_id=campaign.created_by_admin_id,
        updated_by_admin_id=campaign.updated_by_admin_id,
        published_at=campaign.published_at,
        paused_at=campaign.paused_at,
        archived_at=campaign.archived_at,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
    )


def _http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, GrowthCampaignNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="GROWTH_CAMPAIGN_NOT_FOUND")
    if isinstance(exc, DuplicateCampaignKeyError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail="CAMPAIGN_KEY_ALREADY_EXISTS")
    if isinstance(exc, CampaignVersionConflictError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "CAMPAIGN_VERSION_CONFLICT",
                "expected_version": exc.expected_version,
                "actual_version": exc.actual_version,
            },
        )
    if isinstance(exc, CampaignTransitionError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.code.upper())
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc).upper())
