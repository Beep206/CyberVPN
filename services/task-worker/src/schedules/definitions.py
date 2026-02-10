"""Schedule definitions for all periodic tasks.

Registers cron schedules for every periodic task in the worker.
TaskIQ reads the ``schedule`` label and dispatches tasks accordingly.
"""

from typing import Any, cast

import structlog

from src.broker import broker, schedule_source  # noqa: F401 – schedule_source imported for scheduler
from src.utils.constants import (
    INTERVAL_NOTIFICATION_QUEUE_SECONDS,
    INTERVAL_REALTIME_METRICS_SECONDS,
    SCHEDULE_ANOMALY_CHECK,
    SCHEDULE_AUTO_RENEW,
    SCHEDULE_BANDWIDTH,
    SCHEDULE_CLEANUP,
    SCHEDULE_CLEANUP_CACHE,
    SCHEDULE_CLEANUP_NOTIFICATIONS,
    SCHEDULE_CLEANUP_WEBHOOK_WEEKLY,
    SCHEDULE_CLEANUP_WEEKLY,
    SCHEDULE_DAILY_STATS,
    SCHEDULE_DISABLE_EXPIRED,
    SCHEDULE_FINANCIAL_STATS,
    SCHEDULE_HEALTH_CHECK,
    SCHEDULE_HOURLY_BANDWIDTH,
    SCHEDULE_PAYMENT_VERIFY,
    SCHEDULE_QUEUE_DEPTH,
    SCHEDULE_REPORT_DAILY,
    SCHEDULE_REPORT_WEEKLY,
    SCHEDULE_SERVICES_HEALTH,
    SCHEDULE_SUBSCRIPTION_CHECK,
    SCHEDULE_SYNC_GEOLOCATIONS,
    SCHEDULE_SYNC_NODE_CONFIGS,
    SCHEDULE_SYNC_USER_STATS,
    SCHEDULE_TRAFFIC_RESET,
    SCHEDULE_WEBHOOK_RETRY,
)

logger = structlog.get_logger(__name__)


def _schedule_task(task: Any, schedule: list[dict]) -> Any:
    """Attach schedule labels to a task.

    TaskIQ's runtime supports ``with_labels``, but type stubs may not.
    Casting to ``Any`` keeps type checkers quiet.
    """
    return cast(Any, task).with_labels(schedule=schedule)


# =============================================================================
# Notification Tasks
# =============================================================================

from src.tasks.notifications.process_queue import process_notification_queue  # noqa: E402

process_notification_queue = _schedule_task(
    process_notification_queue, [{"interval": INTERVAL_NOTIFICATION_QUEUE_SECONDS}]
)

# =============================================================================
# Monitoring Tasks
# =============================================================================

from src.tasks.monitoring.health_check import check_server_health  # noqa: E402

check_server_health = _schedule_task(check_server_health, [{"cron": SCHEDULE_HEALTH_CHECK}])

from src.tasks.monitoring.services_health import check_external_services  # noqa: E402

check_external_services = _schedule_task(check_external_services, [{"cron": SCHEDULE_SERVICES_HEALTH}])

from src.tasks.monitoring.bandwidth import collect_bandwidth_snapshot  # noqa: E402

collect_bandwidth_snapshot = _schedule_task(collect_bandwidth_snapshot, [{"cron": SCHEDULE_BANDWIDTH}])

from src.tasks.monitoring.queue_depth import monitor_queue_depth  # noqa: E402

monitor_queue_depth = _schedule_task(monitor_queue_depth, [{"cron": SCHEDULE_QUEUE_DEPTH}])

# =============================================================================
# Subscription Tasks
# =============================================================================

from src.tasks.subscriptions.check_expiring import check_expiring_subscriptions  # noqa: E402

check_expiring_subscriptions = _schedule_task(check_expiring_subscriptions, [{"cron": SCHEDULE_SUBSCRIPTION_CHECK}])

from src.tasks.subscriptions.disable_expired import disable_expired_users  # noqa: E402

disable_expired_users = _schedule_task(disable_expired_users, [{"cron": SCHEDULE_DISABLE_EXPIRED}])

from src.tasks.subscriptions.auto_renew import auto_renew_subscriptions  # noqa: E402

auto_renew_subscriptions = _schedule_task(auto_renew_subscriptions, [{"cron": SCHEDULE_AUTO_RENEW}])

from src.tasks.subscriptions.reset_traffic import reset_monthly_traffic  # noqa: E402

reset_monthly_traffic = _schedule_task(reset_monthly_traffic, [{"cron": SCHEDULE_TRAFFIC_RESET}])

