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
    campaign_id: UUID | None = None
    campaign_version_id: UUID | None = None
    root_invite_code_id: UUID | None = None
    parent_invite_code_id: UUID | None = None
    source_redemption_id: UUID | None = None
    generation_depth: int = 0
    status: str | None = None
    code_hash: str | None = None
    code_prefix: str | None = None
    grant_mode: str | None = None
    grant_plan_id: UUID | None = None
    grant_duration_days: int | None = None
    child_grant_plan_id: UUID | None = None
    child_grant_duration_days: int | None = None
    child_policy: dict[str, Any] | None = None


class AdminCreateInviteRequest(BaseModel):
    """Request body for admin-created invite codes."""

    user_id: UUID = Field(..., description="User who will own the invite codes")
    free_days: int = Field(..., gt=0, description="Number of free subscription days the code grants")
    count: int = Field(1, ge=1, le=100, description="Number of codes to generate")
    plan_id: UUID | None = Field(None, description="Optional plan to associate with the codes")
    legacy_acknowledgement: bool = Field(
        False,
        description="Required when using the legacy manual invite endpoint for premium_smart_ru.",
    )


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
    invite_campaign_id: UUID | None = None
    invite_campaign_version_id: UUID | None = None
    root_invite_code_id: UUID | None = None
    parent_invite_code_id: UUID | None = None
    source_redemption_id: UUID | None = None
    root_owner_user_id: UUID | None = None
    generation_depth: int = 0
    batch_kind: str | None = None
    source_growth_code_id: UUID | None = None
    source_benefit_id: UUID | None = None
    source_order_id: UUID | None = None
    source_payment_id: UUID | None = None
    created_at: datetime
    grant_mode: str | None = None
    grant_plan_id: UUID | None = None
    grant_duration_days: int | None = None
    child_grant_plan_id: UUID | None = None
    child_grant_duration_days: int | None = None
    child_policy: dict[str, Any] | None = None


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
    owner_user_id: UUID | None = None
    batch_id: UUID | None = None
    status: str
    is_used: bool
    used_by_user_id: UUID | None = None
    used_at: datetime | None = None
    revoked_at: datetime | None = None
    expires_at: datetime | None = None
    created_at: datetime
    campaign_id: UUID | None = None
    campaign_key: str | None = None
    campaign_version_id: UUID | None = None
    root_invite_code_id: UUID | None = None
    parent_invite_code_id: UUID | None = None
    source_redemption_id: UUID | None = None
    generation_depth: int = 0
    grant_mode: str | None = None
    grant_plan_id: UUID | None = None
    grant_plan_code: str | None = None
    grant_duration_days: int | None = None
    child_grant_plan_id: UUID | None = None
    child_grant_plan_code: str | None = None
    child_grant_duration_days: int | None = None
    child_policy_preview: dict[str, Any] | None = None


class AdminInviteCodeInventoryResponse(BaseModel):
    """Paginated admin invite-code inventory response."""

    items: list[AdminInviteCodeSummaryResponse]
    total: int
    offset: int
    limit: int


