from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.commerce_sessions import (
    CheckoutSessionConflictError,
    CreateCheckoutSessionUseCase,
    GetCheckoutSessionUseCase,
    QuoteSessionDriftError,
    QuoteSessionExpiredError,
)
from src.presentation.dependencies.auth import get_current_mobile_user_id
from src.presentation.dependencies.auth_realms import RealmResolution, get_request_customer_realm
from src.presentation.dependencies.database import get_db

from .schemas import CheckoutSessionResponse, CreateCheckoutSessionRequest

router = APIRouter(prefix="/checkout-sessions", tags=["checkout-sessions"])


def _build_checkout_session_response(model) -> CheckoutSessionResponse:
    context_snapshot = model.context_snapshot or {}
    storefront_snapshot = context_snapshot.get("storefront") or {}
    pricebook_snapshot = context_snapshot.get("pricebook") or {}
    offer_snapshot = context_snapshot.get("offer") or {}
    legal_document_set_snapshot = context_snapshot.get("legal_document_set") or {}
    quote_snapshot = (model.checkout_snapshot or {}).get("quote_snapshot", {})
    return CheckoutSessionResponse(
        id=model.id,
        quote_session_id=model.quote_session_id,
        user_id=model.user_id,
        auth_realm_id=model.auth_realm_id,
        storefront_id=model.storefront_id,
        storefront_key=context_snapshot.get("storefront_key") or storefront_snapshot.get("storefront_key"),
        merchant_profile_id=model.merchant_profile_id,
        invoice_profile_id=model.invoice_profile_id,
        billing_descriptor_id=model.billing_descriptor_id,
        pricebook_id=model.pricebook_id,
        pricebook_key=context_snapshot.get("pricebook_key") or pricebook_snapshot.get("pricebook_key"),
        pricebook_entry_id=model.pricebook_entry_id,
        offer_id=model.offer_id,
        offer_key=context_snapshot.get("offer_key") or offer_snapshot.get("offer_key"),
        legal_document_set_id=model.legal_document_set_id,
        legal_document_set_key=context_snapshot.get("legal_document_set_key")
        or legal_document_set_snapshot.get("set_key"),
        program_eligibility_policy_id=model.program_eligibility_policy_id,
        subscription_plan_id=model.subscription_plan_id,
        sale_channel=model.sale_channel,
        currency_code=model.currency_code,
        status=model.checkout_status,
        idempotency_key=model.idempotency_key,
        expires_at=model.expires_at,
        quote=quote_snapshot,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


@router.post("/", response_model=CheckoutSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_checkout_session(
    payload: CreateCheckoutSessionRequest,
    request: Request,
    http_response: Response,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_mobile_user_id),
    current_realm: RealmResolution = Depends(get_request_customer_realm),
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=1, max_length=120),
) -> CheckoutSessionResponse:
    use_case = CreateCheckoutSessionUseCase(db)
    try:
        checkout_session, created = await use_case.execute(
            quote_session_id=payload.quote_session_id,
            user_id=user_id,
            current_realm=current_realm,
            idempotency_key=idempotency_key,
            host=request.headers.get("X-Forwarded-Host") or request.headers.get("Host"),
        )
    except QuoteSessionExpiredError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except QuoteSessionDriftError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except CheckoutSessionConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    response = _build_checkout_session_response(checkout_session)
    if created:
        return response
    http_response.status_code = status.HTTP_200_OK
    return response


@router.get("/{checkout_session_id}", response_model=CheckoutSessionResponse)
async def get_checkout_session(
    checkout_session_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_mobile_user_id),
) -> CheckoutSessionResponse:
    use_case = GetCheckoutSessionUseCase(db)
    checkout_session = await use_case.execute(checkout_session_id=checkout_session_id)
    if checkout_session is None or checkout_session.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checkout session not found")
    return _build_checkout_session_response(checkout_session)
