"""Generate weekly report with trends compared to previous week."""

import json
from datetime import datetime, timedelta, timezone

import structlog

from src.broker import broker
from src.config import get_settings
from src.services.redis_client import get_redis_client
from src.services.sse_publisher import publish_event
from src.services.telegram_client import TelegramClient
from src.utils.constants import STATS_DAILY_KEY, STATS_PAYMENTS_KEY
from src.utils.formatting import weekly_report

logger = structlog.get_logger(__name__)


@broker.task(task_name="generate_weekly_report", queue="reports")
async def generate_weekly_report() -> dict:
    """Generate weekly report with trends compared to previous week.

    Reads daily stats for the last 7 days and previous 7 days from Redis,
    calculates trends (% change), formats as HTML, and sends via Telegram
    to admins.

    Returns:
        Dictionary with report_sent status
    """
    redis = get_redis_client()
    settings = get_settings()

    try:
        # Calculate date ranges
        today = datetime.now(timezone.utc).date()
        week_end = today - timedelta(days=1)  # Yesterday
        week_start = week_end - timedelta(days=6)  # 7 days ago

        prev_week_end = week_start - timedelta(days=1)
        prev_week_start = prev_week_end - timedelta(days=6)

        # Fetch daily stats for current week
        current_week_stats = []
        date = week_start
        while date <= week_end:
            key = STATS_DAILY_KEY.format(date=date.isoformat())
            data = await redis.get(key)
            if data:
                try:
                    stats = json.loads(data)
                    payments_key = STATS_PAYMENTS_KEY.format(date=date.isoformat())
                    payments_data = await redis.get(payments_key)
                    if payments_data:
                        try:
                            payments_stats = json.loads(payments_data)
                            stats["revenue_usd"] = payments_stats.get("total_revenue", 0)
                        except json.JSONDecodeError:
                            pass
                    current_week_stats.append(stats)
                except json.JSONDecodeError:
                    logger.warning("invalid_stats_json", date=date.isoformat())
            date += timedelta(days=1)

        # Fetch daily stats for previous week
        prev_week_stats = []
        date = prev_week_start
        while date <= prev_week_end:
            key = STATS_DAILY_KEY.format(date=date.isoformat())
            data = await redis.get(key)
            if data:
                try:
                    stats = json.loads(data)
                    payments_key = STATS_PAYMENTS_KEY.format(date=date.isoformat())
                    payments_data = await redis.get(payments_key)
                    if payments_data:
                        try:
                            payments_stats = json.loads(payments_data)
                            stats["revenue_usd"] = payments_stats.get("total_revenue", 0)
                        except json.JSONDecodeError:
                            pass
                    prev_week_stats.append(stats)
                except json.JSONDecodeError:
                    logger.warning("invalid_stats_json", date=date.isoformat())
            date += timedelta(days=1)

        # Aggregate current week
        current_total_users = sum(s.get("total_users", 0) for s in current_week_stats) // max(
            len(current_week_stats), 1
        )
        current_revenue = sum(s.get("revenue_usd", 0) for s in current_week_stats)
        current_bandwidth = sum(s.get("total_bandwidth_bytes", 0) for s in current_week_stats)
        current_uptime = sum(s.get("server_uptime_pct", 0) for s in current_week_stats) / max(
            len(current_week_stats), 1
        )

        # Aggregate previous week
        prev_total_users = sum(s.get("total_users", 0) for s in prev_week_stats) // max(len(prev_week_stats), 1)
        prev_revenue = sum(s.get("revenue_usd", 0) for s in prev_week_stats)

        # Calculate trends (% change)
        user_growth_pct = (
            ((current_total_users - prev_total_users) / prev_total_users * 100) if prev_total_users > 0 else 0
        )
        revenue_growth_pct = ((current_revenue - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else 0

        # Find worst nodes (aggregate incidents_by_node from daily stats)
        node_incidents: dict[str, int] = {}
        for stats in current_week_stats:
            incidents_by_node = stats.get("incidents_by_node") or {}
            for name, count in incidents_by_node.items():
                node_incidents[name] = node_incidents.get(name, 0) + int(count)
        worst_nodes = sorted(node_incidents.items(), key=lambda item: item[1], reverse=True)

        # Format report
        week_label = f"{week_start.isoformat()} to {week_end.isoformat()}"
        report_text = weekly_report(
            week=week_label,
            user_growth_pct=user_growth_pct,
            revenue_growth_pct=revenue_growth_pct,
            total_revenue_usd=current_revenue,
            total_bandwidth_bytes=current_bandwidth,
            avg_uptime_pct=current_uptime,
            worst_nodes=worst_nodes,
        )

        # Send to admins via Telegram
        async with TelegramClient() as tg:
            await tg.send_admin_alert(report_text, severity="info")

        try:
            await publish_event(
                "report.weekly.sent",
                {
                    "week": week_label,
                    "user_growth_pct": user_growth_pct,
                    "revenue_growth_pct": revenue_growth_pct,
                    "total_revenue_usd": current_revenue,
                },
            )
        except Exception:
            logger.warning("weekly_report_sse_failed", week=week_label)

        logger.info(
            "weekly_report_sent",
            week=week_label,
            user_growth=user_growth_pct,
            revenue_growth=revenue_growth_pct,
        )

        return {
            "report_sent": True,
            "week": week_label,
            "user_growth_pct": user_growth_pct,
            "revenue_growth_pct": revenue_growth_pct,
        }

    except Exception as e:
        logger.exception("weekly_report_failed", error=str(e))
        raise
    finally:
        await redis.aclose()
