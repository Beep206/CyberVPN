"""Usage statistics endpoint.

Provides ``GET /api/v1/users/me/usage`` so that the currently
authenticated user can view their VPN usage statistics.

This is a **placeholder implementation** -- returns mock data.
Real implementation will query Remnawave API and/or the database.
"""

import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends

from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.presentation.dependencies.auth import get_current_active_user

from .schemas import UsageResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users/me", tags=["usage"])


@router.get(
    "/usage",
    response_model=UsageResponse,
    summary="Get current user usage statistics",
    description=(
        "Returns VPN usage statistics for the currently authenticated user. "
        "Placeholder implementation returning mock data."
    ),
)
async def get_usage(
    current_user: AdminUserModel = Depends(get_current_active_user),
) -> UsageResponse:
    """Return usage statistics for the authenticated user.

    This is a placeholder that returns mock data.  A real implementation
    would query Remnawave for bandwidth and connection metrics.
    """
    logger.info(
        "Usage statistics requested",
        extra={"user_id": str(current_user.id)},
    )

    now = datetime.now(UTC)
    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    next_month = (period_start.replace(day=28) + timedelta(days=4)).replace(day=1)

    return UsageResponse(
        bandwidth_used_bytes=5_368_709_120,
        bandwidth_limit_bytes=107_374_182_400,
        connections_active=1,
        connections_limit=5,
        period_start=period_start,
        period_end=next_month,
        last_connection_at=now - timedelta(hours=2),
    )
