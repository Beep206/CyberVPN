"""Wallet and WalletTransaction models for user balance management."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.session import Base


class WalletModel(Base):
    """User wallet storing USD balance with freeze support for pending operations."""

    __tablename__ = "wallets"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mobile_users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    balance: Mapped[float] = mapped_column(
        Numeric(20, 8),
        nullable=False,
        default=0,
    )

    currency: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="USD",
    )

    frozen: Mapped[float] = mapped_column(
        Numeric(20, 8),
        nullable=False,
        default=0,
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

    transactions: Mapped[list["WalletTransactionModel"]] = relationship(
        back_populates="wallet",
        lazy="raise",
    )

    def __repr__(self) -> str:
        return f"<Wallet(id={self.id}, user_id={self.user_id}, balance={self.balance})>"


class WalletTransactionModel(Base):
    """Full ledger of all wallet credit/debit operations."""

    __tablename__ = "wallet_transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    wallet_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("wallets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mobile_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    type: Mapped[str] = mapped_column(
        String(10),
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

    balance_after: Mapped[float] = mapped_column(
        Numeric(20, 8),
        nullable=False,
    )

    reason: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    reference_type: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    reference_id: Mapped[uuid.UUID | None] = mapped_column(
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    wallet: Mapped["WalletModel"] = relationship(
        back_populates="transactions",
        lazy="raise",
    )

    def __repr__(self) -> str:
        return f"<WalletTx(id={self.id}, type={self.type}, amount={self.amount}, reason={self.reason})>"
