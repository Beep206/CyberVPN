import logging
from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from src.config.settings import settings
from src.infrastructure.monitoring.instrumentation import instrument_database

logger = logging.getLogger("cybervpn")

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
)

instrument_database(engine)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db_session() -> AsyncGenerator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise e


async def check_db_connection() -> bool:
    for attempt in range(2):
        try:
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except RuntimeError as exc:
            if attempt == 0 and "loop" in str(exc).lower():
                logger.warning(
                    "Database pool loop mismatch detected during health check, disposing engine and retrying"
                )
                await engine.dispose()
                continue
            return False
        except Exception as exc:
            if attempt == 0 and "loop" in str(exc).lower():
                logger.warning(
                    "Database health check encountered loop-bound connection state, disposing engine and retrying"
                )
                await engine.dispose()
                continue
            _ = exc  # Expected when database is unreachable
            return False

    return False
