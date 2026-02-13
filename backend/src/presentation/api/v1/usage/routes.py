"""Usage statistics endpoint.

Provides ``GET /api/v1/users/me/usage`` so that the currently
authenticated user can view their VPN usage statistics.

Fetches real data from Remnawave VPN backend.
"""

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends

from src.application.use_cases.usage.get_user_usage import GetUserUsageUseCase
from src.infrastructure.cache.response_cache import response_cache
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.monitoring.metrics import route_operations_total
from src.infrastructure.remnawave.client import RemnawaveClient, get_remnawave_client
from src.infrastructure.remnawave.user_gateway import RemnawaveUserGateway
from src.presentation.dependencies.auth import get_current_active_user

from .schemas import UsageResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users/me", tags=["usage"])


@router.get(
    "/usage",
    response_model=UsageResponse,
    summary="Get current user usage statistics",
    description="Returns VPN usage statistics for the currently authenticated user from Remnawave.",
    responses={
        404: {"description": "User not found in VPN backend"},
        502: {"description": "VPN backend unavailable"},
    },
)
async def get_usage(
    current_user: AdminUserModel = Depends(get_current_active_user),
    remnawave_client: RemnawaveClient = Depends(get_remnawave_client),
) -> UsageResponse:
    """Return usage statistics for the authenticated user from Remnawave.

    Fetches real bandwidth, connection, and billing period data from the VPN backend.
    """
    logger.info(
        "Usage statistics requested",
        extra={"user_id": str(current_user.id)},
    )

    async def _fetch() -> dict:
        user_gateway = RemnawaveUserGateway(remnawave_client)
        use_case = GetUserUsageUseCase(user_gateway)

        try:
            usage_data = await use_case.execute(current_user.id)

            route_operations_total.labels(route="usage", action="get_usage", status="success").inc()
            return UsageResponse(
                bandwidth_used_bytes=usage_data.bandwidth_used_bytes,
                bandwidth_limit_bytes=usage_data.bandwidth_limit_bytes,
                connections_active=usage_data.connections_active,
                connections_limit=usage_data.connections_limit,
                period_start=usage_data.period_start,
                period_end=usage_data.period_end,
                last_connection_at=usage_data.last_connection_at,
            ).model_dump(mode="json")
        except Exception as exc:
            logger.warning(
                "Could not fetch usage from Remnawave, returning empty usage",
                extra={"user_id": str(current_user.id), "error": str(exc)},
            )
            now = datetime.now(UTC)
            route_operations_total.labels(route="usage", action="get_usage", status="fallback").inc()
            return UsageResponse(
                bandwidth_used_bytes=0,
                bandwidth_limit_bytes=0,
                connections_active=0,
                connections_limit=0,
                period_start=now,
                period_end=now,
                last_connection_at=None,
            ).model_dump(mode="json")

    return await response_cache.get_or_fetch(f"usage:{current_user.id}", 30, _fetch)
