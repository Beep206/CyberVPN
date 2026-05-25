#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json
import os
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from prometheus_client import REGISTRY
from sqlalchemy import func, select

from src.application.events import EventOutboxService, OutboxActorContext
from src.config.settings import settings
from src.domain.enums import OutboxPublicationStatus
from src.infrastructure.database.models.outbox_consumer_receipt_model import OutboxConsumerReceiptModel
from src.infrastructure.database.models.outbox_event_model import OutboxEventModel, OutboxPublicationModel
from src.infrastructure.database.models.partner_workspace_feed_event_model import PartnerWorkspaceFeedEventModel
from src.infrastructure.database.session import AsyncSessionLocal, Base, engine
from src.infrastructure.messaging.nats_partner_runtime import SUPPORTED_CONSUMERS, NatsPartnerRuntime

EVIDENCE_DIR = Path(os.environ["STAGE3_OUTBOX_EVIDENCE_DIR"]).resolve()
LEASE_OWNER = "stage3-outbox-dispatcher-proof"


class FailingJetStream:
    async def publish(self, *args, **kwargs):  # noqa: ANN002, ANN003
        raise RuntimeError("stage3 synthetic broker unavailable")


async def main() -> None:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    await _reset_schema()
    await _write_json("settings.json", _runtime_settings())
    await _write_json("db-before.json", await _db_snapshot())

    workspace_id = uuid4()
    aggregate_id = str(uuid4())
    event = await _append_event(
        event_name="entitlement.grant.activated",
        aggregate_type="entitlement_grant",
        aggregate_id=aggregate_id,
        workspace_id=workspace_id,
        consumer_keys=tuple(SUPPORTED_CONSUMERS),
    )
    await _write_json("db-after-append.json", await _db_snapshot(event_key=event.event_key))

    runtime = NatsPartnerRuntime()
    await runtime._ensure_connection()
    await runtime._ensure_stream()

    for consumer_key in SUPPORTED_CONSUMERS:
        await runtime._dispatch_pending_publications(consumer_key=consumer_key, lease_owner=LEASE_OWNER)
    await _write_json("db-after-dispatch.json", await _db_snapshot(event_key=event.event_key))

    consumed_payloads = await _consume_with_runtime(runtime=runtime, event_key=event.event_key)
    await _write_json("consumed-payloads.json", consumed_payloads)
    await _write_json("consumer-receipts.json", await _consumer_receipts(event_key=event.event_key))
    await _write_json("workspace-feed-events.json", await _workspace_feed_events(workspace_id=workspace_id))

    duplicate_result = await _prove_duplicate_idempotency(
        runtime=runtime,
        consumer_key="operational_replay",
        payload=consumed_payloads["operational_replay"],
        event_key=event.event_key,
        workspace_id=workspace_id,
    )
    await _write_json("duplicate-idempotency-proof.json", duplicate_result)

    failed_event = await _append_event(
        event_name="entitlement.grant.activated",
        aggregate_type="entitlement_grant",
        aggregate_id=str(uuid4()),
        workspace_id=workspace_id,
        consumer_keys=("analytics_mart",),
    )
    original_jetstream = runtime._jetstream
    previous_dead_letter_attempts = settings.outbox_dispatch_dead_letter_after_attempts
    settings.outbox_dispatch_dead_letter_after_attempts = 1
    runtime._jetstream = FailingJetStream()
    try:
        await runtime._dispatch_pending_publications(consumer_key="analytics_mart", lease_owner=LEASE_OWNER)
    finally:
        runtime._jetstream = original_jetstream
        settings.outbox_dispatch_dead_letter_after_attempts = previous_dead_letter_attempts
    await _write_json("dead-letter-proof.json", await _db_snapshot(event_key=failed_event.event_key))

    backlog_event = await _append_event(
        event_name="invite.redeemed",
        aggregate_type="invite_code",
        aggregate_id=str(uuid4()),
        workspace_id=workspace_id,
        consumer_keys=("analytics_mart",),
    )
    await _write_json("backlog-alert-input.json", await _backlog_input(event_key=backlog_event.event_key))
    await _write_json("metrics-proof.json", _metrics_snapshot())
    await _write_json("nats-jsz-after.json", _fetch_json("http://127.0.0.1:8222/jsz?streams=true&consumers=true"))

    await runtime.stop()
    await engine.dispose()

    summary = {
        "status": "ok",
        "event_key": event.event_key,
        "workspace_id": str(workspace_id),
        "successful_event_status": (await _db_snapshot(event_key=event.event_key))["events"][0]["event_status"],
        "published_publications": 2,
        "consumer_receipts": len(await _consumer_receipts(event_key=event.event_key)),
        "duplicate_delivery_idempotent": duplicate_result["idempotent"],
        "dead_letter_event_key": failed_event.event_key,
        "backlog_event_key": backlog_event.event_key,
    }
    await _write_json("summary.json", summary)
    (EVIDENCE_DIR / "summary.txt").write_text(
        "\n".join(f"{key}={value}" for key, value in summary.items()) + "\n",
        encoding="utf-8",
    )


