import logging
from contextlib import asynccontextmanager
from typing import Any, Callable, cast

from fastapi import Depends, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from starlette.types import ExceptionHandler

from src.presentation.dependencies.auth import get_current_active_user

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
    ValidationError as DomainValidationError,
)
from src.presentation.api.v1.router import api_router
from src.presentation.api.well_known.security_txt import router as security_txt_router
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
from src.infrastructure.payments.cryptobot.client import cryptobot_client
from src.version import __version__

logger = logging.getLogger("cybervpn")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("CyberVPN Backend starting up...")

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
    try:
        from src.infrastructure.remnawave.client import remnawave_client

        await remnawave_client.close()
    except Exception:
        pass

    try:
        await cryptobot_client.close()
    except Exception:
        pass

    try:
        from src.infrastructure.tasks.email_task_dispatcher import shutdown_email_dispatcher

        await shutdown_email_dispatcher()
    except Exception:
        pass

    try:
        from src.infrastructure.cache.redis_client import close_redis_pool

        await close_redis_pool()
    except Exception:
        pass

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


@app.get("/metrics")
async def metrics_endpoint():
    """Prometheus metrics endpoint.

    Exposes application metrics for Prometheus scraping.
    LOW-006: Includes websocket_auth_method_total for deprecation tracking.
    """
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
    from starlette.responses import Response

    # Import metrics modules to ensure they're registered
    from src.infrastructure.monitoring import metrics  # noqa: F401

    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
