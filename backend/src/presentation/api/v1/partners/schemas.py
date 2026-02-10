"""Pydantic v2 schemas for the partners API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CreatePartnerCodeRequest(BaseModel):
    code: str = ""
    markup_pct: float = 0


class UpdateMarkupRequest(BaseModel):
    markup_pct: float


class BindPartnerRequest(BaseModel):
    partner_code: str


class PartnerCodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    markup_pct: float
    is_active: bool
    created_at: datetime


class PartnerDashboardResponse(BaseModel):
    total_clients: int
    total_earned: float
    current_tier: dict | None
    codes: list[dict]


class PartnerEarningResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    client_user_id: UUID
    base_price: float
    markup_amount: float
    commission_amount: float
    total_earning: float
    created_at: datetime


class PromotePartnerRequest(BaseModel):
    user_id: UUID