async def _reset_schema() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


async def _append_event(
    *,
    event_name: str,
    aggregate_type: str,
    aggregate_id: str,
    workspace_id,
    consumer_keys: tuple[str, ...],
) -> OutboxEventModel:
    async with AsyncSessionLocal() as session:
        event = await EventOutboxService(session).append_event(
            event_name=event_name,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            partition_key=str(workspace_id),
            event_payload={
                "partner_account_id": str(workspace_id),
                "workspace_id": str(workspace_id),
                "customer_account_id": "stage3-customer-proof",
                "entitlement_grant_id": aggregate_id,
                "grant_status": "active",
                "source_type": "stage3_proof",
            },
            actor_context=OutboxActorContext(principal_type="service", principal_id="stage3-outbox-proof"),
            source_context={"workspace_id": str(workspace_id), "stage": "S3-STAGE-04"},
            consumer_keys=consumer_keys,
        )
        await session.commit()
        await session.refresh(event)
        return event


async def _consume_with_runtime(*, runtime: NatsPartnerRuntime, event_key: str) -> dict[str, dict[str, object]]:
    consumed: dict[str, dict[str, object]] = {}
    for consumer_key in SUPPORTED_CONSUMERS:
        subject = f"{settings.nats_partner_subject_prefix}.{consumer_key}.>"
        subscription = await runtime._jetstream.pull_subscribe(
            subject,
            durable=f"stage3-proof-{consumer_key}",
            stream=settings.nats_partner_stream_name,
        )
        messages = await subscription.fetch(1, timeout=5)
        if not messages:
            raise RuntimeError(f"No message fetched for {consumer_key}")
        message = messages[0]
        payload = json.loads(message.data.decode("utf-8"))
        if payload["event_id"] != event_key:
            raise RuntimeError(f"Unexpected event for {consumer_key}: {payload['event_id']}")
        await runtime._process_message(consumer_key=consumer_key, raw_message=message)
        await message.ack()
        consumed[consumer_key] = payload
        await subscription.unsubscribe()
    return consumed


async def _prove_duplicate_idempotency(
    *,
    runtime: NatsPartnerRuntime,
    consumer_key: str,
    payload: dict[str, object],
    event_key: str,
    workspace_id,
) -> dict[str, object]:
    before_receipts = await _consumer_receipt_count(event_key=event_key, consumer_key=consumer_key)
    before_feed = await _feed_count(workspace_id=workspace_id, event_key=event_key)
    raw_message = SimpleNamespace(data=json.dumps(payload).encode("utf-8"))
    await runtime._process_message(consumer_key=consumer_key, raw_message=raw_message)
    after_receipts = await _consumer_receipt_count(event_key=event_key, consumer_key=consumer_key)
    after_feed = await _feed_count(workspace_id=workspace_id, event_key=event_key)
    return {
        "consumer_key": consumer_key,
        "event_key": event_key,
        "before_receipts": before_receipts,
        "after_receipts": after_receipts,
        "before_feed_events": before_feed,
        "after_feed_events": after_feed,
        "idempotent": before_receipts == after_receipts and before_feed == after_feed,
    }


