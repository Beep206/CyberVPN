"""Dependencies for resolving auth realms."""

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.auth_realms import RealmResolution, ResolveRealmContextUseCase
from src.config.settings import S1_PRODUCTION_ADMIN_ALLOWED_HOSTS, S1_REDIRECT_ONLY_ADMIN_HOSTS
from src.infrastructure.database.repositories.auth_realm_repo import AuthRealmRepository
from src.presentation.dependencies.database import get_db

PARTNER_AUTH_HOSTS = frozenset({"partner.cyber-vpn.net"})


def _request_host(request: Request) -> str:
    raw_host = request.headers.get("X-Forwarded-Host") or request.headers.get("Host") or ""
    return raw_host.split(",", 1)[0].split(":", 1)[0].strip().lower()


def _web_realm_hint_for_host(request: Request) -> str:
    host = _request_host(request)
    if host in S1_PRODUCTION_ADMIN_ALLOWED_HOSTS or host in S1_REDIRECT_ONLY_ADMIN_HOSTS:
        return "admin"
    if host in PARTNER_AUTH_HOSTS:
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
