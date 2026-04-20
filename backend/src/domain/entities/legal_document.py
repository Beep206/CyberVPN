from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class LegalDocument:
    uuid: UUID
    document_key: str
    document_type: str
    locale: str
    title: str
    content_markdown: str
    content_checksum: str
    policy_version_id: UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None
