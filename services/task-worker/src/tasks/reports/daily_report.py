"""Send daily admin report via Telegram."""

import structlog
from datetime import datetime, timedelta, timezone

from src.broker import broker
from src.services.cache_service import CacheService
from src.services.redis_client import get_redis_client
from src.services.sse_publisher import publish_event
from src.services.telegram_client import TelegramClient
from src.utils.constants import STATS_DAILY_KEY, STATS_PAYMENTS_KEY
from src.utils.formatting import daily_report

logger = structlog.get_logger(__name__)


@broker.task(task_name="send_daily_report", queue="reports")
async def send_daily_report() -> dict:
    """Generate and send daily summary report to admin chat."""
    redis = get_redis_client()
    cache = CacheService(redis)

    try:
        target_date = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()
        stats_key = STATS_DAILY_KEY.format(date=target_date)
        payments_key = STATS_PAYMENTS_KEY.format(date=target_date)

        stats = await cache.get(stats_key)
        payments = await cache.get(payments_key)

        if not stats:
            logger.warning("no_daily_stats_available", date=target_date)
            return {"sent": False, "reason": "no_stats"}

        revenue_total = 0.0
        if payments:
            revenue_total = float(payments.get("total_revenue", 0.0))

        report = daily_report(
            date=stats.get("date", target_date),
            total_users=stats.get("total_users", 0),
            active_users=stats.get("active_users", 0),
            new_users=stats.get("new_users", 0),
            churned_users=stats.get("churned_users", 0),
            revenue_usd=revenue_total,
            total_bandwidth_bytes=stats.get("total_bandwidth_bytes", 0),
            server_uptime_pct=stats.get("server_uptime_pct", 99.9),
            incidents=stats.get("incidents", 0),
            top_errors=stats.get("top_errors"),
        )

        async with TelegramClient() as tg:
            await tg.send_admin_alert(report, severity="info")

        try:
            await publish_event(
                "report.daily.sent",
                {
                    "date": stats.get("date", target_date),
                    "total_users": stats.get("total_users", 0),
                    "active_users": stats.get("active_users", 0),
                    "revenue_usd": revenue_total,
                },
            )
        except Exception:
            logger.warning("daily_report_sse_failed", date=target_date)
    finally:
        await redis.aclose()

    logger.info("daily_report_sent")
    return {"sent": True}
