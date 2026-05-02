from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.posthog_bridge import PostHogBridgeInput, build_posthog_capture_record
from src.application.services.posthog_delivery import PostHogDeliveryService
from src.config.settings import settings
from src.infrastructure.database.models.outbox_event_model import OutboxPublicationModel
from src.infrastructure.database.models.partner_workspace_feed_event_model import PartnerWorkspaceFeedEventModel
from src.infrastructure.database.repositories.outbox_repo import OutboxRepository
from src.infrastructure.database.repositories.partner_event_runtime_repo import PartnerEventRuntimeRepository
from src.infrastructure.database.session import AsyncSessionLocal
from src.infrastructure.messaging.partner_workspace_feed_broker import (
    PartnerWorkspaceFeedBroadcast,
    partner_workspace_feed_broker,
)

logger = logging.getLogger("cybervpn")

SUPPORTED_CONSUMERS = ("analytics_mart", "operational_replay")


@dataclass(frozen=True)
class OutboxEnvelope:
    consumer_key: str
    event_key: str
    event_name: str
    event_family: str
    aggregate_type: str
    aggregate_id: str
    schema_version: int
    subject: str
    occurred_at: datetime
    actor_context: dict[str, Any]
    source_context: dict[str, Any]
    event_payload: dict[str, Any]

    def as_payload(self) -> dict[str, Any]:
        return {
            "event_id": self.event_key,
            "event_type": self.event_name,
            "event_version": self.schema_version,
            "subject": self.subject,
            "source": "cybervpn-backend",
            "consumer_key": self.consumer_key,
            "occurred_at": self.occurred_at.isoformat(),
            "published_at": datetime.now(UTC).isoformat(),
            "environment": settings.environment,
            "aggregate_type": self.aggregate_type,
            "aggregate_id": self.aggregate_id,
            "correlation_id": self.event_key,
            "idempotency_key": f"{self.consumer_key}:{self.event_key}",
            "pii_classification": "low",
            "schema_ref": f"events/{self.event_name.replace('.', '/')}/v{self.schema_version}.json",
            "actor_context": dict(self.actor_context),
            "source_context": dict(self.source_context),
            "payload": dict(self.event_payload),
        }


