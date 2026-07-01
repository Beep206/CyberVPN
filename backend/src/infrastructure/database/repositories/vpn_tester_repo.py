"""Persistence repository for CyberVPN VPN Tester."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.infrastructure.database.models.subscription_plan_model import SubscriptionPlanModel
from src.infrastructure.database.models.vpn_tester_model import (
    VpnBalancerRecommendationModel,
    VpnRouteRegistryEntryModel,
    VpnTestEvidenceArtifactModel,
    VpnTestReleaseGateOverrideModel,
    VpnTestResultModel,
    VpnTestRunModel,
    VpnTestScheduleModel,
    VpnTestSuiteModel,
)


class VpnTesterRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_suite(self, suite_key: str, version: str = "v1") -> VpnTestSuiteModel | None:
        result = await self._session.execute(
            select(VpnTestSuiteModel).where(
                VpnTestSuiteModel.suite_key == suite_key,
                VpnTestSuiteModel.version == version,
            )
        )
        return result.scalars().first()

    async def upsert_suite(self, payload: dict) -> VpnTestSuiteModel:
        suite = await self.get_suite(str(payload["suite_key"]), str(payload.get("version") or "v1"))
        if suite is None:
            suite = VpnTestSuiteModel(
                suite_key=str(payload["suite_key"]),
                version=str(payload.get("version") or "v1"),
                display_name=str(payload.get("display_name") or payload["suite_key"]),
                mode=str(payload.get("mode") or "contract"),
                description=str(payload.get("description") or ""),
                spec=dict(payload),
                enabled=True,
            )
            self._session.add(suite)
        else:
            suite.display_name = str(payload.get("display_name") or suite.display_name)
            suite.mode = str(payload.get("mode") or suite.mode)
            suite.description = str(payload.get("description") or suite.description)
            suite.spec = dict(payload)
            suite.enabled = True
        await self._session.flush()
        return suite

    async def upsert_route_registry_entry(self, registry: dict, route: dict) -> VpnRouteRegistryEntryModel:
        registry_key = str(registry["registry_key"])
        route_key = str(route["route_key"])
        result = await self._session.execute(
            select(VpnRouteRegistryEntryModel).where(
                VpnRouteRegistryEntryModel.registry_key == registry_key,
                VpnRouteRegistryEntryModel.route_key == route_key,
            )
        )
        entry = result.scalars().first()
        if entry is None:
            entry = VpnRouteRegistryEntryModel(registry_key=registry_key, route_key=route_key)
            self._session.add(entry)
        entry.suite_key = str(registry["suite_key"])
        entry.country_code = str(route.get("country_code") or "")
        entry.node_tags = [str(item) for item in route.get("node_tags") or []]
        entry.expected_modes = [str(item) for item in route.get("expected_modes") or []]
        entry.metadata_json = dict(route.get("metadata") or {})
        entry.enabled = True
        await self._session.flush()
        return entry

    async def upsert_schedule(self, payload: dict) -> VpnTestScheduleModel:
        schedule_key = str(payload["schedule_key"])
        result = await self._session.execute(
            select(VpnTestScheduleModel).where(VpnTestScheduleModel.schedule_key == schedule_key)
        )
        schedule = result.scalars().first()
        created = schedule is None
        if schedule is None:
            schedule = VpnTestScheduleModel(schedule_key=schedule_key)
            self._session.add(schedule)
        schedule.suite_key = str(payload["suite_key"])
        schedule.mode = str(payload.get("mode") or "contract")
        schedule.cron = str(payload["cron"])
        schedule.schedule_source = str(
            payload.get("schedule_source") or getattr(schedule, "schedule_source", None) or "seeded"
        )
        if created:
            schedule.enabled = bool(payload.get("enabled", False))
            schedule.settings = dict(payload.get("settings") or {})
        elif schedule.settings is None:
            schedule.settings = dict(payload.get("settings") or {})
        await self._session.flush()
        return schedule

    async def list_schedules(self) -> list[VpnTestScheduleModel]:
        result = await self._session.execute(select(VpnTestScheduleModel).order_by(VpnTestScheduleModel.schedule_key))
        return list(result.scalars().all())

    async def get_schedule(self, schedule_key: str) -> VpnTestScheduleModel | None:
        result = await self._session.execute(
            select(VpnTestScheduleModel).where(VpnTestScheduleModel.schedule_key == schedule_key)
        )
        return result.scalars().first()

    async def update_schedule(
        self, schedule_key: str, *, enabled: bool, settings: dict | None = None
    ) -> VpnTestScheduleModel | None:
        result = await self._session.execute(
            select(VpnTestScheduleModel).where(VpnTestScheduleModel.schedule_key == schedule_key)
        )
        schedule = result.scalars().first()
        if schedule is None:
            return None
        schedule.enabled = enabled
        if settings is not None:
            schedule.settings = settings
        await self._session.flush()
        return schedule

    async def update_schedule_gate_state(
        self,
        schedule: VpnTestScheduleModel,
        *,
        checked_at: datetime,
        triggered_at: datetime | None = None,
        last_run_id: UUID | None = None,
        last_status: str | None = None,
        skipped_reason: str | None = None,
        next_run_at: datetime | None = None,
    ) -> VpnTestScheduleModel:
        schedule.last_checked_at = checked_at
        schedule.last_triggered_at = triggered_at or schedule.last_triggered_at
        schedule.last_run_id = last_run_id if last_run_id is not None else schedule.last_run_id
        schedule.last_status = last_status if last_status is not None else schedule.last_status
        schedule.last_skipped_reason = skipped_reason
        schedule.next_run_at = next_run_at if next_run_at is not None else schedule.next_run_at
        await self._session.flush()
        return schedule

    async def create_run(
        self,
        *,
        suite_key: str,
        suite_version: str,
        mode: str,
        trigger: str,
        requested_by_admin_id: UUID | None,
        idempotency_key: str | None,
        request_context: dict,
        agent_id: str | None = None,
        runtime_mode: str | None = None,
        route_registry_version: str | None = None,
    ) -> VpnTestRunModel:
        if idempotency_key:
            result = await self._session.execute(
                select(VpnTestRunModel).where(VpnTestRunModel.idempotency_key == idempotency_key)
            )
            existing = result.scalars().first()
            if existing is not None:
                return existing
        run = VpnTestRunModel(
            suite_key=suite_key,
            suite_version=suite_version,
            mode=mode,
            trigger=trigger,
            requested_by_admin_id=requested_by_admin_id,
            idempotency_key=idempotency_key,
            request_context=request_context,
            agent_id=agent_id,
            runtime_mode=runtime_mode,
            route_registry_version=route_registry_version,
            status="queued",
            summary={"queued_for": "task_worker"},
        )
        self._session.add(run)
        await self._session.flush()
        return run

    async def get_run(self, run_id: UUID) -> VpnTestRunModel | None:
        result = await self._session.execute(
            select(VpnTestRunModel)
            .where(VpnTestRunModel.id == run_id)
            .options(
                selectinload(VpnTestRunModel.results),
                selectinload(VpnTestRunModel.evidence_artifacts),
            )
        )
        return result.scalars().first()

    async def list_runs(self, *, limit: int = 25, status: str | None = None) -> list[VpnTestRunModel]:
        stmt = select(VpnTestRunModel).order_by(VpnTestRunModel.created_at.desc()).limit(max(1, min(limit, 100)))
        if status:
            stmt = stmt.where(VpnTestRunModel.status == status)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def claim_queued_run(self) -> VpnTestRunModel | None:
        result = await self._session.execute(
            select(VpnTestRunModel)
            .where(VpnTestRunModel.status == "queued")
            .order_by(VpnTestRunModel.created_at.asc())
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        run = result.scalars().first()
        if run is None:
            return None
        run.status = "running"
        run.started_at = datetime.now(UTC)
        await self._session.flush()
        return run

    async def mark_run_running(self, run: VpnTestRunModel) -> None:
        run.status = "running"
        run.started_at = run.started_at or datetime.now(UTC)
        await self._session.flush()

    async def replace_run_results(
        self,
        run: VpnTestRunModel,
        *,
        results: list[dict],
        evidence: list[dict],
        summary: dict,
        status: str,
    ) -> VpnTestRunModel:
        await self._session.execute(delete(VpnTestResultModel).where(VpnTestResultModel.run_id == run.id))
        await self._session.execute(
            delete(VpnTestEvidenceArtifactModel).where(VpnTestEvidenceArtifactModel.run_id == run.id)
        )
        for item in results:
            self._session.add(VpnTestResultModel(run_id=run.id, **item))
        for item in evidence:
            self._session.add(VpnTestEvidenceArtifactModel(run_id=run.id, **item))
        run.pass_count = sum(1 for item in results if item["status"] == "pass")
        run.fail_count = sum(1 for item in results if item["status"] == "fail")
        run.degraded_count = sum(1 for item in results if item["status"] == "degraded")
        run.status = status
        run.summary = summary
        run.blocking = status in {"fail", "queued", "running"}
        run.finished_at = datetime.now(UTC)
        await self._session.flush()
        return run

    async def cancel_run(self, run: VpnTestRunModel) -> VpnTestRunModel:
        if run.status in {"queued", "running"}:
            run.status = "cancelled"
            run.finished_at = datetime.now(UTC)
            run.summary = {**dict(run.summary or {}), "cancelled": True}
            await self._session.flush()
        return run

    async def list_active_plans(self) -> list[SubscriptionPlanModel]:
        result = await self._session.execute(
            select(SubscriptionPlanModel)
            .where(SubscriptionPlanModel.is_active.is_(True))
            .order_by(SubscriptionPlanModel.sort_order.asc(), SubscriptionPlanModel.name.asc())
        )
        return list(result.scalars().all())

    async def get_route_registry(
        self, suite_key: str, registry_key: str | None = None
    ) -> list[VpnRouteRegistryEntryModel]:
        stmt = select(VpnRouteRegistryEntryModel).where(
            VpnRouteRegistryEntryModel.suite_key == suite_key,
            VpnRouteRegistryEntryModel.enabled.is_(True),
        )
        if registry_key:
            stmt = stmt.where(VpnRouteRegistryEntryModel.registry_key == registry_key)
        result = await self._session.execute(stmt.order_by(VpnRouteRegistryEntryModel.route_key.asc()))
        return list(result.scalars().all())

    async def overview_counts(self) -> dict[str, int]:
        result = await self._session.execute(
            select(VpnTestRunModel.status, func.count()).group_by(VpnTestRunModel.status)
        )
        counts = {str(status): int(count) for status, count in result.all()}
        counts["total"] = sum(counts.values())
        return counts

    async def cleanup_expired_evidence(self) -> int:
        cutoff = datetime.now(UTC)
        result = await self._session.execute(
            delete(VpnTestEvidenceArtifactModel).where(
                VpnTestEvidenceArtifactModel.expires_at.is_not(None),
                VpnTestEvidenceArtifactModel.expires_at < cutoff,
            )
        )
        await self._session.flush()
        return int(result.rowcount or 0)

    async def create_balancer_recommendation(
        self,
        run: VpnTestRunModel | None,
        *,
        recommendation_key: str,
        recommendation_hash: str,
        scope: str,
        summary: str,
        payload: dict,
        confidence: float,
    ) -> VpnBalancerRecommendationModel:
        result = await self._session.execute(
            select(VpnBalancerRecommendationModel).where(
                VpnBalancerRecommendationModel.recommendation_hash == recommendation_hash
            )
        )
        recommendation = result.scalars().first()
        if recommendation is None:
            recommendation = VpnBalancerRecommendationModel(
                recommendation_key=recommendation_key,
                recommendation_hash=recommendation_hash,
                run_id=run.id if run is not None else None,
                scope=scope,
                status="open",
                safe_summary=summary,
                candidate_changes=payload,
                confidence=confidence,
                expires_at=datetime.now(UTC) + timedelta(days=7),
            )
            self._session.add(recommendation)
        else:
            recommendation.run_id = run.id if run is not None else recommendation.run_id
            recommendation.safe_summary = summary
            recommendation.candidate_changes = payload
            recommendation.confidence = confidence
            recommendation.expires_at = datetime.now(UTC) + timedelta(days=7)
            if recommendation.status == "expired":
                recommendation.status = "open"
        await self._session.flush()
        return recommendation

    async def list_balancer_recommendations(
        self, *, limit: int = 50, include_terminal: bool = False
    ) -> list[VpnBalancerRecommendationModel]:
        now = datetime.now(UTC)
        expired_result = await self._session.execute(
            select(VpnBalancerRecommendationModel).where(
                VpnBalancerRecommendationModel.status == "open",
                VpnBalancerRecommendationModel.expires_at.is_not(None),
                VpnBalancerRecommendationModel.expires_at < now,
            )
        )
        for expired in expired_result.scalars().all():
            expired.status = "expired"
        stmt = select(VpnBalancerRecommendationModel).order_by(VpnBalancerRecommendationModel.updated_at.desc())
        if not include_terminal:
            stmt = stmt.where(
                or_(
                    VpnBalancerRecommendationModel.status.in_(["open", "acknowledged"]),
                    VpnBalancerRecommendationModel.expires_at > now,
                    VpnBalancerRecommendationModel.expires_at.is_(None),
                )
            )
        result = await self._session.execute(stmt.limit(max(1, min(limit, 100))))
        return list(result.scalars().all())

    async def set_balancer_recommendation_status(
        self,
        recommendation_id: UUID,
        *,
        status: str,
        admin_id: UUID,
        reason: str | None = None,
    ) -> VpnBalancerRecommendationModel | None:
        result = await self._session.execute(
            select(VpnBalancerRecommendationModel).where(VpnBalancerRecommendationModel.id == recommendation_id)
        )
        recommendation = result.scalars().first()
        if recommendation is None:
            return None
        now = datetime.now(UTC)
        recommendation.status = status
        if status == "acknowledged":
            recommendation.acknowledged_by_admin_id = admin_id
            recommendation.acknowledged_at = now
        elif status == "dismissed":
            recommendation.dismissed_by_admin_id = admin_id
            recommendation.dismissed_at = now
            recommendation.dismissed_reason = reason
        elif status == "applied_manually":
            recommendation.applied_manually_by_admin_id = admin_id
            recommendation.applied_manually_at = now
        await self._session.flush()
        return recommendation

    async def get_active_release_gate_override(
        self, now: datetime | None = None
    ) -> VpnTestReleaseGateOverrideModel | None:
        now = now or datetime.now(UTC)
        result = await self._session.execute(
            select(VpnTestReleaseGateOverrideModel)
            .where(VpnTestReleaseGateOverrideModel.expires_at > now)
            .order_by(VpnTestReleaseGateOverrideModel.created_at.desc())
            .limit(1)
        )
        return result.scalars().first()

    async def create_release_gate_override(
        self,
        *,
        latest_run_id: UUID | None,
        overridden_by_admin_id: UUID,
        previous_status: str,
        previous_blocking: bool,
        reason: str,
        expires_at: datetime,
        request_context: dict,
    ) -> VpnTestReleaseGateOverrideModel:
        override = VpnTestReleaseGateOverrideModel(
            latest_run_id=latest_run_id,
            overridden_by_admin_id=overridden_by_admin_id,
            previous_status=previous_status,
            previous_blocking=previous_blocking,
            reason=reason,
            expires_at=expires_at,
            request_context=request_context,
        )
        self._session.add(override)
        await self._session.flush()
        return override
