from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.domain.enums import AccessDeliveryChannelType, DeviceCredentialType, ServiceIdentityStatus
from src.presentation.api.v1.device_credentials.schemas import DeviceCredentialResponse
from src.presentation.api.v1.entitlements.schemas import (
    CurrentEntitlementStateResponse,
    EntitlementGrantResponse,
)
from src.presentation.api.v1.provisioning_profiles.schemas import ProvisioningProfileResponse


class CreateServiceIdentityRequest(BaseModel):
    customer_account_id: UUID
    auth_realm_id: UUID
    provider_name: str = Field(..., min_length=1, max_length=40)
    source_order_id: UUID | None = None
    origin_storefront_id: UUID | None = None
    provider_subject_ref: str | None = Field(None, min_length=1, max_length=160)
    service_context: dict[str, Any] = Field(default_factory=dict)


class ServiceIdentityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    id: UUID
    service_key: str
    customer_account_id: UUID
    auth_realm_id: UUID
    source_order_id: UUID | None = None
    origin_storefront_id: UUID | None = None
    provider_name: str
    provider_subject_ref: str | None = None
    identity_status: ServiceIdentityStatus
    service_context: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class ServiceAccessObservabilityRequest(BaseModel):
    service_identity_id: UUID | None = None
    customer_account_id: UUID | None = None
    auth_realm_id: UUID | None = None
    provider_name: str | None = Field(None, min_length=1, max_length=40)
    channel_type: AccessDeliveryChannelType | None = None
    channel_subject_ref: str | None = Field(None, min_length=1, max_length=160)
    provisioning_profile_key: str | None = Field(None, min_length=1, max_length=120)
    credential_type: DeviceCredentialType | None = None
    credential_subject_key: str | None = Field(None, min_length=1, max_length=160)


class ServiceAccessPurchaseContextResponse(BaseModel):
    source_type: str | None = None
    source_order_id: UUID | None = None
    source_order_sale_channel: str | None = None
    source_order_status: str | None = None
    source_order_settlement_status: str | None = None
    source_order_storefront_id: UUID | None = None
    source_growth_reward_allocation_id: UUID | None = None
    source_renewal_order_id: UUID | None = None
    manual_source_key: str | None = None
    origin_storefront_id: UUID | None = None


class ServiceAccessRequestedContextResponse(BaseModel):
    lookup_mode: str
    channel_type: AccessDeliveryChannelType | None = None
    channel_subject_ref: str | None = None
    provisioning_profile_key: str | None = None
    credential_type: DeviceCredentialType | None = None
    credential_subject_key: str | None = None


class ServiceAccessObservedChannelResponse(BaseModel):
    id: UUID
    delivery_key: str
    service_identity_id: UUID
    auth_realm_id: UUID
    origin_storefront_id: UUID | None = None
    provisioning_profile_id: UUID | None = None
    device_credential_id: UUID | None = None
    channel_type: str
    channel_status: str
    channel_subject_ref: str
    provider_name: str
    delivery_context: dict[str, Any]
    delivery_payload: dict[str, Any]
    last_delivered_at: datetime | None = None
    last_accessed_at: datetime | None = None
    archived_at: datetime | None = None
    archived_by_admin_user_id: UUID | None = None
    archive_reason_code: str | None = None
    created_at: datetime
    updated_at: datetime


class LegacyServiceAccessShadowRequest(BaseModel):
    customer_account_id: UUID
    auth_realm_id: UUID
    provider_name: str = Field(..., min_length=1, max_length=40)


class LegacyServiceAccessShadowResponse(BaseModel):
    customer_account_id: UUID
    auth_realm_id: UUID
    provider_name: str
    legacy_provider_subject_ref: str | None = None
    legacy_subscription_url: str | None = None
    legacy_entitlement_snapshot: CurrentEntitlementStateResponse
    canonical_entitlement_snapshot: CurrentEntitlementStateResponse
    service_identity: ServiceIdentityResponse | None = None
    provisioning_profile: ProvisioningProfileResponse | None = None
    access_delivery_channel: ServiceAccessObservedChannelResponse | None = None
    mismatch_codes: list[str] = Field(default_factory=list)


class MigrateLegacyServiceAccessResponse(BaseModel):
    service_identity_created: bool
    provisioning_profile_created: bool
    access_delivery_channel_created: bool
    service_identity: ServiceIdentityResponse
    provisioning_profile: ProvisioningProfileResponse | None = None
    access_delivery_channel: ServiceAccessObservedChannelResponse | None = None
    shadow_before: LegacyServiceAccessShadowResponse
    shadow_after: LegacyServiceAccessShadowResponse


class ServiceAccessObservabilityResponse(BaseModel):
    customer_account_id: UUID
    auth_realm_id: UUID
    provider_name: str
    entitlement_snapshot: CurrentEntitlementStateResponse
    service_identity: ServiceIdentityResponse | None = None
    active_entitlement_grant: EntitlementGrantResponse | None = None
    purchase_context: ServiceAccessPurchaseContextResponse
    requested_context: ServiceAccessRequestedContextResponse
    selected_provisioning_profile: ProvisioningProfileResponse | None = None
    selected_device_credential: DeviceCredentialResponse | None = None
    selected_access_delivery_channel: ServiceAccessObservedChannelResponse | None = None
    provisioning_profiles: list[ProvisioningProfileResponse] = Field(default_factory=list)
    device_credentials: list[DeviceCredentialResponse] = Field(default_factory=list)
    access_delivery_channels: list[ServiceAccessObservedChannelResponse] = Field(default_factory=list)
