"""Daily business metrics aggregation."""

import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import func, select

from src.broker import broker
from src.database.session import get_session_factory
from src.models.audit_log import AuditLogModel
from src.models.payment import PaymentModel
from src.models.webhook_log import WebhookLogModel
from src.services.cache_service import CacheService
from src.services.redis_client import get_redis_client
from src.services.remnawave_client import RemnawaveClient
from src.utils.constants import REDIS_PREFIX, STATS_DAILY_KEY

logger = structlog.get_logger(__name__)


@broker.task(task_name="aggregate_daily_stats", queue="analytics")
async def aggregate_daily_stats() -> dict:
    """Collect daily business metrics and cache them in Redis."""
    redis = get_redis_client()
    cache = CacheService(redis)

    try:
        async with RemnawaveClient() as rw:
            users = await rw.get_users()
            await rw.get_system_stats()

        now = datetime.now(timezone.utc)
        today = now.date()
        start = datetime.combine(today - timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
        end = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc)

        total_users = len(users)
        active_users = sum(1 for u in users if u.get("status") == "active")
        disabled_users = sum(1 for u in users if u.get("status") == "disabled")
        expired_users = 0
        limited_users = 0
        online_users = sum(1 for u in users if u.get("isOnline", False))
        total_bandwidth = sum(u.get("usedTrafficBytes", 0) or 0 for u in users)

        for user in users:
            expire_at = user.get("expiresAt")
            if expire_at:
                try:
                    exp_dt = datetime.fromisoformat(expire_at.replace("Z", "+00:00"))
                    if exp_dt < now:
                        expired_users += 1
                except (ValueError, TypeError):
                    pass

            data_limit = user.get("dataLimit", 0)
            data_used = user.get("dataUsed", 0)
            if data_limit and data_used >= data_limit:
                limited_users += 1

        new_users = 0
        churned_users = 0
        admin_ops = 0
        revenue_total = 0.0
        revenue_by_provider: dict[str, float] = defaultdict(float)
        revenue_by_plan: dict[str, float] = defaultdict(float)
        top_errors: list[str] = []

        session_factory = get_session_factory()
        async with session_factory() as session:
            new_users_stmt = (
                select(func.count())
                .select_from(AuditLogModel)
                .where(
                    AuditLogModel.action == "user.created",
                    AuditLogModel.created_at >= start,
                    AuditLogModel.created_at < end,
                )
            )
            new_users = (await session.execute(new_users_stmt)).scalar() or 0

            admin_ops_stmt = (
                select(func.count())
                .select_from(AuditLogModel)
                .where(
                    AuditLogModel.admin_id.is_not(None),
                    AuditLogModel.created_at >= start,
                    AuditLogModel.created_at < end,
                )
            )
            admin_ops = (await session.execute(admin_ops_stmt)).scalar() or 0

            updated_stmt = select(AuditLogModel).where(
                AuditLogModel.action == "user.updated",
                AuditLogModel.created_at >= start,
                AuditLogModel.created_at < end,
            )
            updated_logs = (await session.execute(updated_stmt)).scalars().all()
            for log in updated_logs:
                new_value = log.new_value or {}
                if new_value.get("status") in {"disabled", "expired"}:
                    churned_users += 1

            payments_stmt = select(PaymentModel).where(
                PaymentModel.status == "completed",
                PaymentModel.created_at >= start,
                PaymentModel.created_at < end,
            )
            payments = (await session.execute(payments_stmt)).scalars().all()
            for payment in payments:
                amount = float(payment.amount)
                revenue_total += amount
                revenue_by_provider[payment.provider] += amount
                plan_name = ""
                if payment.metadata_ and isinstance(payment.metadata_, dict):
                    plan_name = payment.metadata_.get("plan_name") or payment.metadata_.get("planName") or ""
                revenue_by_plan[plan_name or "unknown"] += amount

            errors_stmt = select(WebhookLogModel.error_message).where(
                WebhookLogModel.error_message.is_not(None),
                WebhookLogModel.created_at >= start,
                WebhookLogModel.created_at < end,
            )
            error_rows = (await session.execute(errors_stmt)).all()
            error_messages = [row[0] for row in error_rows if row[0]]
            error_counts = Counter(error_messages)
            top_errors = [err for err, _ in error_counts.most_common(5)]

        incidents = 0
        incidents_by_node: dict[str, int] = defaultdict(int)
        offline_seconds = 0
        node_count = 0
        window_seconds = 24 * 3600
        start_ts = int(start.timestamp())
        end_ts = int(end.timestamp())

        cursor = 0
        while True:
            cursor, keys = await redis.scan(cursor, match=f"{REDIS_PREFIX}health:*:current", count=100)
            for key in keys:
                data = await redis.get(key)
                if not data:
                    continue
                try:
                    health = json.loads(data)
                except json.JSONDecodeError:
                    continue

                node_count += 1
                status = health.get("status")
                if status == "offline":
                    offline_since = health.get("offline_since") or health.get("last_seen")
                    if offline_since:
                        try:
                            duration = int(end_ts - int(offline_since))
                            offline_seconds += max(0, min(duration, window_seconds))
                        except (TypeError, ValueError):
                            pass

            if cursor == 0:
                break

        cursor = 0
        while True:
            cursor, keys = await redis.scan(cursor, match=f"{REDIS_PREFIX}health:*:history", count=100)
            for key in keys:
                events = await redis.zrangebyscore(key, start_ts, end_ts)
                for event in events:
                    try:
                        payload = json.loads(event)
                    except json.JSONDecodeError:
                        continue
                    if payload.get("status") == "offline":
                        incidents += 1
                        node_name = payload.get("name", "unknown")
                        incidents_by_node[node_name] += 1
            if cursor == 0:
                break

        if node_count:
            uptime_pct = max(0.0, min(100.0, 100 - (offline_seconds / (node_count * window_seconds) * 100)))
        else:
            uptime_pct = 100.0

        stats = {
            "date": start.strftime("%Y-%m-%d"),
            "total_users": total_users,
            "active_users": active_users,
            "disabled_users": disabled_users,
            "expired_users": expired_users,
            "limited_users": limited_users,
            "online_users": online_users,
            "new_users": new_users,
            "churned_users": churned_users,
            "revenue_usd": revenue_total,
            "revenue_by_provider": dict(revenue_by_provider),
            "revenue_by_plan": dict(revenue_by_plan),
            "total_bandwidth_bytes": total_bandwidth,
            "server_uptime_pct": uptime_pct,
            "incidents": incidents,
            "incidents_by_node": dict(incidents_by_node),
            "admin_ops": admin_ops,
            "top_errors": top_errors,
        }

        cache_key = STATS_DAILY_KEY.format(date=stats["date"])
        await cache.set(cache_key, stats, ttl=90 * 24 * 3600)
    finally:
        await redis.aclose()

    logger.info("daily_stats_aggregated", stats=stats)
    return stats
