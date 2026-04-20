from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.service_access import (
    CreateServiceIdentityUseCase,
    GetLegacyServiceAccessShadowUseCase,
    GetServiceAccessObservabilityUseCase,
    GetServiceIdentityUseCase,
    ListServiceIdentitiesUseCase,
    MigrateLegacyServiceAccessUseCase,
)
from src.domain.enums import AccessDeliveryChannelType, AdminRole, DeviceCredentialType, ServiceIdentityStatus
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.presentation.api.v1.device_credentials.schemas import DeviceCredentialResponse
from src.presentation.api.v1.entitlements.routes import _serialize_entitlement_grant
from src.presentation.api.v1.provisioning_profiles.schemas import ProvisioningProfileResponse
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_role

from .schemas import (
    CreateServiceIdentityRequest,
    LegacyServiceAccessShadowRequest,
    LegacyServiceAccessShadowResponse,
    MigrateLegacyServiceAccessResponse,
    ServiceAccessObservabilityRequest,
    ServiceAccessObservabilityResponse,
    ServiceAccessObservedChannelResponse,
    ServiceAccessPurchaseContextResponse,
    ServiceAccessRequestedContextResponse,
    ServiceIdentityResponse,
)

router = APIRouter(prefix="/service-identities", tags=["service-identities"])


