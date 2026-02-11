"""Pytest configuration and fixtures for testing."""

import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Set ENABLE_METRICS before importing main.py to ensure metrics endpoint is registered
os.environ["ENABLE_METRICS"] = "true"

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
        "ENABLE_METRICS": "true",  # Enable Prometheus metrics for observability tests
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
async def async_client(test_settings) -> AsyncGenerator[AsyncClient]:
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


@pytest_asyncio.fixture
async def db() -> AsyncGenerator:
    """
    Create a test database session.

    Creates tables, yields session, then rolls back and cleans up.
    """
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
    from src.infrastructure.database.session import Base

    # Use test database from environment (set by test_settings fixture)
    test_db_url = os.environ.get("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/cybervpn_test")

    # Create test engine
    engine = create_async_engine(
        test_db_url,
        echo=False,
        pool_pre_ping=True,
    )

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session
        await session.rollback()

    # Drop tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()
