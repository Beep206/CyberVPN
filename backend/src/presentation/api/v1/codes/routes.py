from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.stage1_growth_policy import (
    Stage1GrowthPolicyError,
    assert_stage1_checkout_codes_enabled,
    assert_stage1_referral_enabled,
)
from src.application.use_cases.growth_codes.resolve_code import (
    GrowthCodeResolutionOutcome,
    ResolveGrowthCodeUseCase,
)
from src.application.use_cases.referrals.claim_referral_attribution import (
    ClaimReferralAttributionUseCase,
    ReferralAttributionError,
    ReferralAttributionPartnerConflictError,
    ReferralAttributionSelfReferralError,
    ReferralAttributionWindowExpiredError,
)
from src.config.settings import settings
from src.domain.enums import (
    GrowthCodeActionContext,
    GrowthCodeRejectReason,
    GrowthCodeResolutionStatus,
    GrowthCodeType,
)
from src.infrastructure.database.repositories.storefront_repo import StorefrontRepository
from src.presentation.dependencies.auth import get_current_mobile_user_id
from src.presentation.dependencies.database import get_db

from .schemas import ResolveGrowthCodeRequest, ResolveGrowthCodeResponse

router = APIRouter(prefix="/codes", tags=["codes"])


def _claim_rejection_outcome(
    *,
    action_context: GrowthCodeActionContext,
    error: ReferralAttributionError,
) -> GrowthCodeResolutionOutcome:
    if isinstance(error, ReferralAttributionSelfReferralError):
        return GrowthCodeResolutionOutcome(
            accepted=False,
            code_type=GrowthCodeType.REFERRAL,
            action_context=action_context,
            result=GrowthCodeResolutionStatus.BLOCKED_BY_RISK,
            reject_reason=GrowthCodeRejectReason.CODE_BLOCKED_BY_RISK,
            user_message_key="growth_codes.referral.self_referral_blocked",
            issuer_type="user",
            owner_type="customer",
        )

    if isinstance(error, ReferralAttributionPartnerConflictError):
        return GrowthCodeResolutionOutcome(
            accepted=False,
            code_type=GrowthCodeType.REFERRAL,
            action_context=action_context,
            result=GrowthCodeResolutionStatus.CONFLICTED,
            reject_reason=GrowthCodeRejectReason.CODE_CONFLICTS_WITH_PARTNER_BINDING,
            conflict_code="partner_binding_present",
            user_message_key="growth_codes.referral.partner_binding_conflict",
            issuer_type="user",
            owner_type="customer",
        )

    if isinstance(error, ReferralAttributionWindowExpiredError):
        return GrowthCodeResolutionOutcome(
            accepted=False,
            code_type=GrowthCodeType.REFERRAL,
            action_context=action_context,
            result=GrowthCodeResolutionStatus.REJECTED,
            reject_reason=GrowthCodeRejectReason.CODE_NOT_ELIGIBLE_FOR_SURFACE,
            user_message_key="growth_codes.referral.signup_window_expired",
            issuer_type="user",
            owner_type="customer",
        )

    return GrowthCodeResolutionOutcome(
        accepted=False,
        code_type=None,
        action_context=action_context,
        result=GrowthCodeResolutionStatus.REJECTED,
        reject_reason=GrowthCodeRejectReason.CODE_NOT_FOUND,
        user_message_key="growth_codes.referral.unavailable",
    )


async def _claim_signup_referral(
    *,
    db: AsyncSession,
    user_id: UUID,
    code: str,
) -> GrowthCodeResolutionOutcome:
    try:
        claim = await ClaimReferralAttributionUseCase(db).execute(
            user_id=user_id,
            referral_code=code,
        )
    except ReferralAttributionError as exc:
        return _claim_rejection_outcome(
            action_context=GrowthCodeActionContext.SIGNUP,
            error=exc,
        )

    return GrowthCodeResolutionOutcome(
        accepted=True,
        code_type=GrowthCodeType.REFERRAL,
        action_context=GrowthCodeActionContext.SIGNUP,
        result=GrowthCodeResolutionStatus.ACCEPTED,
        user_message_key=f"growth_codes.referral.{claim.status}",
        issuer_type="user",
        owner_type="customer",
        resolved_code_id=claim.referrer_user_id,
    )


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

    if payload.action_context == GrowthCodeActionContext.SIGNUP:
        try:
            assert_stage1_referral_enabled(enabled=settings.referral_enabled)
        except Stage1GrowthPolicyError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

        result = await _claim_signup_referral(
            db=db,
            user_id=user_id,
            code=payload.code,
        )
    else:
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

        result = await ResolveGrowthCodeUseCase(db).execute(
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
