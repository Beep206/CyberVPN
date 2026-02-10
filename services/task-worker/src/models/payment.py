"""Payment model for subscription transactions."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.database.session import Base


class PaymentModel(Base):
    """
    Payment record for subscription purchases.

    Tracks payment transactions from various providers (CryptoCloud, Yookassa, etc.)
    with status, amount, and subscription duration information.
    """

    __tablename__ = "payments"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    user_uuid: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    amount: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    subscription_days: Mapped[int] = mapped_column(Integer, nullable=False)

    # Codes & wallet integration (synced with backend migration)
    plan_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    promo_code_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    partner_code_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    discount_amount: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False, server_default="0")
    wallet_amount_used: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False, server_default="0")
    final_amount: Mapped[float | None] = mapped_column(Numeric(20, 8), nullable=True)

    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<PaymentModel(id={self.id}, external_id='{self.external_id}', status='{self.status}')>"
