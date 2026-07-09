import hashlib
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.orders import GetOrderUseCase
from src.application.use_cases.payment_attempts import (
    CreatePaymentAttemptUseCase,
    GetPaymentAttemptUseCase,
    ListPaymentAttemptsUseCase,
)
from src.presentation.api.v1.payments.schemas import InvoiceResponse
from src.presentation.dependencies.auth import get_current_mobile_user_id
from src.presentation.dependencies.auth_realms import RealmResolution, get_request_customer_realm
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.services import get_crypto_client

from .schemas import CreatePaymentAttemptRequest, PaymentAttemptResponse

router = APIRouter(prefix="/payment-attempts", tags=["payment-attempts"])


def _build_invoice(provider_snapshot: dict, fallback_currency: str, fallback_status: str) -> InvoiceResponse | None:
    if not provider_snapshot.get("invoice_id"):
        return None
    return InvoiceResponse(
        invoice_id=provider_snapshot["invoice_id"],
        payment_url=provider_snapshot.get("payment_url", ""),
        amount=float(provider_snapshot.get("amount", 0)),
        currency=provider_snapshot.get("currency", fallback_currency),
        status=provider_snapshot.get("status", fallback_status),
        expires_at=provider_snapshot.get("expires_at"),
    )


def _public_idempotency_fingerprint(idempotency_key: str) -> str:
    return f"sha256:{hashlib.sha256(idempotency_key.encode('utf-8')).hexdigest()[:16]}"


def _public_provider_snapshot(provider_snapshot: dict) -> dict:
    allowed_keys = {"invoice_id", "status", "currency", "amount", "expires_at"}
    return {key: provider_snapshot[key] for key in allowed_keys if key in provider_snapshot}


def _serialize_payment_attempt(model, *, include_sensitive: bool = False) -> PaymentAttemptResponse:
    provider_snapshot = model.provider_snapshot or {}
    public_provider_snapshot = provider_snapshot if include_sensitive else _public_provider_snapshot(provider_snapshot)
    idempotency_key = (
        model.idempotency_key if include_sensitive else _public_idempotency_fingerprint(model.idempotency_key)
    )
    request_snapshot = model.request_snapshot or {} if include_sensitive else {}
    return PaymentAttemptResponse(
        id=model.id,
        order_id=model.order_id,
        payment_id=model.payment_id,
        supersedes_attempt_id=model.supersedes_attempt_id,
        attempt_number=model.attempt_number,
        provider=model.provider,
        sale_channel=model.sale_channel,
        currency_code=model.currency_code,
        status=model.status,
        displayed_amount=float(model.displayed_amount),
        wallet_amount=float(model.wallet_amount),
        gateway_amount=float(model.gateway_amount),
        external_reference=model.external_reference if include_sensitive else None,
        idempotency_key=idempotency_key,
        provider_snapshot=public_provider_snapshot,
        request_snapshot=request_snapshot,
        invoice=_build_invoice(public_provider_snapshot, model.currency_code, model.status),
        terminal_at=model.terminal_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _order_belongs_to_customer_realm(order, *, user_id: UUID, current_realm: RealmResolution) -> bool:
    return order is not None and order.user_id == user_id and str(order.auth_realm_id) == current_realm.realm_id


@router.post("", response_model=PaymentAttemptResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
@router.post("/", response_model=PaymentAttemptResponse, status_code=status.HTTP_201_CREATED)
async def create_payment_attempt(
    payload: CreatePaymentAttemptRequest,
    http_response: Response,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_mobile_user_id),
    current_realm: RealmResolution = Depends(get_request_customer_realm),
    crypto_client=Depends(get_crypto_client),
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=1, max_length=120),
) -> PaymentAttemptResponse:
    use_case = CreatePaymentAttemptUseCase(db, crypto_client)
    try:
        result = await use_case.execute(
            order_id=payload.order_id,
            user_id=user_id,
            current_realm=current_realm,
            idempotency_key=idempotency_key,
        )
    except ValueError as exc:
        detail = str(exc)
        conflict_fragments = ("already settled", "active payment attempt", "succeeded payment attempt")
        is_conflict = any(fragment in detail for fragment in conflict_fragments)
        status_code = status.HTTP_409_CONFLICT if is_conflict else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=detail) from exc
    if not result.created:
        http_response.status_code = status.HTTP_200_OK
    return _serialize_payment_attempt(result.payment_attempt, include_sensitive=True)


@router.get("", response_model=list[PaymentAttemptResponse], include_in_schema=False)
@router.get("/", response_model=list[PaymentAttemptResponse])
async def list_payment_attempts(
    order_id: UUID = Query(..., description="Canonical order identifier"),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_mobile_user_id),
    current_realm: RealmResolution = Depends(get_request_customer_realm),
) -> list[PaymentAttemptResponse]:
    order = await GetOrderUseCase(db).execute(order_id=order_id)
    if not _order_belongs_to_customer_realm(order, user_id=user_id, current_realm=current_realm):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    attempts = await ListPaymentAttemptsUseCase(db).execute(order_id=order_id)
    return [_serialize_payment_attempt(attempt) for attempt in attempts]


@router.get("/{payment_attempt_id}", response_model=PaymentAttemptResponse)
async def get_payment_attempt(
    payment_attempt_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_mobile_user_id),
    current_realm: RealmResolution = Depends(get_request_customer_realm),
) -> PaymentAttemptResponse:
    attempt = await GetPaymentAttemptUseCase(db).execute(payment_attempt_id=payment_attempt_id)
    if attempt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment attempt not found")
    order = await GetOrderUseCase(db).execute(order_id=attempt.order_id)
    if not _order_belongs_to_customer_realm(order, user_id=user_id, current_realm=current_realm):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment attempt not found")
    return _serialize_payment_attempt(attempt)
