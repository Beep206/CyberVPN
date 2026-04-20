"""Canonical payout-hold ORM model for earning events."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class EarningHoldModel(Base):
    __tablename__ = "earning_holds"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    earning_event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("earning_events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    partner_account_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("partner_accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    hold_reason_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    hold_status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", server_default="active")
    reason_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    hold_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
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
    hold_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
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
