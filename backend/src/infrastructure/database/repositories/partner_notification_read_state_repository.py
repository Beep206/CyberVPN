"""Repository for partner notification read and archive state."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.partner_notification_read_state_model import (
    PartnerNotificationReadStateModel,
)


class PartnerNotificationReadStateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_workspace_and_actor(
        self,
        *,
        partner_account_id: UUID,
        admin_user_id: UUID,
    ) -> list[PartnerNotificationReadStateModel]:
        result = await self._session.execute(
            select(PartnerNotificationReadStateModel)
            .where(
                PartnerNotificationReadStateModel.partner_account_id == partner_account_id,
                PartnerNotificationReadStateModel.admin_user_id == admin_user_id,
            )
            .order_by(PartnerNotificationReadStateModel.updated_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_workspace_actor_and_key(
        self,
        *,
        partner_account_id: UUID,
        admin_user_id: UUID,
        notification_key: str,
    ) -> PartnerNotificationReadStateModel | None:
        result = await self._session.execute(
            select(PartnerNotificationReadStateModel).where(
                PartnerNotificationReadStateModel.partner_account_id == partner_account_id,
                PartnerNotificationReadStateModel.admin_user_id == admin_user_id,
                PartnerNotificationReadStateModel.notification_key == notification_key,
            )
        )
        return result.scalar_one_or_none()

    async def upsert_read_state(
        self,
        *,
        partner_account_id: UUID,
        admin_user_id: UUID,
        notification_key: str,
        read_at: datetime | None = None,
        archived_at: datetime | None = None,
    ) -> PartnerNotificationReadStateModel:
        model = await self.get_by_workspace_actor_and_key(
            partner_account_id=partner_account_id,
            admin_user_id=admin_user_id,
            notification_key=notification_key,
        )
        if model is None:
            model = PartnerNotificationReadStateModel(
                partner_account_id=partner_account_id,
                admin_user_id=admin_user_id,
                notification_key=notification_key,
            )
            self._session.add(model)

        if read_at is not None:
            model.read_at = read_at
        if archived_at is not None:
            model.archived_at = archived_at

        await self._session.flush()
        return model
