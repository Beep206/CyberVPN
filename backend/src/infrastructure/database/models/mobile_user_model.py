"""Mobile user database model for CyberVPN mobile app users.

Stores mobile app users separately from admin dashboard users.
Integrates with Remnawave for VPN configuration management.
"""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.session import Base

if TYPE_CHECKING:
    from src.infrastructure.database.models.mobile_device_model import (
        MobileDeviceModel,
    )


class MobileUserModel(Base):
    """Mobile application user model.

    Represents users who access CyberVPN through the mobile app.
    Separate from AdminUserModel which is for dashboard administration.
    """

    __tablename__ = "mobile_users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    username: Mapped[str | None] = mapped_column(
        String(50),
        unique=True,
        nullable=True,
    )

    # Telegram OAuth linking
    telegram_id: Mapped[int | None] = mapped_column(
        BigInteger,
        unique=True,
        nullable=True,
        index=True,
    )
    telegram_username: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # Remnawave VPN user reference
    remnawave_uuid: Mapped[str | None] = mapped_column(
        String(36),
        unique=True,
        nullable=True,
        index=True,
    )
    subscription_url: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )

    # Referral & Partner system
    referral_code: Mapped[str | None] = mapped_column(
        String(12),
        unique=True,
        nullable=True,
        index=True,
    )
    referred_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("mobile_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    partner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("mobile_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_partner: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    partner_promoted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Account status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="active",
        nullable=False,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    devices: Mapped[list["MobileDeviceModel"]] = relationship(
        back_populates="user",
        lazy="raise",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<MobileUser(id={self.id}, email={self.email}, status={self.status})>"
