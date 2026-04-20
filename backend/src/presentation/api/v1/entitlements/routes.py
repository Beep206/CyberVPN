from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.service_access import (
    ActivateEntitlementGrantUseCase,
    CreateEntitlementGrantUseCase,
    ExpireEntitlementGrantUseCase,
    GetCurrentEntitlementStateUseCase,
    GetEntitlementGrantUseCase,
    ListEntitlementGrantsUseCase,
    RevokeEntitlementGrantUseCase,
    SuspendEntitlementGrantUseCase,
)
from src.domain.enums import AdminRole, EntitlementGrantSourceType, EntitlementGrantStatus
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.presentation.dependencies.auth import get_current_mobile_user_id
from src.presentation.dependencies.auth_realms import get_request_customer_realm
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_role

from .schemas import (
    CreateEntitlementGrantRequest,
    CurrentEntitlementStateResponse,
    EntitlementGrantResponse,
    EntitlementGrantTransitionRequest,
)

router = APIRouter(prefix="/entitlements", tags=["entitlements"])


def _serialize_entitlement_grant(model) -> EntitlementGrantResponse:
    return EntitlementGrantResponse(
        id=model.id,
        grant_key=model.grant_key,
        service_identity_id=model.service_identity_id,
        customer_account_id=model.customer_account_id,
        auth_realm_id=model.auth_realm_id,
        origin_storefront_id=model.origin_storefront_id,
        source_type=model.source_type,
        source_order_id=model.source_order_id,
        source_growth_reward_allocation_id=model.source_growth_reward_allocation_id,
        source_renewal_order_id=model.source_renewal_order_id,
        manual_source_key=model.manual_source_key,
        grant_status=model.grant_status,
        grant_snapshot=dict(model.grant_snapshot or {}),
        source_snapshot=dict(model.source_snapshot or {}),
        effective_from=model.effective_from,
        expires_at=model.expires_at,
        created_by_admin_user_id=model.created_by_admin_user_id,
        activated_at=model.activated_at,
        activated_by_admin_user_id=model.activated_by_admin_user_id,
        suspended_at=model.suspended_at,
        suspended_by_admin_user_id=model.suspended_by_admin_user_id,
        suspension_reason_code=model.suspension_reason_code,
        revoked_at=model.revoked_at,
        revoked_by_admin_user_id=model.revoked_by_admin_user_id,
        revoke_reason_code=model.revoke_reason_code,
        expired_at=model.expired_at,
        expired_by_admin_user_id=model.expired_by_admin_user_id,
        expiry_reason_code=model.expiry_reason_code,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


@router.post("/", response_model=EntitlementGrantResponse, status_code=status.HTTP_201_CREATED)
async def create_entitlement_grant(
    payload: CreateEntitlementGrantRequest,
    http_response: Response,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> EntitlementGrantResponse:
    try:
        result = await CreateEntitlementGrantUseCase(db).execute(
            service_identity_id=payload.service_identity_id,
            source_order_id=payload.source_order_id,
            source_growth_reward_allocation_id=payload.source_growth_reward_allocation_id,
            source_renewal_order_id=payload.source_renewal_order_id,
            manual_source_key=payload.manual_source_key,
            grant_snapshot=payload.grant_snapshot,
            expires_at=payload.expires_at,
            created_by_admin_user_id=current_admin.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if not result.created:
        http_response.status_code = status.HTTP_200_OK
    return _serialize_entitlement_grant(result.entitlement_grant)


@router.get("/", response_model=list[EntitlementGrantResponse])
async def list_entitlement_grants(
    service_identity_id: UUID | None = Query(None),
    customer_account_id: UUID | None = Query(None),
    auth_realm_id: UUID | None = Query(None),
    source_type: EntitlementGrantSourceType | None = Query(None),
    grant_status: EntitlementGrantStatus | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.SUPPORT)),
) -> list[EntitlementGrantResponse]:
    items = await ListEntitlementGrantsUseCase(db).execute(
        service_identity_id=service_identity_id,
        customer_account_id=customer_account_id,
        auth_realm_id=auth_realm_id,
        source_type=source_type.value if source_type else None,
        grant_status=grant_status.value if grant_status else None,
        limit=limit,
        offset=offset,
    )
    return [_serialize_entitlement_grant(item) for item in items]


@router.get("/current", response_model=CurrentEntitlementStateResponse)
async def get_current_entitlement_state(
    customer_account_id: UUID = Depends(get_current_mobile_user_id),
    current_realm=Depends(get_request_customer_realm),
    db: AsyncSession = Depends(get_db),
) -> CurrentEntitlementStateResponse:
    snapshot = await GetCurrentEntitlementStateUseCase(db).execute(
        customer_account_id=customer_account_id,
        auth_realm_id=current_realm.auth_realm.id,
    )
    return CurrentEntitlementStateResponse(**snapshot)


@router.get("/{entitlement_grant_id}", response_model=EntitlementGrantResponse)
async def get_entitlement_grant(
    entitlement_grant_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.SUPPORT)),
) -> EntitlementGrantResponse:
    item = await GetEntitlementGrantUseCase(db).execute(entitlement_grant_id=entitlement_grant_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entitlement grant not found")
    return _serialize_entitlement_grant(item)


@router.post("/{entitlement_grant_id}/activate", response_model=EntitlementGrantResponse)
async def activate_entitlement_grant(
    entitlement_grant_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> EntitlementGrantResponse:
    try:
        item = await ActivateEntitlementGrantUseCase(db).execute(
            entitlement_grant_id=entitlement_grant_id,
            activated_by_admin_user_id=current_admin.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_entitlement_grant(item)


@router.post("/{entitlement_grant_id}/suspend", response_model=EntitlementGrantResponse)
async def suspend_entitlement_grant(
    entitlement_grant_id: UUID,
    payload: EntitlementGrantTransitionRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> EntitlementGrantResponse:
    try:
        item = await SuspendEntitlementGrantUseCase(db).execute(
            entitlement_grant_id=entitlement_grant_id,
            suspended_by_admin_user_id=current_admin.id,
            reason_code=payload.reason_code,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_entitlement_grant(item)


@router.post("/{entitlement_grant_id}/revoke", response_model=EntitlementGrantResponse)
async def revoke_entitlement_grant(
    entitlement_grant_id: UUID,
    payload: EntitlementGrantTransitionRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> EntitlementGrantResponse:
    try:
        item = await RevokeEntitlementGrantUseCase(db).execute(
            entitlement_grant_id=entitlement_grant_id,
            revoked_by_admin_user_id=current_admin.id,
            reason_code=payload.reason_code,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_entitlement_grant(item)


@router.post("/{entitlement_grant_id}/expire", response_model=EntitlementGrantResponse)
async def expire_entitlement_grant(
    entitlement_grant_id: UUID,
    payload: EntitlementGrantTransitionRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> EntitlementGrantResponse:
    try:
        item = await ExpireEntitlementGrantUseCase(db).execute(
            entitlement_grant_id=entitlement_grant_id,
            expired_by_admin_user_id=current_admin.id,
            reason_code=payload.reason_code,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_entitlement_grant(item)
