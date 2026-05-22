"""Rate limiting middleware with fail-closed behavior and circuit breaker (MED-1).

Security improvements:
- Fail-closed: If Redis is unavailable, reject requests (503)
- Circuit breaker: After consecutive failures, stop trying Redis temporarily
- Configurable fail-open mode for development
- Audit logging for rate limit events
"""

import logging
import time
from dataclasses import dataclass, field
from threading import Lock

import redis.asyncio as redis
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from src.config.settings import settings
from src.infrastructure.cache.redis_client import get_redis_pool

logger = logging.getLogger("cybervpn")


@dataclass(frozen=True)
class RateLimitRule:
    """Route-category rate-limit policy for launch-critical S1 surfaces."""

    name: str
    limit: int
    methods: frozenset[str] = field(default_factory=frozenset)
    exact_paths: frozenset[str] = field(default_factory=frozenset)
    path_prefixes: tuple[str, ...] = ()
    path_suffixes: tuple[str, ...] = ()

    def matches(self, request: Request) -> bool:
        method = request.method.upper()
        path = request.url.path
        if self.methods and method not in self.methods:
            return False
        return (
            path in self.exact_paths
            or any(path.startswith(prefix) for prefix in self.path_prefixes)
            or any(path.endswith(suffix) for suffix in self.path_suffixes)
        )


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
    _EXEMPT_PATHS = {
        "/health",
        "/health/",
        "/readiness",
        "/readiness/",
        "/api/v1/auth/me",
        "/api/v1/auth/me/",
        "/api/v1/auth/session",
        "/api/v1/auth/session/",
    }
    _HELIX_ADMIN_READ_PREFIX = "/api/v1/helix/admin/"

    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        window_seconds: int | None = None,
        fail_open: bool | None = None,
        circuit_failure_threshold: int = 3,
        circuit_cooldown_seconds: float = 30.0,
        auth_sensitive_requests_per_minute: int | None = None,
        payment_write_requests_per_minute: int | None = None,
        trial_activate_requests_per_minute: int | None = None,
        growth_sensitive_requests_per_minute: int | None = None,
        support_write_requests_per_minute: int | None = None,
    ) -> None:
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.window = self._configured_limit(
            explicit=window_seconds,
            setting_name="rate_limit_window",
            default=60,
        )
        self.helix_admin_read_requests_per_minute = max(
            self._configured_limit(
                explicit=None,
                setting_name="helix_admin_read_rate_limit_requests",
                default=requests_per_minute,
            ),
            self.requests_per_minute,
        )
        self._s1_rules = self._build_s1_rules(
            auth_sensitive_requests_per_minute=auth_sensitive_requests_per_minute,
            payment_write_requests_per_minute=payment_write_requests_per_minute,
            trial_activate_requests_per_minute=trial_activate_requests_per_minute,
            growth_sensitive_requests_per_minute=growth_sensitive_requests_per_minute,
            support_write_requests_per_minute=support_write_requests_per_minute,
        )
        # Default to fail-closed in production, configurable via settings
        if fail_open is None:
            configured_fail_open = getattr(settings, "rate_limit_fail_open", False)
            # Development/staging should fail-open by default to avoid auth lockouts
            # during transient Redis issues. Production remains fail-closed unless
            # explicitly overridden.
            self.fail_open = configured_fail_open or settings.environment != "production"
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
        if request.url.path in self._EXEMPT_PATHS:
            return await call_next(request)

        client_ip = self._get_client_ip(request)
        key = f"cybervpn:rate_limit:{client_ip}:{self._rate_limit_bucket_for(request)}"
        request_budget = self._requests_budget_for(request)

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

            if request_count > request_budget:
                logger.warning(
                    "Rate limit exceeded",
                    extra={
                        "client_ip": client_ip,
                        "path": request.url.path,
                        "count": request_count,
                        "limit": request_budget,
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

    def _requests_budget_for(self, request: Request) -> int:
        rule = self._rule_for(request)
        if rule is not None:
            return rule.limit

        if request.method.upper() == "GET" and request.url.path.startswith(self._HELIX_ADMIN_READ_PREFIX):
            return self.helix_admin_read_requests_per_minute

        return self.requests_per_minute

    def _rate_limit_bucket_for(self, request: Request) -> str:
        rule = self._rule_for(request)
        if rule is not None:
            return rule.name
        return request.url.path

    def _rule_for(self, request: Request) -> RateLimitRule | None:
        return next((rule for rule in self._s1_rules if rule.matches(request)), None)

    @staticmethod
    def _configured_limit(*, explicit: int | None, setting_name: str, default: int) -> int:
        value = explicit
        if value is None:
            configured = getattr(settings, setting_name, default)
            value = configured if isinstance(configured, int) else default
        return max(1, int(value))

    def _build_s1_rules(
        self,
        *,
        auth_sensitive_requests_per_minute: int | None,
        payment_write_requests_per_minute: int | None,
        trial_activate_requests_per_minute: int | None,
        growth_sensitive_requests_per_minute: int | None,
        support_write_requests_per_minute: int | None,
    ) -> tuple[RateLimitRule, ...]:
        auth_limit = self._configured_limit(
            explicit=auth_sensitive_requests_per_minute,
            setting_name="rate_limit_auth_sensitive_requests",
            default=20,
        )
        payment_limit = self._configured_limit(
            explicit=payment_write_requests_per_minute,
            setting_name="rate_limit_payment_write_requests",
            default=30,
        )
        trial_limit = self._configured_limit(
            explicit=trial_activate_requests_per_minute,
            setting_name="rate_limit_trial_activate_requests",
            default=10,
        )
        growth_limit = self._configured_limit(
            explicit=growth_sensitive_requests_per_minute,
            setting_name="rate_limit_growth_sensitive_requests",
            default=60,
        )
        support_limit = self._configured_limit(
            explicit=support_write_requests_per_minute,
            setting_name="rate_limit_support_write_requests",
            default=30,
        )

        return (
            RateLimitRule(
                name="s1_auth_sensitive",
                limit=auth_limit,
                methods=frozenset({"POST", "DELETE"}),
                exact_paths=frozenset(
                    {
                        "/api/v1/auth/login",
                        "/api/v1/auth/register",
                        "/api/v1/auth/refresh",
                        "/api/v1/auth/logout",
                        "/api/v1/auth/resend-otp",
                        "/api/v1/auth/resend-verification",
                        "/api/v1/auth/magic-link",
                        "/api/v1/auth/magic-link/verify",
                        "/api/v1/auth/magic-link/verify-otp",
                        "/api/v1/auth/telegram/miniapp",
                        "/api/v1/auth/telegram/web",
                        "/api/v1/auth/telegram/bot-link",
                        "/api/v1/auth/telegram/generate-login-link",
                        "/api/v1/mobile/auth/register",
                        "/api/v1/mobile/auth/login",
                        "/api/v1/mobile/auth/refresh",
                        "/api/v1/mobile/auth/logout",
                        "/api/v1/mobile/auth/2fa/complete",
                        "/api/v1/mobile/auth/telegram/callback",
                        "/api/v1/mobile/auth/telegram/oidc",
                        "/api/v1/oauth/telegram/callback",
                        "/api/v1/oauth/telegram/magic-link/complete",
                        "/api/v1/oauth/github/callback",
                        "/api/v1/oauth/facebook/callback",
                    }
                ),
                path_prefixes=("/api/v1/oauth/",),
            ),
            RateLimitRule(
                name="s1_payment_write",
                limit=payment_limit,
                methods=frozenset({"POST"}),
                exact_paths=frozenset(
                    {
                        "/api/v1/payments/crypto/invoice",
                        "/api/v1/payments/checkout/quote",
                        "/api/v1/payments/checkout/commit",
                        "/api/v1/payments/checkout/telegram-stars",
                        "/api/v1/payments/checkout",
                        "/api/v1/payments/create",
                        "/api/v1/miniapp/checkout/quote",
                        "/api/v1/miniapp/checkout/commit",
                        "/api/v1/checkout-sessions",
                        "/api/v1/checkout-sessions/",
                        "/api/v1/payment-attempts",
                        "/api/v1/payment-attempts/",
                        "/api/v1/telegram/payments/stars",
                    }
                ),
                path_prefixes=("/api/v1/telegram/payments/",),
                path_suffixes=("/checkout/quote", "/checkout/commit"),
            ),
            RateLimitRule(
                name="s1_trial_activate",
                limit=trial_limit,
                methods=frozenset({"POST"}),
                exact_paths=frozenset(
                    {
                        "/api/v1/trial/activate",
                        "/api/v1/miniapp/trial/activate",
                        "/api/v1/telegram/trial/activate",
                    }
                ),
                path_suffixes=("/trial/activate",),
            ),
            RateLimitRule(
                name="s1_growth_sensitive",
                limit=growth_limit,
                methods=frozenset({"GET", "POST"}),
                exact_paths=frozenset(
                    {
                        "/api/v1/promo/validate",
                        "/api/v1/invites/redeem",
                        "/api/v1/gifts/purchase/quote",
                        "/api/v1/gifts/purchase/commit",
                        "/api/v1/gifts/redeem",
                    }
                ),
                path_prefixes=("/api/v1/referral/", "/api/v1/growth-rewards/"),
            ),
            RateLimitRule(
                name="s1_support_write",
                limit=support_limit,
                methods=frozenset({"POST", "PUT", "PATCH", "DELETE"}),
                path_prefixes=(
                    "/api/v1/admin/mobile-users/",
                    "/api/v1/admin/customer-operations/",
                ),
            ),
        )

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
