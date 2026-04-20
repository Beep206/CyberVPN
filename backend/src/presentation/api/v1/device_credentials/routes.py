from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.service_access import (
    CreateDeviceCredentialUseCase,
    GetDeviceCredentialUseCase,
    ListDeviceCredentialsUseCase,
    RevokeDeviceCredentialUseCase,
)
from src.domain.enums import AdminRole, DeviceCredentialStatus, DeviceCredentialType
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_role

from .schemas import (
    CreateDeviceCredentialRequest,
    DeviceCredentialResponse,
    DeviceCredentialTransitionRequest,
)

router = APIRouter(prefix="/device-credentials", tags=["device-credentials"])


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


@router.post("/", response_model=DeviceCredentialResponse, status_code=status.HTTP_201_CREATED)
async def create_device_credential(
    payload: CreateDeviceCredentialRequest,
    http_response: Response,
    db: AsyncSession = Depends(get_db),
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> DeviceCredentialResponse:
    try:
        result = await CreateDeviceCredentialUseCase(db).execute(
            service_identity_id=payload.service_identity_id,
            provisioning_profile_id=payload.provisioning_profile_id,
            credential_type=payload.credential_type.value,
            subject_key=payload.subject_key,
            provider_credential_ref=payload.provider_credential_ref,
            credential_context=payload.credential_context,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if not result.created:
        http_response.status_code = status.HTTP_200_OK
    return _serialize_device_credential(result.device_credential)


@router.get("/", response_model=list[DeviceCredentialResponse])
async def list_device_credentials(
    service_identity_id: UUID | None = Query(None),
    auth_realm_id: UUID | None = Query(None),
    provisioning_profile_id: UUID | None = Query(None),
    credential_type: DeviceCredentialType | None = Query(None),
    credential_status: DeviceCredentialStatus | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.SUPPORT)),
) -> list[DeviceCredentialResponse]:
    items = await ListDeviceCredentialsUseCase(db).execute(
        service_identity_id=service_identity_id,
        auth_realm_id=auth_realm_id,
        provisioning_profile_id=provisioning_profile_id,
        credential_type=credential_type.value if credential_type else None,
        credential_status=credential_status.value if credential_status else None,
        limit=limit,
        offset=offset,
    )
    return [_serialize_device_credential(item) for item in items]


@router.get("/{device_credential_id}", response_model=DeviceCredentialResponse)
async def get_device_credential(
    device_credential_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.SUPPORT)),
) -> DeviceCredentialResponse:
    item = await GetDeviceCredentialUseCase(db).execute(device_credential_id=device_credential_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device credential not found")
    return _serialize_device_credential(item)


@router.post("/{device_credential_id}/revoke", response_model=DeviceCredentialResponse)
async def revoke_device_credential(
    device_credential_id: UUID,
    payload: DeviceCredentialTransitionRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> DeviceCredentialResponse:
    try:
        item = await RevokeDeviceCredentialUseCase(db).execute(
            device_credential_id=device_credential_id,
            revoked_by_admin_user_id=current_admin.id,
            reason_code=payload.reason_code,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_device_credential(item)
