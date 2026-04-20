from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.pilots.pilot_cohorts import GetPilotCohortReadinessUseCase
from src.application.use_cases.settlement import ListPartnerPayoutAccountsUseCase
from src.domain.enums import PilotCohortStatus, PilotLaneKey
from src.infrastructure.database.repositories.governance_repo import GovernanceRepository
from src.infrastructure.database.repositories.pilot_cohort_repo import PilotCohortRepository

from .workspace_integrations import BuildPartnerWorkspacePostbackReadinessUseCase

_PORTAL_LANE_BY_PILOT_LANE = {
    PilotLaneKey.CREATOR_AFFILIATE.value: "creator_affiliate",
    PilotLaneKey.PERFORMANCE_MEDIA_BUYER.value: "performance_media",
    PilotLaneKey.RESELLER_DISTRIBUTION.value: "reseller_api",
}
_ORDERED_PORTAL_LANES = (
    "creator_affiliate",
    "performance_media",
    "reseller_api",
)
_BLOCKED_WORKSPACE_STATUSES = {
    "restricted",
    "suspended",
    "rejected",
    "terminated",
}
_REVIEW_WORKSPACE_STATUSES = {
    "draft",
    "email_verified",
    "submitted",
    "under_review",
    "waitlisted",
    "approved_probation",
    "needs_info",
}
_PROBATION_WORKSPACE_STATUSES = {"approved_probation"}
_RESTRICTED_WORKSPACE_STATUSES = {"restricted", "suspended"}
_COHORT_STATUS_PRIORITY = {
    PilotCohortStatus.ACTIVE.value: 5,
    PilotCohortStatus.SCHEDULED.value: 4,
    PilotCohortStatus.PAUSED.value: 3,
    PilotCohortStatus.COMPLETED.value: 2,
    PilotCohortStatus.CANCELLED.value: 1,
}
_REASON_NOTE_BY_CODE = {
    "attribution_shadow_blocked": "Attribution shadow evidence is still blocking promotion for this lane.",
    "attribution_shadow_requires_caution": "Attribution shadow evidence is yellow and needs explicit caution.",
    "creative_approval_incomplete": "Creative approval is still incomplete for the current lane posture.",
    "go_no_go_hold": "Latest go/no-go decision is holding this lane in review.",
    "go_no_go_missing": "No explicit go/no-go decision is recorded for this lane yet.",
    "go_no_go_no_go": "Latest go/no-go decision keeps this lane in no-go state.",
    "governance_action_blocking": "Governance actions still block this lane from normal rollout posture.",
    "owner_acknowledgement_missing": "Required owner acknowledgements are still missing for this lane.",
    "risk_review_blocking": "An open risk review is blocking normal lane posture.",
    "rollback_drill_failed": "The latest rollback drill did not pass for this lane.",
    "rollback_drill_missing": "No passed rollback drill exists for this lane yet.",
    "rollout_window_missing": "This lane does not have a rollout window attached yet.",
    "settlement_shadow_blocked": "Settlement shadow evidence is still blocking promotion for this lane.",
    "settlement_shadow_requires_caution": "Settlement shadow evidence is yellow and needs explicit caution.",
    "traffic_declaration_incomplete": "Traffic declarations are still incomplete for this lane.",
    "workspace_inactive": "Workspace status is not active enough for lane promotion.",
}
_PORTAL_LANE_ORDER = {lane: index for index, lane in enumerate(_ORDERED_PORTAL_LANES)}


@dataclass(frozen=True)
class PartnerWorkspaceProgramLaneView:
    lane_key: str
    membership_status: str
    owner_context_label: str
    pilot_cohort_id: UUID | None
    pilot_cohort_status: str | None
    runbook_gate_status: str | None
    blocking_reason_codes: list[str]
    warning_reason_codes: list[str]
    restriction_notes: list[str]
    readiness_notes: list[str]
    updated_at: datetime


@dataclass(frozen=True)
class PartnerWorkspaceProgramReadinessItemView:
    key: str
    status: str
    blocking_reason_codes: list[str]
    notes: list[str]


@dataclass(frozen=True)
class PartnerWorkspaceProgramsView:
    canonical_source: str
    primary_lane_key: str | None
    lane_memberships: list[PartnerWorkspaceProgramLaneView]
    readiness_items: list[PartnerWorkspaceProgramReadinessItemView]
    updated_at: datetime


class BuildPartnerWorkspaceProgramsUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._pilot_repo = PilotCohortRepository(session)
        self._governance = GovernanceRepository(session)

    async def execute(
        self,
        *,
        partner_account_id: UUID,
        workspace_status: str,
        workspace_label: str,
    ) -> PartnerWorkspaceProgramsView:
        cohorts = await self._pilot_repo.list_pilot_cohorts(
            partner_account_id=partner_account_id,
            limit=200,
            offset=0,
        )
        latest_cohort_by_portal_lane = _select_latest_lane_cohorts(cohorts)
        traffic_declarations = await self._governance.list_traffic_declarations(
            partner_account_id=partner_account_id,
            limit=500,
            offset=0,
        )
        creative_approvals = await self._governance.list_creative_approvals(
            partner_account_id=partner_account_id,
            limit=500,
            offset=0,
        )
        payout_accounts = await ListPartnerPayoutAccountsUseCase(self._session).execute(
            partner_account_id=partner_account_id,
            limit=100,
            offset=0,
        )
        postback_readiness = await BuildPartnerWorkspacePostbackReadinessUseCase(self._session).execute(
            partner_account_id=partner_account_id,
            workspace_status=workspace_status,
            workspace_label=workspace_label,
        )

        lane_memberships: list[PartnerWorkspaceProgramLaneView] = []
        for portal_lane in _ORDERED_PORTAL_LANES:
            cohort = latest_cohort_by_portal_lane.get(portal_lane)
            if cohort is None:
                lane_memberships.append(
                    _build_unapplied_lane_view(
                        portal_lane=portal_lane,
                        workspace_status=workspace_status,
                    )
                )
                continue

            readiness = await GetPilotCohortReadinessUseCase(self._session).execute(cohort_id=cohort.id)
            lane_memberships.append(
                _build_lane_view_from_readiness(
                    portal_lane=portal_lane,
                    workspace_status=workspace_status,
                    readiness=readiness,
                )
            )

        readiness_items = [
            _build_finance_readiness_item(
                workspace_status=workspace_status,
                payout_accounts=payout_accounts,
            ),
            _build_compliance_readiness_item(
                workspace_status=workspace_status,
                traffic_declarations=traffic_declarations,
                creative_approvals=creative_approvals,
                lane_memberships=lane_memberships,
            ),
            _build_technical_readiness_item(
                workspace_status=workspace_status,
                lane_memberships=lane_memberships,
                postback_readiness=postback_readiness,
            ),
        ]
        updated_at = max(
            [lane.updated_at for lane in lane_memberships]
            + [datetime.now(UTC)]
        )

        return PartnerWorkspaceProgramsView(
            canonical_source="pilot_cohorts",
            primary_lane_key=_resolve_primary_lane_key(lane_memberships),
            lane_memberships=lane_memberships,
            readiness_items=readiness_items,
            updated_at=updated_at,
        )


def _select_latest_lane_cohorts(cohorts: list) -> dict[str, object]:
    grouped: dict[str, object] = {}
    for cohort in sorted(
        cohorts,
        key=lambda item: (
            _COHORT_STATUS_PRIORITY.get(item.cohort_status, 0),
            _normalize_utc(item.activated_at or item.scheduled_start_at or item.updated_at or item.created_at),
            _normalize_utc(item.updated_at or item.created_at),
        ),
        reverse=True,
    ):
        portal_lane = _PORTAL_LANE_BY_PILOT_LANE.get(cohort.lane_key)
        if portal_lane is None:
            continue
        grouped.setdefault(portal_lane, cohort)
    return grouped


def _build_unapplied_lane_view(
    *,
    portal_lane: str,
    workspace_status: str,
) -> PartnerWorkspaceProgramLaneView:
    if workspace_status in _BLOCKED_WORKSPACE_STATUSES:
        restriction_notes = [
            "Workspace restrictions currently prevent new lane activation.",
        ]
    elif workspace_status in _REVIEW_WORKSPACE_STATUSES:
        restriction_notes = [
            "No canonical lane cohort exists yet while the workspace remains in review posture.",
        ]
    else:
        restriction_notes = [
            "No canonical lane cohort exists for this workspace yet.",
        ]

    return PartnerWorkspaceProgramLaneView(
        lane_key=portal_lane,
        membership_status="not_applied",
        owner_context_label="Pending partner ops assignment",
        pilot_cohort_id=None,
        pilot_cohort_status=None,
        runbook_gate_status=None,
        blocking_reason_codes=[],
        warning_reason_codes=[],
        restriction_notes=restriction_notes,
        readiness_notes=[],
        updated_at=datetime.now(UTC),
    )


