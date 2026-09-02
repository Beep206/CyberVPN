"""Remnawave response validation service (HIGH-4).

Validates all Remnawave API responses against expected schemas:
- Strips unexpected fields from responses
- Logs validation failures as potential upstream compromise indicators
- Raises appropriate errors on validation failure

This prevents malicious data injection from a compromised upstream service.
"""

import logging
from typing import Any, TypeVar

from fastapi import HTTPException, status
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

_SAFE_HTTP_METHODS = frozenset({"DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"})


def _safe_operation(endpoint: str) -> str:
    """Return only the developer-controlled HTTP verb, never an upstream path."""

    operation = endpoint.partition(" ")[0].upper()
    return operation if operation in _SAFE_HTTP_METHODS else "UNKNOWN"


def _safe_validation_summary(exc: ValidationError) -> tuple[int, list[str]]:
    """Reduce Pydantic failures to stable codes without raw input/context."""

    errors = exc.errors(include_url=False, include_context=False, include_input=False)
    return len(errors), sorted({str(error.get("type", "validation_error")) for error in errors})


class RemnawaveResponseValidator:
    """Validates Remnawave API responses against Pydantic schemas.

    Security properties:
    - Only expected fields pass through (strips unexpected)
    - Type coercion is strict
    - Validation failures are logged and raise 502
    """

    @staticmethod
    def validate_single(
        data: dict[str, Any],
        schema: type[T],
        endpoint: str,
    ) -> T:
        """Validate a single response object.

        Args:
            data: Raw response data from Remnawave
            schema: Pydantic schema to validate against
            endpoint: Endpoint name for logging

        Returns:
            Validated and stripped response object

        Raises:
            HTTPException: 502 Bad Gateway on validation failure
        """
        try:
            # Pydantic validation automatically strips unknown fields
            validated = schema.model_validate(data)
            return validated
        except ValidationError as exc:
            error_count, error_codes = _safe_validation_summary(exc)
            logger.error(
                "Remnawave response validation failed - potential upstream compromise",
                extra={
                    "operation": _safe_operation(endpoint),
                    "schema": schema.__name__,
                    "error_count": error_count,
                    "error_codes": error_codes,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Upstream service returned invalid response",
            ) from None

    @staticmethod
    def validate_list(
        data: list[dict[str, Any]],
        schema: type[T],
        endpoint: str,
    ) -> list[T]:
        """Validate a list of response objects.

        Args:
            data: List of raw response data from Remnawave
            schema: Pydantic schema to validate against
            endpoint: Endpoint name for logging

        Returns:
            List of validated and stripped response objects

        Raises:
            HTTPException: 502 Bad Gateway on validation failure
        """
        if not isinstance(data, list):
            logger.error(
                "Remnawave response validation failed - expected list",
                extra={
                    "operation": _safe_operation(endpoint),
                    "actual_type": type(data).__name__,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Upstream service returned invalid response format",
            )

        validated: list[T] = []
        for i, item in enumerate(data):
            try:
                validated.append(schema.model_validate(item))
            except ValidationError as exc:
                error_count, error_codes = _safe_validation_summary(exc)
                logger.error(
                    "Remnawave response validation failed - potential upstream compromise",
                    extra={
                        "operation": _safe_operation(endpoint),
                        "schema": schema.__name__,
                        "index": i,
                        "error_count": error_count,
                        "error_codes": error_codes,
                    },
                )
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Upstream service returned invalid response",
                ) from None

        return validated

    @staticmethod
    def validate_optional(
        data: dict[str, Any] | None,
        schema: type[T],
        endpoint: str,
    ) -> T | None:
        """Validate an optional response object.

        Args:
            data: Raw response data (or None) from Remnawave
            schema: Pydantic schema to validate against
            endpoint: Endpoint name for logging

        Returns:
            Validated response or None

        Raises:
            HTTPException: 502 Bad Gateway on validation failure
        """
        if data is None:
            return None
        return RemnawaveResponseValidator.validate_single(data, schema, endpoint)

    @staticmethod
    def validate_collection(
        data: Any,
        collection_key: str,
        schema: type[T],
        endpoint: str,
    ) -> list[T]:
        """Validate a collection that may be returned as a list or keyed envelope."""
        if isinstance(data, list):
            return RemnawaveResponseValidator.validate_list(data, schema, endpoint)

        if isinstance(data, dict):
            collection = data.get(collection_key)
            if collection is None and "response" in data:
                response = data["response"]
                collection = response.get(collection_key) if isinstance(response, dict) else response

            if isinstance(collection, list):
                return RemnawaveResponseValidator.validate_list(collection, schema, endpoint)

        logger.error(
            "Remnawave response validation failed - expected collection",
            extra={
                "operation": _safe_operation(endpoint),
                "actual_type": type(data).__name__,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Upstream service returned invalid response format",
        )


# Singleton instance
response_validator = RemnawaveResponseValidator()
