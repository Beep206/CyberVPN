"""Schedule definitions for all periodic tasks.

Registers cron schedules for every periodic task in the worker.
TaskIQ reads the ``schedule`` label and dispatches tasks accordingly.
"""

# ruff: noqa: E402

from typing import Any, cast

import structlog

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
    SCHEDULE_GROWTH_REPORTING_CLEANUP,
    SCHEDULE_GROWTH_REPORTING_DELIVERY,
    SCHEDULE_GROWTH_REPORTING_GOVERNANCE_FOLLOWUP,
    SCHEDULE_GROWTH_REPORTING_REFRESH,
    SCHEDULE_HEALTH_CHECK,
    SCHEDULE_HELIX_ACTUATIONS,
    SCHEDULE_HELIX_CANARY_CONTROL,
    SCHEDULE_HELIX_CANARY_GATES,
    SCHEDULE_HELIX_HEALTH,
    SCHEDULE_HELIX_ROLLOUTS,
    SCHEDULE_HOURLY_BANDWIDTH,
    SCHEDULE_PARTNER_BOT_PROVISIONING,
    SCHEDULE_PAYMENT_VERIFY,
    SCHEDULE_PUBLIC_NETWORK_DPI_SCORE,
    SCHEDULE_QUEUE_DEPTH,
    SCHEDULE_REPORT_DAILY,
    SCHEDULE_REPORT_WEEKLY,
    SCHEDULE_SERVICES_HEALTH,
    SCHEDULE_STAGE1_PAYMENT_RECONCILIATION,
    SCHEDULE_SUBSCRIPTION_CHECK,
    SCHEDULE_SYNC_GEOLOCATIONS,
    SCHEDULE_SYNC_NODE_CONFIGS,
    SCHEDULE_SYNC_USER_STATS,
    SCHEDULE_TELEGRAM_STARS_RECONCILIATION,
    SCHEDULE_TRAFFIC_RESET,
    SCHEDULE_WEBHOOK_RETRY,
)

logger = structlog.get_logger(__name__)


def _schedule_task(task: Any, schedule: list[dict]) -> Any:
    """Attach schedule labels to a task.

    TaskIQ's runtime supports ``with_labels``, but type stubs may not.
    Casting to ``Any`` keeps type checkers quiet.
    """
    task_obj = cast(Any, task)
    if hasattr(task_obj, "with_labels"):
        return task_obj.with_labels(schedule=schedule)

    labels = getattr(task_obj, "labels", None)
    if isinstance(labels, dict):
        labels["schedule"] = schedule
    else:
        task_obj.labels = {"schedule": schedule}

    return task_obj


# =============================================================================
# Notification Tasks
# =============================================================================

from src.tasks.notifications.process_queue import (
    process_notification_queue,
)

process_notification_queue = _schedule_task(
    process_notification_queue, [{"interval": INTERVAL_NOTIFICATION_QUEUE_SECONDS}]
)

from src.tasks.email.process_growth_notification_deliveries import (
    process_growth_notification_deliveries,
)

process_growth_notification_deliveries = _schedule_task(
    process_growth_notification_deliveries,
    [{"interval": INTERVAL_NOTIFICATION_QUEUE_SECONDS}],
)

from src.tasks.email.process_growth_reporting_deliveries import (
    process_growth_reporting_deliveries,
)

process_growth_reporting_deliveries = _schedule_task(
    process_growth_reporting_deliveries,
    [{"cron": SCHEDULE_GROWTH_REPORTING_DELIVERY}],
)

# =============================================================================
# Monitoring Tasks
# =============================================================================

from src.tasks.monitoring.health_check import check_server_health

check_server_health = _schedule_task(check_server_health, [{"cron": SCHEDULE_HEALTH_CHECK}])

from src.tasks.monitoring.services_health import check_external_services

check_external_services = _schedule_task(check_external_services, [{"cron": SCHEDULE_SERVICES_HEALTH}])

from src.tasks.monitoring.bandwidth import collect_bandwidth_snapshot

collect_bandwidth_snapshot = _schedule_task(collect_bandwidth_snapshot, [{"cron": SCHEDULE_BANDWIDTH}])

from src.tasks.monitoring.queue_depth import monitor_queue_depth

monitor_queue_depth = _schedule_task(monitor_queue_depth, [{"cron": SCHEDULE_QUEUE_DEPTH}])

