"""Custom Prometheus metrics for CyberVPN task worker.

Provides additional metrics beyond the built-in TaskIQ middleware metrics.
These metrics track queue depth, external service interactions, and worker metadata.
"""

import os

from prometheus_client import Counter, Gauge, Histogram, Info

MULTIPROC_ENABLED = bool(os.getenv("PROMETHEUS_MULTIPROC_DIR"))

# Task metrics (additional to middleware metrics)
TASK_TOTAL = Counter(
    "cybervpn_tasks_total",
    "Total tasks executed",
    ["task_name", "status"],
)

TASK_DURATION = Histogram(
    "cybervpn_task_duration_seconds",
    "Task execution duration",
    ["task_name"],
    buckets=[0.1, 0.5, 1, 5, 10, 30, 60, 120, 300],
)

TASK_IN_PROGRESS = Gauge(
    "cybervpn_tasks_in_progress",
    "Tasks currently executing",
    ["task_name"],
    multiprocess_mode="livesum" if MULTIPROC_ENABLED else "all",
)

# Queue metrics
QUEUE_DEPTH = Gauge(
    "cybervpn_queue_depth",
    "Current queue depth",
    ["queue"],
    multiprocess_mode="livemax" if MULTIPROC_ENABLED else "all",
)

# External service metrics
EXTERNAL_REQUEST_TOTAL = Counter(
    "cybervpn_external_requests_total",
    "External API calls",
    ["service", "method", "status"],
)

EXTERNAL_REQUEST_DURATION = Histogram(
    "cybervpn_external_request_duration_seconds",
    "External API call duration",
    ["service", "method"],
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30],
)

# Worker info
WORKER_INFO = Info(
    "cybervpn_worker",
    "Worker service information",
)

# Stage 1 payment reconciliation metrics for paid-but-no-access visibility.
STAGE1_PAYMENT_RECONCILIATION_RUNS_TOTAL = Counter(
    "cybervpn_stage1_payment_reconciliation_runs_total",
    "Total Stage 1 payment reconciliation runs",
    ["result"],
)

STAGE1_PAYMENT_RECONCILIATION_ITEMS_CURRENT = Gauge(
    "cybervpn_stage1_payment_reconciliation_items_current",
    "Current Stage 1 payment reconciliation findings by severity",
    ["severity"],
    multiprocess_mode="livemax" if MULTIPROC_ENABLED else "all",
)

STAGE1_PAYMENT_RECONCILIATION_MAX_AGE_MINUTES = Gauge(
    "cybervpn_stage1_payment_reconciliation_max_age_minutes",
    "Maximum age in minutes of current Stage 1 payment reconciliation findings",
    multiprocess_mode="livemax" if MULTIPROC_ENABLED else "all",
)

STAGE1_PAYMENT_RECONCILIATION_LAUNCH_BLOCKED = Gauge(
    "cybervpn_stage1_payment_reconciliation_launch_blocked",
    "Whether Stage 1 payment reconciliation currently blocks launch or paid beta",
    multiprocess_mode="livemax" if MULTIPROC_ENABLED else "all",
)

# OTP Email metrics (for Grafana monitoring per PRD requirements)
OTP_EMAILS_SENT = Counter(
    "cybervpn_otp_emails_sent_total",
    "Total OTP emails sent",
    ["provider", "action", "status"],  # provider=resend|brevo, action=initial|resend, status=success|failed
)

OTP_EMAIL_ERRORS = Counter(
    "cybervpn_otp_email_errors_total",
    "OTP email sending errors",
    ["provider", "error_type"],  # error_type=api_error|network_error|unknown
)

OTP_VERIFIED = Counter(
    "cybervpn_otp_verified_total",
    "Total successful OTP verifications",
)

OTP_FAILED = Counter(
    "cybervpn_otp_failed_total",
    "Total failed OTP attempts",
    ["reason"],  # reason=invalid_code|expired|exhausted
)

