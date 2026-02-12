"""Monitoring and health check routes."""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Query

from src.application.use_cases.auth.permissions import Permission
from src.application.use_cases.monitoring.bandwidth_analytics import BandwidthAnalyticsUseCase
from src.application.use_cases.monitoring.server_bandwidth import ServerBandwidthUseCase
from src.application.use_cases.monitoring.system_health import SystemHealthUseCase
from src.infrastructure.cache.redis_client import check_redis_connection
from src.infrastructure.database.session import check_db_connection
from src.infrastructure.monitoring.metrics import monitoring_operations_total
from src.presentation.dependencies.remnawave import get_remnawave_client
from src.presentation.dependencies.roles import require_permission

from .schemas import BandwidthResponse, HealthResponse, StatsResponse

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get(
    "/health",
    response_model=HealthResponse,
    responses={503: {"description": "One or more components unhealthy"}},
)
async def health_check(
    client=Depends(get_remnawave_client),
    _: None = Depends(require_permission(Permission.MONITORING_READ)),
) -> dict[str, Any]:
    """Authenticated system health check endpoint."""

    async def db_check() -> None:
        if not await check_db_connection():
            raise RuntimeError("Database connection failed")

    async def redis_check() -> None:
        ok, _ = await check_redis_connection()
        if not ok:
            raise RuntimeError("Redis connection failed")

    async def remnawave_check() -> None:
        if not await client.health_check():
            raise RuntimeError("Remnawave API health check failed")

    use_case = SystemHealthUseCase(
        db_check=db_check,
        redis_check=redis_check,
        remnawave_check=remnawave_check,
    )
    result = await use_case.execute()

    monitoring_operations_total.labels(operation="health_check").inc()
    return result


@router.get(
    "/stats",
    response_model=StatsResponse,
    responses={200: {"model": StatsResponse, "description": "Server bandwidth statistics"}},
)
async def get_system_stats(
    client=Depends(get_remnawave_client),
    _: None = Depends(require_permission(Permission.MONITORING_READ)),
) -> dict[str, Any]:
    """Get bandwidth statistics (authenticated)."""
    use_case = ServerBandwidthUseCase(client=client)
    stats = await use_case.execute()

    monitoring_operations_total.labels(operation="stats").inc()
    return {
        "timestamp": datetime.now(UTC).isoformat(),
        **stats,
    }


@router.get(
    "/bandwidth",
    response_model=BandwidthResponse,
    responses={200: {"model": BandwidthResponse, "description": "Bandwidth analytics data"}},
)
async def get_bandwidth_analytics(
    client=Depends(get_remnawave_client),
    period: str = Query(
        "today",
        max_length=50,
        description="Period for analytics: today, week, month",
    ),
    _: None = Depends(require_permission(Permission.MONITORING_READ)),
) -> dict[str, Any]:
    """Get bandwidth analytics for a specific period (authenticated)."""
    use_case = BandwidthAnalyticsUseCase(client=client)
    stats = await use_case.execute(period=period)

    monitoring_operations_total.labels(operation="bandwidth").inc()
    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "period": period,
        **stats,
    }
