"""Process messaging outbox publications and local fanout side effects."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.broker import broker
from src.config import get_settings
from src.database.session import get_session_factory
from src.metrics import (
    MESSAGING_FANOUT_RECIPIENTS_TOTAL,
    MESSAGING_OUTBOX_PROCESS_DURATION,
    MESSAGING_OUTBOX_PUBLICATIONS_TOTAL,
)
from src.models.messaging_outbox import (
    BroadcastCampaignModel,
    BroadcastCampaignRecipientModel,
    MessagingOutboxConsumerReceiptModel,
    MessagingOutboxEventModel,
    MessagingOutboxPublicationModel,
    SiteNotificationDeliveryModel,
    SiteNotificationModel,
)

logger = structlog.get_logger(__name__)

CONSUMER_SITE_NOTIFICATION_FANOUT = "site_notification_fanout"
CONSUMER_BROADCAST_FANOUT_WORKER = "broadcast_fanout_worker"
SUPPORTED_MESSAGING_OUTBOX_CONSUMERS = (
    CONSUMER_SITE_NOTIFICATION_FANOUT,
    CONSUMER_BROADCAST_FANOUT_WORKER,
)

STATUS_PENDING = "pending"
STATUS_CLAIMED = "claimed"
STATUS_PUBLISHED = "published"
STATUS_FAILED = "failed"
STATUS_DEAD_LETTER = "dead_letter"

EVENT_STATUS_PENDING = "pending_publication"
EVENT_STATUS_PARTIAL = "partially_published"
EVENT_STATUS_PUBLISHED = "published"
EVENT_STATUS_FAILED = "failed"

BROADCAST_STATUS_DRAFT = "draft"
BROADCAST_STATUS_SCHEDULED = "scheduled"
BROADCAST_STATUS_SENDING = "sending"
BROADCAST_STATUS_SENT = "sent"
BROADCAST_STATUS_CANCELLED = "cancelled"


class PublicationDeferredError(RuntimeError):
    def __init__(self, reason: str, retry_at: datetime) -> None:
        super().__init__(reason)
        self.retry_at = retry_at


@dataclass(slots=True)
class FanoutResult:
    created: int = 0
    skipped: int = 0
    failed: int = 0
    reason: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class ProcessorResult:
    claimed: int = 0
    published: int = 0
    duplicates: int = 0
    failed: int = 0
    dead_lettered: int = 0
    recipients_created: int = 0
    recipients_skipped: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "claimed": self.claimed,
            "published": self.published,
            "duplicates": self.duplicates,
            "failed": self.failed,
            "dead_lettered": self.dead_lettered,
            "recipients_created": self.recipients_created,
            "recipients_skipped": self.recipients_skipped,
        }


@broker.task(task_name="process_messaging_outbox", queue="notifications", retry_policy="notifications")
async def process_messaging_outbox(
    *,
    consumer_keys: list[str] | None = None,
    batch_size: int | None = None,
    lease_owner: str | None = None,
) -> dict[str, int]:
    """Process local messaging outbox consumers without external push delivery."""

    settings = get_settings()
    processor = MessagingOutboxProcessor(
        session_factory=get_session_factory(),
        consumer_keys=tuple(consumer_keys or SUPPORTED_MESSAGING_OUTBOX_CONSUMERS),
        batch_size=batch_size or getattr(settings, "messaging_outbox_batch_size", settings.notification_batch_size),
        lease_owner=lease_owner or f"task-worker-messaging-outbox-{uuid.uuid4().hex}",
        lease_seconds=getattr(settings, "messaging_outbox_lease_seconds", 30),
        retry_after_seconds=getattr(settings, "messaging_outbox_retry_after_seconds", 30),
        dead_letter_after_attempts=getattr(settings, "messaging_outbox_dead_letter_after_attempts", 5),
    )
    return (await processor.run()).as_dict()


class MessagingOutboxProcessor:
    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        consumer_keys: tuple[str, ...] = SUPPORTED_MESSAGING_OUTBOX_CONSUMERS,
        batch_size: int = 50,
        lease_owner: str,
        lease_seconds: int = 30,
        retry_after_seconds: int = 30,
        dead_letter_after_attempts: int = 5,
    ) -> None:
        self.session_factory = session_factory
        self.consumer_keys = tuple(dict.fromkeys(consumer_keys))
        self.batch_size = max(1, min(int(batch_size), 500))
        self.lease_owner = lease_owner
        self.lease_seconds = max(1, int(lease_seconds))
        self.retry_after_seconds = max(1, int(retry_after_seconds))
        self.dead_letter_after_attempts = max(1, int(dead_letter_after_attempts))

    async def run(self) -> ProcessorResult:
        start = time.monotonic()
        result = ProcessorResult()
        publication_ids = await self._claim_publications()
        result.claimed = len(publication_ids)
        try:
            for publication_id in publication_ids:
                status, fanout = await self._process_publication(publication_id)
                if status == "duplicate":
                    result.duplicates += 1
                elif status == STATUS_PUBLISHED:
                    result.published += 1
                elif status == STATUS_DEAD_LETTER:
                    result.dead_lettered += 1
                else:
                    result.failed += 1
                result.recipients_created += fanout.created
                result.recipients_skipped += fanout.skipped
            MESSAGING_OUTBOX_PROCESS_DURATION.labels(result="success").observe(time.monotonic() - start)
            return result
        except Exception:
            MESSAGING_OUTBOX_PROCESS_DURATION.labels(result="error").observe(time.monotonic() - start)
            raise

    async def _claim_publications(self) -> list[uuid.UUID]:
        now = datetime.now(UTC)
        leased_until = now.replace(microsecond=0) + timedelta(seconds=self.lease_seconds)
        async with self.session_factory() as session:
            query = (
                select(MessagingOutboxPublicationModel)
                .where(
                    MessagingOutboxPublicationModel.consumer_key.in_(self.consumer_keys),
                    MessagingOutboxPublicationModel.next_attempt_at <= now,
                    MessagingOutboxPublicationModel.publication_status.in_((STATUS_PENDING, STATUS_FAILED)),
                    or_(
                        MessagingOutboxPublicationModel.leased_until.is_(None),
                        MessagingOutboxPublicationModel.leased_until <= now,
                    ),
                )
                .order_by(
                    MessagingOutboxPublicationModel.next_attempt_at.asc(),
                    MessagingOutboxPublicationModel.created_at.asc(),
                )
                .limit(self.batch_size)
                .with_for_update(skip_locked=True)
            )
            result = await session.execute(query)
            publications = list(result.scalars().all())
            for publication in publications:
                publication.publication_status = STATUS_CLAIMED
                publication.lease_owner = self.lease_owner
                publication.leased_until = leased_until
                publication.attempts = int(publication.attempts or 0) + 1
                publication.updated_at = now
            await session.commit()
            return [publication.id for publication in publications]

    async def _process_publication(self, publication_id: uuid.UUID) -> tuple[str, FanoutResult]:
        try:
            async with self.session_factory() as session:
                publication, event = await self._load_publication_event(session, publication_id)
                self._assert_valid_lease(publication)

                existing_receipt = await self._get_receipt(session, publication.consumer_key, event.event_key)
                if existing_receipt is not None:
                    await self._mark_publication_published(
                        session,
                        publication,
                        event,
                        {"status": "duplicate_receipt", "receipt_id": str(existing_receipt.id)},
                    )
                    await session.commit()
                    MESSAGING_OUTBOX_PUBLICATIONS_TOTAL.labels(
                        consumer_key=publication.consumer_key, status="duplicate"
                    ).inc()
                    return "duplicate", FanoutResult(skipped=1, reason="duplicate_receipt")

                fanout = await self._handle_publication(session, publication, event)
                await self._create_receipt(session, publication, event, fanout)
                await self._mark_publication_published(
                    session,
                    publication,
                    event,
                    {
                        "status": "processed",
                        "created": fanout.created,
                        "skipped": fanout.skipped,
                        "reason": fanout.reason,
                        **fanout.metadata,
                    },
                )
                await session.commit()
                MESSAGING_OUTBOX_PUBLICATIONS_TOTAL.labels(
                    consumer_key=publication.consumer_key, status=STATUS_PUBLISHED
                ).inc()
                return STATUS_PUBLISHED, fanout
        except PublicationDeferredError as exc:
            return await self._mark_publication_failed(publication_id, exc, retry_at=exc.retry_at)
        except Exception as exc:
            return await self._mark_publication_failed(publication_id, exc)

    async def _load_publication_event(
        self, session: AsyncSession, publication_id: uuid.UUID
    ) -> tuple[MessagingOutboxPublicationModel, MessagingOutboxEventModel]:
        result = await session.execute(
            select(MessagingOutboxPublicationModel, MessagingOutboxEventModel)
            .join(
                MessagingOutboxEventModel,
                MessagingOutboxEventModel.id == MessagingOutboxPublicationModel.outbox_event_id,
            )
            .where(MessagingOutboxPublicationModel.id == publication_id)
        )
        row = result.one_or_none()
        if row is None:
            raise LookupError("Outbox publication not found")
        return row

    def _assert_valid_lease(self, publication: MessagingOutboxPublicationModel) -> None:
        if publication.lease_owner != self.lease_owner:
            raise RuntimeError("Outbox publication lease owner mismatch")
        leased_until = _normalize_utc(publication.leased_until)
        if leased_until is not None and leased_until < datetime.now(UTC):
            raise RuntimeError("Outbox publication lease expired")

    async def _handle_publication(
        self,
        session: AsyncSession,
        publication: MessagingOutboxPublicationModel,
        event: MessagingOutboxEventModel,
    ) -> FanoutResult:
        if publication.consumer_key == CONSUMER_SITE_NOTIFICATION_FANOUT:
            return await self._handle_site_notification_fanout(session, event)
        if publication.consumer_key == CONSUMER_BROADCAST_FANOUT_WORKER:
            return await self._handle_broadcast_fanout(session, event)
        return FanoutResult(skipped=1, reason="unsupported_consumer")

    async def _handle_site_notification_fanout(
        self, session: AsyncSession, event: MessagingOutboxEventModel
    ) -> FanoutResult:
        created = 0
        skipped = 0
        for recipient in _recipient_refs(event.event_payload):
            recipient_id = _parse_uuid(recipient["id"])
            if recipient["type"] not in {"customer", "admin"} or recipient_id is None:
                skipped += 1
                continue
            existing = await self._existing_site_delivery(
                session=session,
                event=event,
                recipient_type=recipient["type"],
                recipient_id=recipient_id,
            )
            if existing is not None:
                skipped += 1
                continue
            notification = self._build_site_notification(event=event)
            session.add(notification)
            await session.flush()
            session.add(
                SiteNotificationDeliveryModel(
                    notification_id=notification.id,
                    recipient_type=recipient["type"],
                    recipient_id=recipient_id,
                    delivery_channel="site",
                    status="pending",
                    attempts=0,
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC),
                )
            )
            created += 1
        self._observe_fanout(CONSUMER_SITE_NOTIFICATION_FANOUT, created=created, skipped=skipped)
        return FanoutResult(created=created, skipped=skipped)

    async def _handle_broadcast_fanout(self, session: AsyncSession, event: MessagingOutboxEventModel) -> FanoutResult:
        if event.event_name != "broadcast.created":
            return FanoutResult(skipped=1, reason="unsupported_broadcast_event")
        campaign_id = _parse_uuid(str(event.event_payload.get("campaign_id") or event.aggregate_id))
        if campaign_id is None:
            raise ValueError("Broadcast event is missing campaign_id")
        campaign = await session.get(BroadcastCampaignModel, campaign_id)
        if campaign is None:
            raise LookupError("Broadcast campaign not found")
        if campaign.status == BROADCAST_STATUS_CANCELLED:
            return FanoutResult(skipped=1, reason="campaign_cancelled")
        if campaign.status == BROADCAST_STATUS_DRAFT:
            return FanoutResult(skipped=1, reason="campaign_not_ready")
        scheduled_at = _normalize_utc(campaign.scheduled_at)
        if scheduled_at is not None and scheduled_at > datetime.now(UTC):
            raise PublicationDeferredError("Broadcast campaign is not due", retry_at=scheduled_at)
        if campaign.audience_type != "explicit_customers":
            return FanoutResult(skipped=1, reason="unsupported_audience_type")

        created = 0
        skipped = 0
        for recipient_id in _explicit_customer_ids(campaign.audience_filter):
            existing = await self._get_broadcast_recipient(session, campaign.id, recipient_id)
            if existing is not None:
                skipped += 1
                continue
            notification = SiteNotificationModel(
                notification_type="broadcast",
                severity="info",
                title=campaign.title,
                body=campaign.body,
                action_url=campaign.action_url,
                aggregate_type="broadcast_campaign",
                aggregate_id=str(campaign.id),
                broadcast_campaign_id=campaign.id,
                created_by_actor_type="admin",
                created_by_actor_id=campaign.created_by_admin_id,
                payload={"outbox_event_key": event.event_key, "event_type": event.event_name},
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            session.add(notification)
            await session.flush()
            session.add(
                SiteNotificationDeliveryModel(
                    notification_id=notification.id,
                    recipient_type="customer",
                    recipient_id=recipient_id,
                    delivery_channel="site",
                    status="pending",
                    attempts=0,
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC),
                )
            )
            session.add(
                BroadcastCampaignRecipientModel(
                    campaign_id=campaign.id,
                    recipient_type="customer",
                    recipient_id=recipient_id,
                    site_notification_id=notification.id,
                    status="created",
                    materialized_at=datetime.now(UTC),
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC),
                )
            )
            created += 1
        if campaign.status in {BROADCAST_STATUS_SCHEDULED, BROADCAST_STATUS_SENDING}:
            campaign.status = BROADCAST_STATUS_SENT
            campaign.updated_at = datetime.now(UTC)
        self._observe_fanout(CONSUMER_BROADCAST_FANOUT_WORKER, created=created, skipped=skipped)
        return FanoutResult(created=created, skipped=skipped, metadata={"campaign_id": str(campaign.id)})

    def _build_site_notification(self, *, event: MessagingOutboxEventModel) -> SiteNotificationModel:
        payload = dict(event.event_payload or {})
        conversation_id = (
            _parse_uuid(str(payload.get("conversation_id") or "")) if payload.get("conversation_id") else None
        )
        message_id = _parse_uuid(str(payload.get("message_id") or "")) if payload.get("message_id") else None
        actor_id = _parse_uuid(str((event.actor_context or {}).get("principal_id") or ""))
        return SiteNotificationModel(
            notification_type="message" if event.event_name.startswith("messaging.") else "system",
            severity="info",
            title=_site_notification_title(event.event_name),
            body=None,
            action_url=_conversation_action_url(payload),
            aggregate_type=event.aggregate_type,
            aggregate_id=event.aggregate_id,
            conversation_id=conversation_id,
            message_id=message_id,
            created_by_actor_type=str((event.actor_context or {}).get("principal_type") or "system"),
            created_by_actor_id=actor_id,
            payload={
                "outbox_event_key": event.event_key,
                "event_type": event.event_name,
                "conversation_id": str(conversation_id) if conversation_id else None,
                "message_id": str(message_id) if message_id else None,
                "body_included": False,
            },
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    async def _existing_site_delivery(
        self,
        *,
        session: AsyncSession,
        event: MessagingOutboxEventModel,
        recipient_type: str,
        recipient_id: uuid.UUID,
    ) -> SiteNotificationDeliveryModel | None:
        result = await session.execute(
            select(SiteNotificationModel, SiteNotificationDeliveryModel)
            .join(
                SiteNotificationDeliveryModel,
                SiteNotificationDeliveryModel.notification_id == SiteNotificationModel.id,
            )
            .where(
                SiteNotificationModel.aggregate_type == event.aggregate_type,
                SiteNotificationModel.aggregate_id == event.aggregate_id,
                SiteNotificationDeliveryModel.recipient_type == recipient_type,
                SiteNotificationDeliveryModel.recipient_id == recipient_id,
                SiteNotificationDeliveryModel.delivery_channel == "site",
            )
        )
        for notification, delivery in result.all():
            if dict(notification.payload or {}).get("outbox_event_key") == event.event_key:
                return delivery
        return None

    async def _get_broadcast_recipient(
        self, session: AsyncSession, campaign_id: uuid.UUID, recipient_id: uuid.UUID
    ) -> BroadcastCampaignRecipientModel | None:
        result = await session.execute(
            select(BroadcastCampaignRecipientModel).where(
                BroadcastCampaignRecipientModel.campaign_id == campaign_id,
                BroadcastCampaignRecipientModel.recipient_type == "customer",
                BroadcastCampaignRecipientModel.recipient_id == recipient_id,
            )
        )
        return result.scalar_one_or_none()

    async def _get_receipt(
        self, session: AsyncSession, consumer_key: str, event_key: str
    ) -> MessagingOutboxConsumerReceiptModel | None:
        result = await session.execute(
            select(MessagingOutboxConsumerReceiptModel).where(
                MessagingOutboxConsumerReceiptModel.consumer_key == consumer_key,
                MessagingOutboxConsumerReceiptModel.event_key == event_key,
            )
        )
        return result.scalar_one_or_none()

    async def _create_receipt(
        self,
        session: AsyncSession,
        publication: MessagingOutboxPublicationModel,
        event: MessagingOutboxEventModel,
        fanout: FanoutResult,
    ) -> None:
        session.add(
            MessagingOutboxConsumerReceiptModel(
                consumer_key=publication.consumer_key,
                event_key=event.event_key,
                event_name=event.event_name,
                subject=_build_subject(publication.consumer_key, event.event_name, event.schema_version),
                status="processed",
                metadata_payload={
                    "created": fanout.created,
                    "skipped": fanout.skipped,
                    "failed": fanout.failed,
                    "reason": fanout.reason,
                    **fanout.metadata,
                },
                processed_at=datetime.now(UTC),
                created_at=datetime.now(UTC),
            )
        )

    async def _mark_publication_published(
        self,
        session: AsyncSession,
        publication: MessagingOutboxPublicationModel,
        event: MessagingOutboxEventModel,
        payload: dict[str, object],
    ) -> None:
        now = datetime.now(UTC)
        publication.publication_status = STATUS_PUBLISHED
        publication.published_at = now
        publication.submitted_at = publication.submitted_at or now
        publication.leased_until = None
        publication.lease_owner = None
        publication.last_error = None
        publication.publication_payload = dict(payload)
        publication.updated_at = now
        await session.flush()
        await self._refresh_event_status(session, event.id)

    async def _mark_publication_failed(
        self, publication_id: uuid.UUID, exc: Exception, retry_at: datetime | None = None
    ) -> tuple[str, FanoutResult]:
        async with self.session_factory() as session:
            publication, event = await self._load_publication_event(session, publication_id)
            now = datetime.now(UTC)
            attempts = int(publication.attempts or 0)
            status = STATUS_DEAD_LETTER if attempts >= self.dead_letter_after_attempts else STATUS_FAILED
            publication.publication_status = status
            publication.leased_until = None
            publication.lease_owner = None
            publication.submitted_at = publication.submitted_at or now
            publication.next_attempt_at = retry_at or (
                now.replace(microsecond=0) + timedelta(seconds=self.retry_after_seconds)
            )
            publication.last_error = str(exc)[:500]
            publication.updated_at = now
            await session.flush()
            await self._refresh_event_status(session, event.id)
            await session.commit()
        MESSAGING_OUTBOX_PUBLICATIONS_TOTAL.labels(consumer_key=publication.consumer_key, status=status).inc()
        logger.warning(
            "messaging_outbox_publication_failed",
            publication_id=str(publication_id),
            consumer_key=publication.consumer_key,
            status=status,
            error_type=type(exc).__name__,
        )
        return status, FanoutResult(failed=1, reason=type(exc).__name__)

    async def _refresh_event_status(self, session: AsyncSession, event_id: uuid.UUID) -> None:
        result = await session.execute(
            select(MessagingOutboxPublicationModel.publication_status).where(
                MessagingOutboxPublicationModel.outbox_event_id == event_id
            )
        )
        statuses = {str(status) for status in result.scalars().all()}
        event = await session.get(MessagingOutboxEventModel, event_id)
        if event is None:
            return
        if statuses and statuses == {STATUS_PUBLISHED}:
            event.event_status = EVENT_STATUS_PUBLISHED
        elif statuses.intersection({STATUS_CLAIMED, STATUS_PUBLISHED}):
            event.event_status = EVENT_STATUS_PARTIAL
        elif statuses and statuses.issubset({STATUS_FAILED, STATUS_DEAD_LETTER}):
            event.event_status = EVENT_STATUS_FAILED
        else:
            event.event_status = EVENT_STATUS_PENDING
        event.updated_at = datetime.now(UTC)
        await session.flush()

    @staticmethod
    def _observe_fanout(consumer_key: str, *, created: int, skipped: int) -> None:
        if created:
            MESSAGING_FANOUT_RECIPIENTS_TOTAL.labels(consumer_key=consumer_key, status="created").inc(created)
        if skipped:
            MESSAGING_FANOUT_RECIPIENTS_TOTAL.labels(consumer_key=consumer_key, status="skipped").inc(skipped)


def _recipient_refs(payload: dict[str, Any]) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    for raw in payload.get("recipient_refs") or ():
        if not isinstance(raw, dict):
            continue
        recipient_type = str(raw.get("type") or "").strip()
        recipient_id = str(raw.get("id") or "").strip()
        if recipient_type and recipient_id:
            refs.append({"type": recipient_type, "id": recipient_id})
    return refs


def _explicit_customer_ids(audience_filter: dict[str, Any]) -> list[uuid.UUID]:
    ids: list[uuid.UUID] = []
    for raw in audience_filter.get("customer_account_ids") or ():
        parsed = _parse_uuid(str(raw))
        if parsed is not None:
            ids.append(parsed)
    return ids


def _site_notification_title(event_name: str) -> str:
    if event_name == "messaging.message.created":
        return "New message"
    if event_name == "messaging.conversation.created":
        return "New conversation"
    if event_name == "messaging.conversation.assigned":
        return "Conversation assigned"
    if event_name in {"messaging.conversation.closed", "messaging.conversation.reopened"}:
        return "Conversation updated"
    return "Notification"


def _conversation_action_url(payload: dict[str, Any]) -> str | None:
    public_id = str(payload.get("conversation_public_id") or "").strip()
    if not public_id:
        return None
    return f"/support/conversations/{public_id}"


def _build_subject(consumer_key: str, event_name: str, schema_version: int) -> str:
    return f"messaging.{consumer_key}.{event_name}.v{schema_version}"


def _parse_uuid(value: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(value)
    except (TypeError, ValueError):
        return None


def _normalize_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
