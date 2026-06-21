"""Partner attribution public transfer and authenticated claim routes."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.partner_attribution.attribution import (
    CapturePartnerAttributionCommand,
    CapturePartnerAttributionUseCase,
    ClaimPartnerAttributionCommand,
    ClaimPartnerAttributionUseCase,
    ConsumePartnerAttributionTransferCommand,
    ConsumePartnerAttributionTransferUseCase,
    PartnerAttributionError,
)
from src.application.use_cases.partner_attribution.utils import (
    PARTNER_ATTRIBUTION_COOKIE_NAME,
    PARTNER_ATTRIBUTION_MAX_AGE_SECONDS,
)
from src.config.settings import settings
from src.infrastructure.cache.redis_client import get_redis
from src.presentation.dependencies.auth import get_current_mobile_user_id
from src.presentation.dependencies.auth_realms import (
    RealmResolution,
    get_request_customer_realm,
    get_request_public_customer_realm,
)
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.partner_attribution_rate_limit import (
    check_partner_attribution_capture_rate_limit,
    check_partner_attribution_claim_rate_limit,
    check_partner_attribution_transfer_rate_limit,
)

from .schemas import (
    PartnerAttributionCaptureRequest,
    PartnerAttributionCaptureResponse,
    PartnerAttributionClaimRequest,
    PartnerAttributionClaimResponse,
    PartnerAttributionTransferConsumeRequest,
    PartnerAttributionTransferConsumeResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/partner-attribution", tags=["partner-attribution"])


def _cookie_secure() -> bool:
    return settings.environment.strip().lower() == "production"


def _set_attribution_cookie(response: Response, token: str, *, max_age_seconds: int) -> None:
    response.set_cookie(
        key=PARTNER_ATTRIBUTION_COOKIE_NAME,
        value=token,
        max_age=max(0, min(PARTNER_ATTRIBUTION_MAX_AGE_SECONDS, max_age_seconds)),
        httponly=True,
        secure=_cookie_secure(),
        samesite="lax",
        path="/",
    )
    response.headers["Cache-Control"] = "no-store"


def _clear_attribution_cookie(response: Response) -> None:
    response.delete_cookie(key=PARTNER_ATTRIBUTION_COOKIE_NAME, path="/")
    response.headers["Cache-Control"] = "no-store"


def _error_response(exc: PartnerAttributionError) -> JSONResponse:
    response = JSONResponse(
        status_code=exc.status_code,
        content={"detail": {"code": exc.code, "message": exc.message, "retryable": exc.status_code >= 500}},
    )
    response.headers["Cache-Control"] = "no-store"
    if exc.clear_cookie:
        _clear_attribution_cookie(response)
    return response


@router.post("/capture", response_model=PartnerAttributionCaptureResponse)
async def capture_partner_attribution(
    payload: PartnerAttributionCaptureRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    redis_client=Depends(get_redis),
    current_realm: RealmResolution = Depends(get_request_public_customer_realm),
) -> PartnerAttributionCaptureResponse | JSONResponse:
    await check_partner_attribution_capture_rate_limit(
        request=request,
        payload=payload,
        redis_client=redis_client,
    )
    command = CapturePartnerAttributionCommand(
        public_token=payload.public_token,
        source_host=current_realm.host,
        source_path=payload.source_path,
        destination_path=payload.destination_path,
        locale=payload.locale,
        sale_channel=payload.sale_channel,
        sub_ids=payload.sub_ids,
        click_id=payload.click_id,
        browser_key=payload.browser_key,
        capture_idempotency_key=idempotency_key,
        campaign_params=payload.campaign_params,
        current_realm=current_realm,
    )
    try:
        result = await CapturePartnerAttributionUseCase(db).execute(command)
        await db.commit()
    except PartnerAttributionError as exc:
        await db.rollback()
        return _error_response(exc)
    except Exception as exc:
        await db.rollback()
        logger.exception("partner_attribution_capture_transient_failure")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "PARTNER_ATTRIBUTION_TRANSIENT_FAILURE",
                "message": "Partner attribution is temporarily unavailable.",
            },
        ) from exc

    return PartnerAttributionCaptureResponse(
        attribution_id=result.attribution_id,
        captured_at=result.captured_at,
        expires_at=result.expires_at,
        masked_code=result.masked_code,
        transfer_token=result.transfer_token,
        redirect_url=result.redirect_url,
    )


@router.post("/transfer/consume", response_model=PartnerAttributionTransferConsumeResponse)
async def consume_partner_attribution_transfer(
    payload: PartnerAttributionTransferConsumeRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis_client=Depends(get_redis),
) -> PartnerAttributionTransferConsumeResponse | JSONResponse:
    await check_partner_attribution_transfer_rate_limit(request=request, redis_client=redis_client)
    try:
        result = await ConsumePartnerAttributionTransferUseCase(db).execute(
            ConsumePartnerAttributionTransferCommand(transfer_token=payload.transfer_token)
        )
        await db.commit()
    except PartnerAttributionError as exc:
        await db.rollback()
        return _error_response(exc)
    except Exception as exc:
        await db.rollback()
        logger.exception("partner_attribution_transfer_consume_transient_failure")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "PARTNER_ATTRIBUTION_TRANSIENT_FAILURE",
                "message": "Partner attribution is temporarily unavailable.",
            },
        ) from exc

    max_age_seconds = int(max((result.expires_at - datetime.now(UTC)).total_seconds(), 0))
    _set_attribution_cookie(response, result.cookie_token, max_age_seconds=max_age_seconds)
    return PartnerAttributionTransferConsumeResponse(
        attribution_id=result.attribution_id,
        captured_at=result.captured_at,
        expires_at=result.expires_at,
        masked_code=result.masked_code,
    )


@router.post("/claim", response_model=PartnerAttributionClaimResponse)
async def claim_partner_attribution(
    payload: PartnerAttributionClaimRequest,
    request: Request,
    response: Response,
    user_id: UUID = Depends(get_current_mobile_user_id),
    db: AsyncSession = Depends(get_db),
    redis_client=Depends(get_redis),
    current_realm: RealmResolution = Depends(get_request_customer_realm),
) -> PartnerAttributionClaimResponse | JSONResponse:
    await check_partner_attribution_claim_rate_limit(user_id=user_id, redis_client=redis_client)
    cookie_token = request.cookies.get(PARTNER_ATTRIBUTION_COOKIE_NAME)
    try:
        result = await ClaimPartnerAttributionUseCase(db).execute(
            ClaimPartnerAttributionCommand(
                user_id=user_id,
                cookie_token=cookie_token,
                current_realm=current_realm,
            )
        )
        await db.commit()
    except PartnerAttributionError as exc:
        await db.rollback()
        return _error_response(exc)
    except Exception as exc:
        await db.rollback()
        logger.exception("partner_attribution_claim_transient_failure", extra={"user_id": str(user_id)})
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "PARTNER_ATTRIBUTION_TRANSIENT_FAILURE",
                "message": "Partner attribution is temporarily unavailable.",
            },
        ) from exc

    if result.clear_cookie:
        _clear_attribution_cookie(response)
    else:
        response.headers["Cache-Control"] = "no-store"
    return PartnerAttributionClaimResponse(
        status=result.status,
        partner_account_id=result.partner_account_id,
        partner_code_id=result.partner_code_id,
        binding_id=result.binding_id,
        claimed_at=result.claimed_at,
    )
