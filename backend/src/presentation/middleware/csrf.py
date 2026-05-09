"""CSRF guard for browser cookie-authenticated state-changing requests."""

from __future__ import annotations

from collections.abc import Collection
from urllib.parse import urlparse

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})
LEGACY_AUTH_COOKIES = frozenset({"access_token", "refresh_token"})
AUTH_COOKIE_SUFFIXES = ("_access_token", "_refresh_token")


def request_has_auth_cookie(cookies: dict[str, str]) -> bool:
    return any(name in LEGACY_AUTH_COOKIES or name.endswith(AUTH_COOKIE_SUFFIXES) for name in cookies)


def normalize_origin(value: str | None) -> str | None:
    if not value:
        return None

    stripped = value.strip()
    if not stripped or stripped.lower() == "null":
        return None

    parsed = urlparse(stripped)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None

    return f"{parsed.scheme}://{parsed.netloc}"


class CSRFMiddleware(BaseHTTPMiddleware):
    """Validate Origin/Referer for unsafe requests that rely on auth cookies."""

    def __init__(self, app, allowed_origins: Collection[str]) -> None:
        super().__init__(app)
        self.allowed_origins = frozenset(origin.rstrip("/") for origin in allowed_origins if origin and origin != "*")

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method.upper() in SAFE_METHODS:
            return await call_next(request)

        if request.headers.get("authorization"):
            return await call_next(request)

        if not request_has_auth_cookie(dict(request.cookies)):
            return await call_next(request)

        source_origin = normalize_origin(request.headers.get("origin")) or normalize_origin(
            request.headers.get("referer")
        )
        if source_origin not in self.allowed_origins:
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF origin validation failed"},
            )

        return await call_next(request)
