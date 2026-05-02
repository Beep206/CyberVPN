from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.growth_code_model import (
    GrowthCodeModel,
    GrowthCodeRedemptionModel,
    GrowthCodeReservationModel,
    GrowthCodeResolutionEventModel,
)
from src.infrastructure.database.models.growth_reward_allocation_model import GrowthRewardAllocationModel
from src.infrastructure.database.repositories.growth_reporting_refresh_run_repo import (
    GrowthReportingRefreshRunRepository,
    GrowthReportingRefreshRunWrite,
)
from src.infrastructure.database.repositories.growth_reporting_rollup_repo import (
    GrowthReportingRollupRepository,
    GrowthReportingRollupWriteRow,
)

_CANONICAL_FAMILIES = ("invite", "referral", "promo", "gift")
_AUTO_REFRESH_ENABLED = True
_EXPECTED_REFRESH_INTERVAL_SECONDS = 60 * 60
_STALE_AFTER_SECONDS = 3 * _EXPECTED_REFRESH_INTERVAL_SECONDS
_COVERAGE_NOTES = (
    "Daily rollups currently cover codes, resolution events, reservations, redemptions, and reward allocations.",
    "Touchpoint and signup attribution funnels are excluded until canonical runtime "
    "starts writing those lifecycle tables.",
)


@dataclass
class GrowthReportingBucket:
    issued_total: int = 0
    resolution_attempts_total: int = 0
    resolution_accepted_total: int = 0
    resolution_rejected_total: int = 0
    redemption_total: int = 0
    reservations_reserved_total: int = 0
    reservations_consumed_total: int = 0
    reservations_released_total: int = 0
    reservations_expired_total: int = 0
    rewards_created_total: int = 0
    rewards_available_total: int = 0
    rewards_reversed_total: int = 0
    reward_created_amount_usd: float = 0
    reward_available_amount_usd: float = 0
    reward_reversed_amount_usd: float = 0


@dataclass(frozen=True)
class GrowthReportingFamilySummary:
    family: str
    issued_total: int
    resolution_attempts_total: int
    resolution_accepted_total: int
    resolution_rejected_total: int
    redemption_total: int
    reservations_reserved_total: int
    reservations_consumed_total: int
    reservations_released_total: int
    reservations_expired_total: int
    rewards_created_total: int
    rewards_available_total: int
    rewards_reversed_total: int
    reward_created_amount_usd: float
    reward_available_amount_usd: float
    reward_reversed_amount_usd: float


@dataclass(frozen=True)
class GrowthReportingDailyPoint(GrowthReportingFamilySummary):
    report_date: date


@dataclass(frozen=True)
class GrowthReportingRefreshRunSummary:
    id: str
    trigger_kind: str
    refresh_status: str
    requested_window_days: int
    window_start: date
    window_end: date
    latest_rollup_date: date | None
    rows_written: int
    families_updated: list[str]
    error_message: str | None
    started_at: datetime
    finished_at: datetime
    refreshed_at: datetime | None


@dataclass(frozen=True)
class GrowthReportingHealth:
    freshness_status: str
    stale_reason: str | None
    refresh_age_seconds: int | None
    expected_refresh_interval_seconds: int
    stale_after_seconds: int
    auto_refresh_enabled: bool
    latest_attempt_at: datetime | None
    latest_success_at: datetime | None
    latest_failure_at: datetime | None
    latest_failure_message: str | None
    latest_run: GrowthReportingRefreshRunSummary | None


@dataclass(frozen=True)
class GrowthReportingExecutiveSummary:
    total_issued: int
    total_redemptions: int
    total_reward_available_usd: float
    total_reward_reversed_usd: float
    resolution_acceptance_rate_pct: float
    dominant_family: str | None
    highlights: list[str]


@dataclass(frozen=True)
class GrowthReportingOverview:
    window_start: date
    window_end: date
    latest_rollup_date: date | None
    refreshed_at: datetime | None
    family_summaries: list[GrowthReportingFamilySummary]
    daily_points: list[GrowthReportingDailyPoint]
    totals: GrowthReportingFamilySummary
    health: GrowthReportingHealth
    executive_summary: GrowthReportingExecutiveSummary
    coverage_notes: list[str]


@dataclass(frozen=True)
class GrowthReportingRefreshResult:
    trigger_kind: str
    window_start: date
    window_end: date
    latest_rollup_date: date | None
    refreshed_at: datetime
    rows_written: int
    families_updated: list[str]
    coverage_notes: list[str]


