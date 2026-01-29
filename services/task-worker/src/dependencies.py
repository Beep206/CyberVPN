"""TaskIQ dependency injection providers.

Provides typed dependencies for database sessions, HTTP clients, and Redis clients
using TaskIQ's Context-based dependency injection pattern.

Usage in task functions:
    from src.dependencies import DbSession, HttpClient

    @broker.task
    async def my_task(db: DbSession, http: HttpClient):
        # db and http are automatically injected by TaskIQ
        ...
"""

from collections.abc import AsyncGenerator
from typing import Annotated

import httpx
import redis.asyncio as redis_async
from sqlalchemy.ext.asyncio import AsyncSession
from taskiq import Context, TaskiqDepends

from src.config import get_settings


async def get_db_session(
    context: Annotated[Context, TaskiqDepends()],
) -> AsyncGenerator[AsyncSession, None]:
    """Yield an async SQLAlchemy session from the broker's session factory.

    The broker stores the session factory during WORKER_STARTUP event in src/broker.py.
    This dependency retrieves it from context.state and yields a session with
    proper lifecycle management (commit on success, rollback on error).

    Args:
        context: TaskIQ context containing broker state

    Yields:
        AsyncSession: Database session with automatic lifecycle management
    """
    session_factory = context.state.db_session_factory
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_http_client(context: Annotated[Context, TaskiqDepends()]) -> httpx.AsyncClient:
    """Return the shared httpx client from broker state.

    The broker creates and stores a shared httpx.AsyncClient during WORKER_STARTUP
    event in src/broker.py. This dependency retrieves it for use in tasks.

    Args:
        context: TaskIQ context containing broker state

    Returns:
        httpx.AsyncClient: Shared HTTP client instance
    """
    return context.state.http_client


async def get_redis_client(
    context: Annotated[Context, TaskiqDepends()],
) -> AsyncGenerator[redis_async.Redis, None]:
    """Yield a Redis client connection.

    Creates a new Redis client connection from settings for each task invocation.
    The connection is automatically closed after use.

    Args:
        context: TaskIQ context (unused, but required for dependency injection)

    Yields:
        redis_async.Redis: Redis client connection
    """
    settings = get_settings()
    client = redis_async.from_url(settings.redis_url, decode_responses=True)
    try:
        yield client
    finally:
        await client.aclose()


async def get_settings_dependency(
    context: Annotated[Context, TaskiqDepends()],
) -> get_settings:
    """Return the cached settings instance.

    Provides access to application configuration in task functions.

    Args:
        context: TaskIQ context (unused, but required for dependency injection)

    Returns:
        Settings: Application settings instance
    """
    return get_settings()


# Type aliases for convenient dependency injection in task signatures
DbSession = Annotated[AsyncSession, TaskiqDepends(get_db_session)]
HttpClient = Annotated[httpx.AsyncClient, TaskiqDepends(get_http_client)]
RedisClient = Annotated[redis_async.Redis, TaskiqDepends(get_redis_client)]
Settings = Annotated[get_settings, TaskiqDepends(get_settings_dependency)]
