from uuid import UUID

from pydantic import BaseModel, Field

from src.domain.enums import (
    GrowthCodeActionContext,
    GrowthCodeRejectReason,
    GrowthCodeResolutionStatus,
    GrowthCodeType,
    GrowthCodeWrongContextTarget,
)


class ResolveGrowthCodeRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=64)
    action_context: GrowthCodeActionContext
    storefront_key: str | None = Field(None, min_length=1, max_length=50)
    plan_id: UUID | None = None
    amount: float | None = Field(None, ge=0)
    channel: str = Field("web", min_length=1, max_length=30)
    existing_partner_code_present: bool = False
    existing_promo_present: bool = False


class ResolveGrowthCodeResponse(BaseModel):
    accepted: bool
    code_type: GrowthCodeType | None = None
    action_context: GrowthCodeActionContext
    result: GrowthCodeResolutionStatus
    reject_reason: GrowthCodeRejectReason | None = None
    conflict_code: str | None = None
    wrong_context_target: GrowthCodeWrongContextTarget | None = None
    issuer_type: str | None = None
    owner_type: str | None = None
    resolved_code_id: UUID | None = None
    promo_code_id: UUID | None = None
    partner_code_id: UUID | None = None
    user_message_key: str
