"""Logging middleware with URL sanitization (LOW-004).

Logs requests with sensitive data redacted.
"""

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware

from src.config.settings import settings
from src.shared.logging.sanitization import sanitize_url
from src.presentation.middleware.request_id import get_request_id

logger = logging.getLogger("cybervpn")


class LoggingMiddleware(BaseHTTPMiddleware):
    """HTTP request logging middleware with URL sanitization (LOW-004)."""

    async def dispatch(self, request, call_next):
        start = time.time()
        response = await call_next(request)
        duration_ms = (time.time() - start) * 1000

        # Get request ID for correlation (LOW-005)
        request_id = get_request_id() or "-"

        # Sanitize URL if enabled (LOW-004)
        url_path = request.url.path
        if request.url.query:
            full_url = f"{url_path}?{request.url.query}"
            if getattr(settings, "log_sanitization_enabled", True):
                full_url = sanitize_url(full_url)
            url_path = full_url

        logger.info(
            "%s %s %s %dms",
            request.method,
            url_path,
            response.status_code,
            duration_ms,
            extra={"request_id": request_id},
        )

        return response
