from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.orders import (
    CreateOrderFromCheckoutSessionUseCase,
    GetOrderUseCase,
    ListOrdersUseCase,
)
from src.presentation.dependencies.auth import get_current_mobile_user_id
from src.presentation.dependencies.auth_realms import RealmResolution, get_request_customer_realm
from src.presentation.dependencies.database import get_db

from .explainability.routes import router as explainability_router
from .schemas import CreateOrderFromCheckoutRequest, OrderItemResponse, OrderResponse

router = APIRouter(prefix="/orders", tags=["orders"])
router.include_router(explainability_router)


def _serialize_order_item(item) -> OrderItemResponse:
    return OrderItemResponse(
        id=item.id,
        order_id=item.order_id,
        item_type=item.item_type,
        subject_id=item.subject_id,
        subject_code=item.subject_code,
        display_name=item.display_name,
        quantity=item.quantity,
        unit_price=float(item.unit_price),
        total_price=float(item.total_price),
        currency_code=item.currency_code,
        item_snapshot=item.item_snapshot or {},
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _serialize_order(order) -> OrderResponse:
    return OrderResponse(
        id=order.id,
        quote_session_id=order.quote_session_id,
        checkout_session_id=order.checkout_session_id,
        user_id=order.user_id,
        auth_realm_id=order.auth_realm_id,
        storefront_id=order.storefront_id,
        merchant_profile_id=order.merchant_profile_id,
        invoice_profile_id=order.invoice_profile_id,
        billing_descriptor_id=order.billing_descriptor_id,
        pricebook_id=order.pricebook_id,
        pricebook_entry_id=order.pricebook_entry_id,
        offer_id=order.offer_id,
        legal_document_set_id=order.legal_document_set_id,
        program_eligibility_policy_id=order.program_eligibility_policy_id,
        subscription_plan_id=order.subscription_plan_id,
        promo_code_id=order.promo_code_id,
        partner_code_id=order.partner_code_id,
        sale_channel=order.sale_channel,
        currency_code=order.currency_code,
        order_status=order.order_status,
        settlement_status=order.settlement_status,
        base_price=float(order.base_price),
        addon_amount=float(order.addon_amount),
        displayed_price=float(order.displayed_price),
        discount_amount=float(order.discount_amount),
        wallet_amount=float(order.wallet_amount),
        gateway_amount=float(order.gateway_amount),
        partner_markup=float(order.partner_markup),
        commission_base_amount=float(order.commission_base_amount),
        merchant_snapshot=order.merchant_snapshot or {},
        pricing_snapshot=order.pricing_snapshot or {},
        policy_snapshot=order.policy_snapshot or {},
        entitlements_snapshot=order.entitlements_snapshot or {},
        items=[_serialize_order_item(item) for item in order.items],
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


@router.post("/commit", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order_from_checkout(
    payload: CreateOrderFromCheckoutRequest,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_mobile_user_id),
    current_realm: RealmResolution = Depends(get_request_customer_realm),
) -> OrderResponse:
    use_case = CreateOrderFromCheckoutSessionUseCase(db)
    try:
        order = await use_case.execute(
            checkout_session_id=payload.checkout_session_id,
            user_id=user_id,
            current_realm=current_realm,
        )
    except ValueError as exc:
        detail = str(exc)
        is_conflict = "already exists" in detail or "expired" in detail
        status_code = status.HTTP_409_CONFLICT if is_conflict else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=detail) from exc
    return _serialize_order(order)


@router.get("/", response_model=list[OrderResponse])
async def list_orders(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_mobile_user_id),
) -> list[OrderResponse]:
    use_case = ListOrdersUseCase(db)
    orders = await use_case.execute(user_id=user_id, limit=limit, offset=offset)
    return [_serialize_order(order) for order in orders]


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_mobile_user_id),
) -> OrderResponse:
    use_case = GetOrderUseCase(db)
    order = await use_case.execute(order_id=order_id)
    if order is None or order.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return _serialize_order(order)
