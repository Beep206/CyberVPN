"""WithdrawalRequest ORM model for wallet withdrawals."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class WithdrawalRequestModel(Base):
    """Withdrawal requests from wallet balance to external payment."""

    __tablename__ = "withdrawal_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mobile_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    wallet_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("wallets.id", ondelete="CASCADE"),
        nullable=False,
    )

    amount: Mapped[float] = mapped_column(
        Numeric(20, 8),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="USD",
    )

    method: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        index=True,
    )

    external_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    admin_note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    processed_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
    )

    wallet_tx_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("wallet_transactions.id", ondelete="SET NULL"),
        nullable=True,
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
        return f"<WithdrawalRequest(id={self.id}, user={self.user_id}, amount={self.amount}, status={self.status})>"
