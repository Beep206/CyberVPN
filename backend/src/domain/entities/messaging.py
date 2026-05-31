"""Messaging bounded-context domain model and invariants."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class MessagingDomainError(Exception):
    """Base messaging domain error."""


class MessagingForbiddenError(MessagingDomainError):
    """Raised when an actor attempts a forbidden messaging operation."""


class MessagingConversationNotFoundError(MessagingDomainError):
    """Raised when a conversation is absent or outside caller scope."""


class MessagingConversationClosedError(MessagingDomainError):
    """Raised when an actor writes to a non-writable conversation."""


class SiteNotificationNotFoundError(MessagingDomainError):
    """Raised when a site notification is absent or outside caller scope."""


class BroadcastCampaignNotFoundError(MessagingDomainError):
    """Raised when a broadcast campaign is absent or outside caller scope."""


class MessagingConversationStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"
    ARCHIVED = "archived"
    LOCKED = "locked"


class MessagingResponseState(StrEnum):
    NONE = "none"
    WAITING_CUSTOMER = "waiting_customer"
    WAITING_ADMIN = "waiting_admin"


class MessagingConversationCategory(StrEnum):
    SUPPORT = "support"
    BILLING = "billing"
    SUBSCRIPTION = "subscription"
    SECURITY = "security"
    SYSTEM = "system"
    OTHER = "other"


class MessagingPriority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class MessagingParticipantType(StrEnum):
    CUSTOMER = "customer"
    ADMIN = "admin"
    TEAM = "team"
    SYSTEM = "system"


class MessagingParticipantRole(StrEnum):
    CUSTOMER = "customer"
    CREATOR = "creator"
    ASSIGNEE = "assignee"
    WATCHER = "watcher"
    SYSTEM = "system"


class MessagingSenderType(StrEnum):
    CUSTOMER = "customer"
    ADMIN = "admin"
    SYSTEM = "system"


class MessagingMessageVisibility(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"


class MessagingBodyFormat(StrEnum):
    PLAIN_TEXT = "plain_text"


class SiteNotificationType(StrEnum):
    MESSAGE = "message"
    SYSTEM = "system"
    BILLING = "billing"
    SUBSCRIPTION = "subscription"
    SECURITY = "security"
    BROADCAST = "broadcast"


class SiteNotificationSeverity(StrEnum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    CRITICAL = "critical"


class SiteNotificationRecipientType(StrEnum):
    CUSTOMER = "customer"
    ADMIN = "admin"
    TEAM = "team"


class SiteNotificationDeliveryChannel(StrEnum):
    SITE = "site"
    TELEGRAM = "telegram"
    EMAIL = "email"
    PUSH = "push"


class SiteNotificationDeliveryStatus(StrEnum):
    PENDING = "pending"
    DELIVERED = "delivered"
    READ = "read"
    DISMISSED = "dismissed"
    FAILED = "failed"
    EXPIRED = "expired"


class BroadcastCampaignStatus(StrEnum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    SENDING = "sending"
    SENT = "sent"
    CANCELLED = "cancelled"
    FAILED = "failed"


class BroadcastAudienceType(StrEnum):
    ALL_CUSTOMERS = "all_customers"
    CUSTOMER_SEGMENT = "customer_segment"
    EXPLICIT_CUSTOMERS = "explicit_customers"
    ADMINS = "admins"


class BroadcastRecipientStatus(StrEnum):
    PENDING = "pending"
    CREATED = "created"
    SKIPPED = "skipped"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PresenceStatus(StrEnum):
    ONLINE = "online"
    AWAY = "away"
    OFFLINE = "offline"


@dataclass(frozen=True, slots=True)
class MessagingConversationParticipant:
    id: UUID
    conversation_id: UUID
    participant_type: MessagingParticipantType
    participant_id: UUID | None
    role: MessagingParticipantRole
    can_read: bool
    can_write: bool
    joined_at: datetime
    left_at: datetime | None = None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class MessagingMessage:
    id: UUID
    public_id: str
    conversation_id: UUID
    sender_type: MessagingSenderType
    sender_id: UUID | None
    visibility: MessagingMessageVisibility
    body: str
    body_format: MessagingBodyFormat
    idempotency_key: str
    created_at: datetime
    updated_at: datetime
    client_message_id: str | None = None
    reply_to_message_id: UUID | None = None
    redacted_at: datetime | None = None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class MessagingMessageReadState:
    id: UUID
    conversation_id: UUID
    participant_type: MessagingParticipantType
    participant_id: UUID
    last_read_at: datetime
    updated_at: datetime
    last_read_message_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class MessagingConversation:
    id: UUID
    public_id: str
    customer_account_id: UUID
    status: MessagingConversationStatus
    response_state: MessagingResponseState
    category: MessagingConversationCategory
    priority: MessagingPriority
    subject: str
    created_by_admin_id: UUID | None
    assigned_admin_id: UUID | None
    metadata: dict[str, object]
    created_at: datetime
    updated_at: datetime
    related_support_ticket_id: UUID | None = None
    last_message_id: UUID | None = None
    last_message_at: datetime | None = None
    closed_at: datetime | None = None
    participants: tuple[MessagingConversationParticipant, ...] = field(default_factory=tuple)
    messages: tuple[MessagingMessage, ...] = field(default_factory=tuple)
    read_states: tuple[MessagingMessageReadState, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class SiteNotification:
    id: UUID
    notification_type: SiteNotificationType
    severity: SiteNotificationSeverity
    title: str
    created_by_actor_type: str
    payload: dict[str, object]
    created_at: datetime
    updated_at: datetime
    body: str | None = None
    action_url: str | None = None
    aggregate_type: str | None = None
    aggregate_id: str | None = None
    conversation_id: UUID | None = None
    message_id: UUID | None = None
    broadcast_campaign_id: UUID | None = None
    created_by_actor_id: UUID | None = None
    expires_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class SiteNotificationDelivery:
    id: UUID
    notification_id: UUID
    recipient_type: SiteNotificationRecipientType
    delivery_channel: SiteNotificationDeliveryChannel
    status: SiteNotificationDeliveryStatus
    attempts: int
    created_at: datetime
    updated_at: datetime
    recipient_id: UUID | None = None
    delivered_at: datetime | None = None
    read_at: datetime | None = None
    dismissed_at: datetime | None = None
    last_error: str | None = None


@dataclass(frozen=True, slots=True)
class BroadcastCampaign:
    id: UUID
    public_id: str
    name: str
    status: BroadcastCampaignStatus
    audience_type: BroadcastAudienceType
    audience_filter: dict[str, object]
    title: str
    body: str
    created_by_admin_id: UUID
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, object]
    template_key: str | None = None
    action_url: str | None = None
    scheduled_at: datetime | None = None
    approved_by_admin_id: UUID | None = None
    cancelled_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class BroadcastCampaignRecipient:
    id: UUID
    campaign_id: UUID
    recipient_type: SiteNotificationRecipientType
    recipient_id: UUID
    status: BroadcastRecipientStatus
    materialized_at: datetime
    created_at: datetime
    updated_at: datetime
    site_notification_id: UUID | None = None
    skip_reason: str | None = None
    failure_reason: str | None = None


@dataclass(frozen=True, slots=True)
class MessagingPresenceProjection:
    participant_type: MessagingParticipantType
    participant_id: UUID
    status: PresenceStatus
    observed_at: datetime
    connection_count: int = 0


def assert_customer_cannot_start_conversation() -> None:
    raise MessagingForbiddenError("Customer cannot start a private messaging conversation")


def assert_message_write_allowed(
    *,
    conversation: MessagingConversation,
    sender_type: MessagingSenderType,
    visibility: MessagingMessageVisibility,
) -> None:
    if conversation.status != MessagingConversationStatus.OPEN:
        raise MessagingConversationClosedError("Conversation is not open for writing")
    if visibility == MessagingMessageVisibility.INTERNAL and sender_type not in {
        MessagingSenderType.ADMIN,
        MessagingSenderType.SYSTEM,
    }:
        raise MessagingForbiddenError("Internal notes can only be written by admin or system actors")


def assert_message_sender_attribution(
    *,
    sender_type: MessagingSenderType,
    sender_id: UUID | None,
) -> None:
    if sender_type in {MessagingSenderType.CUSTOMER, MessagingSenderType.ADMIN} and sender_id is None:
        raise MessagingForbiddenError("Customer and admin messages require sender attribution")


def response_state_after_public_message(sender_type: MessagingSenderType) -> MessagingResponseState:
    if sender_type == MessagingSenderType.CUSTOMER:
        return MessagingResponseState.WAITING_ADMIN
    if sender_type == MessagingSenderType.ADMIN:
        return MessagingResponseState.WAITING_CUSTOMER
    return MessagingResponseState.NONE


def customer_visible_messages(messages: tuple[MessagingMessage, ...]) -> tuple[MessagingMessage, ...]:
    return tuple(message for message in messages if message.visibility == MessagingMessageVisibility.PUBLIC)
