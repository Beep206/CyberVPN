"""Payment and cryptocurrency invoice routes."""

import logging
from dataclasses import asdict
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.auth.permissions import Permission
from src.application.use_cases.payments.checkout import CheckoutUseCase
from src.application.use_cases.payments.crypto_payment import CreateCryptoInvoiceUseCase
from src.application.use_cases.payments.payment_history import PaymentHistoryUseCase
from src.infrastructure.database.repositories.payment_repo import PaymentRepository
from src.infrastructure.database.repositories.subscription_plan_repo import SubscriptionPlanRepository
from src.infrastructure.payments.cryptobot.client import CryptoBotClient
from src.presentation.api.v1.payments.schemas import (
    CheckoutRequest,
    CheckoutResponse,
    CreateInvoiceRequest,
    InvoiceResponse,
    PaymentHistoryResponse,
)
from src.presentation.dependencies.auth import get_current_mobile_user_id
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_permission
from src.presentation.dependencies.services import get_crypto_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post(
    "/crypto/invoice",
    response_model=InvoiceResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Invalid payment parameters"},
        422: {"description": "Validation error"},
    },
)
async def create_crypto_invoice(
    request: CreateInvoiceRequest,
    db: AsyncSession = Depends(get_db),
    crypto_client: CryptoBotClient = Depends(get_crypto_client),
    _: None = Depends(require_permission(Permission.PAYMENT_CREATE)),
) -> InvoiceResponse:
    """Create a new cryptocurrency invoice."""
    plan_repo = SubscriptionPlanRepository(db)
    use_case = CreateCryptoInvoiceUseCase(
        crypto_client=crypto_client,
        plan_repo=plan_repo,
    )

    try:
        invoice_data = await use_case.execute(
            user_uuid=request.user_uuid,
            plan_id=request.plan_id,
            currency=request.currency,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return InvoiceResponse(**asdict(invoice_data))


@router.get(
    "/crypto/invoice/{invoice_id}",
    response_model=InvoiceResponse,
    responses={404: {"description": "Invoice not found"}},
)
async def get_crypto_invoice(
    invoice_id: str,
    db: AsyncSession = Depends(get_db),
    crypto_client: CryptoBotClient = Depends(get_crypto_client),
    _: None = Depends(require_permission(Permission.PAYMENT_READ)),
) -> InvoiceResponse:
    """Get a crypto invoice by ID."""
    plan_repo = SubscriptionPlanRepository(db)
    use_case = CreateCryptoInvoiceUseCase(
        crypto_client=crypto_client,
        plan_repo=plan_repo,
    )

    invoice_data = await use_case.get_invoice(invoice_id=invoice_id)

    if not invoice_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice {invoice_id} not found",
        )

    return InvoiceResponse(**asdict(invoice_data))


@router.get("/history", response_model=PaymentHistoryResponse)
async def get_payment_history(
    db: AsyncSession = Depends(get_db),
    user_uuid: UUID | None = Query(None, description="Filter by user UUID"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=100, description="Pagination limit"),
    _: None = Depends(require_permission(Permission.PAYMENT_READ)),
) -> PaymentHistoryResponse:
    """Get payment history with optional user filter."""
    payment_repo = PaymentRepository(db)
    use_case = PaymentHistoryUseCase(repo=payment_repo)

    payments = await use_case.execute(
        user_uuid=user_uuid,
        offset=offset,
        limit=limit,
    )

    return PaymentHistoryResponse(payments=payments)


@router.post("/checkout", response_model=CheckoutResponse)
async def checkout(
    body: CheckoutRequest,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_mobile_user_id),
) -> CheckoutResponse:
    """Unified checkout: plan + promo + wallet + partner resolution."""
    use_case = CheckoutUseCase(db)
    try:
        result = await use_case.execute(
            user_id=user_id,
            plan_id=body.plan_id,
            promo_code=body.promo_code,
            use_wallet=Decimal(str(body.use_wallet)),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None

    response = CheckoutResponse(
        base_price=float(result.base_price),
        displayed_price=float(result.displayed_price),
        discount_amount=float(result.discount_amount),
        wallet_amount=float(result.wallet_amount),
        gateway_amount=float(result.gateway_amount),
        partner_markup=float(result.partner_markup),
        is_zero_gateway=result.is_zero_gateway,
        plan_id=result.plan_id,
        promo_code_id=result.promo_code_id,
        partner_code_id=result.partner_code_id,
    )

    # If zero-gateway, complete payment immediately without creating a CryptoBot invoice
    if result.is_zero_gateway:
        from src.application.use_cases.payments.complete_zero_gateway import CompleteZeroGatewayUseCase

        zero_gw = CompleteZeroGatewayUseCase(db)
        try:
            payment = await zero_gw.execute(
                user_id=user_id,
                plan_id=body.plan_id,
                base_price=result.base_price,
                displayed_price=result.displayed_price,
                discount_amount=result.discount_amount,
                wallet_amount=result.wallet_amount,
                promo_code_id=result.promo_code_id,
                partner_code_id=result.partner_code_id,
                currency=body.currency,
            )
            response.payment_id = payment.id
            response.status = "completed"
        except Exception:
            logger.exception("Zero-gateway completion failed")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Payment processing failed",
            ) from None

    return response


# ── Backward Compatibility Aliases ───────────────────────────────────────────


@router.post(
    "/create",
    response_model=InvoiceResponse,
    status_code=status.HTTP_201_CREATED,
    deprecated=True,
)
async def create_payment_alias(
    request: CreateInvoiceRequest,
    db: AsyncSession = Depends(get_db),
    crypto_client: CryptoBotClient = Depends(get_crypto_client),
    _: None = Depends(require_permission(Permission.PAYMENT_CREATE)),
) -> InvoiceResponse:
    """Create a payment (POST /create alias for mobile compatibility).

    **DEPRECATED**: Use POST /payments/crypto/invoice instead.

    This is an alias route for backward compatibility with mobile clients.
    """
    return await create_crypto_invoice(request, db, crypto_client, _)


@router.get(
    "/{invoice_id}/status",
    response_model=InvoiceResponse,
    deprecated=True,
)
async def get_payment_status_alias(
    invoice_id: str,
    db: AsyncSession = Depends(get_db),
    crypto_client: CryptoBotClient = Depends(get_crypto_client),
    _: None = Depends(require_permission(Permission.PAYMENT_READ)),
) -> InvoiceResponse:
    """Get payment status (GET /:id/status alias for mobile compatibility).

    **DEPRECATED**: Use GET /payments/crypto/invoice/:id instead.

    This is an alias route for backward compatibility with mobile clients.
    """
    return await get_crypto_invoice(invoice_id, db, crypto_client, _)
