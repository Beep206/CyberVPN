from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.orders import GetOrderUseCase
from src.application.use_cases.refunds import (
    CreateRefundUseCase,
    GetRefundUseCase,
    ListRefundsUseCase,
    UpdateRefundUseCase,
)
from src.domain.enums import AdminRole
from src.presentation.dependencies.auth import get_current_mobile_user_id
from src.presentation.dependencies.auth_realms import RealmResolution, get_request_customer_realm
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_role

from .schemas import CreateRefundRequest, RefundResponse, UpdateRefundRequest

router = APIRouter(prefix="/refunds", tags=["refunds"])


def _serialize_refund(model) -> RefundResponse:
    return RefundResponse(
        id=model.id,
        order_id=model.order_id,
        payment_attempt_id=model.payment_attempt_id,
        payment_id=model.payment_id,
        refund_status=model.refund_status,
        amount=float(model.amount),
        currency_code=model.currency_code,
        provider=model.provider,
        reason_code=model.reason_code,
        reason_text=model.reason_text,
        external_reference=model.external_reference,
        idempotency_key=model.idempotency_key,
        provider_snapshot=model.provider_snapshot or {},
        request_snapshot=model.request_snapshot or {},
        submitted_at=model.submitted_at,
        completed_at=model.completed_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


@router.post("/", response_model=RefundResponse, status_code=status.HTTP_201_CREATED)
async def create_refund(
    payload: CreateRefundRequest,
    http_response: Response,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_mobile_user_id),
    current_realm: RealmResolution = Depends(get_request_customer_realm),
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=1, max_length=120),
) -> RefundResponse:
    use_case = CreateRefundUseCase(db)
    try:
        result = await use_case.execute(
            order_id=payload.order_id,
            user_id=user_id,
            current_realm=current_realm,
            idempotency_key=idempotency_key,
            amount=Decimal(str(payload.amount)),
            payment_attempt_id=payload.payment_attempt_id,
            reason_code=payload.reason_code,
            reason_text=payload.reason_text,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if not result.created:
        http_response.status_code = status.HTTP_200_OK
    return _serialize_refund(result.refund)


@router.get("/", response_model=list[RefundResponse])
async def list_refunds(
    order_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_mobile_user_id),
    current_realm: RealmResolution = Depends(get_request_customer_realm),
) -> list[RefundResponse]:
    order = await GetOrderUseCase(db).execute(order_id=order_id)
    if order is None or order.user_id != user_id or str(order.auth_realm_id) != current_realm.realm_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    refunds = await ListRefundsUseCase(db).execute(order_id=order_id)
    return [_serialize_refund(refund) for refund in refunds]


@router.get("/{refund_id}", response_model=RefundResponse)
async def get_refund(
    refund_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_mobile_user_id),
    current_realm: RealmResolution = Depends(get_request_customer_realm),
) -> RefundResponse:
    refund = await GetRefundUseCase(db).execute(refund_id=refund_id)
    if refund is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Refund not found")
    order = await GetOrderUseCase(db).execute(order_id=refund.order_id)
    if order is None or order.user_id != user_id or str(order.auth_realm_id) != current_realm.realm_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Refund not found")
    return _serialize_refund(refund)


@router.patch("/{refund_id}", response_model=RefundResponse)
async def update_refund(
    refund_id: UUID,
    payload: UpdateRefundRequest,
    db: AsyncSession = Depends(get_db),
    _current_admin=Depends(require_role(AdminRole.ADMIN)),
) -> RefundResponse:
    use_case = UpdateRefundUseCase(db)
    try:
        updated = await use_case.execute(
            refund_id=refund_id,
            refund_status=payload.refund_status,
            external_reference=payload.external_reference,
            provider_snapshot=payload.provider_snapshot or None,
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = status.HTTP_409_CONFLICT if "terminal state" in detail else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=detail) from exc
    return _serialize_refund(updated)
