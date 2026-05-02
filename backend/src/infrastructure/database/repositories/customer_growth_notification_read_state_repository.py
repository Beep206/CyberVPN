"""Repository for customer growth notification read/archive state."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.customer_growth_notification_read_state_model import (
    CustomerGrowthNotificationReadStateModel,
)


class CustomerGrowthNotificationReadStateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_user(
        self,
        *,
        mobile_user_id: UUID,
    ) -> list[CustomerGrowthNotificationReadStateModel]:
        result = await self._session.execute(
            select(CustomerGrowthNotificationReadStateModel)
            .where(CustomerGrowthNotificationReadStateModel.mobile_user_id == mobile_user_id)
            .order_by(CustomerGrowthNotificationReadStateModel.updated_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_user_and_key(
        self,
        *,
        mobile_user_id: UUID,
        notification_key: str,
    ) -> CustomerGrowthNotificationReadStateModel | None:
        result = await self._session.execute(
            select(CustomerGrowthNotificationReadStateModel).where(
                CustomerGrowthNotificationReadStateModel.mobile_user_id == mobile_user_id,
                CustomerGrowthNotificationReadStateModel.notification_key == notification_key,
            )
        )
        return result.scalar_one_or_none()

    async def upsert_read_state(
        self,
        *,
        mobile_user_id: UUID,
        notification_key: str,
        read_at: datetime | None = None,
        archived_at: datetime | None = None,
    ) -> CustomerGrowthNotificationReadStateModel:
        model = await self.get_by_user_and_key(
            mobile_user_id=mobile_user_id,
            notification_key=notification_key,
        )
        if model is None:
            model = CustomerGrowthNotificationReadStateModel(
                mobile_user_id=mobile_user_id,
                notification_key=notification_key,
            )
            self._session.add(model)

        if read_at is not None:
            model.read_at = read_at
        if archived_at is not None:
            model.archived_at = archived_at

        await self._session.flush()
        return model
