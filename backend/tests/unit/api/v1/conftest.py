"""Shared fixtures for API v1 unit tests.

These tests run without external services (Redis, PostgreSQL).
The rate-limit middleware is switched to *fail-open* mode so that
the absence of Redis does not cause 503 responses.  The circuit
breaker is also reset before each test to prevent cross-test
interference.
"""

import pytest

from src.config.settings import settings
from src.presentation.middleware.rate_limit import RateLimitMiddleware


@pytest.fixture(autouse=True, scope="session")
def _rate_limit_fail_open():
    """Allow requests through when Redis is unavailable (unit tests).

    Patches both the settings object and any already-constructed
    RateLimitMiddleware instances in the ASGI middleware stack, since
    the middleware reads ``fail_open`` from settings only at construction
    time and stores it on the instance.
    """
    original = settings.rate_limit_fail_open
    # Use object.__setattr__ because pydantic-settings may freeze the model
    object.__setattr__(settings, "rate_limit_fail_open", True)

    # Patch the already-constructed middleware instance(s)
    from src.main import app

    current = getattr(app, "middleware_stack", None)
    while current is not None:
        if isinstance(current, RateLimitMiddleware):
            current.fail_open = True
        current = getattr(current, "app", None)

    yield
    object.__setattr__(settings, "rate_limit_fail_open", original)


@pytest.fixture(autouse=True)
def _reset_circuit_breaker():
    """Reset the shared circuit breaker before each test.

    Without this, a circuit opened by one test (due to Redis being
    unreachable) would carry over and immediately reject requests in
    subsequent tests.
    """
    cb = RateLimitMiddleware._circuit_breaker
    if cb is not None:
        cb._failure_count = 0
        cb._state = cb.CLOSED
    yield
