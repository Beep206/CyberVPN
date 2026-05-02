from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from src.config import Settings
from src.infra.database.models import Base

_ENGINE_CACHE: dict[tuple[str, bool], AsyncEngine] = {}
_SESSION_CACHE: dict[tuple[str, bool], async_sessionmaker[AsyncSession]] = {}


def _cache_key(settings: Settings) -> tuple[str, bool]:
    return (settings.database_url, settings.database_echo)


def get_engine(settings: Settings) -> AsyncEngine:
    key = _cache_key(settings)
    if key not in _ENGINE_CACHE:
        _ENGINE_CACHE[key] = create_async_engine(
            settings.database_url,
            echo=settings.database_echo,
            pool_pre_ping=True,
        )
    return _ENGINE_CACHE[key]


def get_session_factory(settings: Settings) -> async_sessionmaker[AsyncSession]:
    key = _cache_key(settings)
    if key not in _SESSION_CACHE:
        _SESSION_CACHE[key] = async_sessionmaker(
            get_engine(settings),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _SESSION_CACHE[key]


async def initialize_database(settings: Settings) -> None:
    engine = get_engine(settings)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def dispose_database(settings: Settings) -> None:
    key = _cache_key(settings)
    engine = _ENGINE_CACHE.pop(key, None)
    _SESSION_CACHE.pop(key, None)
    if engine is not None:
        await engine.dispose()


async def get_db_session(settings: Settings) -> AsyncGenerator[AsyncSession, None]:
    session_factory = get_session_factory(settings)
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

