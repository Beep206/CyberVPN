from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.legal_document_model import LegalDocumentModel
from src.infrastructure.database.repositories.legal_document_repo import LegalDocumentRepository


class ListLegalDocumentsUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = LegalDocumentRepository(session)

    async def execute(
        self,
        *,
        document_type: str | None = None,
        locale: str | None = None,
    ) -> list[LegalDocumentModel]:
        return await self._repo.list_documents(document_type=document_type, locale=locale)
