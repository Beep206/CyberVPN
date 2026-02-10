"""Security headers middleware (MED-2).

Implements security headers including CSP:
- Content-Security-Policy
- X-Content-Type-Options
- X-Frame-Options
- Strict-Transport-Security
- Referrer-Policy
- X-XSS-Protection
- Permissions-Policy
"""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from src.config.settings import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses (MED-2)."""

    # Content-Security-Policy for API backend
    # Restrictive policy since this is primarily an API server
    CSP_DIRECTIVES = {
        "default-src": "'self'",
        "script-src": "'self'",  # No inline scripts
        "style-src": "'self' 'unsafe-inline'",  # Allow inline styles for Swagger UI
        "img-src": "'self' data:",  # Allow data URIs for images
        "font-src": "'self'",
        "connect-src": "'self'",
        "frame-ancestors": "'none'",  # Prevent framing (clickjacking)
        "form-action": "'self'",
        "base-uri": "'self'",
        "object-src": "'none'",
    }

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)

        # Basic security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # SEC-009: HSTS - only in production environment (not just debug check)
        if settings.environment == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        # Content-Security-Policy
        csp_parts = [f"{key} {value}" for key, value in self.CSP_DIRECTIVES.items()]
        response.headers["Content-Security-Policy"] = "; ".join(csp_parts)

        # Permissions-Policy (replaces Feature-Policy)
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
            "magnetometer=(), microphone=(), payment=(), usb=()"
        )

        # Cache-Control for API responses
        if "Cache-Control" not in response.headers:
            response.headers["Cache-Control"] = "no-store, max-age=0"

        return response
