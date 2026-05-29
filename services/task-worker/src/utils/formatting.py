"""HTML message templates for Telegram notifications.

Provides pre-formatted HTML templates for all notification types used
by the CyberVPN task worker. All templates use Telegram-safe HTML tags:
<b>, <i>, <code>, <pre>, <a>.
"""

from datetime import UTC, datetime
from html import escape

from src.utils.converters import format_bytes, format_duration


def _html(value: object) -> str:
    return escape(str(value), quote=True)


def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")


# =============================================================================
# Subscription Notifications
# =============================================================================


def subscription_expiring(username: str, days_left: int, expire_at: str, renew_url: str = "") -> str:
    """Notification for subscription about to expire."""
    urgency = "🔴" if days_left <= 1 else "🟡" if days_left <= 3 else "🟢"
    msg = (
        f"{urgency} <b>Subscription Expiring</b>\n\n"
        f"User: <code>{_html(username)}</code>\n"
        f"Expires in: <b>{days_left} day{'s' if days_left != 1 else ''}</b>\n"
        f"Expiry date: {_html(expire_at)}\n"
    )
    if renew_url:
        msg += f'\n<a href="{_html(renew_url)}">Renew subscription</a>'
    return msg


def subscription_expired(username: str, expire_at: str) -> str:
    """Notification for expired subscription (user disabled)."""
    return (
        "⛔ <b>Subscription Expired</b>\n\n"
        f"User: <code>{_html(username)}</code>\n"
        f"Expired at: {_html(expire_at)}\n"
        "Your VPN access has been disabled.\n"
        "Please renew your subscription to restore access."
    )


def traffic_reset(username: str, plan_name: str) -> str:
    """Notification for monthly traffic reset."""
    return (
        "🔄 <b>Monthly Traffic Reset</b>\n\n"
        f"User: <code>{_html(username)}</code>\n"
        f"Plan: {_html(plan_name)}\n"
        "Your traffic counter has been reset to zero."
    )


# =============================================================================
# Payment Notifications
# =============================================================================


def payment_received(username: str, amount: float, currency: str, plan_name: str, days: int) -> str:
    """Notification for successful payment."""
    return (
        "✅ <b>Payment Received</b>\n\n"
        f"User: <code>{_html(username)}</code>\n"
        f"Amount: <b>{amount} {_html(currency)}</b>\n"
        f"Plan: {_html(plan_name)} ({days} days)\n"
        f"Time: {_utc_now()}\n"
        "Your subscription has been activated."
    )


def payment_failed(username: str, amount: float, currency: str, reason: str = "") -> str:
    """Notification for failed payment."""
    msg = f"❌ <b>Payment Failed</b>\n\nUser: <code>{_html(username)}</code>\nAmount: {amount} {_html(currency)}\n"
    if reason:
        msg += f"Reason: {_html(reason)}\n"
    msg += "Please try again or contact support."
    return msg


def auto_renew_invoice(username: str, amount: float, currency: str, pay_url: str) -> str:
    """Notification for auto-renewal invoice created."""
    return (
        "💳 <b>Auto-Renewal Invoice</b>\n\n"
        f"User: <code>{_html(username)}</code>\n"
        f"Amount: <b>{amount} {_html(currency)}</b>\n\n"
        f'<a href="{_html(pay_url)}">Pay now</a> to continue your subscription.'
    )


def provisioning_ready(username: str, plan_name: str = "", cabinet_url: str = "") -> str:
    """Notification for VPN access ready after trial/payment provisioning."""
    msg = (
        "🟢 <b>VPN Access Ready</b>\n\n"
        f"User: <code>{_html(username)}</code>\n"
        "Your CyberVPN access is ready.\n"
        "Open CyberVPN to get your QR code, subscription URL or config file."
    )
    if plan_name:
        msg += f"\nPlan: {_html(plan_name)}"
    if cabinet_url:
        msg += f'\n\n<a href="{_html(cabinet_url)}">Open CyberVPN</a>'
    return msg


def provisioning_failed(username: str, support_reference: str = "", retry_hint: str = "") -> str:
    """Notification for delayed VPN provisioning after trial/payment."""
    msg = (
        "🟠 <b>VPN Access Delayed</b>\n\n"
        f"User: <code>{_html(username)}</code>\n"
        "Your payment or trial was accepted, but VPN access is not ready yet.\n"
        "We are retrying automatically and support has been notified."
    )
    if retry_hint:
        msg += f"\nRetry status: {_html(retry_hint)}"
    if support_reference:
        msg += f"\nSupport reference: <code>{_html(support_reference)}</code>"
    return msg


# =============================================================================
# Server / Infrastructure Alerts
# =============================================================================


def server_down(node_name: str, country: str, downtime_seconds: int = 0) -> str:
    """Alert for VPN node going offline."""
    msg = f"🚨 <b>SERVER DOWN</b>\n\nNode: <code>{node_name}</code>\nLocation: {country}\nDetected at: {_utc_now()}\n"
    if downtime_seconds:
        msg += f"Downtime: {format_duration(downtime_seconds)}\n"
    return msg


