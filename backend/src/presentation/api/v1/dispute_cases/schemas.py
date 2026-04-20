from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.domain.enums import DisputeCaseKind, DisputeCaseStatus


class CreateDisputeCaseRequest(BaseModel):
    partner_account_id: UUID
    payment_dispute_id: UUID | None = None
    order_id: UUID | None = None
    case_kind: DisputeCaseKind
    case_status: DisputeCaseStatus = DisputeCaseStatus.OPEN
    summary: str = Field(..., min_length=1, max_length=2000)
    case_payload: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)
    assigned_to_admin_user_id: UUID | None = None


class DisputeCaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    partner_account_id: UUID
    payment_dispute_id: UUID | None
    order_id: UUID | None
    case_kind: DisputeCaseKind
    case_status: DisputeCaseStatus
    summary: str
    payload: dict[str, Any] = Field(
        validation_alias="case_payload",
        serialization_alias="payload",
    )
    notes: list[str] = Field(
        validation_alias="notes_payload",
        serialization_alias="notes",
        default_factory=list,
    )
    opened_by_admin_user_id: UUID | None
    assigned_to_admin_user_id: UUID | None
    closed_by_admin_user_id: UUID | None
    closed_at: datetime | None
    created_at: datetime
    updated_at: datetime
