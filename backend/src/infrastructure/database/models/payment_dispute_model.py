"""Canonical payment dispute ORM model."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class PaymentDisputeModel(Base):
    __tablename__ = "payment_disputes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    payment_attempt_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("payment_attempts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    payment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("payments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    provider: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    external_reference: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    subtype: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    outcome_class: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="open",
        server_default="open",
        index=True,
    )
    lifecycle_status: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default="opened",
        server_default="opened",
        index=True,
    )
    disputed_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    fee_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0, server_default="0")
    fee_status: Mapped[str] = mapped_column(String(40), nullable=False, default="none", server_default="none")
    currency_code: Mapped[str] = mapped_column(String(12), nullable=False, default="USD", server_default="USD")
    reason_code: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    evidence_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    provider_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
