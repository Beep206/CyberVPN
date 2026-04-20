"""Canonical provisioning profile for a service identity and channel."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class ProvisioningProfile:
    id: UUID
    service_identity_id: UUID
    profile_key: str
    target_channel: str
    delivery_method: str
    profile_status: str
    provider_name: str
    provider_profile_ref: str | None
    provisioning_payload: dict
    created_at: datetime
    updated_at: datetime
