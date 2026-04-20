from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.access_delivery_channel_model import AccessDeliveryChannelModel
from src.infrastructure.database.models.device_credential_model import DeviceCredentialModel
from src.infrastructure.database.models.entitlement_grant_model import EntitlementGrantModel
from src.infrastructure.database.models.provisioning_profile_model import ProvisioningProfileModel
from src.infrastructure.database.models.service_identity_model import ServiceIdentityModel


class ServiceAccessRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_service_identity(self, model: ServiceIdentityModel) -> ServiceIdentityModel:
        self._session.add(model)
        await self._session.flush()
        return model

    async def get_service_identity_by_id(self, service_identity_id: UUID) -> ServiceIdentityModel | None:
        return await self._session.get(ServiceIdentityModel, service_identity_id)

    async def get_service_identity_by_service_key(self, service_key: str) -> ServiceIdentityModel | None:
        result = await self._session.execute(
            select(ServiceIdentityModel).where(ServiceIdentityModel.service_key == service_key)
        )
        return result.scalar_one_or_none()

    async def get_service_identity_by_customer_realm_provider(
        self,
        *,
        customer_account_id: UUID,
        auth_realm_id: UUID,
        provider_name: str,
    ) -> ServiceIdentityModel | None:
        result = await self._session.execute(
            select(ServiceIdentityModel).where(
                ServiceIdentityModel.customer_account_id == customer_account_id,
                ServiceIdentityModel.auth_realm_id == auth_realm_id,
                ServiceIdentityModel.provider_name == provider_name,
            )
        )
        return result.scalar_one_or_none()

    async def list_service_identities(
        self,
        *,
        customer_account_id: UUID | None = None,
        auth_realm_id: UUID | None = None,
        source_order_id: UUID | None = None,
        provider_name: str | None = None,
        identity_status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ServiceIdentityModel]:
        query = select(ServiceIdentityModel)
        if customer_account_id is not None:
            query = query.where(ServiceIdentityModel.customer_account_id == customer_account_id)
        if auth_realm_id is not None:
            query = query.where(ServiceIdentityModel.auth_realm_id == auth_realm_id)
        if source_order_id is not None:
            query = query.where(ServiceIdentityModel.source_order_id == source_order_id)
        if provider_name is not None:
            query = query.where(ServiceIdentityModel.provider_name == provider_name)
        if identity_status is not None:
            query = query.where(ServiceIdentityModel.identity_status == identity_status)
        query = query.order_by(ServiceIdentityModel.created_at.desc()).offset(offset).limit(limit)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def create_provisioning_profile(self, model: ProvisioningProfileModel) -> ProvisioningProfileModel:
        self._session.add(model)
        await self._session.flush()
        return model

    async def get_provisioning_profile_by_id(self, provisioning_profile_id: UUID) -> ProvisioningProfileModel | None:
        return await self._session.get(ProvisioningProfileModel, provisioning_profile_id)

    async def get_provisioning_profile_by_service_identity_and_key(
        self,
        *,
        service_identity_id: UUID,
        profile_key: str,
    ) -> ProvisioningProfileModel | None:
        result = await self._session.execute(
            select(ProvisioningProfileModel).where(
                ProvisioningProfileModel.service_identity_id == service_identity_id,
                ProvisioningProfileModel.profile_key == profile_key,
            )
        )
        return result.scalar_one_or_none()

    async def list_provisioning_profiles(
        self,
        *,
        service_identity_id: UUID | None = None,
        target_channel: str | None = None,
        delivery_method: str | None = None,
        profile_status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ProvisioningProfileModel]:
        query = select(ProvisioningProfileModel)
        if service_identity_id is not None:
            query = query.where(ProvisioningProfileModel.service_identity_id == service_identity_id)
        if target_channel is not None:
            query = query.where(ProvisioningProfileModel.target_channel == target_channel)
        if delivery_method is not None:
            query = query.where(ProvisioningProfileModel.delivery_method == delivery_method)
        if profile_status is not None:
            query = query.where(ProvisioningProfileModel.profile_status == profile_status)
        query = query.order_by(ProvisioningProfileModel.created_at.desc()).offset(offset).limit(limit)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def create_device_credential(self, model: DeviceCredentialModel) -> DeviceCredentialModel:
        self._session.add(model)
        await self._session.flush()
        return model

    async def get_device_credential_by_id(self, device_credential_id: UUID) -> DeviceCredentialModel | None:
        return await self._session.get(DeviceCredentialModel, device_credential_id)

    async def get_device_credential_by_service_identity_type_subject(
        self,
        *,
        service_identity_id: UUID,
        credential_type: str,
        subject_key: str,
    ) -> DeviceCredentialModel | None:
        result = await self._session.execute(
            select(DeviceCredentialModel).where(
                DeviceCredentialModel.service_identity_id == service_identity_id,
                DeviceCredentialModel.credential_type == credential_type,
                DeviceCredentialModel.subject_key == subject_key,
            )
        )
        return result.scalar_one_or_none()

    async def list_device_credentials(
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
        query = select(DeviceCredentialModel)
        if service_identity_id is not None:
            query = query.where(DeviceCredentialModel.service_identity_id == service_identity_id)
        if auth_realm_id is not None:
            query = query.where(DeviceCredentialModel.auth_realm_id == auth_realm_id)
        if provisioning_profile_id is not None:
            query = query.where(DeviceCredentialModel.provisioning_profile_id == provisioning_profile_id)
        if credential_type is not None:
            query = query.where(DeviceCredentialModel.credential_type == credential_type)
        if credential_status is not None:
            query = query.where(DeviceCredentialModel.credential_status == credential_status)
        query = query.order_by(DeviceCredentialModel.created_at.desc()).offset(offset).limit(limit)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def create_access_delivery_channel(
        self,
        model: AccessDeliveryChannelModel,
    ) -> AccessDeliveryChannelModel:
        self._session.add(model)
        await self._session.flush()
        return model

    async def get_access_delivery_channel_by_id(
        self,
        access_delivery_channel_id: UUID,
    ) -> AccessDeliveryChannelModel | None:
        return await self._session.get(AccessDeliveryChannelModel, access_delivery_channel_id)

    async def get_access_delivery_channel_by_service_identity_type_subject(
        self,
        *,
        service_identity_id: UUID,
        channel_type: str,
        channel_subject_ref: str,
    ) -> AccessDeliveryChannelModel | None:
        result = await self._session.execute(
            select(AccessDeliveryChannelModel).where(
                AccessDeliveryChannelModel.service_identity_id == service_identity_id,
                AccessDeliveryChannelModel.channel_type == channel_type,
                AccessDeliveryChannelModel.channel_subject_ref == channel_subject_ref,
            )
        )
        return result.scalar_one_or_none()

    async def list_access_delivery_channels(
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
        query = select(AccessDeliveryChannelModel)
        if service_identity_id is not None:
            query = query.where(AccessDeliveryChannelModel.service_identity_id == service_identity_id)
        if auth_realm_id is not None:
            query = query.where(AccessDeliveryChannelModel.auth_realm_id == auth_realm_id)
        if provisioning_profile_id is not None:
            query = query.where(AccessDeliveryChannelModel.provisioning_profile_id == provisioning_profile_id)
        if device_credential_id is not None:
            query = query.where(AccessDeliveryChannelModel.device_credential_id == device_credential_id)
        if channel_type is not None:
            query = query.where(AccessDeliveryChannelModel.channel_type == channel_type)
        if channel_status is not None:
            query = query.where(AccessDeliveryChannelModel.channel_status == channel_status)
        query = query.order_by(AccessDeliveryChannelModel.created_at.desc()).offset(offset).limit(limit)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def create_entitlement_grant(self, model: EntitlementGrantModel) -> EntitlementGrantModel:
        self._session.add(model)
        await self._session.flush()
        return model

    async def get_entitlement_grant_by_id(self, entitlement_grant_id: UUID) -> EntitlementGrantModel | None:
        return await self._session.get(EntitlementGrantModel, entitlement_grant_id)

    async def get_entitlement_grant_by_source_order_id(
        self,
        *,
        source_order_id: UUID,
    ) -> EntitlementGrantModel | None:
        result = await self._session.execute(
            select(EntitlementGrantModel).where(EntitlementGrantModel.source_order_id == source_order_id)
        )
        return result.scalar_one_or_none()

    async def get_entitlement_grant_by_source_growth_reward_allocation_id(
        self,
        *,
        source_growth_reward_allocation_id: UUID,
    ) -> EntitlementGrantModel | None:
        result = await self._session.execute(
            select(EntitlementGrantModel).where(
                EntitlementGrantModel.source_growth_reward_allocation_id == source_growth_reward_allocation_id
            )
        )
        return result.scalar_one_or_none()

    async def get_entitlement_grant_by_source_renewal_order_id(
        self,
        *,
        source_renewal_order_id: UUID,
    ) -> EntitlementGrantModel | None:
        result = await self._session.execute(
            select(EntitlementGrantModel).where(
                EntitlementGrantModel.source_renewal_order_id == source_renewal_order_id
            )
        )
        return result.scalar_one_or_none()

    async def get_entitlement_grant_by_manual_source_key(
        self,
        *,
        manual_source_key: str,
    ) -> EntitlementGrantModel | None:
        result = await self._session.execute(
            select(EntitlementGrantModel).where(EntitlementGrantModel.manual_source_key == manual_source_key)
        )
        return result.scalar_one_or_none()

    async def list_entitlement_grants(
        self,
        *,
        service_identity_id: UUID | None = None,
        customer_account_id: UUID | None = None,
        auth_realm_id: UUID | None = None,
        source_type: str | None = None,
        grant_status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[EntitlementGrantModel]:
        query = select(EntitlementGrantModel)
        if service_identity_id is not None:
            query = query.where(EntitlementGrantModel.service_identity_id == service_identity_id)
        if customer_account_id is not None:
            query = query.where(EntitlementGrantModel.customer_account_id == customer_account_id)
        if auth_realm_id is not None:
            query = query.where(EntitlementGrantModel.auth_realm_id == auth_realm_id)
        if source_type is not None:
            query = query.where(EntitlementGrantModel.source_type == source_type)
        if grant_status is not None:
            query = query.where(EntitlementGrantModel.grant_status == grant_status)
        query = query.order_by(EntitlementGrantModel.created_at.desc()).offset(offset).limit(limit)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def has_any_entitlement_grants_for_customer_realm(
        self,
        *,
        customer_account_id: UUID,
        auth_realm_id: UUID,
    ) -> bool:
        result = await self._session.execute(
            select(EntitlementGrantModel.id).where(
                EntitlementGrantModel.customer_account_id == customer_account_id,
                EntitlementGrantModel.auth_realm_id == auth_realm_id,
            ).limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def get_current_active_entitlement_grant(
        self,
        *,
        customer_account_id: UUID,
        auth_realm_id: UUID,
        now,
    ) -> EntitlementGrantModel | None:
        result = await self._session.execute(
            select(EntitlementGrantModel).where(
                EntitlementGrantModel.customer_account_id == customer_account_id,
                EntitlementGrantModel.auth_realm_id == auth_realm_id,
                EntitlementGrantModel.grant_status == "active",
                (EntitlementGrantModel.expires_at.is_(None) | (EntitlementGrantModel.expires_at > now)),
            ).order_by(
                EntitlementGrantModel.effective_from.desc(),
                EntitlementGrantModel.created_at.desc(),
            ).limit(1)
        )
        return result.scalar_one_or_none()
