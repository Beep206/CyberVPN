from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.domain.enums import TrafficDeclarationKind, TrafficDeclarationStatus


class CreateTrafficDeclarationRequest(BaseModel):
    partner_account_id: UUID
    declaration_kind: TrafficDeclarationKind
    scope_label: str = Field(..., min_length=1, max_length=120)
    declaration_payload: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class TrafficDeclarationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    partner_account_id: UUID
    declaration_kind: TrafficDeclarationKind
    declaration_status: TrafficDeclarationStatus
    scope_label: str
    declaration_payload: dict[str, Any]
    notes: list[str] = Field(
        validation_alias="notes_payload",
        serialization_alias="notes",
        default_factory=list,
    )
    submitted_by_admin_user_id: UUID | None
    reviewed_by_admin_user_id: UUID | None
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime
