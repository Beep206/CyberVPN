from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.outbox_consumer_receipt_model import OutboxConsumerReceiptModel


class OutboxConsumerReceiptRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_receipt(
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

    async def create_receipt(
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
