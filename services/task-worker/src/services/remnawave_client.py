"""Remnawave VPN backend API client.

Wraps httpx.AsyncClient for making authenticated requests to the Remnawave VPN backend.
Includes rate limiting, connection pooling, timeouts, retries, and structured logging.
"""

import asyncio
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import httpx
import structlog

from src.config import get_settings
from src.services.remnawave_normalizers import normalize_nodes, normalize_user, normalize_users
from src.utils.rate_limiter import AsyncTokenBucket

logger = structlog.get_logger(__name__)
_USER_STREAM_PAGE_SIZE = 1000
_USER_STREAM_MAX_PAGES = 100


@asynccontextmanager
async def _dummy_context() -> AsyncIterator[None]:
    """Dummy async context manager for cases where rate limiting is handled externally."""
    yield


class RemnawaveAPIError(Exception):
    """Exception raised when Remnawave API returns an error response."""

    def __init__(self, status_code: int, message: str, response_body: dict | None = None) -> None:
        """Initialize API error with status code and message.

        Args:
            status_code: HTTP status code from the failed request
            message: Error message describing the failure
            response_body: Optional response body from the API
        """
        self.status_code = status_code
        self.message = message
        self.response_body = response_body
        super().__init__(f"Remnawave API error [{status_code}]: {message}")


