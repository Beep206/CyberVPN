"""PaymentModel ORM model for payment processing and tracking."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class PaymentModel(Base):
    """
    Payment model for tracking cryptocurrency payments and subscriptions.

    Tracks payments from various providers (Cryptomus, etc.) and links them
    to VPN user subscriptions.
    """

    __tablename__ = "payments"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False)

    external_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)

    user_uuid: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)

    amount: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)

    currency: Mapped[str] = mapped_column(String(10), nullable=False)

    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    provider: Mapped[str] = mapped_column(String(20), nullable=False)

    subscription_days: Mapped[int] = mapped_column(Integer, nullable=False)

    metadata_: Mapped[Optional[dict[str, Any]]] = mapped_column("metadata", JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<PaymentModel(id={self.id}, external_id='{self.external_id}', status='{self.status}')>"
