"""Payment and cryptocurrency invoice routes."""

from dataclasses import asdict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.auth.permissions import Permission
from src.application.use_cases.payments.crypto_payment import CreateCryptoInvoiceUseCase
from src.application.use_cases.payments.payment_history import PaymentHistoryUseCase
from src.infrastructure.database.repositories.payment_repo import PaymentRepository
from src.infrastructure.database.repositories.subscription_plan_repo import SubscriptionPlanRepository
from src.infrastructure.payments.cryptobot.client import CryptoBotClient
from src.presentation.api.v1.payments.schemas import (
    CreateInvoiceRequest,
    InvoiceResponse,
    PaymentHistoryResponse,
)
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_permission
from src.presentation.dependencies.services import get_crypto_client

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
