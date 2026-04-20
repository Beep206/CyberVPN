from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.orders.explainability import GetOrderExplainabilityUseCase
from src.domain.enums import AdminRole
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_role

from .schemas import (
    CommissionabilityEvaluationResponse,
    OrderExplainabilityOrderSummary,
    OrderExplainabilityResponse,
)

router = APIRouter(tags=["orders-explainability"])


def _serialize_order_summary(order) -> OrderExplainabilityOrderSummary:
    return OrderExplainabilityOrderSummary(
        id=order.id,
        settlement_status=order.settlement_status,
        sale_channel=order.sale_channel,
        currency_code=order.currency_code,
        displayed_price=float(order.displayed_price),
        commission_base_amount=float(order.commission_base_amount),
        partner_code_id=order.partner_code_id,
        program_eligibility_policy_id=order.program_eligibility_policy_id,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


def _serialize_evaluation(model) -> CommissionabilityEvaluationResponse:
    return CommissionabilityEvaluationResponse(
        id=model.id,
        order_id=model.order_id,
        commissionability_status=model.commissionability_status,
        reason_codes=list(model.reason_codes or []),
        partner_context_present=bool(model.partner_context_present),
        program_allows_commissionability=bool(model.program_allows_commissionability),
        positive_commission_base=bool(model.positive_commission_base),
        paid_status=bool(model.paid_status),
        fully_refunded=bool(model.fully_refunded),
        open_payment_dispute_present=bool(model.open_payment_dispute_present),
        risk_allowed=bool(model.risk_allowed),
        evaluation_snapshot=model.evaluation_snapshot or {},
        explainability_snapshot=model.explainability_snapshot or {},
        evaluated_at=model.evaluated_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


@router.get("/{order_id}/explainability", response_model=OrderExplainabilityResponse)
async def get_order_explainability(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_admin=Depends(require_role(AdminRole.SUPPORT)),
) -> OrderExplainabilityResponse:
    use_case = GetOrderExplainabilityUseCase(db)
    try:
        result = await use_case.execute(order_id=order_id)
    except ValueError as exc:
        detail = str(exc)
        status_code = status.HTTP_404_NOT_FOUND if "not found" in detail.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=detail) from exc
    return OrderExplainabilityResponse(
        order=_serialize_order_summary(result.order),
        commissionability_evaluation=_serialize_evaluation(result.commissionability_evaluation),
        explainability=result.explainability_payload,
    )
