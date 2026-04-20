"""Partner workspace membership entity."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class PartnerAccountUser:
    id: UUID
    partner_account_id: UUID
    admin_user_id: UUID
    role_id: UUID
    membership_status: str
    invited_by_admin_user_id: UUID | None
    created_at: datetime
    updated_at: datetime
