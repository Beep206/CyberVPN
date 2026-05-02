from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.growth_reporting_refresh_run_model import (
    GrowthReportingRefreshRunModel,
)


@dataclass(frozen=True)
class GrowthReportingRefreshRunWrite:
    trigger_kind: str
    refresh_status: str
    requested_window_days: int
    window_start: date
    window_end: date
    latest_rollup_date: date | None
    rows_written: int
    families_updated: list[str]
    started_at: datetime
    finished_at: datetime
    refreshed_at: datetime | None
    error_message: str | None = None


class GrowthReportingRefreshRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, payload: GrowthReportingRefreshRunWrite) -> GrowthReportingRefreshRunModel:
        model = GrowthReportingRefreshRunModel(
            trigger_kind=payload.trigger_kind,
            refresh_status=payload.refresh_status,
            requested_window_days=payload.requested_window_days,
            window_start=payload.window_start,
            window_end=payload.window_end,
            latest_rollup_date=payload.latest_rollup_date,
            rows_written=payload.rows_written,
            families_updated=list(payload.families_updated),
            error_message=payload.error_message,
            started_at=_coerce_utc(payload.started_at),
            finished_at=_coerce_utc(payload.finished_at),
            refreshed_at=_coerce_utc(payload.refreshed_at) if payload.refreshed_at is not None else None,
        )
        self._session.add(model)
        await self._session.flush()
        return model

    async def get_latest(self) -> GrowthReportingRefreshRunModel | None:
        result = await self._session.execute(
            select(GrowthReportingRefreshRunModel).order_by(
                GrowthReportingRefreshRunModel.finished_at.desc(),
                GrowthReportingRefreshRunModel.created_at.desc(),
            )
        )
        return result.scalars().first()

    async def get_latest_by_status(self, refresh_status: str) -> GrowthReportingRefreshRunModel | None:
        result = await self._session.execute(
            select(GrowthReportingRefreshRunModel)
            .where(GrowthReportingRefreshRunModel.refresh_status == refresh_status)
            .order_by(
                GrowthReportingRefreshRunModel.finished_at.desc(),
                GrowthReportingRefreshRunModel.created_at.desc(),
            )
        )
        return result.scalars().first()


def _coerce_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
