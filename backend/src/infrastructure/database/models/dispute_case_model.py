"""Operational dispute-case overlay over canonical payment disputes."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class DisputeCaseModel(Base):
    __tablename__ = "dispute_cases"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    partner_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("partner_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    payment_dispute_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("payment_disputes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    case_kind: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    case_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="open",
        server_default="open",
        index=True,
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    case_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    notes_payload: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    opened_by_admin_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    assigned_to_admin_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    closed_by_admin_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
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
