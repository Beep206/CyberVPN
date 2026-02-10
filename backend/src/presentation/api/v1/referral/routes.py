"""Referral API routes for mobile users."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.config_service import ConfigService
from src.application.use_cases.referrals.get_referral_code import GetReferralCodeUseCase
from src.application.use_cases.referrals.get_referral_stats import GetReferralStatsUseCase
from src.domain.exceptions import DomainError
from src.infrastructure.database.repositories.referral_commission_repo import (
    ReferralCommissionRepository,
)
from src.infrastructure.database.repositories.system_config_repo import SystemConfigRepository
from src.presentation.dependencies.auth import get_current_mobile_user_id
from src.presentation.dependencies.database import get_db

from .schemas import (
    ReferralCodeResponse,
    ReferralCommissionResponse,
    ReferralStatsResponse,
    ReferralStatusResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/referral", tags=["referral"])


@router.get("/status", response_model=ReferralStatusResponse)
async def get_referral_status(
    user_id: UUID = Depends(get_current_mobile_user_id),
    db: AsyncSession = Depends(get_db),
) -> ReferralStatusResponse:
    """Return whether the referral programme is enabled and the current commission rate."""
    config_repo = SystemConfigRepository(db)
    config_service = ConfigService(config_repo)

    enabled = await config_service.is_referral_enabled()
    commission_rate = await config_service.get_referral_commission_rate()

    return ReferralStatusResponse(enabled=enabled, commission_rate=commission_rate)


@router.get("/code", response_model=ReferralCodeResponse)
async def get_referral_code(
    user_id: UUID = Depends(get_current_mobile_user_id),
    db: AsyncSession = Depends(get_db),
) -> ReferralCodeResponse:
    """Get or generate the authenticated user's referral code."""
    use_case = GetReferralCodeUseCase(db)
    try:
        code = await use_case.execute(user_id)
    except DomainError as exc:
        logger.warning("get_referral_code_failed", extra={"user_id": str(user_id), "error": str(exc)})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc

    return ReferralCodeResponse(referral_code=code)


@router.get("/stats", response_model=ReferralStatsResponse)
async def get_referral_stats(
    user_id: UUID = Depends(get_current_mobile_user_id),
    db: AsyncSession = Depends(get_db),
) -> ReferralStatsResponse:
    """Return aggregated referral statistics for the authenticated user."""
    config_repo = SystemConfigRepository(db)
    config_service = ConfigService(config_repo)
    commission_repo = ReferralCommissionRepository(db)

    use_case = GetReferralStatsUseCase(commission_repo, config_service)
    try:
        result = await use_case.execute(user_id)
    except DomainError as exc:
        logger.warning("get_referral_stats_failed", extra={"user_id": str(user_id), "error": str(exc)})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc

    return ReferralStatsResponse(
        total_referrals=result["total_referrals"],
        total_earned=float(result["total_earned"]),
        commission_rate=result["commission_rate"],
    )


@router.get("/recent", response_model=list[ReferralCommissionResponse])
async def get_recent_commissions(
    user_id: UUID = Depends(get_current_mobile_user_id),
    db: AsyncSession = Depends(get_db),
) -> list[ReferralCommissionResponse]:
    """Return the 10 most recent referral commissions for the authenticated user."""
    commission_repo = ReferralCommissionRepository(db)
    commissions = await commission_repo.get_by_referrer(user_id, limit=10)
    return commissions
