"""InviteCode ORM model for friend-invite system."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class InviteCodeModel(Base):
    """Invite codes generated from purchases or granted by admin."""

    __tablename__ = "invite_codes"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        index=True,
    )

    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mobile_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    free_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    plan_id: Mapped[uuid.UUID | None] = mapped_column(
        nullable=True,
    )

    source: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    source_payment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("payments.id", ondelete="SET NULL"),
        nullable=True,
    )

    is_used: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    used_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("mobile_users.id", ondelete="SET NULL"),
        nullable=True,
    )

    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<InviteCode(id={self.id}, code={self.code}, is_used={self.is_used})>"
