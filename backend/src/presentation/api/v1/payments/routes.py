"""Payment and cryptocurrency invoice routes."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.auth.permissions import Permission
from src.application.use_cases.payments.crypto_payment import CreateCryptoInvoiceUseCase
from src.application.use_cases.payments.payment_history import PaymentHistoryUseCase
from src.infrastructure.database.repositories.subscription_plan_repo import SubscriptionPlanRepository
from src.infrastructure.database.repositories.payment_repo import PaymentRepository
from src.infrastructure.payments.cryptobot.client import CryptoBotClient
from src.presentation.api.v1.payments.schemas import (
    CreateInvoiceRequest,
    InvoiceResponse,
    PaymentHistoryResponse,
)
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_permission

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/crypto/invoice", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_crypto_invoice(
    request: CreateInvoiceRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(Permission.PAYMENT_CREATE)),
) -> InvoiceResponse:
    """Create a new cryptocurrency invoice."""
    try:
        crypto_client = CryptoBotClient()
        plan_repo = SubscriptionPlanRepository(db)

        use_case = CreateCryptoInvoiceUseCase(
            crypto_client=crypto_client,
            plan_repo=plan_repo,
        )

        invoice_data = await use_case.create_invoice(
            user_uuid=request.user_uuid,
            plan_id=request.plan_id,
            currency=request.currency,
        )

        return InvoiceResponse(**invoice_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create crypto invoice: {str(e)}",
        )


@router.get("/crypto/invoice/{invoice_id}", response_model=InvoiceResponse)
async def get_crypto_invoice(
    invoice_id: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(Permission.PAYMENT_READ)),
) -> InvoiceResponse:
    """Get a crypto invoice by ID."""
    try:
        crypto_client = CryptoBotClient()
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

        return InvoiceResponse(**invoice_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get crypto invoice: {str(e)}",
        )


@router.get("/history", response_model=PaymentHistoryResponse)
async def get_payment_history(
    db: AsyncSession = Depends(get_db),
    user_uuid: Optional[UUID] = Query(None, description="Filter by user UUID"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=100, description="Pagination limit"),
    _: None = Depends(require_permission(Permission.PAYMENT_READ)),
) -> PaymentHistoryResponse:
    """Get payment history with optional user filter."""
    try:
        payment_repo = PaymentRepository(db)
        use_case = PaymentHistoryUseCase(payment_repo=payment_repo)

        payments = await use_case.execute(
            user_uuid=user_uuid,
            offset=offset,
            limit=limit,
        )

        return PaymentHistoryResponse(payments=payments)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get payment history: {str(e)}",
        )
