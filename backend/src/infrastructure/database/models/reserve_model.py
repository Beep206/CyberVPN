"""Canonical reserve ORM model for partner settlement."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class ReserveModel(Base):
    __tablename__ = "reserves"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    partner_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("partner_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_earning_event_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("earning_events.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reserve_scope: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    reserve_reason_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    reserve_status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", server_default="active")
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency_code: Mapped[str] = mapped_column(String(12), nullable=False, default="USD", server_default="USD")
    reason_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    reserve_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    released_by_admin_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
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
