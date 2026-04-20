from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.accepted_legal_document_model import AcceptedLegalDocumentModel
from src.infrastructure.database.repositories.auth_realm_repo import AuthRealmRepository
from src.infrastructure.database.repositories.legal_document_repo import LegalDocumentRepository
from src.infrastructure.database.repositories.storefront_repo import StorefrontRepository


class CreateAcceptedLegalDocumentUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = LegalDocumentRepository(session)
        self._realm_repo = AuthRealmRepository(session)
        self._storefront_repo = StorefrontRepository(session)

    async def execute(
        self,
        *,
        legal_document_id: UUID | None,
        legal_document_set_id: UUID | None,
        storefront_id: UUID,
        auth_realm_id: UUID,
        actor_principal_id: UUID,
        actor_principal_type: str,
        acceptance_channel: str,
        quote_session_id: UUID | None,
        checkout_session_id: UUID | None,
        order_id: UUID | None,
        source_ip: str | None,
        user_agent: str | None,
        device_context: dict | None,
    ) -> AcceptedLegalDocumentModel:
        if (legal_document_id is None) == (legal_document_set_id is None):
            raise ValueError("Acceptance must reference exactly one legal document or one legal document set")
        storefront = await self._storefront_repo.get_storefront_by_id(storefront_id)
        if storefront is None:
            raise ValueError("Storefront not found")
        realm = await self._realm_repo.get_realm_by_id(auth_realm_id)
        if realm is None:
            raise ValueError("Auth realm not found")

        if legal_document_id is not None:
            document = await self._repo.get_document_by_id(legal_document_id)
            if document is None:
                raise ValueError("Legal document not found")

        if legal_document_set_id is not None:
            document_set = await self._repo.get_document_set_by_id(legal_document_set_id)
            if document_set is None:
                raise ValueError("Legal document set not found")
            if document_set.storefront_id != storefront_id:
                raise ValueError("Legal document set does not belong to the specified storefront")
            if document_set.auth_realm_id is not None and document_set.auth_realm_id != auth_realm_id:
                raise ValueError("Legal document set does not belong to the specified auth realm")

        model = AcceptedLegalDocumentModel(
            legal_document_id=legal_document_id,
            legal_document_set_id=legal_document_set_id,
            storefront_id=storefront_id,
            auth_realm_id=auth_realm_id,
            actor_principal_id=actor_principal_id,
            actor_principal_type=actor_principal_type,
            acceptance_channel=acceptance_channel.strip(),
            quote_session_id=quote_session_id,
            checkout_session_id=checkout_session_id,
            order_id=order_id,
            source_ip=source_ip,
            user_agent=user_agent,
            device_context=device_context,
            accepted_at=datetime.now(UTC),
        )
        return await self._repo.create_acceptance(model)
