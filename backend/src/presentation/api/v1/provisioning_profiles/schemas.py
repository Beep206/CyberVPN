from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.domain.enums import ProvisioningProfileStatus


class CreateProvisioningProfileRequest(BaseModel):
    service_identity_id: UUID
    profile_key: str = Field(..., min_length=1, max_length=120)
    target_channel: str = Field(..., min_length=1, max_length=40)
    delivery_method: str = Field(..., min_length=1, max_length=40)
    profile_status: ProvisioningProfileStatus = ProvisioningProfileStatus.ACTIVE
    provider_profile_ref: str | None = Field(None, min_length=1, max_length=160)
    provisioning_payload: dict[str, Any] = Field(default_factory=dict)


class ProvisioningProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    id: UUID
    service_identity_id: UUID
    profile_key: str
    target_channel: str
    delivery_method: str
    profile_status: ProvisioningProfileStatus
    provider_name: str
    provider_profile_ref: str | None = None
    provisioning_payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
