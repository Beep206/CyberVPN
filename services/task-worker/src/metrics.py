"""Custom Prometheus metrics for CyberVPN task worker.

Provides additional metrics beyond the built-in TaskIQ middleware metrics.
These metrics track queue depth, external service interactions, and worker metadata.
"""

from prometheus_client import Counter, Gauge, Histogram, Info

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
)

# Queue metrics
QUEUE_DEPTH = Gauge(
    "cybervpn_queue_depth",
    "Current queue depth",
    ["queue"],
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
