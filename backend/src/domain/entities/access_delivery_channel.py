"""Canonical service-consumption delivery channel detached from purchase surface."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class AccessDeliveryChannel:
    id: UUID
    delivery_key: str
    service_identity_id: UUID
    auth_realm_id: UUID
    origin_storefront_id: UUID | None
    provisioning_profile_id: UUID | None
    device_credential_id: UUID | None
    channel_type: str
    channel_status: str
    channel_subject_ref: str
    provider_name: str
    delivery_context: dict
    delivery_payload: dict
    last_delivered_at: datetime | None
    last_accessed_at: datetime | None
    archived_at: datetime | None
    archived_by_admin_user_id: UUID | None
    archive_reason_code: str | None
    created_at: datetime
    updated_at: datetime
