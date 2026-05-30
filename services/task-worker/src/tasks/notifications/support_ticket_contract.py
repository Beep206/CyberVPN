"""Support ticket Telegram notification contract."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from src.models.notification_queue import NotificationQueueModel
from src.utils.constants import NOTIFICATION_TYPE_SUPPORT_TICKET_UPDATE, STATUS_PENDING
from src.utils.formatting import support_ticket_update

SupportTicketNotificationEventType = Literal[
    "public_reply_added",
    "status_changed",
    "closed",
    "reopened",
]

SUPPORT_TICKET_NOTIFICATION_EVENT_TYPES: frozenset[SupportTicketNotificationEventType] = frozenset(
    {
        "public_reply_added",
        "status_changed",
        "closed",
        "reopened",
    }
)

SUPPORT_TICKET_IDEMPOTENCY_TTL_SECONDS = 86_400


@dataclass(frozen=True, slots=True)
class SupportTicketTelegramNotification:
    """Queue-ready support ticket Telegram notification."""

    telegram_id: int
    ticket_event_id: str
    ticket_public_id: str
    event_type: SupportTicketNotificationEventType
    status: str
    category: str
    support_url: str
    message: str
    scheduled_at: datetime

    @property
    def idempotency_key(self) -> str:
        """Redis key derived from the backend support ticket event id."""
        return f"cybervpn:support-ticket-notification:{self.ticket_event_id}"

    def to_queue_model(self) -> NotificationQueueModel:
        """Convert this contract object to the durable notification queue model."""
        return NotificationQueueModel(
            telegram_id=self.telegram_id,
            message=self.message,
            notification_type=NOTIFICATION_TYPE_SUPPORT_TICKET_UPDATE,
            status=STATUS_PENDING,
            scheduled_at=self.scheduled_at,
        )


def build_support_ticket_telegram_notification(
    *,
    telegram_id: int | None,
    ticket_event_id: str,
    ticket_public_id: str,
    event_type: SupportTicketNotificationEventType,
    status: str,
    category: str,
    support_url: str = "",
    enabled: bool = True,
    scheduled_at: datetime | None = None,
) -> SupportTicketTelegramNotification | None:
    """Build a safe support ticket notification from a backend ticket event."""
    if not enabled or telegram_id is None:
        return None
    if telegram_id <= 0:
        raise ValueError("telegram_id must be a positive integer")
    if not ticket_event_id.strip():
        raise ValueError("ticket_event_id is required for idempotency")
    if not ticket_public_id.strip():
        raise ValueError("ticket_public_id is required")
    if event_type not in SUPPORT_TICKET_NOTIFICATION_EVENT_TYPES:
        raise ValueError(f"Unsupported support ticket notification event type: {event_type}")
    if not status.strip():
        raise ValueError("status is required")
    if not category.strip():
        raise ValueError("category is required")

    message = support_ticket_update(
        ticket_public_id=ticket_public_id,
        event_type=event_type,
        status=status,
        category=category,
        support_url=support_url,
    )
    return SupportTicketTelegramNotification(
        telegram_id=telegram_id,
        ticket_event_id=ticket_event_id.strip(),
        ticket_public_id=ticket_public_id.strip(),
        event_type=event_type,
        status=status.strip(),
        category=category.strip(),
        support_url=support_url.strip(),
        message=message,
        scheduled_at=scheduled_at or datetime.now(UTC),
    )
