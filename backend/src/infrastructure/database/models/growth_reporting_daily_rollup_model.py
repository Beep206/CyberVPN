"""Persisted daily rollup rows for customer growth reporting."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, Numeric, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class GrowthReportingDailyRollupModel(Base):
    __tablename__ = "growth_reporting_daily_rollups"
    __table_args__ = (
        UniqueConstraint(
            "report_date",
            "report_family",
            "metric_key",
            "dimension_key",
            "dimension_value",
            "currency_code",
            name="uq_growth_reporting_daily_rollups_metric",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    report_family: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    metric_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    metric_unit: Mapped[str] = mapped_column(String(20), nullable=False, default="count", server_default="count")
    dimension_key: Mapped[str] = mapped_column(String(40), nullable=False, default="", server_default="")
    dimension_value: Mapped[str] = mapped_column(String(80), nullable=False, default="", server_default="")
    metric_value: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    currency_code: Mapped[str] = mapped_column(String(12), nullable=False, default="", server_default="")
    source_watermark_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    refreshed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        index=True,
    )
