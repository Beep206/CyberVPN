"""Tests for messaging outbox notification and broadcast fanout."""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("METRICS_PROTECT", "false")
os.environ.setdefault("REMNAWAVE_API_TOKEN", "test-token")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123:test-bot")
os.environ.setdefault("CRYPTOBOT_TOKEN", "test-crypto")

from src.models.messaging_outbox import (
    BroadcastCampaignModel,
    BroadcastCampaignRecipientModel,
    MessagingOutboxConsumerReceiptModel,
    MessagingOutboxEventModel,
    MessagingOutboxPublicationModel,
    SiteNotificationDeliveryModel,
    SiteNotificationModel,
)
from src.services.delivery_adapters import DeliveryAttempt, DisabledDeliveryChannelAdapter
from src.tasks.notifications import messaging_outbox as outbox_module
from src.tasks.notifications.messaging_outbox import (
    CONSUMER_BROADCAST_FANOUT_WORKER,
    CONSUMER_SITE_NOTIFICATION_FANOUT,
    MessagingOutboxProcessor,
)


@pytest.fixture
async def session_factory():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    tables = [
        MessagingOutboxEventModel.__table__,
        MessagingOutboxPublicationModel.__table__,
        MessagingOutboxConsumerReceiptModel.__table__,
        SiteNotificationModel.__table__,
        SiteNotificationDeliveryModel.__table__,
        BroadcastCampaignModel.__table__,
        BroadcastCampaignRecipientModel.__table__,
    ]
    async with engine.begin() as conn:
        for table in tables:
            await conn.run_sync(table.create)
    try:
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_site_notification_fanout_materializes_once(session_factory) -> None:
    customer_id = uuid.uuid4()
    admin_id = uuid.uuid4()
    event_id = uuid.uuid4()
    publication_id = uuid.uuid4()
    now = datetime.now(UTC)
    async with session_factory() as session:
        session.add(
            MessagingOutboxEventModel(
                id=event_id,
                event_key="messaging.message.created:msg-1",
                event_name="messaging.message.created",
                event_family="messaging",
                aggregate_type="messaging_message",
                aggregate_id=str(uuid.uuid4()),
                partition_key=str(customer_id),
                schema_version=1,
                event_status="pending_publication",
                event_payload={
                    "conversation_id": str(uuid.uuid4()),
                    "conversation_public_id": "conv_test123",
                    "message_id": str(uuid.uuid4()),
                    "body_included": False,
                    "recipient_refs": [
                        {"type": "customer", "id": str(customer_id)},
                        {"type": "admin", "id": str(admin_id)},
                    ],
                },
                actor_context={"principal_type": "customer", "principal_id": str(customer_id)},
                source_context={"bounded_context": "messaging"},
                occurred_at=now,
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            MessagingOutboxPublicationModel(
                id=publication_id,
                outbox_event_id=event_id,
                consumer_key=CONSUMER_SITE_NOTIFICATION_FANOUT,
                publication_status="pending",
                attempts=0,
                next_attempt_at=now - timedelta(seconds=1),
                publication_payload={},
                created_at=now,
                updated_at=now,
            )
        )
        await session.commit()

    processor = MessagingOutboxProcessor(
        session_factory=session_factory,
        lease_owner="test-worker",
        batch_size=10,
        retry_after_seconds=5,
    )

    first = await processor.run()
    second = await processor.run()

    assert first.as_dict() == {
        "claimed": 1,
        "published": 1,
        "duplicates": 0,
        "failed": 0,
        "dead_lettered": 0,
        "recipients_created": 2,
        "recipients_skipped": 0,
    }
    assert second.claimed == 0

    async with session_factory() as session:
        assert await _count(session, SiteNotificationModel) == 2
        assert await _count(session, SiteNotificationDeliveryModel) == 2
        assert await _count(session, MessagingOutboxConsumerReceiptModel) == 1
        publication = await session.get(MessagingOutboxPublicationModel, publication_id)
        assert publication is not None
        assert publication.publication_status == "published"
        assert publication.lease_owner is None
        delivery_rows = (
            await session.execute(
                select(SiteNotificationDeliveryModel).order_by(SiteNotificationDeliveryModel.created_at)
            )
        ).scalars().all()
        assert {row.recipient_id for row in delivery_rows} == {customer_id, admin_id}


@pytest.mark.asyncio
async def test_duplicate_receipt_suppresses_side_effects(session_factory) -> None:
    event_id = uuid.uuid4()
    publication_id = uuid.uuid4()
    now = datetime.now(UTC)
    event_key = "messaging.message.created:msg-duplicate"
    async with session_factory() as session:
        session.add(
            MessagingOutboxEventModel(
                id=event_id,
                event_key=event_key,
                event_name="messaging.message.created",
                event_family="messaging",
                aggregate_type="messaging_message",
                aggregate_id=str(uuid.uuid4()),
                partition_key=str(uuid.uuid4()),
                schema_version=1,
                event_status="pending_publication",
                event_payload={"recipient_refs": [{"type": "customer", "id": str(uuid.uuid4())}]},
                actor_context={},
                source_context={},
                occurred_at=now,
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            MessagingOutboxPublicationModel(
                id=publication_id,
                outbox_event_id=event_id,
                consumer_key=CONSUMER_SITE_NOTIFICATION_FANOUT,
                publication_status="pending",
                attempts=0,
                next_attempt_at=now - timedelta(seconds=1),
                publication_payload={},
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            MessagingOutboxConsumerReceiptModel(
                consumer_key=CONSUMER_SITE_NOTIFICATION_FANOUT,
                event_key=event_key,
                event_name="messaging.message.created",
                subject="messaging.site_notification_fanout.messaging.message.created.v1",
                metadata_payload={"status": "processed"},
                processed_at=now,
                created_at=now,
            )
        )
        await session.commit()

    processor = MessagingOutboxProcessor(session_factory=session_factory, lease_owner="test-worker")
    result = await processor.run()

    assert result.duplicates == 1
    async with session_factory() as session:
        assert await _count(session, SiteNotificationModel) == 0
        publication = await session.get(MessagingOutboxPublicationModel, publication_id)
        assert publication is not None
        assert publication.publication_status == "published"
        assert publication.publication_payload["status"] == "duplicate_receipt"


@pytest.mark.asyncio
async def test_broadcast_fanout_materializes_explicit_customers(session_factory) -> None:
    campaign_id = uuid.uuid4()
    admin_id = uuid.uuid4()
    customer_ids = [uuid.uuid4(), uuid.uuid4()]
    event_id = uuid.uuid4()
    now = datetime.now(UTC)
    async with session_factory() as session:
        session.add(
            BroadcastCampaignModel(
                id=campaign_id,
                public_id="bc_test123",
                name="Stage 2 test",
                status="scheduled",
                audience_type="explicit_customers",
                audience_filter={"customer_account_ids": [str(item) for item in customer_ids]},
                title="Maintenance window",
                body="Service window scheduled.",
                action_url="/notifications",
                scheduled_at=now - timedelta(minutes=1),
                created_by_admin_id=admin_id,
                metadata_json={},
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            MessagingOutboxEventModel(
                id=event_id,
                event_key=f"broadcast.created:{campaign_id}",
                event_name="broadcast.created",
                event_family="broadcast",
                aggregate_type="broadcast_campaign",
                aggregate_id=str(campaign_id),
                partition_key=str(campaign_id),
                schema_version=1,
                event_status="pending_publication",
                event_payload={"campaign_id": str(campaign_id), "audience_type": "explicit_customers"},
                actor_context={"principal_type": "admin", "principal_id": str(admin_id)},
                source_context={"bounded_context": "messaging"},
                occurred_at=now,
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            MessagingOutboxPublicationModel(
                outbox_event_id=event_id,
                consumer_key=CONSUMER_BROADCAST_FANOUT_WORKER,
                publication_status="pending",
                attempts=0,
                next_attempt_at=now - timedelta(seconds=1),
                publication_payload={},
                created_at=now,
                updated_at=now,
            )
        )
        await session.commit()

    processor = MessagingOutboxProcessor(session_factory=session_factory, lease_owner="test-worker")
    result = await processor.run()
    repeat = await processor.run()

    assert result.recipients_created == 2
    assert repeat.claimed == 0
    async with session_factory() as session:
        assert await _count(session, SiteNotificationModel) == 2
        assert await _count(session, SiteNotificationDeliveryModel) == 2
        assert await _count(session, BroadcastCampaignRecipientModel) == 2
        campaign = await session.get(BroadcastCampaignModel, campaign_id)
        assert campaign is not None
        assert campaign.status == "sent"


@pytest.mark.asyncio
async def test_processing_failure_reschedules_then_dead_letters(
    monkeypatch: pytest.MonkeyPatch,
    session_factory,
) -> None:
    event_id = uuid.uuid4()
    publication_id = uuid.uuid4()
    now = datetime.now(UTC)
    async with session_factory() as session:
        session.add(
            MessagingOutboxEventModel(
                id=event_id,
                event_key="messaging.message.created:msg-fail",
                event_name="messaging.message.created",
                event_family="messaging",
                aggregate_type="messaging_message",
                aggregate_id=str(uuid.uuid4()),
                partition_key=str(uuid.uuid4()),
                schema_version=1,
                event_status="pending_publication",
                event_payload={"recipient_refs": [{"type": "customer", "id": str(uuid.uuid4())}]},
                actor_context={},
                source_context={},
                occurred_at=now,
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            MessagingOutboxPublicationModel(
                id=publication_id,
                outbox_event_id=event_id,
                consumer_key=CONSUMER_SITE_NOTIFICATION_FANOUT,
                publication_status="pending",
                attempts=1,
                next_attempt_at=now - timedelta(seconds=1),
                publication_payload={},
                created_at=now,
                updated_at=now,
            )
        )
        await session.commit()

    async def fail_handler(self, session, event):
        raise RuntimeError("fake nats unavailable")

    monkeypatch.setattr(outbox_module.MessagingOutboxProcessor, "_handle_site_notification_fanout", fail_handler)
    processor = MessagingOutboxProcessor(
        session_factory=session_factory,
        lease_owner="test-worker",
        retry_after_seconds=5,
        dead_letter_after_attempts=2,
    )

    result = await processor.run()

    assert result.dead_lettered == 1
    async with session_factory() as session:
        publication = await session.get(MessagingOutboxPublicationModel, publication_id)
        assert publication is not None
        assert publication.publication_status == "dead_letter"
        assert publication.lease_owner is None
        assert "fake nats unavailable" in str(publication.last_error)


@pytest.mark.asyncio
async def test_future_external_delivery_adapter_is_disabled() -> None:
    adapter = DisabledDeliveryChannelAdapter("telegram")

    result = await adapter.send(
        DeliveryAttempt(
            channel="telegram",
            recipient_type="customer",
            recipient_id=str(uuid.uuid4()),
            notification_id=str(uuid.uuid4()),
            event_key="messaging.message.created:msg-1",
        )
    )

    assert result.disabled is True
    assert result.provider_message_id is None
    assert result.status == "disabled"


async def _count(session, model) -> int:
    return int(await session.scalar(select(func.count()).select_from(model)))
