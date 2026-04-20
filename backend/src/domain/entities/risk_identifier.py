from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.domain.enums import RiskIdentifierType


@dataclass(frozen=True)
class RiskIdentifier:
    uuid: UUID
    risk_subject_id: UUID
    identifier_type: RiskIdentifierType | str
    value_hash: str
    value_preview: str
    is_verified: bool
    source: str
    created_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.value_hash.strip():
            raise ValueError("Risk identifier value_hash must not be empty")