def _serialize_service_identity(model) -> ServiceIdentityResponse:
    return ServiceIdentityResponse(
        id=model.id,
        service_key=model.service_key,
        customer_account_id=model.customer_account_id,
        auth_realm_id=model.auth_realm_id,
        source_order_id=model.source_order_id,
        origin_storefront_id=model.origin_storefront_id,
        provider_name=model.provider_name,
        provider_subject_ref=model.provider_subject_ref,
        identity_status=model.identity_status,
        service_context=dict(model.service_context or {}),
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _serialize_provisioning_profile(model) -> ProvisioningProfileResponse:
    return ProvisioningProfileResponse(
        id=model.id,
        service_identity_id=model.service_identity_id,
        profile_key=model.profile_key,
        target_channel=model.target_channel,
        delivery_method=model.delivery_method,
        profile_status=model.profile_status,
        provider_name=model.provider_name,
        provider_profile_ref=model.provider_profile_ref,
        provisioning_payload=dict(model.provisioning_payload or {}),
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _serialize_device_credential(model) -> DeviceCredentialResponse:
    return DeviceCredentialResponse(
        id=model.id,
        credential_key=model.credential_key,
        service_identity_id=model.service_identity_id,
        auth_realm_id=model.auth_realm_id,
        origin_storefront_id=model.origin_storefront_id,
        provisioning_profile_id=model.provisioning_profile_id,
        credential_type=model.credential_type,
        credential_status=model.credential_status,
        subject_key=model.subject_key,
        provider_name=model.provider_name,
        provider_credential_ref=model.provider_credential_ref,
        credential_context=dict(model.credential_context or {}),
        issued_at=model.issued_at,
        last_used_at=model.last_used_at,
        revoked_at=model.revoked_at,
        revoked_by_admin_user_id=model.revoked_by_admin_user_id,
        revoke_reason_code=model.revoke_reason_code,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _serialize_observed_channel(model) -> ServiceAccessObservedChannelResponse:
    return ServiceAccessObservedChannelResponse(
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


def _build_purchase_context(result) -> ServiceAccessPurchaseContextResponse:
    active_entitlement_grant = result.active_entitlement_grant
    source_order = result.source_order
    return ServiceAccessPurchaseContextResponse(
        source_type=active_entitlement_grant.source_type if active_entitlement_grant is not None else None,
        source_order_id=active_entitlement_grant.source_order_id if active_entitlement_grant is not None else None,
        source_order_sale_channel=source_order.sale_channel if source_order is not None else None,
        source_order_status=source_order.order_status if source_order is not None else None,
        source_order_settlement_status=source_order.settlement_status if source_order is not None else None,
        source_order_storefront_id=source_order.storefront_id if source_order is not None else None,
        source_growth_reward_allocation_id=(
            active_entitlement_grant.source_growth_reward_allocation_id
            if active_entitlement_grant is not None
            else None
        ),
        source_renewal_order_id=(
            active_entitlement_grant.source_renewal_order_id if active_entitlement_grant is not None else None
        ),
        manual_source_key=active_entitlement_grant.manual_source_key if active_entitlement_grant is not None else None,
        origin_storefront_id=(
            active_entitlement_grant.origin_storefront_id
            if active_entitlement_grant is not None
            else result.service_identity.origin_storefront_id if result.service_identity is not None else None
        ),
    )


def _build_service_access_observability_response(
    result,
    *,
    channel_type: AccessDeliveryChannelType | None,
    credential_type: DeviceCredentialType | None,
    credential_subject_key: str | None,
) -> ServiceAccessObservabilityResponse:
    return ServiceAccessObservabilityResponse(
        customer_account_id=result.customer_account_id,
        auth_realm_id=result.auth_realm_id,
        provider_name=result.provider_name,
        entitlement_snapshot=result.entitlement_snapshot,
        service_identity=(
            _serialize_service_identity(result.service_identity) if result.service_identity is not None else None
        ),
        active_entitlement_grant=(
            _serialize_entitlement_grant(result.active_entitlement_grant)
            if result.active_entitlement_grant is not None
            else None
        ),
        purchase_context=_build_purchase_context(result),
        requested_context=ServiceAccessRequestedContextResponse(
            lookup_mode=result.lookup_mode,
            channel_type=channel_type,
            channel_subject_ref=result.resolved_channel_subject_ref or credential_subject_key,
            provisioning_profile_key=result.resolved_provisioning_profile_key,
            credential_type=credential_type,
            credential_subject_key=credential_subject_key,
        ),
        selected_provisioning_profile=(
            _serialize_provisioning_profile(result.selected_provisioning_profile)
            if result.selected_provisioning_profile is not None
            else None
        ),
        selected_device_credential=(
            _serialize_device_credential(result.selected_device_credential)
            if result.selected_device_credential is not None
            else None
        ),
        selected_access_delivery_channel=(
            _serialize_observed_channel(result.selected_access_delivery_channel)
            if result.selected_access_delivery_channel is not None
            else None
        ),
        provisioning_profiles=[_serialize_provisioning_profile(item) for item in result.provisioning_profiles],
        device_credentials=[_serialize_device_credential(item) for item in result.device_credentials],
        access_delivery_channels=[_serialize_observed_channel(item) for item in result.access_delivery_channels],
    )


def _build_legacy_shadow_response(result) -> LegacyServiceAccessShadowResponse:
    return LegacyServiceAccessShadowResponse(
        customer_account_id=result.customer_account_id,
        auth_realm_id=result.auth_realm_id,
        provider_name=result.provider_name,
        legacy_provider_subject_ref=result.legacy_provider_subject_ref,
        legacy_subscription_url=result.legacy_subscription_url,
        legacy_entitlement_snapshot=result.legacy_entitlement_snapshot,
        canonical_entitlement_snapshot=result.canonical_entitlement_snapshot,
        service_identity=(
            _serialize_service_identity(result.service_identity) if result.service_identity is not None else None
        ),
        provisioning_profile=(
            _serialize_provisioning_profile(result.provisioning_profile)
            if result.provisioning_profile is not None
            else None
        ),
        access_delivery_channel=(
            _serialize_observed_channel(result.access_delivery_channel)
            if result.access_delivery_channel is not None
            else None
        ),
        mismatch_codes=list(result.mismatch_codes),
    )


@router.post("/", response_model=ServiceIdentityResponse, status_code=status.HTTP_201_CREATED)
async def create_service_identity(
    payload: CreateServiceIdentityRequest,
    http_response: Response,
    db: AsyncSession = Depends(get_db),
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> ServiceIdentityResponse:
    try:
        result = await CreateServiceIdentityUseCase(db).execute(
            customer_account_id=payload.customer_account_id,
            auth_realm_id=payload.auth_realm_id,
            provider_name=payload.provider_name,
            source_order_id=payload.source_order_id,
            origin_storefront_id=payload.origin_storefront_id,
            provider_subject_ref=payload.provider_subject_ref,
            service_context=payload.service_context,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if not result.created:
        http_response.status_code = status.HTTP_200_OK
    return _serialize_service_identity(result.service_identity)


@router.post("/inspect/service-state", response_model=ServiceAccessObservabilityResponse)
async def inspect_service_access_state(
    payload: ServiceAccessObservabilityRequest,
    db: AsyncSession = Depends(get_db),
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.SUPPORT)),
) -> ServiceAccessObservabilityResponse:
    try:
        result = await GetServiceAccessObservabilityUseCase(db).execute(
            service_identity_id=payload.service_identity_id,
            customer_account_id=payload.customer_account_id,
            auth_realm_id=payload.auth_realm_id,
            provider_name=payload.provider_name,
            channel_type=payload.channel_type.value if payload.channel_type else None,
            channel_subject_ref=payload.channel_subject_ref,
            provisioning_profile_key=payload.provisioning_profile_key,
            credential_type=payload.credential_type.value if payload.credential_type else None,
            credential_subject_key=payload.credential_subject_key,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _build_service_access_observability_response(
        result,
        channel_type=payload.channel_type,
        credential_type=payload.credential_type,
        credential_subject_key=payload.credential_subject_key,
    )


@router.post("/legacy/shadow-parity", response_model=LegacyServiceAccessShadowResponse)
async def get_legacy_service_access_shadow_parity(
    payload: LegacyServiceAccessShadowRequest,
    db: AsyncSession = Depends(get_db),
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.SUPPORT)),
) -> LegacyServiceAccessShadowResponse:
    try:
        result = await GetLegacyServiceAccessShadowUseCase(db).execute(
            customer_account_id=payload.customer_account_id,
            auth_realm_id=payload.auth_realm_id,
            provider_name=payload.provider_name,
        )
    except ValueError as exc:
        if str(exc) == "Customer account not found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _build_legacy_shadow_response(result)


@router.post("/legacy/migrate", response_model=MigrateLegacyServiceAccessResponse)
async def migrate_legacy_service_access(
    payload: LegacyServiceAccessShadowRequest,
    db: AsyncSession = Depends(get_db),
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> MigrateLegacyServiceAccessResponse:
    try:
        result = await MigrateLegacyServiceAccessUseCase(db).execute(
            customer_account_id=payload.customer_account_id,
            auth_realm_id=payload.auth_realm_id,
            provider_name=payload.provider_name,
        )
    except ValueError as exc:
        if str(exc) == "Customer account not found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return MigrateLegacyServiceAccessResponse(
        service_identity_created=result.service_identity_created,
        provisioning_profile_created=result.provisioning_profile_created,
        access_delivery_channel_created=result.access_delivery_channel_created,
        service_identity=_serialize_service_identity(result.service_identity),
        provisioning_profile=(
            _serialize_provisioning_profile(result.provisioning_profile)
            if result.provisioning_profile is not None
            else None
        ),
        access_delivery_channel=(
            _serialize_observed_channel(result.access_delivery_channel)
            if result.access_delivery_channel is not None
            else None
        ),
        shadow_before=_build_legacy_shadow_response(result.shadow_before),
        shadow_after=_build_legacy_shadow_response(result.shadow_after),
    )


@router.get("/", response_model=list[ServiceIdentityResponse])
async def list_service_identities(
    customer_account_id: UUID | None = Query(None),
    auth_realm_id: UUID | None = Query(None),
    source_order_id: UUID | None = Query(None),
    provider_name: str | None = Query(None),
    identity_status: ServiceIdentityStatus | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.SUPPORT)),
) -> list[ServiceIdentityResponse]:
    items = await ListServiceIdentitiesUseCase(db).execute(
        customer_account_id=customer_account_id,
        auth_realm_id=auth_realm_id,
        source_order_id=source_order_id,
        provider_name=provider_name,
        identity_status=identity_status.value if identity_status else None,
        limit=limit,
        offset=offset,
    )
    return [_serialize_service_identity(item) for item in items]


@router.get("/{service_identity_id}/service-state", response_model=ServiceAccessObservabilityResponse)
async def get_service_identity_service_state(
    service_identity_id: UUID,
    channel_type: AccessDeliveryChannelType | None = Query(None),
    channel_subject_ref: str | None = Query(None, min_length=1, max_length=160),
    provisioning_profile_key: str | None = Query(None, min_length=1, max_length=120),
    credential_type: DeviceCredentialType | None = Query(None),
    credential_subject_key: str | None = Query(None, min_length=1, max_length=160),
    db: AsyncSession = Depends(get_db),
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.SUPPORT)),
) -> ServiceAccessObservabilityResponse:
    try:
        result = await GetServiceAccessObservabilityUseCase(db).execute(
            service_identity_id=service_identity_id,
            channel_type=channel_type.value if channel_type else None,
            channel_subject_ref=channel_subject_ref,
            provisioning_profile_key=provisioning_profile_key,
            credential_type=credential_type.value if credential_type else None,
            credential_subject_key=credential_subject_key,
        )
    except ValueError as exc:
        if str(exc) == "Service identity not found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _build_service_access_observability_response(
        result,
        channel_type=channel_type,
        credential_type=credential_type,
        credential_subject_key=credential_subject_key,
    )


@router.get("/{service_identity_id}", response_model=ServiceIdentityResponse)
async def get_service_identity(
    service_identity_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.SUPPORT)),
) -> ServiceIdentityResponse:
    item = await GetServiceIdentityUseCase(db).execute(service_identity_id=service_identity_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service identity not found")
    return _serialize_service_identity(item)
