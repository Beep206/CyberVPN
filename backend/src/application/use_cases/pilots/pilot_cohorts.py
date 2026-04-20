from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.events.outbox import EventOutboxService, OutboxActorContext
from src.domain.enums import (
    GovernanceActionStatus,
    GovernanceActionType,
    PartnerAccountStatus,
    PilotCohortStatus,
    PilotGateStatus,
    PilotGoNoGoStatus,
    PilotLaneKey,
    PilotOwnerAcknowledgementStatus,
    PilotOwnerTeam,
    PilotRollbackDrillStatus,
    PilotRollbackScopeClass,
    PilotRolloutWindowKind,
    PilotRolloutWindowStatus,
    PilotSurfaceKey,
    PrincipalClass,
    RiskReviewDecision,
    RiskReviewStatus,
    TrafficDeclarationStatus,
)
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.creative_approval_model import CreativeApprovalModel
from src.infrastructure.database.models.governance_action_model import GovernanceActionModel
from src.infrastructure.database.models.partner_traffic_declaration_model import (
    PartnerTrafficDeclarationModel,
)
from src.infrastructure.database.models.pilot_cohort_model import (
    PilotCohortModel,
    PilotGoNoGoDecisionModel,
    PilotOwnerAcknowledgementModel,
    PilotRollbackDrillModel,
    PilotRolloutWindowModel,
)
from src.infrastructure.database.models.risk_review_model import RiskReviewModel
from src.infrastructure.database.repositories.governance_repo import GovernanceRepository
from src.infrastructure.database.repositories.partner_account_repository import PartnerAccountRepository
from src.infrastructure.database.repositories.pilot_cohort_repo import PilotCohortRepository
from src.infrastructure.database.repositories.risk_subject_repo import RiskSubjectGraphRepository

_PARTNER_REQUIRED_LANES = {
    PilotLaneKey.CREATOR_AFFILIATE,
    PilotLaneKey.PERFORMANCE_MEDIA_BUYER,
    PilotLaneKey.RESELLER_DISTRIBUTION,
}

_PAYOUT_BEARING_LANES = {
    PilotLaneKey.CREATOR_AFFILIATE,
    PilotLaneKey.PERFORMANCE_MEDIA_BUYER,
    PilotLaneKey.RESELLER_DISTRIBUTION,
}

_HOST_SURFACES = {
    PilotSurfaceKey.OFFICIAL_WEB,
    PilotSurfaceKey.PARTNER_STOREFRONT,
}

_WORKSPACE_SURFACES = {
    PilotSurfaceKey.PARTNER_PORTAL,
}

_CHANNEL_SURFACES = {
    PilotSurfaceKey.MINIAPP,
    PilotSurfaceKey.TELEGRAM_BOT,
    PilotSurfaceKey.DESKTOP_CLIENT,
}

_PARTNER_SURFACES = {
    PilotSurfaceKey.PARTNER_STOREFRONT,
    PilotSurfaceKey.PARTNER_PORTAL,
}

_BLOCKING_GOVERNANCE_ACTIONS = {
    GovernanceActionType.TRAFFIC_PROBATION.value,
    GovernanceActionType.CREATIVE_RESTRICTION.value,
    GovernanceActionType.PAYOUT_FREEZE.value,
}

_RUNBOOK_BLOCKING_CODES = {
    "owner_acknowledgement_missing",
    "rollback_drill_missing",
    "rollback_drill_failed",
    "go_no_go_missing",
    "go_no_go_hold",
    "go_no_go_no_go",
}


@dataclass(frozen=True)
class PilotCohortSnapshot:
    cohort: PilotCohortModel
    windows: list[PilotRolloutWindowModel]


@dataclass(frozen=True)
class PilotCohortReadinessResult:
    cohort: PilotCohortModel
    windows: list[PilotRolloutWindowModel]
    activation_allowed: bool
    blocking_reason_codes: list[str]
    warning_reason_codes: list[str]
    blocking_risk_review_ids: list[UUID]
    blocking_governance_action_ids: list[UUID]
    runbook_gate_status: str
    required_owner_teams: list[str]
    acknowledged_owner_teams: list[str]
    missing_owner_teams: list[str]
    latest_rollback_drill: PilotRollbackDrillModel | None
    latest_go_no_go_decision: PilotGoNoGoDecisionModel | None
    live_monitoring_snapshot: dict[str, Any]
    checked_at: datetime


class CreatePilotCohortUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = PilotCohortRepository(session)
        self._partners = PartnerAccountRepository(session)
        self._outbox = EventOutboxService(session)

    async def execute(
        self,
        *,
        cohort_key: str,
        display_name: str,
        lane_key: str,
        surface_key: str,
        partner_account_id: UUID | None,
        owner_team: str,
        owner_admin_user_id: UUID,
        rollback_trigger_code: str,
        shadow_gate_payload: dict[str, Any],
        monitoring_payload: dict[str, Any] | None,
        notes: list[str] | None,
        rollout_windows: list[dict[str, Any]],
        created_by_admin_user_id: UUID | None,
    ) -> PilotCohortSnapshot:
        normalized_key = cohort_key.strip()
        normalized_name = display_name.strip()
        normalized_owner_team = owner_team.strip()
        normalized_rollback_trigger = rollback_trigger_code.strip()
        if not normalized_key:
            raise ValueError("cohort_key is required")
        if not normalized_name:
            raise ValueError("display_name is required")
        if not normalized_owner_team:
            raise ValueError("owner_team is required")
        if not normalized_rollback_trigger:
            raise ValueError("rollback_trigger_code is required")

        lane = PilotLaneKey(lane_key)
        surface = PilotSurfaceKey(surface_key)
        await self._validate_admin_user(owner_admin_user_id)
        await self._validate_partner_scope(lane=lane, surface=surface, partner_account_id=partner_account_id)
        await self._validate_unique_key(normalized_key)

        validated_shadow_gate_payload = _validate_shadow_gate_payload(shadow_gate_payload)
        validated_windows = _validate_rollout_windows(
            rollout_windows=rollout_windows,
            surface=surface,
            partner_account_id=partner_account_id,
        )

        model = PilotCohortModel(
            cohort_key=normalized_key,
            display_name=normalized_name,
            lane_key=lane.value,
            surface_key=surface.value,
            cohort_status=PilotCohortStatus.SCHEDULED.value,
            partner_account_id=partner_account_id,
            owner_team=normalized_owner_team,
            owner_admin_user_id=owner_admin_user_id,
            rollback_trigger_code=normalized_rollback_trigger,
            shadow_gate_payload=validated_shadow_gate_payload,
            monitoring_payload=dict(monitoring_payload or {}),
            notes_payload=_normalize_string_list(notes),
            scheduled_start_at=min(window["starts_at"] for window in validated_windows),
            scheduled_end_at=max(window["ends_at"] for window in validated_windows),
            created_by_admin_user_id=created_by_admin_user_id,
        )
        created = await self._repo.create_pilot_cohort(model)
        windows: list[PilotRolloutWindowModel] = []
        for window in validated_windows:
            created_window = await self._repo.create_pilot_rollout_window(
                PilotRolloutWindowModel(
                    pilot_cohort_id=created.id,
                    window_kind=window["window_kind"],
                    target_ref=window["target_ref"],
                    window_status=PilotRolloutWindowStatus.SCHEDULED.value,
                    starts_at=window["starts_at"],
                    ends_at=window["ends_at"],
                    notes_payload=list(window["notes"]),
                    created_by_admin_user_id=created_by_admin_user_id,
                )
            )
            windows.append(created_window)

        await self._outbox.append_event(
            event_name="rollout.pilot_cohort.created",
            aggregate_type="pilot_cohort",
            aggregate_id=str(created.id),
            event_payload={
                "pilot_cohort_id": str(created.id),
                "cohort_key": created.cohort_key,
                "lane_key": created.lane_key,
                "surface_key": created.surface_key,
                "cohort_status": created.cohort_status,
                "partner_account_id": str(created.partner_account_id) if created.partner_account_id else None,
                "window_ids": [str(window.id) for window in windows],
                "shadow_gate_payload": validated_shadow_gate_payload,
            },
            actor_context=OutboxActorContext(
                principal_type=PrincipalClass.ADMIN.value,
                principal_id=str(created_by_admin_user_id) if created_by_admin_user_id else None,
            ),
        )
        await self._session.commit()
        await self._session.refresh(created)
        for window in windows:
            await self._session.refresh(window)
        return PilotCohortSnapshot(cohort=created, windows=windows)

    async def _validate_admin_user(self, admin_user_id: UUID) -> None:
        admin_user = await self._session.get(AdminUserModel, admin_user_id)
        if admin_user is None:
            raise ValueError("owner_admin_user_id references an unknown admin user")

    async def _validate_partner_scope(
        self,
        *,
        lane: PilotLaneKey,
        surface: PilotSurfaceKey,
        partner_account_id: UUID | None,
    ) -> None:
        if lane in _PARTNER_REQUIRED_LANES and partner_account_id is None:
            raise ValueError(f"{lane.value} pilot cohorts require partner_account_id")
        if surface in _PARTNER_SURFACES and partner_account_id is None:
            raise ValueError(f"{surface.value} pilot cohorts require partner_account_id")
        if partner_account_id is None:
            return

        workspace = await self._partners.get_account_by_id(partner_account_id)
        if workspace is None:
            raise ValueError("Partner workspace not found")
        if workspace.status != PartnerAccountStatus.ACTIVE.value:
            raise ValueError("Partner workspace must be active for pilot cohorts")

    async def _validate_unique_key(self, cohort_key: str) -> None:
        existing = await self._repo.get_pilot_cohort_by_key(cohort_key)
        if existing is not None:
            raise ValueError("cohort_key already exists")


class ListPilotCohortsUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = PilotCohortRepository(session)

    async def execute(
        self,
        *,
        partner_account_id: UUID | None = None,
        lane_key: str | None = None,
        surface_key: str | None = None,
        cohort_status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PilotCohortSnapshot]:
        cohorts = await self._repo.list_pilot_cohorts(
            partner_account_id=partner_account_id,
            lane_key=lane_key,
            surface_key=surface_key,
            cohort_status=cohort_status,
            limit=limit,
            offset=offset,
        )
        windows_by_cohort = await _windows_by_cohort(
            repo=self._repo,
            cohort_ids=[item.id for item in cohorts],
        )
        return [
            PilotCohortSnapshot(cohort=item, windows=windows_by_cohort.get(item.id, []))
            for item in cohorts
        ]


class GetPilotCohortUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = PilotCohortRepository(session)

    async def execute(self, *, cohort_id: UUID) -> PilotCohortSnapshot | None:
        cohort = await self._repo.get_pilot_cohort_by_id(cohort_id)
        if cohort is None:
            return None
        windows = await self._repo.list_rollout_windows_for_cohort(cohort_id)
        return PilotCohortSnapshot(cohort=cohort, windows=windows)


class ListPilotOwnerAcknowledgementsUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = PilotCohortRepository(session)

    async def execute(self, *, cohort_id: UUID) -> list[PilotOwnerAcknowledgementModel]:
        await _require_existing_cohort(self._repo, cohort_id=cohort_id)
        return await self._repo.list_owner_acknowledgements_for_cohort(cohort_id)


class RecordPilotOwnerAcknowledgementUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = PilotCohortRepository(session)
        self._outbox = EventOutboxService(session)

    async def execute(
        self,
        *,
        cohort_id: UUID,
        owner_team: str,
        runbook_reference: str,
        notes: list[str] | None,
        acknowledged_by_admin_user_id: UUID,
    ) -> PilotOwnerAcknowledgementModel:
        cohort = await _require_existing_cohort(self._repo, cohort_id=cohort_id)
        await _validate_admin_user_exists(self._session, acknowledged_by_admin_user_id)

        normalized_reference = str(runbook_reference).strip()
        if not normalized_reference:
            raise ValueError("runbook_reference is required")

        owner_team_value = PilotOwnerTeam(owner_team).value
        model = await self._repo.create_owner_acknowledgement(
            PilotOwnerAcknowledgementModel(
                pilot_cohort_id=cohort.id,
                owner_team=owner_team_value,
                acknowledgement_status=PilotOwnerAcknowledgementStatus.ACKNOWLEDGED.value,
                runbook_reference=normalized_reference,
                notes_payload=_normalize_string_list(notes),
                acknowledged_by_admin_user_id=acknowledged_by_admin_user_id,
                acknowledged_at=datetime.now(UTC),
            )
        )
        await self._outbox.append_event(
            event_name="rollout.runbook_acknowledged",
            aggregate_type="pilot_cohort",
            aggregate_id=str(cohort.id),
            event_payload={
                "pilot_cohort_id": str(cohort.id),
                "cohort_key": cohort.cohort_key,
                "owner_team": owner_team_value,
                "runbook_reference": normalized_reference,
            },
            actor_context=OutboxActorContext(
                principal_type=PrincipalClass.ADMIN.value,
                principal_id=str(acknowledged_by_admin_user_id),
            ),
        )
        await self._session.commit()
        await self._session.refresh(model)
        return model


class ListPilotRollbackDrillsUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = PilotCohortRepository(session)

    async def execute(self, *, cohort_id: UUID) -> list[PilotRollbackDrillModel]:
        await _require_existing_cohort(self._repo, cohort_id=cohort_id)
        return await self._repo.list_rollback_drills_for_cohort(cohort_id)


class RecordPilotRollbackDrillUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = PilotCohortRepository(session)
        self._outbox = EventOutboxService(session)

    async def execute(
        self,
        *,
        cohort_id: UUID,
        cutover_unit_key: str,
        rollback_scope_class: str,
        trigger_code: str,
        drill_status: str,
        runbook_reference: str,
        observed_metric_payload: dict[str, Any] | None,
        notes: list[str] | None,
        executed_by_admin_user_id: UUID,
    ) -> PilotRollbackDrillModel:
        cohort = await _require_existing_cohort(self._repo, cohort_id=cohort_id)
        await _validate_admin_user_exists(self._session, executed_by_admin_user_id)

        normalized_cutover_unit_key = str(cutover_unit_key).strip()
        normalized_trigger_code = str(trigger_code).strip()
        normalized_runbook_reference = str(runbook_reference).strip()
        if not normalized_cutover_unit_key:
            raise ValueError("cutover_unit_key is required")
        if not normalized_trigger_code:
            raise ValueError("trigger_code is required")
        if not normalized_runbook_reference:
            raise ValueError("runbook_reference is required")

        scope_class_value = PilotRollbackScopeClass(rollback_scope_class).value
        drill_status_value = PilotRollbackDrillStatus(drill_status).value
        model = await self._repo.create_rollback_drill(
            PilotRollbackDrillModel(
                pilot_cohort_id=cohort.id,
                cutover_unit_key=normalized_cutover_unit_key,
                rollback_scope_class=scope_class_value,
                trigger_code=normalized_trigger_code,
                drill_status=drill_status_value,
                runbook_reference=normalized_runbook_reference,
                observed_metric_payload=dict(observed_metric_payload or {}),
                notes_payload=_normalize_string_list(notes),
                executed_by_admin_user_id=executed_by_admin_user_id,
                executed_at=datetime.now(UTC),
            )
        )
        await self._outbox.append_event(
            event_name="rollout.rollback_drill.recorded",
            aggregate_type="pilot_cohort",
            aggregate_id=str(cohort.id),
            event_payload={
                "pilot_cohort_id": str(cohort.id),
                "cohort_key": cohort.cohort_key,
                "cutover_unit_key": normalized_cutover_unit_key,
                "rollback_scope_class": scope_class_value,
                "trigger_code": normalized_trigger_code,
                "drill_status": drill_status_value,
                "runbook_reference": normalized_runbook_reference,
            },
            actor_context=OutboxActorContext(
                principal_type=PrincipalClass.ADMIN.value,
                principal_id=str(executed_by_admin_user_id),
            ),
        )
        await self._session.commit()
        await self._session.refresh(model)
        return model


class ListPilotGoNoGoDecisionsUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = PilotCohortRepository(session)

    async def execute(self, *, cohort_id: UUID) -> list[PilotGoNoGoDecisionModel]:
        await _require_existing_cohort(self._repo, cohort_id=cohort_id)
        return await self._repo.list_go_no_go_decisions_for_cohort(cohort_id)


class RecordPilotGoNoGoDecisionUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = PilotCohortRepository(session)
        self._outbox = EventOutboxService(session)

    async def execute(
        self,
        *,
        cohort_id: UUID,
        decision_status: str,
        decision_reason_code: str | None,
        release_ring: str,
        rollback_scope_class: str,
        cutover_unit_keys: list[str],
        evidence_links: list[str],
        monitoring_snapshot_payload: dict[str, Any] | None,
        notes: list[str] | None,
        decided_by_admin_user_id: UUID,
    ) -> PilotGoNoGoDecisionModel:
        cohort = await _require_existing_cohort(self._repo, cohort_id=cohort_id)
        await _validate_admin_user_exists(self._session, decided_by_admin_user_id)

        status_value = PilotGoNoGoStatus(decision_status).value
        normalized_reason_code = str(decision_reason_code or "").strip() or None
        normalized_release_ring = str(release_ring).strip() or "R3"
        if not normalized_release_ring:
            raise ValueError("release_ring is required")

        scope_class_value = PilotRollbackScopeClass(rollback_scope_class).value
        normalized_cutover_unit_keys = _normalize_required_string_list(
            cutover_unit_keys,
            field_name="cutover_unit_keys",
        )
        normalized_evidence_links = _normalize_required_string_list(
            evidence_links,
            field_name="evidence_links",
        )
        monitoring_snapshot = dict(monitoring_snapshot_payload or {})
        if not monitoring_snapshot:
            raise ValueError("monitoring_snapshot_payload is required")

        owner_acknowledgements = await self._repo.list_owner_acknowledgements_for_cohort(cohort_id)
        latest_acknowledgements = _latest_owner_acknowledgements(owner_acknowledgements)
        required_owner_teams = _determine_required_owner_teams(cohort)
        missing_owner_teams = sorted(
            owner_team for owner_team in required_owner_teams if owner_team not in latest_acknowledgements
        )
        rollback_drills = await self._repo.list_rollback_drills_for_cohort(cohort_id)
        latest_rollback_drill = rollback_drills[0] if rollback_drills else None

        if status_value == PilotGoNoGoStatus.APPROVED.value:
            if missing_owner_teams:
                raise ValueError(
                    "Approved go/no-go requires owner acknowledgements: "
                    + ", ".join(missing_owner_teams)
                )
            if latest_rollback_drill is None:
                raise ValueError("Approved go/no-go requires a recorded rollback drill")
            if latest_rollback_drill.drill_status != PilotRollbackDrillStatus.PASSED.value:
                raise ValueError("Approved go/no-go requires a passed rollback drill")
        elif normalized_reason_code is None:
            raise ValueError("decision_reason_code is required for hold/no_go")

        model = await self._repo.create_go_no_go_decision(
            PilotGoNoGoDecisionModel(
                pilot_cohort_id=cohort.id,
                decision_status=status_value,
                decision_reason_code=normalized_reason_code,
                release_ring=normalized_release_ring,
                rollback_scope_class=scope_class_value,
                cutover_unit_keys_payload=normalized_cutover_unit_keys,
                evidence_links_payload=normalized_evidence_links,
                acknowledged_owner_teams_payload=sorted(latest_acknowledgements.keys()),
                monitoring_snapshot_payload=monitoring_snapshot,
                notes_payload=_normalize_string_list(notes),
                decided_by_admin_user_id=decided_by_admin_user_id,
                decided_at=datetime.now(UTC),
            )
        )
        await self._outbox.append_event(
            event_name="rollout.go_no_go.recorded",
            aggregate_type="pilot_cohort",
            aggregate_id=str(cohort.id),
            event_payload={
                "pilot_cohort_id": str(cohort.id),
                "cohort_key": cohort.cohort_key,
                "decision_status": status_value,
                "decision_reason_code": normalized_reason_code,
                "release_ring": normalized_release_ring,
                "rollback_scope_class": scope_class_value,
                "cutover_unit_keys": normalized_cutover_unit_keys,
                "acknowledged_owner_teams": sorted(latest_acknowledgements.keys()),
            },
            actor_context=OutboxActorContext(
                principal_type=PrincipalClass.ADMIN.value,
                principal_id=str(decided_by_admin_user_id),
            ),
        )
        await self._session.commit()
        await self._session.refresh(model)
        return model


class GetPilotCohortReadinessUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = PilotCohortRepository(session)
        self._partners = PartnerAccountRepository(session)
        self._governance = GovernanceRepository(session)
        self._risk = RiskSubjectGraphRepository(session)

    async def execute(self, *, cohort_id: UUID) -> PilotCohortReadinessResult:
        snapshot = await GetPilotCohortUseCase(self._session).execute(cohort_id=cohort_id)
        if snapshot is None:
            raise ValueError("Pilot cohort not found")

        cohort = snapshot.cohort
        windows = snapshot.windows
        blocking_reason_codes: set[str] = set()
        warning_reason_codes: set[str] = set()
        blocking_risk_review_ids: list[UUID] = []
        blocking_governance_action_ids: list[UUID] = []

        if cohort.cohort_status in {
            PilotCohortStatus.COMPLETED.value,
            PilotCohortStatus.CANCELLED.value,
        }:
            blocking_reason_codes.add("cohort_not_reactivatable")

        if not windows:
            blocking_reason_codes.add("rollout_window_missing")

        shadow_gate_payload = dict(cohort.shadow_gate_payload or {})
        attribution_status = str(shadow_gate_payload.get("attribution_gate_status") or "")
        settlement_status = str(shadow_gate_payload.get("settlement_gate_status") or "")
        if attribution_status != PilotGateStatus.GREEN.value:
            if attribution_status == PilotGateStatus.YELLOW.value:
                warning_reason_codes.add("attribution_shadow_requires_caution")
            else:
                blocking_reason_codes.add("attribution_shadow_blocked")
        if settlement_status != PilotGateStatus.GREEN.value:
            if settlement_status == PilotGateStatus.YELLOW.value:
                warning_reason_codes.add("settlement_shadow_requires_caution")
            else:
                blocking_reason_codes.add("settlement_shadow_blocked")

        workspace = None
        traffic_declarations: list[PartnerTrafficDeclarationModel] = []
        creative_approvals: list[CreativeApprovalModel] = []
        open_risk_reviews: list[RiskReviewModel] = []
        governance_actions: list[GovernanceActionModel] = []
        dispute_case_count = 0

        if cohort.partner_account_id is not None:
            workspace = await self._partners.get_account_by_id(cohort.partner_account_id)
            if workspace is None or workspace.status != PartnerAccountStatus.ACTIVE.value:
                blocking_reason_codes.add("workspace_inactive")
            traffic_declarations = await self._governance.list_traffic_declarations(
                partner_account_id=cohort.partner_account_id,
                limit=500,
                offset=0,
            )
            creative_approvals = await self._governance.list_creative_approvals(
                partner_account_id=cohort.partner_account_id,
                limit=500,
                offset=0,
            )
            dispute_case_count = len(
                await self._governance.list_dispute_cases(
                    partner_account_id=cohort.partner_account_id,
                    limit=500,
                    offset=0,
                )
            )

            risk_subject = await self._risk.get_subject_by_principal(
                principal_class=PrincipalClass.PARTNER_OPERATOR.value,
                principal_subject=_workspace_risk_subject_key(cohort.partner_account_id),
                auth_realm_id=None,
            )
            if risk_subject is not None:
                open_risk_reviews = await self._risk.list_open_reviews_for_subject(risk_subject.id)
                governance_actions = await self._risk.list_governance_actions(risk_subject_id=risk_subject.id)

        blocking_risk_reviews = [
            item
            for item in open_risk_reviews
            if item.status == RiskReviewStatus.OPEN.value
            and item.decision in {RiskReviewDecision.HOLD.value, RiskReviewDecision.BLOCK.value}
        ]
        if blocking_risk_reviews:
            blocking_reason_codes.add("risk_review_blocking")
            blocking_risk_review_ids = [item.id for item in blocking_risk_reviews]

        blocking_governance_actions = [
            item
            for item in governance_actions
            if item.action_status in {
                GovernanceActionStatus.REQUESTED.value,
                GovernanceActionStatus.APPLIED.value,
            }
            and item.action_type in _BLOCKING_GOVERNANCE_ACTIONS
        ]
        if blocking_governance_actions:
            blocking_reason_codes.add("governance_action_blocking")
            blocking_governance_action_ids = [item.id for item in blocking_governance_actions]

        if cohort.lane_key == PilotLaneKey.PERFORMANCE_MEDIA_BUYER.value:
            if not any(
                item.declaration_status == TrafficDeclarationStatus.COMPLETE.value
                for item in traffic_declarations
            ):
                blocking_reason_codes.add("traffic_declaration_incomplete")
            if not any(item.approval_status == "complete" for item in creative_approvals):
                blocking_reason_codes.add("creative_approval_incomplete")

        active_window_count = sum(
            1 for item in windows if item.window_status == PilotRolloutWindowStatus.ACTIVE.value
        )
        scheduled_window_count = sum(
            1 for item in windows if item.window_status == PilotRolloutWindowStatus.SCHEDULED.value
        )
        paused_window_count = sum(
            1 for item in windows if item.window_status == PilotRolloutWindowStatus.PAUSED.value
        )
        if scheduled_window_count == 0 and active_window_count == 0 and paused_window_count == 0:
            blocking_reason_codes.add("no_schedulable_rollout_window")

        owner_acknowledgements = await self._repo.list_owner_acknowledgements_for_cohort(cohort.id)
        latest_owner_acknowledgements = _latest_owner_acknowledgements(owner_acknowledgements)
        required_owner_teams = _determine_required_owner_teams(cohort)
        missing_owner_teams = sorted(
            owner_team for owner_team in required_owner_teams if owner_team not in latest_owner_acknowledgements
        )
        if missing_owner_teams:
            blocking_reason_codes.add("owner_acknowledgement_missing")

        rollback_drills = await self._repo.list_rollback_drills_for_cohort(cohort.id)
        latest_rollback_drill = rollback_drills[0] if rollback_drills else None
        if latest_rollback_drill is None:
            blocking_reason_codes.add("rollback_drill_missing")
        elif latest_rollback_drill.drill_status != PilotRollbackDrillStatus.PASSED.value:
            blocking_reason_codes.add("rollback_drill_failed")

        go_no_go_decisions = await self._repo.list_go_no_go_decisions_for_cohort(cohort.id)
        latest_go_no_go_decision = go_no_go_decisions[0] if go_no_go_decisions else None
        if latest_go_no_go_decision is None:
            blocking_reason_codes.add("go_no_go_missing")
        elif latest_go_no_go_decision.decision_status == PilotGoNoGoStatus.HOLD.value:
            blocking_reason_codes.add("go_no_go_hold")
        elif latest_go_no_go_decision.decision_status == PilotGoNoGoStatus.NO_GO.value:
            blocking_reason_codes.add("go_no_go_no_go")

        runbook_gate_status = (
            PilotGateStatus.RED.value
            if blocking_reason_codes & _RUNBOOK_BLOCKING_CODES
            else PilotGateStatus.GREEN.value
        )

        checked_at = datetime.now(UTC)
        live_monitoring_snapshot = {
            "partner_account_id": str(cohort.partner_account_id) if cohort.partner_account_id else None,
            "shadow_evidence": {
                "attribution_reference": shadow_gate_payload.get("attribution_reference"),
                "attribution_gate_status": attribution_status or None,
                "settlement_reference": shadow_gate_payload.get("settlement_reference"),
                "settlement_gate_status": settlement_status or None,
            },
            "workspace_active": workspace.status == PartnerAccountStatus.ACTIVE.value if workspace else None,
            "traffic_declaration_count": len(traffic_declarations),
            "complete_traffic_declaration_count": sum(
                1
                for item in traffic_declarations
                if item.declaration_status == TrafficDeclarationStatus.COMPLETE.value
            ),
            "creative_approval_count": len(creative_approvals),
            "complete_creative_approval_count": sum(
                1 for item in creative_approvals if item.approval_status == "complete"
            ),
            "open_risk_review_count": len(open_risk_reviews),
            "blocking_risk_review_count": len(blocking_risk_reviews),
            "blocking_governance_action_count": len(blocking_governance_actions),
            "dispute_case_count": dispute_case_count,
            "rollout_window_count": len(windows),
            "active_window_count": active_window_count,
            "scheduled_window_count": scheduled_window_count,
            "paused_window_count": paused_window_count,
            "required_owner_teams": required_owner_teams,
            "acknowledged_owner_teams": sorted(latest_owner_acknowledgements.keys()),
            "missing_owner_teams": missing_owner_teams,
            "runbook_gate_status": runbook_gate_status,
            "latest_rollback_drill": (
                {
                    "id": str(latest_rollback_drill.id),
                    "cutover_unit_key": latest_rollback_drill.cutover_unit_key,
                    "rollback_scope_class": latest_rollback_drill.rollback_scope_class,
                    "trigger_code": latest_rollback_drill.trigger_code,
                    "drill_status": latest_rollback_drill.drill_status,
                    "runbook_reference": latest_rollback_drill.runbook_reference,
                    "executed_at": latest_rollback_drill.executed_at.isoformat(),
                }
                if latest_rollback_drill
                else None
            ),
            "latest_go_no_go_decision": (
                {
                    "id": str(latest_go_no_go_decision.id),
                    "decision_status": latest_go_no_go_decision.decision_status,
                    "decision_reason_code": latest_go_no_go_decision.decision_reason_code,
                    "release_ring": latest_go_no_go_decision.release_ring,
                    "rollback_scope_class": latest_go_no_go_decision.rollback_scope_class,
                    "decided_at": latest_go_no_go_decision.decided_at.isoformat(),
                }
                if latest_go_no_go_decision
                else None
            ),
        }
        return PilotCohortReadinessResult(
            cohort=cohort,
            windows=windows,
            activation_allowed=not blocking_reason_codes,
            blocking_reason_codes=sorted(blocking_reason_codes),
            warning_reason_codes=sorted(warning_reason_codes),
            blocking_risk_review_ids=blocking_risk_review_ids,
            blocking_governance_action_ids=blocking_governance_action_ids,
            runbook_gate_status=runbook_gate_status,
            required_owner_teams=required_owner_teams,
            acknowledged_owner_teams=sorted(latest_owner_acknowledgements.keys()),
            missing_owner_teams=missing_owner_teams,
            latest_rollback_drill=latest_rollback_drill,
            latest_go_no_go_decision=latest_go_no_go_decision,
            live_monitoring_snapshot=live_monitoring_snapshot,
            checked_at=checked_at,
        )


class ActivatePilotCohortUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._outbox = EventOutboxService(session)

    async def execute(
        self,
        *,
        cohort_id: UUID,
        activated_by_admin_user_id: UUID,
    ) -> PilotCohortSnapshot:
        readiness = await GetPilotCohortReadinessUseCase(self._session).execute(cohort_id=cohort_id)
        if not readiness.activation_allowed:
            reason_codes = ", ".join(readiness.blocking_reason_codes)
            raise ValueError(f"Pilot cohort is not ready for activation: {reason_codes}")

        cohort = readiness.cohort
        now = datetime.now(UTC)
        cohort.cohort_status = PilotCohortStatus.ACTIVE.value
        cohort.activated_at = now
        cohort.activated_by_admin_user_id = activated_by_admin_user_id
        cohort.pause_reason_code = None
        for window in readiness.windows:
            if window.window_status in {
                PilotRolloutWindowStatus.SCHEDULED.value,
                PilotRolloutWindowStatus.PAUSED.value,
            }:
                window.window_status = PilotRolloutWindowStatus.ACTIVE.value

        await self._outbox.append_event(
            event_name="rollout.pilot_cohort.activated",
            aggregate_type="pilot_cohort",
            aggregate_id=str(cohort.id),
            event_payload={
                "pilot_cohort_id": str(cohort.id),
                "cohort_key": cohort.cohort_key,
                "lane_key": cohort.lane_key,
                "surface_key": cohort.surface_key,
                "cohort_status": cohort.cohort_status,
                "blocking_reason_codes": readiness.blocking_reason_codes,
                "warning_reason_codes": readiness.warning_reason_codes,
                "runbook_gate_status": readiness.runbook_gate_status,
            },
            actor_context=OutboxActorContext(
                principal_type=PrincipalClass.ADMIN.value,
                principal_id=str(activated_by_admin_user_id),
            ),
        )
        await self._session.commit()
        await self._session.refresh(cohort)
        for window in readiness.windows:
            await self._session.refresh(window)
        return PilotCohortSnapshot(cohort=cohort, windows=readiness.windows)


class PausePilotCohortUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._outbox = EventOutboxService(session)

    async def execute(
        self,
        *,
        cohort_id: UUID,
        paused_by_admin_user_id: UUID,
        reason_code: str | None = None,
    ) -> PilotCohortSnapshot:
        snapshot = await GetPilotCohortUseCase(self._session).execute(cohort_id=cohort_id)
        if snapshot is None:
            raise ValueError("Pilot cohort not found")
        if snapshot.cohort.cohort_status in {
            PilotCohortStatus.COMPLETED.value,
            PilotCohortStatus.CANCELLED.value,
        }:
            raise ValueError("Completed or cancelled pilot cohorts cannot be paused")

        cohort = snapshot.cohort
        cohort.cohort_status = PilotCohortStatus.PAUSED.value
        cohort.paused_at = datetime.now(UTC)
        cohort.paused_by_admin_user_id = paused_by_admin_user_id
        cohort.pause_reason_code = reason_code.strip() if reason_code else None
        for window in snapshot.windows:
            if window.window_status in {
                PilotRolloutWindowStatus.SCHEDULED.value,
                PilotRolloutWindowStatus.ACTIVE.value,
            }:
                window.window_status = PilotRolloutWindowStatus.PAUSED.value

        await self._outbox.append_event(
            event_name="rollout.pilot_cohort.paused",
            aggregate_type="pilot_cohort",
            aggregate_id=str(cohort.id),
            event_payload={
                "pilot_cohort_id": str(cohort.id),
                "cohort_key": cohort.cohort_key,
                "lane_key": cohort.lane_key,
                "surface_key": cohort.surface_key,
                "cohort_status": cohort.cohort_status,
                "pause_reason_code": cohort.pause_reason_code,
            },
            actor_context=OutboxActorContext(
                principal_type=PrincipalClass.ADMIN.value,
                principal_id=str(paused_by_admin_user_id),
            ),
        )
        await self._session.commit()
        await self._session.refresh(cohort)
        for window in snapshot.windows:
            await self._session.refresh(window)
        return snapshot


async def _windows_by_cohort(
    *,
    repo: PilotCohortRepository,
    cohort_ids: list[UUID],
) -> dict[UUID, list[PilotRolloutWindowModel]]:
    grouped: dict[UUID, list[PilotRolloutWindowModel]] = defaultdict(list)
    for window in await repo.list_rollout_windows_for_cohorts(cohort_ids):
        grouped[window.pilot_cohort_id].append(window)
    return grouped


async def _require_existing_cohort(
    repo: PilotCohortRepository,
    *,
    cohort_id: UUID,
) -> PilotCohortModel:
    cohort = await repo.get_pilot_cohort_by_id(cohort_id)
    if cohort is None:
        raise ValueError("Pilot cohort not found")
    return cohort


async def _validate_admin_user_exists(session: AsyncSession, admin_user_id: UUID) -> None:
    admin_user = await session.get(AdminUserModel, admin_user_id)
    if admin_user is None:
        raise ValueError("admin user not found")


