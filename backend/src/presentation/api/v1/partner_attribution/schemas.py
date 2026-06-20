from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class PartnerAttributionCaptureRequest(BaseModel):
    public_token: str = Field(min_length=8, max_length=128)
    source_host: str | None = Field(default=None, max_length=255)
    source_path: str | None = Field(default=None, max_length=500)
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
    expires_at: datetime
    masked_code: str


class PartnerAttributionClaimRequest(BaseModel):
    fallback_token: str | None = Field(default=None, min_length=16, max_length=256)


class PartnerAttributionClaimResponse(BaseModel):
    status: str
    partner_account_id: UUID | None = None
    partner_code_id: UUID | None = None
    binding_id: UUID | None = None
    claimed_at: datetime | None = None
