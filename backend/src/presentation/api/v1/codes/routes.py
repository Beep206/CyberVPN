from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.stage1_growth_policy import (
    Stage1GrowthPolicyError,
    assert_stage1_checkout_codes_enabled,
)
from src.application.use_cases.growth_codes import ResolveGrowthCodeUseCase
from src.config.settings import settings
from src.domain.enums import GrowthCodeActionContext
from src.infrastructure.database.repositories.storefront_repo import StorefrontRepository
from src.presentation.dependencies.auth import get_current_mobile_user_id
from src.presentation.dependencies.database import get_db

from .schemas import ResolveGrowthCodeRequest, ResolveGrowthCodeResponse

router = APIRouter(prefix="/codes", tags=["codes"])


@router.post("/resolve", response_model=ResolveGrowthCodeResponse)
async def resolve_growth_code(
    payload: ResolveGrowthCodeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_mobile_user_id),
) -> ResolveGrowthCodeResponse:
    if payload.action_context == GrowthCodeActionContext.CHECKOUT:
        try:
            assert_stage1_checkout_codes_enabled(
                code_input=payload.code,
                enabled=settings.checkout_code_discounts_enabled,
            )
        except Stage1GrowthPolicyError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    storefront_id = None
    storefront_repo = StorefrontRepository(db)
    if payload.storefront_key:
        storefront = await storefront_repo.get_storefront_by_key(payload.storefront_key)
        if storefront is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Storefront not found")
        storefront_id = storefront.id
    else:
        host = request.headers.get("X-Forwarded-Host") or request.headers.get("Host")
        if host:
            storefront = await storefront_repo.get_storefront_by_host(host)
            storefront_id = storefront.id if storefront is not None else None

    use_case = ResolveGrowthCodeUseCase(db)
    result = await use_case.execute(
        code=payload.code,
        action_context=payload.action_context,
        user_id=user_id,
        plan_id=payload.plan_id,
        amount=Decimal(str(payload.amount)) if payload.amount is not None else None,
        storefront_id=storefront_id,
        existing_partner_code_present=payload.existing_partner_code_present,
        existing_promo_present=payload.existing_promo_present,
        surface=payload.channel,
    )
    await db.commit()
    return ResolveGrowthCodeResponse(
        accepted=result.accepted,
        code_type=result.code_type,
        action_context=result.action_context,
        result=result.result,
        reject_reason=result.reject_reason,
        conflict_code=result.conflict_code,
        wrong_context_target=result.wrong_context_target,
        issuer_type=result.issuer_type,
        owner_type=result.owner_type,
        resolved_code_id=result.resolved_code_id,
        promo_code_id=result.promo_code_id,
        partner_code_id=result.partner_code_id,
        user_message_key=result.user_message_key,
    )
