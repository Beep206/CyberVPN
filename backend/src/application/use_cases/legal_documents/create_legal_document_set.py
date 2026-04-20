from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.legal_document_set_model import LegalDocumentSetItemModel, LegalDocumentSetModel
from src.infrastructure.database.repositories.auth_realm_repo import AuthRealmRepository
from src.infrastructure.database.repositories.legal_document_repo import LegalDocumentRepository
from src.infrastructure.database.repositories.policy_version_repo import PolicyVersionRepository
from src.infrastructure.database.repositories.storefront_repo import StorefrontRepository


class CreateLegalDocumentSetUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = LegalDocumentRepository(session)
        self._policy_repo = PolicyVersionRepository(session)
        self._storefront_repo = StorefrontRepository(session)
        self._realm_repo = AuthRealmRepository(session)

    async def execute(
        self,
        *,
        set_key: str,
        storefront_id,
        auth_realm_id,
        display_name: str,
        policy_version_id,
        documents: list[dict],
    ) -> LegalDocumentSetModel:
        policy_version = await self._policy_repo.get_by_id(policy_version_id)
        if policy_version is None:
            raise ValueError("Policy version not found")
        storefront = await self._storefront_repo.get_storefront_by_id(storefront_id)
        if storefront is None:
            raise ValueError("Storefront not found")
        if auth_realm_id is not None and await self._realm_repo.get_realm_by_id(auth_realm_id) is None:
            raise ValueError("Auth realm not found")

        document_ids = [item["legal_document_id"] for item in documents]
        if len(set(document_ids)) != len(document_ids):
            raise ValueError("Legal document set cannot contain duplicate documents")
        existing_documents = await self._repo.get_documents_by_ids(document_ids)
        if len(existing_documents) != len(set(document_ids)):
            raise ValueError("One or more legal documents do not exist")

        model = LegalDocumentSetModel(
            set_key=set_key.strip(),
            storefront_id=storefront_id,
            auth_realm_id=auth_realm_id,
            display_name=display_name.strip(),
            policy_version_id=policy_version_id,
        )
        item_models = [
            LegalDocumentSetItemModel(
                legal_document_id=item["legal_document_id"],
                required=item.get("required", True),
                display_order=item.get("display_order", index),
            )
            for index, item in enumerate(documents)
        ]
        return await self._repo.create_document_set(model, items=item_models)
