"""CyberVPN Telegram Bot — Backend API client.

Async httpx-based client for CyberVPN Backend API with:
- Retry logic with exponential backoff
- Circuit breaker pattern
- Typed DTO responses
- Structured error handling
"""

from __future__ import annotations

import time
from enum import StrEnum
from typing import Any

import httpx
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.config import BackendSettings

logger = structlog.get_logger(__name__)


# ── Exceptions ───────────────────────────────────────────────────────────


class APIError(Exception):
    """Base API error with status code and detail."""

    def __init__(
        self,
        message: str,
        status_code: int = 0,
        detail: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.detail = detail


class NotFoundError(APIError):
    """Resource not found (404)."""


class AuthError(APIError):
    """Authentication/authorization error (401/403)."""


class RateLimitError(APIError):
    """Rate limit exceeded (429)."""

    def __init__(self, retry_after: int = 60, **kwargs: Any) -> None:
        super().__init__("Rate limit exceeded", status_code=429, **kwargs)
        self.retry_after = retry_after


class ConflictError(APIError):
    """Resource conflict (409)."""


class ServerError(APIError):
    """Backend server error (5xx)."""


# ── Circuit Breaker ──────────────────────────────────────────────────────


class CircuitState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Simple circuit breaker to prevent cascading failures.

    Opens after `failure_threshold` consecutive failures.
    Transitions to half-open after `recovery_timeout` seconds.
    Closes again on a successful request in half-open state.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
    ) -> None:
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._failure_count = 0
        self._state = CircuitState.CLOSED
        self._last_failure_time: float = 0.0

    @property
    def state(self) -> CircuitState:
        """Current circuit state, with automatic half-open transition."""
        if self._state == CircuitState.OPEN:
            elapsed = time.monotonic() - self._last_failure_time
            if elapsed >= self._recovery_timeout:
                self._state = CircuitState.HALF_OPEN
        return self._state

    def record_success(self) -> None:
        """Record a successful request."""
        self._failure_count = 0
        self._state = CircuitState.CLOSED

    def record_failure(self) -> None:
        """Record a failed request."""
        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        if self._failure_count >= self._failure_threshold:
            self._state = CircuitState.OPEN
            logger.warning(
                "circuit_breaker_opened",
                failure_count=self._failure_count,
            )

    @property
    def is_available(self) -> bool:
        """Check if requests are allowed."""
        return self.state != CircuitState.OPEN


# ── API Client ───────────────────────────────────────────────────────────


