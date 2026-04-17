"""Pytest configuration and fixtures for testing."""

import asyncio
import importlib.util
import os
import secrets
import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, text

from src.config.settings import settings

# Set ENABLE_METRICS before importing main.py to ensure metrics endpoint is registered
os.environ["ENABLE_METRICS"] = "true"

from src.main import app


def pytest_ignore_collect(collection_path, path=None, config=None) -> bool:  # noqa: ARG001
    """Skip Locust scenarios from normal pytest collection when Locust is absent."""
    if collection_path.name not in {"test_auth_load.py", "test_helix_load.py"}:
        return False

    return collection_path.parent.name == "load" and importlib.util.find_spec("locust") is None


@pytest.fixture(scope="session")
def test_settings():
    """Set up test environment variables."""
    # Store original values
    original_env = {}

    # Test environment variables
    test_env = {
        "ENVIRONMENT": "test",
        # Reuse the local Docker stack so integration tests hit the same
        # services as the application instead of an absent ad-hoc test DB.
        "DATABASE_URL": settings.database_url,
        "REDIS_URL": settings.redis_url,
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


@pytest.fixture(scope="session", autouse=True)
def ensure_repo_schema(test_settings) -> None:
    """Create repo-managed tables missing from the legacy Docker database.

    The local Docker stack ships an older Remnawave schema. Our backend adds
    extra auth/admin tables on top, so integration tests need a one-time
    metadata sync to make sure those tables exist before the suite runs.
    """
    if os.environ.get("SKIP_TEST_DB_BOOTSTRAP") == "1":
        return

    from sqlalchemy.ext.asyncio import create_async_engine

    from src.infrastructure.database.session import Base
    import src.infrastructure.database.models  # noqa: F401

    schema_engine = create_async_engine(
        os.environ.get("DATABASE_URL", settings.database_url),
        echo=False,
        pool_pre_ping=True,
    )

    async def _sync_schema() -> None:
        try:
            async with schema_engine.begin() as conn:
                existing_tables = set(
                    (
                        await conn.execute(
                            text(
                                "select tablename from pg_tables where schemaname = 'public'"
                            )
                        )
                    )
                    .scalars()
                    .all()
                )

                missing_tables = [
                    Base.metadata.tables[name]
                    for name in sorted(Base.metadata.tables)
                    if name not in existing_tables
                ]

                for table in missing_tables:
                    await conn.run_sync(lambda sync_conn, table=table: table.create(sync_conn, checkfirst=True))

                admin_users_exists = "admin_users" in existing_tables
                if admin_users_exists:
                    totp_secret_length = await conn.scalar(
                        text(
                            """
                            select character_maximum_length
                            from information_schema.columns
                            where table_schema = 'public'
                              and table_name = 'admin_users'
                              and column_name = 'totp_secret'
                            """
                        )
                    )
                    if totp_secret_length is not None and int(totp_secret_length) < 255:
                        await conn.execute(
                            text("alter table admin_users alter column totp_secret type varchar(255)")
                        )
        finally:
            await schema_engine.dispose()

    asyncio.run(_sync_schema())


@pytest_asyncio.fixture(autouse=True)
async def cleanup_global_async_pools() -> AsyncGenerator[None]:
    """Dispose shared pools between tests to avoid cross-loop leftovers."""
    yield

    from src.infrastructure.cache.redis_client import close_redis_pool
    from src.infrastructure.helix.client import helix_adapter_client
    from src.infrastructure.payments.cryptobot.client import cryptobot_client
    from src.infrastructure.remnawave.client import remnawave_client
    from src.infrastructure.database.session import engine

    await remnawave_client.close()
    await helix_adapter_client.close()
    await cryptobot_client.close()
    await close_redis_pool()
    await engine.dispose()


@pytest_asyncio.fixture
async def db() -> AsyncGenerator:
    """
    Create a test database session.

    Creates tables, yields session, then rolls back and cleans up.
    """
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    # Use the Docker-backed database configured for the local stack.
    test_db_url = os.environ.get("DATABASE_URL", settings.database_url)

    # Create test engine
    engine = create_async_engine(
        test_db_url,
        echo=False,
        pool_pre_ping=True,
    )

    # Create session
    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session
        await session.rollback()

    await engine.dispose()


@pytest_asyncio.fixture
async def auth_tokens() -> AsyncGenerator[dict[str, str]]:
    """Create a live super-admin token for integration/e2e tests that need auth."""

    from src.application.services.auth_service import AuthService
    from src.infrastructure.database.models import AdminUserModel
    from src.infrastructure.database.session import AsyncSessionLocal

    auth_service = AuthService()
    user_id = uuid.uuid4()
    login_suffix = secrets.token_hex(4)
    password_hash = await auth_service.hash_password("FixtureAdminPassword123!")

    async with AsyncSessionLocal() as session:
        user = AdminUserModel(
            id=user_id,
            login=f"pytest-admin-{login_suffix}",
            email=f"pytest-admin-{login_suffix}@example.com",
            password_hash=password_hash,
            role="super_admin",
            is_active=True,
            is_email_verified=True,
            language="en-EN",
            timezone="UTC",
        )
        session.add(user)
        await session.commit()

    access_token = auth_service.create_access_token_simple(
        subject=str(user_id),
        role="super_admin",
    )

    try:
        yield {"access_token": access_token}
    finally:
        async with AsyncSessionLocal() as session:
            await session.execute(delete(AdminUserModel).where(AdminUserModel.id == user_id))
            await session.commit()


@pytest.fixture
def auth_headers(auth_tokens: dict[str, str]) -> dict[str, str]:
    """Authorization headers for tests that need an authenticated admin request."""

    return {"Authorization": f"Bearer {auth_tokens['access_token']}"}
