"""Mobile device database model for tracking user devices.

Stores device information for mobile app authentication and session management.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.session import Base


class MobileDeviceModel(Base):
    """Mobile device registration model.

    Tracks devices that have authenticated with a mobile user account.
    Used for session management, push notifications, and security monitoring.
    """

    __tablename__ = "mobile_devices"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Device identification
    device_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )
    platform: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )
    platform_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    os_version: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    app_version: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    device_model: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    # Push notifications
    push_token: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )

    # User relationship
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("mobile_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user: Mapped["MobileUserModel"] = relationship(  # noqa: F821
        back_populates="devices",
        lazy="raise",
    )

    # Timestamps
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    last_active_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<MobileDevice(device_id={self.device_id}, platform={self.platform})>"


# Add relationship to MobileUserModel - done via back_populates
