"""SQLAlchemy models for canonical in-site notifications."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.session import Base


def _utc_now() -> datetime:
    return datetime.now(UTC)


class SiteNotificationModel(Base):
    __tablename__ = "site_notifications"
    __table_args__ = (
        Index("ix_site_notifications_aggregate", "aggregate_type", "aggregate_id"),
        Index("ix_site_notifications_conversation_created", "conversation_id", "created_at"),
        Index("ix_site_notifications_broadcast_created", "broadcast_campaign_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    notification_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    action_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    aggregate_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    aggregate_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("messaging_conversations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    message_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("messaging_messages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    broadcast_campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("broadcast_campaigns.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_by_actor_type: Mapped[str] = mapped_column(String(20), nullable=False)
    created_by_actor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    deliveries: Mapped[list[SiteNotificationDeliveryModel]] = relationship(
        back_populates="notification",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="SiteNotificationDeliveryModel.created_at",
    )


class SiteNotificationDeliveryModel(Base):
    __tablename__ = "site_notification_deliveries"
    __table_args__ = (
        UniqueConstraint(
            "notification_id",
            "recipient_type",
            "recipient_id",
            "delivery_channel",
            name="uq_site_notification_deliveries_recipient_channel",
        ),
        CheckConstraint("recipient_id is not null", name="ck_site_notification_deliveries_recipient_required"),
        Index(
            "ix_site_notification_deliveries_recipient_status_created",
            "recipient_type",
            "recipient_id",
            "status",
            "created_at",
        ),
        Index("ix_site_notification_deliveries_status_created", "status", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    notification_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("site_notifications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recipient_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    recipient_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True, index=True)
    delivery_channel: Mapped[str] = mapped_column(String(20), nullable=False, default="site")
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    notification: Mapped[SiteNotificationModel] = relationship(back_populates="deliveries", lazy="raise")
