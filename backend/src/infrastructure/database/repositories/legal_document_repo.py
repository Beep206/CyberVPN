from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.infrastructure.database.models.accepted_legal_document_model import AcceptedLegalDocumentModel
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.legal_document_model import LegalDocumentModel
from src.infrastructure.database.models.legal_document_set_model import LegalDocumentSetItemModel, LegalDocumentSetModel
from src.infrastructure.database.models.policy_version_model import PolicyVersionModel
from src.infrastructure.database.models.storefront_model import StorefrontModel


class LegalDocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_document(self, model: LegalDocumentModel) -> LegalDocumentModel:
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return model

    async def list_documents(
        self,
        *,
        document_type: str | None = None,
        locale: str | None = None,
    ) -> list[LegalDocumentModel]:
        query: Select[tuple[LegalDocumentModel]] = select(LegalDocumentModel).order_by(
            LegalDocumentModel.document_type.asc(),
            LegalDocumentModel.document_key.asc(),
            LegalDocumentModel.locale.asc(),
        )
        if document_type is not None:
            query = query.where(LegalDocumentModel.document_type == document_type)
        if locale is not None:
            query = query.where(LegalDocumentModel.locale == locale)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def get_document_by_id(self, legal_document_id: UUID) -> LegalDocumentModel | None:
        return await self._session.get(LegalDocumentModel, legal_document_id)

    async def get_documents_by_ids(self, legal_document_ids: list[UUID]) -> list[LegalDocumentModel]:
        if not legal_document_ids:
            return []
        result = await self._session.execute(
            select(LegalDocumentModel).where(LegalDocumentModel.id.in_(legal_document_ids))
        )
        return list(result.scalars().all())

    async def create_document_set(
        self,
        model: LegalDocumentSetModel,
        *,
        items: list[LegalDocumentSetItemModel],
    ) -> LegalDocumentSetModel:
        self._session.add(model)
        await self._session.flush()
        for item in items:
            item.legal_document_set_id = model.id
            self._session.add(item)
        await self._session.flush()
        await self._session.refresh(model)
        return await self.get_document_set_by_id(model.id) or model

    async def get_document_set_by_id(self, legal_document_set_id: UUID) -> LegalDocumentSetModel | None:
        result = await self._session.execute(
            select(LegalDocumentSetModel)
            .options(selectinload(LegalDocumentSetModel.documents).selectinload(LegalDocumentSetItemModel.legal_document))
            .where(LegalDocumentSetModel.id == legal_document_set_id)
        )
        return result.scalar_one_or_none()

    async def resolve_active_set(
        self,
        *,
        storefront_key: str,
        realm_key: str | None = None,
        at: datetime | None = None,
    ) -> LegalDocumentSetModel | None:
        now = at or datetime.now(UTC)
        query = (
            select(LegalDocumentSetModel)
            .join(StorefrontModel, StorefrontModel.id == LegalDocumentSetModel.storefront_id)
            .join(PolicyVersionModel, PolicyVersionModel.id == LegalDocumentSetModel.policy_version_id)
            .options(selectinload(LegalDocumentSetModel.documents).selectinload(LegalDocumentSetItemModel.legal_document))
            .where(
                StorefrontModel.storefront_key == storefront_key,
                PolicyVersionModel.approval_state == "approved",
                PolicyVersionModel.version_status == "active",
                PolicyVersionModel.effective_from <= now,
                (PolicyVersionModel.effective_to.is_(None)) | (PolicyVersionModel.effective_to > now),
            )
            .order_by(PolicyVersionModel.effective_from.desc())
        )
        if realm_key is not None:
            query = query.join(AuthRealmModel, AuthRealmModel.id == LegalDocumentSetModel.auth_realm_id).where(
                AuthRealmModel.realm_key == realm_key
            )

        result = await self._session.execute(query)
        return result.scalars().first()

    async def create_acceptance(self, model: AcceptedLegalDocumentModel) -> AcceptedLegalDocumentModel:
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return model

    async def list_acceptances_for_principal(
        self,
        *,
        actor_principal_id: UUID,
    ) -> list[AcceptedLegalDocumentModel]:
        return await self.list_acceptances(actor_principal_id=actor_principal_id)

    async def get_acceptance_by_id(
        self,
        acceptance_id: UUID,
    ) -> AcceptedLegalDocumentModel | None:
        return await self._session.get(AcceptedLegalDocumentModel, acceptance_id)

    async def list_acceptances(
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
        query = select(AcceptedLegalDocumentModel)
        if actor_principal_id is not None:
            query = query.where(AcceptedLegalDocumentModel.actor_principal_id == actor_principal_id)
        if storefront_id is not None:
            query = query.where(AcceptedLegalDocumentModel.storefront_id == storefront_id)
        if auth_realm_id is not None:
            query = query.where(AcceptedLegalDocumentModel.auth_realm_id == auth_realm_id)
        if order_id is not None:
            query = query.where(AcceptedLegalDocumentModel.order_id == order_id)
        if acceptance_channel is not None:
            query = query.where(AcceptedLegalDocumentModel.acceptance_channel == acceptance_channel)
        result = await self._session.execute(
            query
            .order_by(AcceptedLegalDocumentModel.accepted_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())