@dataclass(frozen=True)
class GrowthReportingExport:
    overview: GrowthReportingOverview
    raw_rows: list[dict[str, object]]


class RefreshGrowthReportingRollupsUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._rollups = GrowthReportingRollupRepository(session)
        self._runs = GrowthReportingRefreshRunRepository(session)

    async def execute(
        self,
        *,
        window_days: int = 30,
        end_date: date | None = None,
        trigger_kind: str = "manual",
    ) -> GrowthReportingRefreshResult:
        resolved_end = end_date or datetime.now(UTC).date()
        resolved_window_days = max(window_days, 1)
        resolved_start = resolved_end - timedelta(days=resolved_window_days - 1)
        started_at = datetime.now(UTC)
        refreshed_at = datetime.now(UTC)
        rows: list[GrowthReportingRollupWriteRow] = []

        try:
            async with self._session.begin_nested():
                rows.extend(await self._collect_code_issue_rows(start_date=resolved_start, end_date=resolved_end))
                rows.extend(await self._collect_resolution_rows(start_date=resolved_start, end_date=resolved_end))
                rows.extend(await self._collect_reservation_rows(start_date=resolved_start, end_date=resolved_end))
                rows.extend(await self._collect_redemption_rows(start_date=resolved_start, end_date=resolved_end))
                rows.extend(await self._collect_reward_rows(start_date=resolved_start, end_date=resolved_end))

                rows_written = await self._rollups.replace_window(
                    start_date=resolved_start,
                    end_date=resolved_end,
                    rows=rows,
                    refreshed_at=refreshed_at,
                )
            families_updated = sorted({row.report_family for row in rows})
            latest_rollup_date = resolved_end if rows_written > 0 else None
            await self._runs.create(
                GrowthReportingRefreshRunWrite(
                    trigger_kind=trigger_kind,
                    refresh_status="success",
                    requested_window_days=resolved_window_days,
                    window_start=resolved_start,
                    window_end=resolved_end,
                    latest_rollup_date=latest_rollup_date,
                    rows_written=rows_written,
                    families_updated=families_updated,
                    started_at=started_at,
                    finished_at=datetime.now(UTC),
                    refreshed_at=refreshed_at,
                )
            )
            return GrowthReportingRefreshResult(
                trigger_kind=trigger_kind,
                window_start=resolved_start,
                window_end=resolved_end,
                latest_rollup_date=latest_rollup_date,
                refreshed_at=refreshed_at,
                rows_written=rows_written,
                families_updated=families_updated,
                coverage_notes=list(_COVERAGE_NOTES),
            )
        except Exception as exc:
            await self._runs.create(
                GrowthReportingRefreshRunWrite(
                    trigger_kind=trigger_kind,
                    refresh_status="failed",
                    requested_window_days=resolved_window_days,
                    window_start=resolved_start,
                    window_end=resolved_end,
                    latest_rollup_date=None,
                    rows_written=0,
                    families_updated=[],
                    error_message=str(exc),
                    started_at=started_at,
                    finished_at=datetime.now(UTC),
                    refreshed_at=None,
                )
            )
            raise

    async def _collect_code_issue_rows(
        self,
        *,
        start_date: date,
        end_date: date,
    ) -> list[GrowthReportingRollupWriteRow]:
        start_dt, end_dt = _date_window_to_datetimes(start_date=start_date, end_date=end_date)
        result = await self._session.execute(
            select(
                func.date(GrowthCodeModel.created_at).label("report_date"),
                GrowthCodeModel.code_type.label("report_family"),
                func.count(GrowthCodeModel.id).label("metric_value"),
                func.max(GrowthCodeModel.created_at).label("source_watermark_at"),
            )
            .where(
                GrowthCodeModel.created_at >= start_dt,
                GrowthCodeModel.created_at < end_dt,
            )
            .group_by(
                func.date(GrowthCodeModel.created_at),
                GrowthCodeModel.code_type,
            )
        )
        return [
            GrowthReportingRollupWriteRow(
                report_date=_coerce_report_date(row.report_date),
                report_family=str(row.report_family or "unknown"),
                metric_key="codes_issued_total",
                metric_unit="count",
                metric_value=Decimal(int(row.metric_value or 0)),
                source_watermark_at=_coerce_utc(row.source_watermark_at),
            )
            for row in result
        ]

    async def _collect_resolution_rows(
        self,
        *,
        start_date: date,
        end_date: date,
    ) -> list[GrowthReportingRollupWriteRow]:
        start_dt, end_dt = _date_window_to_datetimes(start_date=start_date, end_date=end_date)
        result = await self._session.execute(
            select(
                func.date(GrowthCodeResolutionEventModel.created_at).label("report_date"),
                func.coalesce(GrowthCodeResolutionEventModel.code_type, "unknown").label("report_family"),
                GrowthCodeResolutionEventModel.result.label("dimension_value"),
                func.count(GrowthCodeResolutionEventModel.id).label("metric_value"),
                func.max(GrowthCodeResolutionEventModel.created_at).label("source_watermark_at"),
            )
            .where(
                GrowthCodeResolutionEventModel.created_at >= start_dt,
                GrowthCodeResolutionEventModel.created_at < end_dt,
            )
            .group_by(
                func.date(GrowthCodeResolutionEventModel.created_at),
                func.coalesce(GrowthCodeResolutionEventModel.code_type, "unknown"),
                GrowthCodeResolutionEventModel.result,
            )
        )
        return [
            GrowthReportingRollupWriteRow(
                report_date=_coerce_report_date(row.report_date),
                report_family=str(row.report_family or "unknown"),
                metric_key="resolutions_total",
                metric_unit="count",
                metric_value=Decimal(int(row.metric_value or 0)),
                dimension_key="result",
                dimension_value=str(row.dimension_value or "unknown"),
                source_watermark_at=_coerce_utc(row.source_watermark_at),
            )
            for row in result
        ]

    async def _collect_reservation_rows(
        self,
        *,
        start_date: date,
        end_date: date,
    ) -> list[GrowthReportingRollupWriteRow]:
        start_dt, end_dt = _date_window_to_datetimes(start_date=start_date, end_date=end_date)
        rows: list[GrowthReportingRollupWriteRow] = []

        created_result = await self._session.execute(
            select(
                func.date(GrowthCodeReservationModel.reserved_at).label("report_date"),
                GrowthCodeModel.code_type.label("report_family"),
                func.count(GrowthCodeReservationModel.id).label("metric_value"),
                func.max(GrowthCodeReservationModel.reserved_at).label("source_watermark_at"),
            )
            .join(GrowthCodeModel, GrowthCodeModel.id == GrowthCodeReservationModel.growth_code_id)
            .where(
                GrowthCodeReservationModel.reserved_at >= start_dt,
                GrowthCodeReservationModel.reserved_at < end_dt,
            )
            .group_by(
                func.date(GrowthCodeReservationModel.reserved_at),
                GrowthCodeModel.code_type,
            )
        )
        rows.extend(
            GrowthReportingRollupWriteRow(
                report_date=_coerce_report_date(row.report_date),
                report_family=str(row.report_family or "unknown"),
                metric_key="reservations_total",
                metric_unit="count",
                metric_value=Decimal(int(row.metric_value or 0)),
                dimension_key="status_transition",
                dimension_value="reserved",
                source_watermark_at=_coerce_utc(row.source_watermark_at),
            )
            for row in created_result
        )

        transition_at = case(
            (
                GrowthCodeReservationModel.status.in_(("released", "cancelled")),
                func.coalesce(
                    GrowthCodeReservationModel.released_at,
                    GrowthCodeReservationModel.updated_at,
                ),
            ),
            else_=GrowthCodeReservationModel.updated_at,
        )
        transition_result = await self._session.execute(
            select(
                func.date(transition_at).label("report_date"),
                GrowthCodeModel.code_type.label("report_family"),
                GrowthCodeReservationModel.status.label("dimension_value"),
                func.count(GrowthCodeReservationModel.id).label("metric_value"),
                func.max(transition_at).label("source_watermark_at"),
            )
            .join(GrowthCodeModel, GrowthCodeModel.id == GrowthCodeReservationModel.growth_code_id)
            .where(
                GrowthCodeReservationModel.status.in_(("consumed", "expired", "released", "cancelled")),
                transition_at.is_not(None),
                transition_at >= start_dt,
                transition_at < end_dt,
            )
            .group_by(
                func.date(transition_at),
                GrowthCodeModel.code_type,
                GrowthCodeReservationModel.status,
            )
        )
        rows.extend(
            GrowthReportingRollupWriteRow(
                report_date=_coerce_report_date(row.report_date),
                report_family=str(row.report_family or "unknown"),
                metric_key="reservations_total",
                metric_unit="count",
                metric_value=Decimal(int(row.metric_value or 0)),
                dimension_key="status_transition",
                dimension_value=str(row.dimension_value or "unknown"),
                source_watermark_at=_coerce_utc(row.source_watermark_at),
            )
            for row in transition_result
        )

        return rows

    async def _collect_redemption_rows(
        self,
        *,
        start_date: date,
        end_date: date,
    ) -> list[GrowthReportingRollupWriteRow]:
        start_dt, end_dt = _date_window_to_datetimes(start_date=start_date, end_date=end_date)
        result = await self._session.execute(
            select(
                func.date(GrowthCodeRedemptionModel.redeemed_at).label("report_date"),
                GrowthCodeRedemptionModel.code_type.label("report_family"),
                func.count(GrowthCodeRedemptionModel.id).label("metric_value"),
                func.max(GrowthCodeRedemptionModel.redeemed_at).label("source_watermark_at"),
            )
            .where(
                GrowthCodeRedemptionModel.redeemed_at >= start_dt,
                GrowthCodeRedemptionModel.redeemed_at < end_dt,
            )
            .group_by(
                func.date(GrowthCodeRedemptionModel.redeemed_at),
                GrowthCodeRedemptionModel.code_type,
            )
        )
        return [
            GrowthReportingRollupWriteRow(
                report_date=_coerce_report_date(row.report_date),
                report_family=str(row.report_family or "unknown"),
                metric_key="redemptions_total",
                metric_unit="count",
                metric_value=Decimal(int(row.metric_value or 0)),
                source_watermark_at=_coerce_utc(row.source_watermark_at),
            )
            for row in result
        ]

    async def _collect_reward_rows(
        self,
        *,
        start_date: date,
        end_date: date,
    ) -> list[GrowthReportingRollupWriteRow]:
        start_dt, end_dt = _date_window_to_datetimes(start_date=start_date, end_date=end_date)
        rows: list[GrowthReportingRollupWriteRow] = []

        async def _collect_for_transition(
            *,
            timestamp_column,
            transition_key: str,
        ) -> list[GrowthReportingRollupWriteRow]:
            result = await self._session.execute(
                select(
                    func.date(timestamp_column).label("report_date"),
                    GrowthRewardAllocationModel.reward_type.label("reward_type"),
                    GrowthCodeModel.code_type.label("source_code_type"),
                    GrowthRewardAllocationModel.currency_code.label("currency_code"),
                    func.count(GrowthRewardAllocationModel.id).label("reward_count"),
                    func.coalesce(func.sum(GrowthRewardAllocationModel.quantity), 0).label("reward_amount"),
                    func.max(timestamp_column).label("source_watermark_at"),
                )
                .outerjoin(
                    GrowthCodeModel,
                    GrowthCodeModel.id == GrowthRewardAllocationModel.source_code_id,
                )
                .where(
                    timestamp_column.is_not(None),
                    timestamp_column >= start_dt,
                    timestamp_column < end_dt,
                )
                .group_by(
                    func.date(timestamp_column),
                    GrowthRewardAllocationModel.reward_type,
                    GrowthCodeModel.code_type,
                    GrowthRewardAllocationModel.currency_code,
                )
            )
            collected: list[GrowthReportingRollupWriteRow] = []
            for row in result:
                family = _resolve_reward_family(
                    reward_type=str(row.reward_type or "unknown"),
                    source_code_type=str(row.source_code_type) if row.source_code_type else None,
                )
                report_date = _coerce_report_date(row.report_date)
                source_watermark_at = _coerce_utc(row.source_watermark_at)
                collected.append(
                    GrowthReportingRollupWriteRow(
                        report_date=report_date,
                        report_family=family,
                        metric_key="rewards_total",
                        metric_unit="count",
                        metric_value=Decimal(int(row.reward_count or 0)),
                        dimension_key="status_transition",
                        dimension_value=transition_key,
                        source_watermark_at=source_watermark_at,
                    )
                )
                currency_code = str(row.currency_code or "").upper()
                if currency_code == "USD":
                    collected.append(
                        GrowthReportingRollupWriteRow(
                            report_date=report_date,
                            report_family=family,
                            metric_key="reward_amount_usd_total",
                            metric_unit="usd",
                            metric_value=Decimal(str(row.reward_amount or 0)),
                            dimension_key="status_transition",
                            dimension_value=transition_key,
                            currency_code="USD",
                            source_watermark_at=source_watermark_at,
                        )
                    )
            return collected

        rows.extend(
            await _collect_for_transition(
                timestamp_column=GrowthRewardAllocationModel.allocated_at,
                transition_key="created",
            )
        )
        rows.extend(
            await _collect_for_transition(
                timestamp_column=GrowthRewardAllocationModel.available_at,
                transition_key="available",
            )
        )
        rows.extend(
            await _collect_for_transition(
                timestamp_column=GrowthRewardAllocationModel.reversed_at,
                transition_key="reversed",
            )
        )
        return rows


class GetGrowthReportingOverviewUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._rollups = GrowthReportingRollupRepository(session)
        self._runs = GrowthReportingRefreshRunRepository(session)

    async def execute(
        self,
        *,
        window_days: int = 14,
        end_date: date | None = None,
    ) -> GrowthReportingOverview:
        resolved_end = end_date or datetime.now(UTC).date()
        resolved_window_days = max(window_days, 1)
        resolved_start = resolved_end - timedelta(days=resolved_window_days - 1)
        rows = await self._rollups.list_window(start_date=resolved_start, end_date=resolved_end)
        refreshed_at = await self._rollups.get_latest_refresh_time(start_date=resolved_start, end_date=resolved_end)
        latest_rollup_date = max((row.report_date for row in rows), default=None)
        latest_run_model = await self._runs.get_latest()
        latest_success_model = await self._runs.get_latest_by_status("success")
        latest_failure_model = await self._runs.get_latest_by_status("failed")

        observed_families = {row.report_family for row in rows}
        family_order = [
            family
            for family in (*_CANONICAL_FAMILIES, *sorted(observed_families - set(_CANONICAL_FAMILIES)))
            if family in observed_families
        ]

        daily_buckets: dict[tuple[date, str], GrowthReportingBucket] = {}
        family_buckets: dict[str, GrowthReportingBucket] = {}
        total_bucket = GrowthReportingBucket()

        for row in rows:
            daily_bucket = daily_buckets.setdefault((row.report_date, row.report_family), GrowthReportingBucket())
            family_bucket = family_buckets.setdefault(row.report_family, GrowthReportingBucket())
            _apply_rollup_row(bucket=daily_bucket, row=row)
            _apply_rollup_row(bucket=family_bucket, row=row)
            _apply_rollup_row(bucket=total_bucket, row=row)

        family_summaries = [
            _build_family_summary(family=family, bucket=family_buckets.get(family, GrowthReportingBucket()))
            for family in family_order
        ]
        daily_points = [
            _build_daily_point(report_date=report_date, family=family, bucket=bucket)
            for (report_date, family), bucket in sorted(daily_buckets.items())
        ]
        totals = _build_family_summary(family="all", bucket=total_bucket)
        health = _build_reporting_health(
            latest_run=_serialize_refresh_run_model(latest_run_model),
            latest_success=_serialize_refresh_run_model(latest_success_model),
            latest_failure=_serialize_refresh_run_model(latest_failure_model),
        )
        executive_summary = _build_executive_summary(
            totals=totals,
            family_summaries=family_summaries,
        )

        return GrowthReportingOverview(
            window_start=resolved_start,
            window_end=resolved_end,
            latest_rollup_date=latest_rollup_date,
            refreshed_at=refreshed_at,
            family_summaries=family_summaries,
            daily_points=daily_points,
            totals=totals,
            health=health,
            executive_summary=executive_summary,
            coverage_notes=list(_COVERAGE_NOTES),
        )


class ExportGrowthReportingOverviewUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._rollups = GrowthReportingRollupRepository(session)
        self._overview = GetGrowthReportingOverviewUseCase(session)

    async def execute(
        self,
        *,
        window_days: int = 14,
        end_date: date | None = None,
    ) -> GrowthReportingExport:
        overview = await self._overview.execute(window_days=window_days, end_date=end_date)
        raw_models = await self._rollups.list_window(
            start_date=overview.window_start,
            end_date=overview.window_end,
        )
        raw_rows = [
            {
                "report_date": row.report_date.isoformat(),
                "report_family": row.report_family,
                "metric_key": row.metric_key,
                "metric_unit": row.metric_unit,
                "dimension_key": row.dimension_key,
                "dimension_value": row.dimension_value,
                "metric_value": float(row.metric_value),
                "currency_code": row.currency_code or None,
                "source_watermark_at": row.source_watermark_at.isoformat() if row.source_watermark_at else None,
                "refreshed_at": row.refreshed_at.isoformat(),
            }
            for row in raw_models
        ]
        return GrowthReportingExport(overview=overview, raw_rows=raw_rows)


def _date_window_to_datetimes(*, start_date: date, end_date: date) -> tuple[datetime, datetime]:
    start_dt = datetime.combine(start_date, datetime.min.time(), tzinfo=UTC)
    end_dt = datetime.combine(end_date + timedelta(days=1), datetime.min.time(), tzinfo=UTC)
    return start_dt, end_dt


