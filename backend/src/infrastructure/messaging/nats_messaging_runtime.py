from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from nats.errors import TimeoutError as NatsTimeoutError

from src.config.settings import settings
from src.domain.events.messaging import BROADCAST_OUTBOX_CONSUMERS, MESSAGING_OUTBOX_CONSUMERS
from src.infrastructure.database.models.outbox_event_model import OutboxPublicationModel
from src.infrastructure.database.repositories.outbox_consumer_receipt_repo import OutboxConsumerReceiptRepository
from src.infrastructure.database.repositories.outbox_repo import OutboxRepository
from src.infrastructure.database.session import AsyncSessionLocal
from src.infrastructure.messaging.sse_manager import sse_manager
from src.infrastructure.messaging.websocket_manager import ws_manager
from src.infrastructure.monitoring.metrics import (
    messaging_outbox_events_published_total,
    messaging_outbox_lag_seconds,
    messaging_outbox_publish_failures_total,
    messaging_realtime_dispatch_total,
)

logger = logging.getLogger("cybervpn")

SUPPORTED_MESSAGING_CONSUMERS = tuple(dict.fromkeys((*MESSAGING_OUTBOX_CONSUMERS, *BROADCAST_OUTBOX_CONSUMERS)))


@dataclass(frozen=True)
class MessagingOutboxEnvelope:
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
            "pii_classification": "restricted",
            "schema_ref": f"events/{self.event_name.replace('.', '/')}/v{self.schema_version}.json",
            "actor_context": dict(self.actor_context),
            "source_context": dict(self.source_context),
            "payload": dict(self.event_payload),
        }


class MessagingRealtimeDispatcher:
    async def dispatch(self, payload: dict[str, Any]) -> int:
        event_type = str(payload["event_type"])
        payload_body = dict(payload.get("payload") or {})
        recipient_refs = _recipient_refs(payload_body)
        dispatch_count = 0
        for recipient in recipient_refs:
            channel = f"messaging:{recipient['type']}:{recipient['id']}"
            message = _realtime_payload(payload, recipient=recipient)
            await ws_manager.broadcast(channel, message)
            await sse_manager.broadcast_event(channel, event_type, message)
            messaging_realtime_dispatch_total.labels(
                event_type=event_type,
                channel_type=recipient["type"],
                result="success",
            ).inc()
            dispatch_count += 1
        return dispatch_count


