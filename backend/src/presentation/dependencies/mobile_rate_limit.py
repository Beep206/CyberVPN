"""Rate limiting dependencies for mobile authentication endpoints (MED-004).

Provides endpoint-specific rate limiting:
- Login: 5 requests per minute per device_id
- Register: 3 requests per minute per IP

Security (MED-004):
- Fail-closed by default: Returns 503 if Redis unavailable
- Circuit breaker prevents hammering Redis when it's down
- Configurable via MOBILE_RATE_LIMIT_FAIL_OPEN env var

LOW-003:
- Uses asyncio.Lock for state management (non-blocking)
- Singleton instantiation still uses threading.Lock (sync __new__)
"""

import asyncio
import logging
import time
from threading import Lock
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


class MobileCircuitBreaker:
    """Circuit breaker for mobile auth Redis operations (MED-004).

    Shared instance across all rate limit checks.

    LOW-003: Uses asyncio.Lock for async-safe state management.
    The singleton _lock remains threading.Lock since __new__ is synchronous.
    """

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

    _instance: "MobileCircuitBreaker | None" = None
    _lock = Lock()  # Sync lock for singleton instantiation only

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init()
            return cls._instance

    def _init(self):
        self.failure_threshold = 3
        self.cooldown_seconds = 30.0
        self._failure_count = 0
        self._last_failure_time = 0.0
        self._state = self.CLOSED
        self._state_lock = asyncio.Lock()  # LOW-003: async lock for state management

    async def get_state(self) -> str:
        """Get current circuit state (async-safe, LOW-003)."""
        async with self._state_lock:
            if self._state == self.OPEN:
                if time.time() - self._last_failure_time >= self.cooldown_seconds:
                    self._state = self.HALF_OPEN
                    logger.info("Mobile rate limit circuit breaker transitioning to HALF_OPEN")
            return self._state

    async def is_open(self) -> bool:
        """Check if circuit is open (async-safe, LOW-003)."""
        return await self.get_state() == self.OPEN

    async def record_success(self) -> None:
        """Record successful operation (async-safe, LOW-003)."""
        async with self._state_lock:
            self._failure_count = 0
            if self._state != self.CLOSED:
                logger.info("Mobile rate limit circuit breaker reset to CLOSED")
                self._state = self.CLOSED

    async def record_failure(self) -> None:
        """Record failed operation (async-safe, LOW-003)."""
        async with self._state_lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            if self._failure_count >= self.failure_threshold:
                if self._state != self.OPEN:
                    logger.warning(
                        "Mobile rate limit circuit breaker OPEN after %d failures",
                        self._failure_count,
                    )
                self._state = self.OPEN


# Get fail-open setting from settings (MED-004)
def _get_fail_open() -> bool:
    """Get fail-open setting from config or environment."""
    return getattr(settings, "mobile_rate_limit_fail_open", False)


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


async def _check_rate_limit(key: str, limit: int) -> tuple[bool, bool]:
    """Check if rate limit is exceeded (MED-004, LOW-003).

    Args:
        key: Redis key for rate limit tracking.
        limit: Maximum requests allowed in window.

    Returns:
        Tuple of (allowed, redis_available).
        - allowed: True if request allowed, False if rate limited
        - redis_available: True if Redis responded, False on error
    """
    circuit = MobileCircuitBreaker()

    # Check circuit breaker first (LOW-003: async method)
    if await circuit.is_open():
        logger.warning("Mobile rate limit circuit breaker OPEN - Redis unavailable")
        return True, False  # Signal Redis unavailable

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

        # LOW-003: async record_success
        await circuit.record_success()
        return request_count <= limit, True

    except Exception as exc:
        # LOW-003: async record_failure
        await circuit.record_failure()
        logger.warning("Mobile auth rate limit check failed: %s", exc)
        return True, False  # Signal Redis unavailable

    finally:
        if client is not None:
            await client.aclose()


async def check_login_rate_limit(request: Request) -> None:
    """Rate limit login attempts by device_id (5/min) with fail-closed behavior (MED-004).

    Reads device_id from cached request body if available,
    falls back to IP-based limiting.

    Raises:
        HTTPException: 429 if rate limit exceeded.
        HTTPException: 503 if Redis unavailable and fail_open=False.
    """
    # Try to get device_id from request state (set by custom middleware or body parsing)
    device_id = getattr(request.state, "device_id", None)

    if device_id:
        key = f"cybervpn:mobile_auth:login:device:{device_id}"
    else:
        # Fallback to IP-based limiting
        client_ip = _get_client_ip(request)
        key = f"cybervpn:mobile_auth:login:ip:{client_ip}"

    allowed, redis_available = await _check_rate_limit(key, LOGIN_LIMIT)

    # MED-004: Fail-closed behavior when Redis unavailable
    if not redis_available and not _get_fail_open():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "SERVICE_UNAVAILABLE",
                "message": "Service temporarily unavailable. Please try again later.",
            },
            headers={"Retry-After": "30"},
        )

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
    """Rate limit registration attempts by IP (3/min) with fail-closed behavior (MED-004).

    Raises:
        HTTPException: 429 if rate limit exceeded.
        HTTPException: 503 if Redis unavailable and fail_open=False.
    """
    client_ip = _get_client_ip(request)
    key = f"cybervpn:mobile_auth:register:ip:{client_ip}"

    allowed, redis_available = await _check_rate_limit(key, REGISTER_LIMIT)

    # MED-004: Fail-closed behavior when Redis unavailable
    if not redis_available and not _get_fail_open():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "SERVICE_UNAVAILABLE",
                "message": "Service temporarily unavailable. Please try again later.",
            },
            headers={"Retry-After": "30"},
        )

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
