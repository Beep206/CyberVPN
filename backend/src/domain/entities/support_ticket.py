"""Support ticket domain model and transition rules."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class SupportTicketError(Exception):
    """Base support-ticket domain error."""


class SupportTicketNotFoundError(SupportTicketError):
    """Raised when a ticket is absent or outside the caller scope."""


class InvalidSupportTicketTransitionError(SupportTicketError):
    """Raised when a requested status transition is not allowed."""


class SupportActorType(StrEnum):
    CUSTOMER = "customer"
    PARTNER = "partner"
    ADMIN = "admin"
    SYSTEM = "system"


class SupportMessageVisibility(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"


class SupportTicketOwnerType(StrEnum):
    CUSTOMER = "customer"
    PARTNER = "partner"


class SupportTicketSource(StrEnum):
    CUSTOMER_WEB = "customer_web"
    TELEGRAM_MINI_APP = "telegram_mini_app"
    PARTNER_PORTAL = "partner_portal"
    ADMIN_MANUAL = "admin_manual"
    TELEGRAM_BOT = "telegram_bot"


class SupportTicketStatus(StrEnum):
    OPEN = "open"
    PENDING_SUPPORT = "pending_support"
    PENDING_CUSTOMER = "pending_customer"
    RESOLVED = "resolved"
    CLOSED = "closed"


class SupportTicketCategory(StrEnum):
    ACCOUNT = "account"
    BILLING = "billing"
    SETUP = "setup"
    VPN_ACCESS = "vpn_access"
    STATUS = "status"
    PRIVACY = "privacy"
    OTHER = "other"
    ABUSE_REVIEW = "abuse_review"
    DUPLICATE = "duplicate"


class SupportTicketPriority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class SupportTicketEventType(StrEnum):
    TICKET_CREATED = "ticket_created"
    PUBLIC_REPLY_ADDED = "public_reply_added"
    INTERNAL_NOTE_ADDED = "internal_note_added"
    STATUS_CHANGED = "status_changed"
    PRIORITY_CHANGED = "priority_changed"
    CATEGORY_CHANGED = "category_changed"
    ASSIGNED = "assigned"
    CLOSED = "closed"
    REOPENED = "reopened"
    NOTIFICATION_QUEUED = "notification_queued"
    NOTIFICATION_FAILED = "notification_failed"


PUBLIC_EVENT_TYPES = frozenset(
    {
        SupportTicketEventType.TICKET_CREATED,
        SupportTicketEventType.PUBLIC_REPLY_ADDED,
        SupportTicketEventType.STATUS_CHANGED,
        SupportTicketEventType.CLOSED,
        SupportTicketEventType.REOPENED,
    }
)


CUSTOMER_CATEGORIES = frozenset(
    {
        SupportTicketCategory.ACCOUNT,
        SupportTicketCategory.BILLING,
        SupportTicketCategory.SETUP,
        SupportTicketCategory.VPN_ACCESS,
        SupportTicketCategory.STATUS,
        SupportTicketCategory.PRIVACY,
        SupportTicketCategory.OTHER,
    }
)


@dataclass(frozen=True, slots=True)
class SupportTicketMessage:
    id: UUID
    ticket_id: UUID
    author_type: SupportActorType
    author_id: UUID | None
    visibility: SupportMessageVisibility
    body: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class SupportTicketEvent:
    id: UUID
    ticket_id: UUID
    actor_type: SupportActorType
    actor_id: UUID | None
    event_type: SupportTicketEventType
    from_value: str | None
    to_value: str | None
    audit_summary: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class SupportTicket:
    id: UUID
    public_id: str
    owner_type: SupportTicketOwnerType
    customer_account_id: UUID | None
    partner_workspace_id: UUID | None
    created_by_actor_type: SupportActorType
    created_by_actor_id: UUID | None
    source: SupportTicketSource
    status: SupportTicketStatus
    category: SupportTicketCategory
    priority: SupportTicketPriority
    subject: str
    last_message_preview: str
    assigned_admin_id: UUID | None
    metadata: dict[str, object]
    created_at: datetime
    updated_at: datetime
    last_customer_message_at: datetime | None
    last_support_message_at: datetime | None
    resolved_at: datetime | None
    closed_at: datetime | None
    messages: tuple[SupportTicketMessage, ...] = field(default_factory=tuple)
    events: tuple[SupportTicketEvent, ...] = field(default_factory=tuple)


def assert_customer_category(category: SupportTicketCategory) -> None:
    if category not in CUSTOMER_CATEGORIES:
        raise ValueError("Category is admin-only")


def assert_customer_priority(priority: SupportTicketPriority) -> None:
    if priority == SupportTicketPriority.URGENT:
        raise ValueError("Urgent priority is admin-only")


def public_message_preview(body: str, *, max_chars: int = 160) -> str:
    compact = " ".join(body.split())
    if len(compact) <= max_chars:
        return compact
    return f"{compact[: max_chars - 3].rstrip()}..."


def status_after_public_reply(
    actor_type: SupportActorType,
    current_status: SupportTicketStatus,
) -> SupportTicketStatus:
    if actor_type in {SupportActorType.CUSTOMER, SupportActorType.PARTNER}:
        return SupportTicketStatus.PENDING_SUPPORT
    if current_status == SupportTicketStatus.CLOSED:
        raise InvalidSupportTicketTransitionError("Cannot add an admin public reply to a closed ticket")
    return SupportTicketStatus.PENDING_CUSTOMER


def assert_status_transition(
    *,
    actor_type: SupportActorType,
    current_status: SupportTicketStatus,
    requested_status: SupportTicketStatus,
) -> None:
    if requested_status == current_status:
        return

    allowed: set[SupportTicketStatus]
    if actor_type in {SupportActorType.CUSTOMER, SupportActorType.PARTNER}:
        if requested_status == SupportTicketStatus.CLOSED:
            allowed = {
                SupportTicketStatus.OPEN,
                SupportTicketStatus.PENDING_SUPPORT,
                SupportTicketStatus.PENDING_CUSTOMER,
                SupportTicketStatus.RESOLVED,
            }
        elif requested_status == SupportTicketStatus.PENDING_SUPPORT:
            allowed = {
                SupportTicketStatus.OPEN,
                SupportTicketStatus.PENDING_SUPPORT,
                SupportTicketStatus.PENDING_CUSTOMER,
                SupportTicketStatus.RESOLVED,
                SupportTicketStatus.CLOSED,
            }
        else:
            allowed = set()
    elif actor_type == SupportActorType.ADMIN:
        if requested_status == SupportTicketStatus.PENDING_CUSTOMER:
            allowed = {SupportTicketStatus.OPEN, SupportTicketStatus.PENDING_SUPPORT, SupportTicketStatus.RESOLVED}
        elif requested_status == SupportTicketStatus.RESOLVED:
            allowed = {
                SupportTicketStatus.OPEN,
                SupportTicketStatus.PENDING_SUPPORT,
                SupportTicketStatus.PENDING_CUSTOMER,
            }
        elif requested_status == SupportTicketStatus.CLOSED:
            allowed = {
                SupportTicketStatus.OPEN,
                SupportTicketStatus.PENDING_SUPPORT,
                SupportTicketStatus.PENDING_CUSTOMER,
                SupportTicketStatus.RESOLVED,
            }
        elif requested_status == SupportTicketStatus.PENDING_SUPPORT:
            allowed = {SupportTicketStatus.RESOLVED, SupportTicketStatus.CLOSED}
        elif requested_status == SupportTicketStatus.OPEN:
            allowed = set()
        else:
            allowed = set()
    else:
        allowed = set()

    if current_status not in allowed:
        raise InvalidSupportTicketTransitionError(
            f"Invalid transition from {current_status.value} to {requested_status.value}"
        )
