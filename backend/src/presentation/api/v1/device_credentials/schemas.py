from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.domain.enums import DeviceCredentialType


class CreateDeviceCredentialRequest(BaseModel):
    service_identity_id: UUID
    provisioning_profile_id: UUID | None = None
    credential_type: DeviceCredentialType
    subject_key: str = Field(..., min_length=1, max_length=160)
    provider_credential_ref: str | None = Field(None, max_length=160)
    credential_context: dict[str, Any] = Field(default_factory=dict)


class DeviceCredentialTransitionRequest(BaseModel):
    reason_code: str | None = Field(None, max_length=80)


class DeviceCredentialResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    credential_key: str
    service_identity_id: UUID
    auth_realm_id: UUID
    origin_storefront_id: UUID | None = None
    provisioning_profile_id: UUID | None = None
    credential_type: str
    credential_status: str
    subject_key: str
    provider_name: str
    provider_credential_ref: str | None = None
    credential_context: dict[str, Any]
    issued_at: datetime
    last_used_at: datetime | None = None
    revoked_at: datetime | None = None
    revoked_by_admin_user_id: UUID | None = None
    revoke_reason_code: str | None = None
    created_at: datetime
    updated_at: datetime
