"""Global exception handlers for the FastAPI application."""

import logging
from typing import Union

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
    ValidationError as DomainValidationError,
)

logger = logging.getLogger("cybervpn.exceptions")


async def validation_exception_handler(
    request: Request,
    exc: Union[RequestValidationError, ValidationError],
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

    logger.warning(
        "Validation failed for %s %s",
        request.method,
        request.url.path,
        extra={
            "path": request.url.path,
            "method": request.method,
            "errors": errors,
            "client_ip": request.client.host if request.client else None,
        },
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": errors},
    )


# Domain Exception Handlers


async def user_not_found_handler(request: Request, exc: UserNotFoundError) -> JSONResponse:
    """Handle UserNotFoundError - 404 with generic message (no identifier leak)."""
    logger.warning(
        "User not found",
        extra={
            "path": request.url.path,
            "method": request.method,
            "exception": str(exc),
            "details": exc.details,
            "client_ip": request.client.host if request.client else None,
        },
    )
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": "User not found"},
    )


async def server_not_found_handler(request: Request, exc: ServerNotFoundError) -> JSONResponse:
    """Handle ServerNotFoundError - 404 with generic message."""
    logger.warning(
        "Server not found",
        extra={
            "path": request.url.path,
            "method": request.method,
            "exception": str(exc),
            "details": exc.details,
            "client_ip": request.client.host if request.client else None,
        },
    )
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": "Server not found"},
    )


async def payment_not_found_handler(request: Request, exc: PaymentNotFoundError) -> JSONResponse:
    """Handle PaymentNotFoundError - 404 with generic message."""
    logger.warning(
        "Payment not found",
        extra={
            "path": request.url.path,
            "method": request.method,
            "exception": str(exc),
            "details": exc.details,
            "client_ip": request.client.host if request.client else None,
        },
    )
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": "Payment not found"},
    )


async def invalid_credentials_handler(request: Request, exc: InvalidCredentialsError) -> JSONResponse:
    """Handle InvalidCredentialsError - 401 with generic message (no username/email leak)."""
    logger.warning(
        "Invalid credentials",
        extra={
            "path": request.url.path,
            "method": request.method,
            "client_ip": request.client.host if request.client else None,
        },
    )
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": "Invalid credentials"},
    )


async def invalid_token_handler(request: Request, exc: InvalidTokenError) -> JSONResponse:
    """Handle InvalidTokenError - 401 with generic message (no token details leak)."""
    logger.warning(
        "Invalid or expired token",
        extra={
            "path": request.url.path,
            "method": request.method,
            "exception": str(exc),
            "details": exc.details,
            "client_ip": request.client.host if request.client else None,
        },
    )
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": "Invalid or expired token"},
    )


async def insufficient_permissions_handler(
    request: Request, exc: InsufficientPermissionsError
) -> JSONResponse:
    """Handle InsufficientPermissionsError - 403 with generic message (no role leak)."""
    logger.warning(
        "Insufficient permissions",
        extra={
            "path": request.url.path,
            "method": request.method,
            "exception": str(exc),
            "details": exc.details,
            "client_ip": request.client.host if request.client else None,
        },
    )
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={"detail": "Insufficient permissions"},
    )


async def subscription_expired_handler(
    request: Request, exc: SubscriptionExpiredError
) -> JSONResponse:
    """Handle SubscriptionExpiredError - 402 Payment Required."""
    logger.warning(
        "Subscription expired",
        extra={
            "path": request.url.path,
            "method": request.method,
            "exception": str(exc),
            "details": exc.details,
            "client_ip": request.client.host if request.client else None,
        },
    )
    return JSONResponse(
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
        content={"detail": "Subscription expired"},
    )


async def traffic_limit_exceeded_handler(
    request: Request, exc: TrafficLimitExceededError
) -> JSONResponse:
    """Handle TrafficLimitExceededError - 429 Too Many Requests."""
    logger.warning(
        "Traffic limit exceeded",
        extra={
            "path": request.url.path,
            "method": request.method,
            "exception": str(exc),
            "details": exc.details,
            "client_ip": request.client.host if request.client else None,
        },
    )
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": "Traffic limit exceeded"},
    )


async def user_already_exists_handler(request: Request, exc: UserAlreadyExistsError) -> JSONResponse:
    """Handle UserAlreadyExistsError - 409 Conflict."""
    logger.warning(
        "User already exists",
        extra={
            "path": request.url.path,
            "method": request.method,
            "exception": str(exc),
            "details": exc.details,
            "client_ip": request.client.host if request.client else None,
        },
    )
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": "User already exists"},
    )


async def duplicate_username_handler(request: Request, exc: DuplicateUsernameError) -> JSONResponse:
    """Handle DuplicateUsernameError - 409 Conflict."""
    logger.warning(
        "Username already exists",
        extra={
            "path": request.url.path,
            "method": request.method,
            "exception": str(exc),
            "details": exc.details,
            "client_ip": request.client.host if request.client else None,
        },
    )
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": "Username already exists"},
    )


async def invalid_webhook_signature_handler(
    request: Request, exc: InvalidWebhookSignatureError
) -> JSONResponse:
    """Handle InvalidWebhookSignatureError - 401 Unauthorized."""
    logger.warning(
        "Invalid webhook signature",
        extra={
            "path": request.url.path,
            "method": request.method,
            "client_ip": request.client.host if request.client else None,
        },
    )
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": "Invalid webhook signature"},
    )


async def domain_validation_error_handler(
    request: Request, exc: DomainValidationError
) -> JSONResponse:
    """Handle domain ValidationError - 400 Bad Request."""
    logger.warning(
        "Domain validation error",
        extra={
            "path": request.url.path,
            "method": request.method,
            "exception": str(exc),
            "details": exc.details,
            "client_ip": request.client.host if request.client else None,
        },
    )
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": exc.message},
    )


async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    """Handle generic DomainError - 400 Bad Request (catch-all for unhandled domain errors)."""
    logger.warning(
        "Domain error",
        extra={
            "path": request.url.path,
            "method": request.method,
            "exception": str(exc),
            "exception_type": type(exc).__name__,
            "details": exc.details,
            "client_ip": request.client.host if request.client else None,
        },
    )
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": exc.message},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unhandled exceptions - 500 Internal Server Error (no stack trace leak)."""
    logger.exception(
        "Unhandled exception",
        extra={
            "path": request.url.path,
            "method": request.method,
            "exception_type": type(exc).__name__,
            "client_ip": request.client.host if request.client else None,
        },
        exc_info=exc,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )
