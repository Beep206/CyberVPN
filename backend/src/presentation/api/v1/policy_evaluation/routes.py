from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.attribution.qualifying_events import EvaluateOrderPolicyUseCase
from src.domain.enums import AdminRole
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_role

from .schemas import (
    OrderPolicyEvaluationResponse,
    OrderPolicyPayoutRulesResponse,
    OrderPolicyQualifyingEventResponse,
    OrderPolicyStackingResponse,
)

router = APIRouter(prefix="/policy-evaluation", tags=["policy-evaluation"])


@router.get("/orders/{order_id}", response_model=OrderPolicyEvaluationResponse)
async def evaluate_order_policy(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_admin=Depends(require_role(AdminRole.SUPPORT)),
) -> OrderPolicyEvaluationResponse:
    use_case = EvaluateOrderPolicyUseCase(db)
    try:
        result = await use_case.execute(order_id=order_id)
    except ValueError as exc:
        detail = str(exc)
        status_code = status.HTTP_404_NOT_FOUND if "not found" in detail.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=detail) from exc

    return OrderPolicyEvaluationResponse(
        order_id=result.order.id,
        evaluated_at=result.evaluated_at,
        stacking=OrderPolicyStackingResponse(
            commercial_discount_instruments=result.stacking.commercial_discount_instruments,
            settlement_instruments=result.stacking.settlement_instruments,
            stacking_valid=result.stacking.stacking_valid,
            reason_codes=result.stacking.reason_codes,
        ),
        qualifying_event=OrderPolicyQualifyingEventResponse(
            qualifying_first_payment=result.qualifying_event.qualifying_first_payment,
            first_paid_order=result.qualifying_event.first_paid_order,
            order_is_paid=result.qualifying_event.order_is_paid,
            fully_refunded=result.qualifying_event.fully_refunded,
            risk_blocked=result.qualifying_event.risk_blocked,
            positive_paid_economic_amount=result.qualifying_event.positive_paid_economic_amount,
            paid_economic_amount=result.qualifying_event.paid_economic_amount,
            excluded_credit_amount=result.qualifying_event.excluded_credit_amount,
            reason_codes=result.qualifying_event.reason_codes,
        ),
        payout_rules=OrderPolicyPayoutRulesResponse(
            commercial_owner_type=result.payout_rules.commercial_owner_type,
            commercial_owner_present=result.payout_rules.commercial_owner_present,
            program_allows_commercial_owner=result.payout_rules.program_allows_commercial_owner,
            program_allows_referral_credit=result.payout_rules.program_allows_referral_credit,
            referral_cash_payout_allowed=result.payout_rules.referral_cash_payout_allowed,
            partner_cash_payout_allowed=result.payout_rules.partner_cash_payout_allowed,
            no_double_payout=result.payout_rules.no_double_payout,
            referral_reason_codes=result.payout_rules.referral_reason_codes,
            partner_reason_codes=result.payout_rules.partner_reason_codes,
        ),
    )
