"""
Constants and configuration values for the CyberVPN task worker.

This module defines all constant values used throughout the task worker,
including Redis key templates, cron schedules, retry policies, and queue names.
"""

from typing import Final, TypedDict

# ============================================================================
# Redis Key Prefixes
# ============================================================================

REDIS_PREFIX: Final[str] = "cybervpn:"

# ============================================================================
# Redis Key Templates
# ============================================================================
# Use .format() to substitute placeholders (e.g., node_uuid, job_id, etc.)

HEALTH_KEY: Final[str] = f"{REDIS_PREFIX}health:{{node_uuid}}:current"
HEALTH_HISTORY_KEY: Final[str] = f"{REDIS_PREFIX}health:{{node_uuid}}:history"
HEALTH_SERVICE_KEY: Final[str] = f"{REDIS_PREFIX}health:services:{{service_name}}"
BANDWIDTH_KEY: Final[str] = f"{REDIS_PREFIX}bandwidth:{{node_uuid}}:{{timestamp}}"
BULK_PROGRESS_KEY: Final[str] = f"{REDIS_PREFIX}bulk:{{job_id}}:progress"
DASHBOARD_REALTIME_KEY: Final[str] = f"{REDIS_PREFIX}dashboard:realtime"
STATS_DAILY_KEY: Final[str] = f"{REDIS_PREFIX}stats:daily:{{date}}"
STATS_PAYMENTS_KEY: Final[str] = f"{REDIS_PREFIX}stats:payments:{{date}}"
SUB_REMINDER_KEY: Final[str] = f"{REDIS_PREFIX}sub_reminder:{{user_uuid}}:{{bracket}}"
USER_STATS_KEY: Final[str] = f"{REDIS_PREFIX}users:stats:summary"
NODE_CONFIG_KEY: Final[str] = f"{REDIS_PREFIX}nodes:config:{{node_uuid}}"

# ============================================================================
# Cron Schedule Expressions
# ============================================================================
# Format: "second minute hour day_of_month month day_of_week"

INTERVAL_NOTIFICATION_QUEUE_SECONDS: Final[int] = 30  # Every 30 seconds
SCHEDULE_HEALTH_CHECK: Final[str] = "*/2 * * * *"  # Every 2 minutes
SCHEDULE_SERVICES_HEALTH: Final[str] = "*/1 * * * *"  # Every 1 minute
SCHEDULE_BANDWIDTH: Final[str] = "*/5 * * * *"  # Every 5 minutes
SCHEDULE_SUBSCRIPTION_CHECK: Final[str] = "0 */1 * * *"  # Every hour
SCHEDULE_DISABLE_EXPIRED: Final[str] = "*/15 * * * *"  # Every 15 minutes
SCHEDULE_AUTO_RENEW: Final[str] = "*/30 * * * *"  # Every 30 minutes
SCHEDULE_DAILY_STATS: Final[str] = "5 0 * * *"  # Daily at 00:05 UTC
SCHEDULE_HOURLY_BANDWIDTH: Final[str] = "5 * * * *"  # At :05 every hour
INTERVAL_REALTIME_METRICS_SECONDS: Final[int] = 30  # Every 30 seconds
SCHEDULE_PAYMENT_VERIFY: Final[str] = "*/5 * * * *"  # Every 5 minutes
SCHEDULE_WEBHOOK_RETRY: Final[str] = "*/30 * * * *"  # Every 30 minutes
SCHEDULE_CLEANUP: Final[str] = "0 2 * * *"  # Daily at 2 AM UTC
SCHEDULE_CLEANUP_NOTIFICATIONS: Final[str] = "0 1 * * *"  # Daily at 1 AM UTC
SCHEDULE_CLEANUP_CACHE: Final[str] = "0 4 * * *"  # Daily at 4 AM UTC
SCHEDULE_CLEANUP_WEEKLY: Final[str] = "0 3 * * 0"  # Sunday at 3 AM UTC
SCHEDULE_CLEANUP_WEBHOOK_WEEKLY: Final[str] = "0 3 * * 1"  # Monday at 3 AM UTC
SCHEDULE_REPORT_DAILY: Final[str] = "0 6 * * *"  # Daily at 6 AM UTC (09:00 MSK)
SCHEDULE_REPORT_WEEKLY: Final[str] = "0 7 * * 1"  # Monday at 7 AM UTC
SCHEDULE_ANOMALY_CHECK: Final[str] = "*/5 * * * *"  # Every 5 minutes
SCHEDULE_SYNC_NODES: Final[str] = "*/5 * * * *"  # Every 5 minutes (legacy)
SCHEDULE_SYNC_GEOLOCATIONS: Final[str] = "0 */6 * * *"  # Every 6 hours
SCHEDULE_SYNC_USER_STATS: Final[str] = "*/10 * * * *"  # Every 10 minutes
SCHEDULE_SYNC_NODE_CONFIGS: Final[str] = "*/30 * * * *"  # Every 30 minutes
SCHEDULE_FINANCIAL_STATS: Final[str] = "30 0 * * *"  # Daily at 00:30 UTC
SCHEDULE_TRAFFIC_RESET: Final[str] = "0 0 1 * *"  # 1st of month at 00:00 UTC
SCHEDULE_QUEUE_DEPTH: Final[str] = "*/1 * * * *"  # Every 1 minute

