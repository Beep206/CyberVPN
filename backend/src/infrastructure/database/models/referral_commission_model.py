"""ReferralCommission ORM model for tracking referral earnings."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class ReferralCommissionModel(Base):
    """Ledger of referral commissions earned per payment."""

    __tablename__ = "referral_commissions"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    referrer_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mobile_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    referred_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mobile_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    payment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("payments.id", ondelete="CASCADE"),
        nullable=False,
    )

    commission_rate: Mapped[float] = mapped_column(
        Numeric(5, 4),
        nullable=False,
    )

    base_amount: Mapped[float] = mapped_column(
        Numeric(20, 8),
        nullable=False,
    )

    commission_amount: Mapped[float] = mapped_column(
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
        return f"<ReferralCommission(id={self.id}, referrer={self.referrer_user_id}, amount={self.commission_amount})>"
