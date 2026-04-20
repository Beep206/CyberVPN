"""Dependencies for resolving auth realms."""

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.auth_realms import RealmResolution, ResolveRealmContextUseCase
from src.infrastructure.database.repositories.auth_realm_repo import AuthRealmRepository
from src.presentation.dependencies.database import get_db


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
