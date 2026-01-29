"""Global exception handlers for the FastAPI application."""

import logging
from typing import Union

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

logger = logging.getLogger("cybervpn.validation")


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
