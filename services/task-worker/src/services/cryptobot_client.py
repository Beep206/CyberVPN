"""CryptoBot Payment API client wrapper.

This module provides an async HTTP client for interacting with the CryptoBot Payment API.
It handles authentication, request/response formatting, error handling, and connection management.

References:
- CryptoBot API: https://help.crypt.bot/crypto-pay-api
"""

from typing import Any

import httpx
import structlog
from pydantic import SecretStr

from src.config import get_settings

logger = structlog.get_logger(__name__)


class CryptoBotAPIError(Exception):
    """Exception raised when CryptoBot API returns an error response.

    Attributes:
        status_code: HTTP status code from the response
        error_code: CryptoBot error code if available
        message: Error message from the API
        response: Raw response data
    """

    def __init__(self, status_code: int, message: str, error_code: int | None = None, response: dict | None = None):
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        self.response = response or {}
        super().__init__(f"CryptoBot API error {status_code}: {message}")


class CryptoBotClient:
    """Async HTTP client for CryptoBot Payment API.

    This client manages a persistent httpx.AsyncClient connection with proper
    authentication, timeouts, and error handling for all CryptoBot API operations.

    Example:
        async with CryptoBotClient(token="your_token") as client:
            invoices = await client.get_invoices(status="active")
            balance = await client.get_balance()

    Attributes:
        base_url: CryptoBot API base URL
        token: API authentication token (SecretStr)
        client: Persistent httpx.AsyncClient instance
    """

    def __init__(self, token: SecretStr | None = None):
        """Initialize CryptoBot client with authentication token.

        Args:
            token: CryptoBot API token (SecretStr for secure handling)
        """
        settings = get_settings()
        self.base_url = "https://pay.crypt.bot/api"
        self.token = token or settings.cryptobot_token
        self.client: httpx.AsyncClient | None = None
        self._log = logger.bind(service="cryptobot_client")

    async def __aenter__(self) -> "CryptoBotClient":
        """Async context manager entry - initializes HTTP client."""
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Crypto-Pay-API-Token": self.token.get_secret_value()},
            timeout=httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=5.0),
        )
        self._log.info("cryptobot_client_initialized")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit - closes HTTP client."""
        if self.client:
            await self.client.aclose()
            self._log.info("cryptobot_client_closed")

    def _ensure_client(self) -> httpx.AsyncClient:
        """Ensure client is initialized, raise error if not.

        Returns:
            Initialized httpx.AsyncClient instance

        Raises:
            RuntimeError: If client is used outside of context manager
        """
        if self.client is None:
            raise RuntimeError("CryptoBotClient must be used as async context manager")
        return self.client

    async def _request(self, method: str, endpoint: str, **kwargs) -> dict[str, Any]:
        """Execute HTTP request with error handling.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path (without base URL)
            **kwargs: Additional arguments for httpx request

        Returns:
            Parsed JSON response data

        Raises:
            CryptoBotAPIError: On non-2xx response or API error
        """
        client = self._ensure_client()

        try:
            response = await client.request(method, endpoint, **kwargs)
            response.raise_for_status()

            data = response.json()

            # CryptoBot API returns {"ok": true/false, "result": {...}} format
            if not data.get("ok"):
                error_code = data.get("error", {}).get("code")
                error_message = data.get("error", {}).get("name", "Unknown error")
                self._log.error(
                    "cryptobot_api_error",
                    endpoint=endpoint,
                    error_code=error_code,
                    error_message=error_message,
                    response=data,
                )
                raise CryptoBotAPIError(
                    status_code=response.status_code,
                    message=error_message,
                    error_code=error_code,
                    response=data,
                )

            self._log.debug("cryptobot_request_success", endpoint=endpoint, method=method)
            return data.get("result", {})

        except httpx.HTTPStatusError as e:
            error_message = f"HTTP {e.response.status_code}"
            try:
                error_data = e.response.json()
                error_message = error_data.get("error", {}).get("name", error_message)
            except Exception:
                pass

            self._log.error(
                "cryptobot_http_error",
                endpoint=endpoint,
                status_code=e.response.status_code,
                error_message=error_message,
            )
            raise CryptoBotAPIError(
                status_code=e.response.status_code,
                message=error_message,
            ) from e

        except httpx.RequestError as e:
            self._log.error("cryptobot_request_error", endpoint=endpoint, error=str(e))
            raise CryptoBotAPIError(
                status_code=0,
                message=f"Request failed: {str(e)}",
            ) from e

    async def get_invoices(self, invoice_ids: list[int] | None = None, status: str | None = None) -> list[dict]:
        """Get list of invoices with optional filters.

        Args:
            invoice_ids: Optional list of invoice IDs to filter by
            status: Optional status filter ("active", "paid", "expired")

        Returns:
            List of invoice objects

        Raises:
            CryptoBotAPIError: On API error or network failure
        """
        params = {}
        if invoice_ids:
            params["invoice_ids"] = ",".join(map(str, invoice_ids))
        if status:
            params["status"] = status

        result = await self._request("GET", "/getInvoices", params=params)
        return result.get("items", [])

    async def create_invoice(
        self,
        amount: float,
        currency: str = "USDT",
        description: str = "",
        payload: str = "",
    ) -> dict:
        """Create a new payment invoice.

        Args:
            amount: Invoice amount
            currency: Payment currency (default: "USDT")
            description: Invoice description (optional)
            payload: Custom payload data (optional)

        Returns:
            Created invoice object

        Raises:
            CryptoBotAPIError: On API error or network failure
        """
        payload_data = {
            "amount": amount,
            "currency_type": "crypto",
            "asset": currency,
        }

        if description:
            payload_data["description"] = description
        if payload:
            payload_data["payload"] = payload

        return await self._request("POST", "/createInvoice", json=payload_data)

    async def get_balance(self) -> list[dict]:
        """Get account balance for all currencies.

        Returns:
            List of balance objects with currency and amount

        Raises:
            CryptoBotAPIError: On API error or network failure
        """
        return await self._request("GET", "/getBalance")

    async def health_check(self) -> bool:
        """Perform health check by calling get_balance.

        Returns:
            True if API is accessible and responding, False otherwise
        """
        try:
            await self.get_balance()
            self._log.info("cryptobot_health_check_passed")
            return True
        except Exception as e:
            self._log.warning("cryptobot_health_check_failed", error=str(e))
            return False
