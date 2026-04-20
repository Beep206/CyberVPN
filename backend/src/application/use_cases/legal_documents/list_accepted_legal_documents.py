from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.accepted_legal_document_model import AcceptedLegalDocumentModel
from src.infrastructure.database.repositories.legal_document_repo import LegalDocumentRepository


class ListAcceptedLegalDocumentsUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = LegalDocumentRepository(session)

    async def execute(
        self,
        *,
        actor_principal_id: UUID | None = None,
        storefront_id: UUID | None = None,
        auth_realm_id: UUID | None = None,
        order_id: UUID | None = None,
        acceptance_channel: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AcceptedLegalDocumentModel]:
        return await self._repo.list_acceptances(
            actor_principal_id=actor_principal_id,
            storefront_id=storefront_id,
            auth_realm_id=auth_realm_id,
            order_id=order_id,
            acceptance_channel=acceptance_channel,
            limit=limit,
            offset=offset,
        )
