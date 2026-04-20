from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.domain.enums import EarningHoldReasonType, EarningHoldStatus


class ReleaseEarningHoldRequest(BaseModel):
    release_reason_code: str | None = Field(None, min_length=1, max_length=80)
    force: bool = False


class EarningHoldResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    id: UUID
    earning_event_id: UUID
    partner_account_id: UUID | None = None
    hold_reason_type: EarningHoldReasonType
    hold_status: EarningHoldStatus
    reason_code: str | None = None
    hold_until: datetime | None = None
    released_at: datetime | None = None
    released_by_admin_user_id: UUID | None = None
    created_by_admin_user_id: UUID | None = None
    hold_payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
