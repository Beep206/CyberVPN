"""Pydantic schemas for invite code endpoints."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RedeemInviteRequest(BaseModel):
    """Request body for redeeming an invite code."""

    code: str = Field(..., min_length=1, max_length=32, description="Invite code to redeem")


class InviteCodeResponse(BaseModel):
    """Response schema for a single invite code."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    free_days: int
    is_used: bool
    expires_at: datetime | None
    created_at: datetime
    entitlement_grant_id: UUID | None = None
    entitlement_snapshot: dict[str, Any] | None = None
    batch_id: UUID | None = None
    status: str | None = None
    code_hash: str | None = None
    code_prefix: str | None = None


class AdminCreateInviteRequest(BaseModel):
    """Request body for admin-created invite codes."""

    user_id: UUID = Field(..., description="User who will own the invite codes")
    free_days: int = Field(..., gt=0, description="Number of free subscription days the code grants")
    count: int = Field(1, ge=1, le=100, description="Number of codes to generate")
    plan_id: UUID | None = Field(None, description="Optional plan to associate with the codes")


class CustomerInviteBatchResponse(BaseModel):
    """Customer-safe invite batch summary for grouped invite inventory."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_type: str
    requested_count: int
    issued_count: int
    friend_days: int
    expiry_mode: str
    expiry_days: int | None
    expires_at: datetime | None
    status: str
    campaign_id: UUID | None = None
    source_growth_code_id: UUID | None = None
    source_benefit_id: UUID | None = None
    source_order_id: UUID | None = None
    source_payment_id: UUID | None = None
    created_at: datetime


class CustomerInviteBatchGroupResponse(BaseModel):
    """One invite batch with its invite codes for /invites/my?group_by=batch."""

    batch: CustomerInviteBatchResponse
    invites: list[InviteCodeResponse]


class CustomerInviteBatchListResponse(BaseModel):
    """Grouped customer invite inventory response."""

    batches: list[CustomerInviteBatchGroupResponse]
    unbatched: list[InviteCodeResponse] = Field(default_factory=list)
    total_batches: int
    total_invites: int
    offset: int
    limit: int


class AdminInviteCodeSummaryResponse(BaseModel):
    """Admin-safe invite code summary for batch views."""

    id: UUID
    code_prefix: str | None = None
    code_hash: str | None = None
    status: str
    is_used: bool
    used_by_user_id: UUID | None = None
    used_at: datetime | None = None
    revoked_at: datetime | None = None
    expires_at: datetime | None = None
    created_at: datetime


class AdminInviteBatchResponse(BaseModel):
    """Admin invite batch summary."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_user_id: UUID
    campaign_id: UUID | None = None
    source_growth_code_id: UUID | None = None
    source_benefit_id: UUID | None = None
    source_order_id: UUID | None = None
    source_payment_id: UUID | None = None
    source_type: str
    requested_count: int
    issued_count: int
    friend_days: int
    expiry_mode: str
    expiry_days: int | None = None
    expires_at: datetime | None = None
    entitlement_mode: str
    entitlement_profile_key: str | None = None
    plan_id: UUID | None = None
    entitlement_snapshot: dict[str, Any]
    status: str
    idempotency_key: str
    revoked_at: datetime | None = None
    revoked_by_admin_id: UUID | None = None
    revoked_reason: str | None = None
    created_at: datetime
    updated_at: datetime


class AdminInviteBatchDetailResponse(AdminInviteBatchResponse):
    """Admin invite batch detail with masked code inventory."""

    invites: list[AdminInviteCodeSummaryResponse] = Field(default_factory=list)


class AdminInviteBatchListResponse(BaseModel):
    """Paginated admin invite batch list."""

    items: list[AdminInviteBatchResponse]
    total: int
    offset: int
    limit: int


class AdminInviteBatchActionRequest(BaseModel):
    """Reasoned admin invite batch mutation request."""

    reason: str = Field(..., min_length=3, max_length=240)


class AdminExtendInviteBatchRequest(AdminInviteBatchActionRequest):
    """Extend invite batch expiry by duration or explicit timestamp."""

    expiry_days: int | None = Field(default=None, ge=1, le=3_660)
    expires_at: datetime | None = None

    @model_validator(mode="after")
    def _validate_extension(self) -> "AdminExtendInviteBatchRequest":
        if (self.expiry_days is None) == (self.expires_at is None):
            raise ValueError("Provide exactly one of expiry_days or expires_at")
        return self


class AdminInviteBatchExportCodeResponse(BaseModel):
    """Explicit export row; raw code is intentionally returned only by export endpoint."""

    id: UUID
    code: str
    code_prefix: str | None = None
    code_hash: str | None = None
    status: str
    is_used: bool
    expires_at: datetime | None = None


class AdminInviteBatchExportResponse(BaseModel):
    """Admin export payload for one invite batch."""

    batch_id: UUID
    exported_count: int
    codes: list[AdminInviteBatchExportCodeResponse]
