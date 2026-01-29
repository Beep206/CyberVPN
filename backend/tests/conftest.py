"""Pytest configuration and fixtures for testing."""

import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.fixture(scope="session")
def test_settings():
    """Set up test environment variables."""
    # Store original values
    original_env = {}

    # Test environment variables
    test_env = {
        "ENVIRONMENT": "test",
        "DATABASE_URL": "postgresql+asyncpg://test:test@localhost:5432/cybervpn_test",
        "REDIS_URL": "redis://localhost:6379/1",
        "SECRET_KEY": "test-secret-key-for-testing-only",
        "CORS_ORIGINS": "http://localhost:3000",
        "DEBUG": "true",
    }

    # Set test environment variables
    for key, value in test_env.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value

    yield test_env

    # Restore original environment variables
    for key, original_value in original_env.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value


@pytest_asyncio.fixture
async def async_client(test_settings) -> AsyncGenerator[AsyncClient, None]:
    """
    Create an async HTTP client for testing the FastAPI application.

    Yields:
        AsyncClient: HTTPX async client with ASGI transport
    """
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client
