from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.entitlements_service import EntitlementsService
from src.application.use_cases.auth_realms import RealmResolution
from src.application.use_cases.service_access.device_credentials import (
    CreateDeviceCredentialResult,
    CreateDeviceCredentialUseCase,
    TouchDeviceCredentialUseCase,
)
from src.application.use_cases.service_access.provisioning_profiles import (
    CreateProvisioningProfileResult,
    CreateProvisioningProfileUseCase,
)
from src.application.use_cases.service_access.service_identities import (
    CreateServiceIdentityResult,
    CreateServiceIdentityUseCase,
)
from src.infrastructure.database.models.access_delivery_channel_model import AccessDeliveryChannelModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.repositories.service_access_repo import ServiceAccessRepository


def _default_provisioning_profile_key(channel_type: str) -> str:
    return f"{channel_type}-default"


def _default_target_channel(channel_type: str) -> str:
    if channel_type == "telegram_bot":
        return "telegram_bot"
    if channel_type == "desktop_manifest":
        return "desktop"
    return "shared_clients"


def _default_channel_subject_ref(
    *,
    channel_type: str,
    provided_subject_ref: str | None,
    credential_subject_key: str | None,
    service_identity_key: str,
) -> str:
    if provided_subject_ref:
        return provided_subject_ref
    if credential_subject_key:
        return credential_subject_key
    return f"{channel_type}:{service_identity_key}"


@dataclass(frozen=True)
class CreateAccessDeliveryChannelResult:
    created: bool
    access_delivery_channel: AccessDeliveryChannelModel


@dataclass(frozen=True)
class ResolveCurrentAccessDeliveryChannelResult:
    service_identity_created: bool
    provisioning_profile_created: bool
    device_credential_created: bool
    access_delivery_channel_created: bool
    service_identity: Any
    provisioning_profile: Any
    device_credential: Any | None
    access_delivery_channel: AccessDeliveryChannelModel
    entitlement_snapshot: dict[str, Any]


@dataclass(frozen=True)
class GetCurrentServiceStateResult:
    entitlement_snapshot: dict[str, Any]
    active_entitlement_grant: Any | None
    service_identity: Any | None
    provisioning_profile: Any | None
    device_credential: Any | None
    access_delivery_channel: AccessDeliveryChannelModel | None
    resolved_provisioning_profile_key: str | None
    resolved_channel_subject_ref: str | None


class CreateAccessDeliveryChannelUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = ServiceAccessRepository(session)

    async def execute(
        self,
        *,
        service_identity_id: UUID,
        channel_type: str,
        channel_subject_ref: str,
        provisioning_profile_id: UUID | None = None,
        device_credential_id: UUID | None = None,
        delivery_context: dict[str, Any] | None = None,
        delivery_payload: dict[str, Any] | None = None,
    ) -> CreateAccessDeliveryChannelResult:
        service_identity = await self._repo.get_service_identity_by_id(service_identity_id)
        if service_identity is None:
            raise ValueError("Service identity not found")

        if provisioning_profile_id is not None:
            provisioning_profile = await self._repo.get_provisioning_profile_by_id(provisioning_profile_id)
            if provisioning_profile is None:
                raise ValueError("Provisioning profile not found")
            if provisioning_profile.service_identity_id != service_identity_id:
                raise ValueError("Provisioning profile does not belong to service identity")

        if device_credential_id is not None:
            device_credential = await self._repo.get_device_credential_by_id(device_credential_id)
            if device_credential is None:
                raise ValueError("Device credential not found")
            if device_credential.service_identity_id != service_identity_id:
                raise ValueError("Device credential does not belong to service identity")

        existing = await self._repo.get_access_delivery_channel_by_service_identity_type_subject(
            service_identity_id=service_identity_id,
            channel_type=channel_type,
            channel_subject_ref=channel_subject_ref,
        )
        if existing is not None:
            return CreateAccessDeliveryChannelResult(created=False, access_delivery_channel=existing)

        model = AccessDeliveryChannelModel(
            id=uuid.uuid4(),
            delivery_key=f"adch_{uuid.uuid4().hex}",
            service_identity_id=service_identity_id,
            auth_realm_id=service_identity.auth_realm_id,
            origin_storefront_id=service_identity.origin_storefront_id,
            provisioning_profile_id=provisioning_profile_id,
            device_credential_id=device_credential_id,
            channel_type=channel_type,
            channel_status="active",
            channel_subject_ref=channel_subject_ref,
            provider_name=service_identity.provider_name,
            delivery_context=dict(delivery_context or {}),
            delivery_payload=dict(delivery_payload or {}),
        )
        created = await self._repo.create_access_delivery_channel(model)
        return CreateAccessDeliveryChannelResult(created=True, access_delivery_channel=created)


class GetAccessDeliveryChannelUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = ServiceAccessRepository(session)

    async def execute(self, *, access_delivery_channel_id: UUID) -> AccessDeliveryChannelModel | None:
        return await self._repo.get_access_delivery_channel_by_id(access_delivery_channel_id)


class ListAccessDeliveryChannelsUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = ServiceAccessRepository(session)

    async def execute(
        self,
        *,
        service_identity_id: UUID | None = None,
        auth_realm_id: UUID | None = None,
        provisioning_profile_id: UUID | None = None,
        device_credential_id: UUID | None = None,
        channel_type: str | None = None,
        channel_status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AccessDeliveryChannelModel]:
        return await self._repo.list_access_delivery_channels(
            service_identity_id=service_identity_id,
            auth_realm_id=auth_realm_id,
            provisioning_profile_id=provisioning_profile_id,
            device_credential_id=device_credential_id,
            channel_type=channel_type,
            channel_status=channel_status,
            limit=limit,
            offset=offset,
        )


class TouchAccessDeliveryChannelUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ServiceAccessRepository(session)

    async def execute(
        self,
        *,
        access_delivery_channel_id: UUID,
        delivered: bool = False,
    ) -> AccessDeliveryChannelModel:
        item = await self._repo.get_access_delivery_channel_by_id(access_delivery_channel_id)
        if item is None:
            raise ValueError("Access delivery channel not found")
        if item.channel_status != "active":
            raise ValueError("Access delivery channel is not active")
        now = datetime.now(UTC)
        item.last_accessed_at = now
        if delivered:
            item.last_delivered_at = now
        await self._session.flush()
        return item


class ArchiveAccessDeliveryChannelUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ServiceAccessRepository(session)

    async def execute(
        self,
        *,
        access_delivery_channel_id: UUID,
        archived_by_admin_user_id: UUID,
        reason_code: str | None = None,
    ) -> AccessDeliveryChannelModel:
        item = await self._repo.get_access_delivery_channel_by_id(access_delivery_channel_id)
        if item is None:
            raise ValueError("Access delivery channel not found")
        if item.channel_status == "archived":
            return item
        item.channel_status = "archived"
        item.archived_at = datetime.now(UTC)
        item.archived_by_admin_user_id = archived_by_admin_user_id
        item.archive_reason_code = reason_code
        await self._session.flush()
        return item


class GetCurrentServiceStateUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ServiceAccessRepository(session)
        self._entitlements = EntitlementsService(session)

    async def execute(
        self,
        *,
        customer_account_id: UUID,
        current_realm: RealmResolution,
        provider_name: str,
        channel_type: str | None = None,
        channel_subject_ref: str | None = None,
        provisioning_profile_key: str | None = None,
        credential_type: str | None = None,
        credential_subject_key: str | None = None,
    ) -> GetCurrentServiceStateResult:
        customer = await self._session.get(MobileUserModel, customer_account_id)
        if customer is None:
            raise ValueError("Customer account not found")
        if customer.auth_realm_id and customer.auth_realm_id != current_realm.auth_realm.id:
            raise ValueError("Customer account does not belong to auth realm")
        if bool(credential_type) ^ bool(credential_subject_key):
            raise ValueError("credential_type and credential_subject_key must be provided together")

        now = datetime.now(UTC)
        entitlement_snapshot = await self._entitlements.get_current_snapshot(
            customer_account_id,
            auth_realm_id=current_realm.auth_realm.id,
        )
        active_entitlement_grant = await self._repo.get_current_active_entitlement_grant(
            customer_account_id=customer_account_id,
            auth_realm_id=current_realm.auth_realm.id,
            now=now,
        )
        service_identity = await self._repo.get_service_identity_by_customer_realm_provider(
            customer_account_id=customer_account_id,
            auth_realm_id=current_realm.auth_realm.id,
            provider_name=provider_name,
        )

        resolved_provisioning_profile_key: str | None = provisioning_profile_key or (
            _default_provisioning_profile_key(channel_type) if channel_type else None
        )
        provisioning_profile = None
        if service_identity is not None and resolved_provisioning_profile_key is not None:
            provisioning_profile = await self._repo.get_provisioning_profile_by_service_identity_and_key(
                service_identity_id=service_identity.id,
                profile_key=resolved_provisioning_profile_key,
            )

        device_credential = None
        if service_identity is not None and credential_type and credential_subject_key:
            device_credential = await self._repo.get_device_credential_by_service_identity_type_subject(
                service_identity_id=service_identity.id,
                credential_type=credential_type,
                subject_key=credential_subject_key,
            )

        resolved_channel_subject_ref: str | None = None
        access_delivery_channel = None
        if channel_type:
            if channel_subject_ref is not None:
                resolved_channel_subject_ref = channel_subject_ref
            elif credential_subject_key is not None:
                resolved_channel_subject_ref = credential_subject_key
            elif service_identity is not None:
                resolved_channel_subject_ref = _default_channel_subject_ref(
                    channel_type=channel_type,
                    provided_subject_ref=None,
                    credential_subject_key=None,
                    service_identity_key=service_identity.service_key,
                )

            if service_identity is not None and resolved_channel_subject_ref is not None:
                access_delivery_channel = await self._repo.get_access_delivery_channel_by_service_identity_type_subject(
                    service_identity_id=service_identity.id,
                    channel_type=channel_type,
                    channel_subject_ref=resolved_channel_subject_ref,
                )

        return GetCurrentServiceStateResult(
            entitlement_snapshot=entitlement_snapshot,
            active_entitlement_grant=active_entitlement_grant,
            service_identity=service_identity,
            provisioning_profile=provisioning_profile,
            device_credential=device_credential,
            access_delivery_channel=access_delivery_channel,
            resolved_provisioning_profile_key=resolved_provisioning_profile_key,
            resolved_channel_subject_ref=resolved_channel_subject_ref,
        )


class ResolveCurrentAccessDeliveryChannelUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ServiceAccessRepository(session)
        self._entitlements = EntitlementsService(session)

    async def _ensure_current_service_identity(
        self,
        *,
        customer_account_id: UUID,
        current_realm: RealmResolution,
        provider_name: str,
        service_context: dict[str, Any],
    ) -> CreateServiceIdentityResult:
        existing = await self._repo.get_service_identity_by_customer_realm_provider(
            customer_account_id=customer_account_id,
            auth_realm_id=current_realm.auth_realm.id,
            provider_name=provider_name,
        )
        if existing is not None:
            return CreateServiceIdentityResult(created=False, service_identity=existing)

        customer = await self._session.get(MobileUserModel, customer_account_id)
        if customer is None:
            raise ValueError("Customer account not found")
        if customer.auth_realm_id and customer.auth_realm_id != current_realm.auth_realm.id:
            raise ValueError("Customer account does not belong to auth realm")

        provider_subject_ref: str | None = None
        if provider_name == "remnawave":
            provider_subject_ref = customer.remnawave_uuid
        if not provider_subject_ref:
            raise ValueError("Current customer does not have a provider subject reference")

        merged_context = dict(service_context or {})
        merged_context.setdefault("bridge_origin", "access_delivery.resolve_current")
        return await CreateServiceIdentityUseCase(self._session).execute(
            customer_account_id=customer_account_id,
            auth_realm_id=current_realm.auth_realm.id,
            provider_name=provider_name,
            provider_subject_ref=provider_subject_ref,
            service_context=merged_context,
        )

    async def execute(
        self,
        *,
        customer_account_id: UUID,
        current_realm: RealmResolution,
        provider_name: str,
        channel_type: str,
        channel_subject_ref: str | None = None,
        provisioning_profile_key: str | None = None,
        credential_type: str | None = None,
        credential_subject_key: str | None = None,
        credential_context: dict[str, Any] | None = None,
        delivery_context: dict[str, Any] | None = None,
    ) -> ResolveCurrentAccessDeliveryChannelResult:
        entitlement_snapshot = await self._entitlements.get_current_snapshot(
            customer_account_id,
            auth_realm_id=current_realm.auth_realm.id,
        )
        if entitlement_snapshot.get("status") not in {"active", "trial"}:
            raise PermissionError("Current customer is not entitled for service delivery")

        if bool(credential_type) ^ bool(credential_subject_key):
            raise ValueError("credential_type and credential_subject_key must be provided together")

        service_identity_result = await self._ensure_current_service_identity(
            customer_account_id=customer_account_id,
            current_realm=current_realm,
            provider_name=provider_name,
            service_context={
                "resolved_from": "current_access_delivery_channel",
                "realm_key": current_realm.realm_key,
            },
        )
        service_identity = service_identity_result.service_identity

        provisioning_profile_key = provisioning_profile_key or _default_provisioning_profile_key(channel_type)
        provisioning_profile_result: CreateProvisioningProfileResult = await CreateProvisioningProfileUseCase(
            self._session
        ).execute(
            service_identity_id=service_identity.id,
            profile_key=provisioning_profile_key,
            target_channel=_default_target_channel(channel_type),
            delivery_method=channel_type,
            provisioning_payload={
                "resolved_from": "current_access_delivery_channel",
                "channel_type": channel_type,
            },
        )
        provisioning_profile = provisioning_profile_result.provisioning_profile

        device_credential_result: CreateDeviceCredentialResult | None = None
        if credential_type and credential_subject_key:
            device_credential_result = await CreateDeviceCredentialUseCase(self._session).execute(
                service_identity_id=service_identity.id,
                provisioning_profile_id=provisioning_profile.id,
                credential_type=credential_type,
                subject_key=credential_subject_key,
                credential_context={
                    **dict(credential_context or {}),
                    "resolved_from": "current_access_delivery_channel",
                    "realm_key": current_realm.realm_key,
                },
            )
            await TouchDeviceCredentialUseCase(self._session).execute(
                device_credential_id=device_credential_result.device_credential.id
            )
            if device_credential_result.device_credential.credential_status != "active":
                raise PermissionError("Resolved device credential is not active")

        resolved_channel_subject_ref = _default_channel_subject_ref(
            channel_type=channel_type,
            provided_subject_ref=channel_subject_ref,
            credential_subject_key=credential_subject_key,
            service_identity_key=service_identity.service_key,
        )
        channel_result = await CreateAccessDeliveryChannelUseCase(self._session).execute(
            service_identity_id=service_identity.id,
            provisioning_profile_id=provisioning_profile.id,
            device_credential_id=(
                device_credential_result.device_credential.id if device_credential_result is not None else None
            ),
            channel_type=channel_type,
            channel_subject_ref=resolved_channel_subject_ref,
            delivery_context={
                **dict(delivery_context or {}),
                "resolved_from": "current_access_delivery_channel",
                "realm_key": current_realm.realm_key,
            },
            delivery_payload={
                "entitlement_status": entitlement_snapshot.get("status"),
                "provisioning_profile_key": provisioning_profile.profile_key,
                "provider_name": service_identity.provider_name,
            },
        )
        if channel_result.access_delivery_channel.channel_status != "active":
            raise PermissionError("Resolved access delivery channel is not active")
        await TouchAccessDeliveryChannelUseCase(self._session).execute(
            access_delivery_channel_id=channel_result.access_delivery_channel.id,
            delivered=True,
        )

        return ResolveCurrentAccessDeliveryChannelResult(
            service_identity_created=service_identity_result.created,
            provisioning_profile_created=provisioning_profile_result.created,
            device_credential_created=device_credential_result.created if device_credential_result else False,
            access_delivery_channel_created=channel_result.created,
            service_identity=service_identity,
            provisioning_profile=provisioning_profile,
            device_credential=device_credential_result.device_credential if device_credential_result else None,
            access_delivery_channel=channel_result.access_delivery_channel,
            entitlement_snapshot=entitlement_snapshot,
        )
