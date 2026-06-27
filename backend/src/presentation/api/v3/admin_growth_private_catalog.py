from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.auth.permissions import Permission
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.growth_code_set_model import (
    GrowthPrivateCatalogPolicyModel,
    PrivateCatalogAccessGrantModel,
)
from src.infrastructure.database.models.subscription_plan_model import SubscriptionPlanModel
from src.presentation.api.v1.admin.audit import write_required_admin_audit_entry
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_permission

router = APIRouter(prefix="/admin/growth", tags=["admin-growth-private-catalog-v3"])


class AdminGrowthPrivateTargetResponse(BaseModel):
    id: UUID
    plan_code: str | None
    name: str
    display_name: str
    duration_days: int
    catalog_visibility: str
    catalog_access_class: str
    sale_channels: list[str]
    is_active: bool
    policy_count: int


class AdminGrowthPrivateTargetListResponse(BaseModel):
    items: list[AdminGrowthPrivateTargetResponse]
    total: int
    limit: int
    offset: int


class AdminGrowthPrivateGrantResponse(BaseModel):
    id: UUID
    policy_id: UUID
    policy_version_id: UUID
    growth_code_id: UUID
    code_set_hash: str
    user_id: UUID | None
    anonymous_session_id: str | None
    risk_subject_id: UUID | None
    auth_realm_id: UUID
    storefront_id: UUID
    sale_channel: str
    allowed_plan_ids: list[str]
    allowed_offer_ids: list[str]
    risk_decision_id: UUID | None
    status: str
    max_quote_conversions: int | None
    quote_conversions_count: int
    issued_at: datetime
    expires_at: datetime
    attached_quote_session_id: UUID | None
    attached_checkout_session_id: UUID | None
    consumed_order_id: UUID | None
    revoked_at: datetime | None
    revoked_reason: str | None
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class AdminGrowthPrivateGrantListResponse(BaseModel):
    items: list[AdminGrowthPrivateGrantResponse]
    total: int
    limit: int
    offset: int


class AdminGrowthPrivateGrantRevokeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(..., min_length=3, max_length=120)
    expected_status: str | None = Field(default=None, max_length=24)


@router.get("/private-catalog/targets", response_model=AdminGrowthPrivateTargetListResponse)
async def list_private_catalog_targets(
    active_only: bool = True,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_PRIVATE_CATALOG_VIEW)),
    db: AsyncSession = Depends(get_db),
) -> AdminGrowthPrivateTargetListResponse:
    statement = select(SubscriptionPlanModel).where(SubscriptionPlanModel.catalog_access_class == "private_code_gated")
    if active_only:
        statement = statement.where(SubscriptionPlanModel.is_active.is_(True))
    total = await _count_for(statement, db)
    result = await db.execute(statement.order_by(SubscriptionPlanModel.sort_order.asc()).limit(limit).offset(offset))
    plans = result.scalars().all()
    policy_counts = await _policy_counts_for_plans(db, plans)
    return AdminGrowthPrivateTargetListResponse(
        items=[
            AdminGrowthPrivateTargetResponse(
                id=plan.id,
                plan_code=plan.plan_code,
                name=plan.name,
                display_name=plan.display_name or plan.name,
                duration_days=plan.duration_days,
                catalog_visibility=plan.catalog_visibility,
                catalog_access_class=plan.catalog_access_class,
                sale_channels=list(plan.sale_channels or []),
                is_active=bool(plan.is_active),
                policy_count=policy_counts.get(str(plan.id), 0),
            )
            for plan in plans
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/private-grants", response_model=AdminGrowthPrivateGrantListResponse)
async def list_private_catalog_grants(
    status_filter: str | None = Query(default=None, alias="status", max_length=24),
    user_id: UUID | None = None,
    anonymous_session_id: str | None = Query(default=None, max_length=120),
    storefront_id: UUID | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_PRIVATE_GRANTS_VIEW)),
    db: AsyncSession = Depends(get_db),
) -> AdminGrowthPrivateGrantListResponse:
    statement = select(PrivateCatalogAccessGrantModel)
    if status_filter is not None:
        statement = statement.where(PrivateCatalogAccessGrantModel.status == status_filter)
    if user_id is not None:
        statement = statement.where(PrivateCatalogAccessGrantModel.user_id == user_id)
    if anonymous_session_id is not None:
        statement = statement.where(PrivateCatalogAccessGrantModel.anonymous_session_id == anonymous_session_id)
    if storefront_id is not None:
        statement = statement.where(PrivateCatalogAccessGrantModel.storefront_id == storefront_id)
    total = await _count_for(statement, db)
    result = await db.execute(
        statement.order_by(PrivateCatalogAccessGrantModel.issued_at.desc()).limit(limit).offset(offset)
    )
    return AdminGrowthPrivateGrantListResponse(
        items=[_grant_response(item) for item in result.scalars().all()],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/private-grants/{grant_id}", response_model=AdminGrowthPrivateGrantResponse)
async def get_private_catalog_grant(
    grant_id: UUID,
    _current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_PRIVATE_GRANTS_VIEW)),
    db: AsyncSession = Depends(get_db),
) -> AdminGrowthPrivateGrantResponse:
    grant = await db.get(PrivateCatalogAccessGrantModel, grant_id)
    if grant is None:
        raise _admin_growth_error(
            status.HTTP_404_NOT_FOUND,
            "PRIVATE_GRANT_NOT_FOUND",
            "admin.growth.privateAccess.errors.grantNotFound",
            {"grant_id": str(grant_id)},
        )
    return _grant_response(grant)


