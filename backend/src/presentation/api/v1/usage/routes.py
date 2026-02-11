"""Usage statistics endpoint.

Provides ``GET /api/v1/users/me/usage`` so that the currently
authenticated user can view their VPN usage statistics.

Fetches real data from Remnawave VPN backend.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from src.application.use_cases.usage.get_user_usage import GetUserUsageUseCase
from src.infrastructure.database.models.admin_user_model import AdminUserModel
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

    # Initialize gateway and use case
    user_gateway = RemnawaveUserGateway(remnawave_client)
    use_case = GetUserUsageUseCase(user_gateway)

    try:
        # Fetch real usage data from Remnawave
        usage_data = await use_case.execute(current_user.id)

        return UsageResponse(
            bandwidth_used_bytes=usage_data.bandwidth_used_bytes,
            bandwidth_limit_bytes=usage_data.bandwidth_limit_bytes,
            connections_active=usage_data.connections_active,
            connections_limit=usage_data.connections_limit,
            period_start=usage_data.period_start,
            period_end=usage_data.period_end,
            last_connection_at=usage_data.last_connection_at,
        )
    except ValueError as exc:
        logger.warning(
            "User not found in Remnawave",
            extra={"user_id": str(current_user.id), "error": str(exc)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in VPN backend",
        ) from exc
    except Exception as exc:
        logger.exception(
            "Failed to fetch usage statistics from Remnawave",
            extra={"user_id": str(current_user.id)},
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="VPN backend unavailable",
        ) from exc