def _determine_required_owner_teams(cohort: PilotCohortModel) -> list[str]:
    teams = {
        PilotOwnerTeam.PLATFORM.value,
        PilotOwnerTeam.SUPPORT.value,
        PilotOwnerTeam.QA.value,
    }
    if cohort.partner_account_id is not None or cohort.surface_key in {
        PilotSurfaceKey.PARTNER_STOREFRONT.value,
        PilotSurfaceKey.PARTNER_PORTAL.value,
    }:
        teams.add(PilotOwnerTeam.PARTNER_OPS.value)
    if cohort.lane_key in {lane.value for lane in _PAYOUT_BEARING_LANES}:
        teams.add(PilotOwnerTeam.FINANCE_OPS.value)
    if cohort.lane_key == PilotLaneKey.PERFORMANCE_MEDIA_BUYER.value:
        teams.add(PilotOwnerTeam.RISK_OPS.value)
    return sorted(teams)


def _latest_owner_acknowledgements(
    acknowledgements: list[PilotOwnerAcknowledgementModel],
) -> dict[str, PilotOwnerAcknowledgementModel]:
    grouped: dict[str, PilotOwnerAcknowledgementModel] = {}
    for acknowledgement in acknowledgements:
        grouped.setdefault(acknowledgement.owner_team, acknowledgement)
    return grouped


def _validate_shadow_gate_payload(payload: dict[str, Any]) -> dict[str, Any]:
    attribution_reference = str(payload.get("attribution_reference") or "").strip()
    settlement_reference = str(payload.get("settlement_reference") or "").strip()
    if not attribution_reference:
        raise ValueError("shadow_evidence.attribution_reference is required")
    if not settlement_reference:
        raise ValueError("shadow_evidence.settlement_reference is required")

    attribution_gate_status = PilotGateStatus(str(payload.get("attribution_gate_status") or ""))
    settlement_gate_status = PilotGateStatus(str(payload.get("settlement_gate_status") or ""))
    return {
        "attribution_reference": attribution_reference,
        "attribution_gate_status": attribution_gate_status.value,
        "settlement_reference": settlement_reference,
        "settlement_gate_status": settlement_gate_status.value,
        "notes": _normalize_string_list(payload.get("notes")),
    }


def _validate_rollout_windows(
    *,
    rollout_windows: list[dict[str, Any]],
    surface: PilotSurfaceKey,
    partner_account_id: UUID | None,
) -> list[dict[str, Any]]:
    if not rollout_windows:
        raise ValueError("At least one rollout window is required")

    seen_targets: set[tuple[str, str]] = set()
    validated: list[dict[str, Any]] = []
    window_kinds: set[PilotRolloutWindowKind] = set()
    for item in rollout_windows:
        window_kind = PilotRolloutWindowKind(str(item.get("window_kind") or ""))
        target_ref = str(item.get("target_ref") or "").strip()
        starts_at = _normalize_utc(item.get("starts_at"))
        ends_at = _normalize_utc(item.get("ends_at"))
        if not target_ref:
            raise ValueError("rollout_window.target_ref is required")
        if ends_at <= starts_at:
            raise ValueError("rollout_window.ends_at must be after starts_at")
        unique_key = (window_kind.value, target_ref)
        if unique_key in seen_targets:
            raise ValueError("Duplicate rollout window target detected")
        seen_targets.add(unique_key)
        validated.append(
            {
                "window_kind": window_kind.value,
                "target_ref": target_ref,
                "starts_at": starts_at,
                "ends_at": ends_at,
                "notes": _normalize_string_list(item.get("notes")),
            }
        )
        window_kinds.add(window_kind)

    if surface in _HOST_SURFACES and PilotRolloutWindowKind.HOST not in window_kinds:
        raise ValueError(f"{surface.value} cohorts require at least one host rollout window")
    if surface in _WORKSPACE_SURFACES and PilotRolloutWindowKind.PARTNER_WORKSPACE not in window_kinds:
        raise ValueError(f"{surface.value} cohorts require at least one partner_workspace rollout window")
    if surface in _CHANNEL_SURFACES and PilotRolloutWindowKind.CHANNEL not in window_kinds:
        raise ValueError(f"{surface.value} cohorts require at least one channel rollout window")

    if partner_account_id is not None:
        partner_workspace_targets = {
            item["target_ref"]
            for item in validated
            if item["window_kind"] == PilotRolloutWindowKind.PARTNER_WORKSPACE.value
        }
        if partner_workspace_targets and partner_workspace_targets != {str(partner_account_id)}:
            raise ValueError("partner_workspace rollout windows must target the cohort partner_account_id")

    return validated


def _normalize_required_string_list(values: list[str] | None, *, field_name: str) -> list[str]:
    normalized = _normalize_string_list(values)
    if not normalized:
        raise ValueError(f"{field_name} is required")
    return normalized


def _normalize_string_list(values: Any) -> list[str]:
    return [value.strip() for value in list(values or []) if value and str(value).strip()]


def _normalize_utc(value: Any) -> datetime:
    if not isinstance(value, datetime):
        raise ValueError("rollout window timestamps must be datetime values")
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _workspace_risk_subject_key(partner_account_id: UUID) -> str:
    return f"partner_account:{partner_account_id}"
