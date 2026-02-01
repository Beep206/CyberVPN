import time
import logging

from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("cybervpn")


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.time()
        response = await call_next(request)
        duration_ms = (time.time() - start) * 1000
        logger.info(f"{request.method} {request.url.path} {response.status_code} {duration_ms:.0f}ms")
        return response
