"""Canonical payout execution ORM model."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, Uuid, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class PayoutExecutionModel(Base):
    __tablename__ = "payout_executions"
    __table_args__ = (
        UniqueConstraint(
            "payout_instruction_id",
            "request_idempotency_key",
            name="uq_payout_execution_instruction_idempotency",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payout_instruction_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("payout_instructions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    partner_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("partner_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    partner_statement_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("partner_statements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    partner_payout_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("partner_payout_accounts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    execution_key: Mapped[str] = mapped_column(String(180), nullable=False, unique=True, index=True)
    execution_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="dry_run", index=True)
    execution_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="requested",
        server_default="requested",
        index=True,
    )
    request_idempotency_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    external_reference: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    execution_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    result_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    requested_by_admin_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    submitted_by_admin_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    completed_by_admin_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    reconciled_by_admin_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reconciled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    failure_reason_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
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
