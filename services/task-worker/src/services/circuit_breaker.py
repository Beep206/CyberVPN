"""Circuit breaker pattern implementation for resilient external service calls.

A circuit breaker prevents cascading failures by temporarily blocking calls to a failing service,
allowing it time to recover. The circuit has three states:

- CLOSED: Normal operation, requests pass through
- OPEN: Service is failing, requests are immediately rejected
- HALF_OPEN: Testing if service has recovered, limited requests allowed

State transitions:
1. CLOSED -> OPEN: After reaching failure_threshold consecutive failures
2. OPEN -> HALF_OPEN: After recovery_timeout seconds have passed
3. HALF_OPEN -> CLOSED: After half_open_max_calls successful requests
4. HALF_OPEN -> OPEN: If any request fails during half-open state

This implementation is async-safe and uses asyncio.Lock for thread safety.
"""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, TypeVar

import structlog

logger = structlog.get_logger(__name__)

T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation, requests pass through
    OPEN = "open"  # Failing, reject all calls immediately
    HALF_OPEN = "half_open"  # Testing recovery, allow limited calls


class CircuitBreakerError(Exception):
    """Raised when circuit breaker rejects a call because circuit is open."""

    def __init__(self, circuit_name: str, message: str = "Circuit breaker is open") -> None:
        """Initialize circuit breaker error.

        Args:
            circuit_name: Name of the circuit breaker that rejected the call
            message: Error message describing why the call was rejected
        """
        self.circuit_name = circuit_name
        super().__init__(f"[{circuit_name}] {message}")


