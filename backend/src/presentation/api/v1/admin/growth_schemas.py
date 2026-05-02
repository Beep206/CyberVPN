"""Admin schemas for growth-side mobile user analytics."""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.domain.enums import (
    GrowthCodeActionContext,
    GrowthCodeRejectReason,
    GrowthCodeResolutionStatus,
    GrowthCodeType,
    GrowthCodeWrongContextTarget,
)


class AdminGrowthUserSummary(BaseModel):
    id: UUID
    email: str
    username: str | None
    telegram_username: str | None
    referral_code: str | None
    is_partner: bool


class AdminReferralCommissionRecord(BaseModel):
    id: UUID
    referrer_user_id: UUID
    referred_user_id: UUID | None = None
    payment_id: UUID | None = None
    commission_rate: float
    base_amount: float
    commission_amount: float
    currency: str
    reward_status: str | None = None
    hold_until: datetime | None = None
    available_at: datetime | None = None
    reversed_at: datetime | None = None
    source_model: str = "legacy_commission"
    created_at: datetime
    referrer: AdminGrowthUserSummary | None = None
    referred_user: AdminGrowthUserSummary | None = None


class AdminReferralReferrerRow(BaseModel):
    user: AdminGrowthUserSummary
    commission_count: int
    referred_users: int
    total_earned: float
    last_commission_at: datetime | None


class AdminReferralOverviewResponse(BaseModel):
    total_commissions: int
    total_earned: float
    unique_referrers: int
    unique_referred_users: int
    recent_commissions: list[AdminReferralCommissionRecord]
    top_referrers: list[AdminReferralReferrerRow]


class AdminReferralUserDetailResponse(BaseModel):
    user: AdminGrowthUserSummary
    referred_by_user_id: UUID | None
    commission_count: int
    referred_users: int
    total_earned: float
    recent_commissions: list[AdminReferralCommissionRecord]


class AdminPartnerCodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    markup_pct: float
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AdminPartnerEarningResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    client_user_id: UUID
    payment_id: UUID
    base_price: float
    markup_amount: float
    commission_pct: float
    commission_amount: float
    total_earning: float
    currency: str
    created_at: datetime


class AdminPartnerListItemResponse(BaseModel):
    user: AdminGrowthUserSummary
    promoted_at: datetime | None
    code_count: int
    active_code_count: int
    total_clients: int
    total_earned: float
    last_activity_at: datetime | None


class AdminPartnersListResponse(BaseModel):
    items: list[AdminPartnerListItemResponse]
    total: int
    offset: int
    limit: int


class AdminPartnerDetailResponse(AdminPartnerListItemResponse):
    codes: list[AdminPartnerCodeResponse]
    recent_earnings: list[AdminPartnerEarningResponse]


class AdminGrowthCodeLookupRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=64)
    action_context: GrowthCodeActionContext = GrowthCodeActionContext.CHECKOUT
    lookup_user_id: UUID | None = None
    storefront_key: str | None = Field(None, min_length=1, max_length=50)
    plan_id: UUID | None = None
    amount: float | None = Field(None, ge=0)
    channel: str = Field("web", min_length=1, max_length=30)
    existing_partner_code_present: bool = False
    existing_promo_present: bool = False


class AdminGrowthCodeLookupResponse(BaseModel):
    accepted: bool
    code_type: GrowthCodeType | None = None
    action_context: GrowthCodeActionContext
    result: GrowthCodeResolutionStatus
    reject_reason: GrowthCodeRejectReason | None = None
    conflict_code: str | None = None
    wrong_context_target: GrowthCodeWrongContextTarget | None = None
    issuer_type: str | None = None
    owner_type: str | None = None
    resolved_code_id: UUID | None = None
    growth_code_id: UUID | None = None
    promo_code_id: UUID | None = None
    partner_code_id: UUID | None = None
    user_message_key: str
    lifecycle_summary: dict[str, int] = Field(default_factory=dict)
    issuances: list[dict[str, str | int | float | None]] = Field(default_factory=list)
    touchpoints: list[dict[str, str | int | float | None]] = Field(default_factory=list)
    signup_attributions: list[dict[str, str | int | float | None]] = Field(default_factory=list)
    redemptions: list[dict[str, str | int | float | None]] = Field(default_factory=list)
    rewards: list[dict[str, str | int | float | None]] = Field(default_factory=list)
    resolution_events: list[dict[str, str | int | float | None]] = Field(default_factory=list)


class AdminGrowthSignalCountResponse(BaseModel):
    key: str
    count: int


