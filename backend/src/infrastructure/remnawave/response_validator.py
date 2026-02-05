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
        except ValidationError as e:
            logger.error(
                "Remnawave response validation failed - potential upstream compromise",
                extra={
                    "endpoint": endpoint,
                    "errors": e.errors(),
                    "raw_data_keys": list(data.keys()) if isinstance(data, dict) else type(data).__name__,
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
                    "endpoint": endpoint,
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
            except ValidationError as e:
                logger.error(
                    "Remnawave response validation failed - potential upstream compromise",
                    extra={
                        "endpoint": endpoint,
                        "index": i,
                        "errors": e.errors(),
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


# Singleton instance
response_validator = RemnawaveResponseValidator()
