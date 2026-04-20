from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class LegalDocumentSetItem:
    uuid: UUID
    legal_document_id: UUID
    required: bool
    display_order: int


@dataclass(frozen=True)
class LegalDocumentSet:
    uuid: UUID
    set_key: str
    storefront_id: UUID
    auth_realm_id: UUID | None
    display_name: str
    policy_version_id: UUID
    documents: list[LegalDocumentSetItem]
    created_at: datetime | None = None
    updated_at: datetime | None = None