class AdminGrowthLifecycleEventResponse(BaseModel):
    id: UUID
    event_name: str
    event_family: str
    aggregate_type: str
    aggregate_id: str
    occurred_at: datetime
    event_status: str


class AdminGrowthSignalsOverviewResponse(BaseModel):
    total_codes: int
    active_codes: int
    total_redemptions: int
    active_reservations: int
    blocked_reward_count: int
    available_referral_credit_usd: float
    code_status_breakdown: list[AdminGrowthSignalCountResponse]
    resolution_result_breakdown: list[AdminGrowthSignalCountResponse]
    rejection_reason_breakdown: list[AdminGrowthSignalCountResponse]
    redemption_breakdown: list[AdminGrowthSignalCountResponse]
    reward_status_breakdown: list[AdminGrowthSignalCountResponse]
    reward_type_breakdown: list[AdminGrowthSignalCountResponse]
    recent_lifecycle_events: list[AdminGrowthLifecycleEventResponse]


class AdminGrowthReportingFamilySummaryResponse(BaseModel):
    family: str
    issued_total: int
    resolution_attempts_total: int
    resolution_accepted_total: int
    resolution_rejected_total: int
    redemption_total: int
    reservations_reserved_total: int
    reservations_consumed_total: int
    reservations_released_total: int
    reservations_expired_total: int
    rewards_created_total: int
    rewards_available_total: int
    rewards_reversed_total: int
    reward_created_amount_usd: float
    reward_available_amount_usd: float
    reward_reversed_amount_usd: float


class AdminGrowthReportingDailyPointResponse(AdminGrowthReportingFamilySummaryResponse):
    report_date: date


class AdminGrowthReportingRefreshRunResponse(BaseModel):
    id: str
    trigger_kind: str
    refresh_status: str
    requested_window_days: int
    window_start: date
    window_end: date
    latest_rollup_date: date | None = None
    rows_written: int
    families_updated: list[str] = Field(default_factory=list)
    error_message: str | None = None
    started_at: datetime
    finished_at: datetime
    refreshed_at: datetime | None = None


class AdminGrowthReportingHealthResponse(BaseModel):
    freshness_status: str
    stale_reason: str | None = None
    refresh_age_seconds: int | None = None
    expected_refresh_interval_seconds: int
    stale_after_seconds: int
    auto_refresh_enabled: bool
    latest_attempt_at: datetime | None = None
    latest_success_at: datetime | None = None
    latest_failure_at: datetime | None = None
    latest_failure_message: str | None = None
    latest_run: AdminGrowthReportingRefreshRunResponse | None = None


class AdminGrowthReportingExecutiveSummaryResponse(BaseModel):
    total_issued: int
    total_redemptions: int
    total_reward_available_usd: float
    total_reward_reversed_usd: float
    resolution_acceptance_rate_pct: float
    dominant_family: str | None = None
    highlights: list[str] = Field(default_factory=list)


class AdminGrowthReportingOverviewResponse(BaseModel):
    window_start: date
    window_end: date
    latest_rollup_date: date | None = None
    refreshed_at: datetime | None = None
    family_summaries: list[AdminGrowthReportingFamilySummaryResponse]
    daily_points: list[AdminGrowthReportingDailyPointResponse]
    totals: AdminGrowthReportingFamilySummaryResponse
    health: AdminGrowthReportingHealthResponse
    executive_summary: AdminGrowthReportingExecutiveSummaryResponse
    coverage_notes: list[str] = Field(default_factory=list)


class AdminGrowthReportingRefreshResponse(BaseModel):
    trigger_kind: str
    window_start: date
    window_end: date
    latest_rollup_date: date | None = None
    refreshed_at: datetime
    rows_written: int
    families_updated: list[str] = Field(default_factory=list)
    coverage_notes: list[str] = Field(default_factory=list)


class AdminGrowthReportingRecipientPolicyResponse(BaseModel):
    template_key: str
    template_locale: str
    email_subject_prefix: str | None = None
    title_override: str | None = None
    recipient_domain_policy: str
    allowed_recipient_domains: list[str] = Field(default_factory=list)
    suppressed_until: datetime | None = None
    suppression_reason_code: str | None = None


class AdminGrowthReportingGovernanceCoverageCountResponse(BaseModel):
    coverage_state: str
    count: int


