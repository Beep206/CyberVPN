"""Remnawave VPN backend API client.

Wraps httpx.AsyncClient for making authenticated requests to the Remnawave VPN backend.
Includes rate limiting, connection pooling, timeouts, retries, and structured logging.
"""

import asyncio
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Optional

import httpx
import structlog

from src.config import get_settings
from src.utils.rate_limiter import AsyncTokenBucket

logger = structlog.get_logger(__name__)


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
            await client.disable_user(user_uuid)
    """

    def __init__(self, rate_limiter: Optional[AsyncTokenBucket] = None) -> None:
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

        self._base_url = settings.remnawave_url.rstrip("/")
        self._api_token = settings.remnawave_api_token.get_secret_value()

        # Rate limiting: Use token bucket if provided, otherwise fallback to semaphore
        if rate_limiter:
            self._rate_limiter = rate_limiter
            self._use_token_bucket = True
            logger.info("remnawave_client_using_token_bucket", rate=rate_limiter.rate, capacity=rate_limiter.capacity)
        else:
            self._rate_limiter = asyncio.Semaphore(10)
            self._use_token_bucket = False
            logger.info("remnawave_client_using_semaphore", max_concurrent=10)

        # Configure timeouts: connect, read, write, pool
        timeout_config = httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=5.0)

        # Configure connection limits
        limits_config = httpx.Limits(max_connections=50, max_keepalive_connections=10, keepalive_expiry=30.0)

        # Configure transport with connection-level retries
        transport = httpx.AsyncHTTPTransport(retries=2)

        # Initialize httpx client with Bearer token auth
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={"Authorization": f"Bearer {self._api_token}"},
            timeout=timeout_config,
            limits=limits_config,
            transport=transport,
        )

        logger.info("remnawave_client_initialized", base_url=self._base_url)

    async def __aenter__(self) -> "RemnawaveClient":
        """Context manager entry - returns self for async with usage."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit - ensures client cleanup."""
        await self._client.aclose()
        logger.info("remnawave_client_closed")

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict:
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
        if self._use_token_bucket:
            await self._rate_limiter.acquire()  # type: ignore

        # Use context manager for semaphore-based rate limiting
        rate_limit_ctx = self._rate_limiter if not self._use_token_bucket else None  # type: ignore

        async with rate_limit_ctx if rate_limit_ctx else _dummy_context():
            try:
                response = await self._client.request(method, path, **kwargs)
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
                        error_body = response.json()
                    except Exception:
                        error_body = None

                    error_message = error_body.get("message") if error_body else response.text or response.reason_phrase

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

                # Parse and return JSON response
                return response.json()

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

    async def get(self, path: str, params: dict | None = None) -> dict:
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

    async def post(self, path: str, json: dict | None = None) -> dict:
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

    async def patch(self, path: str, json: dict | None = None) -> dict:
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

    async def delete(self, path: str) -> dict:
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
            await self.get("/health")
            return True
        except RemnawaveAPIError:
            try:
                await self.get("/api/health")
                return True
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
        return response if isinstance(response, list) else response.get("nodes", [])

    async def get_users(self) -> list[dict]:
        """Get list of all users.

        Returns:
            List of user dictionaries

        Raises:
            RemnawaveAPIError: If request fails
        """
        response = await self.get("/api/users")
        return response if isinstance(response, list) else response.get("users", [])

    async def get_user(self, uuid: str) -> dict:
        """Get detailed information for a specific user.

        Args:
            uuid: User UUID

        Returns:
            User information dictionary

        Raises:
            RemnawaveAPIError: If request fails or user not found
        """
        return await self.get(f"/api/users/{uuid}")

    async def disable_user(self, uuid: str) -> dict:
        """Disable a user account.

        Args:
            uuid: User UUID to disable

        Returns:
            Updated user information

        Raises:
            RemnawaveAPIError: If request fails or user not found
        """
        return await self.patch(f"/api/users/{uuid}", json={"status": "disabled"})

    async def enable_user(self, uuid: str) -> dict:
        """Enable a user account.

        Args:
            uuid: User UUID to enable

        Returns:
            Updated user information

        Raises:
            RemnawaveAPIError: If request fails or user not found
        """
        return await self.patch(f"/api/users/{uuid}", json={"status": "active"})

    async def reset_user_traffic(self, uuid: str) -> dict:
        """Reset traffic counters for a user.

        Args:
            uuid: User UUID to reset traffic for

        Returns:
            Updated user information

        Raises:
            RemnawaveAPIError: If request fails or user not found
        """
        return await self.patch(f"/api/users/{uuid}/traffic/reset")

    async def bulk_extend_expiration_date(self, uuids: list[str], extend_days: int) -> dict:
        """Extend expiration date for multiple users.

        Args:
            uuids: List of user UUIDs to extend
            extend_days: Number of days to extend

        Returns:
            Response dictionary with affected rows

        Raises:
            RemnawaveAPIError: If request fails
        """
        payload = {"uuids": uuids, "extendDays": extend_days}
        return await self.post("/api/users/bulk/extend-expiration-date", json=payload)

    async def get_system_stats(self) -> dict:
        """Get system statistics and metrics.

        Returns:
            System statistics dictionary including server load, active connections, etc.

        Raises:
            RemnawaveAPIError: If request fails
        """
        return await self.get("/api/system/stats")
