from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from src.domain.enums import PrincipalClass


@dataclass(frozen=True)
class RiskSubject:
    uuid: UUID
    principal_class: PrincipalClass | str
    principal_subject: str
    auth_realm_id: UUID | None
    storefront_id: UUID | None
    status: str
    risk_level: str
    metadata: dict[str, Any]
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.principal_subject.strip():
            raise ValueError("Risk subject principal_subject must not be empty")
