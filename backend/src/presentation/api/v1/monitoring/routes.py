"""Monitoring and health check routes."""

from datetime import UTC, datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.auth.permissions import Permission
from src.application.use_cases.monitoring.bandwidth_analytics import BandwidthAnalyticsUseCase
from src.application.use_cases.monitoring.server_bandwidth import ServerBandwidthUseCase
from src.application.use_cases.monitoring.system_health import SystemHealthUseCase
from src.infrastructure.cache.redis_client import get_redis
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.remnawave import get_remnawave_client
from src.presentation.dependencies.roles import require_permission

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
    client=Depends(get_remnawave_client),
    _: None = Depends(require_permission(Permission.MONITORING_READ)),
) -> Dict[str, Any]:
    """Authenticated system health check endpoint."""
    try:
        use_case = SystemHealthUseCase(
            session=db,
            redis_client=redis,
            remnawave_client=client,
        )
        result = await use_case.execute()

        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Health check failed: {str(e)}",
        )


@router.get("/stats")
async def get_system_stats(
    db: AsyncSession = Depends(get_db),
    client=Depends(get_remnawave_client),
    _: None = Depends(require_permission(Permission.MONITORING_READ)),
) -> Dict[str, Any]:
    """Get bandwidth statistics (authenticated)."""
    try:
        use_case = ServerBandwidthUseCase(client=client)
        stats = await use_case.execute()

        return {
            "timestamp": datetime.now(UTC).isoformat(),
            **stats,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get system stats: {str(e)}",
        )


@router.get("/bandwidth")
async def get_bandwidth_analytics(
    db: AsyncSession = Depends(get_db),
    client=Depends(get_remnawave_client),
    period: str = Query(
        "today",
        max_length=50,
        description="Period for analytics: today, week, month",
    ),
    _: None = Depends(require_permission(Permission.MONITORING_READ)),
) -> Dict[str, Any]:
    """Get bandwidth analytics for a specific period (authenticated)."""
    try:
        use_case = BandwidthAnalyticsUseCase(client=client)
        stats = await use_case.execute(period=period)

        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "period": period,
            **stats,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get bandwidth analytics: {str(e)}",
        )
