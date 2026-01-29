from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.webhook_log_model import WebhookLog


class WebhookLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_paginated(self, offset: int = 0, limit: int = 50) -> list[WebhookLog]:
        result = await self._session.execute(
            select(WebhookLog).order_by(WebhookLog.created_at.desc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all())

    async def count(self) -> int:
        result = await self._session.execute(select(func.count()).select_from(WebhookLog))
        return result.scalar_one()

    async def get_by_source(self, source: str, offset: int = 0, limit: int = 50) -> list[WebhookLog]:
        result = await self._session.execute(
            select(WebhookLog)
            .where(WebhookLog.source == source)
            .order_by(WebhookLog.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())
