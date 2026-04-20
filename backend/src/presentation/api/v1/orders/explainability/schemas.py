from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OrderExplainabilityOrderSummary(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    id: UUID
    settlement_status: str
    sale_channel: str
    currency_code: str
    displayed_price: float
    commission_base_amount: float
    partner_code_id: UUID | None = None
    program_eligibility_policy_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


class CommissionabilityEvaluationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    id: UUID
    order_id: UUID
    commissionability_status: str
    reason_codes: list[str] = Field(default_factory=list)
    partner_context_present: bool
    program_allows_commissionability: bool
    positive_commission_base: bool
    paid_status: bool
    fully_refunded: bool
    open_payment_dispute_present: bool
    risk_allowed: bool
    evaluation_snapshot: dict = Field(default_factory=dict)
    explainability_snapshot: dict = Field(default_factory=dict)
    evaluated_at: datetime
    created_at: datetime
    updated_at: datetime


class OrderExplainabilityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    order: OrderExplainabilityOrderSummary
    commissionability_evaluation: CommissionabilityEvaluationResponse
    explainability: dict = Field(default_factory=dict)
