"""Trial period management endpoints.

Provides:
- ``POST /api/v1/trial/activate`` -- activate a 7-day trial
- ``GET  /api/v1/trial/status``   -- check current trial status

Both endpoints require authentication.

This is a **placeholder implementation** -- no database writes are
performed and eligibility is always ``True``.
"""

import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends

from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.presentation.dependencies.auth import get_current_active_user

from .schemas import TrialActivateResponse, TrialStatusResponse

logger = logging.getLogger(__name__)

TRIAL_DURATION_DAYS = 7

router = APIRouter(prefix="/trial", tags=["trial"])


@router.post(
    "/activate",
    response_model=TrialActivateResponse,
    summary="Activate trial period",
    description=(
        "Activate a 7-day trial period for the authenticated user. Placeholder implementation -- always succeeds."
    ),
)
async def activate_trial(
    current_user: AdminUserModel = Depends(get_current_active_user),
) -> TrialActivateResponse:
    """Activate a trial period for the authenticated user.

    This is a placeholder that always returns a successful activation.
    A real implementation would check trial eligibility in the database,
    provision a Remnawave subscription, and record the trial start/end.
    """
    now = datetime.now(UTC)
    trial_end = now + timedelta(days=TRIAL_DURATION_DAYS)

    logger.info(
        "Trial activated (placeholder)",
        extra={
            "user_id": str(current_user.id),
            "trial_end": trial_end.isoformat(),
        },
    )

    return TrialActivateResponse(
        activated=True,
        trial_end=trial_end,
        message=f"Trial activated successfully. Expires in {TRIAL_DURATION_DAYS} days.",
    )


@router.get(
    "/status",
    response_model=TrialStatusResponse,
    summary="Get trial status",
    description=(
        "Returns the current trial status for the authenticated user. "
        "Placeholder implementation -- always returns not active, eligible."
    ),
)
async def get_trial_status(
    current_user: AdminUserModel = Depends(get_current_active_user),
) -> TrialStatusResponse:
    """Return the trial status for the authenticated user.

    This is a placeholder that always returns the user as eligible
    but with no active trial.  A real implementation would query the
    database for trial records.
    """
    logger.info(
        "Trial status requested",
        extra={"user_id": str(current_user.id)},
    )

    return TrialStatusResponse(
        is_trial_active=False,
        trial_start=None,
        trial_end=None,
        days_remaining=0,
        is_eligible=True,
    )
