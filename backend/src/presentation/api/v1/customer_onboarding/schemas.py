from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CustomerOnboardingCurrentResponse(BaseModel):
    required: bool
    status: Literal["disabled", "unavailable", "pending", "completed", "skipped"]
    flow_key: str
    version: int
    allowed_code_types: list[Literal["promo", "invite", "gift"]]
    flow_token: str | None = None
    message_key: str
    server_state_available: bool
    referral_already_attributed: bool = False


class CustomerOnboardingApplyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(..., min_length=1, max_length=64)
    flow_token: str | None = Field(None, min_length=16, max_length=240)
    idempotency_key: str | None = Field(None, min_length=1, max_length=120)


class CustomerOnboardingApplyResponse(BaseModel):
    status: Literal["pending", "completed", "skipped"]
    message_key: str
    masked_code: str | None = None
    next_destination: str = "/dashboard"


class CustomerOnboardingSkipRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    flow_token: str | None = Field(None, min_length=16, max_length=240)
    idempotency_key: str | None = Field(None, min_length=1, max_length=120)


class CustomerOnboardingSkipResponse(BaseModel):
    status: Literal["skipped", "completed"]
    message_key: str
    next_destination: str = "/dashboard"