# Generic email metrics (BOB-6: metrics hardening)
EMAIL_SEND_TOTAL = Counter(
    "cybervpn_email_send_total",
    "Total email send attempts",
    ["provider", "email_type", "status"],  # provider=resend|brevo|smtp
    # email_type=otp|magic_link|notification, status=success|failed
)

EMAIL_SEND_CONTEXT_TOTAL = Counter(
    "cybervpn_email_send_context_total",
    "Total email send attempts with auth delivery context",
    ["channel", "provider", "email_type", "locale", "status"],
)

EMAIL_SEND_DURATION = Histogram(
    "cybervpn_email_send_duration_seconds",
    "Email sending duration in seconds",
    ["provider", "email_type"],  # provider=resend|brevo|smtp, email_type=otp|magic_link|notification
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30],
)

EMAIL_SEND_CONTEXT_DURATION = Histogram(
    "cybervpn_email_send_context_duration_seconds",
    "Email sending duration in seconds with auth delivery context",
    ["channel", "provider", "email_type", "locale"],
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30],
)

EMAIL_SEND_ERRORS = Counter(
    "cybervpn_email_send_errors_total",
    "Total email sending errors",
    ["provider", "error_type"],  # error_type=api_error|network_error|timeout|unknown
)

# Public network / DPI publish hardening metrics (Wave 6 / Phase 6)
PUBLIC_NETWORK_DPI_PUBLISH_TOTAL = Counter(
    "cybervpn_public_network_dpi_publish_total",
    "Total public DPI snapshot publish runs",
    ["result", "freshness_status", "enabled"],
)

PUBLIC_NETWORK_DPI_PUBLISH_DURATION = Histogram(
    "cybervpn_public_network_dpi_publish_duration_seconds",
    "Duration of public DPI snapshot publishing task",
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30, 60, 120],
)

PUBLIC_NETWORK_DPI_PUBLISH_LAST_ATTEMPT_UNIXTIME = Gauge(
    "cybervpn_public_network_dpi_publish_last_attempt_unixtime",
    "Unix timestamp of the last public DPI publish attempt",
    multiprocess_mode="livemax" if MULTIPROC_ENABLED else "all",
)

PUBLIC_NETWORK_DPI_PUBLISH_LAST_SUCCESS_UNIXTIME = Gauge(
    "cybervpn_public_network_dpi_publish_last_success_unixtime",
    "Unix timestamp of the last successful public DPI publish",
    multiprocess_mode="livemax" if MULTIPROC_ENABLED else "all",
)

PUBLIC_NETWORK_DPI_PUBLISH_CONSECUTIVE_FAILURES = Gauge(
    "cybervpn_public_network_dpi_publish_consecutive_failures",
    "Consecutive failures for the public DPI publish task",
    multiprocess_mode="livemax" if MULTIPROC_ENABLED else "all",
)

PUBLIC_NETWORK_DPI_PUBLISH_COUNTRIES_TRACKED = Gauge(
    "cybervpn_public_network_dpi_publish_countries_tracked",
    "Countries tracked in the latest public DPI snapshot",
    multiprocess_mode="livemax" if MULTIPROC_ENABLED else "all",
)

PUBLIC_NETWORK_DPI_PUBLISH_PROBE_COUNT = Gauge(
    "cybervpn_public_network_dpi_publish_probe_count",
    "Probe count used for the latest public DPI snapshot",
    multiprocess_mode="livemax" if MULTIPROC_ENABLED else "all",
)

PUBLIC_NETWORK_DPI_ENABLED = Gauge(
    "cybervpn_public_network_dpi_enabled",
    "Whether the latest public DPI snapshot is enabled for public scoring",
    multiprocess_mode="livemax" if MULTIPROC_ENABLED else "all",
)

PUBLIC_NETWORK_DPI_SNAPSHOT_FRESHNESS = Gauge(
    "cybervpn_public_network_dpi_snapshot_freshness",
    "Freshness state of the latest public DPI snapshot",
    ["freshness_status"],
    multiprocess_mode="livemax" if MULTIPROC_ENABLED else "all",
)