# ============================================================================
# Retry Policies
# ============================================================================


class RetryPolicy(TypedDict):
    """Type definition for retry policy configuration."""

    max_retries: int
    backoff: str
    delays: list[int]


RETRY_POLICIES: Final[dict[str, RetryPolicy]] = {
    "payments_webhook": {
        "max_retries": 3,
        "backoff": "exponential",
        "delays": [30, 120, 600],
    },
    "notifications_on_demand": {
        "max_retries": 3,
        "backoff": "exponential",
        "delays": [10, 30, 90],
    },
    "notifications": {
        "max_retries": 5,
        "backoff": "exponential",
        "delays": [30, 60, 300, 900, 3600],
    },
    "subscriptions": {
        "max_retries": 3,
        "backoff": "exponential",
        "delays": [60, 300, 900],
    },
    "monitoring": {
        "max_retries": 2,
        "backoff": "fixed",
        "delays": [30, 60],
    },
    "payments": {
        "max_retries": 3,
        "backoff": "exponential",
        "delays": [60, 300, 900],
    },
    "analytics": {
        "max_retries": 2,
        "backoff": "fixed",
        "delays": [60, 120],
    },
    "cleanup": {
        "max_retries": 1,
        "backoff": "fixed",
        "delays": [300],
    },
    "sync": {
        "max_retries": 3,
        "backoff": "exponential",
        "delays": [30, 60, 300],
    },
    "reports": {
        "max_retries": 2,
        "backoff": "exponential",
        "delays": [120, 600],
    },
    "bulk": {
        "max_retries": 3,
        "backoff": "exponential",
        "delays": [60, 300, 900],
    },
}

# ============================================================================
# Notification Types
# ============================================================================

NOTIFICATION_TYPE_SUBSCRIPTION_EXPIRING: Final[str] = "subscription_expiring"
NOTIFICATION_TYPE_SUBSCRIPTION_EXPIRED: Final[str] = "subscription_expired"
NOTIFICATION_TYPE_PAYMENT_RECEIVED: Final[str] = "payment_received"
NOTIFICATION_TYPE_PAYMENT_FAILED: Final[str] = "payment_failed"
NOTIFICATION_TYPE_SERVER_DOWN: Final[str] = "server_down"
NOTIFICATION_TYPE_SERVER_RECOVERED: Final[str] = "server_recovered"
NOTIFICATION_TYPE_TRAFFIC_WARNING: Final[str] = "traffic_warning"
NOTIFICATION_TYPE_SYSTEM_ALERT: Final[str] = "system_alert"

# ============================================================================
# Task Queue Names
# ============================================================================

QUEUE_NOTIFICATIONS: Final[str] = "notifications"
QUEUE_SUBSCRIPTIONS: Final[str] = "subscriptions"
QUEUE_MONITORING: Final[str] = "monitoring"
QUEUE_PAYMENTS: Final[str] = "payments"
QUEUE_ANALYTICS: Final[str] = "analytics"
QUEUE_CLEANUP: Final[str] = "cleanup"
QUEUE_SYNC: Final[str] = "sync"
QUEUE_REPORTS: Final[str] = "reports"
QUEUE_BULK: Final[str] = "bulk"

