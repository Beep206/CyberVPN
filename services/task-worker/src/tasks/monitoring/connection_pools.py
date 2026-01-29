"""Monitor connection pool health for Redis and PostgreSQL.

Periodic task that collects connection pool metrics and exposes them as Prometheus gauges
for monitoring resource utilization and detecting connection leaks.
"""

import structlog
from prometheus_client import Gauge

from src.broker import broker
from src.database.session import get_engine
from src.services.redis_client import get_redis_client

logger = structlog.get_logger(__name__)

# Prometheus metrics for connection pools
REDIS_CONNECTIONS = Gauge("cybervpn_redis_connections", "Number of Redis connections", ["state"])
DB_POOL_SIZE = Gauge("cybervpn_db_pool_size", "Database connection pool size")
DB_POOL_CHECKED_OUT = Gauge("cybervpn_db_pool_checked_out", "Database connections checked out")
DB_POOL_OVERFLOW = Gauge("cybervpn_db_pool_overflow", "Database pool overflow connections")


@broker.task(task_name="monitor_connection_pools", queue="monitoring")
async def monitor_connection_pools() -> dict:
    """Monitor connection pool health for Redis and PostgreSQL.

    Collects metrics about:
    - Redis client connections
    - Database connection pool size and utilization
    - Checked out connections
    - Pool overflow

    Returns:
        Dictionary with pool statistics
    """
    redis_stats = {}
    db_stats = {}

    # Monitor Redis connections
    try:
        redis = get_redis_client()
        try:
            info = await redis.info("clients")
            connected_clients = info.get("connected_clients", 0)
            blocked_clients = info.get("blocked_clients", 0)

            REDIS_CONNECTIONS.labels(state="connected").set(connected_clients)
            REDIS_CONNECTIONS.labels(state="blocked").set(blocked_clients)

            redis_stats = {
                "connected_clients": connected_clients,
                "blocked_clients": blocked_clients,
            }

            logger.debug("redis_pool_monitored", **redis_stats)
        finally:
            await redis.aclose()
    except Exception as e:
        logger.warning("redis_pool_monitor_failed", error=str(e))
        redis_stats = {"error": str(e)}

    # Monitor database connection pool
    try:
        engine = get_engine()
        pool = engine.pool

        # Get pool status
        size = pool.size()
        checked_out = pool.checkedout()
        overflow = pool.overflow()
        checked_in = size - checked_out

        DB_POOL_SIZE.set(size)
        DB_POOL_CHECKED_OUT.set(checked_out)
        DB_POOL_OVERFLOW.set(overflow if overflow > 0 else 0)

        db_stats = {
            "pool_size": size,
            "checked_out": checked_out,
            "checked_in": checked_in,
            "overflow": overflow,
        }

        logger.debug("db_pool_monitored", **db_stats)
    except Exception as e:
        logger.warning("db_pool_monitor_failed", error=str(e))
        db_stats = {"error": str(e)}

    return {
        "redis": redis_stats,
        "database": db_stats,
    }
