"""Referral API routes for mobile users."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.config_service import ConfigService
from src.application.services.stage1_growth_policy import (
    Stage1GrowthPolicyError,
    assert_stage1_referral_enabled,
)
from src.application.use_cases.referrals.get_referral_code import GetReferralCodeUseCase
from src.application.use_cases.referrals.get_referral_stats import GetReferralStatsUseCase
from src.application.use_cases.referrals.list_referral_rewards import ListReferralRewardsUseCase
from src.config.settings import settings
from src.domain.exceptions import DomainError
from src.infrastructure.database.repositories.growth_reward_allocation_repo import (
    GrowthRewardAllocationRepository,
)
from src.infrastructure.database.repositories.mobile_user_repo import MobileUserRepository
from src.infrastructure.database.repositories.referral_commission_repo import (
    ReferralCommissionRepository,
)
from src.infrastructure.database.repositories.system_config_repo import SystemConfigRepository
from src.infrastructure.monitoring.instrumentation.routes import track_referral_operation
from src.presentation.dependencies.auth import get_current_mobile_user_id
from src.presentation.dependencies.database import get_db

from .schemas import (
    ReferralCodeResponse,
    ReferralCommissionResponse,
    ReferralRewardResponse,
    ReferralStatsResponse,
    ReferralStatusResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/referral", tags=["referral"])


def _assert_referral_public_flow_enabled() -> None:
    try:
        assert_stage1_referral_enabled(enabled=settings.referral_enabled)
    except Stage1GrowthPolicyError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


def _serialize_referral_reward(model) -> ReferralRewardResponse:
    reward_payload = dict(model.reward_payload or {})
    payment_id = reward_payload.get("payment_id")
    referred_user_id = reward_payload.get("referred_user_id")
    return ReferralRewardResponse(
        id=model.id,
        referred_user_id=referred_user_id,
        payment_id=payment_id,
        reward_amount=float(model.quantity),
        currency=model.currency_code or "USD",
        reward_status=model.allocation_status,
        hold_until=model.hold_until,
        available_at=model.available_at,
        reversed_at=model.reversed_at,
        created_at=model.allocated_at,
    )


def _serialize_referral_reward_compat(model) -> ReferralCommissionResponse:
    reward_payload = dict(model.reward_payload or {})
    payment_id = reward_payload.get("payment_id")
    referred_user_id = reward_payload.get("referred_user_id")
    commission_rate = float(
        reward_payload.get("legacy_commission_rate")
        or reward_payload.get("friend_discount_value")
        or 0
    )
    return ReferralCommissionResponse(
        id=model.id,
        referred_user_id=referred_user_id,
        payment_id=payment_id,
        commission_amount=float(model.quantity),
        base_amount=float(reward_payload.get("base_amount") or 0),
        commission_rate=commission_rate,
        currency=model.currency_code or "USD",
        reward_status=model.allocation_status,
        hold_until=model.hold_until,
        available_at=model.available_at,
        reversed_at=model.reversed_at,
        source_model="growth_reward",
        created_at=model.allocated_at,
    )


@router.get("/status", response_model=ReferralStatusResponse)
async def get_referral_status(
    user_id: UUID = Depends(get_current_mobile_user_id),
    db: AsyncSession = Depends(get_db),
) -> ReferralStatusResponse:
    """Return whether the referral programme is enabled and the current commission rate."""
    config_repo = SystemConfigRepository(db)
    config_service = ConfigService(config_repo)

    enabled = await config_service.is_referral_enabled()
    commission_rate = await config_service.get_referral_commission_rate() if enabled else 0.0

    track_referral_operation(operation="status")
    return ReferralStatusResponse(
        enabled=enabled,
        commission_rate=commission_rate,
        friend_discount_pct=commission_rate,
        reward_hold_days=14 if enabled else 0,
    )


@router.get("/code", response_model=ReferralCodeResponse)
async def get_referral_code(
    user_id: UUID = Depends(get_current_mobile_user_id),
    db: AsyncSession = Depends(get_db),
) -> ReferralCodeResponse:
    """Get or generate the authenticated user's referral code."""
    _assert_referral_public_flow_enabled()
    use_case = GetReferralCodeUseCase(db)
    try:
        code = await use_case.execute(user_id)
    except DomainError as exc:
        logger.warning("get_referral_code_failed", extra={"user_id": str(user_id), "error": str(exc)})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc

    track_referral_operation(operation="get_code")
    return ReferralCodeResponse(referral_code=code)


