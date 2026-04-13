"""Remnawave API client with response validation (HIGH-4).

Security improvements:
- All responses are validated against expected schemas
- Unexpected fields are stripped from responses
- Validation failures are logged and raise 502 Bad Gateway
- Raw error messages from upstream are not exposed to clients
"""

import asyncio
import logging
from typing import Any, TypeVar

from httpx import AsyncClient, HTTPStatusError, RequestError, Response
from pydantic import BaseModel

from src.config.settings import settings
from src.infrastructure.remnawave.response_validator import response_validator

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class RemnawaveClient:
    """HTTP client for Remnawave API with response validation."""

    def __init__(self) -> None:
        self._base_url = self._normalize_base_url(settings.remnawave_url)
        self._token = settings.remnawave_token.get_secret_value()
        self._retry_attempts = max(0, settings.remnawave_request_retries)
        self._retry_backoff_seconds = max(0.0, settings.remnawave_retry_backoff_seconds)
        self._client: AsyncClient | None = None

    @staticmethod
    def _normalize_base_url(base_url: str) -> str:
        normalized = base_url.rstrip("/")
        return normalized.removesuffix("/api")

    @staticmethod
    def _normalize_path(path: str) -> str:
        normalized = path if path.startswith("/") else f"/{path}"
        if normalized == "/api":
            return normalized
        if normalized.startswith("/api/"):
            return normalized
        return f"/api{normalized}"

    async def _get_client(self) -> AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = AsyncClient(
                base_url=self._base_url,
                headers={
                    "Authorization": f"Bearer {self._token}",
                    # Remnawave may reject internal service traffic without proxy headers.
                    "X-Forwarded-Proto": "https",
                    "X-Forwarded-For": "127.0.0.1",
                },
                timeout=30.0,
            )
        return self._client

    async def _request(self, method: str, path: str, **kwargs: Any) -> Response:
        client = await self._get_client()
        normalized_path = self._normalize_path(path)
        sender = getattr(client, method.lower())
        total_attempts = self._retry_attempts + 1

        for attempt in range(1, total_attempts + 1):
            try:
                response = await sender(normalized_path, **kwargs)
                response.raise_for_status()
                return response
            except HTTPStatusError as exc:
                status_code = exc.response.status_code
                if attempt < total_attempts and status_code >= 500:
                    logger.warning(
                        "Retrying Remnawave request after upstream error",
                        extra={
                            "method": method,
                            "path": normalized_path,
                            "attempt": attempt,
                            "retry_attempts": self._retry_attempts,
                            "status_code": status_code,
                        },
                    )
                    await asyncio.sleep(self._retry_backoff_seconds * attempt)
                    continue

                logger.warning(
                    "Remnawave request failed",
                    extra={
                        "method": method,
                        "path": normalized_path,
                        "status_code": status_code,
                    },
                )
                raise
            except RequestError as exc:
                if attempt < total_attempts:
                    logger.warning(
                        "Retrying Remnawave request after transport error",
                        extra={
                            "method": method,
                            "path": normalized_path,
                            "attempt": attempt,
                            "retry_attempts": self._retry_attempts,
                            "error_type": type(exc).__name__,
                        },
                    )
                    await asyncio.sleep(self._retry_backoff_seconds * attempt)
                    continue

                logger.warning(
                    "Remnawave transport request failed",
                    extra={
                        "method": method,
                        "path": normalized_path,
                        "error_type": type(exc).__name__,
                    },
                )
                raise

    async def get(self, path: str, **kwargs: Any) -> dict[str, Any]:
        """GET request without validation (legacy - use get_validated instead)."""
        response = await self._request("GET", path, **kwargs)
        return self._normalize_response(response.json())

    async def post(self, path: str, **kwargs: Any) -> dict[str, Any]:
        """POST request without validation (legacy - use post_validated instead)."""
        response = await self._request("POST", path, **kwargs)
        return self._normalize_response(response.json())

    async def put(self, path: str, **kwargs: Any) -> dict[str, Any]:
        """PUT request without validation (legacy - use put_validated instead)."""
        response = await self._request("PUT", path, **kwargs)
        return self._normalize_response(response.json())

    async def delete(self, path: str, **kwargs: Any) -> dict[str, Any]:
        """DELETE request without validation (legacy - use delete_validated instead)."""
        response = await self._request("DELETE", path, **kwargs)
        if response.status_code == 204 or not response.content.strip():
            return {}
        return self._normalize_response(response.json())

    async def patch(self, path: str, **kwargs: Any) -> dict[str, Any]:
        """PATCH request without validation (legacy - use patch_validated instead)."""
        response = await self._request("PATCH", path, **kwargs)
        return self._normalize_response(response.json())

    @staticmethod
    def _normalize_response(data: Any) -> Any:
        """Unwrap the common Remnawave ``response`` envelope."""
        if isinstance(data, dict) and "response" in data and len(data) == 1:
            return data["response"]
        return data

    # Validated methods - use these for security

    async def get_validated(
        self,
        path: str,
        schema: type[T],
        **kwargs: Any,
    ) -> T:
        """GET request with response validation.

        Args:
            path: API endpoint path
            schema: Pydantic schema to validate against
            **kwargs: Additional request kwargs

        Returns:
            Validated response object

        Raises:
            HTTPException: 502 on validation failure, others propagated
        """
        data = await self.get(path, **kwargs)
        return response_validator.validate_single(data, schema, f"GET {path}")

    async def get_list_validated(
        self,
        path: str,
        schema: type[T],
        **kwargs: Any,
    ) -> list[T]:
        """GET request expecting a list response with validation.

        Args:
            path: API endpoint path
            schema: Pydantic schema for list items
            **kwargs: Additional request kwargs

        Returns:
            List of validated response objects
        """
        data = await self.get(path, **kwargs)
        return response_validator.validate_list(data, schema, f"GET {path}")

    async def get_collection_validated(
        self,
        path: str,
        collection_key: str,
        schema: type[T],
        **kwargs: Any,
    ) -> list[T]:
        """GET request expecting a bare list or a keyed collection envelope."""
        data = await self.get(path, **kwargs)
        return response_validator.validate_collection(data, collection_key, schema, f"GET {path}")

    async def post_validated(
        self,
        path: str,
        schema: type[T],
        **kwargs: Any,
    ) -> T:
        """POST request with response validation.

        Args:
            path: API endpoint path
            schema: Pydantic schema to validate against
            **kwargs: Additional request kwargs

        Returns:
            Validated response object
        """
        data = await self.post(path, **kwargs)
        return response_validator.validate_single(data, schema, f"POST {path}")

    async def put_validated(
        self,
        path: str,
        schema: type[T],
        **kwargs: Any,
    ) -> T:
        """PUT request with response validation.

        Args:
            path: API endpoint path
            schema: Pydantic schema to validate against
            **kwargs: Additional request kwargs

        Returns:
            Validated response object
        """
        data = await self.put(path, **kwargs)
        return response_validator.validate_single(data, schema, f"PUT {path}")

    async def delete_validated(
        self,
        path: str,
        schema: type[T] | None = None,
        **kwargs: Any,
    ) -> T | None:
        """DELETE request with optional response validation.

        Args:
            path: API endpoint path
            schema: Optional Pydantic schema to validate against
            **kwargs: Additional request kwargs

        Returns:
            Validated response object or None
        """
        data = await self.delete(path, **kwargs)
        if schema is None:
            return None
        return response_validator.validate_single(data, schema, f"DELETE {path}")

    async def patch_validated(
        self,
        path: str,
        schema: type[T],
        **kwargs: Any,
    ) -> T:
        """PATCH request with response validation."""
        data = await self.patch(path, **kwargs)
        return response_validator.validate_single(data, schema, f"PATCH {path}")

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def health_check(self) -> bool:
        try:
            for path in ("/system/health", "/health"):
                try:
                    await self.get(path)
                    return True
                except Exception as path_error:
                    logger.debug("Remnawave health probe failed for %s: %s", path, path_error)
                    continue
            return False
        except Exception as e:
            _ = e  # Expected when Remnawave is unreachable
            return False


remnawave_client = RemnawaveClient()


async def get_remnawave_client() -> RemnawaveClient:
    return remnawave_client
