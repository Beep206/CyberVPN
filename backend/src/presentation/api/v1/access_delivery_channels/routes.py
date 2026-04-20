from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.auth_realms import RealmResolution
from src.application.use_cases.service_access import (
    ArchiveAccessDeliveryChannelUseCase,
    CreateAccessDeliveryChannelUseCase,
    GetAccessDeliveryChannelUseCase,
    GetCurrentServiceStateUseCase,
    ListAccessDeliveryChannelsUseCase,
    ResolveCurrentAccessDeliveryChannelUseCase,
)
from src.domain.enums import AccessDeliveryChannelStatus, AccessDeliveryChannelType, AdminRole
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.presentation.api.v1.device_credentials.routes import _serialize_device_credential
from src.presentation.api.v1.provisioning_profiles.routes import _serialize_provisioning_profile
from src.presentation.api.v1.service_identities.routes import _serialize_service_identity
from src.presentation.dependencies.auth import get_current_mobile_user_id
from src.presentation.dependencies.auth_realms import get_request_customer_realm
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_role

from .schemas import (
    AccessDeliveryChannelResponse,
    AccessDeliveryChannelTransitionRequest,
    CreateAccessDeliveryChannelRequest,
    CurrentServiceStateConsumptionContextResponse,
    CurrentServiceStatePurchaseContextResponse,
    CurrentServiceStateResponse,
    GetCurrentServiceStateRequest,
    ResolveCurrentAccessDeliveryChannelRequest,
    ResolveCurrentAccessDeliveryChannelResponse,
)

router = APIRouter(prefix="/access-delivery-channels", tags=["access-delivery-channels"])


