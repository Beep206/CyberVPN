from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.legal_documents import (
    CreateAcceptedLegalDocumentUseCase,
    GetAcceptedLegalDocumentUseCase,
    ListAcceptedLegalDocumentsUseCase,
)
from src.domain.enums import AdminRole
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.presentation.dependencies.auth import CurrentPrincipalActor, get_current_principal_actor
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_role

from .schemas import (
    AcceptedLegalDocumentResponse,
    CreateAcceptedLegalDocumentRequest,
)

router = APIRouter(prefix="/policy-acceptance", tags=["policy-acceptance"])


@router.post("/", response_model=AcceptedLegalDocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_policy_acceptance(
    payload: CreateAcceptedLegalDocumentRequest,
    request: Request,
    current_actor: CurrentPrincipalActor = Depends(get_current_principal_actor),
    db: AsyncSession = Depends(get_db),
) -> AcceptedLegalDocumentResponse:
    use_case = CreateAcceptedLegalDocumentUseCase(db)
    try:
        return await use_case.execute(
            **payload.model_dump(),
            auth_realm_id=current_actor.auth_realm_id,
            actor_principal_id=current_actor.principal_id,
            actor_principal_type=current_actor.principal_type,
            source_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/me", response_model=list[AcceptedLegalDocumentResponse])
async def list_my_policy_acceptance(
    current_actor: CurrentPrincipalActor = Depends(get_current_principal_actor),
    db: AsyncSession = Depends(get_db),
) -> list[AcceptedLegalDocumentResponse]:
    use_case = ListAcceptedLegalDocumentsUseCase(db)
    return await use_case.execute(actor_principal_id=current_actor.principal_id)


@router.get("/", response_model=list[AcceptedLegalDocumentResponse])
async def list_policy_acceptance(
    actor_principal_id: UUID | None = Query(None),
    storefront_id: UUID | None = Query(None),
    auth_realm_id: UUID | None = Query(None),
    order_id: UUID | None = Query(None),
    acceptance_channel: str | None = Query(None, max_length=50),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    _current_user: AdminUserModel = Depends(require_role(AdminRole.SUPPORT)),
    db: AsyncSession = Depends(get_db),
) -> list[AcceptedLegalDocumentResponse]:
    use_case = ListAcceptedLegalDocumentsUseCase(db)
    return await use_case.execute(
        actor_principal_id=actor_principal_id,
        storefront_id=storefront_id,
        auth_realm_id=auth_realm_id,
        order_id=order_id,
        acceptance_channel=acceptance_channel,
        limit=limit,
        offset=offset,
    )


@router.get("/{acceptance_id}", response_model=AcceptedLegalDocumentResponse)
async def get_policy_acceptance(
    acceptance_id: UUID,
    _current_user: AdminUserModel = Depends(require_role(AdminRole.SUPPORT)),
    db: AsyncSession = Depends(get_db),
) -> AcceptedLegalDocumentResponse:
    item = await GetAcceptedLegalDocumentUseCase(db).execute(acceptance_id=acceptance_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy acceptance not found")
    return item
