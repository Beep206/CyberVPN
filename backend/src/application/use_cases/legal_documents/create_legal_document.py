from __future__ import annotations

import hashlib

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.legal_document_model import LegalDocumentModel
from src.infrastructure.database.repositories.legal_document_repo import LegalDocumentRepository
from src.infrastructure.database.repositories.policy_version_repo import PolicyVersionRepository


class CreateLegalDocumentUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._policy_repo = PolicyVersionRepository(session)
        self._repo = LegalDocumentRepository(session)

    async def execute(
        self,
        *,
        document_key: str,
        document_type: str,
        locale: str,
        title: str,
        content_markdown: str,
        policy_version_id,
    ) -> LegalDocumentModel:
        policy_version = await self._policy_repo.get_by_id(policy_version_id)
        if policy_version is None:
            raise ValueError("Policy version not found")

        checksum = hashlib.sha256(content_markdown.encode("utf-8")).hexdigest()
        model = LegalDocumentModel(
            document_key=document_key.strip(),
            document_type=document_type.strip(),
            locale=locale.strip(),
            title=title.strip(),
            content_markdown=content_markdown,
            content_checksum=checksum,
            policy_version_id=policy_version_id,
        )
        return await self._repo.create_document(model)