class AdminGrowthReportingGovernanceFollowupResponse(BaseModel):
    status: str
    reason_code: str | None = None
    opened_at: datetime | None = None
    due_at: datetime | None = None
    last_notified_at: datetime | None = None
    resolved_at: datetime | None = None
    resolution_code: str | None = None
    is_overdue: bool = False
    action_required: bool = False


class AdminGrowthReportingGovernanceFollowupQueueItemResponse(BaseModel):
    subscription_id: str
    recipient_email: str
    audience_key: str
    health_status: str
    followup: AdminGrowthReportingGovernanceFollowupResponse
    next_delivery_at: datetime
    latest_delivery_status: str | None = None
    latest_delivery_reason: str | None = None


class AdminGrowthReportingGovernanceDecisionResponse(BaseModel):
    delivery_id: str
    subscription_id: str
    recipient_email: str
    audience_key: str
    template_key: str
    decision_kind: str
    status_reason: str
    created_at: datetime
    planned_at: datetime
    window_start: date
    window_end: date
    can_export_artifact: bool = False
    summary: str


class AdminGrowthReportingGovernanceAuditEventResponse(BaseModel):
    id: str
    action: str
    entity_id: str | None = None
    actor_label: str
    reason_code: str | None = None
    changed_fields: list[str] = Field(default_factory=list)
    created_at: datetime


class AdminGrowthReportingGovernanceOverviewResponse(BaseModel):
    generated_at: datetime
    active_subscription_count: int
    paused_subscription_count: int
    coverage_gap_count: int
    followup_open_count: int
    followup_overdue_count: int
    coverage_counts: list[AdminGrowthReportingGovernanceCoverageCountResponse] = Field(default_factory=list)
    followup_queue: list[AdminGrowthReportingGovernanceFollowupQueueItemResponse] = Field(default_factory=list)
    recent_decisions: list[AdminGrowthReportingGovernanceDecisionResponse] = Field(default_factory=list)
    recent_audit_events: list[AdminGrowthReportingGovernanceAuditEventResponse] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class AdminGrowthReportingSubscriptionResponse(BaseModel):
    id: str
    recipient_email: str
    recipient_name: str | None = None
    audience_key: str
    delivery_channel: str
    cadence: str
    report_window_days: int
    subscription_status: str
    next_delivery_at: datetime
    last_delivery_attempt_at: datetime | None = None
    last_success_at: datetime | None = None
    latest_delivery_status: str | None = None
    latest_delivery_reason: str | None = None
    health_status: str
    policy: AdminGrowthReportingRecipientPolicyResponse
    followup: AdminGrowthReportingGovernanceFollowupResponse


class AdminGrowthReportingDeliveryResponse(BaseModel):
    id: str
    subscription_id: str
    recipient_email: str
    recipient_name: str | None = None
    audience_key: str
    delivery_channel: str
    cadence: str
    report_window_days: int
    template_key: str
    template_locale: str
    subject_line: str
    title_line: str
    delivery_status: str
    status_reason: str | None = None
    freshness_status: str
    artifact_checksum: str | None = None
    provider_name: str | None = None
    provider_message_id: str | None = None
    failure_message: str | None = None
    window_start: date
    window_end: date
    planned_at: datetime
    started_at: datetime | None = None
    delivered_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    can_export_artifact: bool = False
    policy: AdminGrowthReportingRecipientPolicyResponse


class AdminGrowthReportingRecipientPolicyRequest(BaseModel):
    template_key: str | None = Field(None, min_length=2, max_length=48)
    template_locale: str = Field("en-EN", min_length=2, max_length=16)
    email_subject_prefix: str | None = Field(None, max_length=120)
    title_override: str | None = Field(None, max_length=160)
    recipient_domain_policy: str = Field("allow_any", min_length=2, max_length=24)
    allowed_recipient_domains: list[str] = Field(default_factory=list, max_length=20)
    suppressed_until: datetime | None = None
    suppression_reason_code: str | None = Field(None, max_length=80)


class AdminGrowthReportingSubscriptionsResponse(BaseModel):
    items: list[AdminGrowthReportingSubscriptionResponse]
    total: int
    overdue_count: int
    active_count: int
    retention_rollup_days: int
    retention_refresh_run_days: int
    retention_delivery_days: int


class AdminGrowthReportingDeliveriesResponse(BaseModel):
    items: list[AdminGrowthReportingDeliveryResponse]
    total: int
    failed_count: int


