from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.offer_model import OfferModel
from src.infrastructure.database.repositories.offer_repo import OfferRepository


class ListOffersUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = OfferRepository(session)

    async def execute(
        self,
        *,
        at: datetime | None = None,
        sale_channel: str | None = None,
        subscription_plan_id: UUID | None = None,
        include_inactive: bool = False,
    ) -> list[OfferModel]:
        return await self._repo.list_active(
            at=at,
            sale_channel=sale_channel,
            subscription_plan_id=subscription_plan_id,
            include_inactive=include_inactive,
        )