from src.tasks.monitoring.publish_public_network_dpi_score import (
    publish_public_network_dpi_score,
)

publish_public_network_dpi_score = _schedule_task(
    publish_public_network_dpi_score, [{"cron": SCHEDULE_PUBLIC_NETWORK_DPI_SCORE}]
)

from src.tasks.monitoring.helix_health import (
    audit_helix_health,
)

audit_helix_health = _schedule_task(audit_helix_health, [{"cron": SCHEDULE_HELIX_HEALTH}])

from src.tasks.monitoring.helix_actuations import (
    audit_helix_actuations,
)

audit_helix_actuations = _schedule_task(audit_helix_actuations, [{"cron": SCHEDULE_HELIX_ACTUATIONS}])

from src.tasks.monitoring.helix_canary_gates import (
    audit_helix_canary_gates,
)

audit_helix_canary_gates = _schedule_task(audit_helix_canary_gates, [{"cron": SCHEDULE_HELIX_CANARY_GATES}])

from src.tasks.monitoring.helix_canary_control import (
    audit_helix_canary_control,
)

audit_helix_canary_control = _schedule_task(audit_helix_canary_control, [{"cron": SCHEDULE_HELIX_CANARY_CONTROL}])

# =============================================================================
# Subscription Tasks
# =============================================================================

from src.tasks.subscriptions.check_expiring import (
    check_expiring_subscriptions,
)

check_expiring_subscriptions = _schedule_task(check_expiring_subscriptions, [{"cron": SCHEDULE_SUBSCRIPTION_CHECK}])

from src.tasks.subscriptions.disable_expired import disable_expired_users

disable_expired_users = _schedule_task(disable_expired_users, [{"cron": SCHEDULE_DISABLE_EXPIRED}])

from src.tasks.subscriptions.auto_renew import auto_renew_subscriptions

auto_renew_subscriptions = _schedule_task(auto_renew_subscriptions, [{"cron": SCHEDULE_AUTO_RENEW}])

from src.tasks.subscriptions.reset_traffic import reset_monthly_traffic

reset_monthly_traffic = _schedule_task(reset_monthly_traffic, [{"cron": SCHEDULE_TRAFFIC_RESET}])

# =============================================================================
# Analytics Tasks
# =============================================================================

from src.tasks.analytics.daily_stats import aggregate_daily_stats

aggregate_daily_stats = _schedule_task(aggregate_daily_stats, [{"cron": SCHEDULE_DAILY_STATS}])

from src.tasks.analytics.financial_stats import aggregate_financial_stats

aggregate_financial_stats = _schedule_task(aggregate_financial_stats, [{"cron": SCHEDULE_FINANCIAL_STATS}])

from src.tasks.analytics.refresh_growth_reporting import refresh_growth_reporting_rollups

refresh_growth_reporting_rollups = _schedule_task(
    refresh_growth_reporting_rollups, [{"cron": SCHEDULE_GROWTH_REPORTING_REFRESH}]
)

from src.tasks.analytics.process_growth_reporting_governance_followups import (
    process_growth_reporting_governance_followups,
)

process_growth_reporting_governance_followups = _schedule_task(
    process_growth_reporting_governance_followups,
    [{"cron": SCHEDULE_GROWTH_REPORTING_GOVERNANCE_FOLLOWUP}],
)

from src.tasks.analytics.cleanup_growth_reporting import cleanup_growth_reporting_artifacts

cleanup_growth_reporting_artifacts = _schedule_task(
    cleanup_growth_reporting_artifacts,
    [{"cron": SCHEDULE_GROWTH_REPORTING_CLEANUP}],
)

from src.tasks.analytics.hourly_bandwidth import (
    aggregate_hourly_bandwidth,
)

aggregate_hourly_bandwidth = _schedule_task(aggregate_hourly_bandwidth, [{"cron": SCHEDULE_HOURLY_BANDWIDTH}])

from src.tasks.analytics.realtime_metrics import update_realtime_metrics

update_realtime_metrics = _schedule_task(update_realtime_metrics, [{"interval": INTERVAL_REALTIME_METRICS_SECONDS}])

# =============================================================================
# Payment Tasks
# =============================================================================

from src.tasks.payments.verify_pending import verify_pending_payments

