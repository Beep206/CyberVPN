"""External services health check task."""

from datetime import datetime, timezone

import structlog

from src.broker import broker
from src.database.session import check_db_connection
from src.services.cache_service import CacheService
from src.services.redis_client import check_redis, get_redis_client
from src.services.remnawave_client import RemnawaveClient
from src.services.telegram_client import TelegramClient
from src.utils.constants import HEALTH_SERVICE_KEY
from src.utils.formatting import service_down, service_recovered

logger = structlog.get_logger(__name__)


@broker.task(task_name="check_external_services", queue="monitoring")
async def check_external_services() -> dict:
    """Check availability of PostgreSQL, Redis, Remnawave, and Telegram.

    Performs health checks on all critical external services and compares results
    to the previous state. Sends Telegram alerts when services go down or recover.

    Returns:
        Dictionary with boolean health status for each service:
        - database: PostgreSQL connection health
        - redis: Redis connection health
        - remnawave: Remnawave API health
        - telegram: Telegram Bot API health
    """
    redis = get_redis_client()
    cache = CacheService(redis)
    results = {}

    try:
        # Check DB
        results["database"] = await check_db_connection()

        # Check Redis
        results["redis"] = await check_redis()

        # Check Remnawave
        try:
            async with RemnawaveClient() as client:
                results["remnawave"] = await client.health_check()
        except Exception:
            results["remnawave"] = False

        # Check Telegram
        try:
            async with TelegramClient() as tg:
                results["telegram"] = await tg.health_check()
        except Exception:
            results["telegram"] = False

        now_ts = int(datetime.now(timezone.utc).timestamp())

        async with TelegramClient() as tg:
            for svc, is_up in results.items():
                service_key = HEALTH_SERVICE_KEY.format(service_name=svc)
                prev = await cache.get(service_key) or {}
                was_up = prev.get("is_up", True)
                prev_failures = int(prev.get("consecutive_failures", 0))

                if is_up:
                    consecutive_failures = 0
                    if not was_up:
                        alert = service_recovered(svc)
                        await tg.send_admin_alert(alert, severity="resolved")
                        logger.info("service_recovered", service=svc)
                else:
                    consecutive_failures = prev_failures + 1
                    if consecutive_failures == 3:
                        alert = service_down(svc, consecutive_failures)
                        await tg.send_admin_alert(alert, severity="critical")
                        logger.error("service_down", service=svc, consecutive_failures=consecutive_failures)

                await cache.set(
                    service_key,
                    {
                        "is_up": is_up,
                        "consecutive_failures": consecutive_failures,
                        "last_checked": now_ts,
                    },
                    ttl=600,
                )
    finally:
        await redis.aclose()

    logger.info("services_health_checked", results=results)
    return results
