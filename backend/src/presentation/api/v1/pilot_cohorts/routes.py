from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.pilots import (
    ActivatePilotCohortUseCase,
    CreatePilotCohortUseCase,
    GetPilotCohortReadinessUseCase,
    GetPilotCohortUseCase,
    ListPilotCohortsUseCase,
    ListPilotGoNoGoDecisionsUseCase,
    ListPilotOwnerAcknowledgementsUseCase,
    ListPilotRollbackDrillsUseCase,
    PausePilotCohortUseCase,
    RecordPilotGoNoGoDecisionUseCase,
    RecordPilotOwnerAcknowledgementUseCase,
    RecordPilotRollbackDrillUseCase,
)
from src.domain.enums import AdminRole, PilotCohortStatus, PilotLaneKey, PilotSurfaceKey
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.monitoring.metrics import route_operations_total
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_role

from .schemas import (
    CreatePilotCohortRequest,
    PausePilotCohortRequest,
    PilotCohortReadinessResponse,
    PilotCohortResponse,
    PilotGoNoGoDecisionRequest,
    PilotGoNoGoDecisionResponse,
    PilotOwnerAcknowledgementRequest,
    PilotOwnerAcknowledgementResponse,
    PilotRollbackDrillRequest,
    PilotRollbackDrillResponse,
    PilotRolloutWindowResponse,
    PilotShadowEvidenceResponse,
)

router = APIRouter(prefix="/pilot-cohorts", tags=["pilot-cohorts"])


