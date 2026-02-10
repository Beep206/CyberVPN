"""Tests for rate limiter middleware with fail-closed behavior and circuit breaker (MED-1)."""

import time

from src.presentation.middleware.rate_limit import CircuitBreaker


class TestCircuitBreaker:
    """Tests for CircuitBreaker class."""

    def test_initial_state_closed(self):
        """Circuit breaker starts in CLOSED state."""
        cb = CircuitBreaker()
        assert cb.state == CircuitBreaker.CLOSED
        assert not cb.is_open()

    def test_opens_after_threshold_failures(self):
        """Circuit opens after reaching failure threshold."""
        cb = CircuitBreaker(failure_threshold=3)

        cb.record_failure()
        assert cb.state == CircuitBreaker.CLOSED

        cb.record_failure()
        assert cb.state == CircuitBreaker.CLOSED

        cb.record_failure()
        assert cb.state == CircuitBreaker.OPEN
        assert cb.is_open()

    def test_success_resets_failures(self):
        """Recording success resets failure count and closes circuit."""
        cb = CircuitBreaker(failure_threshold=3)

        cb.record_failure()
        cb.record_failure()
        cb.record_success()

        # Third failure should not open circuit (count was reset)
        cb.record_failure()
        assert cb.state == CircuitBreaker.CLOSED

    def test_success_closes_open_circuit(self):
        """Success after half-open state closes the circuit."""
        cb = CircuitBreaker(failure_threshold=1, cooldown_seconds=0.01)

        cb.record_failure()
        assert cb.state == CircuitBreaker.OPEN

        # Wait for cooldown
        time.sleep(0.02)
        assert cb.state == CircuitBreaker.HALF_OPEN

        cb.record_success()
        assert cb.state == CircuitBreaker.CLOSED

    def test_half_open_after_cooldown(self):
        """Circuit transitions to HALF_OPEN after cooldown period."""
        cb = CircuitBreaker(failure_threshold=1, cooldown_seconds=0.01)

        cb.record_failure()
        assert cb.state == CircuitBreaker.OPEN

        time.sleep(0.02)
        assert cb.state == CircuitBreaker.HALF_OPEN

    def test_failure_in_half_open_reopens(self):
        """Failure in half-open state reopens the circuit."""
        cb = CircuitBreaker(failure_threshold=1, cooldown_seconds=0.01)

        cb.record_failure()
        time.sleep(0.02)
        assert cb.state == CircuitBreaker.HALF_OPEN

        cb.record_failure()
        assert cb.state == CircuitBreaker.OPEN

    def test_custom_threshold_and_cooldown(self):
        """Circuit breaker respects custom threshold and cooldown."""
        cb = CircuitBreaker(failure_threshold=5, cooldown_seconds=0.05)

        # Need 5 failures to trip
        for _ in range(4):
            cb.record_failure()
        assert cb.state == CircuitBreaker.CLOSED

        cb.record_failure()  # 5th failure
        assert cb.state == CircuitBreaker.OPEN

        # Cooldown is 50ms
        time.sleep(0.03)
        assert cb.state == CircuitBreaker.OPEN  # Still open

        time.sleep(0.03)
        assert cb.state == CircuitBreaker.HALF_OPEN  # Now half-open


class TestRateLimitMiddlewareConfig:
    """Tests for RateLimitMiddleware configuration."""

    def test_default_fail_closed(self):
        """Default mode is fail-closed (fail_open=False)."""
        from unittest.mock import MagicMock, patch

        from src.presentation.middleware.rate_limit import RateLimitMiddleware

        # Reset class-level circuit breaker
        RateLimitMiddleware._circuit_breaker = None

        with patch("src.presentation.middleware.rate_limit.settings") as mock_settings:
            mock_settings.rate_limit_fail_open = False

            app = MagicMock()
            middleware = RateLimitMiddleware(app)

            assert middleware.fail_open is False

    def test_fail_open_from_settings(self):
        """Can enable fail-open mode via settings."""
        from unittest.mock import MagicMock, patch

        from src.presentation.middleware.rate_limit import RateLimitMiddleware

        # Reset class-level circuit breaker
        RateLimitMiddleware._circuit_breaker = None

        with patch("src.presentation.middleware.rate_limit.settings") as mock_settings:
            mock_settings.rate_limit_fail_open = True

            app = MagicMock()
            middleware = RateLimitMiddleware(app)

            assert middleware.fail_open is True

    def test_explicit_fail_open_overrides_settings(self):
        """Explicit fail_open parameter overrides settings."""
        from unittest.mock import MagicMock, patch

        from src.presentation.middleware.rate_limit import RateLimitMiddleware

        # Reset class-level circuit breaker
        RateLimitMiddleware._circuit_breaker = None

        with patch("src.presentation.middleware.rate_limit.settings") as mock_settings:
            mock_settings.rate_limit_fail_open = True

            app = MagicMock()
            middleware = RateLimitMiddleware(app, fail_open=False)

            assert middleware.fail_open is False

    def test_custom_rate_limit(self):
        """Can configure custom requests_per_minute."""
        from unittest.mock import MagicMock

        from src.presentation.middleware.rate_limit import RateLimitMiddleware

        # Reset class-level circuit breaker
        RateLimitMiddleware._circuit_breaker = None

        app = MagicMock()
        middleware = RateLimitMiddleware(app, requests_per_minute=100, fail_open=False)

        assert middleware.requests_per_minute == 100

    def test_circuit_breaker_is_shared(self):
        """Circuit breaker is shared across middleware instances."""
        from unittest.mock import MagicMock

        from src.presentation.middleware.rate_limit import RateLimitMiddleware

        # Reset class-level circuit breaker
        RateLimitMiddleware._circuit_breaker = None

        app = MagicMock()
        middleware1 = RateLimitMiddleware(app, fail_open=False)
        middleware2 = RateLimitMiddleware(app, fail_open=False)

        # Both should share the same circuit breaker
        assert middleware1.circuit is middleware2.circuit

        # Failure recorded by one affects the other
        middleware1.circuit.record_failure()
        assert middleware2.circuit._failure_count == 1
