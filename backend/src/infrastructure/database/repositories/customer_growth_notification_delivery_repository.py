"""Repository for customer growth notification delivery state and history."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.growth_notifications.catalog import normalize_growth_notification_key
from src.infrastructure.database.models.customer_growth_notification_delivery_event_model import (
    CustomerGrowthNotificationDeliveryEventModel,
)
from src.infrastructure.database.models.customer_growth_notification_delivery_model import (
    CustomerGrowthNotificationDeliveryModel,
)


class CustomerGrowthNotificationDeliveryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_user_key_channel(
        self,
        *,
        mobile_user_id: UUID,
        notification_key: str,
        delivery_channel: str,
    ) -> CustomerGrowthNotificationDeliveryModel | None:
        result = await self._session.execute(
            select(CustomerGrowthNotificationDeliveryModel).where(
                CustomerGrowthNotificationDeliveryModel.mobile_user_id == mobile_user_id,
                CustomerGrowthNotificationDeliveryModel.notification_key
                == normalize_growth_notification_key(notification_key),
                CustomerGrowthNotificationDeliveryModel.delivery_channel == delivery_channel,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id(
        self,
        delivery_id: UUID,
    ) -> CustomerGrowthNotificationDeliveryModel | None:
        result = await self._session.execute(
            select(CustomerGrowthNotificationDeliveryModel).where(
                CustomerGrowthNotificationDeliveryModel.id == delivery_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_user_notification_key(
        self,
        *,
        mobile_user_id: UUID,
        notification_key: str,
    ) -> list[CustomerGrowthNotificationDeliveryModel]:
        result = await self._session.execute(
            select(CustomerGrowthNotificationDeliveryModel)
            .where(
                CustomerGrowthNotificationDeliveryModel.mobile_user_id == mobile_user_id,
                CustomerGrowthNotificationDeliveryModel.notification_key
                == normalize_growth_notification_key(notification_key),
            )
            .order_by(
                CustomerGrowthNotificationDeliveryModel.planned_at.desc(),
                CustomerGrowthNotificationDeliveryModel.created_at.desc(),
            )
        )
        return list(result.scalars().all())

    async def get_by_queue_id(
        self,
        notification_queue_id: UUID,
    ) -> CustomerGrowthNotificationDeliveryModel | None:
        result = await self._session.execute(
            select(CustomerGrowthNotificationDeliveryModel).where(
                CustomerGrowthNotificationDeliveryModel.notification_queue_id == notification_queue_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_deliveries(
        self,
        *,
        mobile_user_id: UUID | None = None,
        delivery_channel: str | None = None,
        delivery_status: str | None = None,
        source_kind: str | None = None,
        limit: int = 25,
        offset: int = 0,
    ) -> list[CustomerGrowthNotificationDeliveryModel]:
        stmt = select(CustomerGrowthNotificationDeliveryModel).order_by(
            CustomerGrowthNotificationDeliveryModel.planned_at.desc(),
            CustomerGrowthNotificationDeliveryModel.created_at.desc(),
        )
        if mobile_user_id is not None:
            stmt = stmt.where(CustomerGrowthNotificationDeliveryModel.mobile_user_id == mobile_user_id)
        if delivery_channel:
            stmt = stmt.where(CustomerGrowthNotificationDeliveryModel.delivery_channel == delivery_channel)
        if delivery_status:
            stmt = stmt.where(CustomerGrowthNotificationDeliveryModel.delivery_status == delivery_status)
        if source_kind:
            stmt = stmt.where(CustomerGrowthNotificationDeliveryModel.source_kind == source_kind)

        result = await self._session.execute(stmt.offset(offset).limit(limit))
        return list(result.scalars().all())

    async def count_deliveries(
        self,
        *,
        mobile_user_id: UUID | None = None,
        delivery_channel: str | None = None,
        delivery_status: str | None = None,
        source_kind: str | None = None,
    ) -> int:
        stmt = select(func.count()).select_from(CustomerGrowthNotificationDeliveryModel)
        if mobile_user_id is not None:
            stmt = stmt.where(CustomerGrowthNotificationDeliveryModel.mobile_user_id == mobile_user_id)
        if delivery_channel:
            stmt = stmt.where(CustomerGrowthNotificationDeliveryModel.delivery_channel == delivery_channel)
        if delivery_status:
            stmt = stmt.where(CustomerGrowthNotificationDeliveryModel.delivery_status == delivery_status)
        if source_kind:
            stmt = stmt.where(CustomerGrowthNotificationDeliveryModel.source_kind == source_kind)

        result = await self._session.execute(stmt)
        return int(result.scalar_one() or 0)

    async def upsert_delivery(
        self,
        *,
        mobile_user_id: UUID,
        notification_key: str,
        notification_kind: str,
        delivery_channel: str,
        delivery_status: str,
        title: str,
        message: str,
        delivery_payload: dict,
        source_kind: str | None = None,
        source_id: str | None = None,
        status_reason: str | None = None,
        notification_queue_id: UUID | None = None,
        created_by_admin_user_id: UUID | None = None,
        planned_at: datetime | None = None,
        delivered_at: datetime | None = None,
    ) -> CustomerGrowthNotificationDeliveryModel:
        model = await self.get_by_user_key_channel(
            mobile_user_id=mobile_user_id,
            notification_key=notification_key,
            delivery_channel=delivery_channel,
        )
        if model is None:
            model = CustomerGrowthNotificationDeliveryModel(
                mobile_user_id=mobile_user_id,
                notification_key=normalize_growth_notification_key(notification_key),
                notification_kind=notification_kind,
                delivery_channel=delivery_channel,
                delivery_status=delivery_status,
                title=title,
                message=message,
                delivery_payload=dict(delivery_payload),
                source_kind=source_kind,
                source_id=source_id,
                status_reason=status_reason,
                notification_queue_id=notification_queue_id,
                created_by_admin_user_id=created_by_admin_user_id,
            )
            if planned_at is not None:
                model.planned_at = planned_at
            if delivered_at is not None:
                model.delivered_at = delivered_at
            self._session.add(model)
            await self._session.flush()
            return model

        model.notification_kind = notification_kind
        model.delivery_status = delivery_status
        model.title = title
        model.message = message
        model.delivery_payload = dict(delivery_payload)
        model.source_kind = source_kind
        model.source_id = source_id
        model.status_reason = status_reason
        if notification_queue_id is not None:
            model.notification_queue_id = notification_queue_id
        if created_by_admin_user_id is not None:
            model.created_by_admin_user_id = created_by_admin_user_id
        if planned_at is not None:
            model.planned_at = planned_at
        if delivered_at is not None:
            model.delivered_at = delivered_at

        await self._session.flush()
        return model

    async def create_event(
        self,
        *,
        delivery: CustomerGrowthNotificationDeliveryModel,
        event_type: str,
        reason_code: str | None = None,
        event_payload: dict | None = None,
        event_note: str | None = None,
        notification_queue_id: UUID | None = None,
        created_by_admin_user_id: UUID | None = None,
        occurred_at: datetime | None = None,
    ) -> CustomerGrowthNotificationDeliveryEventModel:
        model = CustomerGrowthNotificationDeliveryEventModel(
            delivery_id=delivery.id,
            event_type=event_type,
            delivery_status=delivery.delivery_status,
            reason_code=reason_code if reason_code is not None else delivery.status_reason,
            event_payload=dict(event_payload or {}),
            event_note=event_note,
            notification_queue_id=(
                notification_queue_id
                if notification_queue_id is not None
                else delivery.notification_queue_id
            ),
            created_by_admin_user_id=(
                created_by_admin_user_id
                if created_by_admin_user_id is not None
                else delivery.created_by_admin_user_id
            ),
            occurred_at=occurred_at or datetime.now(UTC),
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return model

    async def list_events_for_delivery(
        self,
        *,
        delivery_id: UUID,
        limit: int = 200,
    ) -> list[CustomerGrowthNotificationDeliveryEventModel]:
        result = await self._session.execute(
            select(CustomerGrowthNotificationDeliveryEventModel)
            .where(CustomerGrowthNotificationDeliveryEventModel.delivery_id == delivery_id)
            .order_by(
                CustomerGrowthNotificationDeliveryEventModel.occurred_at.desc(),
                CustomerGrowthNotificationDeliveryEventModel.created_at.desc(),
            )
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_events_for_delivery_ids(
        self,
        delivery_ids: list[UUID],
    ) -> list[CustomerGrowthNotificationDeliveryEventModel]:
        if not delivery_ids:
            return []
        result = await self._session.execute(
            select(CustomerGrowthNotificationDeliveryEventModel)
            .where(CustomerGrowthNotificationDeliveryEventModel.delivery_id.in_(delivery_ids))
            .order_by(
                CustomerGrowthNotificationDeliveryEventModel.occurred_at.desc(),
                CustomerGrowthNotificationDeliveryEventModel.created_at.desc(),
            )
        )
        return list(result.scalars().all())