def _coerce_report_date(value: object) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        return date.fromisoformat(value)
    raise TypeError(f"Unsupported report_date value: {value!r}")


def _coerce_utc(value: datetime | str | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, str):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _resolve_reward_family(*, reward_type: str, source_code_type: str | None) -> str:
    if source_code_type:
        return source_code_type
    if reward_type == "referral_credit":
        return "referral"
    if reward_type.startswith("invite"):
        return "invite"
    if reward_type.startswith("gift"):
        return "gift"
    return "reward"


def _apply_rollup_row(
    *,
    bucket: GrowthReportingBucket,
    row,
) -> None:
    metric_value = float(row.metric_value or 0)
    dimension_value = row.dimension_value or ""

    if row.metric_key == "codes_issued_total":
        bucket.issued_total += int(metric_value)
        return
    if row.metric_key == "resolutions_total":
        bucket.resolution_attempts_total += int(metric_value)
        if dimension_value == "accepted":
            bucket.resolution_accepted_total += int(metric_value)
        else:
            bucket.resolution_rejected_total += int(metric_value)
        return
    if row.metric_key == "redemptions_total":
        bucket.redemption_total += int(metric_value)
        return
    if row.metric_key == "reservations_total":
        if dimension_value == "reserved":
            bucket.reservations_reserved_total += int(metric_value)
        elif dimension_value == "consumed":
            bucket.reservations_consumed_total += int(metric_value)
        elif dimension_value in {"released", "cancelled"}:
            bucket.reservations_released_total += int(metric_value)
        elif dimension_value == "expired":
            bucket.reservations_expired_total += int(metric_value)
        return
    if row.metric_key == "rewards_total":
        if dimension_value == "created":
            bucket.rewards_created_total += int(metric_value)
        elif dimension_value == "available":
            bucket.rewards_available_total += int(metric_value)
        elif dimension_value == "reversed":
            bucket.rewards_reversed_total += int(metric_value)
        return
    if row.metric_key == "reward_amount_usd_total":
        if dimension_value == "created":
            bucket.reward_created_amount_usd += metric_value
        elif dimension_value == "available":
            bucket.reward_available_amount_usd += metric_value
        elif dimension_value == "reversed":
            bucket.reward_reversed_amount_usd += metric_value