class NatsPartnerRuntime:
    def __init__(self) -> None:
        self._connection: Any | None = None
        self._jetstream: Any | None = None
        self._stop_event = asyncio.Event()
        self._tasks: list[asyncio.Task[None]] = []
        self._posthog = PostHogDeliveryService()

    async def start(self) -> None:
        if self._tasks:
            return
        if not settings.partner_event_backbone_enabled:
            logger.info("Partner event backbone disabled; runtime will not connect to NATS")
            return

        await self._ensure_connection()
        await self._ensure_stream()
        self._stop_event.clear()
        self._tasks = [
            asyncio.create_task(self._dispatch_loop(), name="partner-outbox-dispatcher"),
            *[
                asyncio.create_task(self._consume_loop(consumer_key), name=f"partner-consumer-{consumer_key}")
                for consumer_key in SUPPORTED_CONSUMERS
            ],
        ]
        logger.info("Partner event backbone runtime started", consumers=list(SUPPORTED_CONSUMERS))

    async def stop(self) -> None:
        self._stop_event.set()
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks = []
        if self._connection is not None:
            await self._connection.drain()
            self._connection = None
            self._jetstream = None

    async def _ensure_connection(self) -> None:
        if self._connection is not None:
            return
        import nats

        self._connection = await nats.connect(settings.nats_url, name="cybervpn-backend")
        self._jetstream = self._connection.jetstream()

    async def _ensure_stream(self) -> None:
        try:
            await self._jetstream.stream_info(settings.nats_partner_stream_name)
        except Exception:
            await self._jetstream.add_stream(
                name=settings.nats_partner_stream_name,
                subjects=[f"{settings.nats_partner_subject_prefix}.>"],
            )

    async def _dispatch_loop(self) -> None:
        lease_owner = f"dispatcher-{uuid4().hex}"
        while not self._stop_event.is_set():
            try:
                for consumer_key in SUPPORTED_CONSUMERS:
                    await self._dispatch_pending_publications(consumer_key=consumer_key, lease_owner=lease_owner)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Partner outbox dispatcher iteration failed")
            await asyncio.sleep(settings.outbox_dispatch_interval_seconds)

    async def _dispatch_pending_publications(self, *, consumer_key: str, lease_owner: str) -> None:
        now = datetime.now(UTC)
        async with AsyncSessionLocal() as session:
            repo = OutboxRepository(session)
            claimed = await repo.claim_publications(
                consumer_key=consumer_key,
                batch_size=settings.outbox_dispatch_batch_size,
                lease_owner=lease_owner,
                leased_until=now.replace(microsecond=0) + timedelta(seconds=settings.outbox_dispatch_lease_seconds),
                now=now,
            )
            envelopes = [
                (
                    publication.id,
                    self._build_envelope(publication=publication),
                )
                for publication in claimed
            ]
            await session.commit()

        for publication_id, envelope in envelopes:
            try:
                ack = await self._publish_envelope(envelope)
                async with AsyncSessionLocal() as session:
                    repo = OutboxRepository(session)
                    publication = await repo.get_publication_by_id(publication_id)
                    if publication is None:
                        continue
                    await repo.mark_publication_submitted(
                        publication=publication,
                        lease_owner=lease_owner,
                        submitted_at=datetime.now(UTC),
                    )
                    await repo.mark_publication_published(
                        publication=publication,
                        lease_owner=lease_owner,
                        published_at=datetime.now(UTC),
                        publication_payload=ack,
                    )
                    await session.commit()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                async with AsyncSessionLocal() as session:
                    repo = OutboxRepository(session)
                    publication = await repo.get_publication_by_id(publication_id)
                    if publication is not None:
                        await repo.mark_publication_failed(
                            publication=publication,
                            lease_owner=lease_owner,
                            failed_at=datetime.now(UTC),
                            retry_at=datetime.now(UTC).replace(microsecond=0)
                            + timedelta(seconds=settings.outbox_dispatch_retry_after_seconds),
                            error_message=str(exc),
                        )
                        await session.commit()
                logger.exception("Partner outbox publication failed", extra={"consumer_key": consumer_key})

    async def _publish_envelope(self, envelope: OutboxEnvelope) -> dict[str, Any]:
        payload = json.dumps(envelope.as_payload(), separators=(",", ":"), default=str).encode("utf-8")
        ack = await self._jetstream.publish(envelope.subject, payload)
        return {
            "status": "published",
            "stream": getattr(ack, "stream", settings.nats_partner_stream_name),
            "sequence": getattr(ack, "seq", None),
            "subject": envelope.subject,
            "consumer_key": envelope.consumer_key,
        }

    async def _consume_loop(self, consumer_key: str) -> None:
        await self._ensure_connection()
        subject = f"{settings.nats_partner_subject_prefix}.{consumer_key}.>"
        subscription = await self._jetstream.pull_subscribe(
            subject,
            durable=f"{consumer_key}-durable",
            stream=settings.nats_partner_stream_name,
        )
        while not self._stop_event.is_set():
            try:
                messages = await subscription.fetch(
                    settings.nats_consumer_fetch_batch_size,
                    timeout=settings.nats_consumer_fetch_timeout_seconds,
                )
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                raise
            for message in messages:
                try:
                    await self._process_message(consumer_key=consumer_key, raw_message=message)
                    await message.ack()
                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.exception("Partner event consumer failed", extra={"consumer_key": consumer_key})
        await subscription.unsubscribe()

    async def _process_message(self, *, consumer_key: str, raw_message: Any) -> None:
        payload = json.loads(raw_message.data.decode("utf-8"))
        event_key = str(payload["event_id"])
        event_name = str(payload["event_type"])
        subject = str(payload["subject"])

        async with AsyncSessionLocal() as session:
            repo = PartnerEventRuntimeRepository(session)
            existing = await repo.get_consumer_receipt(consumer_key=consumer_key, event_key=event_key)
            if existing is not None:
                await session.commit()
                return

            if consumer_key == "analytics_mart":
                await self._handle_analytics_mart(payload=payload, repo=repo)
            elif consumer_key == "operational_replay":
                await self._handle_operational_replay(payload=payload, repo=repo)

            await repo.create_consumer_receipt(
                consumer_key=consumer_key,
                event_key=event_key,
                event_name=event_name,
                subject=subject,
                metadata_payload={"status": "processed"},
            )
            await session.commit()

    async def _handle_analytics_mart(
        self,
        *,
        payload: dict[str, Any],
        repo: PartnerEventRuntimeRepository,
    ) -> None:
        record = build_posthog_capture_record(
            PostHogBridgeInput(
                event_key=str(payload["event_id"]),
                event_name=str(payload["event_type"]),
                aggregate_id=str(payload["aggregate_id"]),
                occurred_at=_parse_datetime(str(payload["occurred_at"])),
                schema_version=int(payload["event_version"]),
                actor_context=dict(payload.get("actor_context") or {}),
                event_payload=dict(payload.get("payload") or {}),
            )
        )
        if record is None:
            return
        result = await self._posthog.deliver(record)
        # Keep a processed receipt even when PostHog is disabled, but expose transport state for audits.
        await repo.create_consumer_receipt(
            consumer_key="analytics_mart.transport",
            event_key=str(payload["event_id"]),
            event_name=record.event,
            subject=str(payload["subject"]),
            metadata_payload=result,
        )

    async def _handle_operational_replay(
        self,
        *,
        payload: dict[str, Any],
        repo: PartnerEventRuntimeRepository,
    ) -> None:
        workspace_id = _extract_workspace_id(payload)
        if workspace_id is None:
            return
        event_key = str(payload["event_id"])
        existing = await repo.get_feed_event_by_key(event_key=event_key)
        if existing is not None:
            return

        model = PartnerWorkspaceFeedEventModel(
            workspace_id=workspace_id,
            event_key=event_key,
            event_name=str(payload["event_type"]),
            event_family=str(payload["event_type"]).split(".", 1)[0],
            aggregate_type=str(payload["aggregate_type"]),
            aggregate_id=str(payload["aggregate_id"]),
            consumer_key="operational_replay",
            subject=str(payload["subject"]),
            payload=dict(payload.get("payload") or {}),
            occurred_at=_parse_datetime(str(payload["occurred_at"])),
        )
        created = await repo.create_feed_event(model)
        await partner_workspace_feed_broker.publish(
            PartnerWorkspaceFeedBroadcast(
                workspace_id=created.workspace_id,
                event_key=created.event_key,
                event_name=created.event_name,
                aggregate_type=created.aggregate_type,
                aggregate_id=created.aggregate_id,
                subject=created.subject,
                payload=dict(created.payload or {}),
                occurred_at=created.occurred_at,
            )
        )

    def _build_envelope(self, *, publication: OutboxPublicationModel) -> OutboxEnvelope:
        event = publication.outbox_event
        subject = _build_subject(
            consumer_key=publication.consumer_key,
            event_name=event.event_name,
            schema_version=event.schema_version,
        )
        return OutboxEnvelope(
            consumer_key=publication.consumer_key,
            event_key=event.event_key,
            event_name=event.event_name,
            event_family=event.event_family,
            aggregate_type=event.aggregate_type,
            aggregate_id=event.aggregate_id,
            schema_version=event.schema_version,
            subject=subject,
            occurred_at=_normalize_utc(event.occurred_at),
            actor_context=dict(event.actor_context or {}),
            source_context=dict(event.source_context or {}),
            event_payload=dict(event.event_payload or {}),
        )


def _build_subject(*, consumer_key: str, event_name: str, schema_version: int) -> str:
    return f"{settings.nats_partner_subject_prefix}.{consumer_key}.{event_name}.v{schema_version}"


def _extract_workspace_id(payload: dict[str, Any]) -> UUID | None:
    candidates = (
        payload.get("payload", {}).get("partner_account_id"),
        payload.get("payload", {}).get("workspace_id"),
        payload.get("source_context", {}).get("partner_account_id"),
        payload.get("source_context", {}).get("workspace_id"),
    )
    for candidate in candidates:
        if not candidate:
            continue
        try:
            return UUID(str(candidate))
        except (TypeError, ValueError):
            continue
    return None


def _normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _parse_datetime(value: str) -> datetime:
    return _normalize_utc(datetime.fromisoformat(value.replace("Z", "+00:00")))
