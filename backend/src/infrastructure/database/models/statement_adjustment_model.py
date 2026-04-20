"""Typed statement adjustment ORM model."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class StatementAdjustmentModel(Base):
    __tablename__ = "statement_adjustments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    partner_statement_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("partner_statements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    partner_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("partner_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_reference_type: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    source_reference_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True, index=True)
    carried_from_adjustment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("statement_adjustments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    adjustment_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    adjustment_direction: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency_code: Mapped[str] = mapped_column(String(12), nullable=False, default="USD", server_default="USD")
    reason_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    adjustment_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_by_admin_user_id: Mapped[uuid.UUID | None] = mapped_column(
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
