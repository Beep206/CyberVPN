"""Immutable history events for customer growth notification deliveries."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class CustomerGrowthNotificationDeliveryEventModel(Base):
    """Append-only event ledger for delivery troubleshooting and export."""

    __tablename__ = "customer_growth_notification_delivery_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    delivery_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customer_growth_notification_deliveries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    delivery_status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    reason_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    event_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    event_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    notification_queue_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("notification_queue.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_by_admin_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )
