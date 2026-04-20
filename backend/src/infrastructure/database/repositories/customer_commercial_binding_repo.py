from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import CustomerCommercialBindingStatus
from src.infrastructure.database.models.customer_commercial_binding_model import (
    CustomerCommercialBindingModel,
)


class CustomerCommercialBindingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, model: CustomerCommercialBindingModel) -> CustomerCommercialBindingModel:
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return model

    async def get_by_id(self, binding_id: UUID) -> CustomerCommercialBindingModel | None:
        return await self._session.get(CustomerCommercialBindingModel, binding_id)

    async def list(
        self,
        *,
        user_id: UUID | None = None,
        storefront_id: UUID | None = None,
        binding_type: str | None = None,
        binding_status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[CustomerCommercialBindingModel]:
        stmt = select(CustomerCommercialBindingModel).order_by(
            CustomerCommercialBindingModel.effective_from.desc(),
            CustomerCommercialBindingModel.created_at.desc(),
        )
        if user_id is not None:
            stmt = stmt.where(CustomerCommercialBindingModel.user_id == user_id)
        if storefront_id is not None:
            stmt = stmt.where(CustomerCommercialBindingModel.storefront_id == storefront_id)
        if binding_type is not None:
            stmt = stmt.where(CustomerCommercialBindingModel.binding_type == binding_type)
        if binding_status is not None:
            stmt = stmt.where(CustomerCommercialBindingModel.binding_status == binding_status)
        result = await self._session.execute(stmt.offset(offset).limit(limit))
        return list(result.scalars().all())

    async def find_active_for_scope(
        self,
        *,
        user_id: UUID,
        binding_type: str,
        storefront_id: UUID | None,
    ) -> CustomerCommercialBindingModel | None:
        stmt = (
            select(CustomerCommercialBindingModel)
            .where(
                CustomerCommercialBindingModel.user_id == user_id,
                CustomerCommercialBindingModel.binding_type == binding_type,
                CustomerCommercialBindingModel.binding_status == CustomerCommercialBindingStatus.ACTIVE.value,
            )
            .order_by(
                CustomerCommercialBindingModel.effective_from.desc(),
                CustomerCommercialBindingModel.created_at.desc(),
            )
        )
        if storefront_id is None:
            stmt = stmt.where(CustomerCommercialBindingModel.storefront_id.is_(None))
        else:
            stmt = stmt.where(CustomerCommercialBindingModel.storefront_id == storefront_id)
        result = await self._session.execute(stmt)
        return result.scalars().first()

    async def supersede(
        self,
        model: CustomerCommercialBindingModel,
        *,
        effective_to: datetime,
    ) -> CustomerCommercialBindingModel:
        normalized_effective_to = (
            effective_to.replace(tzinfo=UTC) if effective_to.tzinfo is None else effective_to.astimezone(UTC)
        )
        model.binding_status = CustomerCommercialBindingStatus.SUPERSEDED.value
        model.effective_to = normalized_effective_to
        model.updated_at = datetime.now(UTC)
        await self._session.flush()
        return model

    async def list_active_for_user(
        self,
        *,
        user_id: UUID,
        storefront_id: UUID | None,
    ) -> list[CustomerCommercialBindingModel]:
        stmt = (
            select(CustomerCommercialBindingModel)
            .where(
                CustomerCommercialBindingModel.user_id == user_id,
                CustomerCommercialBindingModel.binding_status == CustomerCommercialBindingStatus.ACTIVE.value,
            )
            .order_by(
                CustomerCommercialBindingModel.effective_from.desc(),
                CustomerCommercialBindingModel.created_at.desc(),
            )
        )
        if storefront_id is None:
            stmt = stmt.where(CustomerCommercialBindingModel.storefront_id.is_(None))
        else:
            stmt = stmt.where(
                or_(
                    CustomerCommercialBindingModel.storefront_id == storefront_id,
                    CustomerCommercialBindingModel.storefront_id.is_(None),
                )
            )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