def _serialize_rollout_window(model) -> PilotRolloutWindowResponse:
    return PilotRolloutWindowResponse(
        id=model.id,
        pilot_cohort_id=model.pilot_cohort_id,
        window_kind=model.window_kind,
        target_ref=model.target_ref,
        window_status=model.window_status,
        starts_at=model.starts_at,
        ends_at=model.ends_at,
        notes=list(model.notes_payload or []),
        created_by_admin_user_id=model.created_by_admin_user_id,
        closed_by_admin_user_id=model.closed_by_admin_user_id,
        closed_at=model.closed_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _serialize_shadow_evidence(payload: dict) -> PilotShadowEvidenceResponse:
    return PilotShadowEvidenceResponse(
        attribution_reference=str(payload.get("attribution_reference") or ""),
        attribution_gate_status=str(payload.get("attribution_gate_status") or "red"),
        settlement_reference=str(payload.get("settlement_reference") or ""),
        settlement_gate_status=str(payload.get("settlement_gate_status") or "red"),
        notes=list(payload.get("notes") or []),
    )


def _serialize_owner_acknowledgement(model) -> PilotOwnerAcknowledgementResponse:
    return PilotOwnerAcknowledgementResponse(
        id=model.id,
        pilot_cohort_id=model.pilot_cohort_id,
        owner_team=model.owner_team,
        acknowledgement_status=model.acknowledgement_status,
        runbook_reference=model.runbook_reference,
        notes=list(model.notes_payload or []),
        acknowledged_by_admin_user_id=model.acknowledged_by_admin_user_id,
        acknowledged_at=model.acknowledged_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _serialize_rollback_drill(model) -> PilotRollbackDrillResponse:
    return PilotRollbackDrillResponse(
        id=model.id,
        pilot_cohort_id=model.pilot_cohort_id,
        cutover_unit_key=model.cutover_unit_key,
        rollback_scope_class=model.rollback_scope_class,
        trigger_code=model.trigger_code,
        drill_status=model.drill_status,
        runbook_reference=model.runbook_reference,
        observed_metric_payload=dict(model.observed_metric_payload or {}),
        notes=list(model.notes_payload or []),
        executed_by_admin_user_id=model.executed_by_admin_user_id,
        executed_at=model.executed_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _serialize_go_no_go_decision(model) -> PilotGoNoGoDecisionResponse:
    return PilotGoNoGoDecisionResponse(
        id=model.id,
        pilot_cohort_id=model.pilot_cohort_id,
        decision_status=model.decision_status,
        decision_reason_code=model.decision_reason_code,
        release_ring=model.release_ring,
        rollback_scope_class=model.rollback_scope_class,
        cutover_unit_keys=list(model.cutover_unit_keys_payload or []),
        evidence_links=list(model.evidence_links_payload or []),
        acknowledged_owner_teams=list(model.acknowledged_owner_teams_payload or []),
        monitoring_snapshot_payload=dict(model.monitoring_snapshot_payload or {}),
        notes=list(model.notes_payload or []),
        decided_by_admin_user_id=model.decided_by_admin_user_id,
        decided_at=model.decided_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _serialize_pilot_cohort(snapshot) -> PilotCohortResponse:
    cohort = snapshot.cohort
    return PilotCohortResponse(
        id=cohort.id,
        cohort_key=cohort.cohort_key,
        display_name=cohort.display_name,
        lane_key=cohort.lane_key,
        surface_key=cohort.surface_key,
        cohort_status=cohort.cohort_status,
        partner_account_id=cohort.partner_account_id,
        owner_team=cohort.owner_team,
        owner_admin_user_id=cohort.owner_admin_user_id,
        rollback_trigger_code=cohort.rollback_trigger_code,
        shadow_evidence=_serialize_shadow_evidence(dict(cohort.shadow_gate_payload or {})),
        monitoring_payload=dict(cohort.monitoring_payload or {}),
        notes=list(cohort.notes_payload or []),
        scheduled_start_at=cohort.scheduled_start_at,
        scheduled_end_at=cohort.scheduled_end_at,
        activated_at=cohort.activated_at,
        paused_at=cohort.paused_at,
        completed_at=cohort.completed_at,
        pause_reason_code=cohort.pause_reason_code,
        created_by_admin_user_id=cohort.created_by_admin_user_id,
        activated_by_admin_user_id=cohort.activated_by_admin_user_id,
        paused_by_admin_user_id=cohort.paused_by_admin_user_id,
        created_at=cohort.created_at,
        updated_at=cohort.updated_at,
        rollout_windows=[_serialize_rollout_window(window) for window in snapshot.windows],
    )


@router.post("/", response_model=PilotCohortResponse, status_code=status.HTTP_201_CREATED)
async def create_pilot_cohort(
    payload: CreatePilotCohortRequest,
    current_admin: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> PilotCohortResponse:
    try:
        snapshot = await CreatePilotCohortUseCase(db).execute(
            cohort_key=payload.cohort_key,
            display_name=payload.display_name,
            lane_key=payload.lane_key.value,
            surface_key=payload.surface_key.value,
            partner_account_id=payload.partner_account_id,
            owner_team=payload.owner_team,
            owner_admin_user_id=payload.owner_admin_user_id,
            rollback_trigger_code=payload.rollback_trigger_code,
            shadow_gate_payload=payload.shadow_evidence.model_dump(mode="python"),
            monitoring_payload=payload.monitoring_payload,
            notes=payload.notes,
            rollout_windows=[item.model_dump(mode="python") for item in payload.rollout_windows],
            created_by_admin_user_id=current_admin.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    route_operations_total.labels(route="pilot_cohorts", action="create", status="success").inc()
    return _serialize_pilot_cohort(snapshot)


@router.get("/", response_model=list[PilotCohortResponse])
async def list_pilot_cohorts(
    partner_account_id: UUID | None = Query(default=None),
    lane_key: PilotLaneKey | None = Query(default=None),
    surface_key: PilotSurfaceKey | None = Query(default=None),
    cohort_status: PilotCohortStatus | None = Query(default=None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.OPERATOR)),
    db: AsyncSession = Depends(get_db),
) -> list[PilotCohortResponse]:
    snapshots = await ListPilotCohortsUseCase(db).execute(
        partner_account_id=partner_account_id,
        lane_key=lane_key.value if lane_key else None,
        surface_key=surface_key.value if surface_key else None,
        cohort_status=cohort_status.value if cohort_status else None,
        limit=limit,
        offset=offset,
    )
    route_operations_total.labels(route="pilot_cohorts", action="list", status="success").inc()
    return [_serialize_pilot_cohort(item) for item in snapshots]


@router.get("/{cohort_id}", response_model=PilotCohortResponse)
async def get_pilot_cohort(
    cohort_id: UUID,
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.OPERATOR)),
    db: AsyncSession = Depends(get_db),
) -> PilotCohortResponse:
    snapshot = await GetPilotCohortUseCase(db).execute(cohort_id=cohort_id)
    if snapshot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pilot cohort not found")
    route_operations_total.labels(route="pilot_cohorts", action="get", status="success").inc()
    return _serialize_pilot_cohort(snapshot)


@router.get("/{cohort_id}/owner-acknowledgements", response_model=list[PilotOwnerAcknowledgementResponse])
async def list_owner_acknowledgements(
    cohort_id: UUID,
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.OPERATOR)),
    db: AsyncSession = Depends(get_db),
) -> list[PilotOwnerAcknowledgementResponse]:
    try:
        models = await ListPilotOwnerAcknowledgementsUseCase(db).execute(cohort_id=cohort_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    route_operations_total.labels(route="pilot_cohorts", action="list_owner_acknowledgements", status="success").inc()
    return [_serialize_owner_acknowledgement(item) for item in models]


@router.post(
    "/{cohort_id}/owner-acknowledgements",
    response_model=PilotOwnerAcknowledgementResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_owner_acknowledgement(
    cohort_id: UUID,
    payload: PilotOwnerAcknowledgementRequest,
    current_admin: AdminUserModel = Depends(require_role(AdminRole.OPERATOR)),
    db: AsyncSession = Depends(get_db),
) -> PilotOwnerAcknowledgementResponse:
    try:
        model = await RecordPilotOwnerAcknowledgementUseCase(db).execute(
            cohort_id=cohort_id,
            owner_team=payload.owner_team.value,
            runbook_reference=payload.runbook_reference,
            notes=payload.notes,
            acknowledged_by_admin_user_id=current_admin.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    route_operations_total.labels(route="pilot_cohorts", action="create_owner_acknowledgement", status="success").inc()
    return _serialize_owner_acknowledgement(model)


@router.get("/{cohort_id}/rollback-drills", response_model=list[PilotRollbackDrillResponse])
async def list_rollback_drills(
    cohort_id: UUID,
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.OPERATOR)),
    db: AsyncSession = Depends(get_db),
) -> list[PilotRollbackDrillResponse]:
    try:
        models = await ListPilotRollbackDrillsUseCase(db).execute(cohort_id=cohort_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    route_operations_total.labels(route="pilot_cohorts", action="list_rollback_drills", status="success").inc()
    return [_serialize_rollback_drill(item) for item in models]


@router.post(
    "/{cohort_id}/rollback-drills",
    response_model=PilotRollbackDrillResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_rollback_drill(
    cohort_id: UUID,
    payload: PilotRollbackDrillRequest,
    current_admin: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> PilotRollbackDrillResponse:
    try:
        model = await RecordPilotRollbackDrillUseCase(db).execute(
            cohort_id=cohort_id,
            cutover_unit_key=payload.cutover_unit_key,
            rollback_scope_class=payload.rollback_scope_class.value,
            trigger_code=payload.trigger_code,
            drill_status=payload.drill_status.value,
            runbook_reference=payload.runbook_reference,
            observed_metric_payload=payload.observed_metric_payload,
            notes=payload.notes,
            executed_by_admin_user_id=current_admin.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    route_operations_total.labels(route="pilot_cohorts", action="create_rollback_drill", status="success").inc()
    return _serialize_rollback_drill(model)


@router.get("/{cohort_id}/go-no-go-decisions", response_model=list[PilotGoNoGoDecisionResponse])
async def list_go_no_go_decisions(
    cohort_id: UUID,
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.OPERATOR)),
    db: AsyncSession = Depends(get_db),
) -> list[PilotGoNoGoDecisionResponse]:
    try:
        models = await ListPilotGoNoGoDecisionsUseCase(db).execute(cohort_id=cohort_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    route_operations_total.labels(route="pilot_cohorts", action="list_go_no_go_decisions", status="success").inc()
    return [_serialize_go_no_go_decision(item) for item in models]


@router.post(
    "/{cohort_id}/go-no-go-decisions",
    response_model=PilotGoNoGoDecisionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_go_no_go_decision(
    cohort_id: UUID,
    payload: PilotGoNoGoDecisionRequest,
    current_admin: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> PilotGoNoGoDecisionResponse:
    try:
        model = await RecordPilotGoNoGoDecisionUseCase(db).execute(
            cohort_id=cohort_id,
            decision_status=payload.decision_status.value,
            decision_reason_code=payload.decision_reason_code,
            release_ring=payload.release_ring,
            rollback_scope_class=payload.rollback_scope_class.value,
            cutover_unit_keys=payload.cutover_unit_keys,
            evidence_links=payload.evidence_links,
            monitoring_snapshot_payload=payload.monitoring_snapshot_payload,
            notes=payload.notes,
            decided_by_admin_user_id=current_admin.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    route_operations_total.labels(route="pilot_cohorts", action="create_go_no_go_decision", status="success").inc()
    return _serialize_go_no_go_decision(model)


@router.get("/{cohort_id}/readiness", response_model=PilotCohortReadinessResponse)
async def get_pilot_cohort_readiness(
    cohort_id: UUID,
    _current_admin: AdminUserModel = Depends(require_role(AdminRole.OPERATOR)),
    db: AsyncSession = Depends(get_db),
) -> PilotCohortReadinessResponse:
    try:
        readiness = await GetPilotCohortReadinessUseCase(db).execute(cohort_id=cohort_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    route_operations_total.labels(route="pilot_cohorts", action="readiness", status="success").inc()
    return PilotCohortReadinessResponse(
        cohort_id=readiness.cohort.id,
        cohort_status=readiness.cohort.cohort_status,
        activation_allowed=readiness.activation_allowed,
        blocking_reason_codes=readiness.blocking_reason_codes,
        warning_reason_codes=readiness.warning_reason_codes,
        blocking_risk_review_ids=readiness.blocking_risk_review_ids,
        blocking_governance_action_ids=readiness.blocking_governance_action_ids,
        runbook_gate_status=readiness.runbook_gate_status,
        required_owner_teams=readiness.required_owner_teams,
        acknowledged_owner_teams=readiness.acknowledged_owner_teams,
        missing_owner_teams=readiness.missing_owner_teams,
        latest_rollback_drill_id=readiness.latest_rollback_drill.id if readiness.latest_rollback_drill else None,
        latest_rollback_drill_status=(
            readiness.latest_rollback_drill.drill_status if readiness.latest_rollback_drill else None
        ),
        latest_go_no_go_decision_id=(
            readiness.latest_go_no_go_decision.id if readiness.latest_go_no_go_decision else None
        ),
        latest_go_no_go_status=(
            readiness.latest_go_no_go_decision.decision_status
            if readiness.latest_go_no_go_decision
            else None
        ),
        live_monitoring_snapshot=readiness.live_monitoring_snapshot,
        checked_at=readiness.checked_at,
    )


@router.post("/{cohort_id}/activate", response_model=PilotCohortResponse)
async def activate_pilot_cohort(
    cohort_id: UUID,
    current_admin: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> PilotCohortResponse:
    try:
        snapshot = await ActivatePilotCohortUseCase(db).execute(
            cohort_id=cohort_id,
            activated_by_admin_user_id=current_admin.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    route_operations_total.labels(route="pilot_cohorts", action="activate", status="success").inc()
    return _serialize_pilot_cohort(snapshot)


@router.post("/{cohort_id}/pause", response_model=PilotCohortResponse)
async def pause_pilot_cohort(
    cohort_id: UUID,
    payload: PausePilotCohortRequest,
    current_admin: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> PilotCohortResponse:
    try:
        snapshot = await PausePilotCohortUseCase(db).execute(
            cohort_id=cohort_id,
            paused_by_admin_user_id=current_admin.id,
            reason_code=payload.reason_code,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    route_operations_total.labels(route="pilot_cohorts", action="pause", status="success").inc()
    return _serialize_pilot_cohort(snapshot)