def _build_family_summary(*, family: str, bucket: GrowthReportingBucket) -> GrowthReportingFamilySummary:
    return GrowthReportingFamilySummary(
        family=family,
        issued_total=bucket.issued_total,
        resolution_attempts_total=bucket.resolution_attempts_total,
        resolution_accepted_total=bucket.resolution_accepted_total,
        resolution_rejected_total=bucket.resolution_rejected_total,
        redemption_total=bucket.redemption_total,
        reservations_reserved_total=bucket.reservations_reserved_total,
        reservations_consumed_total=bucket.reservations_consumed_total,
        reservations_released_total=bucket.reservations_released_total,
        reservations_expired_total=bucket.reservations_expired_total,
        rewards_created_total=bucket.rewards_created_total,
        rewards_available_total=bucket.rewards_available_total,
        rewards_reversed_total=bucket.rewards_reversed_total,
        reward_created_amount_usd=round(bucket.reward_created_amount_usd, 2),
        reward_available_amount_usd=round(bucket.reward_available_amount_usd, 2),
        reward_reversed_amount_usd=round(bucket.reward_reversed_amount_usd, 2),
    )


def _build_daily_point(
    *,
    report_date: date,
    family: str,
    bucket: GrowthReportingBucket,
) -> GrowthReportingDailyPoint:
    summary = _build_family_summary(family=family, bucket=bucket)
    return GrowthReportingDailyPoint(report_date=report_date, **summary.__dict__)


