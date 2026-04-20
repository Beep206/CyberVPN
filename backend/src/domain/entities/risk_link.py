from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from src.domain.enums import RiskIdentifierType, RiskLinkType


@dataclass(frozen=True)
class RiskLink:
    uuid: UUID
    left_subject_id: UUID
    right_subject_id: UUID
    link_type: RiskLinkType | str
    identifier_type: RiskIdentifierType | str
    source_identifier_id: UUID | None
    status: str
    evidence: dict[str, Any]
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.left_subject_id == self.right_subject_id:
            raise ValueError("Risk link must join two distinct subjects")
