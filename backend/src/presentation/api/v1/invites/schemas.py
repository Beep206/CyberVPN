"""Pydantic schemas for invite code endpoints."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

InviteAccessDurationMode = Literal["fixed_days", "lifetime"]
InviteCodeExpiryMode = Literal["relative", "absolute", "none"]
AdminInviteBatchExpiryMode = Literal["campaign_default", "relative", "absolute", "none"]
InviteCodeUsageMode = Literal["single_use", "multi_use"]
AdminInviteBatchUsageMode = Literal["campaign_default", "single_use", "multi_use"]


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
    used_at: datetime | None = None
    revoked_at: datetime | None = None
    expires_at: datetime | None
    created_at: datetime
    usage_mode: InviteCodeUsageMode = "single_use"
    max_redemptions: int | None = None
    redeemed_count: int = 0
    active_redemptions_count: int = 0
    reversed_redemptions_count: int = 0
    remaining_redemptions: int | None = None
    first_redeemed_at: datetime | None = None
    last_redeemed_at: datetime | None = None
    exhausted_at: datetime | None = None
    per_user_redemption_cap: int = 1
    is_redeemable: bool = True
    status_sort_order: int = 5
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
    grant_duration_mode: str | None = None
    grant_duration_days: int | None = None
    grant_device_limit_override: int | None = None
    child_grant_plan_id: UUID | None = None
    child_grant_duration_mode: str | None = None
    child_grant_duration_days: int | None = None
    child_grant_device_limit_override: int | None = None
    child_invite_expiry_mode: str | None = None
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
    usage_mode: InviteCodeUsageMode = "single_use"
    max_redemptions_per_code: int | None = None
    per_user_redemption_cap: int = 1
    multi_use_policy: dict[str, Any] | None = None
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
    grant_duration_mode: str | None = None
    grant_duration_days: int | None = None
    grant_device_limit_override: int | None = None
    child_grant_plan_id: UUID | None = None
    child_grant_duration_mode: str | None = None
    child_grant_duration_days: int | None = None
    child_grant_device_limit_override: int | None = None
    child_invite_expiry_mode: str | None = None
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
    is_redeemable: bool = False
    status_sort_order: int = 5
    used_by_user_id: UUID | None = None
    used_at: datetime | None = None
    revoked_at: datetime | None = None
    expires_at: datetime | None = None
    created_at: datetime
    usage_mode: InviteCodeUsageMode = "single_use"
    max_redemptions: int | None = None
    redeemed_count: int = 0
    active_redemptions_count: int = 0
    reversed_redemptions_count: int = 0
    remaining_redemptions: int | None = None
    first_redeemed_at: datetime | None = None
    last_redeemed_at: datetime | None = None
    exhausted_at: datetime | None = None
    per_user_redemption_cap: int = 1
    multi_use_policy: dict[str, Any] | None = None
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
    grant_duration_mode: str | None = None
    grant_duration_days: int | None = None
    grant_device_limit_override: int | None = None
    root_invite_expiry_mode: str | None = None
    child_grant_plan_id: UUID | None = None
    child_grant_plan_code: str | None = None
    child_grant_duration_mode: str | None = None
    child_grant_duration_days: int | None = None
    child_grant_device_limit_override: int | None = None
    child_invite_count: int = 0
    child_invite_expiry_mode: str | None = None
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
    usage_mode: InviteCodeUsageMode = "single_use"
    max_redemptions_per_code: int | None = None
    per_user_redemption_cap: int = 1
    multi_use_policy: dict[str, Any] | None = None
    entitlement_mode: str
    entitlement_profile_key: str | None = None
    plan_id: UUID | None = None
    entitlement_snapshot: dict[str, Any]
    grant_mode: str | None = None
    grant_plan_id: UUID | None = None
    grant_duration_mode: str | None = None
    grant_duration_days: int | None = None
    grant_device_limit_override: int | None = None
    grant_snapshot: dict[str, Any] | None = None
    child_grant_plan_id: UUID | None = None
    child_grant_duration_mode: str | None = None
    child_grant_duration_days: int | None = None
    child_grant_device_limit_override: int | None = None
    child_invite_expiry_mode: str | None = None
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
    grant_duration_mode: InviteAccessDurationMode = "fixed_days"
    grant_duration_days: int | None = Field(365, ge=1, le=3_660)
    grant_device_limit_override: int | None = Field(None, ge=1, le=200)
    root_invite_expiry_mode: InviteCodeExpiryMode = "relative"
    root_invite_expiry_days: int | None = Field(30, ge=1, le=3_660)
    root_invite_expires_at: datetime | None = None
    root_usage_mode: InviteCodeUsageMode = "single_use"
    root_max_redemptions: int | None = Field(1, ge=1, le=1_000_000)
    root_per_user_redemption_cap: int = Field(1, ge=1, le=1)
    child_invite_count: int = Field(10, ge=0, le=100)
    child_invite_free_days: int = Field(365, ge=0, le=3_660)
    child_invite_expiry_mode: InviteCodeExpiryMode = "relative"
    child_invite_expiry_days: int | None = Field(30, ge=1, le=3_660)
    child_invite_expires_at: datetime | None = None
    child_usage_mode: InviteCodeUsageMode = "single_use"
    child_max_redemptions: int | None = Field(1, ge=1, le=1_000_000)
    child_per_user_redemption_cap: int = Field(1, ge=1, le=1)
    child_grant_plan_id: UUID | None = None
    child_grant_plan_code: str | None = Field("premium_smart_ru", max_length=80)
    child_grant_duration_mode: InviteAccessDurationMode = "fixed_days"
    child_grant_duration_days: int | None = Field(365, ge=1, le=3_660)
    child_grant_device_limit_override: int | None = Field(None, ge=1, le=200)
    max_generation_depth: int = Field(5, ge=0, le=12)
    require_no_active_access: bool = True
    block_self_redemption: bool = True
    risk_policy: dict[str, Any] = Field(default_factory=dict)
    export_policy: dict[str, Any] = Field(default_factory=lambda: {"raw_export_enabled": True})
    notification_policy: dict[str, Any] = Field(default_factory=dict)
    caps: dict[str, Any] = Field(default_factory=dict)
    multi_use_policy: dict[str, Any] = Field(default_factory=dict)
    multi_use_acknowledgement: bool = False
    lifetime_campaign_acknowledgement: bool = False
    publish: bool = False
    reason: str | None = Field(None, max_length=240)

    @model_validator(mode="after")
    def _validate_lifetime_and_expiry_fields(self) -> "AdminInviteCampaignCreateRequest":
        _normalize_duration_fields(self, "grant_duration_mode", "grant_duration_days")
        _normalize_duration_fields(self, "child_grant_duration_mode", "child_grant_duration_days")
        _normalize_expiry_fields(self, "root_invite_expiry_mode", "root_invite_expiry_days", "root_invite_expires_at")
        _normalize_expiry_fields(
            self,
            "child_invite_expiry_mode",
            "child_invite_expiry_days",
            "child_invite_expires_at",
        )
        _normalize_multi_use_fields(self, "root")
        _normalize_multi_use_fields(self, "child")
        return self


class AdminInviteCampaignVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    campaign_id: UUID
    version: int
    status: str
    grant_mode: str
    grant_plan_id: UUID | None = None
    grant_duration_mode: str = "fixed_days"
    grant_duration_days: int | None = None
    grant_device_limit_override: int | None = None
    root_invite_expiry_mode: str = "relative"
    root_invite_expiry_days: int | None = None
    root_invite_expires_at: datetime | None = None
    grant_snapshot: dict[str, Any]
    child_invite_count: int
    child_invite_free_days: int
    child_invite_expiry_days: int | None = None
    child_invite_expiry_mode: str = "relative"
    child_invite_expires_at: datetime | None = None
    root_usage_mode: InviteCodeUsageMode = "single_use"
    root_max_redemptions: int | None = None
    root_per_user_redemption_cap: int = 1
    child_usage_mode: InviteCodeUsageMode = "single_use"
    child_max_redemptions: int | None = None
    child_per_user_redemption_cap: int = 1
    multi_use_policy: dict[str, Any]
    child_grant_plan_id: UUID | None = None
    child_grant_duration_mode: str = "fixed_days"
    child_grant_duration_days: int | None = None
    child_grant_device_limit_override: int | None = None
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
    grant_duration_mode: InviteAccessDurationMode = "fixed_days"
    grant_duration_days: int | None = Field(365, ge=1, le=3_660)
    grant_device_limit_override: int | None = Field(None, ge=1, le=200)
    root_invite_expiry_mode: InviteCodeExpiryMode = "relative"
    root_invite_expiry_days: int | None = Field(30, ge=1, le=3_660)
    root_invite_expires_at: datetime | None = None
    root_usage_mode: InviteCodeUsageMode = "single_use"
    root_max_redemptions: int | None = Field(1, ge=1, le=1_000_000)
    root_per_user_redemption_cap: int = Field(1, ge=1, le=1)
    child_invite_count: int = Field(10, ge=0, le=100)
    child_invite_free_days: int = Field(365, ge=0, le=3_660)
    child_invite_expiry_mode: InviteCodeExpiryMode = "relative"
    child_invite_expiry_days: int | None = Field(30, ge=1, le=3_660)
    child_invite_expires_at: datetime | None = None
    child_usage_mode: InviteCodeUsageMode = "single_use"
    child_max_redemptions: int | None = Field(1, ge=1, le=1_000_000)
    child_per_user_redemption_cap: int = Field(1, ge=1, le=1)
    child_grant_plan_id: UUID | None = None
    child_grant_plan_code: str | None = Field("premium_smart_ru", max_length=80)
    child_grant_duration_mode: InviteAccessDurationMode = "fixed_days"
    child_grant_duration_days: int | None = Field(365, ge=1, le=3_660)
    child_grant_device_limit_override: int | None = Field(None, ge=1, le=200)
    max_generation_depth: int = Field(5, ge=0, le=12)
    require_no_active_access: bool = True
    block_self_redemption: bool = True
    allowed_surfaces: list[str] = Field(default_factory=lambda: ["web", "miniapp", "telegram_bot"])
    risk_policy: dict[str, Any] = Field(default_factory=dict)
    export_policy: dict[str, Any] = Field(default_factory=lambda: {"raw_export_enabled": True})
    notification_policy: dict[str, Any] = Field(default_factory=dict)
    caps: dict[str, Any] = Field(default_factory=dict)
    multi_use_policy: dict[str, Any] = Field(default_factory=dict)
    multi_use_acknowledgement: bool = False
    lifetime_campaign_acknowledgement: bool = False
    reason: str | None = Field(None, max_length=240)

    @model_validator(mode="after")
    def _validate_lifetime_and_expiry_fields(self) -> "AdminInviteCampaignVersionCreateRequest":
        _normalize_duration_fields(self, "grant_duration_mode", "grant_duration_days")
        _normalize_duration_fields(self, "child_grant_duration_mode", "child_grant_duration_days")
        _normalize_expiry_fields(self, "root_invite_expiry_mode", "root_invite_expiry_days", "root_invite_expires_at")
        _normalize_expiry_fields(
            self,
            "child_invite_expiry_mode",
            "child_invite_expiry_days",
            "child_invite_expires_at",
        )
        _normalize_multi_use_fields(self, "root")
        _normalize_multi_use_fields(self, "child")
        return self


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
    expiry_mode: AdminInviteBatchExpiryMode = "campaign_default"
    expires_at: datetime | None = None
    expiry_days: int | None = Field(None, ge=1, le=3_660)
    usage_mode: AdminInviteBatchUsageMode = "campaign_default"
    max_redemptions_per_code: int | None = Field(None, ge=1, le=1_000_000)
    per_user_redemption_cap: int | None = Field(None, ge=1, le=1)
    reason: str = Field(..., min_length=3, max_length=240)

    @model_validator(mode="after")
    def _validate_batch_expiry(self) -> "AdminInviteCampaignBatchCreateRequest":
        if self.expiry_mode == "relative":
            if self.expiry_days is None:
                raise ValueError("expiry_days is required for relative invite expiry")
            self.expires_at = None
        elif self.expiry_mode == "absolute":
            if self.expires_at is None:
                raise ValueError("expires_at is required for absolute invite expiry")
            self.expiry_days = None
        elif self.expiry_mode in {"none", "campaign_default"}:
            self.expiry_days = None
            self.expires_at = None
        if self.usage_mode == "single_use":
            self.max_redemptions_per_code = 1
        if self.per_user_redemption_cap not in {None, 1}:
            raise ValueError("per_user_redemption_cap greater than 1 is not enabled for invite codes")
        return self


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
    usage_mode_snapshot: InviteCodeUsageMode = "single_use"
    redemption_sequence: int | None = None
    code_redemptions_count_after: int | None = None
    device_key_hash: str | None = None
    client_ip_hash: str | None = None
    user_agent_hash: str | None = None
    child_batch_id: UUID | None = None
    child_issued_count: int = 0
    status: str
    blocked_reason: str | None = None
    risk_decision: dict[str, Any]
    grant_snapshot: dict[str, Any]
    redeemed_at: datetime | None = None
    reversed_at: datetime | None = None
    created_at: datetime


class AdminInviteRedemptionReverseRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=240)
    cascade_mode: Literal["none", "unused_child_invites", "all_descendants"] = "unused_child_invites"
    confirm_descendant_reversal: bool = False

    @model_validator(mode="after")
    def _validate_descendant_confirmation(self) -> "AdminInviteRedemptionReverseRequest":
        if self.cascade_mode == "all_descendants" and not self.confirm_descendant_reversal:
            raise ValueError("confirm_descendant_reversal is required for all_descendants")
        return self


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
    grant_duration_mode: str | None = None
    grant_device_limit_override: int | None = None
    child_batch_id: UUID | None = None
    granted_plan_id: UUID | None = None
    granted_plan_code: str | None = None
    grant_lifetime: bool = False
    child_invite_count: int = 0
    child_invite_expiry_mode: str | None = None
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


def _normalize_duration_fields(model: BaseModel, mode_field: str, days_field: str) -> None:
    mode = getattr(model, mode_field)
    days = getattr(model, days_field)
    if mode == "lifetime":
        setattr(model, days_field, None)
        return
    if days is None:
        raise ValueError(f"{days_field} is required for fixed_days duration")


def _normalize_expiry_fields(model: BaseModel, mode_field: str, days_field: str, expires_field: str) -> None:
    mode = getattr(model, mode_field)
    if mode == "none":
        setattr(model, days_field, None)
        setattr(model, expires_field, None)
        return
    if mode == "absolute":
        if getattr(model, expires_field) is None:
            raise ValueError(f"{expires_field} is required for absolute invite expiry")
        setattr(model, days_field, None)
        return
    if getattr(model, days_field) is None:
        raise ValueError(f"{days_field} is required for relative invite expiry")
    setattr(model, expires_field, None)


def _normalize_multi_use_fields(model: BaseModel, prefix: Literal["root", "child"]) -> None:
    mode_field = f"{prefix}_usage_mode"
    max_field = f"{prefix}_max_redemptions"
    cap_field = f"{prefix}_per_user_redemption_cap"
    mode = getattr(model, mode_field)
    per_user_cap = getattr(model, cap_field)
    if per_user_cap != 1:
        raise ValueError(f"{cap_field} greater than 1 is not enabled for invite codes")
    if mode == "single_use":
        setattr(model, max_field, 1)
        return

    max_redemptions = getattr(model, max_field)
    if not getattr(model, "multi_use_acknowledgement", False):
        raise ValueError("multi_use_acknowledgement is required for multi_use invite codes")
    if max_redemptions is None:
        setattr(model, max_field, 1_000_000)
        max_redemptions = 1_000_000
        policy = dict(getattr(model, "multi_use_policy", {}) or {})
        policy.setdefault("cap_mode", "practically_unlimited")
        policy.setdefault("technical_hard_cap", max_redemptions)
        policy_field = "multi_use_policy"
        setattr(model, policy_field, policy)
    if int(max_redemptions) <= 1:
        raise ValueError(f"{max_field} must be greater than 1 for multi_use invite codes")

    risk_policy = dict(getattr(model, "risk_policy", {}) or {})
    max_per_device = _positive_int_or_none(risk_policy.get("max_redemptions_per_device"))
    max_per_ip_window = _positive_int_or_none(risk_policy.get("max_redemptions_per_ip_window"))
    velocity_window_hours = _positive_int_or_none(risk_policy.get("velocity_window_hours"))
    if max_per_device is None or max_per_device > 1:
        raise ValueError("multi_use invite codes require max_redemptions_per_device <= 1")
    if max_per_ip_window is None or max_per_ip_window > 3:
        raise ValueError("multi_use invite codes require max_redemptions_per_ip_window <= 3")
    if velocity_window_hours is None or velocity_window_hours > 24:
        raise ValueError("multi_use invite codes require velocity_window_hours <= 24")
    if risk_policy.get("deny_disposable_email") is not True:
        raise ValueError("multi_use invite codes require deny_disposable_email=true")
    if risk_policy.get("deny_known_abuse_subject") is not True:
        raise ValueError("multi_use invite codes require deny_known_abuse_subject=true")


def _positive_int_or_none(value: object) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = int(value)
        except ValueError:
            return None
    else:
        return None
    return parsed if parsed > 0 else None


class AdminInviteTreeRootListResponse(BaseModel):
    items: list[AdminInviteTreeRootResponse]
    total: int
    offset: int
    limit: int
