import logging
from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import Any, cast

import structlog
from fastapi import Depends, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from starlette.types import ExceptionHandler

from src.config.settings import settings
from src.domain.exceptions.domain_errors import (
    DomainError,
    DuplicateUsernameError,
    InsufficientPermissionsError,
    InvalidCredentialsError,
    InvalidTokenError,
    InvalidWebhookSignatureError,
    PaymentNotFoundError,
    ServerNotFoundError,
    SubscriptionExpiredError,
    TrafficLimitExceededError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from src.domain.exceptions.domain_errors import (
    ValidationError as DomainValidationError,
)
from src.infrastructure.payments.cryptobot.client import cryptobot_client
from src.presentation.api.v1.router import api_router
from src.presentation.api.well_known.security_txt import router as security_txt_router
from src.presentation.dependencies.auth import get_current_active_user
from src.presentation.exception_handlers import (
    domain_error_handler,
    domain_validation_error_handler,
    duplicate_username_handler,
    insufficient_permissions_handler,
    invalid_credentials_handler,
    invalid_token_handler,
    invalid_webhook_signature_handler,
    payment_not_found_handler,
    server_not_found_handler,
    subscription_expired_handler,
    traffic_limit_exceeded_handler,
    unhandled_exception_handler,
    user_already_exists_handler,
    user_not_found_handler,
    validation_exception_handler,
)
from src.presentation.middleware.logging import LoggingMiddleware
from src.presentation.middleware.rate_limit import RateLimitMiddleware
from src.presentation.middleware.request_id import RequestIDMiddleware
from src.presentation.middleware.security_headers import SecurityHeadersMiddleware
from src.version import __version__

logger = structlog.get_logger("cybervpn")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    # Configure structured JSON logging before any logging occurs
    from src.shared.logging.config import configure_logging

    configure_logging(json_logs=settings.json_logs, log_level=settings.log_level)

    logger.info("CyberVPN Backend starting up...")

    # Initialize Sentry SDK if DSN is configured
    if settings.sentry_dsn:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.environment,
            traces_sample_rate=1.0 if settings.environment == "development" else 0.1,
            profiles_sample_rate=1.0 if settings.environment == "development" else 0.1,
            integrations=[FastApiIntegration()],
        )
        logger.info("Sentry SDK initialized", environment=settings.environment)

    # Initialize OpenTelemetry tracing if enabled
    if settings.otel_enabled:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        from opentelemetry.instrumentation.redis import RedisInstrumentor
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        # Create resource with service name
        resource = Resource.create({"service.name": settings.otel_service_name})

        # Configure tracer provider
        tracer_provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(tracer_provider)

        # Configure OTLP exporter
        otlp_exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_endpoint, insecure=True)

        # Add batch span processor
        tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

        # Store instrumentors for cleanup
        app.state.otel_instrumentors = []

        logger.info(
            "OpenTelemetry initialized",
            service_name=settings.otel_service_name,
            exporter_endpoint=settings.otel_exporter_endpoint,
        )

    # HIGH-001: Enforce TOTP encryption key in production
    if settings.environment == "production":
        totp_key = settings.totp_encryption_key.get_secret_value()
        if not totp_key:
            raise RuntimeError(
                "TOTP_ENCRYPTION_KEY is required in production. "
                'Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"'
            )
        logger.info("TOTP encryption key: configured")

    try:
        from src.infrastructure.database.session import check_db_connection

        db_ok = await check_db_connection()
        logger.info(f"Database connection: {'OK' if db_ok else 'FAILED'}")
    except Exception as e:
        logger.warning(f"Database check skipped: {e}")

    try:
        from src.infrastructure.cache.redis_client import check_redis_connection

        redis_ok, _ = await check_redis_connection()
        logger.info(f"Redis connection: {'OK' if redis_ok else 'FAILED'}")
    except Exception as e:
        logger.warning(f"Redis check skipped: {e}")

    yield

    # Shutdown
    logger.info("CyberVPN Backend shutting down...")

    # Shutdown OpenTelemetry tracer provider if enabled
    if settings.otel_enabled:
        try:
            from opentelemetry import trace

            tracer_provider = trace.get_tracer_provider()
            if hasattr(tracer_provider, "shutdown"):
                tracer_provider.shutdown()
                logger.info("OpenTelemetry tracer provider shut down")
        except Exception as e:
            logger.warning("Shutdown error in OpenTelemetry: %s", e, exc_info=True)

    try:
        from src.infrastructure.remnawave.client import remnawave_client

        await remnawave_client.close()
    except Exception as e:
        logger.warning("Shutdown error in remnawave_client: %s", e, exc_info=True)

    try:
        await cryptobot_client.close()
    except Exception as e:
        logger.warning("Shutdown error in cryptobot_client: %s", e, exc_info=True)

    try:
        from src.infrastructure.tasks.email_task_dispatcher import shutdown_email_dispatcher

        await shutdown_email_dispatcher()
    except Exception as e:
        logger.warning("Shutdown error in email_dispatcher: %s", e, exc_info=True)

    try:
        from src.infrastructure.cache.redis_client import close_redis_pool

        await close_redis_pool()
    except Exception as e:
        logger.warning("Shutdown error in redis_pool: %s", e, exc_info=True)

    from src.infrastructure.messaging.websocket_manager import ws_manager

    logger.info(f"Closed {ws_manager.active_connections} WebSocket connections")