def _serialize_refresh_run_model(model) -> GrowthReportingRefreshRunSummary | None:
    if model is None:
        return None
    return GrowthReportingRefreshRunSummary(
        id=str(model.id),
        trigger_kind=str(model.trigger_kind),
        refresh_status=str(model.refresh_status),
        requested_window_days=int(model.requested_window_days),
        window_start=model.window_start,
        window_end=model.window_end,
        latest_rollup_date=model.latest_rollup_date,
        rows_written=int(model.rows_written or 0),
        families_updated=list(model.normalized_families_updated()),
        error_message=model.error_message,
        started_at=_coerce_utc(model.started_at) or datetime.now(UTC),
        finished_at=_coerce_utc(model.finished_at) or datetime.now(UTC),
        refreshed_at=_coerce_utc(model.refreshed_at),
    )


def _build_reporting_health(
    *,
    latest_run: GrowthReportingRefreshRunSummary | None,
    latest_success: GrowthReportingRefreshRunSummary | None,
    latest_failure: GrowthReportingRefreshRunSummary | None,
) -> GrowthReportingHealth:
    now = datetime.now(UTC)
    latest_success_at = latest_success.refreshed_at if latest_success is not None else None
    refresh_age_seconds = (
        max(int((now - latest_success_at).total_seconds()), 0)
        if latest_success_at is not None
        else None
    )

    freshness_status = "fresh"
    stale_reason: str | None = None
    if latest_run is None:
        freshness_status = "never_refreshed"
        stale_reason = "no_refresh_runs_recorded"
    elif latest_run.refresh_status == "failed":
        freshness_status = "failed"
        stale_reason = "latest_refresh_run_failed"
    elif refresh_age_seconds is None:
        freshness_status = "never_refreshed"
        stale_reason = "no_successful_refresh_recorded"
    elif refresh_age_seconds > _STALE_AFTER_SECONDS:
        freshness_status = "stale"
        stale_reason = "refresh_lag_exceeded"

    return GrowthReportingHealth(
        freshness_status=freshness_status,
        stale_reason=stale_reason,
        refresh_age_seconds=refresh_age_seconds,
        expected_refresh_interval_seconds=_EXPECTED_REFRESH_INTERVAL_SECONDS,
        stale_after_seconds=_STALE_AFTER_SECONDS,
        auto_refresh_enabled=_AUTO_REFRESH_ENABLED,
        latest_attempt_at=latest_run.finished_at if latest_run is not None else None,
        latest_success_at=latest_success_at,
        latest_failure_at=latest_failure.finished_at if latest_failure is not None else None,
        latest_failure_message=latest_failure.error_message if latest_failure is not None else None,
        latest_run=latest_run,
    )


def _build_executive_summary(
    *,
    totals: GrowthReportingFamilySummary,
    family_summaries: list[GrowthReportingFamilySummary],
) -> GrowthReportingExecutiveSummary:
    dominant_family = None
    if family_summaries:
        dominant = max(
            family_summaries,
            key=lambda item: (
                item.redemption_total
                + item.resolution_attempts_total
                + item.issued_total
                + item.rewards_available_total
            ),
        )
        dominant_family = dominant.family

    acceptance_rate_pct = 0.0
    if totals.resolution_attempts_total > 0:
        acceptance_rate_pct = round(
            (totals.resolution_accepted_total / totals.resolution_attempts_total) * 100,
            1,
        )

    highlights = [
        f"Acceptance rate {acceptance_rate_pct:.1f}% over the selected reporting window.",
        f"Available referral and growth rewards total ${totals.reward_available_amount_usd:.2f}.",
    ]
    if dominant_family is not None:
        highlights.append(f"Most active family in this window: {dominant_family}.")
    if totals.reward_reversed_amount_usd > 0:
        highlights.append(
            f"Reversed reward volume reached ${totals.reward_reversed_amount_usd:.2f}; review risk and refund posture.",
        )

    return GrowthReportingExecutiveSummary(
        total_issued=totals.issued_total,
        total_redemptions=totals.redemption_total,
        total_reward_available_usd=round(totals.reward_available_amount_usd, 2),
        total_reward_reversed_usd=round(totals.reward_reversed_amount_usd, 2),
        resolution_acceptance_rate_pct=acceptance_rate_pct,
        dominant_family=dominant_family,
        highlights=highlights,
    )
