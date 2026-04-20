"""Canonical device credential bound to service access, not entitlement state."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class DeviceCredential:
    id: UUID
    credential_key: str
    service_identity_id: UUID
    auth_realm_id: UUID
    origin_storefront_id: UUID | None
    provisioning_profile_id: UUID | None
    credential_type: str
    credential_status: str
    subject_key: str
    provider_name: str
    provider_credential_ref: str | None
    credential_context: dict
    issued_at: datetime
    last_used_at: datetime | None
    revoked_at: datetime | None
    revoked_by_admin_user_id: UUID | None
    revoke_reason_code: str | None
    created_at: datetime
    updated_at: datetime
