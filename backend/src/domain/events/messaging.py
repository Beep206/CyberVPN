"""Domain event names and payload builders for messaging."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

MESSAGING_CONVERSATION_CREATED = "messaging.conversation.created"
MESSAGING_MESSAGE_CREATED = "messaging.message.created"
MESSAGING_MESSAGE_READ = "messaging.message.read"
MESSAGING_CONVERSATION_ASSIGNED = "messaging.conversation.assigned"
MESSAGING_CONVERSATION_CLOSED = "messaging.conversation.closed"
MESSAGING_CONVERSATION_REOPENED = "messaging.conversation.reopened"
NOTIFICATION_CREATED = "notification.created"
NOTIFICATION_READ = "notification.read"
NOTIFICATION_DISMISSED = "notification.dismissed"
BROADCAST_CREATED = "broadcast.created"
BROADCAST_CANCELLED = "broadcast.cancelled"
BROADCAST_RECIPIENT_CREATED = "broadcast.recipient.created"

MESSAGING_OUTBOX_CONSUMERS = (
    "messaging_realtime_projection",
    "site_notification_fanout",
    "messaging_audit_projection",
)
BROADCAST_OUTBOX_CONSUMERS = (
    "broadcast_fanout_worker",
    "messaging_audit_projection",
)
MESSAGING_EVENT_FAMILIES = {
    "messaging": (
        MESSAGING_CONVERSATION_CREATED,
        MESSAGING_MESSAGE_CREATED,
        MESSAGING_MESSAGE_READ,
        MESSAGING_CONVERSATION_ASSIGNED,
        MESSAGING_CONVERSATION_CLOSED,
        MESSAGING_CONVERSATION_REOPENED,
    ),
    "notification": (
        NOTIFICATION_CREATED,
        NOTIFICATION_READ,
        NOTIFICATION_DISMISSED,
    ),
    "broadcast": (
        BROADCAST_CREATED,
        BROADCAST_CANCELLED,
        BROADCAST_RECIPIENT_CREATED,
    ),
}


@dataclass(frozen=True, slots=True)
class MessagingDomainEvent:
    event_name: str
    aggregate_type: str
    aggregate_id: str
    payload: dict[str, object]
    occurred_at: datetime
    idempotency_key: str
    consumer_keys: tuple[str, ...] = field(default_factory=lambda: MESSAGING_OUTBOX_CONSUMERS)


def message_created_payload(
    *,
    conversation_id: UUID,
    message_id: UUID,
    sender_type: str,
    sender_id: UUID | None,
    visibility: str,
    recipient_refs: tuple[dict[str, str], ...],
) -> dict[str, object]:
    return {
        "conversation_id": str(conversation_id),
        "message_id": str(message_id),
        "sender_type": sender_type,
        "sender_id": str(sender_id) if sender_id is not None else None,
        "visibility": visibility,
        "recipient_refs": list(recipient_refs),
        "body_included": False,
    }
