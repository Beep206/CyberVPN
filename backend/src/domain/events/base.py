from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4


@dataclass(frozen=True)
class DomainEvent:
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    event_type: str = ""
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class UserCreatedEvent(DomainEvent):
    event_type: str = "user.created"
    user_uuid: UUID | None = None
    username: str = ""


@dataclass(frozen=True)
class UserUpdatedEvent(DomainEvent):
    event_type: str = "user.updated"
    user_uuid: UUID | None = None


@dataclass(frozen=True)
class PaymentCompletedEvent(DomainEvent):
    event_type: str = "payment.completed"
    payment_uuid: UUID | None = None
    user_uuid: UUID | None = None
    amount: str = ""


@dataclass(frozen=True)
class ServerStatusChangedEvent(DomainEvent):
    event_type: str = "server.status_changed"
    server_uuid: UUID | None = None
    old_status: str = ""
    new_status: str = ""
