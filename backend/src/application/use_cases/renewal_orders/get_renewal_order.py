from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.repositories.renewal_order_repo import RenewalOrderRepository


class GetRenewalOrderUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = RenewalOrderRepository(session)

    async def execute(
        self,
        *,
        renewal_order_id: UUID | None = None,
        order_id: UUID | None = None,
    ):
        if renewal_order_id is not None:
            return await self._repo.get_by_id(renewal_order_id)
        if order_id is not None:
            return await self._repo.get_by_order_id(order_id)
        raise ValueError("Either renewal_order_id or order_id must be provided")
