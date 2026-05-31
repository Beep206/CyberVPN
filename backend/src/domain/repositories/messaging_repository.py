"""Messaging repository contract."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.domain.entities.messaging import (
    BroadcastAudienceType,
    BroadcastCampaign,
    BroadcastCampaignRecipient,
    BroadcastCampaignStatus,
    BroadcastRecipientStatus,
    MessagingBodyFormat,
    MessagingConversation,
    MessagingConversationCategory,
    MessagingConversationStatus,
    MessagingMessage,
    MessagingMessageReadState,
    MessagingMessageVisibility,
    MessagingParticipantType,
    MessagingPriority,
    MessagingSenderType,
    SiteNotification,
    SiteNotificationDelivery,
    SiteNotificationDeliveryChannel,
    SiteNotificationDeliveryStatus,
    SiteNotificationRecipientType,
    SiteNotificationSeverity,
    SiteNotificationType,
)


@dataclass(frozen=True, slots=True)
class MessagingConversationListResult:
    conversations: tuple[MessagingConversation, ...]
    next_cursor: str | None = None


@dataclass(frozen=True, slots=True)
class MessagingMessageWriteResult:
    conversation: MessagingConversation
    message: MessagingMessage
    created: bool


@dataclass(frozen=True, slots=True)
class SiteNotificationWriteResult:
    notification: SiteNotification
    delivery: SiteNotificationDelivery
    created: bool


@dataclass(frozen=True, slots=True)
class SiteNotificationDeliveryView:
    notification: SiteNotification
    delivery: SiteNotificationDelivery


@dataclass(frozen=True, slots=True)
class SiteNotificationListResult:
    notifications: tuple[SiteNotificationDeliveryView, ...]
    next_cursor: str | None = None


class MessagingRepository:
    async def create_conversation(
        self,
        *,
        conversation_id: UUID | None = None,
        public_id: str,
        customer_account_id: UUID,
        created_by_admin_id: UUID | None,
        assigned_admin_id: UUID | None,
        category: MessagingConversationCategory,
        priority: MessagingPriority,
        subject: str,
        initial_message_public_id: str,
        initial_message_body: str,
        initial_message_client_id: str | None,
        initial_message_idempotency_key: str,
        related_support_ticket_id: UUID | None = None,
        metadata: dict[str, object] | None = None,
        now: datetime | None = None,
    ) -> MessagingConversation:
        raise NotImplementedError

    async def get_conversation(self, conversation_ref: str) -> MessagingConversation | None:
        raise NotImplementedError

    async def list_for_customer(
        self,
        *,
        customer_account_id: UUID,
        status: MessagingConversationStatus | None = None,
        cursor: str | None = None,
        limit: int = 50,
    ) -> MessagingConversationListResult:
        raise NotImplementedError

    async def list_for_admin(
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
        raise NotImplementedError

    async def add_message(
        self,
        *,
        public_id: str,
        conversation_id: UUID,
        sender_type: MessagingSenderType,
        sender_id: UUID | None,
        visibility: MessagingMessageVisibility,
        body: str,
        client_message_id: str | None,
        idempotency_key: str,
        body_format: MessagingBodyFormat = MessagingBodyFormat.PLAIN_TEXT,
        reply_to_message_id: UUID | None = None,
        metadata: dict[str, object] | None = None,
        now: datetime | None = None,
    ) -> MessagingMessageWriteResult:
        raise NotImplementedError

    async def mark_read(
        self,
        *,
        conversation_id: UUID,
        participant_type: MessagingParticipantType,
        participant_id: UUID,
        last_read_message_id: UUID | None,
        now: datetime | None = None,
    ) -> MessagingMessageReadState:
        raise NotImplementedError

    async def update_conversation(
        self,
        *,
        conversation_id: UUID,
        status: MessagingConversationStatus | None = None,
        category: MessagingConversationCategory | None = None,
        priority: MessagingPriority | None = None,
        assigned_admin_id: UUID | None = None,
        assigned_admin_id_set: bool = False,
        closed_at: datetime | None = None,
        now: datetime | None = None,
    ) -> MessagingConversation:
        raise NotImplementedError

    async def create_site_notification(
        self,
        *,
        notification_type: SiteNotificationType,
        severity: SiteNotificationSeverity,
        title: str,
        recipient_type: SiteNotificationRecipientType,
        recipient_id: UUID | None,
        delivery_channel: SiteNotificationDeliveryChannel = SiteNotificationDeliveryChannel.SITE,
        body: str | None = None,
        action_url: str | None = None,
        aggregate_type: str | None = None,
        aggregate_id: str | None = None,
        conversation_id: UUID | None = None,
        message_id: UUID | None = None,
        broadcast_campaign_id: UUID | None = None,
        created_by_actor_type: str = "system",
        created_by_actor_id: UUID | None = None,
        payload: dict[str, object] | None = None,
        expires_at: datetime | None = None,
        now: datetime | None = None,
    ) -> SiteNotificationWriteResult:
        raise NotImplementedError

    async def list_site_notifications(
        self,
        *,
        recipient_type: SiteNotificationRecipientType,
        recipient_id: UUID,
        cursor: str | None = None,
        limit: int = 50,
    ) -> SiteNotificationListResult:
        raise NotImplementedError

    async def mark_site_notifications(
        self,
        *,
        recipient_type: SiteNotificationRecipientType,
        recipient_id: UUID,
        notification_ids: tuple[UUID, ...],
        read_all_before: datetime | None,
        status: SiteNotificationDeliveryStatus,
        now: datetime | None = None,
    ) -> tuple[SiteNotificationDeliveryView, ...]:
        raise NotImplementedError

    async def count_unread_site_notifications(
        self,
        *,
        recipient_type: SiteNotificationRecipientType,
        recipient_id: UUID,
    ) -> int:
        raise NotImplementedError

    async def create_broadcast_campaign(
        self,
        *,
        public_id: str,
        name: str,
        audience_type: BroadcastAudienceType,
        audience_filter: dict[str, object],
        title: str,
        body: str,
        created_by_admin_id: UUID,
        status: BroadcastCampaignStatus = BroadcastCampaignStatus.DRAFT,
        template_key: str | None = None,
        action_url: str | None = None,
        scheduled_at: datetime | None = None,
        metadata: dict[str, object] | None = None,
        now: datetime | None = None,
    ) -> BroadcastCampaign:
        raise NotImplementedError

    async def cancel_broadcast_campaign(
        self,
        *,
        campaign_ref: str,
        cancelled_at: datetime | None = None,
    ) -> BroadcastCampaign:
        raise NotImplementedError

    async def add_broadcast_recipient(
        self,
        *,
        campaign_id: UUID,
        recipient_type: SiteNotificationRecipientType,
        recipient_id: UUID,
        status: BroadcastRecipientStatus = BroadcastRecipientStatus.PENDING,
        site_notification_id: UUID | None = None,
        skip_reason: str | None = None,
        failure_reason: str | None = None,
        now: datetime | None = None,
    ) -> BroadcastCampaignRecipient:
        raise NotImplementedError
