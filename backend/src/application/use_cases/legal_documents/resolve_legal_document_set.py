from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.legal_document_set_model import LegalDocumentSetModel
from src.infrastructure.database.repositories.legal_document_repo import LegalDocumentRepository


class ResolveLegalDocumentSetUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = LegalDocumentRepository(session)

    async def execute(
        self,
        *,
        storefront_key: str,
        realm_key: str | None = None,
        at: datetime | None = None,
    ) -> LegalDocumentSetModel | None:
        return await self._repo.resolve_active_set(storefront_key=storefront_key, realm_key=realm_key, at=at)