bearer_scheme = HTTPBearer(
    scheme_name="BearerAuth",
    description="JWT Bearer token authentication",
    bearerFormat="JWT",
)

tags_metadata = [
    {"name": "auth", "description": "Authentication (login, register, refresh, logout)"},
    {"name": "two-factor", "description": "Two-factor authentication management"},
    {"name": "oauth", "description": "OAuth social account linking"},
    {"name": "users", "description": "User CRUD operations"},
    {"name": "profile", "description": "Authenticated user profile management"},
    {"name": "servers", "description": "VPN server management"},
    {"name": "status", "description": "Public API status (unauthenticated)"},
    {"name": "monitoring", "description": "System health, stats, bandwidth"},
    {"name": "payments", "description": "Crypto payments and invoices"},
    {"name": "billing", "description": "Billing proxy (Remnawave)"},
    {"name": "plans", "description": "Subscription plans (Remnawave proxy)"},
    {"name": "subscriptions", "description": "Subscription templates (Remnawave proxy)"},
    {"name": "hosts", "description": "VPN host management (Remnawave proxy)"},
    {"name": "config-profiles", "description": "Config profiles (Remnawave proxy)"},
    {"name": "inbounds", "description": "Inbound configurations (Remnawave proxy)"},
    {"name": "squads", "description": "Squad management (Remnawave proxy)"},
    {"name": "snippets", "description": "Snippet management (Remnawave proxy)"},
    {"name": "keygen", "description": "Key generation and signing (Remnawave proxy)"},
    {"name": "xray", "description": "Xray VPN config (Remnawave proxy)"},
    {"name": "settings", "description": "System settings (Remnawave proxy)"},
    {"name": "admin", "description": "Audit logs, webhook logs"},
    {"name": "webhooks", "description": "External webhook receivers"},
    {"name": "telegram", "description": "Telegram bot integration"},
    {"name": "fcm", "description": "FCM push-notification token management"},
    {"name": "websocket", "description": "Real-time WebSocket channels"},
]

# MED-7: Conditionally disable Swagger UI in production
openapi_url = "/openapi.json" if settings.swagger_enabled else None
docs_url = "/docs" if settings.swagger_enabled else None
redoc_url = "/redoc" if settings.swagger_enabled else None

if not settings.swagger_enabled:
    logger.info("Swagger UI disabled (SWAGGER_ENABLED=false)")

