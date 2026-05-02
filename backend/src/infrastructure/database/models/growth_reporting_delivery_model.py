"""Persisted recurring delivery artifacts for customer growth reporting."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import JSON, Date, DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class GrowthReportingDeliveryModel(Base):
    __tablename__ = "growth_reporting_deliveries"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subscription_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("growth_reporting_subscriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recipient_email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    recipient_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    audience_key: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    delivery_channel: Mapped[str] = mapped_column(String(20), nullable=False, default="email", server_default="email")
    cadence: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    report_window_days: Mapped[int] = mapped_column(nullable=False)
    template_key: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    template_locale: Mapped[str] = mapped_column(String(16), nullable=False)
    subject_line: Mapped[str] = mapped_column(String(255), nullable=False)
    title_line: Mapped[str] = mapped_column(String(255), nullable=False)
    recipient_domain_policy: Mapped[str] = mapped_column(String(24), nullable=False)
    allowed_recipient_domains: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    delivery_status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    status_reason: Mapped[str | None] = mapped_column(String(120), nullable=True)
    window_start: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    window_end: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    freshness_status: Mapped[str] = mapped_column(String(20), nullable=False, default="fresh", server_default="fresh")
    artifact_checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
    artifact_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    provider_name: Mapped[str | None] = mapped_column(String(40), nullable=True)
    provider_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    failure_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    planned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
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
