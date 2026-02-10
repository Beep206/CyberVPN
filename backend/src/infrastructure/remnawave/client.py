"""Remnawave API client with response validation (HIGH-4).

Security improvements:
- All responses are validated against expected schemas
- Unexpected fields are stripped from responses
- Validation failures are logged and raise 502 Bad Gateway
- Raw error messages from upstream are not exposed to clients
"""

import logging
from typing import Any, TypeVar

from httpx import AsyncClient
from pydantic import BaseModel

from src.config.settings import settings
from src.infrastructure.remnawave.response_validator import response_validator

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class RemnawaveClient:
    """HTTP client for Remnawave API with response validation."""

    def __init__(self) -> None:
        self._base_url = settings.remnawave_url.rstrip("/")
        self._token = settings.remnawave_token.get_secret_value()
        self._client: AsyncClient | None = None

    async def _get_client(self) -> AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = AsyncClient(
                base_url=self._base_url,
                headers={"Authorization": f"Bearer {self._token}"},
                timeout=30.0,
            )
        return self._client

    async def get(self, path: str, **kwargs: Any) -> dict[str, Any]:
        """GET request without validation (legacy - use get_validated instead)."""
        client = await self._get_client()
        response = await client.get(path, **kwargs)
        response.raise_for_status()
        return response.json()

    async def post(self, path: str, **kwargs: Any) -> dict[str, Any]:
        """POST request without validation (legacy - use post_validated instead)."""
        client = await self._get_client()
        response = await client.post(path, **kwargs)
        response.raise_for_status()
        return response.json()

    async def put(self, path: str, **kwargs: Any) -> dict[str, Any]:
        """PUT request without validation (legacy - use put_validated instead)."""
        client = await self._get_client()
        response = await client.put(path, **kwargs)
        response.raise_for_status()
        return response.json()

    async def delete(self, path: str, **kwargs: Any) -> dict[str, Any]:
        """DELETE request without validation (legacy - use delete_validated instead)."""
        client = await self._get_client()
        response = await client.delete(path, **kwargs)
        response.raise_for_status()
        return response.json()

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

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def health_check(self) -> bool:
        try:
            await self.get("/api/health")
            return True
        except Exception:
            return False


remnawave_client = RemnawaveClient()


async def get_remnawave_client() -> RemnawaveClient:
    return remnawave_client
