from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from src.domain.entities.accepted_legal_document import AcceptedLegalDocument
from src.domain.entities.legal_document import LegalDocument
from src.domain.entities.legal_document_set import LegalDocumentSet


class LegalDocumentRepository(ABC):
    @abstractmethod
    async def create_document(self, document: LegalDocument) -> LegalDocument: ...

    @abstractmethod
    async def create_document_set(self, document_set: LegalDocumentSet) -> LegalDocumentSet: ...

    @abstractmethod
    async def list_documents(self, *, document_type: str | None = None) -> list[LegalDocument]: ...

    @abstractmethod
    async def resolve_active_set(
        self,
        *,
        storefront_key: str,
        at: datetime | None = None,
    ) -> LegalDocumentSet | None: ...

    @abstractmethod
    async def create_acceptance(self, acceptance: AcceptedLegalDocument) -> AcceptedLegalDocument: ...

    @abstractmethod
    async def list_acceptances_for_principal(
        self,
        *,
        actor_principal_id: UUID,
    ) -> list[AcceptedLegalDocument]: ...