app = FastAPI(
    title="CyberVPN Backend API",
    version=__version__,
    description="Backend API for CyberVPN admin dashboard",
    lifespan=lifespan,
    openapi_tags=tags_metadata,
    servers=[{"url": "/", "description": "Current server"}],
    swagger_ui_parameters={"persistAuthorization": True},
    openapi_url=openapi_url,
    docs_url=docs_url,
    redoc_url=redoc_url,
)

# Auto-instrument with OpenTelemetry if enabled (must be done after app creation)
if settings.otel_enabled:
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.instrumentation.redis import RedisInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

    # Instrument FastAPI app
    FastAPIInstrumentor.instrument_app(app)
    logger.info("OpenTelemetry FastAPI instrumentation applied")

    # Instrument httpx (for Remnawave, Cryptobot clients)
    HTTPXClientInstrumentor().instrument()
    logger.info("OpenTelemetry httpx instrumentation applied")

    # Instrument SQLAlchemy
    from src.infrastructure.database.session import engine

    SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)
    logger.info("OpenTelemetry SQLAlchemy instrumentation applied")

    # Instrument Redis
    RedisInstrumentor().instrument()
    logger.info("OpenTelemetry Redis instrumentation applied")

# Initialize Prometheus FastAPI instrumentator
# Expose metrics on separate metrics_app (port 9091), not main app
from prometheus_fastapi_instrumentator import Instrumentator

instrumentator = Instrumentator(
    should_group_status_codes=True,
    should_ignore_untemplated=False,
    should_respect_env_var=True,
    should_instrument_requests_inprogress=True,
    excluded_handlers=["/health", "/metrics", "/docs", "/openapi.json", "/redoc"],
    env_var_name="ENABLE_METRICS",
    inprogress_name="http_requests_in_progress",
    inprogress_labels=True,
)

# Instrument the main app but expose metrics on metrics_app
instrumentator.instrument(app)

# Middleware (order matters - last added = first executed)
# Order: Logging (runs last) → RequestID → SecurityHeaders → Rate Limit → CORS (runs first)

# Add LoggingMiddleware first (runs last in chain)
app.add_middleware(LoggingMiddleware)

# Add RequestIDMiddleware (LOW-005: adds X-Request-ID for tracing)
app.add_middleware(RequestIDMiddleware)

# Add SecurityHeadersMiddleware (runs after logging, adds OWASP security headers)
app.add_middleware(SecurityHeadersMiddleware)

# Add RateLimitMiddleware third (runs second)
# Conditionally add based on settings
if settings.rate_limit_enabled:
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=settings.rate_limit_requests,
    )

# Add CORSMiddleware last (runs FIRST to handle preflight OPTIONS requests)
allow_credentials = True
if "*" in settings.cors_origins:
    logger.warning("CORS '*' origin with credentials is unsafe; disabling credentials.")
    allow_credentials = False

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=allow_credentials,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Request-ID"],
)


def register_exception_handler(exc: type[Exception], handler: Callable[..., Any]) -> None:
    app.add_exception_handler(exc, cast(ExceptionHandler, handler))


# Register validation error handler
register_exception_handler(RequestValidationError, validation_exception_handler)

# Register specific domain exception handlers (order matters - most specific first)
register_exception_handler(UserNotFoundError, user_not_found_handler)
register_exception_handler(ServerNotFoundError, server_not_found_handler)
register_exception_handler(PaymentNotFoundError, payment_not_found_handler)
register_exception_handler(InvalidCredentialsError, invalid_credentials_handler)
register_exception_handler(InvalidTokenError, invalid_token_handler)
register_exception_handler(InsufficientPermissionsError, insufficient_permissions_handler)
register_exception_handler(SubscriptionExpiredError, subscription_expired_handler)
register_exception_handler(TrafficLimitExceededError, traffic_limit_exceeded_handler)
register_exception_handler(UserAlreadyExistsError, user_already_exists_handler)
register_exception_handler(DuplicateUsernameError, duplicate_username_handler)
register_exception_handler(InvalidWebhookSignatureError, invalid_webhook_signature_handler)
register_exception_handler(DomainValidationError, domain_validation_error_handler)

