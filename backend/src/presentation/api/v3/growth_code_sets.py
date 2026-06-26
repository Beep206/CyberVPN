from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.private_catalog import (
    PrivateCatalogPreflightCommand,
    PrivateCatalogPreflightUseCase,
)
from src.application.use_cases.private_catalog.preflight import PrivateCatalogCodeInput
from src.infrastructure.database.repositories.private_catalog_repo import SqlAlchemyPrivateCatalogRepository
from src.presentation.api.shared.private_catalog_session import ensure_private_catalog_anonymous_session
from src.presentation.dependencies.auth import get_optional_current_mobile_user_id
from src.presentation.dependencies.database import get_db

router = APIRouter(prefix="/growth/code-sets", tags=["growth-code-sets-v3"])


class CodeSetPreflightCodeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=120)
    client_slot_id: str = Field(min_length=1, max_length=80)


class CodeSetPreflightRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    codes: list[CodeSetPreflightCodeRequest] = Field(min_length=1, max_length=5)
    storefront_key: str = Field(min_length=1, max_length=80)
    channel: str = Field(min_length=1, max_length=30)
    currency: str = Field(min_length=3, max_length=3)
    anonymous_session_id: str | None = Field(default=None, max_length=120)


class CodeSetPreflightApplicationResponse(BaseModel):
    client_slot_id: str
    masked_code: str
    status: str
    roles: list[str]
    message_key: str


class CodeSetPrivateCatalogGrantResponse(BaseModel):
    id: UUID
    expires_at: datetime


class CodeSetPrivateOfferPriceResponse(BaseModel):
    amount: str
    currency: str


class CodeSetPrivateOfferQuoteHandoffResponse(BaseModel):
    private_catalog_grant_id: UUID


class CodeSetPrivateOfferResponse(BaseModel):
    plan_id: UUID
    offer_id: UUID | None = None
    display_name: str
    duration_days: int
    price: CodeSetPrivateOfferPriceResponse
    entitlement_summary: dict[str, Any]
    quote_handoff: CodeSetPrivateOfferQuoteHandoffResponse


class CodeSetRiskResponse(BaseModel):
    action: str


class CodeSetPreflightResponse(BaseModel):
    code_set_id: UUID | None
    code_set_hash: str
    status: str
    applications: list[CodeSetPreflightApplicationResponse]
    private_catalog_grant: CodeSetPrivateCatalogGrantResponse | None
    private_offers: list[CodeSetPrivateOfferResponse]
    risk: CodeSetRiskResponse


@router.post("/preflight", response_model=CodeSetPreflightResponse)
async def preflight_growth_code_set(
    payload: CodeSetPreflightRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    user_id: UUID | None = Depends(get_optional_current_mobile_user_id),
) -> CodeSetPreflightResponse:
    use_case = _use_case(db)
    anonymous_session_id = None
    if user_id is None:
        anonymous_session_id = ensure_private_catalog_anonymous_session(request, response)
    try:
        result = await use_case.execute(
            PrivateCatalogPreflightCommand(
                codes=tuple(
                    PrivateCatalogCodeInput(code=item.code, client_slot_id=item.client_slot_id)
                    for item in payload.codes
                ),
                storefront_key=payload.storefront_key,
                channel=payload.channel,
                currency=payload.currency,
                anonymous_session_id=anonymous_session_id,
                user_id=user_id,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    response.headers["Cache-Control"] = "no-store, private"
    return CodeSetPreflightResponse(
        code_set_id=result.code_set_id,
        code_set_hash=result.code_set_hash,
        status=result.status,
        applications=[
            CodeSetPreflightApplicationResponse(
                client_slot_id=item.client_slot_id,
                masked_code=item.masked_code,
                status=item.status,
                roles=list(item.roles),
                message_key=item.message_key,
            )
            for item in result.applications
        ],
        private_catalog_grant=(
            CodeSetPrivateCatalogGrantResponse(
                id=result.private_catalog_grant.id,
                expires_at=result.private_catalog_grant.expires_at,
            )
            if result.private_catalog_grant
            else None
        ),
        private_offers=[
            CodeSetPrivateOfferResponse(
                plan_id=item.plan_id,
                display_name=item.display_name,
                duration_days=item.duration_days,
                price=CodeSetPrivateOfferPriceResponse(
                    amount=item.price_amount,
                    currency=item.price_currency,
                ),
                entitlement_summary=item.entitlement_summary,
                quote_handoff=CodeSetPrivateOfferQuoteHandoffResponse(
                    private_catalog_grant_id=item.private_catalog_grant_id,
                ),
            )
            for item in result.private_offers
        ],
        risk=CodeSetRiskResponse(action=result.risk.action),
    )


def _use_case(db: AsyncSession) -> PrivateCatalogPreflightUseCase:
    return PrivateCatalogPreflightUseCase(SqlAlchemyPrivateCatalogRepository(db))