def server_recovered(node_name: str, country: str, downtime_seconds: int = 0) -> str:
    """Alert for VPN node recovered."""
    msg = (
        "✅ <b>SERVER RECOVERED</b>\n\n"
        f"Node: <code>{node_name}</code>\n"
        f"Location: {country}\n"
        f"Recovered at: {_utc_now()}\n"
    )
    if downtime_seconds:
        msg += f"Total downtime: {format_duration(downtime_seconds)}\n"
    return msg


def service_down(service_name: str, consecutive_failures: int) -> str:
    """Alert for external service unavailable."""
    return (
        "🔥 <b>SERVICE UNAVAILABLE</b>\n\n"
        f"Service: <code>{service_name}</code>\n"
        f"Consecutive failures: <b>{consecutive_failures}</b>\n"
        f"Time: {_utc_now()}"
    )


def service_recovered(service_name: str) -> str:
    """Alert for external service recovered."""
    return f"✅ <b>SERVICE RECOVERED</b>\n\nService: <code>{service_name}</code>\nRecovered at: {_utc_now()}"


# =============================================================================
# Bulk Operation Notifications
# =============================================================================


def bulk_operation_complete(
    operation: str,
    total: int,
    processed: int,
    failed: int,
    initiated_by: str,
    duration_seconds: float = 0,
) -> str:
    """Summary notification for completed bulk operation."""
    success = processed - failed
    status_emoji = "✅" if failed == 0 else "⚠️" if failed < total * 0.1 else "❌"
    msg = (
        f"{status_emoji} <b>Bulk Operation Complete</b>\n\n"
        f"Operation: <code>{operation}</code>\n"
        f"Total: {total}\n"
        f"Success: {success}\n"
        f"Failed: {failed}\n"
    )
    if duration_seconds:
        msg += f"Duration: {format_duration(int(duration_seconds))}\n"
    msg += f"Initiated by: {initiated_by}"
    return msg


# =============================================================================
# Report Templates
# =============================================================================


def daily_report(
    date: str,
    total_users: int,
    active_users: int,
    new_users: int,
    churned_users: int,
    revenue_usd: float,
    total_bandwidth_bytes: int,
    server_uptime_pct: float,
    incidents: int,
    top_errors: list[str] | None = None,
) -> str:
    """Daily summary report for admins."""
    msg = (
        f"📊 <b>Daily Report — {date}</b>\n\n"
        "<b>Users</b>\n"
        f"  Total: {total_users}\n"
        f"  Active: {active_users}\n"
        f"  New: +{new_users}\n"
        f"  Churned: -{churned_users}\n\n"
        "<b>Revenue</b>\n"
        f"  Total: <b>${revenue_usd:.2f}</b>\n\n"
        "<b>Infrastructure</b>\n"
        f"  Bandwidth: {format_bytes(total_bandwidth_bytes)}\n"
        f"  Uptime: {server_uptime_pct:.1f}%\n"
        f"  Incidents: {incidents}\n"
    )
    if top_errors:
        msg += "\n<b>Top Errors</b>\n"
        for i, err in enumerate(top_errors[:5], 1):
            msg += f"  {i}. <code>{err}</code>\n"
    return msg


def weekly_report(
    week: str,
    user_growth_pct: float,
    revenue_growth_pct: float,
    total_revenue_usd: float,
    total_bandwidth_bytes: int,
    avg_uptime_pct: float,
    worst_nodes: list[tuple[str, int]] | None = None,
) -> str:
    """Weekly summary report with trends."""
    user_trend = "📈" if user_growth_pct >= 0 else "📉"
    rev_trend = "📈" if revenue_growth_pct >= 0 else "📉"
    msg = (
        f"📋 <b>Weekly Report — {week}</b>\n\n"
        "<b>Trends</b>\n"
        f"  {user_trend} Users: {user_growth_pct:+.1f}%\n"
        f"  {rev_trend} Revenue: {revenue_growth_pct:+.1f}% (${total_revenue_usd:.2f})\n\n"
        "<b>Infrastructure</b>\n"
        f"  Total bandwidth: {format_bytes(total_bandwidth_bytes)}\n"
        f"  Avg uptime: {avg_uptime_pct:.1f}%\n"
    )
    if worst_nodes:
        msg += "\n<b>Worst Nodes (by incidents)</b>\n"
        for name, count in worst_nodes[:5]:
            msg += f"  <code>{name}</code>: {count} incidents\n"
    return msg


# =============================================================================
# System Alerts
# =============================================================================


def anomaly_alert(metric: str, current_value: str, threshold: str, severity: str = "warning") -> str:
    """Alert for anomalous metric values."""
    emoji = {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}.get(severity, "⚠️")  # noqa: RUF001
    return (
        f"{emoji} <b>Anomaly Detected</b> [{severity.upper()}]\n\n"
        f"Metric: <code>{metric}</code>\n"
        f"Current: <b>{current_value}</b>\n"
        f"Threshold: {threshold}\n"
        f"Time: {_utc_now()}"
    )


def worker_error(task_name: str, error_type: str, error_message: str, task_id: str = "") -> str:
    """Alert for critical task worker error."""
    msg = (
        "🔥 <b>Worker Error</b>\n\n"
        f"Task: <code>{task_name}</code>\n"
        f"Error: <code>{error_type}</code>\n"
        f"Message: {error_message[:500]}\n"
        f"Time: {_utc_now()}"
    )
    if task_id:
        msg += f"\nTask ID: <code>{task_id}</code>"
    return msg
