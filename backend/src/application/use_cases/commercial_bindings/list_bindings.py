from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.repositories.customer_commercial_binding_repo import (
    CustomerCommercialBindingRepository,
)


class ListCustomerCommercialBindingsUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._bindings = CustomerCommercialBindingRepository(session)

    async def execute(
        self,
        *,
        user_id: UUID | None = None,
        storefront_id: UUID | None = None,
        binding_type: str | None = None,
        binding_status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ):
        return await self._bindings.list(
            user_id=user_id,
            storefront_id=storefront_id,
            binding_type=binding_type,
            binding_status=binding_status,
            limit=limit,
            offset=offset,
        )
