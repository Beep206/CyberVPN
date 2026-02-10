"""Global exception handlers for the FastAPI application.

LOW-005: All handlers include request_id for tracing and return it in responses.
"""

import logging

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

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
from src.presentation.middleware.request_id import get_request_id

logger = logging.getLogger("cybervpn.exceptions")


def _get_request_id_header() -> dict[str, str]:
    """Get X-Request-ID header for response (LOW-005)."""
    request_id = get_request_id()
    return {"X-Request-ID": request_id} if request_id else {}


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError | ValidationError,
) -> JSONResponse:
    """Transform Pydantic validation errors into a standardized JSON response."""
    errors = []
    for error in exc.errors():
        errors.append(
            {
                "loc": list(error["loc"]),
                "msg": error["msg"],
                "type": error["type"],
            }
        )

    request_id = get_request_id()
    logger.warning(
        "Validation failed for %s %s",
        request.method,
        request.url.path,
        extra={
            "path": request.url.path,
            "method": request.method,
            "errors": errors,
            "client_ip": request.client.host if request.client else None,
            "request_id": request_id,
        },
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": errors},
        headers=_get_request_id_header(),
    )


# Domain Exception Handlers


async def user_not_found_handler(request: Request, exc: UserNotFoundError) -> JSONResponse:
    """Handle UserNotFoundError - 404 with generic message (no identifier leak)."""
    request_id = get_request_id()
    logger.warning(
        "User not found",
        extra={
            "path": request.url.path,
            "method": request.method,
            "exception": str(exc),
            "details": exc.details,
            "client_ip": request.client.host if request.client else None,
            "request_id": request_id,
        },
    )
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": "User not found"},
        headers=_get_request_id_header(),
    )


async def server_not_found_handler(request: Request, exc: ServerNotFoundError) -> JSONResponse:
    """Handle ServerNotFoundError - 404 with generic message."""
    request_id = get_request_id()
    logger.warning(
        "Server not found",
        extra={
            "path": request.url.path,
            "method": request.method,
            "exception": str(exc),
            "details": exc.details,
            "client_ip": request.client.host if request.client else None,
            "request_id": request_id,
        },
    )
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": "Server not found"},
        headers=_get_request_id_header(),
    )


async def payment_not_found_handler(request: Request, exc: PaymentNotFoundError) -> JSONResponse:
    """Handle PaymentNotFoundError - 404 with generic message."""
    request_id = get_request_id()
    logger.warning(
        "Payment not found",
        extra={
            "path": request.url.path,
            "method": request.method,
            "exception": str(exc),
            "details": exc.details,
            "client_ip": request.client.host if request.client else None,
            "request_id": request_id,
        },
    )
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": "Payment not found"},
        headers=_get_request_id_header(),
    )


async def invalid_credentials_handler(request: Request, exc: InvalidCredentialsError) -> JSONResponse:
    """Handle InvalidCredentialsError - 401 with generic message (no username/email leak)."""
    _ = exc  # exc not used but required by signature
    request_id = get_request_id()
    logger.warning(
        "Invalid credentials",
        extra={
            "path": request.url.path,
            "method": request.method,
            "client_ip": request.client.host if request.client else None,
            "request_id": request_id,
        },
    )
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": "Invalid credentials"},
        headers=_get_request_id_header(),
    )


async def invalid_token_handler(request: Request, exc: InvalidTokenError) -> JSONResponse:
    """Handle InvalidTokenError - 401 with generic message (no token details leak)."""
    request_id = get_request_id()
    logger.warning(
        "Invalid or expired token",
        extra={
            "path": request.url.path,
            "method": request.method,
            "exception": str(exc),
            "details": exc.details,
            "client_ip": request.client.host if request.client else None,
            "request_id": request_id,
        },
    )
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": "Invalid or expired token"},
        headers=_get_request_id_header(),
    )


async def insufficient_permissions_handler(request: Request, exc: InsufficientPermissionsError) -> JSONResponse:
    """Handle InsufficientPermissionsError - 403 with generic message (no role leak)."""
    request_id = get_request_id()
    logger.warning(
        "Insufficient permissions",
        extra={
            "path": request.url.path,
            "method": request.method,
            "exception": str(exc),
            "details": exc.details,
            "client_ip": request.client.host if request.client else None,
            "request_id": request_id,
        },
    )
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={"detail": "Insufficient permissions"},
        headers=_get_request_id_header(),
    )


