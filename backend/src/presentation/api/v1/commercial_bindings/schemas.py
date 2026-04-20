from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.domain.enums import CommercialOwnerType, CustomerCommercialBindingStatus, CustomerCommercialBindingType


class CreateCustomerCommercialBindingRequest(BaseModel):
    user_id: UUID
    binding_type: CustomerCommercialBindingType
    owner_type: CommercialOwnerType
    storefront_id: UUID | None = None
    partner_code: str | None = Field(None, max_length=30)
    partner_code_id: UUID | None = None
    partner_account_id: UUID | None = None
    reason_code: str | None = Field(None, max_length=80)
    evidence_payload: dict[str, Any] = Field(default_factory=dict)
    effective_from: datetime | None = None


class CustomerCommercialBindingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    id: UUID
    user_id: UUID
    auth_realm_id: UUID
    storefront_id: UUID | None = None
    binding_type: CustomerCommercialBindingType
    binding_status: CustomerCommercialBindingStatus
    owner_type: CommercialOwnerType
    partner_account_id: UUID | None = None
    partner_code_id: UUID | None = None
    reason_code: str | None = None
    evidence_payload: dict[str, Any] = Field(default_factory=dict)
    created_by_admin_user_id: UUID | None = None
    effective_from: datetime
    effective_to: datetime | None = None
    created_at: datetime
    updated_at: datetime
