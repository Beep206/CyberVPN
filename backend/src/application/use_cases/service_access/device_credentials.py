from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.device_credential_model import DeviceCredentialModel
from src.infrastructure.database.repositories.service_access_repo import ServiceAccessRepository


@dataclass(frozen=True)
class CreateDeviceCredentialResult:
    created: bool
    device_credential: DeviceCredentialModel


class CreateDeviceCredentialUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = ServiceAccessRepository(session)

    async def execute(
        self,
        *,
        service_identity_id: UUID,
        credential_type: str,
        subject_key: str,
        provisioning_profile_id: UUID | None = None,
        provider_credential_ref: str | None = None,
        credential_context: dict[str, Any] | None = None,
    ) -> CreateDeviceCredentialResult:
        service_identity = await self._repo.get_service_identity_by_id(service_identity_id)
        if service_identity is None:
            raise ValueError("Service identity not found")

        if provisioning_profile_id is not None:
            provisioning_profile = await self._repo.get_provisioning_profile_by_id(provisioning_profile_id)
            if provisioning_profile is None:
                raise ValueError("Provisioning profile not found")
            if provisioning_profile.service_identity_id != service_identity_id:
                raise ValueError("Provisioning profile does not belong to service identity")

        existing = await self._repo.get_device_credential_by_service_identity_type_subject(
            service_identity_id=service_identity_id,
            credential_type=credential_type,
            subject_key=subject_key,
        )
        if existing is not None:
            return CreateDeviceCredentialResult(created=False, device_credential=existing)

        model = DeviceCredentialModel(
            id=uuid.uuid4(),
            credential_key=f"dcred_{uuid.uuid4().hex}",
            service_identity_id=service_identity_id,
            auth_realm_id=service_identity.auth_realm_id,
            origin_storefront_id=service_identity.origin_storefront_id,
            provisioning_profile_id=provisioning_profile_id,
            credential_type=credential_type,
            credential_status="active",
            subject_key=subject_key,
            provider_name=service_identity.provider_name,
            provider_credential_ref=provider_credential_ref,
            credential_context=dict(credential_context or {}),
        )
        created = await self._repo.create_device_credential(model)
        return CreateDeviceCredentialResult(created=True, device_credential=created)


class GetDeviceCredentialUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = ServiceAccessRepository(session)

    async def execute(self, *, device_credential_id: UUID) -> DeviceCredentialModel | None:
        return await self._repo.get_device_credential_by_id(device_credential_id)


class ListDeviceCredentialsUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = ServiceAccessRepository(session)

    async def execute(
        self,
        *,
        service_identity_id: UUID | None = None,
        auth_realm_id: UUID | None = None,
        provisioning_profile_id: UUID | None = None,
        credential_type: str | None = None,
        credential_status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[DeviceCredentialModel]:
        return await self._repo.list_device_credentials(
            service_identity_id=service_identity_id,
            auth_realm_id=auth_realm_id,
            provisioning_profile_id=provisioning_profile_id,
            credential_type=credential_type,
            credential_status=credential_status,
            limit=limit,
            offset=offset,
        )


class TouchDeviceCredentialUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ServiceAccessRepository(session)

    async def execute(self, *, device_credential_id: UUID) -> DeviceCredentialModel:
        item = await self._repo.get_device_credential_by_id(device_credential_id)
        if item is None:
            raise ValueError("Device credential not found")
        if item.credential_status != "active":
            raise ValueError("Device credential is not active")
        item.last_used_at = datetime.now(UTC)
        await self._session.flush()
        return item


class RevokeDeviceCredentialUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ServiceAccessRepository(session)

    async def execute(
        self,
        *,
        device_credential_id: UUID,
        revoked_by_admin_user_id: UUID,
        reason_code: str | None = None,
    ) -> DeviceCredentialModel:
        item = await self._repo.get_device_credential_by_id(device_credential_id)
        if item is None:
            raise ValueError("Device credential not found")
        if item.credential_status == "revoked":
            return item
        item.credential_status = "revoked"
        item.revoked_at = datetime.now(UTC)
        item.revoked_by_admin_user_id = revoked_by_admin_user_id
        item.revoke_reason_code = reason_code
        await self._session.flush()
        return item