class AdminInviteBatchResponse(BaseModel):
    """Admin invite batch summary."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_user_id: UUID | None
    campaign_id: UUID | None = None
    invite_campaign_id: UUID | None = None
    invite_campaign_version_id: UUID | None = None
    root_invite_code_id: UUID | None = None
    parent_invite_code_id: UUID | None = None
    source_redemption_id: UUID | None = None
    root_owner_user_id: UUID | None = None
    generation_depth: int = 0
    batch_kind: str | None = None
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
    grant_mode: str | None = None
    grant_plan_id: UUID | None = None
    grant_duration_days: int | None = None
    grant_snapshot: dict[str, Any] | None = None
    child_grant_plan_id: UUID | None = None
    child_grant_duration_days: int | None = None
    child_policy: dict[str, Any] | None = None
    risk_policy: dict[str, Any] | None = None
    redemption_policy: dict[str, Any] | None = None
    issue_policy: dict[str, Any] | None = None
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


class AdminInviteCampaignCreateRequest(BaseModel):
    """Create a flexible invite campaign with an initial draft version."""

    campaign_key: str = Field(..., min_length=3, max_length=80, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    name: str = Field(..., min_length=3, max_length=160)
    description: str | None = Field(None, max_length=2_000)
    owner_mode: str = Field("selected_user", max_length=30)
    starts_at: datetime | None = None
    expires_at: datetime | None = None
    allowed_surfaces: list[str] = Field(default_factory=lambda: ["web", "miniapp", "telegram_bot"])
    allowed_geos: list[str] = Field(default_factory=list, max_length=200)
    allowed_markets: list[str] = Field(default_factory=list, max_length=200)
    allowed_segments: list[str] = Field(default_factory=list, max_length=200)
    risk_policy_key: str | None = Field(None, max_length=120)
    grant_plan_id: UUID | None = None
    grant_plan_code: str | None = Field("premium_smart_ru", max_length=80)
    grant_duration_days: int = Field(365, ge=1, le=3_660)
    child_invite_count: int = Field(10, ge=0, le=100)
    child_invite_free_days: int = Field(365, ge=1, le=3_660)
    child_invite_expiry_days: int = Field(30, ge=1, le=3_660)
    child_grant_plan_id: UUID | None = None
    child_grant_plan_code: str | None = Field("premium_smart_ru", max_length=80)
    child_grant_duration_days: int | None = Field(365, ge=1, le=3_660)
    max_generation_depth: int = Field(5, ge=0, le=12)
    require_no_active_access: bool = True
    block_self_redemption: bool = True
    risk_policy: dict[str, Any] = Field(default_factory=dict)
    export_policy: dict[str, Any] = Field(default_factory=lambda: {"raw_export_enabled": True})
    notification_policy: dict[str, Any] = Field(default_factory=dict)
    caps: dict[str, Any] = Field(default_factory=dict)
    publish: bool = False
    reason: str | None = Field(None, max_length=240)


class AdminInviteCampaignVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    campaign_id: UUID
    version: int
    status: str
    grant_mode: str
    grant_plan_id: UUID | None = None
    grant_duration_days: int | None = None
    grant_snapshot: dict[str, Any]
    child_invite_count: int
    child_invite_free_days: int
    child_invite_expiry_days: int
    child_grant_plan_id: UUID | None = None
    child_grant_duration_days: int | None = None
    child_grant_snapshot: dict[str, Any]
    max_generation_depth: int
    block_self_redemption: bool
    require_no_active_access: bool
    allowed_surfaces: list[str]
    risk_policy: dict[str, Any]
    redemption_policy: dict[str, Any]
    child_policy: dict[str, Any]
    issue_policy: dict[str, Any]
    export_policy: dict[str, Any]
    notification_policy: dict[str, Any]
    checksum: str
    created_by_admin_id: UUID
    published_by_admin_id: UUID | None = None
    published_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class AdminInviteCampaignResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    campaign_key: str
    name: str
    description: str | None = None
    status: str
    owner_mode: str
    current_version_id: UUID | None = None
    starts_at: datetime | None = None
    expires_at: datetime | None = None
    allowed_surfaces: list[str]
    allowed_geos: dict[str, Any]
    risk_policy: dict[str, Any]
    export_policy: dict[str, Any]
    notification_policy: dict[str, Any]
    caps: dict[str, Any]
    created_by_admin_id: UUID
    updated_by_admin_id: UUID | None = None
    published_at: datetime | None = None
    paused_at: datetime | None = None
    archived_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    current_version: AdminInviteCampaignVersionResponse | None = None


class AdminInviteCampaignListResponse(BaseModel):
    items: list[AdminInviteCampaignResponse]
    total: int
    offset: int
    limit: int


class AdminInviteCampaignActionRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=240)


class AdminInviteCampaignVersionCreateRequest(BaseModel):
    grant_plan_id: UUID | None = None
    grant_plan_code: str | None = Field("premium_smart_ru", max_length=80)
    grant_duration_days: int = Field(365, ge=1, le=3_660)
    child_invite_count: int = Field(10, ge=0, le=100)
    child_invite_free_days: int = Field(365, ge=1, le=3_660)
    child_invite_expiry_days: int = Field(30, ge=1, le=3_660)
    child_grant_plan_id: UUID | None = None
    child_grant_plan_code: str | None = Field("premium_smart_ru", max_length=80)
    child_grant_duration_days: int | None = Field(365, ge=1, le=3_660)
    max_generation_depth: int = Field(5, ge=0, le=12)
    require_no_active_access: bool = True
    block_self_redemption: bool = True
    allowed_surfaces: list[str] = Field(default_factory=lambda: ["web", "miniapp", "telegram_bot"])
    risk_policy: dict[str, Any] = Field(default_factory=dict)
    export_policy: dict[str, Any] = Field(default_factory=lambda: {"raw_export_enabled": True})
    notification_policy: dict[str, Any] = Field(default_factory=dict)
    reason: str | None = Field(None, max_length=240)


class AdminInviteCampaignVersionValidationResponse(BaseModel):
    version_id: UUID
    checksum: str
    valid: bool
    errors: list[str]
    warnings: list[str]


class AdminInviteCampaignBatchCreateRequest(BaseModel):
    owner_user_id: UUID | None = None
    owner_user_ids: list[UUID] = Field(default_factory=list, max_length=1_000)
    count: int = Field(1, ge=1, le=1_000)
    version_id: UUID | None = None
    idempotency_key: str | None = Field(None, min_length=3, max_length=200)
    expires_at: datetime | None = None
    expiry_days: int | None = Field(30, ge=1, le=3_660)
    reason: str = Field(..., min_length=3, max_length=240)


class AdminInviteCampaignBatchCreateResponse(BaseModel):
    campaign: AdminInviteCampaignResponse
    batch: AdminInviteBatchResponse
    raw_codes: list[str]


class AdminInviteRedemptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    invite_code_id: UUID
    campaign_id: UUID | None = None
    campaign_version_id: UUID | None = None
    root_invite_code_id: UUID | None = None
    parent_invite_code_id: UUID | None = None
    inviter_user_id: UUID | None = None
    invitee_user_id: UUID
    generation_depth: int
    source_surface: str
    entitlement_grant_id: UUID | None = None
    granted_plan_id: UUID | None = None
    granted_plan_code: str | None = None
    granted_duration_days: int | None = None
    child_batch_id: UUID | None = None
    child_issued_count: int = 0
    status: str
    blocked_reason: str | None = None
    risk_decision: dict[str, Any]
    grant_snapshot: dict[str, Any]
    redeemed_at: datetime | None = None
    reversed_at: datetime | None = None
    created_at: datetime


class AdminInviteRedemptionListResponse(BaseModel):
    items: list[AdminInviteRedemptionResponse]
    total: int
    offset: int
    limit: int


class AdminInviteTreeNodeResponse(BaseModel):
    invite_code_id: UUID
    parent_invite_code_id: UUID | None = None
    root_invite_code_id: UUID
    owner_user_id: UUID | None = None
    used_by_user_id: UUID | None = None
    generation_depth: int
    status: str
    grant_mode: str | None = None
    grant_plan_id: UUID | None = None
    child_batch_id: UUID | None = None
    granted_plan_id: UUID | None = None
    granted_plan_code: str | None = None
    child_count: int = 0
    created_at: datetime | None = None
    used_at: datetime | None = None


class AdminInviteTreeEdgeResponse(BaseModel):
    id: UUID
    root_invite_code_id: UUID
    parent_invite_code_id: UUID | None = None
    redeemed_invite_code_id: UUID
    redemption_id: UUID
    inviter_user_id: UUID | None = None
    invitee_user_id: UUID
    generation_depth: int
    status: str
    child_batch_id: UUID | None = None
    granted_plan_id: UUID | None = None
    granted_plan_code: str | None = None


class AdminInviteTreeResponse(BaseModel):
    root_invite_code_id: UUID
    nodes: list[AdminInviteTreeNodeResponse]
    edges: list[AdminInviteTreeEdgeResponse]
    stats: dict[str, Any]


class AdminInviteTreeRootResponse(BaseModel):
    root_invite_code_id: UUID
    campaign_id: UUID | None = None
    campaign_key: str | None = None
    owner_user_id: UUID | None = None
    generation_depth: int = 0
    status: str
    issued_count: int = 0
    redeemed_count: int = 0
    child_invites_issued_count: int = 0
    max_depth_reached: int = 0
    created_at: datetime | None = None


class AdminInviteTreeRootListResponse(BaseModel):
    items: list[AdminInviteTreeRootResponse]
    total: int
    offset: int
    limit: int