class AdminCreateGrowthReportingSubscriptionRequest(BaseModel):
    recipient_email: str = Field(..., min_length=3, max_length=320)
    recipient_name: str | None = Field(None, max_length=160)
    audience_key: str = Field(..., min_length=2, max_length=32)
    cadence: str = Field(..., min_length=5, max_length=20)
    report_window_days: int = Field(30, ge=1, le=90)
    policy: AdminGrowthReportingRecipientPolicyRequest = Field(
        default_factory=AdminGrowthReportingRecipientPolicyRequest
    )


class AdminUpdateGrowthReportingSubscriptionRequest(BaseModel):
    recipient_email: str = Field(..., min_length=3, max_length=320)
    recipient_name: str | None = Field(None, max_length=160)
    audience_key: str = Field(..., min_length=2, max_length=32)
    cadence: str = Field(..., min_length=5, max_length=20)
    report_window_days: int = Field(30, ge=1, le=90)
    policy: AdminGrowthReportingRecipientPolicyRequest = Field(
        default_factory=AdminGrowthReportingRecipientPolicyRequest
    )
    reason_code: str | None = Field(None, min_length=2, max_length=120)


class AdminUpdateGrowthReportingSubscriptionStatusRequest(BaseModel):
    reason_code: str | None = Field(None, min_length=2, max_length=120)


class AdminUpdateGrowthReportingGovernanceFollowupRequest(BaseModel):
    reason_code: str | None = Field(None, min_length=2, max_length=120)


class AdminGrowthReportingDeliveryArtifactExportResponse(BaseModel):
    export_kind: str
    filename: str
    exported_at: datetime
    delivery: AdminGrowthReportingDeliveryResponse
    payload: dict[str, Any] = Field(default_factory=dict)


class AdminGrowthReportingGovernanceExportResponse(BaseModel):
    export_kind: str
    filename: str
    exported_at: datetime
    overview: AdminGrowthReportingGovernanceOverviewResponse
    payload: dict[str, Any] = Field(default_factory=dict)


class InternalGrowthReportingDeliveryDispatchResponse(BaseModel):
    delivery_id: str
    recipient_email: str
    recipient_name: str | None = None
    audience_key: str
    delivery_channel: str
    subject: str
    title: str
    message: str
    notes: list[str] = Field(default_factory=list)
    locale: str


class InternalClaimGrowthReportingDeliveriesResponse(BaseModel):
    deliveries: list[InternalGrowthReportingDeliveryDispatchResponse] = Field(default_factory=list)
    claimed_count: int
    skipped_count: int
    overdue_count: int


class InternalCompleteGrowthReportingDeliveryRequest(BaseModel):
    delivery_status: str = Field(..., min_length=4, max_length=20)
    provider_name: str | None = Field(None, max_length=40)
    provider_message_id: str | None = Field(None, max_length=255)
    failure_message: str | None = Field(None, max_length=1000)


class InternalCleanupGrowthReportingArtifactsResponse(BaseModel):
    rollups_deleted: int
    refresh_runs_deleted: int
    deliveries_deleted: int
    executed_at: datetime


class InternalProcessGrowthReportingGovernanceFollowupsResponse(BaseModel):
    processed_at: datetime
    scanned_count: int
    opened_count: int
    reopened_count: int
    auto_resolved_count: int
    reminded_count: int
    open_count: int
    overdue_count: int


class AdminGrowthAbuseSignalResponse(BaseModel):
    signal_key: str
    signal_type: str
    severity: str
    code_type: str | None = None
    reason_code: str
    count: int
    unique_users: int
    latest_event_at: datetime
    review_hint: str
    growth_code_id: str | None = None
    reward_allocation_id: str | None = None
    beneficiary_user_id: str | None = None
    source_redemption_id: str | None = None


class AdminGrowthAbuseSignalsResponse(BaseModel):
    items: list[AdminGrowthAbuseSignalResponse]
    total: int


class AdminGrowthNotificationDeliveryResponse(BaseModel):
    id: UUID
    mobile_user_id: UUID
    user: AdminGrowthUserSummary | None = None
    notification_key: str
    notification_kind: str
    delivery_channel: str
    delivery_status: str
    status_reason: str | None = None
    title: str
    message: str
    route_slug: str | None = None
    notes: list[str] = Field(default_factory=list)
    source_kind: str | None = None
    source_id: str | None = None
    notification_queue_id: UUID | None = None
    queue_status: str | None = None
    queue_error_message: str | None = None
    created_by_admin_user_id: UUID | None = None
    planned_at: datetime
    delivered_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    can_resend: bool = False
    can_pause: bool = False
    can_revoke: bool = False
    can_resolve: bool = False


