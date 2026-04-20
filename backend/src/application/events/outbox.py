from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import OutboxEventStatus, OutboxPublicationStatus
from src.infrastructure.database.models.outbox_event_model import OutboxEventModel, OutboxPublicationModel
from src.infrastructure.database.repositories.outbox_repo import OutboxRepository

from .partner_platform_events import PARTNER_PLATFORM_EVENT_FAMILIES

DEFAULT_OUTBOX_CONSUMERS = ("analytics_mart", "operational_replay")
PARTNER_PLATFORM_EVENT_NAMES = frozenset(
    event_name for family_events in PARTNER_PLATFORM_EVENT_FAMILIES.values() for event_name in family_events
)


@dataclass(frozen=True)
class OutboxActorContext:
    principal_type: str | None = None
    principal_id: str | None = None
    auth_realm_id: str | None = None


class EventOutboxService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = OutboxRepository(session)

    async def append_event(
        self,
        *,
        event_name: str,
        aggregate_type: str,
        aggregate_id: str,
        partition_key: str | None = None,
        event_payload: dict[str, Any] | None = None,
        actor_context: OutboxActorContext | None = None,
        source_context: dict[str, Any] | None = None,
        consumer_keys: tuple[str, ...] | None = None,
        occurred_at: datetime | None = None,
        schema_version: int = 1,
    ) -> OutboxEventModel:
        normalized_name = event_name.strip()
        if normalized_name not in PARTNER_PLATFORM_EVENT_NAMES:
            raise ValueError(f"Unknown canonical partner-platform event: {normalized_name}")
        event_family = normalized_name.split(".", 1)[0]
        normalized_partition_key = partition_key or aggregate_id
        normalized_consumers = consumer_keys or DEFAULT_OUTBOX_CONSUMERS
        occurred_at = _normalize_utc(occurred_at or datetime.now(UTC))
        now = datetime.now(UTC)
        event = OutboxEventModel(
            id=uuid.uuid4(),
            event_key=f"evt_{uuid.uuid4().hex}",
            event_name=normalized_name,
            event_family=event_family,
            aggregate_type=aggregate_type.strip(),
            aggregate_id=aggregate_id.strip(),
            partition_key=normalized_partition_key.strip(),
            schema_version=schema_version,
            event_status=OutboxEventStatus.PENDING_PUBLICATION.value,
            event_payload=dict(event_payload or {}),
            actor_context=_serialize_actor_context(actor_context),
            source_context=dict(source_context or {}),
            occurred_at=occurred_at,
        )
        publications = [
            OutboxPublicationModel(
                id=uuid.uuid4(),
                outbox_event_id=event.id,
                consumer_key=consumer_key,
                publication_status=OutboxPublicationStatus.PENDING.value,
                attempts=0,
                next_attempt_at=now,
                publication_payload={},
            )
            for consumer_key in normalized_consumers
        ]
        return await self._repo.create_event(event, publications)


def _serialize_actor_context(actor_context: OutboxActorContext | None) -> dict[str, Any]:
    if actor_context is None:
        return {}
    payload: dict[str, Any] = {}
    if actor_context.principal_type is not None:
        payload["principal_type"] = actor_context.principal_type
    if actor_context.principal_id is not None:
        payload["principal_id"] = actor_context.principal_id
    if actor_context.auth_realm_id is not None:
        payload["auth_realm_id"] = actor_context.auth_realm_id
    return payload


def _normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
