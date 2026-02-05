"""Rate limiting middleware with fail-closed behavior (MED-1).

Security improvements:
- Fail-closed: If Redis is unavailable, reject requests (503)
- Configurable fail-open mode for development
- Audit logging for rate limit events
"""

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

import redis.asyncio as redis

from src.config.settings import settings
from src.infrastructure.cache.redis_client import get_redis_pool

logger = logging.getLogger("cybervpn")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware with fail-closed behavior (MED-1).

    When Redis is unavailable:
    - Production (RATE_LIMIT_FAIL_OPEN=false): Returns 503 Service Unavailable
    - Development (RATE_LIMIT_FAIL_OPEN=true): Allows requests through
    """

    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        fail_open: bool | None = None,
    ) -> None:
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.window = 60
        # Default to fail-closed in production, configurable via settings
        if fail_open is None:
            self.fail_open = getattr(settings, "rate_limit_fail_open", False)
        else:
            self.fail_open = fail_open

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        client_ip = self._get_client_ip(request)
        key = f"cybervpn:rate_limit:{client_ip}:{request.url.path}"

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
            logger.error(
                "Rate limiter Redis error - failing %s",
                "open (dev mode)" if self.fail_open else "closed",
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
