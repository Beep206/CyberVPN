from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.legal_documents import (
    CreateLegalDocumentSetUseCase,
    CreateLegalDocumentUseCase,
    ListLegalDocumentsUseCase,
    ResolveLegalDocumentSetUseCase,
)
from src.domain.enums import AdminRole
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.presentation.dependencies.auth_realms import RealmResolution, get_request_auth_realm
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_role

from .schemas import (
    CreateLegalDocumentRequest,
    CreateLegalDocumentSetRequest,
    LegalDocumentResponse,
    LegalDocumentSetResponse,
)

router = APIRouter(prefix="/legal-documents", tags=["legal-documents"])


@router.get("/", response_model=list[LegalDocumentResponse])
async def list_legal_documents(
    document_type: str | None = Query(None),
    locale: str | None = Query(None),
    _current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> list[LegalDocumentResponse]:
    use_case = ListLegalDocumentsUseCase(db)
    return await use_case.execute(document_type=document_type, locale=locale)


@router.post("/", response_model=LegalDocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_legal_document(
    payload: CreateLegalDocumentRequest,
    _current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> LegalDocumentResponse:
    use_case = CreateLegalDocumentUseCase(db)
    try:
        return await use_case.execute(**payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/sets", response_model=LegalDocumentSetResponse, status_code=status.HTTP_201_CREATED)
async def create_legal_document_set(
    payload: CreateLegalDocumentSetRequest,
    _current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> LegalDocumentSetResponse:
    use_case = CreateLegalDocumentSetUseCase(db)
    try:
        return await use_case.execute(**payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/sets/resolve", response_model=LegalDocumentSetResponse)
async def resolve_legal_document_set(
    storefront_key: str = Query(..., min_length=1),
    at: datetime | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_realm: RealmResolution = Depends(get_request_auth_realm),
) -> LegalDocumentSetResponse:
    use_case = ResolveLegalDocumentSetUseCase(db)
    resolved = await use_case.execute(storefront_key=storefront_key, realm_key=current_realm.realm_key, at=at)
    if resolved is None:
        resolved = await use_case.execute(storefront_key=storefront_key, at=at)
    if resolved is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Legal document set not found")
    return resolved
