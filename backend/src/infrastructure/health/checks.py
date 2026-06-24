import asyncio
import logging
from datetime import UTC, datetime
from typing import Any, cast

import httpx
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.async_compat import resolve_maybe_awaitable

logger = logging.getLogger("cybervpn")


def _utc_timestamp() -> str:
    """Return an ISO-8601 UTC timestamp for health payloads."""
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


async def check_database(db_session: AsyncSession) -> dict[str, Any]:
    """
    Check database connectivity and health

    Args:
        db_session: SQLAlchemy async session

    Returns:
        Health check result with status and details
    """
    try:
        # Simple query to test connectivity
        result = await db_session.execute(text("SELECT 1"))
        result.scalar()

        return {"status": "healthy", "service": "database", "details": "PostgreSQL connection successful"}
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        return {"status": "unhealthy", "service": "database", "error": str(e)}


async def check_redis(redis_client: Redis) -> dict[str, Any]:
    """
    Check Redis connectivity and health

    Args:
        redis_client: Redis async client

    Returns:
        Health check result with status and details
    """
    try:
        # Ping Redis
        await resolve_maybe_awaitable(redis_client.ping())

        # Get info
        info = await resolve_maybe_awaitable(redis_client.info())

        return {
            "status": "healthy",
            "service": "redis",
            "details": {
                "connected_clients": info.get("connected_clients", "unknown"),
                "used_memory_human": info.get("used_memory_human", "unknown"),
            },
        }
    except Exception as e:
        logger.error(f"Redis health check failed: {str(e)}")
        return {"status": "unhealthy", "service": "redis", "error": str(e)}


async def check_remnawave(base_url: str, timeout: float = 5.0) -> dict[str, Any]:
    """
    Check Remnawave API connectivity and health

    Args:
        base_url: Remnawave API base URL
        timeout: Request timeout in seconds

    Returns:
        Health check result with status and details
    """
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            # Try to reach health endpoint
            response = await client.get(f"{base_url}/health")

            if response.status_code == 200:
                return {
                    "status": "healthy",
                    "service": "remnawave",
                    "details": "Remnawave API is reachable",
                    "response_time_ms": response.elapsed.total_seconds() * 1000,
                }
            else:
                return {
                    "status": "degraded",
                    "service": "remnawave",
                    "details": f"Unexpected status code: {response.status_code}",
                }
    except httpx.TimeoutException:
        logger.error("Remnawave health check timed out")
        return {"status": "unhealthy", "service": "remnawave", "error": "Request timed out"}
    except Exception as e:
        logger.error(f"Remnawave health check failed: {str(e)}")
        return {"status": "unhealthy", "service": "remnawave", "error": str(e)}


async def perform_all_checks(db_session: AsyncSession, redis_client: Redis, remnawave_url: str) -> dict[str, Any]:
    """
    Perform all health checks concurrently

    Args:
        db_session: SQLAlchemy async session
        redis_client: Redis async client
        remnawave_url: Remnawave API base URL

    Returns:
        Combined health check results
    """
    # Run all checks concurrently
    check_results = cast(
        tuple[dict[str, Any] | BaseException, dict[str, Any] | BaseException, dict[str, Any] | BaseException],
        await asyncio.gather(
            check_database(db_session),
            check_redis(redis_client),
            check_remnawave(remnawave_url),
            return_exceptions=True,
        ),
    )
    db_check_raw, redis_check_raw, remnawave_check_raw = check_results
    db_check = _normalize_check_result(db_check_raw)
    redis_check = _normalize_check_result(redis_check_raw)
    remnawave_check = _normalize_check_result(remnawave_check_raw)

    # Determine overall status
    checks = [db_check, redis_check, remnawave_check]
    unhealthy = any(c.get("status") == "unhealthy" or c.get("status") == "error" for c in checks)
    degraded = any(c.get("status") == "degraded" for c in checks)

    if unhealthy:
        overall_status = "unhealthy"
    elif degraded:
        overall_status = "degraded"
    else:
        overall_status = "healthy"

    return {
        "status": overall_status,
        "timestamp": _utc_timestamp(),
        "checks": {
            "database": db_check,
            "redis": redis_check,
            "remnawave": remnawave_check,
        },
    }


def _normalize_check_result(result: dict[str, Any] | BaseException) -> dict[str, Any]:
    if isinstance(result, BaseException):
        return {"status": "error", "error": str(result)}
    return result
