"""Rate limiting dependencies for mobile authentication endpoints.

Provides endpoint-specific rate limiting:
- Login: 5 requests per minute per device_id
- Register: 3 requests per minute per IP
"""

import logging
import time
from typing import Annotated

import redis.asyncio as redis
from fastapi import Depends, HTTPException, Request, status

from src.config.settings import settings
from src.infrastructure.cache.redis_client import get_redis_pool

logger = logging.getLogger("cybervpn")

# Rate limit configurations
LOGIN_LIMIT = 5  # requests per minute
REGISTER_LIMIT = 3  # requests per minute
WINDOW_SECONDS = 60


def _get_client_ip(request: Request) -> str:
    """Extract client IP from request, respecting proxy headers if configured."""
    if settings.trust_proxy_headers:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()

    if request.client:
        return request.client.host

    return "unknown"


async def _check_rate_limit(key: str, limit: int) -> bool:
    """Check if rate limit is exceeded.

    Args:
        key: Redis key for rate limit tracking.
        limit: Maximum requests allowed in window.

    Returns:
        True if request allowed, False if rate limited.
    """
    pool = None
    client = None
    try:
        pool = get_redis_pool()
        client = redis.Redis(connection_pool=pool)
        now = time.time()

        pipe = client.pipeline()
        pipe.zremrangebyscore(key, 0, now - WINDOW_SECONDS)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, WINDOW_SECONDS)
        results = await pipe.execute()
        request_count = results[2]

        return request_count <= limit

    except Exception as exc:
        logger.warning("Mobile auth rate limit check failed: %s", exc)
        return True  # Allow on error to avoid blocking users

    finally:
        if client is not None:
            await client.aclose()


async def check_login_rate_limit(request: Request) -> None:
    """Rate limit login attempts by device_id (5/min).

    Reads device_id from cached request body if available,
    falls back to IP-based limiting.

    Raises:
        HTTPException: 429 if rate limit exceeded.
    """
    # Try to get device_id from request state (set by custom middleware or body parsing)
    device_id = getattr(request.state, "device_id", None)

    if device_id:
        key = f"cybervpn:mobile_auth:login:device:{device_id}"
    else:
        # Fallback to IP-based limiting
        client_ip = _get_client_ip(request)
        key = f"cybervpn:mobile_auth:login:ip:{client_ip}"

    allowed = await _check_rate_limit(key, LOGIN_LIMIT)

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "RATE_LIMITED",
                "message": "Too many login attempts. Please try again later.",
            },
            headers={"Retry-After": str(WINDOW_SECONDS)},
        )


async def check_register_rate_limit(request: Request) -> None:
    """Rate limit registration attempts by IP (3/min).

    Raises:
        HTTPException: 429 if rate limit exceeded.
    """
    client_ip = _get_client_ip(request)
    key = f"cybervpn:mobile_auth:register:ip:{client_ip}"

    allowed = await _check_rate_limit(key, REGISTER_LIMIT)

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "RATE_LIMITED",
                "message": "Too many registration attempts. Please try again later.",
            },
            headers={"Retry-After": str(WINDOW_SECONDS)},
        )


# Type aliases for FastAPI Depends
LoginRateLimit = Annotated[None, Depends(check_login_rate_limit)]
RegisterRateLimit = Annotated[None, Depends(check_register_rate_limit)]
