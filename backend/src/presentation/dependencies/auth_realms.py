"""Dependencies for resolving auth realms."""

from ipaddress import ip_address, ip_network

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.auth_realms import RealmResolution, ResolveRealmContextUseCase
from src.config.settings import S1_PRODUCTION_ADMIN_ALLOWED_HOSTS, S1_REDIRECT_ONLY_ADMIN_HOSTS, settings
from src.infrastructure.database.repositories.auth_realm_repo import AuthRealmRepository
from src.presentation.dependencies.database import get_db

PARTNER_AUTH_HOSTS = frozenset({"partner.cyber-vpn.net"})
PARTNER_LOCAL_AUTH_HOSTS = frozenset({"portal.localhost", "storefront.localhost"})
PUBLIC_CUSTOMER_CAPTURE_HOSTS = frozenset({"cyber-vpn.net", "www.cyber-vpn.net", "my.cyber-vpn.net"})
PUBLIC_CUSTOMER_LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1", "testserver"})
_LOOPBACK_TRUSTED_PROXY_IPS = ("127.0.0.1", "::1")


def _request_host(request: Request) -> str:
    raw_forwarded_host = request.headers.get("X-Forwarded-Host")
    raw_host = request.headers.get("Host")
    environment = settings.environment.strip().lower()
    if raw_forwarded_host and (environment != "production" or _request_from_trusted_proxy(request)):
        return _normalize_host(raw_forwarded_host) or ""
    return _normalize_host(raw_host) or ""


def _web_realm_hint_for_host(request: Request) -> str:
    host = _request_host(request)
    if host in S1_PRODUCTION_ADMIN_ALLOWED_HOSTS or host in S1_REDIRECT_ONLY_ADMIN_HOSTS:
        return "admin"
    if host in PARTNER_AUTH_HOSTS or host in PARTNER_LOCAL_AUTH_HOSTS:
        return "partner"
    return "customer"


async def get_request_auth_realm(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> RealmResolution:
    repo = AuthRealmRepository(db)
    use_case = ResolveRealmContextUseCase(repo)
    return await use_case.execute(request)


async def get_request_customer_realm(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> RealmResolution:
    repo = AuthRealmRepository(db)
    use_case = ResolveRealmContextUseCase(repo)
    return await use_case.execute(request, realm_type_hint="customer")


async def get_request_public_customer_realm(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> RealmResolution:
    """Resolve public partner-capture realms without trusting client realm headers."""

    host = _public_capture_host(request)
    if host is None:
        raise HTTPException(
            status_code=status.HTTP_421_MISDIRECTED_REQUEST,
            detail={
                "code": "PARTNER_ATTRIBUTION_HOST_NOT_TRUSTED",
                "message": "Partner attribution capture host is not trusted.",
            },
        )

    repo = AuthRealmRepository(db)
    realm = await repo.get_realm_by_storefront_host(host)
    if realm is not None:
        if realm.realm_type != "customer":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "PARTNER_ATTRIBUTION_HOST_NOT_FOUND",
                    "message": "Partner attribution capture host was not found.",
                },
            )
        return RealmResolution(auth_realm=realm, source="host", host=host)

    if _is_allowed_public_customer_host(host):
        default_realm = await repo.get_or_create_default_realm("customer")
        return RealmResolution(auth_realm=default_realm, source="public_host_default", host=host)

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "code": "PARTNER_ATTRIBUTION_HOST_NOT_FOUND",
            "message": "Partner attribution capture host was not found.",
        },
    )


async def get_request_admin_realm(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> RealmResolution:
    repo = AuthRealmRepository(db)
    use_case = ResolveRealmContextUseCase(repo)
    return await use_case.execute(request, realm_type_hint="admin")


async def get_request_web_auth_realm(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> RealmResolution:
    """Resolve web auth realm from trusted host boundary, not client headers."""

    repo = AuthRealmRepository(db)
    use_case = ResolveRealmContextUseCase(repo)
    return await use_case.execute(
        request,
        realm_type_hint=_web_realm_hint_for_host(request),
        allow_header=False,
    )


def _public_capture_host(request: Request) -> str | None:
    raw_forwarded_host = request.headers.get("X-Forwarded-Host")
    raw_host = request.headers.get("Host")
    environment = settings.environment.strip().lower()
    if raw_forwarded_host and (environment != "production" or _request_from_trusted_proxy(request)):
        return _normalize_host(raw_forwarded_host)
    return _normalize_host(raw_host)


def _normalize_host(raw_host: str | None) -> str | None:
    if not raw_host:
        return None
    host = raw_host.split(",", 1)[0].strip().lower()
    if host.startswith("http://") or host.startswith("https://"):
        host = host.split("://", 1)[1]
    if host.startswith("[") and "]" in host:
        return host[1 : host.index("]")]
    return host.split(":", 1)[0].strip() or None


def _is_allowed_public_customer_host(host: str) -> bool:
    if host in PUBLIC_CUSTOMER_CAPTURE_HOSTS:
        return True
    if settings.environment.strip().lower() == "production":
        return False
    return host in PUBLIC_CUSTOMER_LOCAL_HOSTS or host.endswith(".localhost") or host.endswith(".example.test")


def _request_from_trusted_proxy(request: Request) -> bool:
    direct_host = request.client.host if request.client else None
    if direct_host is None:
        return False
    trusted_entries = tuple(settings.trusted_proxy_ips or _LOOPBACK_TRUSTED_PROXY_IPS)
    try:
        peer = ip_address(direct_host)
    except ValueError:
        return direct_host == "testserver" and settings.environment.strip().lower() != "production"
    for trusted_entry in trusted_entries:
        try:
            if peer in ip_network(str(trusted_entry).strip(), strict=False):
                return True
        except ValueError:
            continue
    return False
