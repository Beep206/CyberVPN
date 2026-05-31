"""Messaging application service."""

from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.application.events.outbox import EventOutboxService, OutboxActorContext
from src.domain.entities.messaging import (
    BroadcastAudienceType,
    BroadcastCampaign,
    BroadcastCampaignStatus,
    MessagingConversation,
    MessagingConversationCategory,
    MessagingConversationClosedError,
    MessagingConversationNotFoundError,
    MessagingConversationStatus,
    MessagingForbiddenError,
    MessagingMessage,
    MessagingMessageReadState,
    MessagingMessageVisibility,
    MessagingParticipantType,
    MessagingPriority,
    MessagingSenderType,
    SiteNotificationDeliveryStatus,
    SiteNotificationRecipientType,
    customer_visible_messages,
)
from src.domain.events.messaging import (
    BROADCAST_CANCELLED,
    BROADCAST_CREATED,
    BROADCAST_OUTBOX_CONSUMERS,
    MESSAGING_CONVERSATION_ASSIGNED,
    MESSAGING_CONVERSATION_CLOSED,
    MESSAGING_CONVERSATION_CREATED,
    MESSAGING_CONVERSATION_REOPENED,
    MESSAGING_MESSAGE_CREATED,
    MESSAGING_MESSAGE_READ,
    MESSAGING_OUTBOX_CONSUMERS,
    NOTIFICATION_READ,
)
from src.domain.repositories.messaging_repository import (
    MessagingConversationListResult,
    MessagingMessageWriteResult,
    MessagingRepository,
    SiteNotificationDeliveryView,
    SiteNotificationListResult,
)
from src.domain.value_objects.messaging import build_message_idempotency_key


@dataclass(frozen=True, slots=True)
class AdminMessagingConversationUpdate:
    category: MessagingConversationCategory | None = None
    priority: MessagingPriority | None = None
    assigned_admin_id: UUID | None = None
    assigned_admin_id_set: bool = False


@dataclass(frozen=True, slots=True)
class MessagingSyncResult:
    cursor: str
    conversations: tuple[MessagingConversation, ...]
    notifications: tuple[SiteNotificationDeliveryView, ...]
    unread_conversations: int
    unread_notifications: int


