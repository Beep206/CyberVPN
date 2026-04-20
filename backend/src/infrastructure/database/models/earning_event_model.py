"""Canonical partner settlement accrual event ORM model."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class EarningEventModel(Base):
    __tablename__ = "earning_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    partner_account_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("partner_accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
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
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    payment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("payments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    partner_code_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("partner_codes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    legacy_partner_earning_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("partner_earnings.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    order_attribution_result_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("order_attribution_results.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    owner_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    event_status: Mapped[str] = mapped_column(String(20), nullable=False, default="on_hold", server_default="on_hold")
    commission_base_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    markup_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    commission_pct: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    commission_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency_code: Mapped[str] = mapped_column(String(12), nullable=False, default="USD", server_default="USD")
    available_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    source_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
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
