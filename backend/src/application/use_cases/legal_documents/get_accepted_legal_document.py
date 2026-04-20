from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.accepted_legal_document_model import AcceptedLegalDocumentModel
from src.infrastructure.database.repositories.legal_document_repo import LegalDocumentRepository


class GetAcceptedLegalDocumentUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = LegalDocumentRepository(session)

    async def execute(self, *, acceptance_id: UUID) -> AcceptedLegalDocumentModel | None:
        return await self._repo.get_acceptance_by_id(acceptance_id)
