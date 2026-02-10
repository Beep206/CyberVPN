from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.domain.enums import InviteSource


@dataclass(frozen=True)
class InviteCode:
    id: UUID
    code: str
    owner_user_id: UUID
    free_days: int
    source: InviteSource
    is_used: bool
    created_at: datetime
    plan_id: UUID | None = None
    source_payment_id: UUID | None = None
    used_by_user_id: UUID | None = None
    used_at: datetime | None = None
    expires_at: datetime | None = None