async def subscription_expired_handler(request: Request, exc: SubscriptionExpiredError) -> JSONResponse:
    """Handle SubscriptionExpiredError - 402 Payment Required."""
    request_id = get_request_id()
    logger.warning(
        "Subscription expired",
        extra={
            "path": request.url.path,
            "method": request.method,
            "exception": str(exc),
            "details": exc.details,
            "client_ip": request.client.host if request.client else None,
            "request_id": request_id,
        },
    )
    return JSONResponse(
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
        content={"detail": "Subscription expired"},
        headers=_get_request_id_header(),
    )


async def traffic_limit_exceeded_handler(request: Request, exc: TrafficLimitExceededError) -> JSONResponse:
    """Handle TrafficLimitExceededError - 429 Too Many Requests."""
    request_id = get_request_id()
    logger.warning(
        "Traffic limit exceeded",
        extra={
            "path": request.url.path,
            "method": request.method,
            "exception": str(exc),
            "details": exc.details,
            "client_ip": request.client.host if request.client else None,
            "request_id": request_id,
        },
    )
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": "Traffic limit exceeded"},
        headers=_get_request_id_header(),
    )


async def user_already_exists_handler(request: Request, exc: UserAlreadyExistsError) -> JSONResponse:
    """Handle UserAlreadyExistsError - 409 Conflict."""
    request_id = get_request_id()
    logger.warning(
        "User already exists",
        extra={
            "path": request.url.path,
            "method": request.method,
            "exception": str(exc),
            "details": exc.details,
            "client_ip": request.client.host if request.client else None,
            "request_id": request_id,
        },
    )
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": "User already exists"},
        headers=_get_request_id_header(),
    )


async def duplicate_username_handler(request: Request, exc: DuplicateUsernameError) -> JSONResponse:
    """Handle DuplicateUsernameError - 409 Conflict."""
    request_id = get_request_id()
    logger.warning(
        "Username already exists",
        extra={
            "path": request.url.path,
            "method": request.method,
            "exception": str(exc),
            "details": exc.details,
            "client_ip": request.client.host if request.client else None,
            "request_id": request_id,
        },
    )
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": "Username already exists"},
        headers=_get_request_id_header(),
    )


async def invalid_webhook_signature_handler(request: Request, exc: InvalidWebhookSignatureError) -> JSONResponse:
    """Handle InvalidWebhookSignatureError - 401 Unauthorized."""
    _ = exc  # exc not used but required by signature
    request_id = get_request_id()
    logger.warning(
        "Invalid webhook signature",
        extra={
            "path": request.url.path,
            "method": request.method,
            "client_ip": request.client.host if request.client else None,
            "request_id": request_id,
        },
    )
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": "Invalid webhook signature"},
        headers=_get_request_id_header(),
    )


async def domain_validation_error_handler(request: Request, exc: DomainValidationError) -> JSONResponse:
    """Handle domain ValidationError - 400 Bad Request."""
    request_id = get_request_id()
    logger.warning(
        "Domain validation error",
        extra={
            "path": request.url.path,
            "method": request.method,
            "exception": str(exc),
            "details": exc.details,
            "client_ip": request.client.host if request.client else None,
            "request_id": request_id,
        },
    )
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": exc.message},
        headers=_get_request_id_header(),
    )


async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    """Handle generic DomainError - 400 Bad Request (catch-all for unhandled domain errors)."""
    request_id = get_request_id()
    logger.warning(
        "Domain error",
        extra={
            "path": request.url.path,
            "method": request.method,
            "exception": str(exc),
            "exception_type": type(exc).__name__,
            "details": exc.details,
            "client_ip": request.client.host if request.client else None,
            "request_id": request_id,
        },
    )
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": exc.message},
        headers=_get_request_id_header(),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unhandled exceptions - 500 Internal Server Error (no stack trace leak)."""
    request_id = get_request_id()
    logger.exception(
        "Unhandled exception",
        extra={
            "path": request.url.path,
            "method": request.method,
            "exception_type": type(exc).__name__,
            "client_ip": request.client.host if request.client else None,
            "request_id": request_id,
        },
        exc_info=exc,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
        headers=_get_request_id_header(),
    )
