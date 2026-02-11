"""TaskIQ broker configuration with Redis backend.

Provides RedisStreamBroker with async result backend, schedule source, and lifecycle hooks.
Uses lazy initialization pattern to defer expensive operations until broker startup.
Implements production-grade error handling and resource cleanup.
"""

import platform

import httpx
import structlog
from taskiq import TaskiqEvents, TaskiqScheduler
from taskiq.schedule_sources import LabelScheduleSource
from taskiq_redis import ListRedisScheduleSource, RedisAsyncResultBackend, RedisStreamBroker

from src.config import get_settings
from src.database.session import get_engine, get_session_factory
from src.logging_config import configure_logging
from src.metrics import WORKER_INFO
from src.metrics_server import start_metrics_server
from src.middleware import (
    ErrorHandlerMiddleware,
    LoggingMiddleware,
    MetricsMiddleware,
    RetryMiddleware,
)

# Configure structured JSON logging before anything else
configure_logging()

logger = structlog.get_logger(__name__)

# Lazy initialization: settings loaded on first access
settings = get_settings()

# Initialize RedisStreamBroker with Redis URL from settings
broker = RedisStreamBroker(url=settings.redis_url)

# Configure async result backend with TTL
result_backend = RedisAsyncResultBackend(
    redis_url=settings.redis_url,
    result_ex_time=settings.result_ttl_seconds,
)
broker = broker.with_result_backend(result_backend)

# Configure default task timeout (5 minutes = 300 seconds)
# Tasks running longer than this will be cancelled automatically
# Note: with_labels removed in newer taskiq versions - set labels per task instead
# broker = broker.with_labels(timeout=300)

# Register middleware chain.
# Order: Logging (captures all) → Metrics (timing) → ErrorHandler (alerts) → Retry (re-queue)
broker.add_middlewares(
    [
        LoggingMiddleware(),
        MetricsMiddleware(),
        ErrorHandlerMiddleware(),
        RetryMiddleware(),
    ],
)

# Initialize schedule source with ListRedisScheduleSource (latest durable variant)
schedule_source = ListRedisScheduleSource(url=settings.redis_url)

# Create TaskiqScheduler with Redis + label-based schedule sources
scheduler = TaskiqScheduler(broker, sources=[schedule_source, LabelScheduleSource(broker)])


@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def startup_event(state) -> None:
    """Initialize shared resources on worker startup.

    Creates and stores in broker.state:
    - Database engine and session factory
    - Shared httpx.AsyncClient for external API calls
    - Prometheus metrics HTTP server

    Logs initialization status for monitoring and debugging.
    """
    try:
        logger.info("worker_startup_initiated", redis_url=settings.redis_url)

        # Initialize Sentry SDK if DSN is configured
        if settings.sentry_dsn:
            import sentry_sdk

            sentry_sdk.init(
                dsn=settings.sentry_dsn,
                environment=settings.environment,
                traces_sample_rate=1.0 if settings.environment == "development" else 0.1,
                profiles_sample_rate=1.0 if settings.environment == "development" else 0.1,
            )
            logger.info("sentry_initialized", environment=settings.environment)

        # Start Prometheus metrics HTTP server
        if settings.metrics_enabled:
            start_metrics_server(
                port=settings.metrics_port,
                protect=settings.metrics_protect,
                allowed_ips=settings.metrics_allowed_ips,
                basic_auth_user=settings.metrics_basic_auth_user,
                basic_auth_password=(
                    settings.metrics_basic_auth_password.get_secret_value()
                    if settings.metrics_basic_auth_password
                    else None
                ),
            )

        # Set worker information metrics
        WORKER_INFO.info(
            {
                "version": "1.0.0",
                "environment": settings.environment,
                "python_version": platform.python_version(),
                "platform": platform.system(),
                "concurrency": str(settings.worker_concurrency),
            }
        )

        # Initialize database engine (cached via lru_cache)
        engine = get_engine()
        state.db_engine = engine

        # Initialize session factory (cached via lru_cache)
        session_factory = get_session_factory()
        state.db_session_factory = session_factory

        logger.info("database_engine_initialized", pool_size=10, max_overflow=20)

        # Initialize shared httpx client for external API calls
        state.http_client = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
            headers={"User-Agent": "CyberVPN-TaskWorker/1.0"},
        )

        logger.info(
            "worker_startup_complete",
            http_timeout=30.0,
            http_max_connections=100,
        )

    except Exception as exc:
        logger.exception("worker_startup_failed", error=str(exc))
        raise


@broker.on_event(TaskiqEvents.WORKER_SHUTDOWN)
async def shutdown_event(state) -> None:
    """Clean up resources on worker shutdown.

    Closes httpx client and disposes database engine to ensure graceful shutdown.
    Implements proper error handling to prevent shutdown hangs.
    """
    try:
        logger.info("worker_shutdown_initiated")

        # Close httpx client
        if hasattr(state, "http_client"):
            await state.http_client.aclose()
            logger.info("http_client_closed")

        # Dispose database engine
        if hasattr(state, "db_engine"):
            await state.db_engine.dispose()
            logger.info("database_engine_disposed")

        logger.info("worker_shutdown_complete")

    except Exception as exc:
        logger.exception("worker_shutdown_failed", error=str(exc))
        # Don't re-raise during shutdown to allow other cleanup to proceed


# Import tasks at module end to register them with broker
# This avoids circular imports while ensuring tasks are discovered
import src.tasks  # noqa: F401, E402
