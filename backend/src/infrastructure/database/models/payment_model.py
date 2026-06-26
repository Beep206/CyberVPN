"""PaymentModel ORM model for payment processing and tracking."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, String, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class PaymentModel(Base):
    """
    Payment model for tracking cryptocurrency payments and subscriptions.

    Tracks payments from various providers (Cryptomus, etc.) and links them
    to VPN user subscriptions.
    """

    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint(
            "provider <> 'internal_zero' OR external_id IS NOT NULL",
            name="ck_payments_internal_zero_external_id_required",
        ),
        Index(
            "uq_payments_internal_zero_external_id",
            "provider",
            "external_id",
            unique=True,
            postgresql_where=text("provider = 'internal_zero' AND external_id IS NOT NULL"),
            sqlite_where=text("provider = 'internal_zero' AND external_id IS NOT NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4, nullable=False)

    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    user_uuid: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)

    amount: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)

    currency: Mapped[str] = mapped_column(String(10), nullable=False)

    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    provider: Mapped[str] = mapped_column(String(20), nullable=False)

    subscription_days: Mapped[int] = mapped_column(Integer, nullable=False)

    # Codes & wallet integration
    plan_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)

    promo_code_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)

    partner_code_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)

    code_set_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("checkout_code_sets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    discount_amount: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False, server_default="0")

    wallet_amount_used: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False, server_default="0")

    final_amount: Mapped[float | None] = mapped_column(Numeric(20, 8), nullable=True)

    addons_snapshot: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)

    entitlements_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    growth_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<PaymentModel(id={self.id}, external_id='{self.external_id}', status='{self.status}')>"