# Partner bot provisioning hardening metrics (Wave 6 / Phase 6)
PARTNER_BOT_PROVISIONING_RUNS_TOTAL = Counter(
    "cybervpn_partner_bot_provisioning_runs_total",
    "Total partner bot provisioning task runs",
    ["result"],
)

PARTNER_BOT_PROVISIONING_DURATION = Histogram(
    "cybervpn_partner_bot_provisioning_duration_seconds",
    "Duration of the partner bot provisioning task",
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30, 60, 120],
)

PARTNER_BOT_PROVISIONING_LAST_ATTEMPT_UNIXTIME = Gauge(
    "cybervpn_partner_bot_provisioning_last_attempt_unixtime",
    "Unix timestamp of the last partner bot provisioning task attempt",
    multiprocess_mode="livemax" if MULTIPROC_ENABLED else "all",
)

PARTNER_BOT_PROVISIONING_LAST_SUCCESS_UNIXTIME = Gauge(
    "cybervpn_partner_bot_provisioning_last_success_unixtime",
    "Unix timestamp of the last successful partner bot provisioning task run",
    multiprocess_mode="livemax" if MULTIPROC_ENABLED else "all",
)

PARTNER_BOT_PROVISIONING_CONSECUTIVE_FAILURES = Gauge(
    "cybervpn_partner_bot_provisioning_consecutive_failures",
    "Consecutive failures for the partner bot provisioning task",
    multiprocess_mode="livemax" if MULTIPROC_ENABLED else "all",
)

PARTNER_BOT_PROVISIONING_LAST_PROCESSED_JOBS = Gauge(
    "cybervpn_partner_bot_provisioning_last_processed_jobs",
    "Number of jobs processed during the latest partner bot provisioning task run",
    multiprocess_mode="livemax" if MULTIPROC_ENABLED else "all",
)

PARTNER_BOT_PROVISIONING_LAST_ERRORS = Gauge(
    "cybervpn_partner_bot_provisioning_last_errors",
    "Number of errors observed during the latest partner bot provisioning task run",
    multiprocess_mode="livemax" if MULTIPROC_ENABLED else "all",
)

PARTNER_BOT_PROVISIONING_ACTIONS_TOTAL = Counter(
    "cybervpn_partner_bot_provisioning_actions_total",
    "Partner bot provisioning actions by terminal job status and provisioning path",
    ["action", "provisioning_path"],
)

GROWTH_REPORTING_REFRESH_RUNS_TOTAL = Counter(
    "cybervpn_growth_reporting_refresh_worker_runs_total",
    "Total scheduled customer growth reporting refresh worker runs.",
    ["result"],
)

GROWTH_REPORTING_REFRESH_DURATION = Histogram(
    "cybervpn_growth_reporting_refresh_worker_duration_seconds",
    "Duration of scheduled customer growth reporting refresh worker runs.",
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30, 60, 120, 300],
)

GROWTH_REPORTING_REFRESH_LAST_ATTEMPT_UNIXTIME = Gauge(
    "cybervpn_growth_reporting_refresh_worker_last_attempt_unixtime",
    "Unix timestamp of the latest scheduled customer growth reporting refresh attempt.",
    multiprocess_mode="livemax" if MULTIPROC_ENABLED else "all",
)

GROWTH_REPORTING_REFRESH_LAST_SUCCESS_UNIXTIME = Gauge(
    "cybervpn_growth_reporting_refresh_worker_last_success_unixtime",
    "Unix timestamp of the latest successful scheduled customer growth reporting refresh.",
    multiprocess_mode="livemax" if MULTIPROC_ENABLED else "all",
)

GROWTH_REPORTING_REFRESH_CONSECUTIVE_FAILURES = Gauge(
    "cybervpn_growth_reporting_refresh_worker_consecutive_failures",
    "Consecutive failures for scheduled customer growth reporting refresh.",
    multiprocess_mode="livemax" if MULTIPROC_ENABLED else "all",
)

