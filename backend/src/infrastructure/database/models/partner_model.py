"""PartnerCode and PartnerEarning ORM models for reseller system."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class PartnerCodeModel(Base):
    """Partner-created referral codes with configurable markup."""

    __tablename__ = "partner_codes"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    code: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        nullable=False,
        index=True,
    )

    partner_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mobile_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    markup_pct: Mapped[float] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=0,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
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
        return f"<PartnerCode(id={self.id}, code={self.code}, markup={self.markup_pct}%)>"


class PartnerEarningModel(Base):
    """Ledger of partner earnings per client payment."""

    __tablename__ = "partner_earnings"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    partner_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mobile_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    client_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mobile_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    payment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("payments.id", ondelete="CASCADE"),
        nullable=False,
    )

    partner_code_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("partner_codes.id", ondelete="CASCADE"),
        nullable=False,
    )

    base_price: Mapped[float] = mapped_column(
        Numeric(20, 8),
        nullable=False,
    )

    markup_amount: Mapped[float] = mapped_column(
        Numeric(20, 8),
        nullable=False,
    )

    commission_pct: Mapped[float] = mapped_column(
        Numeric(5, 2),
        nullable=False,
    )

    commission_amount: Mapped[float] = mapped_column(
        Numeric(20, 8),
        nullable=False,
    )

    total_earning: Mapped[float] = mapped_column(
        Numeric(20, 8),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="USD",
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

    def __repr__(self) -> str:
        return f"<PartnerEarning(id={self.id}, partner={self.partner_user_id}, total={self.total_earning})>"
