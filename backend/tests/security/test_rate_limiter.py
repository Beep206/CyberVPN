"""Tests for rate limiter middleware with fail-closed behavior and circuit breaker (MED-1)."""

import time
from unittest.mock import MagicMock, patch

import pytest
from starlette.requests import Request

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
        from src.presentation.middleware.rate_limit import RateLimitMiddleware

        # Reset class-level circuit breaker
        RateLimitMiddleware._circuit_breaker = None

        with patch("src.presentation.middleware.rate_limit.settings") as mock_settings:
            mock_settings.rate_limit_fail_open = False
            mock_settings.environment = "production"
            mock_settings.helix_admin_read_rate_limit_requests = 1500

            app = MagicMock()
            middleware = RateLimitMiddleware(app)

            assert middleware.fail_open is False

    def test_fail_open_from_settings(self):
        """Can enable fail-open mode via settings."""
        from src.presentation.middleware.rate_limit import RateLimitMiddleware

        # Reset class-level circuit breaker
        RateLimitMiddleware._circuit_breaker = None

        with patch("src.presentation.middleware.rate_limit.settings") as mock_settings:
            mock_settings.rate_limit_fail_open = True
            mock_settings.environment = "production"
            mock_settings.helix_admin_read_rate_limit_requests = 1500

            app = MagicMock()
            middleware = RateLimitMiddleware(app)

            assert middleware.fail_open is True

    def test_explicit_fail_open_overrides_settings(self):
        """Explicit fail_open parameter overrides settings."""
        from src.presentation.middleware.rate_limit import RateLimitMiddleware

        # Reset class-level circuit breaker
        RateLimitMiddleware._circuit_breaker = None

        with patch("src.presentation.middleware.rate_limit.settings") as mock_settings:
            mock_settings.rate_limit_fail_open = True
            mock_settings.environment = "production"
            mock_settings.helix_admin_read_rate_limit_requests = 1500

            app = MagicMock()
            middleware = RateLimitMiddleware(app, fail_open=False)

            assert middleware.fail_open is False

    def test_custom_rate_limit(self):
        """Can configure custom requests_per_minute."""
        from src.presentation.middleware.rate_limit import RateLimitMiddleware

        # Reset class-level circuit breaker
        RateLimitMiddleware._circuit_breaker = None

        app = MagicMock()
        middleware = RateLimitMiddleware(app, requests_per_minute=100, fail_open=False)

        assert middleware.requests_per_minute == 100

    def test_circuit_breaker_is_shared(self):
        """Circuit breaker is shared across middleware instances."""
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

    def test_helix_admin_read_budget_uses_separate_limit(self):
        """Helix admin GET routes get a higher polling budget than public routes."""
        from src.presentation.middleware.rate_limit import RateLimitMiddleware

        RateLimitMiddleware._circuit_breaker = None

        with patch("src.presentation.middleware.rate_limit.settings") as mock_settings:
            mock_settings.rate_limit_fail_open = False
            mock_settings.helix_admin_read_rate_limit_requests = 1500

            app = MagicMock()
            middleware = RateLimitMiddleware(app, requests_per_minute=100, fail_open=False)

            request = Request(
                {
                    "type": "http",
                    "method": "GET",
                    "path": "/api/v1/helix/admin/rollouts/rollout-helix-lab/canary-evidence",
                    "headers": [],
                }
            )

            assert middleware._requests_budget_for(request) == 1500

    def test_non_helix_or_non_get_routes_keep_default_budget(self):
        """POST admin actions and non-Helix routes keep the default global budget."""
        from src.presentation.middleware.rate_limit import RateLimitMiddleware

        RateLimitMiddleware._circuit_breaker = None

        with patch("src.presentation.middleware.rate_limit.settings") as mock_settings:
            mock_settings.rate_limit_fail_open = False
            mock_settings.helix_admin_read_rate_limit_requests = 1500

            app = MagicMock()
            middleware = RateLimitMiddleware(app, requests_per_minute=100, fail_open=False)

            admin_post = Request(
                {
                    "type": "http",
                    "method": "POST",
                    "path": "/api/v1/helix/admin/rollouts/rollout-helix-lab/pause",
                    "headers": [],
                }
            )
            public_get = Request(
                {
                    "type": "http",
                    "method": "GET",
                    "path": "/api/v1/auth/me",
                    "headers": [],
                }
            )

            assert middleware._requests_budget_for(admin_post) == 100
            assert middleware._requests_budget_for(public_get) == 100

    @pytest.mark.parametrize(
        ("method", "path", "expected_budget", "expected_bucket"),
        [
            ("POST", "/api/v1/auth/login", 7, "s1_auth_sensitive"),
            ("POST", "/api/v1/auth/register", 7, "s1_auth_sensitive"),
            ("POST", "/api/v1/auth/magic-link/verify-otp", 7, "s1_auth_sensitive"),
            ("POST", "/api/v1/auth/telegram/miniapp", 7, "s1_auth_sensitive"),
            ("POST", "/api/v1/oauth/google/login/callback", 7, "s1_auth_sensitive"),
            ("POST", "/api/v1/oauth/github/login/callback", 7, "s1_auth_sensitive"),
            ("POST", "/api/v1/invites/redeem", 11, "s1_growth_sensitive"),
        ],
    )
    def test_stage2_public_auth_registration_paths_use_sensitive_buckets(
        self,
        method: str,
        path: str,
        expected_budget: int,
        expected_bucket: str,
    ):
        """S2 public auth and invite entrypoints use bounded launch-sensitive budgets."""
        from src.presentation.middleware.rate_limit import RateLimitMiddleware

        RateLimitMiddleware._circuit_breaker = None

        app = MagicMock()
        middleware = RateLimitMiddleware(
            app,
            requests_per_minute=100,
            fail_open=False,
            auth_sensitive_requests_per_minute=7,
            growth_sensitive_requests_per_minute=11,
        )
        request = Request({"type": "http", "method": method, "path": path, "headers": []})

        assert middleware._requests_budget_for(request) == expected_budget
        assert middleware._rate_limit_bucket_for(request) == expected_bucket