# Register catch-all domain error handler
register_exception_handler(DomainError, domain_error_handler)

# Register unhandled exception handler (last resort)
register_exception_handler(Exception, unhandled_exception_handler)

# Routes
app.include_router(api_router)
app.include_router(security_txt_router)  # SEC-017: /.well-known/security.txt


@app.get("/health")
async def health_check() -> dict:
    """Minimal health check for load balancers and orchestrators.

    LOW-008: Returns only status to prevent service identification attacks.
    For detailed health information, use the authenticated /health/detailed endpoint.
    """
    return {"status": "ok"}


@app.get("/readiness")
async def readiness_check() -> dict:
    """Readiness check for Kubernetes and orchestrators (unauthenticated).

    Checks if the service is ready to accept traffic by verifying:
    - Database connection is healthy
    - Redis connection is healthy
    - Task queue depth is below threshold (< 1000)

    Returns:
        200 OK if all checks pass
        503 Service Unavailable if any check fails
    """
    from fastapi import status as http_status
    from fastapi.responses import JSONResponse

    from src.infrastructure.cache.redis_client import check_redis_connection
    from src.infrastructure.database.session import check_db_connection

    checks = {
        "database": False,
        "redis": False,
        "queue": False,
    }
    all_healthy = True

    # Check database connection
    try:
        checks["database"] = await check_db_connection()
        if not checks["database"]:
            all_healthy = False
    except Exception:
        checks["database"] = False
        all_healthy = False

    # Check Redis connection
    try:
        redis_ok, _ = await check_redis_connection()
        checks["redis"] = redis_ok
        if not redis_ok:
            all_healthy = False
    except Exception:
        checks["redis"] = False
        all_healthy = False

    # Check task queue depth (optional - requires Redis)
    try:
        if checks["redis"]:
            from src.infrastructure.cache.redis_client import get_redis_client

            redis = await get_redis_client()
            # Check pending tasks in TaskIQ queue (stream length)
            queue_depth = await redis.xlen("taskiq:stream")
            checks["queue"] = queue_depth < 1000
            checks["queue_depth"] = queue_depth
            if not checks["queue"]:
                all_healthy = False
        else:
            checks["queue"] = False
            all_healthy = False
    except Exception:
        checks["queue"] = False
        all_healthy = False

    # Return appropriate status code
    if all_healthy:
        return JSONResponse(
            status_code=http_status.HTTP_200_OK,
            content={"status": "ready", "checks": checks},
        )
    else:
        return JSONResponse(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not_ready", "checks": checks},
        )


@app.get("/health/detailed")
async def health_check_detailed(
    _user=Depends(get_current_active_user),
) -> dict:
    """Detailed health check with dependency status (authenticated).

    LOW-008: Service identification info only available to authenticated users.
    Returns service name, version, environment, and dependency health.
    """
    from src.infrastructure.cache.redis_client import check_redis_connection
    from src.infrastructure.database.session import check_db_connection

    # Check dependencies
    db_ok = False
    redis_ok = False

    try:
        db_ok = await check_db_connection()
    except Exception:
        pass

    try:
        redis_ok, _ = await check_redis_connection()
    except Exception:
        pass

    return {
        "status": "ok" if (db_ok and redis_ok) else "degraded",
        "service": "cybervpn-backend",
        "version": __version__,
        "environment": settings.environment,
        "dependencies": {
            "database": "ok" if db_ok else "error",
            "redis": "ok" if redis_ok else "error",
        },
    }


def create_metrics_app() -> FastAPI:
    """SEC-02: Separate ASGI app for /metrics on internal-only port."""
    metrics_app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    # Expose Prometheus metrics from instrumentator on metrics_app
    instrumentator.expose(metrics_app, endpoint="/metrics", include_in_schema=False)

    @metrics_app.get("/health")
    async def metrics_health():
        return {"status": "ok"}

    return metrics_app


metrics_app = create_metrics_app()
