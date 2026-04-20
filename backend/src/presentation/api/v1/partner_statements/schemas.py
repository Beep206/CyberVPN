from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.domain.enums import (
    PartnerStatementStatus,
    StatementAdjustmentDirection,
    StatementAdjustmentType,
)


class GeneratePartnerStatementRequest(BaseModel):
    settlement_period_id: UUID


class CreateStatementAdjustmentRequest(BaseModel):
    adjustment_type: StatementAdjustmentType = StatementAdjustmentType.MANUAL
    adjustment_direction: StatementAdjustmentDirection
    amount: Decimal
    currency_code: str = Field(..., min_length=1, max_length=12)
    reason_code: str | None = Field(None, min_length=1, max_length=80)
    source_reference_type: str | None = Field(None, min_length=1, max_length=40)
    source_reference_id: UUID | None = None
    adjustment_payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("currency_code")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()


class StatementAdjustmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    id: UUID
    partner_statement_id: UUID
    partner_account_id: UUID
    source_reference_type: str | None = None
    source_reference_id: UUID | None = None
    carried_from_adjustment_id: UUID | None = None
    adjustment_type: StatementAdjustmentType
    adjustment_direction: StatementAdjustmentDirection
    amount: float
    currency_code: str
    reason_code: str | None = None
    adjustment_payload: dict[str, Any] = Field(default_factory=dict)
    created_by_admin_user_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


class PartnerStatementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    id: UUID
    partner_account_id: UUID
    settlement_period_id: UUID
    statement_key: str
    statement_version: int
    statement_status: PartnerStatementStatus
    reopened_from_statement_id: UUID | None = None
    superseded_by_statement_id: UUID | None = None
    currency_code: str
    accrual_amount: float
    on_hold_amount: float
    reserve_amount: float
    adjustment_net_amount: float
    available_amount: float
    source_event_count: int
    held_event_count: int
    active_reserve_count: int
    adjustment_count: int
    statement_snapshot: dict[str, Any] = Field(default_factory=dict)
    closed_at: datetime | None = None
    closed_by_admin_user_id: UUID | None = None
    created_at: datetime
    updated_at: datetime
