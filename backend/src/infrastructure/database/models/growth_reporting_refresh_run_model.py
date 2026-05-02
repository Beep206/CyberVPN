"""Persisted refresh attempts for customer growth reporting rollups."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import JSON, Date, DateTime, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class GrowthReportingRefreshRunModel(Base):
    __tablename__ = "growth_reporting_refresh_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trigger_kind: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    refresh_status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    requested_window_days: Mapped[int] = mapped_column(Integer, nullable=False)
    window_start: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    window_end: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    latest_rollup_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    rows_written: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    families_updated: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    refreshed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        index=True,
    )

    def normalized_families_updated(self) -> list[str]:
        raw = self.families_updated
        if isinstance(raw, list):
            return [str(item) for item in raw if str(item).strip()]
        if isinstance(raw, tuple):
            return [str(item) for item in raw if str(item).strip()]
        return []

    def as_payload(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "trigger_kind": self.trigger_kind,
            "refresh_status": self.refresh_status,
            "requested_window_days": self.requested_window_days,
            "window_start": self.window_start.isoformat(),
            "window_end": self.window_end.isoformat(),
            "latest_rollup_date": self.latest_rollup_date.isoformat() if self.latest_rollup_date else None,
            "rows_written": self.rows_written,
            "families_updated": self.normalized_families_updated(),
            "error_message": self.error_message,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat(),
            "refreshed_at": self.refreshed_at.isoformat() if self.refreshed_at else None,
            "created_at": self.created_at.isoformat(),
        }
