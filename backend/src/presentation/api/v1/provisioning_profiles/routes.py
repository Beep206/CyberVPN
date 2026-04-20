from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.service_access import (
    CreateProvisioningProfileUseCase,
    GetProvisioningProfileUseCase,
    ListProvisioningProfilesUseCase,
)
from src.domain.enums import AdminRole, ProvisioningProfileStatus
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_role

from .schemas import CreateProvisioningProfileRequest, ProvisioningProfileResponse

router = APIRouter(prefix="/provisioning-profiles", tags=["provisioning-profiles"])


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


@router.post("/", response_model=ProvisioningProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_provisioning_profile(
    payload: CreateProvisioningProfileRequest,
    http_response: Response,
    db: AsyncSession = Depends(get_db),
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
) -> ProvisioningProfileResponse:
    try:
        result = await CreateProvisioningProfileUseCase(db).execute(
            service_identity_id=payload.service_identity_id,
            profile_key=payload.profile_key,
            target_channel=payload.target_channel,
            delivery_method=payload.delivery_method,
            profile_status=payload.profile_status.value,
            provider_profile_ref=payload.provider_profile_ref,
            provisioning_payload=payload.provisioning_payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if not result.created:
        http_response.status_code = status.HTTP_200_OK
    return _serialize_provisioning_profile(result.provisioning_profile)


@router.get("/", response_model=list[ProvisioningProfileResponse])
async def list_provisioning_profiles(
    service_identity_id: UUID | None = Query(None),
    target_channel: str | None = Query(None),
    delivery_method: str | None = Query(None),
    profile_status: ProvisioningProfileStatus | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.SUPPORT)),
) -> list[ProvisioningProfileResponse]:
    items = await ListProvisioningProfilesUseCase(db).execute(
        service_identity_id=service_identity_id,
        target_channel=target_channel,
        delivery_method=delivery_method,
        profile_status=profile_status.value if profile_status else None,
        limit=limit,
        offset=offset,
    )
    return [_serialize_provisioning_profile(item) for item in items]


@router.get("/{provisioning_profile_id}", response_model=ProvisioningProfileResponse)
async def get_provisioning_profile(
    provisioning_profile_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.SUPPORT)),
) -> ProvisioningProfileResponse:
    item = await GetProvisioningProfileUseCase(db).execute(provisioning_profile_id=provisioning_profile_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provisioning profile not found")
    return _serialize_provisioning_profile(item)
