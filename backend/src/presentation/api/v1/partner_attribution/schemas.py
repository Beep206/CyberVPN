from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class PartnerAttributionCaptureRequest(BaseModel):
    public_token: str = Field(min_length=8, max_length=128)
    source_path: str | None = Field(default=None, max_length=500)
    destination_path: str | None = Field(default=None, max_length=500)
    locale: str | None = Field(default=None, max_length=16)
    sale_channel: str | None = Field(default=None, max_length=40)
    sub_ids: dict[str, str] | None = None
    click_id: str | None = Field(default=None, max_length=160)
    browser_key: str = Field(min_length=1, max_length=160)
    campaign_params: dict[str, Any] | None = None


class PartnerAttributionCaptureResponse(BaseModel):
    attribution_id: UUID
    captured_at: datetime
    expires_at: datetime
    masked_code: str
    transfer_token: str
    redirect_url: str


class PartnerAttributionTransferConsumeRequest(BaseModel):
    transfer_token: str = Field(min_length=16, max_length=256)


class PartnerAttributionTransferConsumeResponse(BaseModel):
    attribution_id: UUID
    captured_at: datetime
    expires_at: datetime
    masked_code: str


class PartnerAttributionClaimRequest(BaseModel):
    pass


class PartnerAttributionClaimResponse(BaseModel):
    status: str
    partner_account_id: UUID | None = None
    partner_code_id: UUID | None = None
    binding_id: UUID | None = None
    claimed_at: datetime | None = None
