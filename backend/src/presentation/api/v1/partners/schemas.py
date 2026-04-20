"""Pydantic v2 schemas for the partners API."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.domain.enums import AdminRole
from src.domain.enums import TrafficDeclarationKind


class CreatePartnerCodeRequest(BaseModel):
    code: str = ""
    markup_pct: float = 0


class UpdateMarkupRequest(BaseModel):
    markup_pct: float


class BindPartnerRequest(BaseModel):
    partner_code: str


class PartnerCodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    markup_pct: float
    is_active: bool
    created_at: datetime


class PartnerDashboardResponse(BaseModel):
    total_clients: int
    total_earned: float
    current_tier: dict | None
    codes: list[dict]


class PartnerEarningResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    client_user_id: UUID
    base_price: float
    markup_amount: float
    commission_amount: float
    total_earning: float
    created_at: datetime


class PromotePartnerRequest(BaseModel):
    user_id: UUID


class CreatePartnerWorkspaceRequest(BaseModel):
    display_name: str
    account_key: str | None = None
    legacy_owner_user_id: UUID | None = None
    owner_admin_user_id: UUID | None = None


class AddPartnerWorkspaceMemberRequest(BaseModel):
    admin_user_id: UUID | None = None
    operator_lookup: str | None = Field(default=None, min_length=1, max_length=255)
    role_key: str

    @model_validator(mode="after")
    def validate_member_target(self) -> "AddPartnerWorkspaceMemberRequest":
        if self.admin_user_id is None and self.operator_lookup is None:
            raise ValueError("Either admin_user_id or operator_lookup is required")
        return self


class UpdatePartnerWorkspaceMemberRequest(BaseModel):
    role_key: str | None = Field(default=None, min_length=1, max_length=50)
    membership_status: str | None = Field(default=None, min_length=1, max_length=20)


class PartnerWorkspaceRoleResponse(BaseModel):
    id: UUID
    role_key: str
    display_name: str
    description: str
    permission_keys: list[str]
    is_system: bool


class PartnerWorkspaceMemberResponse(BaseModel):
    id: UUID
    admin_user_id: UUID
    operator_login: str | None = None
    operator_email: str | None = None
    operator_display_name: str | None = None
    role_id: UUID
    role_key: str
    role_display_name: str
    membership_status: str
    permission_keys: list[str]
    invited_by_admin_user_id: UUID | None
    created_at: datetime
    updated_at: datetime


class PartnerWorkspaceResponse(BaseModel):
    id: UUID
    account_key: str
    display_name: str
    status: str
    legacy_owner_user_id: UUID | None
    created_by_admin_user_id: UUID | None
    code_count: int
    active_code_count: int
    total_clients: int
    total_earned: float
    last_activity_at: datetime | None
    current_role_key: str | None = None
    current_permission_keys: list[str] = Field(default_factory=list)
    members: list[PartnerWorkspaceMemberResponse]


class PartnerWorkspaceOrganizationProfileResponse(BaseModel):
    partner_account_id: UUID
    workspace_name: str
    website: str = ""
    country: str = ""
    operating_regions: str = ""
    languages: str = ""
    primary_lane: str | None = None
    contact_name: str = ""
    contact_email: str = ""
    support_contact: str = ""
    technical_contact: str = ""
    finance_contact: str = ""
    business_description: str = ""
    acquisition_channels: str = ""
    updated_at: datetime | None = None


class UpdatePartnerWorkspaceOrganizationProfileRequest(BaseModel):
    workspace_name: str | None = Field(default=None, min_length=1, max_length=120)
    website: str | None = Field(default=None, max_length=255)
    country: str | None = Field(default=None, max_length=120)
    operating_regions: str | None = None
    languages: str | None = None
    contact_name: str | None = Field(default=None, max_length=120)
    contact_email: str | None = Field(default=None, max_length=255)
    support_contact: str | None = Field(default=None, max_length=255)
    technical_contact: str | None = Field(default=None, max_length=255)
    finance_contact: str | None = Field(default=None, max_length=255)
    business_description: str | None = None
    acquisition_channels: str | None = None


class PartnerWorkspaceSettingsResponse(BaseModel):
    partner_account_id: UUID
    operator_email: str | None = None
    operator_display_name: str | None = None
    operator_role: str | None = None
    is_email_verified: bool
    preferred_language: str
    preferred_currency: str
    workspace_security_alerts: bool
    payout_status_emails: bool
    product_announcements: bool
    require_mfa_for_workspace: bool
    prefer_passkeys: bool
    reviewed_active_sessions: bool
    updated_at: datetime | None = None


class UpdatePartnerWorkspaceSettingsRequest(BaseModel):
    preferred_language: str | None = Field(default=None, min_length=2, max_length=16)
    preferred_currency: str | None = Field(default=None, min_length=3, max_length=10)
    workspace_security_alerts: bool | None = None
    payout_status_emails: bool | None = None
    product_announcements: bool | None = None
    require_mfa_for_workspace: bool | None = None
    prefer_passkeys: bool | None = None
    reviewed_active_sessions: bool | None = None


class PartnerWorkspaceLegalDocumentResponse(BaseModel):
    id: str
    kind: str
    title: str
    version: str
    status: str
    accepted_at: datetime | None = None
    accepted_by_role_key: str | None = None
    notes: list[str] = Field(default_factory=list)


class PartnerSessionPrincipalResponse(BaseModel):
    id: UUID
    login: str
    email: str | None = None
    role: AdminRole
    is_active: bool
    is_email_verified: bool = False
    auth_realm_id: UUID | None = None
    auth_realm_key: str | None = None
    audience: str | None = None
    principal_type: str | None = None
    scope_family: str | None = None


class PartnerSessionBootstrapCounterResponse(BaseModel):
    open_review_requests: int = 0
    open_cases: int = 0
    unread_notifications: int = 0
    pending_tasks: int = 0


class PartnerSessionBootstrapPendingTaskResponse(BaseModel):
    id: str
    task_key: str
    tone: str
    route_slug: str | None = None
    source_kind: str | None = None
    source_id: str | None = None
    notes: list[str] = Field(default_factory=list)


class PartnerSessionBootstrapBlockedReasonResponse(BaseModel):
    code: str
    severity: str
    route_slug: str | None = None
    notes: list[str] = Field(default_factory=list)


class PartnerSessionBootstrapResponse(BaseModel):
    principal: PartnerSessionPrincipalResponse
    workspaces: list[PartnerWorkspaceResponse] = Field(default_factory=list)
    active_workspace_id: UUID | None = None
    active_workspace: PartnerWorkspaceResponse | None = None
    workspace_resolution: str = "none"
    programs: "PartnerWorkspaceProgramsResponse | None" = None
    release_ring: str
    finance_readiness: str
    compliance_readiness: str
    technical_readiness: str
    governance_state: str
    current_permission_keys: list[str] = Field(default_factory=list)
    counters: PartnerSessionBootstrapCounterResponse = Field(
        default_factory=PartnerSessionBootstrapCounterResponse
    )
    pending_tasks: list[PartnerSessionBootstrapPendingTaskResponse] = Field(default_factory=list)
    blocked_reasons: list[PartnerSessionBootstrapBlockedReasonResponse] = Field(default_factory=list)
    updated_at: datetime


class PartnerNotificationFeedItemResponse(BaseModel):
    id: str
    kind: str
    tone: str
    route_slug: str
    message: str
    notes: list[str] = Field(default_factory=list)
    action_required: bool = False
    unread: bool = True
    created_at: datetime
    source_kind: str | None = None
    source_id: str | None = None
    source_event_id: str | None = None
    source_event_kind: str | None = None


class PartnerNotificationCountersResponse(BaseModel):
    total_notifications: int = 0
    unread_notifications: int = 0
    action_required_notifications: int = 0


class PartnerNotificationReadStateResponse(BaseModel):
    notification_id: str
    unread: bool = False
    archived: bool = False
    read_at: datetime | None = None
    archived_at: datetime | None = None


class PartnerNotificationPreferencesResponse(BaseModel):
    email_security: bool = True
    email_marketing: bool = False
    partner_payout_status_emails: bool = True
    partner_application_updates: bool = True
    partner_case_messages: bool = True
    partner_compliance_alerts: bool = True
    partner_integration_alerts: bool = True


class PartnerNotificationPreferencesUpdateRequest(BaseModel):
    email_security: bool | None = None
    email_marketing: bool | None = None
    partner_payout_status_emails: bool | None = None
    partner_application_updates: bool | None = None
    partner_case_messages: bool | None = None
    partner_compliance_alerts: bool | None = None
    partner_integration_alerts: bool | None = None


class PartnerApplicationPayloadResponse(BaseModel):
    workspace_name: str = ""
    contact_name: str = ""
    contact_email: str = ""
    country: str = ""
    website: str = ""
    primary_lane: str = ""
    business_description: str = ""
    acquisition_channels: str = ""
    operating_regions: str = ""
    languages: str = ""
    support_contact: str = ""
    technical_contact: str = ""
    finance_contact: str = ""
    compliance_accepted: bool = False


class PartnerApplicationWorkspaceSummaryResponse(BaseModel):
    id: UUID
    account_key: str
    display_name: str
    status: str
    current_role_key: str | None = None
    current_permission_keys: list[str] = Field(default_factory=list)


class PartnerApplicationDraftResponse(BaseModel):
    id: UUID
    partner_account_id: UUID
    applicant_admin_user_id: UUID | None = None
    workspace: PartnerApplicationWorkspaceSummaryResponse
    draft_payload: PartnerApplicationPayloadResponse
    review_ready: bool
    submitted_at: datetime | None = None
    withdrawn_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class PartnerLaneApplicationResponse(BaseModel):
    id: UUID
    partner_account_id: UUID
    partner_application_draft_id: UUID
    lane_key: str
    status: str
    application_payload: dict[str, Any] = Field(default_factory=dict)
    submitted_at: datetime | None = None
    decided_at: datetime | None = None
    decision_reason_code: str | None = None
    decision_summary: str | None = None
    created_at: datetime
    updated_at: datetime


class PartnerApplicationAttachmentResponse(BaseModel):
    id: UUID
    partner_account_id: UUID
    partner_application_draft_id: UUID
    lane_application_id: UUID | None = None
    review_request_id: UUID | None = None
    attachment_type: str
    storage_key: str
    file_name: str | None = None
    attachment_metadata: dict[str, Any] = Field(default_factory=dict)
    uploaded_by_admin_user_id: UUID | None = None
    created_at: datetime


class PartnerApplicationReviewRequestDetailResponse(BaseModel):
    id: UUID
    partner_account_id: UUID
    partner_application_draft_id: UUID
    lane_application_id: UUID | None = None
    request_kind: str
    message: str
    required_fields: list[str] = Field(default_factory=list)
    required_attachments: list[str] = Field(default_factory=list)
    status: str
    requested_by_admin_user_id: UUID | None = None
    resolved_by_admin_user_id: UUID | None = None
    requested_at: datetime
    response_due_at: datetime | None = None
    responded_at: datetime | None = None
    resolved_at: datetime | None = None
    thread_events: list["PartnerWorkspaceThreadEventResponse"] = Field(default_factory=list)


class PartnerApplicationDraftDetailResponse(BaseModel):
    draft: PartnerApplicationDraftResponse
    lane_applications: list[PartnerLaneApplicationResponse] = Field(default_factory=list)
    review_requests: list[PartnerApplicationReviewRequestDetailResponse] = Field(default_factory=list)
    attachments: list[PartnerApplicationAttachmentResponse] = Field(default_factory=list)


class UpsertPartnerApplicationDraftRequest(BaseModel):
    draft_payload: dict[str, Any] = Field(default_factory=dict)
    review_ready: bool | None = None


class CreatePartnerApplicationAttachmentRequest(BaseModel):
    attachment_type: str = Field(..., min_length=1, max_length=40)
    storage_key: str = Field(..., min_length=1, max_length=255)
    file_name: str | None = Field(default=None, max_length=255)
    lane_application_id: UUID | None = None
    review_request_id: UUID | None = None
    attachment_metadata: dict[str, Any] = Field(default_factory=dict)


class CreatePartnerLaneApplicationRequest(BaseModel):
    lane_key: str = Field(..., min_length=1, max_length=40)
    application_payload: dict[str, Any] = Field(default_factory=dict)


class UpdatePartnerLaneApplicationRequest(BaseModel):
    application_payload: dict[str, Any] = Field(default_factory=dict)


class PartnerApplicationReviewDecisionRequest(BaseModel):
    reason_code: str = Field(..., min_length=1, max_length=80)
    reason_summary: str = Field(..., min_length=1, max_length=2000)


class RequestPartnerApplicationInfoRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    request_kind: str = Field(..., min_length=1, max_length=40)
    required_fields: list[str] = Field(default_factory=list)
    required_attachments: list[str] = Field(default_factory=list)
    lane_application_id: UUID | None = None
    response_due_at: datetime | None = None


class PartnerApplicationApplicantSummaryResponse(BaseModel):
    id: UUID
    login: str
    email: str | None = None
    is_email_verified: bool


class PartnerApplicationAdminSummaryResponse(BaseModel):
    workspace: PartnerApplicationWorkspaceSummaryResponse
    applicant: PartnerApplicationApplicantSummaryResponse | None = None
    primary_lane: str | None = None
    review_ready: bool
    submitted_at: datetime | None = None
    updated_at: datetime
    open_review_request_count: int = 0
    lane_statuses: list[str] = Field(default_factory=list)


class PartnerApplicationAdminDetailResponse(BaseModel):
    workspace: PartnerApplicationWorkspaceSummaryResponse
    applicant: PartnerApplicationApplicantSummaryResponse | None = None
    draft: PartnerApplicationDraftResponse
    lane_applications: list[PartnerLaneApplicationResponse] = Field(default_factory=list)
    review_requests: list[PartnerApplicationReviewRequestDetailResponse] = Field(default_factory=list)
    attachments: list[PartnerApplicationAttachmentResponse] = Field(default_factory=list)


class PartnerWorkspaceCodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    partner_account_id: UUID | None
    partner_user_id: UUID
    code: str
    markup_pct: float
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PartnerWorkspaceCampaignAssetResponse(BaseModel):
    id: str
    name: str
    channel: str
    status: str
    approval_owner: str
    updated_at: datetime
    notes: list[str] = Field(default_factory=list)


class PartnerWorkspacePayoutAccountResponse(BaseModel):
    id: UUID
    settlement_profile_id: UUID | None = None
    payout_rail: str
    display_label: str
    masked_destination: str
    destination_metadata: dict[str, Any] = Field(default_factory=dict)
    verification_status: str
    approval_status: str
    account_status: str
    is_default: bool
    verified_at: datetime | None = None
    approved_at: datetime | None = None
    suspended_at: datetime | None = None
    suspension_reason_code: str | None = None
    archived_at: datetime | None = None
    archive_reason_code: str | None = None
    created_at: datetime
    updated_at: datetime


class CreatePartnerWorkspacePayoutAccountRequest(BaseModel):
    payout_rail: str = Field(..., min_length=1, max_length=40)
    display_label: str = Field(..., min_length=1, max_length=120)
    destination_reference: str = Field(..., min_length=1, max_length=255)
    destination_metadata: dict[str, Any] = Field(default_factory=dict)
    settlement_profile_id: UUID | None = None
    make_default: bool = False


class PartnerWorkspacePayoutAccountEligibilityResponse(BaseModel):
    partner_payout_account_id: UUID
    partner_account_id: UUID
    eligible: bool
    reason_codes: list[str] = Field(default_factory=list)
    blocking_risk_review_ids: list[UUID] = Field(default_factory=list)
    active_reserve_ids: list[UUID] = Field(default_factory=list)
    checked_at: datetime


class PartnerWorkspacePayoutHistoryResponse(BaseModel):
    id: str
    instruction_id: UUID
    execution_id: UUID | None = None
    partner_statement_id: UUID
    partner_payout_account_id: UUID | None = None
    statement_key: str
    payout_account_label: str | None = None
    amount: float
    currency_code: str
    lifecycle_status: str
    instruction_status: str
    execution_status: str | None = None
    execution_mode: str | None = None
    external_reference: str | None = None
    created_at: datetime
    updated_at: datetime
    notes: list[str] = Field(default_factory=list)


class PartnerWorkspaceProgramLaneResponse(BaseModel):
    lane_key: str
    membership_status: str
    owner_context_label: str
    pilot_cohort_id: UUID | None = None
    pilot_cohort_status: str | None = None
    runbook_gate_status: str | None = None
    blocking_reason_codes: list[str] = Field(default_factory=list)
    warning_reason_codes: list[str] = Field(default_factory=list)
    restriction_notes: list[str] = Field(default_factory=list)
    readiness_notes: list[str] = Field(default_factory=list)
    updated_at: datetime


class PartnerWorkspaceProgramReadinessItemResponse(BaseModel):
    key: str
    status: str
    blocking_reason_codes: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class PartnerWorkspaceProgramsResponse(BaseModel):
    canonical_source: str
    primary_lane_key: str | None = None
    lane_memberships: list[PartnerWorkspaceProgramLaneResponse] = Field(default_factory=list)
    readiness_items: list[PartnerWorkspaceProgramReadinessItemResponse] = Field(default_factory=list)
    updated_at: datetime


class PartnerWorkspaceThreadEventResponse(BaseModel):
    id: UUID
    action_kind: str
    message: str
    created_by_admin_user_id: UUID | None
    created_at: datetime


class PartnerWorkspaceReviewRequestResponse(BaseModel):
    id: str
    kind: str
    due_date: datetime
    status: str
    available_actions: list[str] = Field(default_factory=list)
    thread_events: list[PartnerWorkspaceThreadEventResponse] = Field(default_factory=list)


class PartnerWorkspaceCaseResponse(BaseModel):
    id: str
    kind: str
    status: str
    updated_at: datetime
    notes: list[str] = Field(default_factory=list)
    available_actions: list[str] = Field(default_factory=list)
    thread_events: list[PartnerWorkspaceThreadEventResponse] = Field(default_factory=list)


class PartnerWorkspaceTrafficDeclarationResponse(BaseModel):
    id: str
    kind: str
    status: str
    scope_label: str
    updated_at: datetime
    notes: list[str] = Field(default_factory=list)


class SubmitPartnerWorkspaceTrafficDeclarationRequest(BaseModel):
    declaration_kind: TrafficDeclarationKind
    scope_label: str = Field(..., min_length=1, max_length=120)
    declaration_payload: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class SubmitPartnerWorkspaceCreativeApprovalRequest(BaseModel):
    scope_label: str = Field(..., min_length=1, max_length=120)
    creative_ref: str | None = Field(default=None, max_length=255)
    approval_payload: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class SchedulePartnerWorkspaceReportExportRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    request_payload: dict[str, Any] = Field(default_factory=dict)


class SubmitPartnerWorkspaceReviewRequestResponseRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    response_payload: dict[str, Any] = Field(default_factory=dict)


class SubmitPartnerWorkspaceCaseResponseRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    response_payload: dict[str, Any] = Field(default_factory=dict)


class MarkPartnerWorkspaceCaseReadyForOpsRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    response_payload: dict[str, Any] = Field(default_factory=dict)


class PartnerWorkspaceAnalyticsMetricResponse(BaseModel):
    id: str
    key: str
    value: str
    trend: str
    notes: list[str] = Field(default_factory=list)


class PartnerWorkspaceReportExportResponse(BaseModel):
    id: str
    kind: str
    status: str
    cadence: str
    notes: list[str] = Field(default_factory=list)
    available_actions: list[str] = Field(default_factory=list)
    thread_events: list[PartnerWorkspaceThreadEventResponse] = Field(default_factory=list)
    last_requested_at: datetime | None = None


class PartnerWorkspaceIntegrationCredentialResponse(BaseModel):
    id: UUID
    kind: str
    status: str
    scope_key: str
    token_hint: str
    destination_ref: str | None = None
    last_rotated_at: datetime | None = None
    notes: list[str] = Field(default_factory=list)


class RotatePartnerWorkspaceIntegrationCredentialRequest(BaseModel):
    destination_ref: str | None = Field(default=None, max_length=255)
    credential_metadata: dict[str, object] = Field(default_factory=dict)


class RotatePartnerWorkspaceIntegrationCredentialResponse(BaseModel):
    credential: PartnerWorkspaceIntegrationCredentialResponse
    issued_secret: str
    issued_at: datetime


class PartnerWorkspaceIntegrationDeliveryLogResponse(BaseModel):
    id: str
    channel: str
    status: str
    destination: str
    last_attempt_at: datetime
    notes: list[str] = Field(default_factory=list)


class PartnerWorkspacePostbackReadinessResponse(BaseModel):
    status: str
    delivery_status: str
    scope_label: str
    credential_id: UUID | None = None
    credential_status: str | None = None
    notes: list[str] = Field(default_factory=list)


class PartnerWorkspaceConversionRecordResponse(BaseModel):
    id: str
    kind: str
    status: str
    order_label: str
    customer_label: str
    code_label: str
    geo: str
    amount: str
    customer_scope: str
    updated_at: datetime
    notes: list[str] = Field(default_factory=list)


class PromotePartnerResponse(BaseModel):
    status: str
    user_id: UUID
    partner_account_id: UUID


PartnerApplicationReviewRequestDetailResponse.model_rebuild()
