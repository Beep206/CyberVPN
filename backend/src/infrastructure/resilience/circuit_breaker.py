import time
from enum import Enum
from functools import wraps
from typing import Any, Callable


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open"""

    pass


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for handling cascading failures
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type[BaseException] = Exception,
    ):
        """
        Initialize circuit breaker

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: Exception type to count as failure
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection

        Args:
            func: Function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function

        Returns:
            Function result if successful

        Raises:
            CircuitBreakerError: If circuit is open
            Original exception: If function fails and circuit moves to open
        """
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
            else:
                raise CircuitBreakerError("Circuit breaker is OPEN")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e

    def _on_success(self):
        """Handle successful function execution"""
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    def _on_failure(self):
        """Handle failed function execution"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery"""
        if self.last_failure_time is None:
            return True
        return (time.time() - self.last_failure_time) >= self.recovery_timeout

    def reset(self):
        """Manually reset circuit breaker to closed state"""
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED


def circuit_breaker(
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    expected_exception: type[BaseException] = Exception,
):
    """
    Decorator for applying circuit breaker to functions

    Args:
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Seconds to wait before attempting recovery
        expected_exception: Exception type to count as failure
    """
    breaker = CircuitBreaker(failure_threshold, recovery_timeout, expected_exception)

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return breaker.call(func, *args, **kwargs)

        return wrapper

    return decorator
