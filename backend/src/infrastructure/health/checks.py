import asyncio
import logging
from typing import Any

import httpx
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("cybervpn")


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
        await redis_client.ping()

        # Get info
        info = await redis_client.info()

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
    db_check, redis_check, remnawave_check = await asyncio.gather(
        check_database(db_session), check_redis(redis_client), check_remnawave(remnawave_url), return_exceptions=True
    )

    # Determine overall status
    checks = [db_check, redis_check, remnawave_check]
    unhealthy = any(isinstance(c, Exception) or c.get("status") == "unhealthy" for c in checks)
    degraded = any(c.get("status") == "degraded" for c in checks if not isinstance(c, Exception))

    if unhealthy:
        overall_status = "unhealthy"
    elif degraded:
        overall_status = "degraded"
    else:
        overall_status = "healthy"

    return {
        "status": overall_status,
        "timestamp": asyncio.get_event_loop().time(),
        "checks": {
            "database": (
                db_check if not isinstance(db_check, Exception) else {"status": "error", "error": str(db_check)}
            ),
            "redis": (
                redis_check
                if not isinstance(redis_check, Exception)
                else {"status": "error", "error": str(redis_check)}
            ),
            "remnawave": (
                remnawave_check
                if not isinstance(remnawave_check, Exception)
                else {"status": "error", "error": str(remnawave_check)}
            ),
        },
    }
