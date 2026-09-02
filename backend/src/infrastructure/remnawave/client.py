"""Remnawave API client with response validation (HIGH-4).

Security improvements:
- All responses are validated against expected schemas
- Unexpected fields are stripped from responses
- Validation failures are logged and raise 502 Bad Gateway
- Raw error messages from upstream are not exposed to clients
"""

import asyncio
import logging
import re
from typing import Any, TypeVar

from httpx import AsyncClient, HTTPStatusError, Request, RequestError, Response
from pydantic import BaseModel

from src.config.settings import settings
from src.infrastructure.remnawave.contracts import RemnawaveCursorPage
from src.infrastructure.remnawave.response_validator import response_validator

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

_SAFE_ERROR_URL = "https://remnawave.invalid/"
_SAFE_CORRELATION_RE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


class RemnawaveHTTPStatusError(HTTPStatusError):
    """HTTP failure stripped of upstream body, URL, headers, and PII."""

    error_code = "remnawave_upstream_http_error"

    def __init__(self, *, status_code: int, correlation_id: str | None = None) -> None:
        self.correlation_id = correlation_id
        safe_request = Request("GET", _SAFE_ERROR_URL)
        safe_headers = {"x-correlation-id": correlation_id} if correlation_id else {}
        safe_response = Response(status_code, request=safe_request, headers=safe_headers)
        message = f"Remnawave request failed (code={self.error_code}, status={status_code}"
        if correlation_id:
            message += f", correlation={correlation_id}"
        super().__init__(f"{message})", request=safe_request, response=safe_response)


class RemnawaveTransportError(RequestError):
    """Transport failure without the original URL, headers, or provider text."""

    error_code = "remnawave_upstream_transport_error"

    def __init__(self) -> None:
        super().__init__(
            f"Remnawave request failed (code={self.error_code})",
            request=Request("GET", _SAFE_ERROR_URL),
        )


