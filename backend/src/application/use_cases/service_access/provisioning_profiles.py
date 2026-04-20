from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.provisioning_profile_model import ProvisioningProfileModel
from src.infrastructure.database.repositories.service_access_repo import ServiceAccessRepository


@dataclass(frozen=True)
class CreateProvisioningProfileResult:
    created: bool
    provisioning_profile: ProvisioningProfileModel


class CreateProvisioningProfileUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = ServiceAccessRepository(session)

    async def execute(
        self,
        *,
        service_identity_id: UUID,
        profile_key: str,
        target_channel: str,
        delivery_method: str,
        profile_status: str = "active",
        provider_profile_ref: str | None = None,
        provisioning_payload: dict[str, Any] | None = None,
    ) -> CreateProvisioningProfileResult:
        service_identity = await self._repo.get_service_identity_by_id(service_identity_id)
        if service_identity is None:
            raise ValueError("Service identity not found")

        existing = await self._repo.get_provisioning_profile_by_service_identity_and_key(
            service_identity_id=service_identity_id,
            profile_key=profile_key,
        )
        if existing is not None:
            return CreateProvisioningProfileResult(created=False, provisioning_profile=existing)

        model = ProvisioningProfileModel(
            service_identity_id=service_identity_id,
            profile_key=profile_key,
            target_channel=target_channel,
            delivery_method=delivery_method,
            profile_status=profile_status,
            provider_name=service_identity.provider_name,
            provider_profile_ref=provider_profile_ref,
            provisioning_payload=dict(provisioning_payload or {}),
        )
        created = await self._repo.create_provisioning_profile(model)
        return CreateProvisioningProfileResult(created=True, provisioning_profile=created)


class GetProvisioningProfileUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = ServiceAccessRepository(session)

    async def execute(self, *, provisioning_profile_id: UUID) -> ProvisioningProfileModel | None:
        return await self._repo.get_provisioning_profile_by_id(provisioning_profile_id)


class ListProvisioningProfilesUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = ServiceAccessRepository(session)

    async def execute(
        self,
        *,
        service_identity_id: UUID | None = None,
        target_channel: str | None = None,
        delivery_method: str | None = None,
        profile_status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ProvisioningProfileModel]:
        return await self._repo.list_provisioning_profiles(
            service_identity_id=service_identity_id,
            target_channel=target_channel,
            delivery_method=delivery_method,
            profile_status=profile_status,
            limit=limit,
            offset=offset,
        )
