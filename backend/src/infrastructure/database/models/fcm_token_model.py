"""FCM token model for push notification management."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class FCMTokenModel(Base):
    """Firebase Cloud Messaging tokens for admin user push notifications.

    Stores device-specific FCM tokens. Each user can have multiple tokens
    (one per device). Unique constraint on (user_id, device_id) ensures
    one token per device.
    """

    __tablename__ = "fcm_tokens"

    __table_args__ = (
        UniqueConstraint("user_id", "device_id", name="uq_fcm_tokens_user_device"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("admin_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    token: Mapped[str] = mapped_column(
        String(4096),
        nullable=False,
    )

    device_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    platform: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<FCMToken(id={self.id}, user_id={self.user_id}, device={self.device_id}, platform={self.platform})>"