class AdminListGrowthNotificationDeliveriesResponse(BaseModel):
    items: list[AdminGrowthNotificationDeliveryResponse]
    total: int
    offset: int
    limit: int


class AdminGrowthNotificationQueueSnapshotResponse(BaseModel):
    id: UUID
    status: str
    attempts: int
    scheduled_at: datetime
    sent_at: datetime | None = None
    error_message: str | None = None


class AdminGrowthNotificationDeliveryEventResponse(BaseModel):
    id: UUID
    event_type: str
    delivery_status: str
    reason_code: str | None = None
    event_payload: dict[str, Any] = Field(default_factory=dict)
    event_note: str | None = None
    notification_queue_id: UUID | None = None
    created_by_admin_user_id: UUID | None = None
    occurred_at: datetime
    created_at: datetime


class AdminGrowthNotificationSourceSummaryResponse(BaseModel):
    source_kind: str
    source_id: str | None = None
    source_label: str | None = None
    source_status: str | None = None
    owner_user_id: str | None = None
    beneficiary_user_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AdminGrowthNotificationDeliveryDetailResponse(BaseModel):
    delivery: AdminGrowthNotificationDeliveryResponse
    sibling_deliveries: list[AdminGrowthNotificationDeliveryResponse]
    event_timeline: list[AdminGrowthNotificationDeliveryEventResponse]
    queue_snapshot: AdminGrowthNotificationQueueSnapshotResponse | None = None
    source_summary: AdminGrowthNotificationSourceSummaryResponse | None = None
    lifecycle_events: list[AdminGrowthLifecycleEventResponse] = Field(default_factory=list)
    troubleshooting_state: str
    customer_message_key: str
    support_summary: str


class AdminGrowthNotificationDeliveryExportResponse(BaseModel):
    export_kind: str
    filename: str
    exported_at: datetime
    delivery_id: UUID
    payload: AdminGrowthNotificationDeliveryDetailResponse


class AdminGrowthNotificationDeliveryActionRequest(BaseModel):
    reason_code: str | None = Field(None, max_length=120)


class AdminManualGrowthNotificationRequest(BaseModel):
    mobile_user_id: UUID
    title: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1, max_length=1000)
    route_slug: str = Field("/referral", min_length=1, max_length=200)
    locale: str = Field("en-EN", min_length=2, max_length=16)
    notes: list[str] = Field(default_factory=list, max_length=6)
    channels: list[str] = Field(default_factory=lambda: ["in_app", "email", "telegram"])


class AdminManualGrowthNotificationResponse(BaseModel):
    deliveries: list[AdminGrowthNotificationDeliveryResponse]


class AdminGiftCodeListItemResponse(BaseModel):
    id: UUID
    masked_code: str
    raw_code: str | None = None
    batch_id: UUID | None = None
    status: str
    issuer_type: str
    source_type: str | None = None
    owner_user_id: UUID | None = None
    issued_by_admin_id: UUID | None = None
    plan_family: str | None = None
    duration_days: int | None = None
    recipient_hint: str | None = None
    gift_message: str | None = None
    expires_at: datetime | None = None
    created_at: datetime
    redeemed_at: datetime | None = None
    redeemed_by_user_id: UUID | None = None
    source_order_id: UUID | None = None
    source_payment_id: UUID | None = None


class AdminListGiftCodesResponse(BaseModel):
    items: list[AdminGiftCodeListItemResponse]
    total: int
    offset: int
    limit: int


class AdminIssueGiftCodeRequest(BaseModel):
    owner_user_id: UUID
    plan_id: UUID
    recipient_hint: str | None = Field(None, max_length=160)
    gift_message: str | None = Field(None, max_length=500)
    reason_code: str | None = Field(None, max_length=80)
    admin_note: str | None = Field(None, max_length=1000)


class AdminIssueGiftCodeResponse(BaseModel):
    gift_code: AdminGiftCodeListItemResponse


class AdminIssueGiftCodeBatchRequest(BaseModel):
    owner_user_id: UUID
    plan_id: UUID
    count: int = Field(1, ge=1, le=100)
    recipient_hint: str | None = Field(None, max_length=160)
    gift_message: str | None = Field(None, max_length=500)
    reason_code: str | None = Field(None, max_length=80)
    admin_note: str | None = Field(None, max_length=1000)


class AdminIssueGiftCodeBatchResponse(BaseModel):
    batch_id: UUID
    issued_count: int
    gift_codes: list[AdminGiftCodeListItemResponse]
