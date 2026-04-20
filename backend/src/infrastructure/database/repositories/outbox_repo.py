from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.enums import OutboxEventStatus, OutboxPublicationStatus
from src.infrastructure.database.models.outbox_event_model import OutboxEventModel, OutboxPublicationModel


class OutboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_event(
        self,
        model: OutboxEventModel,
        publications: list[OutboxPublicationModel],
    ) -> OutboxEventModel:
        self._session.add(model)
        self._session.add_all(publications)
        await self._session.flush()
        return model

    async def get_event_by_id(self, event_id: UUID) -> OutboxEventModel | None:
        result = await self._session.execute(
            select(OutboxEventModel)
            .execution_options(populate_existing=True)
            .options(selectinload(OutboxEventModel.publications))
            .where(OutboxEventModel.id == event_id)
        )
        return result.scalars().first()

    async def list_events(
        self,
        *,
        event_family: str | None = None,
        event_name: str | None = None,
        event_status: str | None = None,
        aggregate_type: str | None = None,
        aggregate_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[OutboxEventModel]:
        query = select(OutboxEventModel).execution_options(populate_existing=True).options(
            selectinload(OutboxEventModel.publications)
        )
        if event_family is not None:
            query = query.where(OutboxEventModel.event_family == event_family)
        if event_name is not None:
            query = query.where(OutboxEventModel.event_name == event_name)
        if event_status is not None:
            query = query.where(OutboxEventModel.event_status == event_status)
        if aggregate_type is not None:
            query = query.where(OutboxEventModel.aggregate_type == aggregate_type)
        if aggregate_id is not None:
            query = query.where(OutboxEventModel.aggregate_id == aggregate_id)
        query = (
            query.order_by(
                OutboxEventModel.occurred_at.desc(),
                OutboxEventModel.created_at.desc(),
            )
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(query)
        return list(result.scalars().unique().all())

    async def get_publication_by_id(self, publication_id: UUID) -> OutboxPublicationModel | None:
        result = await self._session.execute(
            select(OutboxPublicationModel)
            .execution_options(populate_existing=True)
            .options(selectinload(OutboxPublicationModel.outbox_event))
            .where(OutboxPublicationModel.id == publication_id)
        )
        return result.scalars().first()

    async def list_publications(
        self,
        *,
        consumer_key: str | None = None,
        publication_status: str | None = None,
        outbox_event_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[OutboxPublicationModel]:
        query = (
            select(OutboxPublicationModel)
            .execution_options(populate_existing=True)
            .options(selectinload(OutboxPublicationModel.outbox_event))
        )
        if consumer_key is not None:
            query = query.where(OutboxPublicationModel.consumer_key == consumer_key)
        if publication_status is not None:
            query = query.where(OutboxPublicationModel.publication_status == publication_status)
        if outbox_event_id is not None:
            query = query.where(OutboxPublicationModel.outbox_event_id == outbox_event_id)
        query = query.order_by(OutboxPublicationModel.next_attempt_at.asc(), OutboxPublicationModel.created_at.asc())
        query = query.offset(offset).limit(limit)
        result = await self._session.execute(query)
        return list(result.scalars().unique().all())

    async def claim_publications(
        self,
        *,
        consumer_key: str,
        batch_size: int,
        lease_owner: str,
        leased_until: datetime,
        now: datetime | None = None,
    ) -> list[OutboxPublicationModel]:
        now = now or datetime.now(UTC)
        result = await self._session.execute(
            select(OutboxPublicationModel)
            .execution_options(populate_existing=True)
            .options(selectinload(OutboxPublicationModel.outbox_event))
            .where(
                OutboxPublicationModel.consumer_key == consumer_key,
                OutboxPublicationModel.next_attempt_at <= now,
                or_(
                    OutboxPublicationModel.publication_status == OutboxPublicationStatus.PENDING.value,
                    OutboxPublicationModel.publication_status == OutboxPublicationStatus.FAILED.value,
                ),
                or_(
                    OutboxPublicationModel.leased_until.is_(None),
                    OutboxPublicationModel.leased_until <= now,
                ),
            )
            .order_by(OutboxPublicationModel.next_attempt_at.asc(), OutboxPublicationModel.created_at.asc())
            .limit(batch_size)
        )
        items = list(result.scalars().unique().all())
        for item in items:
            item.publication_status = OutboxPublicationStatus.CLAIMED.value
            item.lease_owner = lease_owner
            item.leased_until = leased_until
            item.attempts = int(item.attempts or 0) + 1
        await self._session.flush()
        for item in items:
            await self.refresh_event_status(item.outbox_event_id)
        return items

    async def mark_publication_submitted(
        self,
        *,
        publication: OutboxPublicationModel,
        lease_owner: str,
        submitted_at: datetime,
    ) -> OutboxPublicationModel:
        _ensure_lease_owner(publication=publication, lease_owner=lease_owner)
        publication.publication_status = OutboxPublicationStatus.SUBMITTED.value
        publication.submitted_at = submitted_at
        publication.last_error = None
        await self._session.flush()
        await self.refresh_event_status(publication.outbox_event_id)
        return publication

    async def mark_publication_published(
        self,
        *,
        publication: OutboxPublicationModel,
        lease_owner: str,
        published_at: datetime,
        publication_payload: dict | None,
    ) -> OutboxPublicationModel:
        _ensure_lease_owner(publication=publication, lease_owner=lease_owner)
        publication.publication_status = OutboxPublicationStatus.PUBLISHED.value
        publication.published_at = published_at
        publication.leased_until = None
        publication.lease_owner = None
        publication.last_error = None
        if publication_payload is not None:
            publication.publication_payload = dict(publication_payload)
        await self._session.flush()
        await self.refresh_event_status(publication.outbox_event_id)
        return publication

    async def mark_publication_failed(
        self,
        *,
        publication: OutboxPublicationModel,
        lease_owner: str,
        failed_at: datetime,
        retry_at: datetime,
        error_message: str,
    ) -> OutboxPublicationModel:
        _ensure_lease_owner(publication=publication, lease_owner=lease_owner)
        publication.publication_status = OutboxPublicationStatus.FAILED.value
        publication.leased_until = None
        publication.lease_owner = None
        publication.next_attempt_at = retry_at
        publication.last_error = error_message.strip()
        publication.submitted_at = publication.submitted_at or failed_at
        await self._session.flush()
        await self.refresh_event_status(publication.outbox_event_id)
        return publication

    async def refresh_event_status(self, outbox_event_id: UUID) -> OutboxEventModel | None:
        event = await self.get_event_by_id(outbox_event_id)
        if event is None:
            return None

        publication_statuses = {item.publication_status for item in event.publications}
        if publication_statuses and publication_statuses == {OutboxPublicationStatus.PUBLISHED.value}:
            event.event_status = OutboxEventStatus.PUBLISHED.value
        elif publication_statuses.intersection(
            {
                OutboxPublicationStatus.CLAIMED.value,
                OutboxPublicationStatus.SUBMITTED.value,
                OutboxPublicationStatus.PUBLISHED.value,
            }
        ):
            event.event_status = OutboxEventStatus.PARTIALLY_PUBLISHED.value
        elif publication_statuses == {OutboxPublicationStatus.FAILED.value}:
            event.event_status = OutboxEventStatus.FAILED.value
        else:
            event.event_status = OutboxEventStatus.PENDING_PUBLICATION.value

        await self._session.flush()
        return event


def _ensure_lease_owner(*, publication: OutboxPublicationModel, lease_owner: str) -> None:
    if publication.lease_owner != lease_owner:
        raise ValueError("Publication is not leased by the requested owner")
    leased_until = _normalize_utc(publication.leased_until)
    if leased_until is not None and leased_until < datetime.now(UTC):
        raise ValueError("Publication lease has expired")


def _normalize_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
