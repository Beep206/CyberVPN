"""Per-channel delivery state for customer growth notifications."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class CustomerGrowthNotificationDeliveryModel(Base):
    """Track fanout planning and delivery state for customer growth notifications."""

    __tablename__ = "customer_growth_notification_deliveries"
    __table_args__ = (
        UniqueConstraint(
            "mobile_user_id",
            "notification_key",
            "delivery_channel",
            name="uq_customer_growth_notification_delivery_user_key_channel",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    mobile_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mobile_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    notification_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    notification_kind: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    delivery_channel: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    delivery_status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    status_reason: Mapped[str | None] = mapped_column(String(120), nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(String(1000), nullable=False)
    delivery_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    source_kind: Mapped[str | None] = mapped_column(String(80), nullable=True)
    source_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
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
    planned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        onupdate=func.now(),
    )