def _build_lane_view_from_readiness(
    *,
    portal_lane: str,
    workspace_status: str,
    readiness,
) -> PartnerWorkspaceProgramLaneView:
    cohort = readiness.cohort
    blocking_reason_codes = list(readiness.blocking_reason_codes)
    warning_reason_codes = list(readiness.warning_reason_codes)
    restriction_notes = _notes_for_reason_codes(blocking_reason_codes)
    readiness_notes = _notes_for_reason_codes(warning_reason_codes)

    if not restriction_notes:
        restriction_notes = [
            _membership_note_for_status(
                workspace_status=workspace_status,
                cohort_status=cohort.cohort_status,
            )
        ]

    readiness_notes = [
        *readiness_notes,
        f"Owner context: {_humanize_owner_context(cohort.owner_team)}.",
        *(
            [f"Runbook gate: {readiness.runbook_gate_status}."]
            if readiness.runbook_gate_status
            else []
        ),
    ]

    return PartnerWorkspaceProgramLaneView(
        lane_key=portal_lane,
        membership_status=_map_membership_status(
            workspace_status=workspace_status,
            cohort_status=cohort.cohort_status,
        ),
        owner_context_label=_humanize_owner_context(cohort.owner_team),
        pilot_cohort_id=cohort.id,
        pilot_cohort_status=cohort.cohort_status,
        runbook_gate_status=readiness.runbook_gate_status,
        blocking_reason_codes=blocking_reason_codes,
        warning_reason_codes=warning_reason_codes,
        restriction_notes=restriction_notes,
        readiness_notes=readiness_notes,
        updated_at=_normalize_utc(cohort.updated_at or cohort.created_at),
    )


def _build_finance_readiness_item(
    *,
    workspace_status: str,
    payout_accounts: list,
) -> PartnerWorkspaceProgramReadinessItemView:
    if workspace_status in _BLOCKED_WORKSPACE_STATUSES:
        status = "blocked"
        notes = ["Workspace restrictions currently block payout-bearing lane rollout."]
    elif not payout_accounts:
        status = "not_started"
        notes = ["No payout account is recorded for this workspace yet."]
    elif any(
        account.account_status == "active"
        and account.verification_status == "verified"
        and account.approval_status == "approved"
        for account in payout_accounts
    ):
        status = "ready"
        notes = ["At least one verified and approved payout account is available."]
    else:
        status = "in_progress"
        notes = ["Finance setup exists, but payout accounts are still pending verification or approval."]

    return PartnerWorkspaceProgramReadinessItemView(
        key="finance",
        status=status,
        blocking_reason_codes=["workspace_blocked"] if status == "blocked" else [],
        notes=notes,
    )


def _build_compliance_readiness_item(
    *,
    workspace_status: str,
    traffic_declarations: list,
    creative_approvals: list,
    lane_memberships: list[PartnerWorkspaceProgramLaneView],
) -> PartnerWorkspaceProgramReadinessItemView:
    blocking_codes: list[str] = []
    if workspace_status in _BLOCKED_WORKSPACE_STATUSES:
        status = "blocked"
        notes = ["Workspace restrictions currently block compliance-driven lane rollout."]
        blocking_codes.append("workspace_blocked")
    elif workspace_status == "needs_info":
        status = "evidence_requested"
        notes = ["Workspace still has requested-info posture and needs more evidence."]
        blocking_codes.append("needs_info")
    else:
        compliance_blockers = {
            code
            for lane in lane_memberships
            for code in lane.blocking_reason_codes
            if code in {
                "traffic_declaration_incomplete",
                "creative_approval_incomplete",
                "governance_action_blocking",
                "risk_review_blocking",
            }
        }
        if compliance_blockers:
            status = "evidence_requested"
            blocking_codes.extend(sorted(compliance_blockers))
            notes = _notes_for_reason_codes(sorted(compliance_blockers))
        elif traffic_declarations or creative_approvals:
            has_complete_declaration = any(
                item.declaration_status == "complete" for item in traffic_declarations
            )
            has_complete_approval = any(
                item.approval_status == "complete" for item in creative_approvals
            )
            if has_complete_declaration or has_complete_approval:
                status = "approved"
                notes = ["Canonical compliance evidence exists for the current workspace lanes."]
            else:
                status = "declarations_complete"
                notes = ["Compliance submissions exist, but final approvals are still in flight."]
        else:
            status = "not_started"
            notes = ["No canonical traffic declaration or creative approval exists yet."]

    return PartnerWorkspaceProgramReadinessItemView(
        key="compliance",
        status=status,
        blocking_reason_codes=blocking_codes,
        notes=notes,
    )