GROWTH_REPORTING_REFRESH_LAST_ROWS_WRITTEN = Gauge(
    "cybervpn_growth_reporting_refresh_worker_last_rows_written",
    "Rows written during the latest successful scheduled customer growth reporting refresh.",
    multiprocess_mode="livemax" if MULTIPROC_ENABLED else "all",
)

GROWTH_REPORTING_DELIVERY_RUNS_TOTAL = Counter(
    "cybervpn_growth_reporting_delivery_worker_runs_total",
    "Total scheduled customer growth reporting delivery worker runs.",
    ["result"],
)

GROWTH_REPORTING_DELIVERY_DURATION = Histogram(
    "cybervpn_growth_reporting_delivery_worker_duration_seconds",
    "Duration of scheduled customer growth reporting delivery worker runs.",
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30, 60, 120, 300],
)

GROWTH_REPORTING_DELIVERY_LAST_ATTEMPT_UNIXTIME = Gauge(
    "cybervpn_growth_reporting_delivery_worker_last_attempt_unixtime",
    "Unix timestamp of the latest scheduled customer growth reporting delivery attempt.",
    multiprocess_mode="livemax" if MULTIPROC_ENABLED else "all",
)

GROWTH_REPORTING_DELIVERY_LAST_SUCCESS_UNIXTIME = Gauge(
    "cybervpn_growth_reporting_delivery_worker_last_success_unixtime",
    "Unix timestamp of the latest successful scheduled customer growth reporting delivery run.",
    multiprocess_mode="livemax" if MULTIPROC_ENABLED else "all",
)

GROWTH_REPORTING_DELIVERY_CONSECUTIVE_FAILURES = Gauge(
    "cybervpn_growth_reporting_delivery_worker_consecutive_failures",
    "Consecutive failures for scheduled customer growth reporting deliveries.",
    multiprocess_mode="livemax" if MULTIPROC_ENABLED else "all",
)

GROWTH_REPORTING_DELIVERY_LAST_CLAIMED = Gauge(
    "cybervpn_growth_reporting_delivery_worker_last_claimed",
    "Deliveries claimed during the latest scheduled customer growth reporting delivery run.",
    multiprocess_mode="livemax" if MULTIPROC_ENABLED else "all",
)

GROWTH_REPORTING_DELIVERY_LAST_DELIVERED = Gauge(
    "cybervpn_growth_reporting_delivery_worker_last_delivered",
    "Deliveries marked delivered during the latest scheduled customer growth reporting delivery run.",
    multiprocess_mode="livemax" if MULTIPROC_ENABLED else "all",
)

GROWTH_REPORTING_DELIVERY_LAST_FAILED = Gauge(
    "cybervpn_growth_reporting_delivery_worker_last_failed",
    "Deliveries marked failed during the latest scheduled customer growth reporting delivery run.",
    multiprocess_mode="livemax" if MULTIPROC_ENABLED else "all",
)

GROWTH_REPORTING_GOVERNANCE_FOLLOWUP_RUNS_TOTAL = Counter(
    "cybervpn_growth_reporting_governance_followup_worker_runs_total",
    "Total scheduled customer growth reporting governance follow-up worker runs.",
    ["result"],
)

GROWTH_REPORTING_GOVERNANCE_FOLLOWUP_DURATION = Histogram(
    "cybervpn_growth_reporting_governance_followup_worker_duration_seconds",
    "Duration of scheduled customer growth reporting governance follow-up worker runs.",
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30, 60, 120, 300],
)

GROWTH_REPORTING_GOVERNANCE_FOLLOWUP_LAST_ATTEMPT_UNIXTIME = Gauge(
    "cybervpn_growth_reporting_governance_followup_worker_last_attempt_unixtime",
    "Unix timestamp of the latest scheduled customer growth reporting governance follow-up attempt.",
    multiprocess_mode="livemax" if MULTIPROC_ENABLED else "all",
)

