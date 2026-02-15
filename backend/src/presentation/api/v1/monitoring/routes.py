"""Monitoring and health check routes."""

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Query

from src.application.use_cases.auth.permissions import Permission
from src.application.use_cases.monitoring.bandwidth_analytics import BandwidthAnalyticsUseCase
from src.application.use_cases.monitoring.server_bandwidth import ServerBandwidthUseCase
from src.application.use_cases.monitoring.system_health import SystemHealthUseCase
from src.infrastructure.cache.redis_client import check_redis_connection
from src.infrastructure.cache.response_cache import response_cache
from src.infrastructure.database.session import check_db_connection
from src.infrastructure.monitoring.metrics import monitoring_operations_total
from src.presentation.dependencies.remnawave import get_remnawave_client
from src.presentation.dependencies.roles import require_permission

from .schemas import BandwidthResponse, HealthResponse, StatsResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get(
    "/health",
    response_model=HealthResponse,
    responses={503: {"description": "One or more components unhealthy"}},
)
@router.get(
    "/health/",
    response_model=HealthResponse,
    include_in_schema=False,
)
async def health_check(
    client=Depends(get_remnawave_client),
    _: None = Depends(require_permission(Permission.MONITORING_READ)),
) -> dict[str, Any]:
    """Authenticated system health check endpoint."""

    async def _fetch() -> dict[str, Any]:
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
        return await use_case.execute()

    result = await response_cache.get_or_fetch("monitoring:health", 10, _fetch)
    monitoring_operations_total.labels(operation="health_check").inc()
    return result


@router.get(
    "/stats",
    response_model=StatsResponse,
    responses={200: {"model": StatsResponse, "description": "Server bandwidth statistics"}},
)
@router.get(
    "/stats/",
    response_model=StatsResponse,
    include_in_schema=False,
)
async def get_system_stats(
    client=Depends(get_remnawave_client),
    _: None = Depends(require_permission(Permission.MONITORING_READ)),
) -> dict[str, Any]:
    """Get bandwidth statistics (authenticated)."""

    async def _fetch() -> dict[str, Any]:
        use_case = ServerBandwidthUseCase(client=client)

        try:
            stats = await use_case.execute()
        except Exception:
            logger.warning("Remnawave unavailable for monitoring stats, returning zeros")
            stats = {
                "total_users": 0,
                "active_users": 0,
                "total_servers": 0,
                "online_servers": 0,
                "total_traffic_bytes": 0,
            }

        return {
            "timestamp": datetime.now(UTC).isoformat(),
            **stats,
        }

    result = await response_cache.get_or_fetch("monitoring:stats", 15, _fetch)
    monitoring_operations_total.labels(operation="stats").inc()
    return result


@router.get(
    "/bandwidth",
    response_model=BandwidthResponse,
    responses={200: {"model": BandwidthResponse, "description": "Bandwidth analytics data"}},
)
@router.get(
    "/bandwidth/",
    response_model=BandwidthResponse,
    include_in_schema=False,
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

    async def _fetch() -> dict[str, Any]:
        use_case = BandwidthAnalyticsUseCase(client=client)

        try:
            stats = await use_case.execute(period=period)
        except Exception:
            logger.warning("Remnawave unavailable for bandwidth analytics, returning zeros")
            stats = {"bytes_in": 0, "bytes_out": 0}

        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "period": period,
            **stats,
        }

    result = await response_cache.get_or_fetch(f"monitoring:bandwidth:{period}", 10, _fetch)
    monitoring_operations_total.labels(operation="bandwidth").inc()
    return result
