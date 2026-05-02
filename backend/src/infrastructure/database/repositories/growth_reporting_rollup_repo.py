from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.growth_reporting_daily_rollup_model import (
    GrowthReportingDailyRollupModel,
)


@dataclass(frozen=True)
class GrowthReportingRollupWriteRow:
    report_date: date
    report_family: str
    metric_key: str
    metric_unit: str
    metric_value: Decimal
    dimension_key: str = ""
    dimension_value: str = ""
    currency_code: str = ""
    source_watermark_at: datetime | None = None


class GrowthReportingRollupRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def replace_window(
        self,
        *,
        start_date: date,
        end_date: date,
        rows: list[GrowthReportingRollupWriteRow],
        refreshed_at: datetime | None = None,
    ) -> int:
        resolved_refreshed_at = refreshed_at or datetime.now(UTC)
        await self._session.execute(
            delete(GrowthReportingDailyRollupModel).where(
                GrowthReportingDailyRollupModel.report_date >= start_date,
                GrowthReportingDailyRollupModel.report_date <= end_date,
            )
        )
        for row in rows:
            self._session.add(
                GrowthReportingDailyRollupModel(
                    report_date=row.report_date,
                    report_family=row.report_family,
                    metric_key=row.metric_key,
                    metric_unit=row.metric_unit,
                    dimension_key=row.dimension_key,
                    dimension_value=row.dimension_value,
                    metric_value=float(row.metric_value),
                    currency_code=row.currency_code,
                    source_watermark_at=row.source_watermark_at,
                    refreshed_at=resolved_refreshed_at,
                )
            )
        await self._session.flush()
        return len(rows)

    async def list_window(
        self,
        *,
        start_date: date,
        end_date: date,
        report_family: str | None = None,
    ) -> list[GrowthReportingDailyRollupModel]:
        stmt = (
            select(GrowthReportingDailyRollupModel)
            .where(
                GrowthReportingDailyRollupModel.report_date >= start_date,
                GrowthReportingDailyRollupModel.report_date <= end_date,
            )
            .order_by(
                GrowthReportingDailyRollupModel.report_date.asc(),
                GrowthReportingDailyRollupModel.report_family.asc(),
                GrowthReportingDailyRollupModel.metric_key.asc(),
                GrowthReportingDailyRollupModel.dimension_key.asc(),
                GrowthReportingDailyRollupModel.dimension_value.asc(),
            )
        )
        if report_family is not None:
            stmt = stmt.where(GrowthReportingDailyRollupModel.report_family == report_family)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_latest_report_date(self) -> date | None:
        result = await self._session.execute(select(func.max(GrowthReportingDailyRollupModel.report_date)))
        return result.scalar_one_or_none()

    async def get_latest_refresh_time(
        self,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> datetime | None:
        stmt = select(func.max(GrowthReportingDailyRollupModel.refreshed_at))
        if start_date is not None:
            stmt = stmt.where(GrowthReportingDailyRollupModel.report_date >= start_date)
        if end_date is not None:
            stmt = stmt.where(GrowthReportingDailyRollupModel.report_date <= end_date)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
