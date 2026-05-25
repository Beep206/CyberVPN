"""Partner portal runtime observability metrics.

These metrics cover the partner-facing runtime flows that must move from
generic application telemetry to explicit partner portal signals:
- auth / realm / session
- bootstrap
- application / onboarding
- notifications / cases
- finance / payout / statements
- attribution / conversions
- outbox publication lifecycle
"""

from prometheus_client import Counter, Gauge, Histogram

_REQUEST_DURATION_BUCKETS = (0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
_APPLICATION_DECISION_DURATION_BUCKETS = (
    60.0,
    300.0,
    900.0,
    1800.0,
    3600.0,
    21600.0,
    86400.0,
    259200.0,
    604800.0,
    2592000.0,
)
_OUTBOX_LAG_BUCKETS = (1.0, 5.0, 10.0, 30.0, 60.0, 300.0, 900.0, 3600.0, 21600.0, 86400.0)
_FRONTEND_DURATION_BUCKETS = (0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
_FRONTEND_CLS_BUCKETS = (0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0)


cybervpn_partner_auth_login_attempts_total = Counter(
    "cybervpn_partner_auth_login_attempts_total",
    "Partner auth login attempts.",
    ["surface", "realm_type", "principal_class", "result", "reason"],
)

cybervpn_partner_auth_refresh_attempts_total = Counter(
    "cybervpn_partner_auth_refresh_attempts_total",
    "Partner auth refresh attempts.",
    ["surface", "realm_type", "principal_class", "result", "reason"],
)

cybervpn_partner_auth_logout_total = Counter(
    "cybervpn_partner_auth_logout_total",
    "Partner auth logout operations.",
    ["surface", "realm_type", "principal_class", "result", "reason"],
)

cybervpn_partner_auth_password_reset_requested_total = Counter(
    "cybervpn_partner_auth_password_reset_requested_total",
    "Partner password reset requests.",
    ["surface", "realm_type", "principal_class", "result"],
)

cybervpn_partner_auth_email_verification_total = Counter(
    "cybervpn_partner_auth_email_verification_total",
    "Partner email verification attempts.",
    ["surface", "realm_type", "principal_class", "result", "reason"],
)

cybervpn_partner_auth_mfa_challenges_total = Counter(
    "cybervpn_partner_auth_mfa_challenges_total",
    "Partner MFA challenge events.",
    ["surface", "realm_type", "principal_class", "result", "reason"],
)

cybervpn_partner_auth_mfa_failures_total = Counter(
    "cybervpn_partner_auth_mfa_failures_total",
    "Partner MFA failure events.",
    ["surface", "realm_type", "principal_class", "reason"],
)

cybervpn_partner_auth_wrong_host_token_rejected_total = Counter(
    "cybervpn_partner_auth_wrong_host_token_rejected_total",
    "Partner tokens rejected because the token realm does not match the partner surface.",
    ["surface", "realm_type", "principal_class", "reason"],
)

cybervpn_partner_auth_cross_realm_denied_total = Counter(
    "cybervpn_partner_auth_cross_realm_denied_total",
    "Partner requests denied because a token from another realm or audience was presented.",
    ["surface", "realm_type", "principal_class", "reason"],
)

cybervpn_partner_bootstrap_requests_total = Counter(
    "cybervpn_partner_bootstrap_requests_total",
    "Partner session bootstrap requests.",
    ["surface", "realm_type", "principal_class", "workspace_status", "result"],
)

cybervpn_partner_bootstrap_duration_seconds = Histogram(
    "cybervpn_partner_bootstrap_duration_seconds",
    "Partner session bootstrap duration in seconds.",
    ["surface", "realm_type", "principal_class", "workspace_status", "result"],
    buckets=_REQUEST_DURATION_BUCKETS,
)

cybervpn_partner_bootstrap_failures_total = Counter(
    "cybervpn_partner_bootstrap_failures_total",
    "Partner session bootstrap failures.",
    ["surface", "realm_type", "principal_class", "reason"],
)

cybervpn_partner_application_drafts_created_total = Counter(
    "cybervpn_partner_application_drafts_created_total",
    "Partner application drafts created.",
    ["surface", "lane", "workspace_status", "result"],
)

cybervpn_partner_application_drafts_saved_total = Counter(
    "cybervpn_partner_application_drafts_saved_total",
    "Partner application drafts saved.",
    ["surface", "lane", "workspace_status", "result"],
)

cybervpn_partner_application_submissions_total = Counter(
    "cybervpn_partner_application_submissions_total",
    "Partner application submissions and resubmissions.",
    ["surface", "lane", "workspace_status", "result", "reason"],
)

cybervpn_partner_application_submit_duration_seconds = Histogram(
    "cybervpn_partner_application_submit_duration_seconds",
    "Partner application submit and resubmit duration in seconds.",
    ["surface", "lane", "workspace_status", "result"],
    buckets=_REQUEST_DURATION_BUCKETS,
)

cybervpn_partner_application_requested_info_total = Counter(
    "cybervpn_partner_application_requested_info_total",
    "Partner application info requests issued by admin review.",
    ["surface", "lane", "workspace_status", "review_level", "result"],
)

cybervpn_partner_application_evidence_uploads_total = Counter(
    "cybervpn_partner_application_evidence_uploads_total",
    "Partner application evidence uploads.",
    ["surface", "lane", "workspace_status", "result"],
)

cybervpn_partner_application_evidence_upload_failures_total = Counter(
    "cybervpn_partner_application_evidence_upload_failures_total",
    "Partner application evidence upload failures.",
    ["surface", "lane", "workspace_status", "reason"],
)

cybervpn_partner_application_decisions_total = Counter(
    "cybervpn_partner_application_decisions_total",
    "Partner application review decisions.",
    ["surface", "lane", "workspace_status", "decision", "review_level", "result", "reason"],
)

cybervpn_partner_application_decision_duration_seconds = Histogram(
    "cybervpn_partner_application_decision_duration_seconds",
    "Partner application review decision duration in seconds.",
    ["surface", "lane", "decision", "review_level", "result"],
    buckets=_APPLICATION_DECISION_DURATION_BUCKETS,
)

cybervpn_partner_notifications_generated_total = Counter(
    "cybervpn_partner_notifications_generated_total",
    "Partner notifications generated from canonical workflow and finance/compliance events.",
    ["surface", "notification_type", "result"],
)

cybervpn_partner_notification_state_changes_total = Counter(
    "cybervpn_partner_notification_state_changes_total",
    "Partner notification read and archive state changes.",
    ["surface", "notification_type", "action", "result"],
)

cybervpn_partner_cases_created_total = Counter(
    "cybervpn_partner_cases_created_total",
    "Partner cases created for governed workflow follow-up.",
    ["surface", "case_type", "result"],
)

cybervpn_partner_case_actions_total = Counter(
    "cybervpn_partner_case_actions_total",
    "Partner case actions emitted by admin or partner operators.",
    ["surface", "case_type", "action", "result"],
)

cybervpn_partner_support_cases_open = Gauge(
    "cybervpn_partner_support_cases_open",
    "Current partner support/admin case backlog observed by partner ops overview.",
    ["surface", "case_status"],
)

cybervpn_partner_admin_ops_overview_requests_total = Counter(
    "cybervpn_partner_admin_ops_overview_requests_total",
    "Partner admin ops overview requests.",
    ["surface", "workspace_status", "result"],
)

cybervpn_partner_payout_review_queue_items = Gauge(
    "cybervpn_partner_payout_review_queue_items",
    "Current partner payout review queue items observed by partner ops overview.",
    ["surface", "kind", "status"],
)

cybervpn_partner_audit_events_observed_total = Counter(
    "cybervpn_partner_audit_events_observed_total",
    "Partner audit/workflow events observed by partner admin ops overview.",
    ["surface", "action_kind", "result"],
)

cybervpn_partner_statements_closed_total = Counter(
    "cybervpn_partner_statements_closed_total",
    "Partner statements closed for settlement review.",
    ["surface", "settlement_state", "result"],
)

cybervpn_partner_statement_close_duration_seconds = Histogram(
    "cybervpn_partner_statement_close_duration_seconds",
    "Partner statement close duration in seconds from period open to statement close.",
    ["surface", "result"],
    buckets=_APPLICATION_DECISION_DURATION_BUCKETS,
)

cybervpn_partner_statement_reopen_total = Counter(
    "cybervpn_partner_statement_reopen_total",
    "Partner statement reopen operations.",
    ["surface", "result"],
)

cybervpn_partner_payout_accounts_created_total = Counter(
    "cybervpn_partner_payout_accounts_created_total",
    "Partner payout accounts created.",
    ["surface", "payout_rail", "result"],
)

cybervpn_partner_payout_accounts_verified_total = Counter(
    "cybervpn_partner_payout_accounts_verified_total",
    "Partner payout accounts verified.",
    ["surface", "payout_rail", "result"],
)

cybervpn_partner_payout_instructions_created_total = Counter(
    "cybervpn_partner_payout_instructions_created_total",
    "Partner payout instructions created.",
    ["surface", "payout_state", "result"],
)

cybervpn_partner_payout_executions_total = Counter(
    "cybervpn_partner_payout_executions_total",
    "Partner payout execution lifecycle transitions.",
    ["surface", "payout_state", "result"],
)

cybervpn_partner_payout_execution_duration_seconds = Histogram(
    "cybervpn_partner_payout_execution_duration_seconds",
    "Partner payout execution lifecycle duration in seconds.",
    ["surface", "payout_state", "result"],
    buckets=_APPLICATION_DECISION_DURATION_BUCKETS,
)

cybervpn_partner_payout_failures_total = Counter(
    "cybervpn_partner_payout_failures_total",
    "Partner payout execution failures.",
    ["surface", "payout_state", "reason"],
)

cybervpn_partner_touchpoints_recorded_total = Counter(
    "cybervpn_partner_touchpoints_recorded_total",
    "Partner attribution touchpoints recorded.",
    ["surface", "touchpoint_type", "result"],
)

cybervpn_partner_touchpoints_rejected_total = Counter(
    "cybervpn_partner_touchpoints_rejected_total",
    "Partner attribution touchpoints rejected during validation.",
    ["surface", "touchpoint_type", "reason"],
)

cybervpn_partner_attribution_resolutions_total = Counter(
    "cybervpn_partner_attribution_resolutions_total",
    "Partner attribution resolution outcomes.",
    ["surface", "owner_type", "owner_source", "result", "reason"],
)

cybervpn_partner_attribution_resolution_duration_seconds = Histogram(
    "cybervpn_partner_attribution_resolution_duration_seconds",
    "Partner attribution resolution duration in seconds.",
    ["surface", "owner_type", "result"],
    buckets=_REQUEST_DURATION_BUCKETS,
)

cybervpn_partner_attribution_no_owner_total = Counter(
    "cybervpn_partner_attribution_no_owner_total",
    "Partner attribution resolutions that ended with no commercial owner.",
    ["surface", "result"],
)

cybervpn_partner_outbox_events_created_total = Counter(
    "cybervpn_partner_outbox_events_created_total",
    "Partner platform outbox events created.",
    ["event_type", "aggregate_type", "result"],
)

cybervpn_partner_outbox_events_published_total = Counter(
    "cybervpn_partner_outbox_events_published_total",
    "Partner platform outbox publications published.",
    ["event_type", "consumer_name", "result"],
)

cybervpn_partner_outbox_publish_failures_total = Counter(
    "cybervpn_partner_outbox_publish_failures_total",
    "Partner platform outbox publication failures.",
    ["event_type", "consumer_name", "result"],
)

cybervpn_partner_outbox_lag_seconds = Histogram(
    "cybervpn_partner_outbox_lag_seconds",
    "Partner platform outbox publication lag in seconds.",
    ["event_type", "consumer_name", "result"],
    buckets=_OUTBOX_LAG_BUCKETS,
)

cybervpn_partner_frontend_route_load_duration_seconds = Histogram(
    "cybervpn_partner_frontend_route_load_duration_seconds",
    "Frontend route load duration reported by partner/admin browser runtimes.",
    ["surface", "route_group"],
    buckets=_FRONTEND_DURATION_BUCKETS,
)

cybervpn_partner_frontend_api_call_duration_seconds = Histogram(
    "cybervpn_partner_frontend_api_call_duration_seconds",
    "Frontend API call duration reported by partner/admin browser runtimes.",
    ["surface", "route_group", "method", "endpoint_template", "result", "error_code"],
    buckets=_FRONTEND_DURATION_BUCKETS,
)

cybervpn_partner_frontend_route_guard_blocks_total = Counter(
    "cybervpn_partner_frontend_route_guard_blocks_total",
    "Frontend route guard blocks reported by partner/admin browser runtimes.",
    ["surface", "route_group", "blocked_reason", "workspace_status", "lane"],
)

cybervpn_partner_frontend_form_validation_errors_total = Counter(
    "cybervpn_partner_frontend_form_validation_errors_total",
    "Frontend form validation errors reported by partner/admin browser runtimes.",
    ["surface", "route_group", "form_name", "error_code"],
)

cybervpn_partner_frontend_submit_attempts_total = Counter(
    "cybervpn_partner_frontend_submit_attempts_total",
    "Frontend submit attempts reported by partner/admin browser runtimes.",
    ["surface", "route_group", "form_name", "result"],
)

cybervpn_partner_frontend_submit_failures_total = Counter(
    "cybervpn_partner_frontend_submit_failures_total",
    "Frontend submit failures reported by partner/admin browser runtimes.",
    ["surface", "route_group", "form_name", "error_code"],
)

cybervpn_partner_frontend_unhandled_errors_total = Counter(
    "cybervpn_partner_frontend_unhandled_errors_total",
    "Frontend unhandled errors reported by partner/admin browser runtimes.",
    ["surface", "route_group", "error_code"],
)

cybervpn_partner_frontend_render_errors_total = Counter(
    "cybervpn_partner_frontend_render_errors_total",
    "Frontend render errors reported by partner/admin browser runtimes.",
    ["surface", "route_group", "error_code"],
)

cybervpn_partner_frontend_lcp_seconds = Histogram(
    "cybervpn_partner_frontend_lcp_seconds",
    "Largest Contentful Paint reported by partner/admin browser runtimes.",
    ["surface", "route_group", "rating"],
    buckets=_FRONTEND_DURATION_BUCKETS,
)

cybervpn_partner_frontend_fcp_seconds = Histogram(
    "cybervpn_partner_frontend_fcp_seconds",
    "First Contentful Paint reported by partner/admin browser runtimes.",
    ["surface", "route_group", "rating"],
    buckets=_FRONTEND_DURATION_BUCKETS,
)

cybervpn_partner_frontend_inp_seconds = Histogram(
    "cybervpn_partner_frontend_inp_seconds",
    "Interaction to Next Paint reported by partner/admin browser runtimes.",
    ["surface", "route_group", "rating"],
    buckets=_FRONTEND_DURATION_BUCKETS,
)

cybervpn_partner_frontend_ttfb_seconds = Histogram(
    "cybervpn_partner_frontend_ttfb_seconds",
    "Time to First Byte reported by partner/admin browser runtimes.",
    ["surface", "route_group", "rating"],
    buckets=_FRONTEND_DURATION_BUCKETS,
)

cybervpn_partner_frontend_cls_ratio = Histogram(
    "cybervpn_partner_frontend_cls_ratio",
    "Cumulative Layout Shift ratio reported by partner/admin browser runtimes.",
    ["surface", "route_group", "rating"],
    buckets=_FRONTEND_CLS_BUCKETS,
)