async def _db_snapshot(*, event_key: str | None = None) -> dict[str, object]:
    async with AsyncSessionLocal() as session:
        query = select(OutboxEventModel).order_by(OutboxEventModel.created_at.asc())
        if event_key:
            query = query.where(OutboxEventModel.event_key == event_key)
        events = list((await session.execute(query)).scalars().all())
        publications = list(
            (
                await session.execute(
                    select(OutboxPublicationModel).order_by(OutboxPublicationModel.created_at.asc())
                )
            )
            .scalars()
            .all()
        )
        if event_key:
            event_ids = {event.id for event in events}
            publications = [publication for publication in publications if publication.outbox_event_id in event_ids]
        return {
            "captured_at": datetime.now(UTC).isoformat(),
            "counts": {
                "events": len(events),
                "publications": len(publications),
                "pending_publications": sum(
                    1
                    for publication in publications
                    if publication.publication_status == OutboxPublicationStatus.PENDING.value
                ),
                "published_publications": sum(
                    1
                    for publication in publications
                    if publication.publication_status == OutboxPublicationStatus.PUBLISHED.value
                ),
                "dead_letter_publications": sum(
                    1
                    for publication in publications
                    if publication.publication_status == OutboxPublicationStatus.DEAD_LETTER.value
                ),
            },
            "events": [_serialize_event(event) for event in events],
            "publications": [_serialize_publication(publication) for publication in publications],
        }


async def _consumer_receipts(*, event_key: str) -> list[dict[str, object]]:
    async with AsyncSessionLocal() as session:
        receipts = list(
            (
                await session.execute(
                    select(OutboxConsumerReceiptModel)
                    .where(OutboxConsumerReceiptModel.event_key == event_key)
                    .order_by(OutboxConsumerReceiptModel.consumer_key.asc())
                )
            )
            .scalars()
            .all()
        )
        return [_serialize_receipt(receipt) for receipt in receipts]


async def _workspace_feed_events(*, workspace_id) -> list[dict[str, object]]:
    async with AsyncSessionLocal() as session:
        events = list(
            (
                await session.execute(
                    select(PartnerWorkspaceFeedEventModel)
                    .where(PartnerWorkspaceFeedEventModel.workspace_id == workspace_id)
                    .order_by(PartnerWorkspaceFeedEventModel.created_at.asc())
                )
            )
            .scalars()
            .all()
        )
        return [_serialize_feed_event(event) for event in events]


async def _consumer_receipt_count(*, event_key: str, consumer_key: str) -> int:
    async with AsyncSessionLocal() as session:
        return int(
            (
                await session.execute(
                    select(func.count())
                    .select_from(OutboxConsumerReceiptModel)
                    .where(
                        OutboxConsumerReceiptModel.event_key == event_key,
                        OutboxConsumerReceiptModel.consumer_key == consumer_key,
                    )
                )
            ).scalar_one()
        )


async def _feed_count(*, workspace_id, event_key: str) -> int:
    async with AsyncSessionLocal() as session:
        return int(
            (
                await session.execute(
                    select(func.count())
                    .select_from(PartnerWorkspaceFeedEventModel)
                    .where(
                        PartnerWorkspaceFeedEventModel.workspace_id == workspace_id,
                        PartnerWorkspaceFeedEventModel.event_key == event_key,
                    )
                )
            ).scalar_one()
        )


async def _backlog_input(*, event_key: str) -> dict[str, object]:
    snapshot = await _db_snapshot(event_key=event_key)
    pending = [
        publication
        for publication in snapshot["publications"]
        if publication["publication_status"] == OutboxPublicationStatus.PENDING.value
    ]
    return {
        "event_key": event_key,
        "pending_publications": len(pending),
        "oldest_pending_next_attempt_at": pending[0]["next_attempt_at"] if pending else None,
        "alert_rule_input": "pending_publications > 0 and age exceeds S3 threshold",
        "snapshot": snapshot,
    }


def _runtime_settings() -> dict[str, object]:
    return {
        "environment": settings.environment,
        "partner_event_backbone_enabled": settings.partner_event_backbone_enabled,
        "nats_partner_stream_name": settings.nats_partner_stream_name,
        "nats_partner_subject_prefix": settings.nats_partner_subject_prefix,
        "outbox_dispatch_batch_size": settings.outbox_dispatch_batch_size,
        "outbox_dispatch_dead_letter_after_attempts": settings.outbox_dispatch_dead_letter_after_attempts,
        "posthog_enabled": settings.posthog_enabled,
    }


