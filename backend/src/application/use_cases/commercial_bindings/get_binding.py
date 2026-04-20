from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.repositories.customer_commercial_binding_repo import (
    CustomerCommercialBindingRepository,
)


class GetCustomerCommercialBindingUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._bindings = CustomerCommercialBindingRepository(session)

    async def execute(self, *, binding_id: UUID):
        return await self._bindings.get_by_id(binding_id)