# ============================================================================
# Status Constants
# ============================================================================

STATUS_PENDING: Final[str] = "pending"
STATUS_PROCESSING: Final[str] = "processing"
STATUS_SENT: Final[str] = "sent"
STATUS_FAILED: Final[str] = "failed"
STATUS_CANCELLED: Final[str] = "cancelled"

# ============================================================================
# Public API
# ============================================================================

__all__ = [
    # Redis
    "REDIS_PREFIX",
    "HEALTH_KEY",
    "HEALTH_HISTORY_KEY",
    "HEALTH_SERVICE_KEY",
    "BANDWIDTH_KEY",
    "BULK_PROGRESS_KEY",
    "DASHBOARD_REALTIME_KEY",
    "STATS_DAILY_KEY",
    "STATS_PAYMENTS_KEY",
    "SUB_REMINDER_KEY",
    "USER_STATS_KEY",
    "NODE_CONFIG_KEY",
    # Schedules
    "INTERVAL_NOTIFICATION_QUEUE_SECONDS",
    "SCHEDULE_HEALTH_CHECK",
    "SCHEDULE_SERVICES_HEALTH",
    "SCHEDULE_BANDWIDTH",
    "SCHEDULE_SUBSCRIPTION_CHECK",
    "SCHEDULE_DISABLE_EXPIRED",
    "SCHEDULE_AUTO_RENEW",
    "SCHEDULE_DAILY_STATS",
    "SCHEDULE_HOURLY_BANDWIDTH",
    "INTERVAL_REALTIME_METRICS_SECONDS",
    "SCHEDULE_PAYMENT_VERIFY",
    "SCHEDULE_WEBHOOK_RETRY",
    "SCHEDULE_CLEANUP",
    "SCHEDULE_CLEANUP_NOTIFICATIONS",
    "SCHEDULE_CLEANUP_CACHE",
    "SCHEDULE_CLEANUP_WEEKLY",
    "SCHEDULE_CLEANUP_WEBHOOK_WEEKLY",
    "SCHEDULE_REPORT_DAILY",
    "SCHEDULE_REPORT_WEEKLY",
    "SCHEDULE_ANOMALY_CHECK",
    "SCHEDULE_SYNC_NODES",
    "SCHEDULE_SYNC_GEOLOCATIONS",
    "SCHEDULE_SYNC_USER_STATS",
    "SCHEDULE_SYNC_NODE_CONFIGS",
    "SCHEDULE_FINANCIAL_STATS",
    "SCHEDULE_TRAFFIC_RESET",
    "SCHEDULE_QUEUE_DEPTH",
    # Retry Policies
    "RetryPolicy",
    "RETRY_POLICIES",
    # Notification Types
    "NOTIFICATION_TYPE_SUBSCRIPTION_EXPIRING",
    "NOTIFICATION_TYPE_SUBSCRIPTION_EXPIRED",
    "NOTIFICATION_TYPE_PAYMENT_RECEIVED",
    "NOTIFICATION_TYPE_PAYMENT_FAILED",
    "NOTIFICATION_TYPE_SERVER_DOWN",
    "NOTIFICATION_TYPE_SERVER_RECOVERED",
    "NOTIFICATION_TYPE_TRAFFIC_WARNING",
    "NOTIFICATION_TYPE_SYSTEM_ALERT",
    # Queue Names
    "QUEUE_NOTIFICATIONS",
    "QUEUE_SUBSCRIPTIONS",
    "QUEUE_MONITORING",
    "QUEUE_PAYMENTS",
    "QUEUE_ANALYTICS",
    "QUEUE_CLEANUP",
    "QUEUE_SYNC",
    "QUEUE_REPORTS",
    "QUEUE_BULK",
    # Status Constants
    "STATUS_PENDING",
    "STATUS_PROCESSING",
    "STATUS_SENT",
    "STATUS_FAILED",
    "STATUS_CANCELLED",
]
