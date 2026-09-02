"""TaskIQ broker configuration with Redis backend.

Provides RedisStreamBroker with async result backend, schedule source, and lifecycle hooks.
Uses lazy initialization pattern to defer expensive operations until broker startup.
Implements production-grade error handling and resource cleanup.
"""

from __future__ import annotations

import asyncio
import os
import platform
from contextlib import suppress
from typing import Any

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
from src.observability import before_send

# Configure structured JSON logging before anything else
configure_logging()

logger = structlog.get_logger(__name__)

# Lazy initialization: settings loaded on first access
settings = get_settings()

# Initialize RedisStreamBroker with Redis URL from settings
broker = RedisStreamBroker(url=settings.redis_url)

# Configure async result backend with TTL
result_backend: RedisAsyncResultBackend[Any] = RedisAsyncResultBackend(
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
    LoggingMiddleware(),
    MetricsMiddleware(),
    ErrorHandlerMiddleware(),
    RetryMiddleware(),
)

# Initialize schedule source with ListRedisScheduleSource (latest durable variant)
schedule_source = ListRedisScheduleSource(url=settings.redis_url)

# Create TaskiqScheduler with Redis + label-based schedule sources
scheduler = TaskiqScheduler(broker, sources=[schedule_source, LabelScheduleSource(broker)])


async def _start_remnawave_stream_consumer(state: Any) -> None:
    from src.services.backend_api_client import BackendAPIClient
    from src.services.redis_client import create_remnawave_stream_redis_client
    from src.services.remnawave_streams import (
        BackendRemnawaveStreamSink,
        RedisStreamTransport,
        RemnawaveStreamConsumer,
        RemnawaveStreamConsumerConfig,
    )

    backend = BackendAPIClient()
    redis_client = create_remnawave_stream_redis_client()
    try:
        await backend.__aenter__()
        consumer_name = f"{platform.node() or 'worker'}-{os.getpid()}"
        stream_hmac_secret = settings.remnawave_stream_ip_hmac_secret
        if stream_hmac_secret is None:  # Settings validation fails first; keep startup fail closed.
            raise RuntimeError("REMNAWAVE_STREAM_IP_HMAC_SECRET is not configured")
        payload_fingerprint_hmac_key = stream_hmac_secret.get_secret_value().encode("utf-8")
        consumer = RemnawaveStreamConsumer(
            RedisStreamTransport(
                redis_client,
                payload_fingerprint_hmac_key=payload_fingerprint_hmac_key,
            ),
            BackendRemnawaveStreamSink(backend),
            RemnawaveStreamConsumerConfig(
                consumer_name=consumer_name,
                payload_fingerprint_hmac_key=payload_fingerprint_hmac_key,
                group_name=settings.remnawave_stream_consumer_group,
                read_count=settings.remnawave_stream_read_count,
                block_ms=settings.remnawave_stream_block_ms,
                reclaim_count=settings.remnawave_stream_reclaim_count,
                reclaim_min_idle_ms=settings.remnawave_stream_reclaim_min_idle_ms,
                max_delivery_attempts=settings.remnawave_stream_max_delivery_attempts,
                dlq_maxlen=settings.remnawave_stream_dlq_maxlen,
                receipt_retention_days=settings.remnawave_stream_receipt_retention_days,
                checkpoint_observe_interval_seconds=(settings.remnawave_stream_checkpoint_observe_interval_seconds),
            ),
        )
        await consumer.initialize()
    except (Exception, asyncio.CancelledError):
        await backend.__aexit__(None, None, None)
        await redis_client.aclose()
        raise

    state.remnawave_stream_backend = backend
    state.remnawave_stream_redis = redis_client
    state.remnawave_stream_consumer = consumer
    state.remnawave_stream_consumer_task = asyncio.create_task(
        consumer.run(),
        name="remnawave-stream-consumer",
    )
    logger.info(
        "remnawave_stream_consumer_started",
        consumer_name=consumer_name,
        group_name=settings.remnawave_stream_consumer_group,
    )


async def _stop_remnawave_stream_consumer(state: Any) -> None:
    from src.services.backend_api_client import BackendAPIClient
    from src.services.remnawave_streams import RemnawaveStreamConsumer

    consumer = getattr(state, "remnawave_stream_consumer", None)
    task = getattr(state, "remnawave_stream_consumer_task", None)
    if isinstance(consumer, RemnawaveStreamConsumer):
        consumer.stop()
    if isinstance(task, asyncio.Task):
        timeout = settings.remnawave_stream_block_ms / 1000 + 2
        try:
            await asyncio.wait_for(task, timeout=timeout)
        except TimeoutError:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    backend = getattr(state, "remnawave_stream_backend", None)
    redis_client = getattr(state, "remnawave_stream_redis", None)
    try:
        if isinstance(backend, BackendAPIClient):
            await backend.__aexit__(None, None, None)
    finally:
        if redis_client is not None and hasattr(redis_client, "aclose"):
            await redis_client.aclose()
    logger.info("remnawave_stream_consumer_stopped")


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
                release=settings.sentry_release or None,
                traces_sample_rate=1.0 if settings.environment == "development" else 0.1,
                profiles_sample_rate=1.0 if settings.environment == "development" else 0.1,
                send_default_pii=False,
                max_request_body_size="never",
                include_local_variables=False,
                before_send=before_send,  # type: ignore[arg-type]
            )
            logger.info(
                "sentry_initialized",
                environment=settings.environment,
                release=settings.sentry_release or None,
            )

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

            # Keep queue depth gauges fresh even when the scheduler is not running.
            from src.tasks.monitoring.queue_depth import queue_depth_metrics_loop

            state.queue_depth_metrics_task = asyncio.create_task(queue_depth_metrics_loop())

        # Info metrics are not supported by prometheus_client multiprocess mode.
        if os.getenv("PROMETHEUS_MULTIPROC_DIR"):
            logger.info("worker_info_metric_skipped_in_multiprocess_mode")
        else:
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

        if settings.remnawave_stream_consumer_enabled is True:
            await _start_remnawave_stream_consumer(state)

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

        queue_depth_task = getattr(state, "queue_depth_metrics_task", None)
        if isinstance(queue_depth_task, asyncio.Task):
            queue_depth_task.cancel()
            with suppress(asyncio.CancelledError):
                await queue_depth_task
            logger.info("queue_depth_metrics_loop_cancelled")

        if isinstance(getattr(state, "remnawave_stream_consumer_task", None), asyncio.Task):
            await _stop_remnawave_stream_consumer(state)

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