class MessagingService:
    def __init__(self, repository: MessagingRepository, outbox: EventOutboxService | None = None) -> None:
        self._repository = repository
        self._outbox = outbox

    async def list_customer_conversations(
        self,
        *,
        customer_account_id: UUID,
        status: MessagingConversationStatus | None = None,
        cursor: str | None = None,
        limit: int = 50,
    ) -> MessagingConversationListResult:
        result = await self._repository.list_for_customer(
            customer_account_id=customer_account_id,
            status=status,
            cursor=cursor,
            limit=limit,
        )
        return MessagingConversationListResult(
            conversations=tuple(self._customer_view(conversation) for conversation in result.conversations),
            next_cursor=result.next_cursor,
        )

    async def get_customer_conversation(
        self,
        *,
        conversation_ref: str,
        customer_account_id: UUID,
    ) -> MessagingConversation:
        conversation = await self._get_conversation(conversation_ref)
        if conversation.customer_account_id != customer_account_id:
            raise MessagingConversationNotFoundError("Conversation not found")
        return self._customer_view(conversation)

    async def add_customer_message(
        self,
        *,
        conversation_ref: str,
        customer_account_id: UUID,
        body: str,
        client_message_id: str | None,
        header_idempotency_key: str | None,
    ) -> MessagingMessageWriteResult:
        conversation = await self.get_customer_conversation(
            conversation_ref=conversation_ref,
            customer_account_id=customer_account_id,
        )
        idempotency_key = build_message_idempotency_key(
            actor_type=MessagingSenderType.CUSTOMER.value,
            actor_id=customer_account_id,
            conversation_id=conversation.id,
            client_message_id=client_message_id,
            header_idempotency_key=header_idempotency_key,
        )
        result = await self._repository.add_message(
            public_id=self._new_message_public_id(),
            conversation_id=conversation.id,
            sender_type=MessagingSenderType.CUSTOMER,
            sender_id=customer_account_id,
            visibility=MessagingMessageVisibility.PUBLIC,
            body=body,
            client_message_id=client_message_id,
            idempotency_key=idempotency_key,
        )
        if result.created:
            await self._append_message_created_event(
                conversation=result.conversation,
                message=result.message,
                actor_context=OutboxActorContext(principal_type="customer", principal_id=str(customer_account_id)),
            )
        return MessagingMessageWriteResult(
            conversation=self._customer_view(result.conversation),
            message=result.message,
            created=result.created,
        )

    async def mark_customer_read(
        self,
        *,
        conversation_ref: str,
        customer_account_id: UUID,
        last_read_message_id: UUID | None,
    ):
        conversation = await self.get_customer_conversation(
            conversation_ref=conversation_ref,
            customer_account_id=customer_account_id,
        )
        read_state = await self._repository.mark_read(
            conversation_id=conversation.id,
            participant_type=MessagingParticipantType.CUSTOMER,
            participant_id=customer_account_id,
            last_read_message_id=last_read_message_id,
        )
        await self._append_conversation_read_event(
            conversation=conversation,
            read_state=read_state,
            actor_context=OutboxActorContext(principal_type="customer", principal_id=str(customer_account_id)),
        )
        return read_state

    async def list_customer_notifications(
        self,
        *,
        customer_account_id: UUID,
        cursor: str | None = None,
        limit: int = 50,
    ) -> SiteNotificationListResult:
        return await self._repository.list_site_notifications(
            recipient_type=SiteNotificationRecipientType.CUSTOMER,
            recipient_id=customer_account_id,
            cursor=cursor,
            limit=limit,
        )

    async def mark_customer_notifications_read(
        self,
        *,
        customer_account_id: UUID,
        notification_ids: tuple[UUID, ...],
        read_all_before: datetime | None,
    ) -> tuple[SiteNotificationDeliveryView, ...]:
        views = await self._repository.mark_site_notifications(
            recipient_type=SiteNotificationRecipientType.CUSTOMER,
            recipient_id=customer_account_id,
            notification_ids=notification_ids,
            read_all_before=read_all_before,
            status=SiteNotificationDeliveryStatus.READ,
        )
        for view in views:
            await self._append_notification_read_event(
                view=view,
                actor_context=OutboxActorContext(principal_type="customer", principal_id=str(customer_account_id)),
            )
        return views

    async def sync_customer_realtime(
        self,
        *,
        customer_account_id: UUID,
        cursor: str | None = None,
        limit: int = 50,
    ) -> MessagingSyncResult:
        _ = cursor
        conversations = await self.list_customer_conversations(customer_account_id=customer_account_id, limit=limit)
        notifications = await self.list_customer_notifications(customer_account_id=customer_account_id, limit=limit)
        return MessagingSyncResult(
            cursor=self._sync_cursor(),
            conversations=conversations.conversations,
            notifications=notifications.notifications,
            unread_conversations=sum(
                self.unread_count(conversation, MessagingSenderType.CUSTOMER)
                for conversation in conversations.conversations
            ),
            unread_notifications=await self._repository.count_unread_site_notifications(
                recipient_type=SiteNotificationRecipientType.CUSTOMER,
                recipient_id=customer_account_id,
            ),
        )

    async def list_admin_conversations(
        self,
        *,
        status: MessagingConversationStatus | None = None,
        category: MessagingConversationCategory | None = None,
        priority: MessagingPriority | None = None,
        assigned_admin_id: UUID | None = None,
        customer_account_id: UUID | None = None,
        query: str | None = None,
        cursor: str | None = None,
        limit: int = 50,
    ) -> MessagingConversationListResult:
        return await self._repository.list_for_admin(
            status=status,
            category=category,
            priority=priority,
            assigned_admin_id=assigned_admin_id,
            customer_account_id=customer_account_id,
            query=query,
            cursor=cursor,
            limit=limit,
        )

    async def get_admin_conversation(self, *, conversation_ref: str) -> MessagingConversation:
        return await self._get_conversation(conversation_ref)

    async def create_admin_conversation(
        self,
        *,
        admin_id: UUID,
        customer_account_id: UUID,
        subject: str,
        category: MessagingConversationCategory,
        priority: MessagingPriority,
        initial_message_body: str,
        initial_message_client_id: str | None,
        header_idempotency_key: str | None,
        assigned_admin_id: UUID | None = None,
        related_support_ticket_id: UUID | None = None,
    ) -> MessagingConversation:
        conversation_id = uuid4()
        idempotency_key = build_message_idempotency_key(
            actor_type=MessagingSenderType.ADMIN.value,
            actor_id=admin_id,
            conversation_id=conversation_id,
            client_message_id=initial_message_client_id,
            header_idempotency_key=header_idempotency_key,
        )
        conversation = await self._repository.create_conversation(
            conversation_id=conversation_id,
            public_id=self._new_conversation_public_id(),
            customer_account_id=customer_account_id,
            created_by_admin_id=admin_id,
            assigned_admin_id=assigned_admin_id or admin_id,
            category=category,
            priority=priority,
            subject=subject,
            initial_message_public_id=self._new_message_public_id(),
            initial_message_body=initial_message_body,
            initial_message_client_id=initial_message_client_id,
            initial_message_idempotency_key=idempotency_key,
            related_support_ticket_id=related_support_ticket_id,
        )
        await self._append_conversation_created_event(
            conversation=conversation,
            actor_context=OutboxActorContext(principal_type="admin", principal_id=str(admin_id)),
        )
        initial_message = next(
            (message for message in conversation.messages if message.id == conversation.last_message_id),
            None,
        )
        if initial_message is not None:
            await self._append_message_created_event(
                conversation=conversation,
                message=initial_message,
                actor_context=OutboxActorContext(principal_type="admin", principal_id=str(admin_id)),
            )
        return conversation

    async def add_admin_message(
        self,
        *,
        conversation_ref: str,
        admin_id: UUID,
        body: str,
        client_message_id: str | None,
        header_idempotency_key: str | None,
        visibility: MessagingMessageVisibility,
    ) -> MessagingMessageWriteResult:
        conversation = await self.get_admin_conversation(conversation_ref=conversation_ref)
        idempotency_key = build_message_idempotency_key(
            actor_type=MessagingSenderType.ADMIN.value,
            actor_id=admin_id,
            conversation_id=conversation.id,
            client_message_id=client_message_id,
            header_idempotency_key=header_idempotency_key,
        )
        result = await self._repository.add_message(
            public_id=self._new_message_public_id(),
            conversation_id=conversation.id,
            sender_type=MessagingSenderType.ADMIN,
            sender_id=admin_id,
            visibility=visibility,
            body=body,
            client_message_id=client_message_id,
            idempotency_key=idempotency_key,
        )
        if result.created:
            await self._append_message_created_event(
                conversation=result.conversation,
                message=result.message,
                actor_context=OutboxActorContext(principal_type="admin", principal_id=str(admin_id)),
            )
        return result

    async def update_admin_conversation(
        self,
        *,
        conversation_ref: str,
        update: AdminMessagingConversationUpdate,
    ) -> MessagingConversation:
        conversation = await self.get_admin_conversation(conversation_ref=conversation_ref)
        updated = await self._repository.update_conversation(
            conversation_id=conversation.id,
            category=update.category,
            priority=update.priority,
            assigned_admin_id=update.assigned_admin_id,
            assigned_admin_id_set=update.assigned_admin_id_set,
        )
        if update.assigned_admin_id_set:
            await self._append_conversation_assigned_event(conversation=updated)
        return updated

    async def close_admin_conversation(self, *, conversation_ref: str) -> MessagingConversation:
        conversation = await self.get_admin_conversation(conversation_ref=conversation_ref)
        if conversation.status != MessagingConversationStatus.OPEN:
            raise MessagingConversationClosedError("Conversation is not open")
        updated = await self._repository.update_conversation(
            conversation_id=conversation.id,
            status=MessagingConversationStatus.CLOSED,
            closed_at=datetime.now(UTC),
        )
        await self._append_conversation_status_event(
            event_name=MESSAGING_CONVERSATION_CLOSED,
            conversation=updated,
        )
        return updated

    async def reopen_admin_conversation(self, *, conversation_ref: str) -> MessagingConversation:
        conversation = await self.get_admin_conversation(conversation_ref=conversation_ref)
        if conversation.status == MessagingConversationStatus.OPEN:
            return conversation
        if conversation.status not in {MessagingConversationStatus.CLOSED, MessagingConversationStatus.LOCKED}:
            raise MessagingForbiddenError("Conversation cannot be reopened")
        updated = await self._repository.update_conversation(
            conversation_id=conversation.id,
            status=MessagingConversationStatus.OPEN,
        )
        await self._append_conversation_status_event(
            event_name=MESSAGING_CONVERSATION_REOPENED,
            conversation=updated,
        )
        return updated

    async def create_broadcast_campaign(
        self,
        *,
        admin_id: UUID,
        name: str,
        audience_type: BroadcastAudienceType,
        audience_filter: dict[str, object],
        title: str,
        body: str,
        action_url: str | None = None,
        scheduled_at: datetime | None = None,
    ) -> BroadcastCampaign:
        self._assert_safe_broadcast_audience(audience_type=audience_type, audience_filter=audience_filter)
        campaign = await self._repository.create_broadcast_campaign(
            public_id=self._new_broadcast_public_id(),
            name=name,
            audience_type=audience_type,
            audience_filter=audience_filter,
            title=title,
            body=body,
            action_url=action_url,
            scheduled_at=scheduled_at,
            created_by_admin_id=admin_id,
            status=BroadcastCampaignStatus.SCHEDULED if scheduled_at is not None else BroadcastCampaignStatus.DRAFT,
        )
        await self._append_broadcast_created_event(campaign=campaign, admin_id=admin_id)
        return campaign

    async def cancel_broadcast_campaign(
        self,
        *,
        campaign_ref: str,
        admin_id: UUID,
    ) -> BroadcastCampaign:
        campaign = await self._repository.cancel_broadcast_campaign(campaign_ref=campaign_ref)
        await self._append_broadcast_cancelled_event(campaign=campaign, admin_id=admin_id)
        return campaign

    async def _append_outbox_event(
        self,
        *,
        event_name: str,
        aggregate_type: str,
        aggregate_id: UUID | str,
        partition_key: UUID | str,
        event_payload: dict[str, object],
        actor_context: OutboxActorContext | None = None,
        consumer_keys: tuple[str, ...] = MESSAGING_OUTBOX_CONSUMERS,
        event_key: str | None = None,
        occurred_at: datetime | None = None,
    ) -> None:
        if self._outbox is None:
            return
        await self._outbox.append_event(
            event_name=event_name,
            aggregate_type=aggregate_type,
            aggregate_id=str(aggregate_id),
            partition_key=str(partition_key),
            event_payload=event_payload,
            actor_context=actor_context,
            source_context={"bounded_context": "messaging"},
            consumer_keys=consumer_keys,
            event_key=event_key,
            occurred_at=occurred_at,
        )

    async def _append_conversation_created_event(
        self,
        *,
        conversation: MessagingConversation,
        actor_context: OutboxActorContext,
    ) -> None:
        await self._append_outbox_event(
            event_name=MESSAGING_CONVERSATION_CREATED,
            aggregate_type="messaging_conversation",
            aggregate_id=conversation.id,
            partition_key=conversation.customer_account_id,
            event_payload={
                "conversation_id": str(conversation.id),
                "conversation_public_id": conversation.public_id,
                "customer_account_id": str(conversation.customer_account_id),
                "category": conversation.category.value,
                "priority": conversation.priority.value,
                "status": conversation.status.value,
                "assigned_admin_id": _uuid_to_str(conversation.assigned_admin_id),
                "recipient_refs": _conversation_recipient_refs(conversation),
            },
            actor_context=actor_context,
            event_key=f"messaging.conversation.created:{conversation.id}",
            occurred_at=conversation.created_at,
        )

    async def _append_message_created_event(
        self,
        *,
        conversation: MessagingConversation,
        message: MessagingMessage,
        actor_context: OutboxActorContext,
    ) -> None:
        consumer_keys = (
            MESSAGING_OUTBOX_CONSUMERS
            if message.visibility == MessagingMessageVisibility.PUBLIC
            else ("messaging_audit_projection",)
        )
        await self._append_outbox_event(
            event_name=MESSAGING_MESSAGE_CREATED,
            aggregate_type="messaging_message",
            aggregate_id=message.id,
            partition_key=conversation.customer_account_id,
            event_payload={
                "conversation_id": str(conversation.id),
                "conversation_public_id": conversation.public_id,
                "message_id": str(message.id),
                "message_public_id": message.public_id,
                "sender_type": message.sender_type.value,
                "sender_id": _uuid_to_str(message.sender_id),
                "visibility": message.visibility.value,
                "body_included": False,
                "recipient_refs": _conversation_recipient_refs(conversation),
            },
            actor_context=actor_context,
            consumer_keys=consumer_keys,
            event_key=f"messaging.message.created:{message.id}",
            occurred_at=message.created_at,
        )

    async def _append_conversation_read_event(
        self,
        *,
        conversation: MessagingConversation,
        read_state: MessagingMessageReadState,
        actor_context: OutboxActorContext,
    ) -> None:
        await self._append_outbox_event(
            event_name=MESSAGING_MESSAGE_READ,
            aggregate_type="messaging_conversation",
            aggregate_id=conversation.id,
            partition_key=conversation.customer_account_id,
            event_payload={
                "conversation_id": str(conversation.id),
                "participant_type": read_state.participant_type.value,
                "participant_id": str(read_state.participant_id),
                "last_read_message_id": _uuid_to_str(read_state.last_read_message_id),
                "recipient_refs": _conversation_recipient_refs(conversation),
            },
            actor_context=actor_context,
            event_key=f"messaging.message.read:{read_state.id}:{uuid.uuid4().hex}",
            occurred_at=read_state.last_read_at,
        )

    async def _append_conversation_assigned_event(self, *, conversation: MessagingConversation) -> None:
        await self._append_outbox_event(
            event_name=MESSAGING_CONVERSATION_ASSIGNED,
            aggregate_type="messaging_conversation",
            aggregate_id=conversation.id,
            partition_key=conversation.customer_account_id,
            event_payload={
                "conversation_id": str(conversation.id),
                "assigned_admin_id": _uuid_to_str(conversation.assigned_admin_id),
                "recipient_refs": _conversation_recipient_refs(conversation),
            },
            event_key=f"messaging.conversation.assigned:{conversation.id}:{uuid.uuid4().hex}",
            occurred_at=conversation.updated_at,
        )

    async def _append_conversation_status_event(
        self,
        *,
        event_name: str,
        conversation: MessagingConversation,
    ) -> None:
        await self._append_outbox_event(
            event_name=event_name,
            aggregate_type="messaging_conversation",
            aggregate_id=conversation.id,
            partition_key=conversation.customer_account_id,
            event_payload={
                "conversation_id": str(conversation.id),
                "status": conversation.status.value,
                "recipient_refs": _conversation_recipient_refs(conversation),
            },
            event_key=f"{event_name}:{conversation.id}:{uuid.uuid4().hex}",
            occurred_at=conversation.updated_at,
        )

    async def _append_notification_read_event(
        self,
        *,
        view: SiteNotificationDeliveryView,
        actor_context: OutboxActorContext,
    ) -> None:
        if view.delivery.recipient_id is None:
            return
        await self._append_outbox_event(
            event_name=NOTIFICATION_READ,
            aggregate_type="site_notification",
            aggregate_id=view.notification.id,
            partition_key=view.delivery.recipient_id,
            event_payload={
                "notification_id": str(view.notification.id),
                "delivery_id": str(view.delivery.id),
                "recipient_type": view.delivery.recipient_type.value,
                "recipient_id": str(view.delivery.recipient_id),
                "status": view.delivery.status.value,
                "recipient_refs": [{"type": view.delivery.recipient_type.value, "id": str(view.delivery.recipient_id)}],
            },
            actor_context=actor_context,
            event_key=f"notification.read:{view.delivery.id}:{uuid.uuid4().hex}",
            occurred_at=view.delivery.read_at or view.delivery.updated_at,
        )

    async def _append_broadcast_created_event(self, *, campaign: BroadcastCampaign, admin_id: UUID) -> None:
        await self._append_outbox_event(
            event_name=BROADCAST_CREATED,
            aggregate_type="broadcast_campaign",
            aggregate_id=campaign.id,
            partition_key=campaign.id,
            event_payload={
                "campaign_id": str(campaign.id),
                "campaign_public_id": campaign.public_id,
                "audience_type": campaign.audience_type.value,
                "status": campaign.status.value,
                "scheduled_at": campaign.scheduled_at.isoformat() if campaign.scheduled_at is not None else None,
            },
            actor_context=OutboxActorContext(principal_type="admin", principal_id=str(admin_id)),
            consumer_keys=BROADCAST_OUTBOX_CONSUMERS,
            event_key=f"broadcast.created:{campaign.id}",
            occurred_at=campaign.created_at,
        )

    async def _append_broadcast_cancelled_event(self, *, campaign: BroadcastCampaign, admin_id: UUID) -> None:
        await self._append_outbox_event(
            event_name=BROADCAST_CANCELLED,
            aggregate_type="broadcast_campaign",
            aggregate_id=campaign.id,
            partition_key=campaign.id,
            event_payload={
                "campaign_id": str(campaign.id),
                "campaign_public_id": campaign.public_id,
                "status": campaign.status.value,
                "cancelled_at": campaign.cancelled_at.isoformat() if campaign.cancelled_at is not None else None,
            },
            actor_context=OutboxActorContext(principal_type="admin", principal_id=str(admin_id)),
            consumer_keys=("messaging_audit_projection",),
            event_key=f"broadcast.cancelled:{campaign.id}:{uuid.uuid4().hex}",
            occurred_at=campaign.cancelled_at or campaign.updated_at,
        )

    async def _get_conversation(self, conversation_ref: str) -> MessagingConversation:
        conversation = await self._repository.get_conversation(conversation_ref)
        if conversation is None:
            raise MessagingConversationNotFoundError("Conversation not found")
        return conversation

    @staticmethod
    def _customer_view(conversation: MessagingConversation) -> MessagingConversation:
        return replace(conversation, messages=customer_visible_messages(conversation.messages))

    @staticmethod
    def unread_count(conversation: MessagingConversation, own_sender_type: MessagingSenderType) -> int:
        read_at = None
        read_message_id = None
        for read_state in conversation.read_states:
            if read_state.participant_type.value == own_sender_type.value:
                read_at = read_state.last_read_at
                read_message_id = read_state.last_read_message_id
                break
        count = 0
        for message in conversation.messages:
            if message.visibility != MessagingMessageVisibility.PUBLIC:
                continue
            if message.sender_type == own_sender_type:
                continue
            if read_message_id is not None and message.id == read_message_id:
                count = 0
                continue
            if read_at is None or message.created_at > read_at:
                count += 1
        return count

    @staticmethod
    def _assert_safe_broadcast_audience(
        *,
        audience_type: BroadcastAudienceType,
        audience_filter: dict[str, object],
    ) -> None:
        if audience_type == BroadcastAudienceType.EXPLICIT_CUSTOMERS:
            customer_ids = audience_filter.get("customer_account_ids")
            if not isinstance(customer_ids, list) or not customer_ids:
                raise ValueError("explicit_customers audience requires customer_account_ids")
        if audience_type == BroadcastAudienceType.CUSTOMER_SEGMENT and not audience_filter:
            raise ValueError("customer_segment audience requires a structured audience_filter")

    @staticmethod
    def _new_conversation_public_id() -> str:
        return f"conv_{secrets.token_urlsafe(8).replace('-', '').replace('_', '').lower()[:10]}"

    @staticmethod
    def _new_message_public_id() -> str:
        return f"msg_{secrets.token_urlsafe(8).replace('-', '').replace('_', '').lower()[:10]}"

    @staticmethod
    def _new_broadcast_public_id() -> str:
        return f"bc_{secrets.token_urlsafe(8).replace('-', '').replace('_', '').lower()[:10]}"

    @staticmethod
    def _sync_cursor() -> str:
        now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        return f"sync:{now}"


def _uuid_to_str(value: UUID | None) -> str | None:
    return str(value) if value is not None else None


def _conversation_recipient_refs(conversation: MessagingConversation) -> list[dict[str, str]]:
    refs = [{"type": "customer", "id": str(conversation.customer_account_id)}]
    if conversation.assigned_admin_id is not None:
        refs.append({"type": "admin", "id": str(conversation.assigned_admin_id)})
    return refs