class NatsMessagingRuntime:
    def __init__(self, realtime_dispatcher: MessagingRealtimeDispatcher | None = None) -> None:
        self._connection: Any | None = None
        self._jetstream: Any | None = None
        self._stop_event = asyncio.Event()
        self._tasks: list[asyncio.Task[None]] = []
        self._realtime_dispatcher = realtime_dispatcher or MessagingRealtimeDispatcher()

    async def start(self) -> None:
        if self._tasks:
            return
        if not settings.messaging_event_backbone_enabled:
            logger.info("Messaging event backbone disabled; runtime will not connect to NATS")
            return

        await self._ensure_connection()
        await self._ensure_stream()
        self._stop_event.clear()
        self._tasks = [
            asyncio.create_task(self._dispatch_loop(), name="messaging-outbox-dispatcher"),
            *[
                asyncio.create_task(self._consume_loop(consumer_key), name=f"messaging-consumer-{consumer_key}")
                for consumer_key in SUPPORTED_MESSAGING_CONSUMERS
            ],
        ]
        logger.info(
            "Messaging event backbone runtime started",
            extra={"consumers": list(SUPPORTED_MESSAGING_CONSUMERS)},
        )

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

        self._connection = await nats.connect(settings.nats_url, name="cybervpn-messaging-backend")
        self._jetstream = self._connection.jetstream()

    async def _ensure_stream(self) -> None:
        try:
            await self._jetstream.stream_info(settings.nats_messaging_stream_name)
        except Exception:
            await self._jetstream.add_stream(
                name=settings.nats_messaging_stream_name,
                subjects=[f"{settings.nats_messaging_subject_prefix}.>"],
            )

    async def _dispatch_loop(self) -> None:
        lease_owner = f"messaging-dispatcher-{uuid4().hex}"
        while not self._stop_event.is_set():
            try:
                for consumer_key in SUPPORTED_MESSAGING_CONSUMERS:
                    await self._dispatch_pending_publications(consumer_key=consumer_key, lease_owner=lease_owner)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Messaging outbox dispatcher iteration failed")
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
            envelopes = [(publication.id, self._build_envelope(publication=publication)) for publication in claimed]
            await session.commit()

        for publication_id, envelope in envelopes:
            try:
                ack = await self._publish_envelope(envelope)
                async with AsyncSessionLocal() as session:
                    repo = OutboxRepository(session)
                    publication = await repo.get_publication_by_id(publication_id)
                    if publication is None:
                        continue
                    outbox_event = publication.outbox_event
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
                    _observe_publish_success(
                        event_type=outbox_event.event_name,
                        consumer_name=publication.consumer_key,
                        lag_seconds=_lag_seconds(
                            start=outbox_event.occurred_at,
                            end=publication.published_at or datetime.now(UTC),
                        ),
                    )
                    await session.commit()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                async with AsyncSessionLocal() as session:
                    repo = OutboxRepository(session)
                    publication = await repo.get_publication_by_id(publication_id)
                    if publication is not None:
                        await self._mark_publication_failure(
                            repo=repo,
                            publication=publication,
                            lease_owner=lease_owner,
                            exc=exc,
                        )
                        await session.commit()
                logger.exception("Messaging outbox publication failed", extra={"consumer_key": consumer_key})

    async def _publish_envelope(self, envelope: MessagingOutboxEnvelope) -> dict[str, Any]:
        payload = json.dumps(envelope.as_payload(), separators=(",", ":"), default=str).encode("utf-8")
        idempotency_key = f"{envelope.consumer_key}:{envelope.event_key}"
        published_at = datetime.now(UTC)
        ack = await self._jetstream.publish(
            envelope.subject,
            payload,
            stream=settings.nats_messaging_stream_name,
            headers={"Nats-Msg-Id": idempotency_key},
        )
        sequence = getattr(ack, "sequence", getattr(ack, "seq", None))
        return {
            "status": "published",
            "stream": getattr(ack, "stream", settings.nats_messaging_stream_name),
            "sequence": sequence,
            "broker_sequence": sequence,
            "duplicate": bool(getattr(ack, "duplicate", False)),
            "subject": envelope.subject,
            "consumer_key": envelope.consumer_key,
            "event_version": envelope.schema_version,
            "idempotency_key": idempotency_key,
            "published_at": published_at.isoformat(),
        }

    async def _consume_loop(self, consumer_key: str) -> None:
        await self._ensure_connection()
        subject = f"{settings.nats_messaging_subject_prefix}.{consumer_key}.>"
        subscription = await self._jetstream.pull_subscribe(
            subject,
            durable=f"{consumer_key}-durable",
            stream=settings.nats_messaging_stream_name,
        )
        while not self._stop_event.is_set():
            try:
                messages = await subscription.fetch(
                    settings.nats_consumer_fetch_batch_size,
                    timeout=settings.nats_consumer_fetch_timeout_seconds,
                )
            except NatsTimeoutError:
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
                    logger.exception("Messaging event consumer failed", extra={"consumer_key": consumer_key})
        await subscription.unsubscribe()

    async def _process_message(self, *, consumer_key: str, raw_message: Any) -> None:
        payload = json.loads(raw_message.data.decode("utf-8"))
        event_key = str(payload["event_id"])
        event_name = str(payload["event_type"])
        subject = str(payload["subject"])

        async with AsyncSessionLocal() as session:
            repo = OutboxConsumerReceiptRepository(session)
            existing = await repo.get_receipt(consumer_key=consumer_key, event_key=event_key)
            if existing is not None:
                await session.commit()
                return

            metadata_payload: dict[str, object] = {"status": "processed"}
            if consumer_key == "messaging_realtime_projection":
                dispatch_count = await self._realtime_dispatcher.dispatch(payload)
                metadata_payload["dispatch_count"] = dispatch_count

            await repo.create_receipt(
                consumer_key=consumer_key,
                event_key=event_key,
                event_name=event_name,
                subject=subject,
                metadata_payload=metadata_payload,
            )
            await session.commit()

    async def _mark_publication_failure(
        self,
        *,
        repo: OutboxRepository,
        publication: OutboxPublicationModel,
        lease_owner: str,
        exc: Exception,
    ) -> str:
        outbox_event = publication.outbox_event
        failed_at = datetime.now(UTC)
        error_message = str(exc)
        if int(publication.attempts or 0) >= settings.outbox_dispatch_dead_letter_after_attempts:
            await repo.mark_publication_dead_letter(
                publication=publication,
                lease_owner=lease_owner,
                failed_at=failed_at,
                error_message=error_message,
            )
            failure_result = "dead_letter"
        else:
            await repo.mark_publication_failed(
                publication=publication,
                lease_owner=lease_owner,
                failed_at=failed_at,
                retry_at=failed_at.replace(microsecond=0)
                + timedelta(seconds=settings.outbox_dispatch_retry_after_seconds),
                error_message=error_message,
            )
            failure_result = "failure"
        _observe_publish_failure(
            event_type=outbox_event.event_name,
            consumer_name=publication.consumer_key,
            result=failure_result,
            lag_seconds=_lag_seconds(start=outbox_event.occurred_at, end=failed_at),
        )
        return failure_result

    def _build_envelope(self, *, publication: OutboxPublicationModel) -> MessagingOutboxEnvelope:
        event = publication.outbox_event
        subject = _build_subject(
            consumer_key=publication.consumer_key,
            event_name=event.event_name,
            schema_version=event.schema_version,
        )
        return MessagingOutboxEnvelope(
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
    return f"{settings.nats_messaging_subject_prefix}.{consumer_key}.{event_name}.v{schema_version}"


def _recipient_refs(payload: dict[str, Any]) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for raw in payload.get("recipient_refs") or ():
        if not isinstance(raw, dict):
            continue
        recipient_type = str(raw.get("type") or "").strip()
        recipient_id = str(raw.get("id") or "").strip()
        key = (recipient_type, recipient_id)
        if recipient_type and recipient_id and key not in seen:
            seen.add(key)
            refs.append({"type": recipient_type, "id": recipient_id})
    return refs


def _realtime_payload(payload: dict[str, Any], *, recipient: dict[str, str]) -> dict[str, Any]:
    payload_body = _sanitize_realtime_payload(dict(payload.get("payload") or {}), recipient=recipient)
    return {
        "event_id": str(payload["event_id"]),
        "event_type": str(payload["event_type"]),
        "occurred_at": str(payload["occurred_at"]),
        "aggregate_type": str(payload["aggregate_type"]),
        "aggregate_id": str(payload["aggregate_id"]),
        "payload": payload_body,
    }


def _sanitize_realtime_payload(payload: dict[str, Any], *, recipient: dict[str, str]) -> dict[str, Any]:
    payload.pop("recipient_refs", None)
    if recipient.get("type") == "customer":
        for key in (
            "assigned_admin_id",
            "created_by_admin_id",
            "sender_id",
            "participant_id",
            "customer_account_id",
            "recipient_id",
        ):
            payload.pop(key, None)
    return payload


def _normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _lag_seconds(*, start: datetime, end: datetime) -> float:
    return max((_normalize_utc(end) - _normalize_utc(start)).total_seconds(), 0.0)


def _observe_publish_success(*, event_type: str, consumer_name: str, lag_seconds: float | None) -> None:
    labels = {"event_type": event_type, "consumer_name": consumer_name, "result": "success"}
    messaging_outbox_events_published_total.labels(**labels).inc()
    if lag_seconds is not None:
        messaging_outbox_lag_seconds.labels(**labels).observe(max(lag_seconds, 0.0))


def _observe_publish_failure(
    *,
    event_type: str,
    consumer_name: str,
    result: str,
    lag_seconds: float | None,
) -> None:
    labels = {"event_type": event_type, "consumer_name": consumer_name, "result": result}
    messaging_outbox_publish_failures_total.labels(**labels).inc()
    if lag_seconds is not None:
        messaging_outbox_lag_seconds.labels(**labels).observe(max(lag_seconds, 0.0))
