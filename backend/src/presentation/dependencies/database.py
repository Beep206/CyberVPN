from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.di.container import container


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    factory = container.get("db")
    async for session in factory():
        yield session
