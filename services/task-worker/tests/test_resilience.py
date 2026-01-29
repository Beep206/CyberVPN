"""Tests for resilience and security features.

Tests security hardening, circuit breaker, idempotency, and rate limiting.
"""

import asyncio
import pytest

from src.security import mask_secret, validate_secrets
from src.services.circuit_breaker import CircuitBreaker, CircuitBreakerError, CircuitState
from src.utils.idempotency import idempotency_key
from src.utils.rate_limiter import AsyncTokenBucket


class TestSecurityHardening:
    """Tests for security audit utilities."""

    def test_mask_secret_full_length(self):
        """Test masking secrets with sufficient length."""
        assert mask_secret("sk_live_1234567890abcdef", 4) == "***cdef"
        assert mask_secret("very_long_secret_token_here", 6) == "***n_here"

    def test_mask_secret_short_value(self):
        """Test masking very short secrets."""
        assert mask_secret("abc", 4) == "***"
        assert mask_secret("", 4) == "***"

    def test_mask_secret_exact_length(self):
        """Test masking when value length equals visible chars."""
        assert mask_secret("test", 4) == "***"

    def test_validate_secrets_structure(self):
        """Test that validate_secrets returns a list of warnings."""
        warnings = validate_secrets()
        assert isinstance(warnings, list)
        # Warnings depend on environment configuration


class TestCircuitBreaker:
    """Tests for circuit breaker implementation."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_success(self):
        """Test successful calls keep circuit closed."""
        breaker = CircuitBreaker(name="test", failure_threshold=3)

        async def success_func():
            return "success"

        result = await breaker.call(success_func)
        assert result == "success"
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_on_failures(self):
        """Test circuit opens after threshold failures."""
        breaker = CircuitBreaker(name="test", failure_threshold=3, recovery_timeout=1.0)

        async def failing_func():
            raise ValueError("API error")

        # Should fail 3 times before opening
        for i in range(3):
            with pytest.raises(ValueError):
                await breaker.call(failing_func)

        # Circuit should now be OPEN
        assert breaker.state == CircuitState.OPEN

        # Next call should be rejected immediately
        with pytest.raises(CircuitBreakerError):
            await breaker.call(failing_func)

    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_recovery(self):
        """Test circuit transitions to half-open after timeout."""
        breaker = CircuitBreaker(
            name="test",
            failure_threshold=2,
            recovery_timeout=0.1,
            half_open_max_calls=1
        )

        async def failing_func():
            raise ValueError("API error")

        async def success_func():
            return "recovered"

        # Open the circuit
        for i in range(2):
            with pytest.raises(ValueError):
                await breaker.call(failing_func)

        assert breaker.state == CircuitState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(0.15)

        # Next call should transition to HALF_OPEN and succeed
        result = await breaker.call(success_func)
        assert result == "recovered"
        assert breaker.state == CircuitState.CLOSED


class TestIdempotency:
    """Tests for idempotency utilities."""

    def test_idempotency_key_deterministic(self):
        """Test idempotency key is deterministic for same inputs."""
        key1 = idempotency_key("task_name", "arg1", kwarg1="value1")
        key2 = idempotency_key("task_name", "arg1", kwarg1="value1")
        assert key1 == key2

    def test_idempotency_key_different_args(self):
        """Test different arguments produce different keys."""
        key1 = idempotency_key("task_name", "arg1")
        key2 = idempotency_key("task_name", "arg2")
        assert key1 != key2

    def test_idempotency_key_kwargs_order(self):
        """Test kwargs order doesn't affect key."""
        key1 = idempotency_key("task", a=1, b=2, c=3)
        key2 = idempotency_key("task", c=3, a=1, b=2)
        assert key1 == key2

    def test_idempotency_key_format(self):
        """Test idempotency key has correct format."""
        key = idempotency_key("test_task", 123)
        assert key.startswith("cybervpn:idempotency:")
        assert len(key) > 30  # Prefix + SHA-256 hash


class TestRateLimiter:
    """Tests for async token bucket rate limiter."""

    @pytest.mark.asyncio
    async def test_rate_limiter_immediate_acquire(self):
        """Test acquiring tokens when bucket is full."""
        limiter = AsyncTokenBucket(rate=10.0, capacity=10)

        # Should acquire immediately from full bucket
        acquired = await limiter.acquire(tokens=5)
        assert acquired is True

    @pytest.mark.asyncio
    async def test_rate_limiter_try_acquire(self):
        """Test non-blocking token acquisition."""
        limiter = AsyncTokenBucket(rate=10.0, capacity=5)

        # Acquire all tokens
        assert await limiter.try_acquire(tokens=5) is True

        # Next acquire should fail (no wait)
        assert await limiter.try_acquire(tokens=1) is False

    @pytest.mark.asyncio
    async def test_rate_limiter_refill(self):
        """Test tokens refill over time."""
        limiter = AsyncTokenBucket(rate=10.0, capacity=10)

        # Consume all tokens
        await limiter.acquire(tokens=10)

        # Wait for refill (10 tokens/sec = 0.5s for 5 tokens)
        await asyncio.sleep(0.5)

        # Should be able to acquire ~5 tokens
        acquired = await limiter.try_acquire(tokens=4)
        assert acquired is True

    @pytest.mark.asyncio
    async def test_rate_limiter_validation(self):
        """Test rate limiter validates inputs."""
        limiter = AsyncTokenBucket(rate=10.0, capacity=10)

        # Should reject invalid token counts
        with pytest.raises(ValueError):
            await limiter.acquire(tokens=0)

        with pytest.raises(ValueError):
            await limiter.acquire(tokens=20)  # Exceeds capacity

    @pytest.mark.asyncio
    async def test_rate_limiter_timeout(self):
        """Test rate limiter timeout."""
        limiter = AsyncTokenBucket(rate=1.0, capacity=1)

        # Consume the token
        await limiter.acquire(tokens=1)

        # Try to acquire with short timeout (need 1 second, give 0.1)
        acquired = await limiter.acquire(tokens=1, timeout=0.1)
        assert acquired is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
