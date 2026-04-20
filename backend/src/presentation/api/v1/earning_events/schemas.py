from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.domain.enums import EarningEventStatus


class EarningEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    id: UUID
    partner_account_id: UUID | None = None
    partner_user_id: UUID
    client_user_id: UUID
    order_id: UUID
    payment_id: UUID | None = None
    partner_code_id: UUID | None = None
    legacy_partner_earning_id: UUID | None = None
    order_attribution_result_id: UUID | None = None
    owner_type: str
    event_status: EarningEventStatus
    commission_base_amount: float
    markup_amount: float
    commission_pct: float
    commission_amount: float
    total_amount: float
    currency_code: str
    available_at: datetime | None = None
    source_snapshot: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
