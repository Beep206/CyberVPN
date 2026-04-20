from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.payment_disputes import (
    GetPaymentDisputeUseCase,
    ListPaymentDisputesUseCase,
    UpsertPaymentDisputeUseCase,
)
from src.domain.enums import AdminRole
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_role

from .schemas import PaymentDisputeResponse, UpsertPaymentDisputeRequest

router = APIRouter(prefix="/payment-disputes", tags=["payment-disputes"])


def _serialize_payment_dispute(model) -> PaymentDisputeResponse:
    return PaymentDisputeResponse(
        id=model.id,
        order_id=model.order_id,
        payment_attempt_id=model.payment_attempt_id,
        payment_id=model.payment_id,
        provider=model.provider,
        external_reference=model.external_reference,
        subtype=model.subtype,
        outcome_class=model.outcome_class,
        lifecycle_status=model.lifecycle_status,
        disputed_amount=float(model.disputed_amount),
        fee_amount=float(model.fee_amount),
        fee_status=model.fee_status,
        currency_code=model.currency_code,
        reason_code=model.reason_code,
        evidence_snapshot=model.evidence_snapshot or {},
        provider_snapshot=model.provider_snapshot or {},
        opened_at=model.opened_at,
        closed_at=model.closed_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


@router.post("/", response_model=PaymentDisputeResponse, status_code=status.HTTP_201_CREATED)
async def upsert_payment_dispute(
    payload: UpsertPaymentDisputeRequest,
    http_response: Response,
    db: AsyncSession = Depends(get_db),
    _current_admin=Depends(require_role(AdminRole.ADMIN)),
) -> PaymentDisputeResponse:
    use_case = UpsertPaymentDisputeUseCase(db)
    try:
        result = await use_case.execute(
            order_id=payload.order_id,
            payment_attempt_id=payload.payment_attempt_id,
            payment_id=payload.payment_id,
            provider=payload.provider,
            external_reference=payload.external_reference,
            subtype=payload.subtype,
            outcome_class=payload.outcome_class,
            lifecycle_status=payload.lifecycle_status,
            disputed_amount=Decimal(str(payload.disputed_amount)),
            fee_amount=Decimal(str(payload.fee_amount)),
            fee_status=payload.fee_status,
            currency_code=payload.currency_code,
            reason_code=payload.reason_code,
            evidence_snapshot=payload.evidence_snapshot,
            provider_snapshot=payload.provider_snapshot,
            opened_at=payload.opened_at,
            closed_at=payload.closed_at,
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = status.HTTP_409_CONFLICT if "different order" in detail else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=detail) from exc
    if not result.created:
        http_response.status_code = status.HTTP_200_OK
    return _serialize_payment_dispute(result.payment_dispute)


@router.get("/", response_model=list[PaymentDisputeResponse])
async def list_payment_disputes(
    order_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    _current_admin=Depends(require_role(AdminRole.ADMIN)),
) -> list[PaymentDisputeResponse]:
    disputes = await ListPaymentDisputesUseCase(db).execute(order_id=order_id)
    return [_serialize_payment_dispute(dispute) for dispute in disputes]


@router.get("/{payment_dispute_id}", response_model=PaymentDisputeResponse)
async def get_payment_dispute(
    payment_dispute_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_admin=Depends(require_role(AdminRole.ADMIN)),
) -> PaymentDisputeResponse:
    dispute = await GetPaymentDisputeUseCase(db).execute(payment_dispute_id=payment_dispute_id)
    if dispute is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment dispute not found")
    return _serialize_payment_dispute(dispute)
