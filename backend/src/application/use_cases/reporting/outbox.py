from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.outbox_event_model import OutboxEventModel, OutboxPublicationModel
from src.infrastructure.database.repositories.outbox_repo import OutboxRepository
from src.infrastructure.monitoring.instrumentation.partner_runtime import (
    log_partner_runtime_event,
    observe_partner_outbox_event_published,
    observe_partner_outbox_publish_failure,
)


class ListOutboxEventsUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = OutboxRepository(session)

    async def execute(
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
        return await self._repo.list_events(
            event_family=event_family,
            event_name=event_name,
            event_status=event_status,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            limit=limit,
            offset=offset,
        )


class GetOutboxEventUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = OutboxRepository(session)

    async def execute(self, *, outbox_event_id: UUID) -> OutboxEventModel | None:
        return await self._repo.get_event_by_id(outbox_event_id)


class ListOutboxPublicationsUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = OutboxRepository(session)

    async def execute(
        self,
        *,
        consumer_key: str | None = None,
        publication_status: str | None = None,
        outbox_event_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[OutboxPublicationModel]:
        return await self._repo.list_publications(
            consumer_key=consumer_key,
            publication_status=publication_status,
            outbox_event_id=outbox_event_id,
            limit=limit,
            offset=offset,
        )


@dataclass(frozen=True)
class ClaimOutboxPublicationsResult:
    claimed_publications: list[OutboxPublicationModel]


class ClaimOutboxPublicationsUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = OutboxRepository(session)

    async def execute(
        self,
        *,
        consumer_key: str,
        lease_owner: str,
        batch_size: int,
        lease_seconds: int,
    ) -> ClaimOutboxPublicationsResult:
        now = datetime.now(UTC)
        leased_until = now + timedelta(seconds=lease_seconds)
        items = await self._repo.claim_publications(
            consumer_key=consumer_key,
            batch_size=batch_size,
            lease_owner=lease_owner,
            leased_until=leased_until,
            now=now,
        )
        return ClaimOutboxPublicationsResult(claimed_publications=items)


class MarkOutboxPublicationSubmittedUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = OutboxRepository(session)

    async def execute(
        self,
        *,
        publication_id: UUID,
        lease_owner: str,
    ) -> OutboxPublicationModel:
        publication = await self._repo.get_publication_by_id(publication_id)
        if publication is None:
            raise ValueError("Outbox publication not found")
        return await self._repo.mark_publication_submitted(
            publication=publication,
            lease_owner=lease_owner,
            submitted_at=datetime.now(UTC),
        )


class MarkOutboxPublicationPublishedUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = OutboxRepository(session)

    async def execute(
        self,
        *,
        publication_id: UUID,
        lease_owner: str,
        publication_payload: dict | None,
    ) -> OutboxPublicationModel:
        publication = await self._repo.get_publication_by_id(publication_id)
        if publication is None:
            raise ValueError("Outbox publication not found")
        outbox_event = await self._repo.get_event_by_id(publication.outbox_event_id)
        if outbox_event is None:
            raise ValueError("Outbox event not found")
        item = await self._repo.mark_publication_published(
            publication=publication,
            lease_owner=lease_owner,
            published_at=datetime.now(UTC),
            publication_payload=publication_payload,
        )
        lag_seconds = max(
            (_normalize_utc(item.published_at) - _normalize_utc(outbox_event.occurred_at)).total_seconds(),
            0.0,
        )
        observe_partner_outbox_event_published(
            event_type=outbox_event.event_name,
            consumer_name=publication.consumer_key,
            result="success",
            lag_seconds=lag_seconds,
        )
        log_partner_runtime_event(
            "partner_outbox.publication_published",
            surface="partner_backend",
            route_group="outbox",
            event_type=outbox_event.event_name,
            consumer_name=publication.consumer_key,
            publication_id=str(publication.id),
            result="success",
        )
        return item


class MarkOutboxPublicationFailedUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = OutboxRepository(session)

    async def execute(
        self,
        *,
        publication_id: UUID,
        lease_owner: str,
        retry_after_seconds: int,
        error_message: str,
    ) -> OutboxPublicationModel:
        publication = await self._repo.get_publication_by_id(publication_id)
        if publication is None:
            raise ValueError("Outbox publication not found")
        outbox_event = await self._repo.get_event_by_id(publication.outbox_event_id)
        if outbox_event is None:
            raise ValueError("Outbox event not found")
        now = datetime.now(UTC)
        item = await self._repo.mark_publication_failed(
            publication=publication,
            lease_owner=lease_owner,
            failed_at=now,
            retry_at=now + timedelta(seconds=retry_after_seconds),
            error_message=error_message,
        )
        lag_seconds = max(
            (_normalize_utc(now) - _normalize_utc(outbox_event.occurred_at)).total_seconds(),
            0.0,
        )
        observe_partner_outbox_publish_failure(
            event_type=outbox_event.event_name,
            consumer_name=publication.consumer_key,
            result="failure",
            lag_seconds=lag_seconds,
        )
        log_partner_runtime_event(
            "partner_outbox.publication_failed",
            surface="partner_backend",
            route_group="outbox",
            event_type=outbox_event.event_name,
            consumer_name=publication.consumer_key,
            publication_id=str(publication.id),
            error_code="publication_failed",
            result="failure",
        )
        return item


def _normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