class RemnawaveProtocolError(RuntimeError):
    """Successful upstream response could not be decoded safely."""

    error_code = "remnawave_upstream_protocol_error"

    def __init__(self) -> None:
        super().__init__(f"Remnawave request failed (code={self.error_code})")


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
                trust_env=False,
            )
        return self._client

    async def _request(self, method: str, path: str, **kwargs: Any) -> Response:
        client = await self._get_client()
        normalized_path = self._normalize_path(path)
        sender = getattr(client, method.lower())
        # Remnawave 3.x uses 202/204 for many actions.  A lost mutation
        # response is ambiguous and repeating the request can create a second
        # user/action because the upstream API does not provide an idempotency
        # contract for these operations.  Only reads are retried here;
        # mutation callers must reconcile authoritative upstream state.
        retry_safe = method.upper() in {"GET", "HEAD", "OPTIONS"}
        total_attempts = (self._retry_attempts + 1) if retry_safe else 1
        terminal_error: RemnawaveHTTPStatusError | RemnawaveTransportError | None = None

        for attempt in range(1, total_attempts + 1):
            try:
                response = await sender(normalized_path, **kwargs)
                response.raise_for_status()
                return response
            except HTTPStatusError as exc:
                status_code = exc.response.status_code
                correlation_id = self._safe_correlation_id(exc.response)
                if retry_safe and attempt < total_attempts and status_code >= 500:
                    logger.warning(
                        "Retrying Remnawave request after upstream error",
                        extra={
                            "attempt": attempt,
                            "retry_attempts": self._retry_attempts,
                            "status_code": status_code,
                            "error_code": RemnawaveHTTPStatusError.error_code,
                            "correlation_id": correlation_id,
                        },
                    )
                    await asyncio.sleep(self._retry_backoff_seconds * attempt)
                    continue

                logger.warning(
                    "Remnawave request failed",
                    extra={
                        "status_code": status_code,
                        "error_code": RemnawaveHTTPStatusError.error_code,
                        "correlation_id": correlation_id,
                    },
                )
                terminal_error = RemnawaveHTTPStatusError(
                    status_code=status_code,
                    correlation_id=correlation_id,
                )
                break
            except RequestError:
                if retry_safe and attempt < total_attempts:
                    logger.warning(
                        "Retrying Remnawave request after transport error",
                        extra={
                            "attempt": attempt,
                            "retry_attempts": self._retry_attempts,
                            "error_code": RemnawaveTransportError.error_code,
                        },
                    )
                    await asyncio.sleep(self._retry_backoff_seconds * attempt)
                    continue

                logger.warning(
                    "Remnawave transport request failed",
                    extra={
                        "error_code": RemnawaveTransportError.error_code,
                    },
                )
                terminal_error = RemnawaveTransportError()
                break
        if terminal_error is not None:
            # Raise outside the provider exception handler so the original
            # response/request cannot survive in ``__context__``.
            raise terminal_error
        raise RuntimeError("Remnawave request retry loop exhausted unexpectedly")

    @staticmethod
    def _safe_correlation_id(response: Response) -> str | None:
        for header in ("x-correlation-id", "x-request-id"):
            value = response.headers.get(header, "").strip()
            if _SAFE_CORRELATION_RE.fullmatch(value):
                return value
        return None

    @staticmethod
    def _decode_json(response: Response) -> Any:
        decode_failed = False
        try:
            return response.json()
        except (TypeError, ValueError, UnicodeError):
            decode_failed = True
        if decode_failed:
            # Raised after leaving the decoder's exception handler so raw
            # response text is not retained as exception context.
            raise RemnawaveProtocolError()
        raise RemnawaveProtocolError()

    async def get(self, path: str, **kwargs: Any) -> dict[str, Any]:
        """GET request without validation (legacy - use get_validated instead)."""
        response = await self._request("GET", path, **kwargs)
        return self._normalize_response(self._decode_json(response))

    async def post(self, path: str, **kwargs: Any) -> dict[str, Any]:
        """POST request without validation (legacy - use post_validated instead)."""
        response = await self._request("POST", path, **kwargs)
        if response.status_code == 204 or not response.content.strip():
            return {}
        return self._normalize_response(self._decode_json(response))

    async def put(self, path: str, **kwargs: Any) -> dict[str, Any]:
        """PUT request without validation (legacy - use put_validated instead)."""
        response = await self._request("PUT", path, **kwargs)
        if response.status_code == 204 or not response.content.strip():
            return {}
        return self._normalize_response(self._decode_json(response))

    async def delete(self, path: str, **kwargs: Any) -> dict[str, Any]:
        """DELETE request without validation (legacy - use delete_validated instead)."""
        response = await self._request("DELETE", path, **kwargs)
        if response.status_code == 204 or not response.content.strip():
            return {}
        return self._normalize_response(self._decode_json(response))

    async def patch(self, path: str, **kwargs: Any) -> dict[str, Any]:
        """PATCH request without validation (legacy - use patch_validated instead)."""
        response = await self._request("PATCH", path, **kwargs)
        if response.status_code == 204 or not response.content.strip():
            return {}
        return self._normalize_response(self._decode_json(response))

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
            Validated response object, or None for an empty successful acknowledgement

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
        data: Any = await self.get(path, **kwargs)
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
    ) -> T | None:
        """POST request with response validation.

        Args:
            path: API endpoint path
            schema: Pydantic schema to validate against
            **kwargs: Additional request kwargs

        Returns:
            Validated response object, or None for an empty successful acknowledgement
        """
        return await self._mutation_validated("POST", path, schema, **kwargs)

    async def put_validated(
        self,
        path: str,
        schema: type[T],
        **kwargs: Any,
    ) -> T | None:
        """PUT request with response validation.

        Args:
            path: API endpoint path
            schema: Pydantic schema to validate against
            **kwargs: Additional request kwargs

        Returns:
            Validated response object
        """
        return await self._mutation_validated("PUT", path, schema, **kwargs)

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
        return await self._mutation_validated("DELETE", path, schema, **kwargs)

    async def patch_validated(
        self,
        path: str,
        schema: type[T],
        **kwargs: Any,
    ) -> T | None:
        """PATCH request with validation or ``None`` for an empty success."""
        return await self._mutation_validated("PATCH", path, schema, **kwargs)

    async def _mutation_validated(
        self,
        method: str,
        path: str,
        schema: type[T] | None,
        **kwargs: Any,
    ) -> T | None:
        """Validate a mutation response without inventing a body for empty success.

        Remnawave 3.x legitimately acknowledges mutations with an empty
        ``201``, ``202`` or ``204`` response.  Treating that acknowledgement as
        ``{}`` and validating it against a required response schema turns an
        already-applied upstream mutation into a local 502.  Callers receive
        ``None`` and must return an explicit accepted/no-content response or
        reconcile authoritative state; the mutation is never repeated here.
        """
        response = await self._request(method, path, **kwargs)
        if response.status_code == 204 or not response.content.strip():
            return None
        if schema is None:
            return None
        data = self._normalize_response(self._decode_json(response))
        return response_validator.validate_single(data, schema, f"{method} {path}")

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
                    logger.debug(
                        "Remnawave health probe failed",
                        extra={"probe": path, "error_type": type(path_error).__name__},
                    )
                    continue
            return False
        except Exception as e:
            _ = e  # Expected when Remnawave is unreachable
            return False

    async def get_all_users_cursor_page(
        self,
        *,
        cursor: str | None = None,
        limit: int = 1000,
    ) -> RemnawaveCursorPage:
        """Fetch a Remnawave users page using cursor pagination when available.

        Remnawave 3.x publishes ``GET /api/users/stream`` with ``size`` and a
        numeric cursor.  The 2.8 variants remain read-only fallbacks solely for
        pre-cutover reconciliation.
        """

        bounded_limit = max(1, min(int(limit), 1000))
        cursor_params: dict[str, Any] = {"size": bounded_limit}
        if cursor:
            cursor_params["cursor"] = cursor

        for path in ("/users/stream", "/users/all", "/users/cursor", "/users"):
            try:
                if path == "/users" and cursor:
                    continue
                params = cursor_params if path != "/users" else {"start": 0, "size": bounded_limit}
                data = await self.get(path, params=params)
                if isinstance(data, list):
                    return RemnawaveCursorPage(response=[item for item in data if isinstance(item, dict)])
                if isinstance(data, dict):
                    return response_validator.validate_single(data, RemnawaveCursorPage, f"GET {path}")
            except HTTPStatusError as exc:
                if exc.response.status_code in {400, 404, 405, 501}:
                    logger.info(
                        "Remnawave cursor users endpoint unavailable; trying fallback",
                        extra={"path": path, "status_code": exc.response.status_code},
                    )
                    continue
                raise

        legacy = await self.get("/users", params={"start": 0, "size": bounded_limit})
        if isinstance(legacy, list):
            return RemnawaveCursorPage(response=[item for item in legacy if isinstance(item, dict)])
        if isinstance(legacy, dict):
            return response_validator.validate_single(legacy, RemnawaveCursorPage, "GET /users")
        return RemnawaveCursorPage(response=[])


remnawave_client = RemnawaveClient()


async def get_remnawave_client() -> RemnawaveClient:
    return remnawave_client
