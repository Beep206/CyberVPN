"""Recurring distribution subscriptions for customer growth reporting."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class GrowthReportingSubscriptionModel(Base):
    __tablename__ = "growth_reporting_subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipient_email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    recipient_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    audience_key: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    delivery_channel: Mapped[str] = mapped_column(String(20), nullable=False, default="email", server_default="email")
    cadence: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    report_window_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30, server_default="30")
    template_key: Mapped[str] = mapped_column(
        String(48),
        nullable=False,
        default="cross_function_exec",
        server_default="cross_function_exec",
    )
    template_locale: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="en-EN",
        server_default="en-EN",
    )
    email_subject_prefix: Mapped[str | None] = mapped_column(String(120), nullable=True)
    title_override: Mapped[str | None] = mapped_column(String(160), nullable=True)
    recipient_domain_policy: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default="allow_any",
        server_default="allow_any",
    )
    allowed_recipient_domains: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    suppressed_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    suppression_reason_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    governance_followup_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="none",
        server_default="none",
        index=True,
    )
    governance_followup_reason_code: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    governance_followup_opened_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    governance_followup_due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    governance_followup_last_notified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    governance_followup_resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    governance_followup_resolution_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    subscription_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
        default="active",
        server_default="active",
    )
    next_delivery_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    last_delivery_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    latest_delivery_status: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    latest_delivery_reason: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_by_admin_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    updated_by_admin_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        onupdate=func.now(),
    )
