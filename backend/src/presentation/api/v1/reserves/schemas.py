from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.domain.enums import ReserveReasonType, ReserveScope, ReserveStatus


class CreateReserveRequest(BaseModel):
    partner_account_id: UUID
    amount: Decimal
    currency_code: str = Field(..., min_length=1, max_length=12)
    reserve_scope: ReserveScope
    reserve_reason_type: ReserveReasonType
    source_earning_event_id: UUID | None = None
    reason_code: str | None = Field(None, min_length=1, max_length=80)
    reserve_payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("currency_code")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()


class ReleaseReserveRequest(BaseModel):
    release_reason_code: str | None = Field(None, min_length=1, max_length=80)


class ReserveResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    id: UUID
    partner_account_id: UUID
    source_earning_event_id: UUID | None = None
    reserve_scope: ReserveScope
    reserve_reason_type: ReserveReasonType
    reserve_status: ReserveStatus
    amount: float
    currency_code: str
    reason_code: str | None = None
    reserve_payload: dict[str, Any] = Field(default_factory=dict)
    released_at: datetime | None = None
    released_by_admin_user_id: UUID | None = None
    created_by_admin_user_id: UUID | None = None
    created_at: datetime
    updated_at: datetime
