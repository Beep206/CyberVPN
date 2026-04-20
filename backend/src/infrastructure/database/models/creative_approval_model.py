"""Canonical creative approval ORM model."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class CreativeApprovalModel(Base):
    __tablename__ = "creative_approvals"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    partner_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("partner_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    approval_kind: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    approval_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="under_review",
        server_default="under_review",
        index=True,
    )
    scope_label: Mapped[str] = mapped_column(String(120), nullable=False)
    creative_ref: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    approval_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    notes_payload: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    submitted_by_admin_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reviewed_by_admin_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
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
