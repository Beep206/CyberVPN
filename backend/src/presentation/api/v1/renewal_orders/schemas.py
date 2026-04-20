from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ResolveRenewalOrderRequest(BaseModel):
    order_id: UUID
    prior_order_id: UUID
    renewal_mode: str = Field(..., pattern="^(manual|auto)$")


class RenewalOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    id: UUID
    order_id: UUID
    initial_order_id: UUID
    prior_order_id: UUID
    user_id: UUID
    auth_realm_id: UUID
    storefront_id: UUID
    originating_attribution_result_id: UUID | None = None
    winning_binding_id: UUID | None = None
    renewal_sequence_number: int
    renewal_mode: str
    provenance_owner_type: str
    provenance_owner_source: str | None = None
    provenance_partner_account_id: UUID | None = None
    provenance_partner_code_id: UUID | None = None
    effective_owner_type: str
    effective_owner_source: str | None = None
    effective_partner_account_id: UUID | None = None
    effective_partner_code_id: UUID | None = None
    payout_eligible: bool
    payout_block_reason_codes: list[str] = Field(default_factory=list)
    lineage_snapshot: dict = Field(default_factory=dict)
    explainability_snapshot: dict = Field(default_factory=dict)
    policy_snapshot: dict = Field(default_factory=dict)
    resolved_at: datetime
    created_at: datetime
    updated_at: datetime