def _build_technical_readiness_item(
    *,
    workspace_status: str,
    lane_memberships: list[PartnerWorkspaceProgramLaneView],
    postback_readiness,
) -> PartnerWorkspaceProgramReadinessItemView:
    performance_lane = next(
        (lane for lane in lane_memberships if lane.lane_key == "performance_media"),
        None,
    )
    if performance_lane is None or performance_lane.membership_status == "not_applied":
        return PartnerWorkspaceProgramReadinessItemView(
            key="technical",
            status="not_required",
            blocking_reason_codes=[],
            notes=["No active performance-media lane requires technical rollout posture yet."],
        )

    if workspace_status in _BLOCKED_WORKSPACE_STATUSES or postback_readiness.status == "blocked":
        status = "blocked"
    elif postback_readiness.status == "complete":
        status = "ready"
    else:
        status = "in_progress"

    blocking_codes = (
        ["postback_blocked"]
        if status == "blocked"
        else ["postback_pending"]
        if status == "in_progress"
        else []
    )
    return PartnerWorkspaceProgramReadinessItemView(
        key="technical",
        status=status,
        blocking_reason_codes=blocking_codes,
        notes=list(postback_readiness.notes),
    )


def _resolve_primary_lane_key(
    lane_memberships: list[PartnerWorkspaceProgramLaneView],
) -> str | None:
    ranked = sorted(
        lane_memberships,
        key=lambda item: (
            _membership_priority(item.membership_status),
            -_PORTAL_LANE_ORDER[item.lane_key],
        ),
        reverse=True,
    )
    top = ranked[0] if ranked else None
    if top is None or top.membership_status == "not_applied":
        return None
    return top.lane_key


def _membership_priority(status: str) -> int:
    if status == "approved_active":
        return 6
    if status == "approved_probation":
        return 5
    if status == "pending":
        return 4
    if status == "paused":
        return 3
    if status == "suspended":
        return 2
    if status in {"declined", "terminated"}:
        return 1
    return 0


def _map_membership_status(*, workspace_status: str, cohort_status: str) -> str:
    if cohort_status == PilotCohortStatus.CANCELLED.value:
        return "declined"
    if workspace_status in _PROBATION_WORKSPACE_STATUSES:
        return "approved_probation"
    if workspace_status in _RESTRICTED_WORKSPACE_STATUSES:
        return "suspended" if cohort_status != PilotCohortStatus.PAUSED.value else "paused"
    if workspace_status == "terminated":
        return "terminated"
    if workspace_status in _REVIEW_WORKSPACE_STATUSES or cohort_status == PilotCohortStatus.SCHEDULED.value:
        return "pending"
    if cohort_status == PilotCohortStatus.PAUSED.value:
        return "paused"
    return "approved_active"


def _membership_note_for_status(*, workspace_status: str, cohort_status: str) -> str:
    if cohort_status == PilotCohortStatus.SCHEDULED.value:
        return "Lane cohort exists and remains scheduled for a later activation window."
    if cohort_status == PilotCohortStatus.PAUSED.value:
        return "Lane cohort exists but is currently paused."
    if workspace_status in _PROBATION_WORKSPACE_STATUSES:
        return "Lane is running in probation posture and remains explicitly gated."
    if workspace_status in _RESTRICTED_WORKSPACE_STATUSES:
        return "Lane remains constrained by the current workspace restriction posture."
    return "Lane has an explicit canonical cohort and readiness trail."


def _notes_for_reason_codes(reason_codes: list[str]) -> list[str]:
    return [_REASON_NOTE_BY_CODE.get(code, _humanize_reason_code(code)) for code in reason_codes]


def _humanize_reason_code(reason_code: str) -> str:
    return reason_code.replace("_", " ").capitalize() + "."


def _humanize_owner_context(owner_team: str) -> str:
    return owner_team.replace("_", " ").title()


def _normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