@router.post("/private-grants/{grant_id}/revoke", response_model=AdminGrowthPrivateGrantResponse)
async def revoke_private_catalog_grant(
    grant_id: UUID,
    payload: AdminGrowthPrivateGrantRevokeRequest,
    request: Request,
    current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_PRIVATE_GRANTS_REVOKE)),
    db: AsyncSession = Depends(get_db),
) -> AdminGrowthPrivateGrantResponse:
    result = await db.execute(
        select(PrivateCatalogAccessGrantModel).where(PrivateCatalogAccessGrantModel.id == grant_id).with_for_update()
    )
    grant = result.scalars().first()
    if grant is None:
        raise _admin_growth_error(
            status.HTTP_404_NOT_FOUND,
            "PRIVATE_GRANT_NOT_FOUND",
            "admin.growth.privateAccess.errors.grantNotFound",
            {"grant_id": str(grant_id)},
        )
    if payload.expected_status is not None and grant.status != payload.expected_status:
        raise _admin_growth_error(
            status.HTTP_409_CONFLICT,
            "PRIVATE_GRANT_STATE_CONFLICT",
            "admin.growth.privateAccess.errors.grantStateConflict",
            {"grant_id": str(grant.id), "expected": payload.expected_status, "actual": grant.status},
        )
    if grant.status == "consumed" or grant.consumed_order_id is not None:
        raise _admin_growth_error(
            status.HTTP_409_CONFLICT,
            "PRIVATE_GRANT_ALREADY_CONSUMED",
            "admin.growth.privateAccess.errors.grantAlreadyConsumed",
            {"grant_id": str(grant.id), "consumed_order_id": str(grant.consumed_order_id)},
        )

    old_value = _grant_state(grant)
    grant.status = "revoked"
    grant.revoked_at = datetime.now(UTC)
    grant.revoked_reason = payload.reason
    await db.flush()
    await write_required_admin_audit_entry(
        db=db,
        action="growth_private_grant.revoked",
        resource_type="private_catalog_access_grant",
        resource_id=grant.id,
        actor=current_user,
        request=request,
        old_value=old_value,
        details={**_grant_state(grant), "reason": payload.reason},
    )
    return _grant_response(grant)


async def _policy_counts_for_plans(
    db: AsyncSession,
    plans: Sequence[SubscriptionPlanModel],
) -> dict[str, int]:
    if not plans:
        return {}
    plan_ids = {str(plan.id) for plan in plans}
    result = await db.execute(
        select(GrowthPrivateCatalogPolicyModel.target_plan_ids).where(
            GrowthPrivateCatalogPolicyModel.is_active.is_(True)
        )
    )
    counts = {plan_id: 0 for plan_id in plan_ids}
    for target_plan_ids in result.scalars().all():
        for plan_id in target_plan_ids or []:
            if str(plan_id) in counts:
                counts[str(plan_id)] += 1
    return counts


def _grant_response(grant: PrivateCatalogAccessGrantModel) -> AdminGrowthPrivateGrantResponse:
    return AdminGrowthPrivateGrantResponse(
        id=grant.id,
        policy_id=grant.policy_id,
        policy_version_id=grant.policy_version_id,
        growth_code_id=grant.growth_code_id,
        code_set_hash=grant.code_set_hash,
        user_id=grant.user_id,
        anonymous_session_id=grant.anonymous_session_id,
        risk_subject_id=grant.risk_subject_id,
        auth_realm_id=grant.auth_realm_id,
        storefront_id=grant.storefront_id,
        sale_channel=grant.sale_channel,
        allowed_plan_ids=list(grant.allowed_plan_ids or []),
        allowed_offer_ids=list(grant.allowed_offer_ids or []),
        risk_decision_id=grant.risk_decision_id,
        status=grant.status,
        max_quote_conversions=grant.max_quote_conversions,
        quote_conversions_count=grant.quote_conversions_count,
        issued_at=grant.issued_at,
        expires_at=grant.expires_at,
        attached_quote_session_id=grant.attached_quote_session_id,
        attached_checkout_session_id=grant.attached_checkout_session_id,
        consumed_order_id=grant.consumed_order_id,
        revoked_at=grant.revoked_at,
        revoked_reason=grant.revoked_reason,
        metadata=dict(grant.metadata_ or {}),
        created_at=grant.created_at,
        updated_at=grant.updated_at,
    )


def _grant_state(grant: PrivateCatalogAccessGrantModel) -> dict[str, Any]:
    return {
        "status": grant.status,
        "revoked_at": grant.revoked_at.isoformat() if grant.revoked_at else None,
        "revoked_reason": grant.revoked_reason,
        "quote_conversions_count": grant.quote_conversions_count,
        "consumed_order_id": str(grant.consumed_order_id) if grant.consumed_order_id else None,
    }


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