@router.get("/stats", response_model=ReferralStatsResponse)
async def get_referral_stats(
    user_id: UUID = Depends(get_current_mobile_user_id),
    db: AsyncSession = Depends(get_db),
) -> ReferralStatsResponse:
    """Return aggregated referral statistics for the authenticated user."""
    _assert_referral_public_flow_enabled()
    config_repo = SystemConfigRepository(db)
    config_service = ConfigService(config_repo)
    commission_repo = ReferralCommissionRepository(db)
    growth_reward_repo = GrowthRewardAllocationRepository(db)
    mobile_user_repo = MobileUserRepository(db)

    use_case = GetReferralStatsUseCase(
        commission_repo,
        growth_reward_repo,
        mobile_user_repo,
        config_service,
    )
    try:
        result = await use_case.execute(user_id)
    except DomainError as exc:
        logger.warning("get_referral_stats_failed", extra={"user_id": str(user_id), "error": str(exc)})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc

    track_referral_operation(operation="stats")
    return ReferralStatsResponse(
        total_referrals=result["total_referrals"],
        total_earned=float(result["total_earned"]),
        commission_rate=result["commission_rate"],
        pending_rewards_usd=float(result["pending_rewards_usd"]),
        available_rewards_usd=float(result["available_rewards_usd"]),
        reversed_rewards_usd=float(result["reversed_rewards_usd"]),
        monthly_cap_used_usd=float(result["monthly_cap_used_usd"]),
        lifetime_cap_used_usd=float(result["lifetime_cap_used_usd"]),
        qualifying_orders=int(result["qualifying_orders"]),
    )


@router.get("/recent", response_model=list[ReferralCommissionResponse])
async def get_recent_commissions(
    user_id: UUID = Depends(get_current_mobile_user_id),
    db: AsyncSession = Depends(get_db),
) -> list[ReferralCommissionResponse]:
    """Return recent referral activity with compatibility fields for legacy clients."""
    _assert_referral_public_flow_enabled()
    commission_repo = ReferralCommissionRepository(db)
    reward_repo = GrowthRewardAllocationRepository(db)

    legacy_commissions = await commission_repo.get_by_referrer(user_id, limit=10)
    recent_rewards = await reward_repo.list_recent_referral_rewards(
        beneficiary_user_id=user_id,
        limit=10,
    )
    items = [
        *[
            ReferralCommissionResponse(
                id=commission.id,
                referred_user_id=commission.referred_user_id,
                payment_id=commission.payment_id,
                commission_amount=float(commission.commission_amount),
                base_amount=float(commission.base_amount),
                commission_rate=float(commission.commission_rate),
                currency=commission.currency,
                source_model="legacy_commission",
                created_at=commission.created_at,
            )
            for commission in legacy_commissions
        ],
        *[_serialize_referral_reward_compat(item) for item in recent_rewards],
    ]
    items.sort(key=lambda item: item.created_at, reverse=True)
    track_referral_operation(operation="list_recent_rewards")
    return items[:10]


@router.get("/rewards", response_model=list[ReferralRewardResponse])
async def get_referral_rewards(
    user_id: UUID = Depends(get_current_mobile_user_id),
    db: AsyncSession = Depends(get_db),
) -> list[ReferralRewardResponse]:
    _assert_referral_public_flow_enabled()
    rewards = await ListReferralRewardsUseCase(db).execute(
        beneficiary_user_id=user_id,
        limit=20,
    )
    track_referral_operation(operation="list_rewards")
    return [_serialize_referral_reward(item) for item in rewards]
