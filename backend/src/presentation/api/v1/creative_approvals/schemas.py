from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.domain.enums import CreativeApprovalKind, CreativeApprovalStatus


class CreateCreativeApprovalRequest(BaseModel):
    partner_account_id: UUID
    approval_kind: CreativeApprovalKind = CreativeApprovalKind.CREATIVE_APPROVAL
    approval_status: CreativeApprovalStatus = CreativeApprovalStatus.UNDER_REVIEW
    scope_label: str = Field(..., min_length=1, max_length=120)
    creative_ref: str | None = Field(default=None, max_length=255)
    approval_payload: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)
    expires_at: datetime | None = None


class CreativeApprovalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    partner_account_id: UUID
    approval_kind: CreativeApprovalKind
    approval_status: CreativeApprovalStatus
    scope_label: str
    creative_ref: str | None
    approval_payload: dict[str, Any]
    notes: list[str] = Field(
        validation_alias="notes_payload",
        serialization_alias="notes",
        default_factory=list,
    )
    submitted_by_admin_user_id: UUID | None
    reviewed_by_admin_user_id: UUID | None
    reviewed_at: datetime | None
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime
