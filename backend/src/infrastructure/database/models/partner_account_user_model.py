"""Partner workspace membership ORM model."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class PartnerAccountUserModel(Base):
    """Membership record linking an operator account to a partner workspace."""

    __tablename__ = "partner_account_users"
    __table_args__ = (
        UniqueConstraint(
            "partner_account_id",
            "admin_user_id",
            name="uq_partner_account_users_account_admin_user",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    partner_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("partner_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    admin_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("admin_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    role_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("partner_account_roles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    membership_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
    )

    invited_by_admin_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
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
        return (
            f"<PartnerAccountUser(id={self.id}, partner_account_id={self.partner_account_id}, "
            f"admin_user_id={self.admin_user_id}, membership_status={self.membership_status})>"
        )