def _metrics_snapshot() -> dict[str, object]:
    metric_prefixes = (
        "cybervpn_partner_outbox_events_created",
        "cybervpn_partner_outbox_events_published",
        "cybervpn_partner_outbox_publish_failures",
        "cybervpn_partner_outbox_lag_seconds",
    )
    labeled_samples: list[dict[str, object]] = []
    for metric_family in REGISTRY.collect():
        if not metric_family.name.startswith(metric_prefixes):
            continue
        for sample in metric_family.samples:
            labeled_samples.append(
                {
                    "name": sample.name,
                    "labels": dict(sample.labels),
                    "value": sample.value,
                }
            )
    return {
        "captured_at": datetime.now(UTC).isoformat(),
        "note": (
            "Prometheus samples are emitted in-process. This snapshot captures label-specific sample values "
            "for the S3-STAGE-04 proof process."
        ),
        "labeled_samples": labeled_samples,
        "registered_metric_names": [
            "cybervpn_partner_outbox_events_created_total",
            "cybervpn_partner_outbox_events_published_total",
            "cybervpn_partner_outbox_publish_failures_total",
            "cybervpn_partner_outbox_lag_seconds",
        ],
    }


def _fetch_json(url: str) -> dict[str, object]:
    if not url.startswith("http://127.0.0.1:"):
        raise ValueError("Only localhost HTTP evidence endpoints are allowed")
    with urllib.request.urlopen(url, timeout=5) as response:  # noqa: S310
        return json.loads(response.read().decode("utf-8"))


def _serialize_event(event: OutboxEventModel) -> dict[str, object]:
    return {
        "id": str(event.id),
        "event_key": event.event_key,
        "event_name": event.event_name,
        "event_family": event.event_family,
        "aggregate_type": event.aggregate_type,
        "aggregate_id": event.aggregate_id,
        "partition_key": event.partition_key,
        "schema_version": event.schema_version,
        "event_status": event.event_status,
        "event_payload": dict(event.event_payload or {}),
        "actor_context": dict(event.actor_context or {}),
        "source_context": dict(event.source_context or {}),
        "occurred_at": _iso(event.occurred_at),
        "created_at": _iso(event.created_at),
        "updated_at": _iso(event.updated_at),
    }


def _serialize_publication(publication: OutboxPublicationModel) -> dict[str, object]:
    return {
        "id": str(publication.id),
        "outbox_event_id": str(publication.outbox_event_id),
        "consumer_key": publication.consumer_key,
        "publication_status": publication.publication_status,
        "attempts": publication.attempts,
        "lease_owner": publication.lease_owner,
        "leased_until": _iso(publication.leased_until),
        "next_attempt_at": _iso(publication.next_attempt_at),
        "submitted_at": _iso(publication.submitted_at),
        "published_at": _iso(publication.published_at),
        "last_error": publication.last_error,
        "publication_payload": dict(publication.publication_payload or {}),
        "created_at": _iso(publication.created_at),
        "updated_at": _iso(publication.updated_at),
    }


def _serialize_receipt(receipt: OutboxConsumerReceiptModel) -> dict[str, object]:
    return {
        "id": str(receipt.id),
        "consumer_key": receipt.consumer_key,
        "event_key": receipt.event_key,
        "event_name": receipt.event_name,
        "subject": receipt.subject,
        "status": receipt.status,
        "metadata_payload": dict(receipt.metadata_payload or {}),
        "processed_at": _iso(receipt.processed_at),
    }


def _serialize_feed_event(event: PartnerWorkspaceFeedEventModel) -> dict[str, object]:
    return {
        "id": str(event.id),
        "workspace_id": str(event.workspace_id),
        "event_key": event.event_key,
        "event_name": event.event_name,
        "event_family": event.event_family,
        "aggregate_type": event.aggregate_type,
        "aggregate_id": event.aggregate_id,
        "consumer_key": event.consumer_key,
        "subject": event.subject,
        "payload": dict(event.payload or {}),
        "occurred_at": _iso(event.occurred_at),
        "created_at": _iso(event.created_at),
    }


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat()


async def _write_json(filename: str, payload: object) -> None:
    (EVIDENCE_DIR / filename).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    asyncio.run(main())
