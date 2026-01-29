"""SQLAlchemy async session management for task-worker microservice.

Provides database connectivity with lazy engine initialization:
- DeclarativeBase for ORM models (independent from backend)
- Async engine with connection pooling (created on first use)
- Session factory and context manager
- Database health check functionality
"""

from collections.abc import AsyncGenerator
from functools import lru_cache

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from src.config import get_settings


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for task-worker ORM models.

    Independent from the backend's Base — the worker maintains its own ORM
    layer that reads the same PostgreSQL tables created by backend Alembic migrations.
    """


@lru_cache
def get_engine() -> AsyncEngine:
    """Create and cache the async database engine.

    Lazy initialization ensures the engine is only created when first needed,
    not at module import time. Uses connection pooling for production performance.
    """
    settings = get_settings()
    return create_async_engine(
        settings.database_url,
        echo=False,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=3600,
    )


@lru_cache
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Create and cache the async session factory."""
    return async_sessionmaker(
        get_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Async generator for database sessions with automatic lifecycle management.

    Yields an AsyncSession that commits on success or rolls back on exception.
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def check_db_connection() -> bool:
    """Check database connectivity by executing SELECT 1.

    Returns True if database is accessible, False otherwise.
    """
    try:
        async with get_engine().begin() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
