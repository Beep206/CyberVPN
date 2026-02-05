"""Request ID middleware for request tracing (LOW-005).

Adds a unique request ID to each request for correlation in logs and responses.
"""

import logging
import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

# Context variable to store request ID across async calls
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

logger = logging.getLogger("cybervpn")


def get_request_id() -> str | None:
    """Get the current request ID from context.

    Use this function to access the request ID from anywhere in the code.
    Returns None if called outside of a request context.
    """
    return request_id_var.get()


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware that adds request ID to each request.

    - Generates UUID if not provided in X-Request-ID header
    - Stores request ID in context variable for logging
    - Returns request ID in X-Request-ID response header
    """

    HEADER_NAME = "X-Request-ID"

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        # Get request ID from header or generate new one
        request_id = request.headers.get(self.HEADER_NAME)

        if not request_id:
            request_id = str(uuid.uuid4())

        # Store in context variable for access in logs and handlers
        token = request_id_var.set(request_id)

        try:
            # Process request
            response = await call_next(request)

            # Add request ID to response headers
            response.headers[self.HEADER_NAME] = request_id

            return response

        finally:
            # Reset context variable
            request_id_var.reset(token)


class RequestIDFilter(logging.Filter):
    """Logging filter that adds request_id to log records.

    Usage:
        handler = logging.StreamHandler()
        handler.addFilter(RequestIDFilter())
        formatter = logging.Formatter('%(asctime)s [%(request_id)s] %(message)s')
        handler.setFormatter(formatter)
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id() or "-"
        return True
