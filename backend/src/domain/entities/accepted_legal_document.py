from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from src.domain.enums import PrincipalClass


@dataclass(frozen=True)
class AcceptedLegalDocument:
    uuid: UUID
    legal_document_id: UUID | None
    legal_document_set_id: UUID | None
    storefront_id: UUID
    auth_realm_id: UUID
    actor_principal_id: UUID
    actor_principal_type: PrincipalClass | str
    acceptance_channel: str
    quote_session_id: UUID | None
    checkout_session_id: UUID | None
    order_id: UUID | None
    source_ip: str | None
    user_agent: str | None
    device_context: dict[str, Any] | None
    accepted_at: datetime

    def __post_init__(self) -> None:
        if (self.legal_document_id is None) == (self.legal_document_set_id is None):
            raise ValueError("Accepted legal document must reference exactly one document or one document set")
