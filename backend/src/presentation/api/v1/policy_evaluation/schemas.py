from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.domain.enums import CommercialOwnerType


class OrderPolicyStackingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    commercial_discount_instruments: list[str] = Field(default_factory=list)
    settlement_instruments: list[str] = Field(default_factory=list)
    stacking_valid: bool
    reason_codes: list[str] = Field(default_factory=list)


class OrderPolicyQualifyingEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    qualifying_first_payment: bool
    first_paid_order: bool
    order_is_paid: bool
    fully_refunded: bool
    risk_blocked: bool
    positive_paid_economic_amount: bool
    paid_economic_amount: float
    excluded_credit_amount: float
    reason_codes: list[str] = Field(default_factory=list)


class OrderPolicyPayoutRulesResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    commercial_owner_type: CommercialOwnerType
    commercial_owner_present: bool
    program_allows_commercial_owner: bool
    program_allows_referral_credit: bool
    referral_cash_payout_allowed: bool
    partner_cash_payout_allowed: bool
    no_double_payout: bool
    referral_reason_codes: list[str] = Field(default_factory=list)
    partner_reason_codes: list[str] = Field(default_factory=list)


class OrderPolicyEvaluationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    order_id: UUID
    evaluated_at: datetime
    stacking: OrderPolicyStackingResponse
    qualifying_event: OrderPolicyQualifyingEventResponse
    payout_rules: OrderPolicyPayoutRulesResponse
