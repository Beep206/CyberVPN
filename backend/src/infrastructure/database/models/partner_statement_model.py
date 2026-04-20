"""Canonical partner statement ORM model."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class PartnerStatementModel(Base):
    __tablename__ = "partner_statements"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    partner_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("partner_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    settlement_period_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("settlement_periods.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    statement_key: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    statement_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    statement_status: Mapped[str] = mapped_column(String(20), nullable=False, default="open", server_default="open")
    reopened_from_statement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("partner_statements.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    superseded_by_statement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("partner_statements.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    currency_code: Mapped[str] = mapped_column(String(12), nullable=False, default="USD", server_default="USD")
    accrual_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0, server_default="0")
    on_hold_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0, server_default="0")
    reserve_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0, server_default="0")
    adjustment_net_amount: Mapped[float] = mapped_column(
        Numeric(12, 2), nullable=False, default=0, server_default="0"
    )
    available_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0, server_default="0")
    source_event_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    held_event_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    active_reserve_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    adjustment_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    statement_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    closed_by_admin_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
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
