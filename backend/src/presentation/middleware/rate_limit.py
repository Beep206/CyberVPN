import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

import redis.asyncio as redis

from src.infrastructure.cache.redis_client import get_redis_pool


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests_per_minute: int = 60) -> None:
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.window = 60

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        key = f"cybervpn:rate_limit:{client_ip}:{request.url.path}"

        try:
            pool = get_redis_pool()
            r = redis.Redis(connection_pool=pool)
            now = time.time()

            pipe = r.pipeline()
            pipe.zremrangebyscore(key, 0, now - self.window)
            pipe.zadd(key, {str(now): now})
            pipe.zcard(key)
            pipe.expire(key, self.window)
            results = await pipe.execute()
            request_count = results[2]

            if request_count > self.requests_per_minute:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests"},
                    headers={"Retry-After": str(self.window)},
                )
            await r.aclose()
        except Exception:
            pass

        return await call_next(request)
