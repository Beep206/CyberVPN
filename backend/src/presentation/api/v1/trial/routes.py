"""Trial period management endpoints.

Provides:
- ``POST /api/v1/trial/activate`` -- activate a 7-day trial
- ``GET  /api/v1/trial/status``   -- check current trial status

Both endpoints require authentication and track trial usage in the database.
"""

import logging

import redis.asyncio as redis
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.trial.activate_trial import ActivateTrialUseCase
from src.application.use_cases.trial.get_trial_status import GetTrialStatusUseCase
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.monitoring.instrumentation.routes import track_trial_activation
from src.presentation.dependencies.auth import get_current_active_user
from src.presentation.dependencies.database import get_db

from .schemas import TrialActivateResponse, TrialStatusResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/trial", tags=["trial"])


@router.post(
    "/activate",
    response_model=TrialActivateResponse,
    summary="Activate trial period",
    description="Activate a 7-day trial period for the authenticated user.",
    responses={
        400: {"description": "Trial already activated or currently active"},
        404: {"description": "User not found"},
        429: {"description": "Rate limit exceeded (3 requests per hour)"},
    },
)
async def activate_trial(
    current_user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
) -> TrialActivateResponse:
    """Activate a trial period for the authenticated user.

    Checks eligibility (user hasn't used a trial before), then activates
    a 7-day trial period and records it in the database.

    Rate limited to 3 requests per hour per user to prevent abuse.
    """
    # Rate limiting: 3 requests per hour per user
    rate_limit_key = f"trial_activate:{current_user.id}"
    rate_limit_window = 3600  # 1 hour in seconds
    rate_limit_max = 3

    # Check current request count
    current_count = await redis_client.get(rate_limit_key)
    if current_count and int(current_count) >= rate_limit_max:
        ttl = await redis_client.ttl(rate_limit_key)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again in {ttl} seconds.",
        )

    use_case = ActivateTrialUseCase(db)

    try:
        result = await use_case.execute(current_user.id)

        if not result.activated:
            # Trial is already active
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.message,
            )

        # Increment rate limit counter
        pipe = redis_client.pipeline()
        await pipe.incr(rate_limit_key)
        await pipe.expire(rate_limit_key, rate_limit_window)
        await pipe.execute()

        # Track trial activation
        track_trial_activation()

        return TrialActivateResponse(
            activated=result.activated,
            trial_end=result.trial_end,
            message=result.message,
        )
    except ValueError as exc:
        # User not found or trial already used
        if "already activated" in str(exc):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "/status",
    response_model=TrialStatusResponse,
    summary="Get trial status",
    description="Returns the current trial status for the authenticated user.",
    responses={404: {"description": "User not found"}},
)
async def get_trial_status(
    current_user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> TrialStatusResponse:
    """Return the trial status for the authenticated user.

    Retrieves trial activation date, expiration date, and eligibility
    status from the database.
    """
    use_case = GetTrialStatusUseCase(db)

    try:
        status_data = await use_case.execute(current_user.id)

        return TrialStatusResponse(
            is_trial_active=status_data.is_trial_active,
            trial_start=status_data.trial_start,
            trial_end=status_data.trial_end,
            days_remaining=status_data.days_remaining,
            is_eligible=status_data.is_eligible,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
