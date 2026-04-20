from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.domain.enums import GrowthRewardAllocationStatus, GrowthRewardType


class CreateGrowthRewardAllocationRequest(BaseModel):
    reward_type: GrowthRewardType
    beneficiary_user_id: UUID
    quantity: Decimal | None = None
    unit: str | None = Field(None, min_length=1, max_length=20)
    currency_code: str | None = Field(None, min_length=1, max_length=12)
    storefront_id: UUID | None = None
    order_id: UUID | None = None
    invite_code_id: UUID | None = None
    referral_commission_id: UUID | None = None
    source_key: str | None = Field(None, min_length=1, max_length=160)
    reward_payload: dict[str, Any] = Field(default_factory=dict)
    allocated_at: datetime | None = None

    @field_validator("currency_code")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        return value.upper() if value else None

    @model_validator(mode="after")
    def validate_source_reference(self) -> "CreateGrowthRewardAllocationRequest":
        if not any((self.order_id, self.invite_code_id, self.referral_commission_id, self.source_key)):
            raise ValueError("At least one source reference is required")
        return self


class GrowthRewardAllocationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    id: UUID
    reward_type: GrowthRewardType
    allocation_status: GrowthRewardAllocationStatus
    beneficiary_user_id: UUID
    auth_realm_id: UUID
    storefront_id: UUID | None = None
    order_id: UUID | None = None
    invite_code_id: UUID | None = None
    referral_commission_id: UUID | None = None
    source_key: str | None = None
    quantity: float
    unit: str
    currency_code: str | None = None
    reward_payload: dict[str, Any] = Field(default_factory=dict)
    created_by_admin_user_id: UUID | None = None
    allocated_at: datetime
    reversed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
