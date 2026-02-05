"""Rate limiting middleware with fail-closed behavior and circuit breaker (MED-1).

Security improvements:
- Fail-closed: If Redis is unavailable, reject requests (503)
- Circuit breaker: After consecutive failures, stop trying Redis temporarily
- Configurable fail-open mode for development
- Audit logging for rate limit events
"""

import logging
import time
from threading import Lock

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

import redis.asyncio as redis

from src.config.settings import settings
from src.infrastructure.cache.redis_client import get_redis_pool

logger = logging.getLogger("cybervpn")


class CircuitBreaker:
    """Circuit breaker for Redis connection failures.

    States:
    - CLOSED: Normal operation, requests go through
    - OPEN: Too many failures, reject immediately without trying Redis
    - HALF_OPEN: After cooldown, allow one request to test if Redis recovered
    """

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

    def __init__(
        self,
        failure_threshold: int = 3,
        cooldown_seconds: float = 30.0,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self._failure_count = 0
        self._last_failure_time: float = 0.0
        self._state = self.CLOSED
        self._lock = Lock()

    @property
    def state(self) -> str:
        """Get current circuit state, transitioning from OPEN to HALF_OPEN if cooldown elapsed."""
        with self._lock:
            if self._state == self.OPEN:
                if time.time() - self._last_failure_time >= self.cooldown_seconds:
                    self._state = self.HALF_OPEN
                    logger.info("Circuit breaker transitioning to HALF_OPEN")
            return self._state

    def is_open(self) -> bool:
        """Check if circuit is open (should reject without trying)."""
        return self.state == self.OPEN

    def record_success(self) -> None:
        """Record a successful operation - reset the circuit."""
        with self._lock:
            self._failure_count = 0
            if self._state != self.CLOSED:
                logger.info("Circuit breaker reset to CLOSED after success")
                self._state = self.CLOSED

    def record_failure(self) -> None:
        """Record a failed operation - may trip the circuit."""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()

            if self._failure_count >= self.failure_threshold:
                if self._state != self.OPEN:
                    logger.warning(
                        "Circuit breaker OPEN after %d consecutive failures",
                        self._failure_count,
                    )
                self._state = self.OPEN


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware with fail-closed behavior and circuit breaker (MED-1).

    When Redis is unavailable:
    - Production (RATE_LIMIT_FAIL_OPEN=false): Returns 503 Service Unavailable
    - Development (RATE_LIMIT_FAIL_OPEN=true): Allows requests through

    Circuit breaker prevents hammering Redis when it's down:
    - After 3 consecutive failures, circuit opens for 30 seconds
    - During open state, requests are rejected immediately (503)
    - After cooldown, one test request is allowed (half-open state)
    """

    # Shared circuit breaker across all middleware instances
    _circuit_breaker: CircuitBreaker | None = None
    _circuit_lock = Lock()

    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        fail_open: bool | None = None,
        circuit_failure_threshold: int = 3,
        circuit_cooldown_seconds: float = 30.0,
    ) -> None:
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.window = 60
        # Default to fail-closed in production, configurable via settings
        if fail_open is None:
            self.fail_open = getattr(settings, "rate_limit_fail_open", False)
        else:
            self.fail_open = fail_open

        # Initialize shared circuit breaker
        with self._circuit_lock:
            if RateLimitMiddleware._circuit_breaker is None:
                RateLimitMiddleware._circuit_breaker = CircuitBreaker(
                    failure_threshold=circuit_failure_threshold,
                    cooldown_seconds=circuit_cooldown_seconds,
                )
        self.circuit = RateLimitMiddleware._circuit_breaker

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        client_ip = self._get_client_ip(request)
        key = f"cybervpn:rate_limit:{client_ip}:{request.url.path}"

        # Check circuit breaker first
        if self.circuit.is_open():
            logger.warning(
                "Rate limiter circuit breaker OPEN - rejecting request",
                extra={"client_ip": client_ip, "path": request.url.path},
            )
            if not self.fail_open:
                return JSONResponse(
                    status_code=503,
                    content={"detail": "Service temporarily unavailable"},
                    headers={"Retry-After": "30"},
                )
            # In fail-open mode, skip rate limiting when circuit is open
            return await call_next(request)

        pool = None
        client = None
        try:
            pool = get_redis_pool()
            client = redis.Redis(connection_pool=pool)
            now = time.time()

            async with client.pipeline(transaction=True) as pipe:
                pipe.zremrangebyscore(key, 0, now - self.window)
                pipe.zadd(key, {str(now): now})
                pipe.zcard(key)
                pipe.expire(key, self.window)
                results = await pipe.execute()

            request_count = results[2]

            # Redis operation succeeded - reset circuit breaker
            self.circuit.record_success()

            if request_count > self.requests_per_minute:
                logger.warning(
                    "Rate limit exceeded",
                    extra={
                        "client_ip": client_ip,
                        "path": request.url.path,
                        "count": request_count,
                        "limit": self.requests_per_minute,
                    },
                )
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests"},
                    headers={"Retry-After": str(self.window)},
                )

        except redis.RedisError as exc:
            # MED-1: Fail-closed behavior when Redis unavailable
            self.circuit.record_failure()
            logger.error(
                "Rate limiter Redis error - failing %s (circuit: %s)",
                "open (dev mode)" if self.fail_open else "closed",
                self.circuit.state,
                extra={"error": str(exc), "client_ip": client_ip},
            )

            if not self.fail_open:
                # Production: fail-closed - reject request
                return JSONResponse(
                    status_code=503,
                    content={"detail": "Service temporarily unavailable"},
                    headers={"Retry-After": "30"},
                )
            # Development: fail-open - allow request through

        except Exception as exc:
            # Unexpected error - always fail-closed
            self.circuit.record_failure()
            logger.exception(
                "Rate limiter unexpected error",
                extra={"error": str(exc), "client_ip": client_ip},
            )
            return JSONResponse(
                status_code=503,
                content={"detail": "Service temporarily unavailable"},
                headers={"Retry-After": "30"},
            )

        finally:
            if client is not None:
                await client.aclose()

        return await call_next(request)

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address with trusted proxy validation (MED-8).

        Only accepts X-Forwarded-For from trusted proxies.
        """
        direct_ip = request.client.host if request.client else "unknown"

        if not settings.trust_proxy_headers:
            return direct_ip

        # MED-8: Validate request comes from trusted proxy
        trusted_proxies = set(settings.trusted_proxy_ips) if settings.trusted_proxy_ips else set()

        # If trusted_proxy_ips is configured, validate direct connection is from trusted proxy
        if trusted_proxies and direct_ip not in trusted_proxies:
            # Direct connection not from trusted proxy - use direct IP
            logger.warning(
                "X-Forwarded-For from untrusted source ignored",
                extra={"direct_ip": direct_ip, "trusted_proxies": list(trusted_proxies)[:5]},
            )
            return direct_ip

        # Accept X-Forwarded-For from trusted proxy
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()

        return direct_ip
