from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.domain.enums import (
    PartnerPayoutAccountApprovalStatus,
    PartnerPayoutAccountStatus,
    PartnerPayoutAccountVerificationStatus,
)


class CreatePartnerPayoutAccountRequest(BaseModel):
    partner_account_id: UUID
    payout_rail: str = Field(..., min_length=1, max_length=40)
    display_label: str = Field(..., min_length=1, max_length=120)
    destination_reference: str = Field(..., min_length=1, max_length=255)
    destination_metadata: dict[str, Any] = Field(default_factory=dict)
    settlement_profile_id: UUID | None = None
    make_default: bool = False


class SuspendPartnerPayoutAccountRequest(BaseModel):
    reason_code: str | None = Field(None, min_length=1, max_length=80)


class ArchivePartnerPayoutAccountRequest(BaseModel):
    reason_code: str | None = Field(None, min_length=1, max_length=80)


class PartnerPayoutAccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    id: UUID
    partner_account_id: UUID
    settlement_profile_id: UUID | None = None
    payout_rail: str
    display_label: str
    masked_destination: str
    destination_metadata: dict[str, Any] = Field(default_factory=dict)
    verification_status: PartnerPayoutAccountVerificationStatus
    approval_status: PartnerPayoutAccountApprovalStatus
    account_status: PartnerPayoutAccountStatus
    is_default: bool
    created_by_admin_user_id: UUID | None = None
    verified_by_admin_user_id: UUID | None = None
    verified_at: datetime | None = None
    approved_by_admin_user_id: UUID | None = None
    approved_at: datetime | None = None
    suspended_by_admin_user_id: UUID | None = None
    suspended_at: datetime | None = None
    suspension_reason_code: str | None = None
    archived_by_admin_user_id: UUID | None = None
    archived_at: datetime | None = None
    archive_reason_code: str | None = None
    default_selected_by_admin_user_id: UUID | None = None
    default_selected_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class PartnerPayoutAccountEligibilityResponse(BaseModel):
    partner_payout_account_id: UUID
    partner_account_id: UUID
    eligible: bool
    reason_codes: list[str]
    blocking_risk_review_ids: list[UUID]
    active_reserve_ids: list[UUID]
    checked_at: datetime