class RemnawaveClient:
    """Async HTTP client for Remnawave VPN backend API.

    Provides methods for interacting with the Remnawave API including user management,
    node operations, and system statistics. Includes built-in rate limiting, connection
    pooling, retries, and comprehensive error handling.

    Example:
        async with RemnawaveClient() as client:
            users = await client.get_users()
            await client.disable_user(user_id)
    """

    def __init__(self, rate_limiter: AsyncTokenBucket | None = None) -> None:
        """Initialize Remnawave client with settings from environment.

        Configures httpx.AsyncClient with:
        - Bearer token authentication
        - Connection pooling (50 max connections, 10 keepalive)
        - Timeouts (5s connect, 30s read, 10s write, 5s pool)
        - Retry transport (2 connection-level retries)
        - Rate limiting (token bucket or semaphore fallback)

        Args:
            rate_limiter: Optional AsyncTokenBucket for rate limiting.
                         If None, uses semaphore with 10 concurrent requests.
        """
        settings = get_settings()

        self._base_url = self._normalize_base_url(settings.remnawave_url)
        self._api_token = settings.remnawave_api_token.get_secret_value()
        self._token_bucket: AsyncTokenBucket | None = rate_limiter
        self._semaphore: asyncio.Semaphore | None = None

        # Rate limiting: Use token bucket if provided, otherwise fallback to semaphore
        if rate_limiter:
            logger.info("remnawave_client_using_token_bucket", rate=rate_limiter.rate, capacity=rate_limiter.capacity)
        else:
            self._semaphore = asyncio.Semaphore(10)
            logger.info("remnawave_client_using_semaphore", max_concurrent=10)

        # Configure timeouts: connect, read, write, pool
        timeout_config = httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=5.0)

        # Configure connection limits
        limits_config = httpx.Limits(max_connections=50, max_keepalive_connections=10, keepalive_expiry=30.0)

        # A transport-level retry cannot distinguish reads from mutations and
        # can therefore duplicate an accepted user action. Keep the transport
        # fail-once; higher layers may reconcile mutations, while any future
        # automatic retry must be implemented explicitly for safe reads only.
        transport = httpx.AsyncHTTPTransport(retries=0)

        # Initialize httpx client with Bearer token auth
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={
                "Authorization": f"Bearer {self._api_token}",
                "X-Forwarded-Proto": "https",
                "X-Forwarded-For": "127.0.0.1",
            },
            timeout=timeout_config,
            limits=limits_config,
            transport=transport,
            trust_env=False,
        )

        logger.info("remnawave_client_initialized", base_url=self._base_url)

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

    async def __aenter__(self) -> "RemnawaveClient":
        """Context manager entry - returns self for async with usage."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit - ensures client cleanup."""
        await self._client.aclose()
        logger.info("remnawave_client_closed")

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any | None:
        """Make an HTTP request with rate limiting, logging, and error handling.

        Args:
            method: HTTP method (GET, POST, PATCH, DELETE)
            path: API endpoint path (e.g., "/api/users")
            **kwargs: Additional arguments passed to httpx request (params, json, etc.)

        Returns:
            Response body parsed as JSON dictionary

        Raises:
            RemnawaveAPIError: If API returns non-2xx status code
        """
        start_time = time.perf_counter()

        # Apply rate limiting based on limiter type
        if self._token_bucket is not None:
            await self._token_bucket.acquire()

        # Use context manager for semaphore-based rate limiting
        rate_limit_ctx = self._semaphore

        async with rate_limit_ctx if rate_limit_ctx else _dummy_context():
            try:
                response = await self._client.request(method, self._normalize_path(path), **kwargs)
                duration = time.perf_counter() - start_time

                logger.info(
                    "remnawave_api_request",
                    method=method,
                    path=path,
                    status_code=response.status_code,
                    duration_ms=round(duration * 1000, 2),
                )

                # Check for error status codes
                if not response.is_success:
                    try:
                        raw_error_body = response.json()
                    except ValueError:
                        raw_error_body = None

                    error_body = raw_error_body if isinstance(raw_error_body, dict) else None
                    error_message = (
                        str(error_body.get("message"))
                        if error_body and error_body.get("message") is not None
                        else response.text or response.reason_phrase
                    )

                    logger.error(
                        "remnawave_api_error",
                        method=method,
                        path=path,
                        status_code=response.status_code,
                        error=error_message,
                    )

                    raise RemnawaveAPIError(
                        status_code=response.status_code, message=error_message, response_body=error_body
                    )

                # Remnawave 3.x uses successful no-body responses for a number
                # of asynchronous/bulk mutations. Do not turn a valid 202/204
                # into a JSON decoding failure.
                if response.status_code == httpx.codes.NO_CONTENT or not response.content:
                    return None

                try:
                    payload = response.json()
                except ValueError as exc:
                    raise RemnawaveAPIError(
                        status_code=response.status_code,
                        message="invalid_json_response",
                    ) from exc

                return self._normalize_response(payload)

            except httpx.HTTPError as e:
                duration = time.perf_counter() - start_time
                logger.error(
                    "remnawave_api_exception",
                    method=method,
                    path=path,
                    error=str(e),
                    duration_ms=round(duration * 1000, 2),
                )
                raise RemnawaveAPIError(status_code=0, message=f"HTTP error: {e}") from e

    @staticmethod
    def _normalize_response(data: Any) -> Any:
        """Unwrap the common Remnawave ``response`` envelope."""
        if isinstance(data, dict) and "response" in data and len(data) == 1:
            return data["response"]
        return data

    @staticmethod
    def _require_collection(response: Any, key: str) -> list[dict]:
        collection = (
            response if isinstance(response, list) else response.get(key) if isinstance(response, dict) else None
        )
        if not isinstance(collection, list) or any(not isinstance(item, dict) for item in collection):
            raise RemnawaveAPIError(status_code=200, message=f"invalid_{key}_response")
        return collection

    @classmethod
    def _require_bound_user_response(cls, response: Any, expected_user_id: int) -> dict:
        if not isinstance(response, dict):
            raise RemnawaveAPIError(status_code=502, message="invalid_user_response")
        normalized = normalize_user(response)
        if normalized.get("user_id") != expected_user_id:
            raise RemnawaveAPIError(status_code=502, message="user_identity_mismatch")
        return normalized

    @classmethod
    def _require_user_status(cls, response: Any, expected_user_id: int, expected_status: str) -> dict:
        user = cls._require_bound_user_response(response, expected_user_id)
        if str(user.get("status") or "").lower() != expected_status:
            raise RemnawaveAPIError(status_code=502, message="user_status_postcondition_mismatch")
        return user

    async def _reconcile_user_status(self, user_id: int, expected_status: str) -> dict:
        user = await self.get_user(user_id)
        if str(user.get("status") or "").lower() != expected_status:
            raise RemnawaveAPIError(status_code=502, message="user_status_postcondition_mismatch")
        return user

    async def get(self, path: str, params: dict | None = None) -> Any | None:
        """Make a GET request to the API.

        Args:
            path: API endpoint path
            params: Optional query parameters

        Returns:
            Response body as dictionary

        Raises:
            RemnawaveAPIError: If request fails
        """
        return await self._request("GET", path, params=params)

    async def post(self, path: str, json: dict | None = None) -> Any | None:
        """Make a POST request to the API.

        Args:
            path: API endpoint path
            json: Optional JSON request body

        Returns:
            Response body as dictionary

        Raises:
            RemnawaveAPIError: If request fails
        """
        return await self._request("POST", path, json=json)

    async def patch(self, path: str, json: dict | None = None) -> Any | None:
        """Make a PATCH request to the API.

        Args:
            path: API endpoint path
            json: Optional JSON request body

        Returns:
            Response body as dictionary

        Raises:
            RemnawaveAPIError: If request fails
        """
        return await self._request("PATCH", path, json=json)

    async def delete(self, path: str) -> Any | None:
        """Make a DELETE request to the API.

        Args:
            path: API endpoint path

        Returns:
            Response body as dictionary

        Raises:
            RemnawaveAPIError: If request fails
        """
        return await self._request("DELETE", path)

    async def health_check(self) -> bool:
        """Check if Remnawave API is healthy and accessible.

        Returns:
            True if API is healthy, False otherwise
        """
        try:
            for path in ("/system/health", "/health"):
                try:
                    await self.get(path)
                    return True
                except RemnawaveAPIError:
                    continue
            return False
        except RemnawaveAPIError:
            return False

    async def get_nodes(self) -> list[dict]:
        """Get list of all VPN nodes.

        Returns:
            List of node dictionaries

        Raises:
            RemnawaveAPIError: If request fails
        """
        response = await self.get("/api/nodes")
        nodes = self._require_collection(response, "nodes")
        return normalize_nodes(nodes)

    async def get_inbounds(self) -> list[dict]:
        """Get list of all inbounds from Remnawave."""
        response = await self.get("/api/inbounds")
        return self._require_collection(response, "inbounds")

    async def get_hosts(self) -> list[dict]:
        """Get list of all hosts from Remnawave."""
        response = await self.get("/api/hosts")
        return self._require_collection(response, "hosts")

    async def get_users(self) -> list[dict]:
        """Get a bounded, complete cursor snapshot of all users.

        Target Remnawave 3.x exposes ``/users/stream``.  A one-page fallback
        is unsafe for scheduled control-plane jobs because it silently omits
        identities, so missing, repeated, or overlong cursor chains fail the
        entire scan before any caller may act on it.
        """
        users: list[dict] = []
        seen_user_ids: set[int] = set()
        seen_cursors: set[str] = set()
        cursor: str | None = None

        for _page_number in range(_USER_STREAM_MAX_PAGES):
            params: dict[str, object] = {"size": _USER_STREAM_PAGE_SIZE}
            if cursor is not None:
                params["cursor"] = cursor
            response = await self.get("/api/users/stream", params=params)
            if not isinstance(response, dict):
                raise RemnawaveAPIError(status_code=502, message="invalid_users_stream_response")

            page_payload = response.get("users")
            if page_payload is None:
                page_payload = response.get("response")
            if not isinstance(page_payload, list) or any(not isinstance(item, dict) for item in page_payload):
                raise RemnawaveAPIError(status_code=502, message="invalid_users_stream_collection")
            page = normalize_users(page_payload)
            for user in page:
                user_id = user["id"]
                if user_id in seen_user_ids:
                    raise RemnawaveAPIError(status_code=502, message="duplicate_users_stream_identity")
                seen_user_ids.add(user_id)
                users.append(user)

            has_next_raw = response.get("hasNextPage", response.get("hasMore", response.get("hasNext")))
            if has_next_raw is not None and not isinstance(has_next_raw, bool):
                raise RemnawaveAPIError(status_code=502, message="invalid_users_stream_pagination")
            if has_next_raw is False:
                return users

            next_cursor_raw = response.get("nextCursor", response.get("cursor", response.get("next")))
            if next_cursor_raw is None:
                if has_next_raw is True or len(page) >= _USER_STREAM_PAGE_SIZE:
                    raise RemnawaveAPIError(status_code=502, message="incomplete_users_stream_pagination")
                return users
            next_cursor = str(next_cursor_raw).strip()
            if not next_cursor or len(next_cursor) > 128 or not next_cursor.isdecimal():
                raise RemnawaveAPIError(status_code=502, message="invalid_users_stream_cursor")
            if next_cursor in seen_cursors or next_cursor == cursor:
                raise RemnawaveAPIError(status_code=502, message="repeated_users_stream_cursor")
            seen_cursors.add(next_cursor)
            cursor = next_cursor

        raise RemnawaveAPIError(status_code=502, message="users_stream_page_limit_exceeded")

    async def get_user(self, user_id: int) -> dict:
        """Get detailed information for a specific user.

        Args:
            user_id: Numeric Remnawave user ID

        Returns:
            User information dictionary

        Raises:
            RemnawaveAPIError: If request fails or user not found
        """
        expected_user_id = self._validate_user_id(user_id)
        response = await self.get(f"/api/users/{expected_user_id}")
        return self._require_bound_user_response(response, expected_user_id)

    async def disable_user(self, user_id: int) -> dict:
        """Disable a user account.

        Args:
            user_id: Numeric Remnawave user ID to disable

        Returns:
            Updated user information

        Raises:
            RemnawaveAPIError: If request fails or user not found
        """
        expected_user_id = self._validate_user_id(user_id)
        try:
            response = await self.post(f"/api/users/{expected_user_id}/actions/disable")
        except RemnawaveAPIError as exc:
            if exc.status_code != 0:
                raise
            return await self._reconcile_user_status(expected_user_id, "disabled")
        if response is None:
            return await self._reconcile_user_status(expected_user_id, "disabled")
        return self._require_user_status(response, expected_user_id, "disabled")

    async def enable_user(self, user_id: int) -> dict:
        """Enable a user account.

        Args:
            user_id: Numeric Remnawave user ID to enable

        Returns:
            Updated user information

        Raises:
            RemnawaveAPIError: If request fails or user not found
        """
        expected_user_id = self._validate_user_id(user_id)
        try:
            response = await self.post(f"/api/users/{expected_user_id}/actions/enable")
        except RemnawaveAPIError as exc:
            if exc.status_code != 0:
                raise
            return await self._reconcile_user_status(expected_user_id, "active")
        if response is None:
            return await self._reconcile_user_status(expected_user_id, "active")
        return self._require_user_status(response, expected_user_id, "active")

    async def reset_user_traffic(self, user_id: int) -> dict | None:
        """Reset traffic counters for a user.

        Args:
            user_id: Numeric Remnawave user ID to reset traffic for

        Returns:
            Updated user information

        Raises:
            RemnawaveAPIError: If request fails or user not found
        """
        expected_user_id = self._validate_user_id(user_id)
        response = await self.post(f"/api/users/{expected_user_id}/actions/reset-traffic")
        if response is None:
            return None
        return self._require_bound_user_response(response, expected_user_id)

    async def bulk_extend_expiration_date(self, user_ids: list[int], extend_days: int) -> None:
        """Extend expiration date for multiple users.

        Args:
            user_ids: Numeric Remnawave user IDs to extend
            extend_days: Number of days to extend

        Returns:
            None. Remnawave 3.x accepts the operation asynchronously and does
            not return the legacy ``affectedRows`` response.

        Raises:
            RemnawaveAPIError: If request fails
        """
        validated_user_ids = [self._validate_user_id(user_id) for user_id in user_ids]
        if not validated_user_ids:
            raise ValueError("user_ids must not be empty")
        if len(validated_user_ids) > 500:
            raise ValueError("user_ids must contain no more than 500 entries")
        if not 1 <= extend_days <= 9999:
            raise ValueError("extend_days must be between 1 and 9999")

        payload = {"userIds": validated_user_ids, "extendDays": extend_days}
        await self.post("/api/users/bulk/extend-expiration-date", json=payload)

    @staticmethod
    def _validate_user_id(user_id: int) -> int:
        if isinstance(user_id, bool) or not isinstance(user_id, int) or user_id <= 0:
            raise ValueError("Remnawave user_id must be a positive integer")
        return user_id

    async def get_system_stats(self) -> dict:
        """Get system statistics and metrics.

        Returns:
            System statistics dictionary including server load, active connections, etc.

        Raises:
            RemnawaveAPIError: If request fails
        """
        response = await self.get("/api/system/stats")
        if not isinstance(response, dict):
            raise RemnawaveAPIError(status_code=200, message="invalid_system_stats_response")
        return response
