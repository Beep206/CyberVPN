from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.domain.enums import AccessDeliveryChannelType, DeviceCredentialType
from src.presentation.api.v1.device_credentials.schemas import DeviceCredentialResponse
from src.presentation.api.v1.entitlements.schemas import CurrentEntitlementStateResponse
from src.presentation.api.v1.provisioning_profiles.schemas import ProvisioningProfileResponse
from src.presentation.api.v1.service_identities.schemas import ServiceIdentityResponse


class CreateAccessDeliveryChannelRequest(BaseModel):
    service_identity_id: UUID
    provisioning_profile_id: UUID | None = None
    device_credential_id: UUID | None = None
    channel_type: AccessDeliveryChannelType
    channel_subject_ref: str = Field(..., min_length=1, max_length=160)
    delivery_context: dict[str, Any] = Field(default_factory=dict)
    delivery_payload: dict[str, Any] = Field(default_factory=dict)


class AccessDeliveryChannelTransitionRequest(BaseModel):
    reason_code: str | None = Field(None, max_length=80)


class ResolveCurrentAccessDeliveryChannelRequest(BaseModel):
    provider_name: str = Field("remnawave", min_length=1, max_length=40)
    channel_type: AccessDeliveryChannelType
    channel_subject_ref: str | None = Field(None, min_length=1, max_length=160)
    provisioning_profile_key: str | None = Field(None, min_length=1, max_length=120)
    credential_type: DeviceCredentialType | None = None
    credential_subject_key: str | None = Field(None, min_length=1, max_length=160)
    credential_context: dict[str, Any] = Field(default_factory=dict)
    delivery_context: dict[str, Any] = Field(default_factory=dict)


class GetCurrentServiceStateRequest(BaseModel):
    provider_name: str = Field("remnawave", min_length=1, max_length=40)
    channel_type: AccessDeliveryChannelType | None = None
    channel_subject_ref: str | None = Field(None, min_length=1, max_length=160)
    provisioning_profile_key: str | None = Field(None, min_length=1, max_length=120)
    credential_type: DeviceCredentialType | None = None
    credential_subject_key: str | None = Field(None, min_length=1, max_length=160)


class AccessDeliveryChannelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class ResolveCurrentAccessDeliveryChannelResponse(BaseModel):
    service_identity_id: UUID
    service_key: str
    auth_realm_id: UUID
    provider_name: str
    provisioning_profile_id: UUID
    provisioning_profile_key: str
    access_delivery_channel: AccessDeliveryChannelResponse
    device_credential: DeviceCredentialResponse | None = None
    entitlement_status: str
    effective_entitlements: dict[str, Any]


class CurrentServiceStatePurchaseContextResponse(BaseModel):
    active_entitlement_grant_id: UUID | None = None
    source_type: str | None = None
    source_order_id: UUID | None = None
    source_growth_reward_allocation_id: UUID | None = None
    source_renewal_order_id: UUID | None = None
    manual_source_key: str | None = None
    origin_storefront_id: UUID | None = None


class CurrentServiceStateConsumptionContextResponse(BaseModel):
    channel_type: AccessDeliveryChannelType | None = None
    channel_subject_ref: str | None = None
    provisioning_profile_key: str | None = None
    credential_type: DeviceCredentialType | None = None
    credential_subject_key: str | None = None


class CurrentServiceStateResponse(BaseModel):
    customer_account_id: UUID
    auth_realm_id: UUID
    provider_name: str
    entitlement_snapshot: CurrentEntitlementStateResponse
    service_identity: ServiceIdentityResponse | None = None
    provisioning_profile: ProvisioningProfileResponse | None = None
    device_credential: DeviceCredentialResponse | None = None
    access_delivery_channel: AccessDeliveryChannelResponse | None = None
    purchase_context: CurrentServiceStatePurchaseContextResponse
    consumption_context: CurrentServiceStateConsumptionContextResponse
