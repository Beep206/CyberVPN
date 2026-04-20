"""Canonical payout destination identity for partner settlement."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class PartnerPayoutAccount:
    id: UUID
    partner_account_id: UUID
    settlement_profile_id: UUID | None
    payout_rail: str
    display_label: str
    masked_destination: str
    destination_metadata: dict
    verification_status: str
    approval_status: str
    account_status: str
    is_default: bool
    created_by_admin_user_id: UUID | None
    verified_by_admin_user_id: UUID | None
    verified_at: datetime | None
    approved_by_admin_user_id: UUID | None
    approved_at: datetime | None
    suspended_by_admin_user_id: UUID | None
    suspended_at: datetime | None
    suspension_reason_code: str | None
    archived_by_admin_user_id: UUID | None
    archived_at: datetime | None
    archive_reason_code: str | None
    default_selected_by_admin_user_id: UUID | None
    default_selected_at: datetime | None
    created_at: datetime
    updated_at: datetime