def _serialize_access_delivery_channel(model) -> AccessDeliveryChannelResponse:
    return AccessDeliveryChannelResponse(
        id=model.id,
        delivery_key=model.delivery_key,
        service_identity_id=model.service_identity_id,
        auth_realm_id=model.auth_realm_id,
        origin_storefront_id=model.origin_storefront_id,
        provisioning_profile_id=model.provisioning_profile_id,
        device_credential_id=model.device_credential_id,
        channel_type=model.channel_type,
        channel_status=model.channel_status,
        channel_subject_ref=model.channel_subject_ref,
        provider_name=model.provider_name,
        delivery_context=dict(model.delivery_context or {}),
        delivery_payload=dict(model.delivery_payload or {}),
        last_delivered_at=model.last_delivered_at,
        last_accessed_at=model.last_accessed_at,
        archived_at=model.archived_at,
        archived_by_admin_user_id=model.archived_by_admin_user_id,
        archive_reason_code=model.archive_reason_code,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _serialize_purchase_context(active_entitlement_grant) -> CurrentServiceStatePurchaseContextResponse:
    if active_entitlement_grant is None:
        return CurrentServiceStatePurchaseContextResponse()
    return CurrentServiceStatePurchaseContextResponse(
        active_entitlement_grant_id=active_entitlement_grant.id,
        source_type=active_entitlement_grant.source_type,
        source_order_id=active_entitlement_grant.source_order_id,
        source_growth_reward_allocation_id=active_entitlement_grant.source_growth_reward_allocation_id,
        source_renewal_order_id=active_entitlement_grant.source_renewal_order_id,
        manual_source_key=active_entitlement_grant.manual_source_key,
        origin_storefront_id=active_entitlement_grant.origin_storefront_id,
    )


@router.post("/", response_model=AccessDeliveryChannelResponse, status_code=status.HTTP_201_CREATED)
async def create_access_delivery_channel(
    payload: CreateAccessDeliveryChannelRequest,
    http_response: Response,
    db: AsyncSession = Depends(get_db),
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> AccessDeliveryChannelResponse:
    try:
        result = await CreateAccessDeliveryChannelUseCase(db).execute(
            service_identity_id=payload.service_identity_id,
            provisioning_profile_id=payload.provisioning_profile_id,
            device_credential_id=payload.device_credential_id,
            channel_type=payload.channel_type.value,
            channel_subject_ref=payload.channel_subject_ref,
            delivery_context=payload.delivery_context,
            delivery_payload=payload.delivery_payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if not result.created:
        http_response.status_code = status.HTTP_200_OK
    return _serialize_access_delivery_channel(result.access_delivery_channel)


@router.post(
    "/resolve/current",
    response_model=ResolveCurrentAccessDeliveryChannelResponse,
    status_code=status.HTTP_201_CREATED,
)
async def resolve_current_access_delivery_channel(
    payload: ResolveCurrentAccessDeliveryChannelRequest,
    http_response: Response,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_mobile_user_id),
    current_realm: RealmResolution = Depends(get_request_customer_realm),
) -> ResolveCurrentAccessDeliveryChannelResponse:
    try:
        result = await ResolveCurrentAccessDeliveryChannelUseCase(db).execute(
            customer_account_id=user_id,
            current_realm=current_realm,
            provider_name=payload.provider_name,
            channel_type=payload.channel_type.value,
            channel_subject_ref=payload.channel_subject_ref,
            provisioning_profile_key=payload.provisioning_profile_key,
            credential_type=payload.credential_type.value if payload.credential_type else None,
            credential_subject_key=payload.credential_subject_key,
            credential_context=payload.credential_context,
            delivery_context=payload.delivery_context,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if not result.access_delivery_channel_created:
        http_response.status_code = status.HTTP_200_OK
    return ResolveCurrentAccessDeliveryChannelResponse(
        service_identity_id=result.service_identity.id,
        service_key=result.service_identity.service_key,
        auth_realm_id=result.service_identity.auth_realm_id,
        provider_name=result.service_identity.provider_name,
        provisioning_profile_id=result.provisioning_profile.id,
        provisioning_profile_key=result.provisioning_profile.profile_key,
        access_delivery_channel=_serialize_access_delivery_channel(result.access_delivery_channel),
        device_credential=(
            _serialize_device_credential(result.device_credential) if result.device_credential is not None else None
        ),
        entitlement_status=result.entitlement_snapshot.get("status", "none"),
        effective_entitlements=dict(result.entitlement_snapshot.get("effective_entitlements") or {}),
    )


@router.post(
    "/current/service-state",
    response_model=CurrentServiceStateResponse,
    status_code=status.HTTP_200_OK,
)
async def get_current_service_state(
    payload: GetCurrentServiceStateRequest,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_mobile_user_id),
    current_realm: RealmResolution = Depends(get_request_customer_realm),
) -> CurrentServiceStateResponse:
    try:
        result = await GetCurrentServiceStateUseCase(db).execute(
            customer_account_id=user_id,
            current_realm=current_realm,
            provider_name=payload.provider_name,
            channel_type=payload.channel_type.value if payload.channel_type else None,
            channel_subject_ref=payload.channel_subject_ref,
            provisioning_profile_key=payload.provisioning_profile_key,
            credential_type=payload.credential_type.value if payload.credential_type else None,
            credential_subject_key=payload.credential_subject_key,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return CurrentServiceStateResponse(
        customer_account_id=user_id,
        auth_realm_id=current_realm.auth_realm.id,
        provider_name=payload.provider_name,
        entitlement_snapshot=result.entitlement_snapshot,
        service_identity=(
            _serialize_service_identity(result.service_identity) if result.service_identity is not None else None
        ),
        provisioning_profile=(
            _serialize_provisioning_profile(result.provisioning_profile)
            if result.provisioning_profile is not None
            else None
        ),
        device_credential=(
            _serialize_device_credential(result.device_credential) if result.device_credential is not None else None
        ),
        access_delivery_channel=(
            _serialize_access_delivery_channel(result.access_delivery_channel)
            if result.access_delivery_channel is not None
            else None
        ),
        purchase_context=_serialize_purchase_context(result.active_entitlement_grant),
        consumption_context=CurrentServiceStateConsumptionContextResponse(
            channel_type=payload.channel_type,
            channel_subject_ref=(
                result.resolved_channel_subject_ref or payload.channel_subject_ref or payload.credential_subject_key
            ),
            provisioning_profile_key=(
                result.resolved_provisioning_profile_key or payload.provisioning_profile_key
            ),
            credential_type=payload.credential_type,
            credential_subject_key=payload.credential_subject_key,
        ),
    )


@router.get("/", response_model=list[AccessDeliveryChannelResponse])
async def list_access_delivery_channels(
    service_identity_id: UUID | None = Query(None),
    auth_realm_id: UUID | None = Query(None),
    provisioning_profile_id: UUID | None = Query(None),
    device_credential_id: UUID | None = Query(None),
    channel_type: AccessDeliveryChannelType | None = Query(None),
    channel_status: AccessDeliveryChannelStatus | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.SUPPORT)),
) -> list[AccessDeliveryChannelResponse]:
    items = await ListAccessDeliveryChannelsUseCase(db).execute(
        service_identity_id=service_identity_id,
        auth_realm_id=auth_realm_id,
        provisioning_profile_id=provisioning_profile_id,
        device_credential_id=device_credential_id,
        channel_type=channel_type.value if channel_type else None,
        channel_status=channel_status.value if channel_status else None,
        limit=limit,
        offset=offset,
    )
    return [_serialize_access_delivery_channel(item) for item in items]


@router.get("/{access_delivery_channel_id}", response_model=AccessDeliveryChannelResponse)
async def get_access_delivery_channel(
    access_delivery_channel_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.SUPPORT)),
) -> AccessDeliveryChannelResponse:
    item = await GetAccessDeliveryChannelUseCase(db).execute(access_delivery_channel_id=access_delivery_channel_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Access delivery channel not found")
    return _serialize_access_delivery_channel(item)


@router.post("/{access_delivery_channel_id}/archive", response_model=AccessDeliveryChannelResponse)
async def archive_access_delivery_channel(
    access_delivery_channel_id: UUID,
    payload: AccessDeliveryChannelTransitionRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> AccessDeliveryChannelResponse:
    try:
        item = await ArchiveAccessDeliveryChannelUseCase(db).execute(
            access_delivery_channel_id=access_delivery_channel_id,
            archived_by_admin_user_id=current_admin.id,
            reason_code=payload.reason_code,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_access_delivery_channel(item)