class CyberVPNAPIClient:
    """Async HTTP client for CyberVPN Backend API.

    Provides typed methods for all API domains: users, subscriptions,
    payments, referrals, promocodes, and admin operations.

    Features:
    - Automatic retry with exponential backoff for transient errors
    - Circuit breaker to prevent cascading failures
    - Typed DTO response parsing
    - Structured logging and error handling
    """

    def __init__(self, settings: BackendSettings) -> None:
        self._settings = settings
        self._circuit = CircuitBreaker()
        self._client = httpx.AsyncClient(
            base_url=str(settings.api_url),
            timeout=httpx.Timeout(
                connect=5.0,
                read=float(settings.timeout),
                write=10.0,
                pool=5.0,
            ),
            limits=httpx.Limits(
                max_connections=100,
                max_keepalive_connections=20,
                keepalive_expiry=30.0,
            ),
            headers={
                "Authorization": f"Bearer {settings.api_key.get_secret_value()}",
                "Content-Type": "application/json",
                "User-Agent": "CyberVPN-TelegramBot/1.0",
            },
            transport=httpx.AsyncHTTPTransport(retries=1),
        )

    # ── Core request method ──────────────────────────────────────────

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type(ServerError),
        reraise=True,
    )
    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[Any]:
        """Execute an HTTP request with retry and circuit breaker.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, PATCH).
            path: API endpoint path (e.g., '/telegram/users').
            json: Request body as dict.
            params: Query parameters.

        Returns:
            Parsed JSON response.

        Raises:
            APIError: On API-level errors.
            ServerError: On 5xx errors (triggers retry).
        """
        if not self._circuit.is_available:
            msg = "Circuit breaker is open — backend unavailable"
            raise APIError(msg, status_code=503)

        try:
            response = await self._client.request(
                method=method,
                url=path,
                json=json,
                params=params,
            )
            self._handle_response(response)
            self._circuit.record_success()

            if response.status_code == 204:
                return {}
            return response.json()

        except (httpx.ConnectError, httpx.PoolTimeout, httpx.ReadTimeout) as exc:
            self._circuit.record_failure()
            logger.error("api_connection_error", path=path, error=str(exc))
            raise ServerError(
                message=f"Backend connection error: {exc}",
                status_code=503,
            ) from exc

    def _handle_response(self, response: httpx.Response) -> None:
        """Map HTTP status codes to typed exceptions."""
        if response.is_success:
            return

        status = response.status_code
        detail = self._extract_detail(response)

        if status == 404:
            raise NotFoundError("Resource not found", status_code=status, detail=detail)
        if status in (401, 403):
            raise AuthError("Authentication failed", status_code=status, detail=detail)
        if status == 429:
            retry_after = int(response.headers.get("Retry-After", "60"))
            raise RateLimitError(retry_after=retry_after, detail=detail)
        if status == 409:
            raise ConflictError("Resource conflict", status_code=status, detail=detail)
        if status >= 500:
            self._circuit.record_failure()
            raise ServerError("Backend server error", status_code=status, detail=detail)

        raise APIError(f"API error: {status}", status_code=status, detail=detail)

    @staticmethod
    def _extract_detail(response: httpx.Response) -> str | None:
        """Extract error detail from response body."""
        try:
            data = response.json()
            return data.get("detail") or data.get("message")
        except Exception:
            return response.text[:200] if response.text else None

    # ── Users ────────────────────────────────────────────────────────

    async def get_user(self, telegram_id: int) -> dict[str, Any]:
        """Get user by Telegram ID.

        Args:
            telegram_id: User's Telegram ID.

        Returns:
            User data dict.
        """
        return await self._request("GET", f"/telegram/users/{telegram_id}")

    async def register_user(
        self,
        telegram_id: int,
        username: str | None = None,
        language: str = "ru",
        referrer_id: int | None = None,
    ) -> dict[str, Any]:
        """Register or update a Telegram user.

        Args:
            telegram_id: User's Telegram ID.
            username: Telegram username.
            language: Preferred language code.
            referrer_id: Referrer's Telegram ID (optional).

        Returns:
            Created/updated user data dict.
        """
        payload: dict[str, Any] = {
            "telegram_id": telegram_id,
            "username": username,
            "language": language,
        }
        if referrer_id is not None:
            payload["referrer_id"] = referrer_id
        return await self._request("POST", "/telegram/users", json=payload)

    async def update_user_language(
        self,
        telegram_id: int,
        language: str,
    ) -> dict[str, Any]:
        """Update user's language preference.

        Args:
            telegram_id: User's Telegram ID.
            language: New language code.

        Returns:
            Updated user data dict.
        """
        return await self._request(
            "PATCH",
            f"/telegram/users/{telegram_id}",
            json={"language": language},
        )

    # ── Subscriptions ────────────────────────────────────────────────

    async def get_user_config(self, telegram_id: int) -> dict[str, Any]:
        """Get user's subscription configuration (connection link).

        Args:
            telegram_id: User's Telegram ID.

        Returns:
            Subscription config with connection link.
        """
        return await self._request("GET", f"/telegram/users/{telegram_id}/config")

    async def get_available_plans(
        self,
        telegram_id: int | None = None,
    ) -> list[Any]:
        """Get available subscription plans.

        Args:
            telegram_id: Optional user ID for personalized plans.

        Returns:
            List of available plan dicts.
        """
        params = {}
        if telegram_id is not None:
            params["telegram_id"] = telegram_id
        return await self._request("GET", "/telegram/plans", params=params)

    async def create_subscription(
        self,
        telegram_id: int,
        plan_id: str,
        duration_days: int,
        *,
        is_trial: bool = False,
    ) -> dict[str, Any]:
        """Create a new subscription for a user.

        Args:
            telegram_id: User's Telegram ID.
            plan_id: Subscription plan identifier.
            duration_days: Subscription duration in days.
            is_trial: Whether this is a trial subscription.

        Returns:
            Created subscription data.
        """
        return await self._request(
            "POST",
            "/telegram/subscriptions",
            json={
                "telegram_id": telegram_id,
                "plan_id": plan_id,
                "duration_days": duration_days,
                "is_trial": is_trial,
            },
        )

    # ── Payments ─────────────────────────────────────────────────────

    async def create_crypto_invoice(
        self,
        amount: str,
        currency: str,
        user_uuid: str,
        plan_id: str,
        payload: str | None = None,
    ) -> dict[str, Any]:
        """Create a Crypto Bot payment invoice.

        Args:
            amount: Payment amount as string.
            currency: Currency code (e.g., "TON", "USDT").
            user_uuid: User's UUID in the backend.
            plan_id: Plan being purchased.
            payload: Optional metadata payload.

        Returns:
            Invoice data with payment URL.
        """
        return await self._request(
            "POST",
            "/telegram/payments/crypto",
            json={
                "amount": amount,
                "currency": currency,
                "user_uuid": user_uuid,
                "plan_id": plan_id,
                "payload": payload,
            },
        )

    async def create_yookassa_payment(
        self,
        amount: str,
        description: str,
        metadata: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Create a YooKassa payment.

        Args:
            amount: Payment amount as string.
            description: Payment description.
            metadata: Additional payment metadata.

        Returns:
            Payment data with confirmation URL.
        """
        return await self._request(
            "POST",
            "/telegram/payments/yookassa",
            json={
                "amount": amount,
                "description": description,
                "metadata": metadata or {},
            },
        )

    async def create_stars_invoice(
        self,
        telegram_id: int,
        plan_id: str,
        duration_days: int,
        amount: int,
    ) -> dict[str, Any]:
        """Create a Telegram Stars invoice.

        Args:
            telegram_id: User's Telegram ID.
            plan_id: Plan being purchased.
            duration_days: Subscription duration.
            amount: Stars amount.

        Returns:
            Invoice data for Telegram Stars payment.
        """
        return await self._request(
            "POST",
            "/telegram/payments/stars",
            json={
                "telegram_id": telegram_id,
                "plan_id": plan_id,
                "duration_days": duration_days,
                "amount": amount,
            },
        )

    async def get_invoice_status(self, invoice_id: str) -> dict[str, Any]:
        """Check payment/invoice status.

        Args:
            invoice_id: Invoice identifier.

        Returns:
            Invoice status data.
        """
        return await self._request("GET", f"/telegram/payments/{invoice_id}")

    # ── Referrals ────────────────────────────────────────────────────

    async def get_referral_stats(self, telegram_id: int) -> dict[str, Any]:
        """Get referral statistics for a user.

        Args:
            telegram_id: User's Telegram ID.

        Returns:
            Referral stats (count, bonus days, referral link).
        """
        return await self._request(
            "GET",
            f"/telegram/referrals/{telegram_id}",
        )

    async def withdraw_referral_points(
        self,
        telegram_id: int,
        points: int,
    ) -> dict[str, Any]:
        """Withdraw referral points/days.

        Args:
            telegram_id: User's Telegram ID.
            points: Number of points to withdraw.

        Returns:
            Updated referral balance.
        """
        return await self._request(
            "POST",
            f"/telegram/referrals/{telegram_id}/withdraw",
            json={"points": points},
        )

    # ── Promocodes ───────────────────────────────────────────────────

    async def activate_promocode(
        self,
        telegram_id: int,
        code: str,
    ) -> dict[str, Any]:
        """Activate a promo code for a user.

        Args:
            telegram_id: User's Telegram ID.
            code: Promo code string.

        Returns:
            Activation result data.
        """
        return await self._request(
            "POST",
            "/telegram/promocodes/activate",
            json={
                "telegram_id": telegram_id,
                "code": code,
            },
        )

    # ── Admin ────────────────────────────────────────────────────────

    async def get_statistics(self) -> dict[str, Any]:
        """Get dashboard statistics.

        Returns:
            Aggregated statistics (users, subscriptions, revenue, etc.).
        """
        return await self._request("GET", "/telegram/admin/statistics")

    async def get_users(
        self,
        search: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> dict[str, Any]:
        """List users with optional search.

        Args:
            search: Search query (username or telegram ID).
            page: Page number.
            per_page: Items per page.

        Returns:
            Paginated user list.
        """
        params: dict[str, Any] = {"page": page, "per_page": per_page}
        if search:
            params["search"] = search
        return await self._request("GET", "/telegram/admin/users", params=params)

    async def manage_user(
        self,
        telegram_id: int,
        action: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Perform an admin action on a user.

        Args:
            telegram_id: Target user's Telegram ID.
            action: Action name (block, unblock, extend, reset_traffic, etc.).
            **kwargs: Action-specific parameters.

        Returns:
            Action result data.
        """
        return await self._request(
            "POST",
            f"/telegram/admin/users/{telegram_id}/{action}",
            json=kwargs if kwargs else None,
        )

    async def get_admin_plans(self) -> list[Any]:
        """Get all subscription plans (admin view).

        Returns:
            List of all plans with full details.
        """
        return await self._request("GET", "/telegram/admin/plans")

    async def get_admin_promocodes(
        self,
        page: int = 1,
        per_page: int = 20,
    ) -> dict[str, Any]:
        """List promo codes (admin view).

        Returns:
            Paginated promo code list.
        """
        return await self._request(
            "GET",
            "/telegram/admin/promocodes",
            params={"page": page, "per_page": per_page},
        )

    async def create_broadcast(
        self,
        message: str,
        audience: str,
    ) -> dict[str, Any]:
        """Create and send a broadcast message.

        Args:
            message: Broadcast message text (HTML).
            audience: Target audience (all, active, expired, trial).

        Returns:
            Broadcast job data (id, status, recipient count).
        """
        return await self._request(
            "POST",
            "/telegram/admin/broadcast",
            json={"message": message, "audience": audience},
        )

    async def get_access_settings(self) -> dict[str, Any]:
        """Get bot access configuration.

        Returns:
            Access settings (mode, channel_id, rules_url, etc.).
        """
        return await self._request("GET", "/telegram/admin/settings/access")

    async def get_gateway_settings(self) -> dict[str, Any]:
        """Get payment gateway configuration.

        Returns:
            Gateway settings for all providers.
        """
        return await self._request("GET", "/telegram/admin/settings/gateways")

    async def get_remnawave_stats(self) -> dict[str, Any]:
        """Get Remnawave VPN server statistics.

        Returns:
            Server health, traffic, and user stats.
        """
        return await self._request("GET", "/telegram/admin/remnawave/stats")

    # ── Lifecycle ────────────────────────────────────────────────────

    async def close(self) -> None:
        """Close the HTTP client and release resources."""
        await self._client.aclose()
        logger.info("api_client_closed")

    async def health_check(self) -> bool:
        """Check backend API health.

        Returns:
            True if the backend is reachable and healthy.
        """
        try:
            await self._request("GET", "/health")
            return True
        except APIError:
            return False