verify_pending_payments = _schedule_task(verify_pending_payments, [{"cron": SCHEDULE_PAYMENT_VERIFY}])

from src.tasks.payments.reconcile_stage1 import reconcile_stage1_payments

reconcile_stage1_payments = _schedule_task(
    reconcile_stage1_payments, [{"cron": SCHEDULE_STAGE1_PAYMENT_RECONCILIATION}]
)

from src.tasks.payments.reconcile_telegram_stars import (
    reconcile_telegram_stars_refunds,
)

reconcile_telegram_stars_refunds = _schedule_task(
    reconcile_telegram_stars_refunds, [{"cron": SCHEDULE_TELEGRAM_STARS_RECONCILIATION}]
)

from src.tasks.payments.retry_webhooks import retry_failed_webhooks

retry_failed_webhooks = _schedule_task(retry_failed_webhooks, [{"cron": SCHEDULE_WEBHOOK_RETRY}])

# =============================================================================
# Partner Bot Tasks
# =============================================================================

from src.tasks.partner_bots.process_provisioning_jobs import (
    process_partner_bot_provisioning_jobs,
)

process_partner_bot_provisioning_jobs = _schedule_task(
    process_partner_bot_provisioning_jobs, [{"cron": SCHEDULE_PARTNER_BOT_PROVISIONING}]
)

# =============================================================================
# Cleanup Tasks
# =============================================================================

from src.tasks.cleanup.tokens import cleanup_expired_tokens

cleanup_expired_tokens = _schedule_task(cleanup_expired_tokens, [{"cron": SCHEDULE_CLEANUP}])

from src.tasks.cleanup.audit_logs import cleanup_audit_logs

cleanup_audit_logs = _schedule_task(cleanup_audit_logs, [{"cron": SCHEDULE_CLEANUP_WEEKLY}])

from src.tasks.cleanup.webhook_logs import cleanup_webhook_logs

cleanup_webhook_logs = _schedule_task(cleanup_webhook_logs, [{"cron": SCHEDULE_CLEANUP_WEBHOOK_WEEKLY}])

from src.tasks.cleanup.notifications import cleanup_notifications

cleanup_notifications = _schedule_task(cleanup_notifications, [{"cron": SCHEDULE_CLEANUP_NOTIFICATIONS}])

from src.tasks.cleanup.cache import cleanup_cache

cleanup_cache = _schedule_task(cleanup_cache, [{"cron": SCHEDULE_CLEANUP_CACHE}])

# =============================================================================
# Sync Tasks
# =============================================================================

from src.tasks.sync.geolocations import sync_server_geolocations

sync_server_geolocations = _schedule_task(sync_server_geolocations, [{"cron": SCHEDULE_SYNC_GEOLOCATIONS}])

from src.tasks.sync.user_stats import sync_user_stats

sync_user_stats = _schedule_task(sync_user_stats, [{"cron": SCHEDULE_SYNC_USER_STATS}])

from src.tasks.sync.node_configs import sync_node_configurations

sync_node_configurations = _schedule_task(sync_node_configurations, [{"cron": SCHEDULE_SYNC_NODE_CONFIGS}])

from src.tasks.sync.helix_rollouts import (
    audit_helix_rollouts,
)

audit_helix_rollouts = _schedule_task(audit_helix_rollouts, [{"cron": SCHEDULE_HELIX_ROLLOUTS}])

# =============================================================================
# Report Tasks
# =============================================================================

from src.tasks.reports.daily_report import send_daily_report

send_daily_report = _schedule_task(send_daily_report, [{"cron": SCHEDULE_REPORT_DAILY}])

from src.tasks.reports.weekly_report import generate_weekly_report

generate_weekly_report = _schedule_task(generate_weekly_report, [{"cron": SCHEDULE_REPORT_WEEKLY}])

from src.tasks.reports.anomaly_alert import check_anomalies

check_anomalies = _schedule_task(check_anomalies, [{"cron": SCHEDULE_ANOMALY_CHECK}])


def register_schedules() -> None:
    """Log schedule registration. Tasks are auto-discovered via labels."""
    logger.info(
        "schedules_registered",
        total=32,
        categories=[
            "notifications",
            "monitoring",
            "subscriptions",
            "analytics",
            "payments",
            "cleanup",
            "sync",
            "reports",
            "helix",
        ],
    )
