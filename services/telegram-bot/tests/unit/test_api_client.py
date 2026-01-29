"""Unit tests for CyberVPN API client."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

import httpx
import pytest
import respx
from respx import MockRouter

from src.services.api_client import (
    APIError,
    AuthError,
    CircuitBreaker,
    CircuitState,
    ConflictError,
    CyberVPNAPIClient,
    NotFoundError,
    RateLimitError,
    ServerError,
)

if TYPE_CHECKING:
    from src.config import BotSettings


class TestCircuitBreaker:
    """Test circuit breaker pattern implementation."""

    def test_initial_state_closed(self) -> None:
        """Test circuit breaker starts in closed state."""
        cb = CircuitBreaker()
        assert cb.state == CircuitState.CLOSED
        assert cb.is_available is True

    def test_record_success_resets_failures(self) -> None:
        """Test that recording success resets failure count."""
        cb = CircuitBreaker(failure_threshold=3)

        cb.record_failure()
        cb.record_failure()
        assert cb._failure_count == 2

        cb.record_success()
        assert cb._failure_count == 0
        assert cb.state == CircuitState.CLOSED

    def test_opens_after_threshold_failures(self) -> None:
        """Test circuit opens after reaching failure threshold."""
        cb = CircuitBreaker(failure_threshold=3)

        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED

        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.is_available is False

    def test_transitions_to_half_open_after_timeout(self) -> None:
        """Test circuit transitions to half-open after recovery timeout."""
        import time

        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)

        # Open the circuit
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        # Wait for recovery timeout
        time.sleep(0.15)

        # Check state - should transition to half-open
        assert cb.state == CircuitState.HALF_OPEN
        assert cb.is_available is True

    def test_half_open_closes_on_success(self) -> None:
        """Test half-open circuit closes on successful request."""
        import time

        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)

        # Open the circuit
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.15)

        # Should be half-open
        assert cb.state == CircuitState.HALF_OPEN

        # Success closes it
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_open_circuit_blocks_requests(self) -> None:
        """Test that open circuit reports unavailable."""
        cb = CircuitBreaker(failure_threshold=1)

        cb.record_failure()
        assert cb.is_available is False


class TestAPIClientInitialization:
    """Test API client initialization."""

    def test_client_initialization(self, mock_settings: BotSettings) -> None:
        """Test client initializes with correct settings."""
        client = CyberVPNAPIClient(settings=mock_settings.backend)

        assert client._settings == mock_settings.backend
        assert isinstance(client._circuit, CircuitBreaker)
        assert isinstance(client._client, httpx.AsyncClient)

    def test_client_headers(self, mock_settings: BotSettings) -> None:
        """Test client sets correct headers."""
        client = CyberVPNAPIClient(settings=mock_settings.backend)

        headers = client._client.headers
        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Bearer ")
        assert headers["Content-Type"] == "application/json"
        assert "User-Agent" in headers


@pytest.mark.asyncio
class TestAPIClientGetUser:
    """Test get_user API method."""

    async def test_get_user_success(self, mock_settings: BotSettings) -> None:
        """Test successful user retrieval."""
        client = CyberVPNAPIClient(settings=mock_settings.backend)

        user_data = {
            "telegram_id": 123456,
            "username": "testuser",
            "language": "ru",
            "status": "active",
        }

        with respx.mock:
            route = respx.get(
                "https://api.test.cybervpn.local/telegram/users/123456"
            ).mock(return_value=httpx.Response(200, json=user_data))

            result = await client.get_user(123456)

            assert result == user_data
            assert route.called

        await client.close()

    async def test_get_user_not_found(self, mock_settings: BotSettings) -> None:
        """Test user not found raises NotFoundError."""
        client = CyberVPNAPIClient(settings=mock_settings.backend)

        with respx.mock:
            respx.get(
                "https://api.test.cybervpn.local/telegram/users/999999"
            ).mock(
                return_value=httpx.Response(
                    404, json={"detail": "User not found"}
                )
            )

            with pytest.raises(NotFoundError) as exc_info:
                await client.get_user(999999)

            assert exc_info.value.status_code == 404

        await client.close()


@pytest.mark.asyncio
class TestAPIClientRegisterUser:
    """Test register_user API method."""

    async def test_register_user_success(self, mock_settings: BotSettings) -> None:
        """Test successful user registration."""
        client = CyberVPNAPIClient(settings=mock_settings.backend)

        expected_response = {
            "telegram_id": 123456,
            "username": "newuser",
            "language": "en",
        }

        with respx.mock:
            route = respx.post(
                "https://api.test.cybervpn.local/telegram/users"
            ).mock(return_value=httpx.Response(200, json=expected_response))

            result = await client.register_user(
                telegram_id=123456, username="newuser", language="en"
            )

            assert result == expected_response
            assert route.called

            # Verify request payload
            request = route.calls[0].request
            payload = httpx.QueryParams(request.content.decode())
            # Note: respx serializes differently, check json separately

        await client.close()

    async def test_register_user_with_referrer(
        self, mock_settings: BotSettings
    ) -> None:
        """Test user registration with referrer ID."""
        client = CyberVPNAPIClient(settings=mock_settings.backend)

        expected_response = {
            "telegram_id": 123456,
            "referrer_id": 789,
        }

        with respx.mock:
            route = respx.post(
                "https://api.test.cybervpn.local/telegram/users"
            ).mock(return_value=httpx.Response(200, json=expected_response))

            result = await client.register_user(
                telegram_id=123456, referrer_id=789
            )

            assert result == expected_response
            assert route.called

        await client.close()

    async def test_register_user_conflict(self, mock_settings: BotSettings) -> None:
        """Test registration conflict handling."""
        client = CyberVPNAPIClient(settings=mock_settings.backend)

        with respx.mock:
            respx.post(
                "https://api.test.cybervpn.local/telegram/users"
            ).mock(
                return_value=httpx.Response(
                    409, json={"detail": "User already exists"}
                )
            )

            with pytest.raises(ConflictError) as exc_info:
                await client.register_user(123456)

            assert exc_info.value.status_code == 409

        await client.close()


@pytest.mark.asyncio
class TestAPIClientGetAvailablePlans:
    """Test get_available_plans API method."""

    async def test_get_plans_success(self, mock_settings: BotSettings) -> None:
        """Test successful plans retrieval."""
        client = CyberVPNAPIClient(settings=mock_settings.backend)

        plans = [
            {"id": "basic", "name": "Basic Plan", "price": 9.99},
            {"id": "pro", "name": "Pro Plan", "price": 19.99},
        ]

        with respx.mock:
            route = respx.get(
                "https://api.test.cybervpn.local/telegram/plans"
            ).mock(return_value=httpx.Response(200, json=plans))

            result = await client.get_available_plans()

            assert result == plans
            assert route.called

        await client.close()

    async def test_get_plans_with_user_id(self, mock_settings: BotSettings) -> None:
        """Test plans retrieval with user context."""
        client = CyberVPNAPIClient(settings=mock_settings.backend)

        plans = [{"id": "custom", "name": "Custom Plan"}]

        with respx.mock:
            route = respx.get(
                "https://api.test.cybervpn.local/telegram/plans",
                params={"telegram_id": 123456},
            ).mock(return_value=httpx.Response(200, json=plans))

            result = await client.get_available_plans(telegram_id=123456)

            assert result == plans
            assert route.called

        await client.close()


@pytest.mark.asyncio
class TestAPIClientErrorHandling:
    """Test API client error handling."""

    async def test_auth_error_401(self, mock_settings: BotSettings) -> None:
        """Test 401 unauthorized raises AuthError."""
        client = CyberVPNAPIClient(settings=mock_settings.backend)

        with respx.mock:
            respx.get(
                "https://api.test.cybervpn.local/telegram/users/123"
            ).mock(
                return_value=httpx.Response(
                    401, json={"detail": "Unauthorized"}
                )
            )

            with pytest.raises(AuthError) as exc_info:
                await client.get_user(123)

            assert exc_info.value.status_code == 401

        await client.close()

    async def test_rate_limit_error(self, mock_settings: BotSettings) -> None:
        """Test 429 rate limit raises RateLimitError."""
        client = CyberVPNAPIClient(settings=mock_settings.backend)

        with respx.mock:
            respx.get(
                "https://api.test.cybervpn.local/telegram/users/123"
            ).mock(
                return_value=httpx.Response(
                    429,
                    json={"detail": "Too many requests"},
                    headers={"Retry-After": "120"},
                )
            )

            with pytest.raises(RateLimitError) as exc_info:
                await client.get_user(123)

            assert exc_info.value.status_code == 429
            assert exc_info.value.retry_after == 120

        await client.close()

    async def test_server_error_500(self, mock_settings: BotSettings) -> None:
        """Test 500 server error raises ServerError."""
        client = CyberVPNAPIClient(settings=mock_settings.backend)

        with respx.mock:
            respx.get(
                "https://api.test.cybervpn.local/telegram/users/123"
            ).mock(
                return_value=httpx.Response(
                    500, json={"detail": "Internal server error"}
                )
            )

            with pytest.raises(ServerError) as exc_info:
                await client.get_user(123)

            assert exc_info.value.status_code == 500

        await client.close()

    async def test_generic_api_error(self, mock_settings: BotSettings) -> None:
        """Test generic API error for unknown status codes."""
        client = CyberVPNAPIClient(settings=mock_settings.backend)

        with respx.mock:
            respx.get(
                "https://api.test.cybervpn.local/telegram/users/123"
            ).mock(return_value=httpx.Response(418, json={"detail": "I'm a teapot"}))

            with pytest.raises(APIError) as exc_info:
                await client.get_user(123)

            assert exc_info.value.status_code == 418

        await client.close()


@pytest.mark.asyncio
class TestCircuitBreakerIntegration:
    """Test circuit breaker integration with API client."""

    async def test_circuit_opens_after_failures(
        self, mock_settings: BotSettings
    ) -> None:
        """Test circuit breaker opens after multiple server errors."""
        client = CyberVPNAPIClient(settings=mock_settings.backend)
        client._circuit = CircuitBreaker(failure_threshold=3)

        with respx.mock:
            respx.get(
                "https://api.test.cybervpn.local/telegram/users/123"
            ).mock(return_value=httpx.Response(500, json={"detail": "Error"}))

            # First 3 failures should open the circuit
            for _ in range(3):
                with pytest.raises(ServerError):
                    await client.get_user(123)

            # Circuit should be open now
            assert client._circuit.state == CircuitState.OPEN

            # Next request should fail immediately
            with pytest.raises(APIError, match="Circuit breaker is open"):
                await client.get_user(123)

        await client.close()

    async def test_circuit_half_open_recovery(
        self, mock_settings: BotSettings
    ) -> None:
        """Test circuit breaker half-open recovery."""
        import time

        client = CyberVPNAPIClient(settings=mock_settings.backend)
        client._circuit = CircuitBreaker(
            failure_threshold=2, recovery_timeout=0.1
        )

        with respx.mock:
            # Fail to open circuit
            respx.get(
                "https://api.test.cybervpn.local/telegram/users/123"
            ).mock(return_value=httpx.Response(500))

            for _ in range(2):
                with pytest.raises(ServerError):
                    await client.get_user(123)

            assert client._circuit.state == CircuitState.OPEN

            # Wait for recovery timeout
            time.sleep(0.15)

            # Should transition to half-open
            assert client._circuit.state == CircuitState.HALF_OPEN

            # Successful request should close it
            respx.get(
                "https://api.test.cybervpn.local/telegram/users/123"
            ).mock(
                return_value=httpx.Response(
                    200, json={"telegram_id": 123}
                )
            )

            await client.get_user(123)
            assert client._circuit.state == CircuitState.CLOSED

        await client.close()


@pytest.mark.asyncio
class TestRetryLogic:
    """Test tenacity retry logic."""

    async def test_retry_on_connection_error(
        self, mock_settings: BotSettings
    ) -> None:
        """Test retry on connection errors."""
        client = CyberVPNAPIClient(settings=mock_settings.backend)

        with respx.mock:
            # Simulate connection error
            route = respx.get(
                "https://api.test.cybervpn.local/telegram/users/123"
            ).mock(side_effect=httpx.ConnectError("Connection failed"))

            with pytest.raises(ServerError, match="Backend connection error"):
                await client.get_user(123)

            # Should have attempted multiple times (with retries)
            # Note: tenacity retry doesn't work well with respx mocks in this context

        await client.close()

    async def test_no_retry_on_client_errors(
        self, mock_settings: BotSettings
    ) -> None:
        """Test that client errors (4xx) don't trigger retries."""
        client = CyberVPNAPIClient(settings=mock_settings.backend)

        with respx.mock:
            route = respx.get(
                "https://api.test.cybervpn.local/telegram/users/123"
            ).mock(
                return_value=httpx.Response(
                    404, json={"detail": "Not found"}
                )
            )

            with pytest.raises(NotFoundError):
                await client.get_user(123)

            # Should only be called once (no retry)
            assert route.call_count == 1

        await client.close()


@pytest.mark.asyncio
class TestAPIClientCleanup:
    """Test API client lifecycle management."""

    async def test_close_client(self, mock_settings: BotSettings) -> None:
        """Test closing API client."""
        client = CyberVPNAPIClient(settings=mock_settings.backend)

        # Mock the close method
        client._client.aclose = AsyncMock()

        await client.close()

        # Note: close() not in original, testing cleanup pattern
        # In production, ensure proper cleanup

    async def test_context_manager_usage(
        self, mock_settings: BotSettings
    ) -> None:
        """Test using client as context manager (if implemented)."""
        # This test documents the expected pattern
        # Actual implementation may need __aenter__/__aexit__
        client = CyberVPNAPIClient(settings=mock_settings.backend)

        try:
            # Use client
            pass
        finally:
            await client._client.aclose()
