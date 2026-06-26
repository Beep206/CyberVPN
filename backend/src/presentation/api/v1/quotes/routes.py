from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.commerce_sessions import CreateQuoteSessionUseCase, GetQuoteSessionUseCase
from src.application.use_cases.partner_attribution.attribution import PartnerAttributionError
from src.application.use_cases.partner_attribution.utils import PARTNER_ATTRIBUTION_COOKIE_NAME
from src.presentation.api.shared.private_catalog_session import (
    PRIVATE_CATALOG_ANONYMOUS_SESSION_COOKIE,
    private_catalog_anonymous_session_subject,
)
from src.presentation.dependencies.auth import get_current_mobile_user_id
from src.presentation.dependencies.auth_realms import RealmResolution, get_request_customer_realm
from src.presentation.dependencies.database import get_db

from .schemas import CreateQuoteSessionRequest, QuoteSessionResponse

router = APIRouter(prefix="/quotes", tags=["quotes"])


def _clear_attribution_cookie(response: Response) -> None:
    response.delete_cookie(
        key=PARTNER_ATTRIBUTION_COOKIE_NAME,
        path="/",
        secure=True,
        httponly=True,
        samesite="lax",
    )
    response.headers["Cache-Control"] = "no-store"


def _partner_attribution_error_response(exc: PartnerAttributionError) -> JSONResponse:
    response = JSONResponse(
        status_code=exc.status_code,
        content={"detail": {"code": exc.code, "message": exc.message, "retryable": exc.status_code >= 500}},
    )
    response.headers["Cache-Control"] = "no-store"
    if exc.clear_cookie:
        _clear_attribution_cookie(response)
    return response


def _build_quote_session_response(model) -> QuoteSessionResponse:
    context_snapshot = model.context_snapshot or {}
    storefront_snapshot = context_snapshot.get("storefront") or {}
    pricebook_snapshot = context_snapshot.get("pricebook") or {}
    offer_snapshot = context_snapshot.get("offer") or {}
    legal_document_set_snapshot = context_snapshot.get("legal_document_set") or {}
    return QuoteSessionResponse(
        id=model.id,
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
        status=model.quote_status,
        expires_at=model.expires_at,
        quote=model.quote_snapshot,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


@router.post("/", response_model=QuoteSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_quote_session(
    payload: CreateQuoteSessionRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_mobile_user_id),
    current_realm: RealmResolution = Depends(get_request_customer_realm),
) -> QuoteSessionResponse | JSONResponse:
    use_case = CreateQuoteSessionUseCase(db)
    attribution_cookie_token = request.cookies.get(PARTNER_ATTRIBUTION_COOKIE_NAME)
    try:
        created = await use_case.execute(
            user_id=user_id,
            current_realm=current_realm,
            storefront_key=payload.storefront_key,
            host=request.headers.get("X-Forwarded-Host") or request.headers.get("Host"),
            plan_id=payload.plan_id,
            pricebook_key=payload.pricebook_key,
            offer_key=payload.offer_key,
            code_input=payload.code_input,
            promo_code=payload.promo_code,
            partner_code=payload.partner_code,
            use_wallet=payload.use_wallet,
            currency=payload.currency,
            channel=payload.channel,
            addons=[addon.model_dump() for addon in payload.addons],
            private_catalog_grant_id=payload.private_catalog_grant_id,
            source_host=current_realm.host,
            source_path=request.url.path,
            campaign_params={key: value for key, value in request.query_params.items()},
            partner_attribution_cookie_token=attribution_cookie_token,
            private_catalog_anonymous_session_id=(
                private_catalog_anonymous_session_subject(request.cookies.get(PRIVATE_CATALOG_ANONYMOUS_SESSION_COOKIE))
                if payload.private_catalog_grant_id is not None
                else None
            ),
        )
    except PartnerAttributionError as exc:
        await db.rollback()
        return _partner_attribution_error_response(exc)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if attribution_cookie_token:
        _clear_attribution_cookie(response)
    return _build_quote_session_response(created)


@router.get("/{quote_session_id}", response_model=QuoteSessionResponse)
async def get_quote_session(
    quote_session_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_mobile_user_id),
) -> QuoteSessionResponse:
    use_case = GetQuoteSessionUseCase(db)
    quote_session = await use_case.execute(quote_session_id=quote_session_id)
    if quote_session is None or quote_session.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quote session not found")
    return _build_quote_session_response(quote_session)