# =============================================================================
# Analytics Tasks
# =============================================================================

from src.tasks.analytics.daily_stats import aggregate_daily_stats  # noqa: E402

aggregate_daily_stats = _schedule_task(aggregate_daily_stats, [{"cron": SCHEDULE_DAILY_STATS}])

from src.tasks.analytics.financial_stats import aggregate_financial_stats  # noqa: E402

aggregate_financial_stats = _schedule_task(aggregate_financial_stats, [{"cron": SCHEDULE_FINANCIAL_STATS}])

from src.tasks.analytics.hourly_bandwidth import aggregate_hourly_bandwidth  # noqa: E402

aggregate_hourly_bandwidth = _schedule_task(aggregate_hourly_bandwidth, [{"cron": SCHEDULE_HOURLY_BANDWIDTH}])

from src.tasks.analytics.realtime_metrics import update_realtime_metrics  # noqa: E402

update_realtime_metrics = _schedule_task(update_realtime_metrics, [{"interval": INTERVAL_REALTIME_METRICS_SECONDS}])

# =============================================================================
# Payment Tasks
# =============================================================================

from src.tasks.payments.verify_pending import verify_pending_payments  # noqa: E402

verify_pending_payments = _schedule_task(verify_pending_payments, [{"cron": SCHEDULE_PAYMENT_VERIFY}])

from src.tasks.payments.retry_webhooks import retry_failed_webhooks  # noqa: E402

retry_failed_webhooks = _schedule_task(retry_failed_webhooks, [{"cron": SCHEDULE_WEBHOOK_RETRY}])

# =============================================================================
# Cleanup Tasks
# =============================================================================

from src.tasks.cleanup.tokens import cleanup_expired_tokens  # noqa: E402

cleanup_expired_tokens = _schedule_task(cleanup_expired_tokens, [{"cron": SCHEDULE_CLEANUP}])

from src.tasks.cleanup.audit_logs import cleanup_audit_logs  # noqa: E402

cleanup_audit_logs = _schedule_task(cleanup_audit_logs, [{"cron": SCHEDULE_CLEANUP_WEEKLY}])

from src.tasks.cleanup.webhook_logs import cleanup_webhook_logs  # noqa: E402

cleanup_webhook_logs = _schedule_task(cleanup_webhook_logs, [{"cron": SCHEDULE_CLEANUP_WEBHOOK_WEEKLY}])

from src.tasks.cleanup.notifications import cleanup_notifications  # noqa: E402

cleanup_notifications = _schedule_task(cleanup_notifications, [{"cron": SCHEDULE_CLEANUP_NOTIFICATIONS}])

from src.tasks.cleanup.cache import cleanup_cache  # noqa: E402

cleanup_cache = _schedule_task(cleanup_cache, [{"cron": SCHEDULE_CLEANUP_CACHE}])

# =============================================================================
# Sync Tasks
# =============================================================================

from src.tasks.sync.geolocations import sync_server_geolocations  # noqa: E402

sync_server_geolocations = _schedule_task(sync_server_geolocations, [{"cron": SCHEDULE_SYNC_GEOLOCATIONS}])

from src.tasks.sync.user_stats import sync_user_stats  # noqa: E402

sync_user_stats = _schedule_task(sync_user_stats, [{"cron": SCHEDULE_SYNC_USER_STATS}])

from src.tasks.sync.node_configs import sync_node_configurations  # noqa: E402

sync_node_configurations = _schedule_task(sync_node_configurations, [{"cron": SCHEDULE_SYNC_NODE_CONFIGS}])

# =============================================================================
# Report Tasks
# =============================================================================

from src.tasks.reports.daily_report import send_daily_report  # noqa: E402

send_daily_report = _schedule_task(send_daily_report, [{"cron": SCHEDULE_REPORT_DAILY}])

from src.tasks.reports.weekly_report import generate_weekly_report  # noqa: E402

generate_weekly_report = _schedule_task(generate_weekly_report, [{"cron": SCHEDULE_REPORT_WEEKLY}])

from src.tasks.reports.anomaly_alert import check_anomalies  # noqa: E402

check_anomalies = _schedule_task(check_anomalies, [{"cron": SCHEDULE_ANOMALY_CHECK}])


def register_schedules() -> None:
    """Log schedule registration. Tasks are auto-discovered via labels."""
    logger.info(
        "schedules_registered",
        total=26,
        categories=[
            "notifications",
            "monitoring",
            "subscriptions",
            "analytics",
            "payments",
            "cleanup",
            "sync",
            "reports",
        ],
    )
