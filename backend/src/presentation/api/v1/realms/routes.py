from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import AdminRole
from src.infrastructure.database.repositories.auth_realm_repo import AuthRealmRepository
from src.presentation.api.v1.realms.schemas import RealmResolutionResponse, RealmResponse
from src.presentation.dependencies import require_role
from src.presentation.dependencies.auth_realms import get_request_auth_realm
from src.presentation.dependencies.database import get_db

router = APIRouter(prefix="/realms", tags=["realms"])


@router.get("/resolve", response_model=RealmResolutionResponse)
async def resolve_realm_context(
    resolution=Depends(get_request_auth_realm),
) -> RealmResolutionResponse:
    return RealmResolutionResponse(
        realm=RealmResponse.model_validate(resolution.auth_realm),
        source=resolution.source,
        host=resolution.host,
    )


@router.get("/", response_model=list[RealmResponse])
async def list_realms(
    _current_user=Depends(require_role(AdminRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> list[RealmResponse]:
    repo = AuthRealmRepository(db)
    realms = await repo.list_realms()
    return [RealmResponse.model_validate(realm) for realm in realms]
