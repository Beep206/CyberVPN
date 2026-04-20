from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.domain.enums import (
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
)


class PilotShadowEvidenceRequest(BaseModel):
    attribution_reference: str = Field(..., min_length=1, max_length=255)
    attribution_gate_status: PilotGateStatus
    settlement_reference: str = Field(..., min_length=1, max_length=255)
    settlement_gate_status: PilotGateStatus
    notes: list[str] = Field(default_factory=list)


class PilotShadowEvidenceResponse(BaseModel):
    attribution_reference: str
    attribution_gate_status: PilotGateStatus
    settlement_reference: str
    settlement_gate_status: PilotGateStatus
    notes: list[str] = Field(default_factory=list)


class PilotRolloutWindowRequest(BaseModel):
    window_kind: PilotRolloutWindowKind
    target_ref: str = Field(..., min_length=1, max_length=255)
    starts_at: datetime
    ends_at: datetime
    notes: list[str] = Field(default_factory=list)


class PilotRolloutWindowResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    id: UUID
    pilot_cohort_id: UUID
    window_kind: PilotRolloutWindowKind
    target_ref: str
    window_status: PilotRolloutWindowStatus
    starts_at: datetime
    ends_at: datetime
    notes: list[str] = Field(default_factory=list)
    created_by_admin_user_id: UUID | None = None
    closed_by_admin_user_id: UUID | None = None
    closed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class CreatePilotCohortRequest(BaseModel):
    cohort_key: str = Field(..., min_length=1, max_length=80)
    display_name: str = Field(..., min_length=1, max_length=120)
    lane_key: PilotLaneKey
    surface_key: PilotSurfaceKey
    partner_account_id: UUID | None = None
    owner_team: str = Field(..., min_length=1, max_length=40)
    owner_admin_user_id: UUID
    rollback_trigger_code: str = Field(..., min_length=1, max_length=120)
    shadow_evidence: PilotShadowEvidenceRequest
    rollout_windows: list[PilotRolloutWindowRequest] = Field(..., min_length=1)
    monitoring_payload: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class PausePilotCohortRequest(BaseModel):
    reason_code: str | None = Field(default=None, min_length=1, max_length=120)


class PilotOwnerAcknowledgementRequest(BaseModel):
    owner_team: PilotOwnerTeam
    runbook_reference: str = Field(..., min_length=1, max_length=255)
    notes: list[str] = Field(default_factory=list)


class PilotOwnerAcknowledgementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    id: UUID
    pilot_cohort_id: UUID
    owner_team: PilotOwnerTeam
    acknowledgement_status: PilotOwnerAcknowledgementStatus
    runbook_reference: str
    notes: list[str] = Field(default_factory=list)
    acknowledged_by_admin_user_id: UUID | None = None
    acknowledged_at: datetime
    created_at: datetime
    updated_at: datetime


class PilotRollbackDrillRequest(BaseModel):
    cutover_unit_key: str = Field(..., min_length=1, max_length=40)
    rollback_scope_class: PilotRollbackScopeClass
    trigger_code: str = Field(..., min_length=1, max_length=120)
    drill_status: PilotRollbackDrillStatus
    runbook_reference: str = Field(..., min_length=1, max_length=255)
    observed_metric_payload: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class PilotRollbackDrillResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    id: UUID
    pilot_cohort_id: UUID
    cutover_unit_key: str
    rollback_scope_class: PilotRollbackScopeClass
    trigger_code: str
    drill_status: PilotRollbackDrillStatus
    runbook_reference: str
    observed_metric_payload: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)
    executed_by_admin_user_id: UUID | None = None
    executed_at: datetime
    created_at: datetime
    updated_at: datetime


class PilotGoNoGoDecisionRequest(BaseModel):
    decision_status: PilotGoNoGoStatus
    decision_reason_code: str | None = Field(default=None, min_length=1, max_length=120)
    release_ring: str = Field(default="R3", min_length=2, max_length=10)
    rollback_scope_class: PilotRollbackScopeClass
    cutover_unit_keys: list[str] = Field(..., min_length=1)
    evidence_links: list[str] = Field(..., min_length=1)
    monitoring_snapshot_payload: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class PilotGoNoGoDecisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    id: UUID
    pilot_cohort_id: UUID
    decision_status: PilotGoNoGoStatus
    decision_reason_code: str | None = None
    release_ring: str
    rollback_scope_class: PilotRollbackScopeClass
    cutover_unit_keys: list[str] = Field(default_factory=list)
    evidence_links: list[str] = Field(default_factory=list)
    acknowledged_owner_teams: list[PilotOwnerTeam] = Field(default_factory=list)
    monitoring_snapshot_payload: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)
    decided_by_admin_user_id: UUID | None = None
    decided_at: datetime
    created_at: datetime
    updated_at: datetime


class PilotCohortResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    id: UUID
    cohort_key: str
    display_name: str
    lane_key: PilotLaneKey
    surface_key: PilotSurfaceKey
    cohort_status: PilotCohortStatus
    partner_account_id: UUID | None = None
    owner_team: str
    owner_admin_user_id: UUID
    rollback_trigger_code: str
    shadow_evidence: PilotShadowEvidenceResponse
    monitoring_payload: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)
    scheduled_start_at: datetime
    scheduled_end_at: datetime
    activated_at: datetime | None = None
    paused_at: datetime | None = None
    completed_at: datetime | None = None
    pause_reason_code: str | None = None
    created_by_admin_user_id: UUID | None = None
    activated_by_admin_user_id: UUID | None = None
    paused_by_admin_user_id: UUID | None = None
    created_at: datetime
    updated_at: datetime
    rollout_windows: list[PilotRolloutWindowResponse]


class PilotCohortReadinessResponse(BaseModel):
    cohort_id: UUID
    cohort_status: PilotCohortStatus
    activation_allowed: bool
    blocking_reason_codes: list[str]
    warning_reason_codes: list[str]
    blocking_risk_review_ids: list[UUID]
    blocking_governance_action_ids: list[UUID]
    runbook_gate_status: PilotGateStatus
    required_owner_teams: list[PilotOwnerTeam]
    acknowledged_owner_teams: list[PilotOwnerTeam]
    missing_owner_teams: list[PilotOwnerTeam]
    latest_rollback_drill_id: UUID | None = None
    latest_rollback_drill_status: PilotRollbackDrillStatus | None = None
    latest_go_no_go_decision_id: UUID | None = None
    latest_go_no_go_status: PilotGoNoGoStatus | None = None
    live_monitoring_snapshot: dict[str, Any]
    checked_at: datetime
