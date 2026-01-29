import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer

from src.config.settings import settings
from src.presentation.api.v1.router import api_router
from src.presentation.middleware.auth import AuthMiddleware
from src.presentation.middleware.logging import LoggingMiddleware
from src.presentation.middleware.rate_limit import RateLimitMiddleware

logger = logging.getLogger("cybervpn")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("CyberVPN Backend starting up...")
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
    {"name": "servers", "description": "VPN server management"},
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
    {"name": "websocket", "description": "Real-time WebSocket channels"},
]

app = FastAPI(
    title="CyberVPN Backend API",
    version="0.1.0",
    description="Backend API for CyberVPN admin dashboard",
    lifespan=lifespan,
    openapi_tags=tags_metadata,
    servers=[{"url": "/", "description": "Current server"}],
    swagger_ui_parameters={"persistAuthorization": True},
)

# Middleware (order matters - last added = first executed)
# Order: Logging (runs last) → Auth → Rate Limit → CORS (runs first)

# Add LoggingMiddleware first (runs last in chain)
app.add_middleware(LoggingMiddleware)

# Add AuthMiddleware second (runs third)
app.add_middleware(AuthMiddleware)

# Add RateLimitMiddleware third (runs second)
# Conditionally add based on settings
if settings.rate_limit_enabled:
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=settings.rate_limit_requests,
    )

# Add CORSMiddleware last (runs FIRST to handle preflight OPTIONS requests)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Request-ID"],
)

# Exception handlers
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

# Register validation error handler
app.add_exception_handler(RequestValidationError, validation_exception_handler)

# Register specific domain exception handlers (order matters - most specific first)
app.add_exception_handler(UserNotFoundError, user_not_found_handler)
app.add_exception_handler(ServerNotFoundError, server_not_found_handler)
app.add_exception_handler(PaymentNotFoundError, payment_not_found_handler)
app.add_exception_handler(InvalidCredentialsError, invalid_credentials_handler)
app.add_exception_handler(InvalidTokenError, invalid_token_handler)
app.add_exception_handler(InsufficientPermissionsError, insufficient_permissions_handler)
app.add_exception_handler(SubscriptionExpiredError, subscription_expired_handler)
app.add_exception_handler(TrafficLimitExceededError, traffic_limit_exceeded_handler)
app.add_exception_handler(UserAlreadyExistsError, user_already_exists_handler)
app.add_exception_handler(DuplicateUsernameError, duplicate_username_handler)
app.add_exception_handler(InvalidWebhookSignatureError, invalid_webhook_signature_handler)
app.add_exception_handler(DomainValidationError, domain_validation_error_handler)

# Register catch-all domain error handler
app.add_exception_handler(DomainError, domain_error_handler)

# Register unhandled exception handler (last resort)
app.add_exception_handler(Exception, unhandled_exception_handler)

# Routes
app.include_router(api_router)


@app.get("/health")
async def health_check() -> dict:
    return {"status": "ok", "service": "cybervpn-backend"}
