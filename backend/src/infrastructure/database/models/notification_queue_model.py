"""NotificationQueue ORM model for Telegram notification management."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, DateTime, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class NotificationQueue(Base):
    """
    Notification queue model for Telegram bot message delivery.

    Manages queued notifications with retry logic, scheduling, and
    delivery tracking for admin notifications.
    """

    __tablename__ = "notification_queue"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False)

    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    message: Mapped[str] = mapped_column(Text, nullable=False)

    notification_type: Mapped[str | None] = mapped_column(String(50), nullable=True)

    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)

    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (Index("ix_notification_queue_status_scheduled", "status", "scheduled_at"),)

    def __repr__(self) -> str:
        return f"<NotificationQueue(id={self.id}, telegram_id={self.telegram_id}, status='{self.status}')>"
