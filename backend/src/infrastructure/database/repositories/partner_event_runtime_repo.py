from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.outbox_consumer_receipt_model import OutboxConsumerReceiptModel
from src.infrastructure.database.models.partner_workspace_feed_event_model import PartnerWorkspaceFeedEventModel


class PartnerEventRuntimeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_consumer_receipt(
        self,
        *,
        consumer_key: str,
        event_key: str,
    ) -> OutboxConsumerReceiptModel | None:
        result = await self._session.execute(
            select(OutboxConsumerReceiptModel).where(
                OutboxConsumerReceiptModel.consumer_key == consumer_key,
                OutboxConsumerReceiptModel.event_key == event_key,
            )
        )
        return result.scalar_one_or_none()

    async def create_consumer_receipt(
        self,
        *,
        consumer_key: str,
        event_key: str,
        event_name: str,
        subject: str,
        metadata_payload: dict[str, object] | None = None,
        status: str = "processed",
    ) -> OutboxConsumerReceiptModel:
        model = OutboxConsumerReceiptModel(
            consumer_key=consumer_key,
            event_key=event_key,
            event_name=event_name,
            subject=subject,
            status=status,
            metadata_payload=dict(metadata_payload or {}),
            processed_at=datetime.now(UTC),
        )
        self._session.add(model)
        await self._session.flush()
        return model

    async def get_feed_event_by_key(self, *, event_key: str) -> PartnerWorkspaceFeedEventModel | None:
        result = await self._session.execute(
            select(PartnerWorkspaceFeedEventModel).where(PartnerWorkspaceFeedEventModel.event_key == event_key)
        )
        return result.scalar_one_or_none()

    async def create_feed_event(
        self,
        model: PartnerWorkspaceFeedEventModel,
    ) -> PartnerWorkspaceFeedEventModel:
        self._session.add(model)
        await self._session.flush()
        return model

    async def list_feed_events(
        self,
        *,
        workspace_id: UUID,
        after_event_key: str | None = None,
        limit: int = 100,
    ) -> list[PartnerWorkspaceFeedEventModel]:
        query = select(PartnerWorkspaceFeedEventModel).where(
            PartnerWorkspaceFeedEventModel.workspace_id == workspace_id
        )
        if after_event_key:
            anchor = await self.get_feed_event_by_key(event_key=after_event_key)
            if anchor is not None and anchor.workspace_id == workspace_id:
                query = query.where(PartnerWorkspaceFeedEventModel.created_at > anchor.created_at)
        query = query.order_by(PartnerWorkspaceFeedEventModel.created_at.asc()).limit(limit)
        result = await self._session.execute(query)
        return list(result.scalars().all())