GROWTH_REPORTING_GOVERNANCE_FOLLOWUP_LAST_SUCCESS_UNIXTIME = Gauge(
    "cybervpn_growth_reporting_governance_followup_worker_last_success_unixtime",
    "Unix timestamp of the latest successful scheduled customer growth reporting governance follow-up run.",
    multiprocess_mode="livemax" if MULTIPROC_ENABLED else "all",
)

GROWTH_REPORTING_GOVERNANCE_FOLLOWUP_CONSECUTIVE_FAILURES = Gauge(
    "cybervpn_growth_reporting_governance_followup_worker_consecutive_failures",
    "Consecutive failures for scheduled customer growth reporting governance follow-up processing.",
    multiprocess_mode="livemax" if MULTIPROC_ENABLED else "all",
)

GROWTH_REPORTING_GOVERNANCE_FOLLOWUP_LAST_SCANNED = Gauge(
    "cybervpn_growth_reporting_governance_followup_worker_last_scanned",
    "Subscriptions scanned during the latest scheduled governance follow-up run.",
    multiprocess_mode="livemax" if MULTIPROC_ENABLED else "all",
)

GROWTH_REPORTING_GOVERNANCE_FOLLOWUP_LAST_OPEN = Gauge(
    "cybervpn_growth_reporting_governance_followup_worker_last_open",
    "Open governance follow-up items reported by the latest scheduled run.",
    multiprocess_mode="livemax" if MULTIPROC_ENABLED else "all",
)

GROWTH_REPORTING_GOVERNANCE_FOLLOWUP_LAST_OVERDUE = Gauge(
    "cybervpn_growth_reporting_governance_followup_worker_last_overdue",
    "Overdue governance follow-up items reported by the latest scheduled run.",
    multiprocess_mode="livemax" if MULTIPROC_ENABLED else "all",
)

GROWTH_REPORTING_CLEANUP_RUNS_TOTAL = Counter(
    "cybervpn_growth_reporting_cleanup_worker_runs_total",
    "Total scheduled customer growth reporting cleanup worker runs.",
    ["result"],
)

GROWTH_REPORTING_CLEANUP_DURATION = Histogram(
    "cybervpn_growth_reporting_cleanup_worker_duration_seconds",
    "Duration of scheduled customer growth reporting cleanup worker runs.",
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30, 60, 120, 300],
)

GROWTH_REPORTING_CLEANUP_LAST_ATTEMPT_UNIXTIME = Gauge(
    "cybervpn_growth_reporting_cleanup_worker_last_attempt_unixtime",
    "Unix timestamp of the latest scheduled customer growth reporting cleanup attempt.",
    multiprocess_mode="livemax" if MULTIPROC_ENABLED else "all",
)

GROWTH_REPORTING_CLEANUP_LAST_SUCCESS_UNIXTIME = Gauge(
    "cybervpn_growth_reporting_cleanup_worker_last_success_unixtime",
    "Unix timestamp of the latest successful scheduled customer growth reporting cleanup run.",
    multiprocess_mode="livemax" if MULTIPROC_ENABLED else "all",
)

GROWTH_REPORTING_CLEANUP_CONSECUTIVE_FAILURES = Gauge(
    "cybervpn_growth_reporting_cleanup_worker_consecutive_failures",
    "Consecutive failures for scheduled customer growth reporting cleanup.",
    multiprocess_mode="livemax" if MULTIPROC_ENABLED else "all",
)

GROWTH_REPORTING_CLEANUP_LAST_DELETED = Gauge(
    "cybervpn_growth_reporting_cleanup_worker_last_deleted",
    "Artifacts deleted during the latest scheduled customer growth reporting cleanup run.",
    ["artifact_kind"],
    multiprocess_mode="livemax" if MULTIPROC_ENABLED else "all",
)
