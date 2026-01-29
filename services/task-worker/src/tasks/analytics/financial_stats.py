"""Daily financial statistics aggregation."""

import structlog
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from src.broker import broker
from src.database.session import get_session_factory
from src.models.payment import PaymentModel
from src.services.cache_service import CacheService
from src.services.redis_client import get_redis_client
from src.utils.constants import STATS_PAYMENTS_KEY

logger = structlog.get_logger(__name__)


@broker.task(task_name="aggregate_financial_stats", queue="analytics")
async def aggregate_financial_stats() -> dict:
    """Aggregate daily payment statistics."""
    factory = get_session_factory()
    redis = get_redis_client()
    cache = CacheService(redis)
    today = datetime.now(timezone.utc).date()
    start = datetime.combine(today - timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
    end = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc)

    try:
        async with factory() as session:
            stmt_currency = (
                select(
                    PaymentModel.currency,
                    func.count(PaymentModel.id).label("count"),
                    func.sum(PaymentModel.amount).label("total"),
                )
                .where(
                    PaymentModel.status == "completed",
                    PaymentModel.created_at >= start,
                    PaymentModel.created_at < end,
                )
                .group_by(PaymentModel.currency)
            )

            stmt_provider = (
                select(
                    PaymentModel.provider,
                    func.count(PaymentModel.id).label("count"),
                    func.sum(PaymentModel.amount).label("total"),
                )
                .where(
                    PaymentModel.status == "completed",
                    PaymentModel.created_at >= start,
                    PaymentModel.created_at < end,
                )
                .group_by(PaymentModel.provider)
            )

            stmt_totals = select(
                func.count(PaymentModel.id).label("count"),
                func.sum(PaymentModel.amount).label("total"),
                func.avg(PaymentModel.amount).label("avg"),
            ).where(
                PaymentModel.status == "completed",
                PaymentModel.created_at >= start,
                PaymentModel.created_at < end,
            )

            result_currency = await session.execute(stmt_currency)
            result_provider = await session.execute(stmt_provider)
            result_totals = await session.execute(stmt_totals)

            currency_rows = result_currency.all()
            provider_rows = result_provider.all()
            totals_row = result_totals.one()

        stats = {
            "date": str(today - timedelta(days=1)),
            "by_currency": {},
            "by_provider": {},
            "total_count": int(totals_row.count or 0),
            "total_revenue": float(totals_row.total or 0),
            "avg_amount": float(totals_row.avg or 0),
        }

        for row in currency_rows:
            stats["by_currency"][row.currency] = {"count": row.count, "total": float(row.total or 0)}

        for row in provider_rows:
            stats["by_provider"][row.provider] = {"count": row.count, "total": float(row.total or 0)}

        key = STATS_PAYMENTS_KEY.format(date=stats["date"])
        await cache.set(key, stats, ttl=90 * 24 * 3600)
    finally:
        await redis.aclose()

    logger.info("financial_stats_aggregated", date=stats["date"], count=stats["total_count"])
    return stats
