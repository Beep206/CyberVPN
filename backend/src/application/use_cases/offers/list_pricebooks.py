from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.pricebook_model import PricebookModel
from src.infrastructure.database.repositories.pricebook_repo import PricebookRepository


class ListPricebooksUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = PricebookRepository(session)

    async def execute(
        self,
        *,
        storefront_id: UUID | None = None,
        storefront_key: str | None = None,
        at: datetime | None = None,
        currency_code: str | None = None,
        region_code: str | None = None,
        include_inactive: bool = False,
    ) -> list[PricebookModel]:
        return await self._repo.list_active(
            storefront_id=storefront_id,
            storefront_key=storefront_key,
            at=at,
            currency_code=currency_code,
            region_code=region_code,
            include_inactive=include_inactive,
        )
