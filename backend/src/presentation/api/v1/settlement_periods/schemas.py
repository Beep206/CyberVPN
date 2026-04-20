from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.domain.enums import SettlementPeriodStatus


class CreateSettlementPeriodRequest(BaseModel):
    partner_account_id: UUID
    period_key: str = Field(..., min_length=1, max_length=80)
    currency_code: str = Field(..., min_length=1, max_length=12)
    window_start: datetime
    window_end: datetime

    @field_validator("currency_code")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()


class SettlementPeriodResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    id: UUID
    partner_account_id: UUID
    period_key: str
    period_status: SettlementPeriodStatus
    currency_code: str
    window_start: datetime
    window_end: datetime
    closed_at: datetime | None = None
    closed_by_admin_user_id: UUID | None = None
    reopened_at: datetime | None = None
    reopened_by_admin_user_id: UUID | None = None
    created_at: datetime
    updated_at: datetime