@dataclass
class CircuitBreaker:
    """Async circuit breaker for protecting calls to external services.

    Attributes:
        name: Identifier for this circuit breaker (used in logs and errors)
        failure_threshold: Number of consecutive failures before opening circuit
        recovery_timeout: Seconds to wait before attempting recovery (OPEN -> HALF_OPEN)
        half_open_max_calls: Number of successful calls needed to close circuit from HALF_OPEN

    Example:
        >>> breaker = CircuitBreaker(name="payment_api", failure_threshold=3, recovery_timeout=30.0)
        >>> try:
        ...     result = await breaker.call(payment_api.charge, user_id=123, amount=50.0)
        ... except CircuitBreakerError:
        ...     logger.warning("payment_api_unavailable")
        ...     # Handle fallback logic
    """

    name: str
    failure_threshold: int = 5
    recovery_timeout: float = 60.0  # seconds
    half_open_max_calls: int = 1

    # Internal state - do not modify directly
    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _failure_count: int = field(default=0, init=False)
    _success_count: int = field(default=0, init=False)
    _last_failure_time: float = field(default=0.0, init=False)
    _half_open_calls: int = field(default=0, init=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False)

    def __post_init__(self) -> None:
        """Initialize circuit breaker and log creation."""
        logger.info(
            "circuit_breaker_initialized",
            name=self.name,
            failure_threshold=self.failure_threshold,
            recovery_timeout=self.recovery_timeout,
            half_open_max_calls=self.half_open_max_calls,
        )

    async def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute a function through the circuit breaker.

        Args:
            func: Async function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            Result of the function call

        Raises:
            CircuitBreakerError: If circuit is open and not ready for recovery
            Exception: Any exception raised by the wrapped function

        Example:
            >>> result = await breaker.call(api_client.get_user, user_id=123)
        """
        async with self._lock:
            current_state = self._state

            # Check if we should transition from OPEN to HALF_OPEN
            if current_state == CircuitState.OPEN:
                if time.monotonic() - self._last_failure_time >= self.recovery_timeout:
                    self._transition_to_half_open()
                    current_state = CircuitState.HALF_OPEN
                else:
                    # Circuit is still open, reject the call
                    logger.warning(
                        "circuit_breaker_rejected_call",
                        name=self.name,
                        state="open",
                        time_until_retry=round(
                            self.recovery_timeout - (time.monotonic() - self._last_failure_time), 2
                        ),
                    )
                    raise CircuitBreakerError(
                        self.name,
                        f"Circuit breaker is open. Retry in {round(self.recovery_timeout - (time.monotonic() - self._last_failure_time), 1)}s",
                    )

            # Check half-open call limit
            if current_state == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self.half_open_max_calls:
                    logger.warning(
                        "circuit_breaker_rejected_call",
                        name=self.name,
                        state="half_open",
                        reason="max_half_open_calls_reached",
                    )
                    raise CircuitBreakerError(self.name, "Circuit is half-open but max test calls reached")
                self._half_open_calls += 1

        # Execute the function outside the lock to avoid blocking other calls
        try:
            result = await func(*args, **kwargs)
            await self._record_success()
            return result

        except Exception as exc:
            await self._record_failure(exc)
            raise

    async def _record_success(self) -> None:
        """Record a successful call and update circuit state accordingly."""
        async with self._lock:
            self._success_count += 1

            if self._state == CircuitState.HALF_OPEN:
                # Check if we've had enough successful calls to close the circuit
                if self._success_count >= self.half_open_max_calls:
                    self._transition_to_closed()
                else:
                    logger.info(
                        "circuit_breaker_half_open_success",
                        name=self.name,
                        success_count=self._success_count,
                        needed=self.half_open_max_calls,
                    )
            elif self._state == CircuitState.CLOSED:
                # Reset failure count on success
                self._failure_count = 0

    async def _record_failure(self, exception: Exception) -> None:
        """Record a failed call and update circuit state accordingly.

        Args:
            exception: The exception that caused the failure
        """
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.monotonic()

            logger.warning(
                "circuit_breaker_call_failed",
                name=self.name,
                state=self._state.value,
                failure_count=self._failure_count,
                exception_type=type(exception).__name__,
                exception_message=str(exception),
            )

            # Transition to OPEN if we've hit the failure threshold
            if self._state == CircuitState.CLOSED:
                if self._failure_count >= self.failure_threshold:
                    self._transition_to_open()

            # Any failure in HALF_OPEN immediately opens the circuit
            elif self._state == CircuitState.HALF_OPEN:
                self._transition_to_open()

    def _transition_to_open(self) -> None:
        """Transition circuit to OPEN state."""
        self._state = CircuitState.OPEN
        self._last_failure_time = time.monotonic()

        logger.error(
            "circuit_breaker_opened",
            name=self.name,
            failure_count=self._failure_count,
            recovery_timeout=self.recovery_timeout,
        )

    def _transition_to_half_open(self) -> None:
        """Transition circuit to HALF_OPEN state for recovery testing."""
        self._state = CircuitState.HALF_OPEN
        self._half_open_calls = 0
        self._success_count = 0

        logger.info(
            "circuit_breaker_half_open",
            name=self.name,
            message="Testing if service has recovered",
        )

    def _transition_to_closed(self) -> None:
        """Transition circuit to CLOSED state (normal operation)."""
        previous_state = self._state
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0

        logger.info(
            "circuit_breaker_closed",
            name=self.name,
            previous_state=previous_state.value,
            message="Circuit recovered, normal operation resumed",
        )

    @property
    def state(self) -> CircuitState:
        """Get current circuit state.

        Returns:
            Current state of the circuit breaker

        Example:
            >>> if breaker.state == CircuitState.OPEN:
            ...     logger.warning("service_unavailable")
        """
        return self._state

    @property
    def failure_count(self) -> int:
        """Get current failure count.

        Returns:
            Number of consecutive failures in current state
        """
        return self._failure_count

    @property
    def is_available(self) -> bool:
        """Check if circuit is available for calls.

        Returns:
            True if circuit is CLOSED or ready to test in HALF_OPEN, False otherwise
        """
        if self._state == CircuitState.CLOSED:
            return True
        if self._state == CircuitState.HALF_OPEN:
            return self._half_open_calls < self.half_open_max_calls
        if self._state == CircuitState.OPEN:
            return time.monotonic() - self._last_failure_time >= self.recovery_timeout
        return False

    def reset(self) -> None:
        """Manually reset circuit breaker to CLOSED state.

        Use this for testing or manual intervention. In production, prefer
        letting the circuit breaker recover naturally.
        """
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0

        logger.info("circuit_breaker_manually_reset", name=self.name)
