"""Durable Stage 1 Remnawave provisioning retry jobs."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class Stage1ProvisioningRetryJobModel(Base):
    """PostgreSQL-backed retry job for S1 VPN provisioning recovery."""

    __tablename__ = "stage1_provisioning_retry_jobs"
    __table_args__ = (
        UniqueConstraint("operation", "correlation_id", name="uq_stage1_provisioning_retry_operation_correlation"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    queue_name: Mapped[str] = mapped_column(String(80), nullable=False, default="stage1_provisioning_retry")
    operation: Mapped[str] = mapped_column(String(40), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(160), nullable=False)
    customer_account_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(40), nullable=False, default="queued", index=True)
    reason: Mapped[str] = mapped_column(String(80), nullable=False)
    error_code: Mapped[str] = mapped_column(String(80), nullable=False)
    provisioning_state: Mapped[str] = mapped_column(String(80), nullable=False)
    payment_state: Mapped[str | None] = mapped_column(String(80), nullable=True)
    support_state: Mapped[str] = mapped_column(String(80), nullable=False)
    request_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    result_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=6)
    queued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_code: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    last_error_message: Mapped[str] = mapped_column(
        String(240),
        nullable=False,
        default="Remnawave provisioning attempt failed; details redacted.",
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
