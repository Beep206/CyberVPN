"""Host boundary guard for S1 admin API surfaces."""

from __future__ import annotations

from collections.abc import Collection
from urllib.parse import urlparse

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from src.presentation.dependencies.client_ip import LOOPBACK_TRUSTED_PROXY_IPS, is_trusted_proxy_peer

ADMIN_PROTECTED_PATH_PREFIXES = ("/api/v1/admin",)
ADMIN_INTERNAL_EXEMPT_PATH_PREFIXES = ("/api/v1/admin/growth-reporting/internal/",)
TASK2_ROUTE_EVIDENCE_EXEMPT_PATH = "/api/v1/admin/vpn-tester/internal/task2/route-evidence/xray-routing-webhook"
TASK2_ROUTE_EVIDENCE_HOST = "task2-evidence.cyber-vpn.org"
LOCAL_DEVELOPMENT_ADMIN_HOSTS = frozenset({"localhost", "127.0.0.1", "::1", "testserver", "backend"})


def normalize_host(value: str | None) -> str:
    if not value:
        return ""

    host = value.split(",", 1)[0].strip().lower()
    if not host:
        return ""

    if "://" in host:
        parsed = urlparse(host)
        host = parsed.netloc or parsed.path

    if host.startswith("["):
        end = host.find("]")
        if end != -1:
            return host[1:end]

    return host.split(":", 1)[0]


def is_admin_host_protected_path(path: str) -> bool:
    if any(path.startswith(prefix) for prefix in ADMIN_INTERNAL_EXEMPT_PATH_PREFIXES):
        return False

    return any(path == prefix or path.startswith(f"{prefix}/") for prefix in ADMIN_PROTECTED_PATH_PREFIXES)


class AdminHostGuardMiddleware(BaseHTTPMiddleware):
    """Hide interactive admin API routes when the request is not on an admin host."""

    def __init__(
        self,
        app,
        *,
        allowed_hosts: Collection[str],
        environment: str,
        trust_proxy_headers: bool = False,
        trusted_proxy_ips: Collection[str] | None = None,
    ) -> None:
        super().__init__(app)
        self.environment = environment.lower()
        self.trust_proxy_headers = trust_proxy_headers
        self.trusted_proxy_ips = tuple(trusted_proxy_ips or LOOPBACK_TRUSTED_PROXY_IPS)
        self.allowed_hosts = frozenset(normalize_host(host) for host in allowed_hosts if normalize_host(host))
        if self.environment != "production":
            self.allowed_hosts = self.allowed_hosts | LOCAL_DEVELOPMENT_ADMIN_HOSTS

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not is_admin_host_protected_path(request.url.path):
            return await call_next(request)

        candidate_host = request.headers.get("x-forwarded-host") if self._can_trust_forwarded_host(request) else None
        request_host = normalize_host(candidate_host or request.headers.get("host"))

        if request.url.path == TASK2_ROUTE_EVIDENCE_EXEMPT_PATH and request_host == TASK2_ROUTE_EVIDENCE_HOST:
            return await call_next(request)

        if request_host not in self.allowed_hosts:
            return JSONResponse(status_code=404, content={"detail": "Not found"})

        return await call_next(request)

    def _can_trust_forwarded_host(self, request: Request) -> bool:
        if not self.trust_proxy_headers:
            return False
        direct_host = request.client.host if request.client else None
        return is_trusted_proxy_peer(direct_host, self.trusted_proxy_ips)
