from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.entitlements_service import EntitlementsService
from src.application.use_cases.service_access.access_delivery_channels import (
    _default_channel_subject_ref,
    _default_provisioning_profile_key,
)
from src.infrastructure.database.models.order_model import OrderModel
from src.infrastructure.database.repositories.service_access_repo import ServiceAccessRepository


@dataclass(frozen=True)
class GetServiceAccessObservabilityResult:
    customer_account_id: UUID
    auth_realm_id: UUID
    provider_name: str
    entitlement_snapshot: dict[str, Any]
    active_entitlement_grant: Any | None
    service_identity: Any | None
    source_order: OrderModel | None
    provisioning_profiles: list[Any]
    device_credentials: list[Any]
    access_delivery_channels: list[Any]
    selected_provisioning_profile: Any | None
    selected_device_credential: Any | None
    selected_access_delivery_channel: Any | None
    resolved_provisioning_profile_key: str | None
    resolved_channel_subject_ref: str | None
    lookup_mode: str


class GetServiceAccessObservabilityUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ServiceAccessRepository(session)
        self._entitlements = EntitlementsService(session)

    async def execute(
        self,
        *,
        service_identity_id: UUID | None = None,
        customer_account_id: UUID | None = None,
        auth_realm_id: UUID | None = None,
        provider_name: str | None = None,
        channel_type: str | None = None,
        channel_subject_ref: str | None = None,
        provisioning_profile_key: str | None = None,
        credential_type: str | None = None,
        credential_subject_key: str | None = None,
    ) -> GetServiceAccessObservabilityResult:
        if bool(credential_type) ^ bool(credential_subject_key):
            raise ValueError("credential_type and credential_subject_key must be provided together")

        service_identity = None
        lookup_mode = "customer_realm_provider"
        if service_identity_id is not None:
            service_identity = await self._repo.get_service_identity_by_id(service_identity_id)
            if service_identity is None:
                raise ValueError("Service identity not found")
            customer_account_id = service_identity.customer_account_id
            auth_realm_id = service_identity.auth_realm_id
            provider_name = service_identity.provider_name
            lookup_mode = "service_identity"
        else:
            if customer_account_id is None or auth_realm_id is None or provider_name is None:
                raise ValueError(
                    "Either service_identity_id or customer_account_id + auth_realm_id + provider_name is required"
                )
            service_identity = await self._repo.get_service_identity_by_customer_realm_provider(
                customer_account_id=customer_account_id,
                auth_realm_id=auth_realm_id,
                provider_name=provider_name,
            )

        entitlement_snapshot = await self._entitlements.get_current_snapshot(
            customer_account_id,
            auth_realm_id=auth_realm_id,
        )
        active_entitlement_grant = await self._repo.get_current_active_entitlement_grant(
            customer_account_id=customer_account_id,
            auth_realm_id=auth_realm_id,
            now=datetime.now(UTC),
        )

        source_order_id = None
        if active_entitlement_grant is not None and active_entitlement_grant.source_order_id is not None:
            source_order_id = active_entitlement_grant.source_order_id
        elif service_identity is not None and service_identity.source_order_id is not None:
            source_order_id = service_identity.source_order_id
        source_order = await self._session.get(OrderModel, source_order_id) if source_order_id is not None else None

        provisioning_profiles: list[Any] = []
        device_credentials: list[Any] = []
        access_delivery_channels: list[Any] = []
        selected_provisioning_profile = None
        selected_device_credential = None
        selected_access_delivery_channel = None

        resolved_provisioning_profile_key = provisioning_profile_key or (
            _default_provisioning_profile_key(channel_type) if channel_type else None
        )
        resolved_channel_subject_ref = channel_subject_ref

        if service_identity is not None:
            provisioning_profiles = await self._repo.list_provisioning_profiles(
                service_identity_id=service_identity.id,
                target_channel=None,
                delivery_method=None,
                profile_status=None,
                limit=200,
                offset=0,
            )
            device_credentials = await self._repo.list_device_credentials(
                service_identity_id=service_identity.id,
                auth_realm_id=None,
                provisioning_profile_id=None,
                credential_type=credential_type,
                credential_status=None,
                limit=200,
                offset=0,
            )
            access_delivery_channels = await self._repo.list_access_delivery_channels(
                service_identity_id=service_identity.id,
                auth_realm_id=None,
                provisioning_profile_id=None,
                device_credential_id=None,
                channel_type=channel_type,
                channel_status=None,
                limit=200,
                offset=0,
            )

            if resolved_provisioning_profile_key is not None:
                selected_provisioning_profile = next(
                    (item for item in provisioning_profiles if item.profile_key == resolved_provisioning_profile_key),
                    None,
                )

            if credential_type is not None and credential_subject_key is not None:
                selected_device_credential = await self._repo.get_device_credential_by_service_identity_type_subject(
                    service_identity_id=service_identity.id,
                    credential_type=credential_type,
                    subject_key=credential_subject_key,
                )

            if channel_type is not None:
                if resolved_channel_subject_ref is None:
                    resolved_channel_subject_ref = _default_channel_subject_ref(
                        channel_type=channel_type,
                        provided_subject_ref=None,
                        credential_subject_key=credential_subject_key,
                        service_identity_key=service_identity.service_key,
                    )
                selected_access_delivery_channel = next(
                    (
                        item
                        for item in access_delivery_channels
                        if item.channel_subject_ref == resolved_channel_subject_ref
                    ),
                    None,
                )

        return GetServiceAccessObservabilityResult(
            customer_account_id=customer_account_id,
            auth_realm_id=auth_realm_id,
            provider_name=provider_name,
            entitlement_snapshot=entitlement_snapshot,
            active_entitlement_grant=active_entitlement_grant,
            service_identity=service_identity,
            source_order=source_order,
            provisioning_profiles=provisioning_profiles,
            device_credentials=device_credentials,
            access_delivery_channels=access_delivery_channels,
            selected_provisioning_profile=selected_provisioning_profile,
            selected_device_credential=selected_device_credential,
            selected_access_delivery_channel=selected_access_delivery_channel,
            resolved_provisioning_profile_key=resolved_provisioning_profile_key,
            resolved_channel_subject_ref=resolved_channel_subject_ref,
            lookup_mode=lookup_mode,
        )
