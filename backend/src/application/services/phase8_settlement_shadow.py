"""Phase 8 shadow settlement, payout, and reporting comparison helpers."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from src.application.services.phase4_reconciliation import build_phase4_settlement_reconciliation_pack
from src.application.services.phase7_reporting_marts import build_phase7_reporting_marts_pack

REPORT_VERSION = "phase8-settlement-shadow-v1"

_WARNING_ONLY_CODES = {
    "phase4_reference_not_green",
    "analytical_reference_not_green",
}


@dataclass(frozen=True)
class SettlementShadowMismatch:
    code: str
    severity: str
    source_family: str
    source_reference: str
    message: str
    details: dict[str, Any]
    approved: bool = False
    approval_reference: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "source_family": self.source_family,
            "source_reference": self.source_reference,
            "message": self.message,
            "details": self.details,
            "approved": self.approved,
            "approval_reference": self.approval_reference,
        }


def build_phase8_settlement_shadow_pack(snapshot: dict[str, Any]) -> dict[str, Any]:
    metadata = dict(snapshot.get("metadata") or {})
    phase4_snapshot = dict(snapshot.get("phase4_snapshot") or {})
    analytical_snapshot = dict(snapshot.get("analytical_snapshot") or {})
    statement_shadow_observations = _sorted_rows(snapshot.get("statement_shadow_observations", []))
    liability_shadow_observations = _sorted_rows(snapshot.get("liability_shadow_observations", []))
    payout_dry_run_observations = _sorted_rows(snapshot.get("payout_dry_run_observations", []))
    partner_export_observations = _sorted_rows(snapshot.get("partner_export_observations", []))
    amount_tolerances = _sorted_rows(snapshot.get("amount_tolerances", []))
    approved_divergences = _sorted_rows(snapshot.get("approved_divergences", []))

    phase4_report = build_phase4_settlement_reconciliation_pack(phase4_snapshot)
    analytical_report = build_phase7_reporting_marts_pack(analytical_snapshot)

    statement_views_by_id = {
        str(item["statement_id"]): dict(item)
        for item in phase4_report.get("statement_views", [])
        if item.get("statement_id") is not None
    }
    liability_views_by_partner_id = {
        str(item["partner_account_id"]): dict(item)
        for item in phase4_report.get("liability_views", [])
        if item.get("partner_account_id") is not None
    }
    payout_views_by_instruction_id = {
        str(item["payout_instruction_id"]): dict(item)
        for item in phase4_report.get("payout_views", [])
        if item.get("payout_instruction_id") is not None
    }
    partner_reporting_rows_by_partner_id = {
        str(item["partner_account_id"]): dict(item)
        for item in analytical_report.get("partner_reporting_mart", [])
        if item.get("partner_account_id") is not None
    }
    payout_executions_by_instruction_id = _payout_executions_by_instruction(
        rows=phase4_snapshot.get("payout_executions", [])
    )

    mismatches: list[SettlementShadowMismatch] = []
    phase4_status = str((phase4_report.get("reconciliation") or {}).get("status") or "unknown")
    if phase4_status == "red":
        mismatches.append(
            SettlementShadowMismatch(
                code="phase4_reference_red",
                severity="blocking",
                source_family="phase4_reference",
                source_reference=str(metadata.get("snapshot_id") or "phase8"),
                message="Phase 4 settlement reference is red and cannot support Phase 8 finance shadow sign-off.",
                details={"phase4_status": phase4_status},
            )
        )
    elif phase4_status != "green":
        mismatches.append(
            SettlementShadowMismatch(
                code="phase4_reference_not_green",
                severity="warning",
                source_family="phase4_reference",
                source_reference=str(metadata.get("snapshot_id") or "phase8"),
                message="Phase 4 settlement reference is not green; finance shadow output must be read with caution.",
                details={"phase4_status": phase4_status},
            )
        )

    analytical_status = str((analytical_report.get("reconciliation") or {}).get("status") or "unknown")
    if analytical_status == "red":
        mismatches.append(
            SettlementShadowMismatch(
                code="analytical_reference_red",
                severity="blocking",
                source_family="analytical_reference",
                source_reference=str(metadata.get("snapshot_id") or "phase8"),
                message="Phase 7 analytical reference is red and cannot support Phase 8 reporting/export sign-off.",
                details={"analytical_status": analytical_status},
            )
        )
    elif analytical_status != "green":
        mismatches.append(
            SettlementShadowMismatch(
                code="analytical_reference_not_green",
                severity="warning",
                source_family="analytical_reference",
                source_reference=str(metadata.get("snapshot_id") or "phase8"),
                message="Phase 7 analytical reference is not green; export shadow output must be read with caution.",
                details={"analytical_status": analytical_status},
            )
        )

    tolerance_map = _build_amount_tolerance_map(amount_tolerances=amount_tolerances, metadata=metadata)

    statement_observations_by_id = _unique_observations_by_key(
        rows=statement_shadow_observations,
        key_field="statement_id",
        duplicate_code="duplicate_statement_shadow_observation",
        source_family="statement_shadow",
        source_label="statement shadow observation",
        mismatches=mismatches,
    )
    liability_observations_by_partner = _unique_observations_by_key(
        rows=liability_shadow_observations,
        key_field="partner_account_id",
        duplicate_code="duplicate_liability_shadow_observation",
        source_family="liability_shadow",
        source_label="liability shadow observation",
        mismatches=mismatches,
    )
    payout_observations_by_instruction = _unique_observations_by_key(
        rows=payout_dry_run_observations,
        key_field="payout_instruction_id",
        duplicate_code="duplicate_payout_dry_run_observation",
        source_family="payout_dry_run",
        source_label="payout dry-run observation",
        mismatches=mismatches,
    )
    export_observations_by_key = _unique_observations_by_key(
        rows=partner_export_observations,
        key_field="export_key",
        duplicate_code="duplicate_partner_export_observation",
        source_family="partner_export",
        source_label="partner export observation",
        mismatches=mismatches,
    )

    statement_shadow_views: list[dict[str, Any]] = []
    for statement_id in sorted(statement_views_by_id):
        canonical_view = statement_views_by_id[statement_id]
        observation = statement_observations_by_id.pop(statement_id, None)
        view, view_mismatches = _build_statement_shadow_view(
            statement_id=statement_id,
            canonical_view=canonical_view,
            observation=observation,
            tolerance_map=tolerance_map,
            approved_divergences=approved_divergences,
        )
        statement_shadow_views.append(view)
        mismatches.extend(view_mismatches)

    for statement_id in sorted(statement_observations_by_id):
        mismatches.extend(
            _approve_mismatches(
                mismatches=[
                    SettlementShadowMismatch(
                        code="unexpected_statement_shadow_observation_without_canonical_statement",
                        severity="blocking",
                        source_family="statement_shadow",
                        source_reference=statement_id,
                        message=(
                            "Statement shadow observation references a statement "
                            "missing from canonical settlement truth."
                        ),
                        details={},
                    )
                ],
                approved_divergences=approved_divergences,
            )
        )

    liability_shadow_views: list[dict[str, Any]] = []
    for partner_account_id in sorted(liability_views_by_partner_id):
        canonical_view = liability_views_by_partner_id[partner_account_id]
        observation = liability_observations_by_partner.pop(partner_account_id, None)
        view, view_mismatches = _build_liability_shadow_view(
            partner_account_id=partner_account_id,
            canonical_view=canonical_view,
            observation=observation,
            tolerance_map=tolerance_map,
            approved_divergences=approved_divergences,
        )
        liability_shadow_views.append(view)
        mismatches.extend(view_mismatches)

    for partner_account_id in sorted(liability_observations_by_partner):
        mismatches.extend(
            _approve_mismatches(
                mismatches=[
                    SettlementShadowMismatch(
                        code="unexpected_liability_shadow_observation_without_canonical_partner",
                        severity="blocking",
                        source_family="liability_shadow",
                        source_reference=partner_account_id,
                        message=(
                            "Liability shadow observation references a partner "
                            "account missing from canonical settlement truth."
                        ),
                        details={},
                    )
                ],
                approved_divergences=approved_divergences,
            )
        )

    payout_dry_run_views: list[dict[str, Any]] = []
    for instruction_id in sorted(payout_views_by_instruction_id):
        canonical_view = payout_views_by_instruction_id[instruction_id]
        observation = payout_observations_by_instruction.pop(instruction_id, None)
        liability_view = liability_views_by_partner_id.get(str(canonical_view.get("partner_account_id") or ""))
        dry_run_executions = payout_executions_by_instruction_id.get(instruction_id, [])
        view, view_mismatches = _build_payout_dry_run_view(
            instruction_id=instruction_id,
            canonical_view=canonical_view,
            liability_view=liability_view,
            dry_run_executions=dry_run_executions,
            observation=observation,
            tolerance_map=tolerance_map,
            approved_divergences=approved_divergences,
        )
        payout_dry_run_views.append(view)
        mismatches.extend(view_mismatches)

    for instruction_id in sorted(payout_observations_by_instruction):
        mismatches.extend(
            _approve_mismatches(
                mismatches=[
                    SettlementShadowMismatch(
                        code="unexpected_payout_dry_run_observation_without_instruction",
                        severity="blocking",
                        source_family="payout_dry_run",
                        source_reference=instruction_id,
                        message=(
                            "Payout dry-run observation references an instruction "
                            "missing from canonical settlement truth."
                        ),
                        details={},
                    )
                ],
                approved_divergences=approved_divergences,
            )
        )

    partner_export_views: list[dict[str, Any]] = []
    for export_key in sorted(export_observations_by_key):
        observation = export_observations_by_key[export_key]
        partner_account_id = _string_or_none(observation.get("partner_account_id"))
        canonical_row = partner_reporting_rows_by_partner_id.get(partner_account_id or "")
        view, view_mismatches = _build_partner_export_view(
            export_key=export_key,
            observation=observation,
            canonical_row=canonical_row,
            tolerance_map=tolerance_map,
            approved_divergences=approved_divergences,
        )
        partner_export_views.append(view)
        mismatches.extend(view_mismatches)

    mismatch_counts = dict(Counter(item.code for item in mismatches))
    blocking_mismatches = [item.to_dict() for item in mismatches if item.severity == "blocking"]
    tolerated_mismatches = [item.to_dict() for item in mismatches if item.approved]
    status = "green"
    if blocking_mismatches:
        status = "red"
    elif mismatches:
        status = "yellow"

    return {
        "metadata": {
            "report_version": REPORT_VERSION,
            "generated_at": metadata.get("replay_generated_at") or datetime.now(UTC).isoformat(),
            "snapshot_id": metadata.get("snapshot_id"),
            "source": metadata.get("source"),
        },
        "input_summary": {
            "statement_shadow_observations": len(statement_shadow_observations),
            "liability_shadow_observations": len(liability_shadow_observations),
            "payout_dry_run_observations": len(payout_dry_run_observations),
            "partner_export_observations": len(partner_export_observations),
            "amount_tolerances": len(amount_tolerances),
            "approved_divergences": len(approved_divergences),
        },
        "phase4_reference": {
            "status": phase4_status,
            "reconciliation": phase4_report.get("reconciliation", {}),
        },
        "analytical_reference": {
            "status": analytical_status,
            "reconciliation": analytical_report.get("reconciliation", {}),
            "partner_reporting_mart_count": len(analytical_report.get("partner_reporting_mart", [])),
        },
        "statement_shadow_views": statement_shadow_views,
        "liability_shadow_views": liability_shadow_views,
        "payout_dry_run_views": payout_dry_run_views,
        "partner_export_views": partner_export_views,
        "pilot_finance_gate": {
            "status": status,
            "blocking_statement_ids": sorted(
                {
                    item["statement_id"]
                    for item in statement_shadow_views
                    if item.get("blocking_mismatch_codes")
                }
            ),
            "blocking_partner_account_ids": sorted(
                {
                    item["partner_account_id"]
                    for item in liability_shadow_views + partner_export_views
                    if item.get("blocking_mismatch_codes")
                }
            ),
            "blocking_payout_instruction_ids": sorted(
                {
                    item["payout_instruction_id"]
                    for item in payout_dry_run_views
                    if item.get("blocking_mismatch_codes")
                }
            ),
        },
        "reconciliation": {
            "status": status,
            "mismatch_counts": mismatch_counts,
            "mismatches": [item.to_dict() for item in mismatches],
            "blocking_mismatches": blocking_mismatches,
            "tolerated_mismatches": tolerated_mismatches,
        },
    }


def _build_statement_shadow_view(
    *,
    statement_id: str,
    canonical_view: dict[str, Any],
    observation: dict[str, Any] | None,
    tolerance_map: dict[tuple[str, str], Decimal],
    approved_divergences: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[SettlementShadowMismatch]]:
    mismatches: list[SettlementShadowMismatch] = []
    if observation is None:
        mismatches.extend(
            _approve_mismatches(
                mismatches=[
                    SettlementShadowMismatch(
                        code="missing_statement_shadow_observation",
                        severity="blocking",
                        source_family="statement_shadow",
                        source_reference=statement_id,
                        message="Canonical statement is missing a finance shadow observation.",
                        details={},
                    )
                ],
                approved_divergences=approved_divergences,
            )
        )
        return (
            {
                "statement_id": statement_id,
                "partner_account_id": canonical_view.get("partner_account_id"),
                "status": "missing",
                "mismatch_codes": [item.code for item in mismatches],
                "blocking_mismatch_codes": [item.code for item in mismatches if item.severity == "blocking"],
                "tolerated_mismatch_codes": [item.code for item in mismatches if item.approved],
                "canonical_statement_view": canonical_view,
                "shadow_observation": None,
            },
            mismatches,
        )

    canonical_status = _string_or_none(canonical_view.get("statement_status"))
    observed_status = _string_or_none(observation.get("observed_statement_status"))
    if observed_status != canonical_status:
        mismatches.append(
            SettlementShadowMismatch(
                code="statement_status_mismatch",
                severity="blocking",
                source_family="statement_shadow",
                source_reference=statement_id,
                message="Observed statement status differs from canonical statement lifecycle state.",
                details={
                    "expected_statement_status": canonical_status,
                    "observed_statement_status": observed_status,
                },
            )
        )

    mismatches.extend(
        _compare_amount_delta(
            source_family="statement_shadow",
            source_reference=statement_id,
            comparison_family="statement",
            metric_key="available_amount",
            expected_value=_to_decimal(canonical_view["statement_totals"]["available_amount"]),
            observed_value=_to_decimal(observation.get("observed_available_amount")),
            tolerance_map=tolerance_map,
            mismatch_code="statement_available_amount_delta_exceeded",
            message="Observed statement available amount differs from canonical statement truth beyond tolerance.",
        )
    )
    mismatches.extend(
        _compare_amount_delta(
            source_family="statement_shadow",
            source_reference=statement_id,
            comparison_family="statement",
            metric_key="reserve_amount",
            expected_value=_to_decimal(canonical_view["statement_totals"]["reserve_amount"]),
            observed_value=_to_decimal(observation.get("observed_reserve_amount")),
            tolerance_map=tolerance_map,
            mismatch_code="statement_reserve_amount_delta_exceeded",
            message="Observed statement reserve amount differs from canonical statement truth beyond tolerance.",
        )
    )
    mismatches.extend(
        _compare_amount_delta(
            source_family="statement_shadow",
            source_reference=statement_id,
            comparison_family="statement",
            metric_key="adjustment_net_amount",
            expected_value=_to_decimal(canonical_view["statement_totals"]["adjustment_net_amount"]),
            observed_value=_to_decimal(observation.get("observed_adjustment_net_amount")),
            tolerance_map=tolerance_map,
            mismatch_code="statement_adjustment_net_amount_delta_exceeded",
            message="Observed statement adjustment net amount differs from canonical statement truth beyond tolerance.",
        )
    )
    mismatches = _approve_mismatches(mismatches=mismatches, approved_divergences=approved_divergences)
    return (
        {
            "statement_id": statement_id,
            "partner_account_id": canonical_view.get("partner_account_id"),
            "status": "green" if not mismatches else "red",
            "mismatch_codes": [item.code for item in mismatches],
            "blocking_mismatch_codes": [item.code for item in mismatches if item.severity == "blocking"],
            "tolerated_mismatch_codes": [item.code for item in mismatches if item.approved],
            "canonical_statement_view": canonical_view,
            "shadow_observation": observation,
        },
        mismatches,
    )


def _build_liability_shadow_view(
    *,
    partner_account_id: str,
    canonical_view: dict[str, Any],
    observation: dict[str, Any] | None,
    tolerance_map: dict[tuple[str, str], Decimal],
    approved_divergences: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[SettlementShadowMismatch]]:
    mismatches: list[SettlementShadowMismatch] = []
    if observation is None:
        mismatches.extend(
            _approve_mismatches(
                mismatches=[
                    SettlementShadowMismatch(
                        code="missing_liability_shadow_observation",
                        severity="blocking",
                        source_family="liability_shadow",
                        source_reference=partner_account_id,
                        message="Canonical partner liability is missing a finance shadow observation.",
                        details={},
                    )
                ],
                approved_divergences=approved_divergences,
            )
        )
        return (
            {
                "partner_account_id": partner_account_id,
                "status": "missing",
                "mismatch_codes": [item.code for item in mismatches],
                "blocking_mismatch_codes": [item.code for item in mismatches if item.severity == "blocking"],
                "tolerated_mismatch_codes": [item.code for item in mismatches if item.approved],
                "canonical_liability_view": canonical_view,
                "shadow_observation": None,
            },
            mismatches,
        )

    liability_totals = canonical_view["liability_totals"]
    reserve_totals = canonical_view["reserve_totals"]
    mismatches.extend(
        _compare_amount_delta(
            source_family="liability_shadow",
            source_reference=partner_account_id,
            comparison_family="liability",
            metric_key="outstanding_statement_liability_amount",
            expected_value=_to_decimal(liability_totals["outstanding_statement_liability_amount"]),
            observed_value=_to_decimal(observation.get("observed_outstanding_statement_liability_amount")),
            tolerance_map=tolerance_map,
            mismatch_code="liability_outstanding_statement_amount_delta_exceeded",
            message=(
                "Observed outstanding statement liability differs from canonical "
                "settlement truth beyond tolerance."
            ),
        )
    )
    mismatches.extend(
        _compare_amount_delta(
            source_family="liability_shadow",
            source_reference=partner_account_id,
            comparison_family="liability",
            metric_key="completed_payout_amount",
            expected_value=_to_decimal(liability_totals["completed_payout_amount"]),
            observed_value=_to_decimal(observation.get("observed_completed_payout_amount")),
            tolerance_map=tolerance_map,
            mismatch_code="liability_completed_payout_amount_delta_exceeded",
            message="Observed completed payout amount differs from canonical settlement truth beyond tolerance.",
        )
    )
    mismatches.extend(
        _compare_amount_delta(
            source_family="liability_shadow",
            source_reference=partner_account_id,
            comparison_family="liability",
            metric_key="total_active_reserve_amount",
            expected_value=_to_decimal(reserve_totals["total_active_reserve_amount"]),
            observed_value=_to_decimal(observation.get("observed_total_active_reserve_amount")),
            tolerance_map=tolerance_map,
            mismatch_code="liability_total_active_reserve_amount_delta_exceeded",
            message="Observed active reserve total differs from canonical settlement truth beyond tolerance.",
        )
    )
    mismatches = _approve_mismatches(mismatches=mismatches, approved_divergences=approved_divergences)
    return (
        {
            "partner_account_id": partner_account_id,
            "status": "green" if not mismatches else "red",
            "mismatch_codes": [item.code for item in mismatches],
            "blocking_mismatch_codes": [item.code for item in mismatches if item.severity == "blocking"],
            "tolerated_mismatch_codes": [item.code for item in mismatches if item.approved],
            "canonical_liability_view": canonical_view,
            "shadow_observation": observation,
        },
        mismatches,
    )


def _build_payout_dry_run_view(
    *,
    instruction_id: str,
    canonical_view: dict[str, Any],
    liability_view: dict[str, Any] | None,
    dry_run_executions: list[dict[str, Any]],
    observation: dict[str, Any] | None,
    tolerance_map: dict[tuple[str, str], Decimal],
    approved_divergences: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[SettlementShadowMismatch]]:
    mismatches: list[SettlementShadowMismatch] = []
    if not dry_run_executions:
        mismatches.append(
            SettlementShadowMismatch(
                code="payout_dry_run_missing_canonical_execution",
                severity="blocking",
                source_family="payout_dry_run",
                source_reference=instruction_id,
                message=(
                    "Canonical settlement snapshot is missing a dry-run execution "
                    "for the observed payout instruction."
                ),
                details={},
            )
        )
    if str(canonical_view.get("instruction_status")) == "completed":
        mismatches.append(
            SettlementShadowMismatch(
                code="payout_dry_run_completed_instruction_unexpected",
                severity="blocking",
                source_family="payout_dry_run",
                source_reference=instruction_id,
                message="Dry-run payout instruction must not already be completed in canonical settlement truth.",
                details={},
            )
        )
    if observation is None:
        mismatches.extend(
            _approve_mismatches(
                mismatches=[
                    SettlementShadowMismatch(
                        code="missing_payout_dry_run_observation",
                        severity="blocking",
                        source_family="payout_dry_run",
                        source_reference=instruction_id,
                        message="Canonical dry-run payout instruction is missing an observed dry-run record.",
                        details={},
                    )
                ],
                approved_divergences=approved_divergences,
            )
        )
        base_mismatches = _approve_mismatches(mismatches=mismatches, approved_divergences=approved_divergences)
        return (
            {
                "payout_instruction_id": instruction_id,
                "partner_account_id": canonical_view.get("partner_account_id"),
                "status": "missing",
                "mismatch_codes": [item.code for item in base_mismatches],
                "blocking_mismatch_codes": [item.code for item in base_mismatches if item.severity == "blocking"],
                "tolerated_mismatch_codes": [item.code for item in base_mismatches if item.approved],
                "canonical_payout_view": canonical_view,
                "dry_run_observation": None,
                "canonical_dry_run_execution_ids": [str(item["id"]) for item in dry_run_executions if item.get("id")],
            },
            base_mismatches,
        )

    expected_instruction_status = _string_or_none(canonical_view.get("instruction_status"))
    observed_instruction_status = _string_or_none(observation.get("observed_instruction_status"))
    if observed_instruction_status != expected_instruction_status:
        mismatches.append(
            SettlementShadowMismatch(
                code="payout_dry_run_instruction_status_mismatch",
                severity="blocking",
                source_family="payout_dry_run",
                source_reference=instruction_id,
                message="Observed dry-run instruction status differs from canonical payout instruction state.",
                details={
                    "expected_instruction_status": expected_instruction_status,
                    "observed_instruction_status": observed_instruction_status,
                },
            )
        )

    expected_execution_statuses = sorted(
        {
            str(item.get("execution_status"))
            for item in dry_run_executions
            if item.get("execution_status") is not None
        }
    )
    observed_execution_statuses = sorted(
        {str(item) for item in observation.get("observed_execution_statuses") or [] if item is not None}
    )
    if observed_execution_statuses != expected_execution_statuses:
        mismatches.append(
            SettlementShadowMismatch(
                code="payout_dry_run_execution_status_mismatch",
                severity="blocking",
                source_family="payout_dry_run",
                source_reference=instruction_id,
                message="Observed dry-run execution statuses differ from canonical dry-run execution state.",
                details={
                    "expected_execution_statuses": expected_execution_statuses,
                    "observed_execution_statuses": observed_execution_statuses,
                },
            )
        )

    liability_totals = dict((liability_view or {}).get("liability_totals") or {})
    mismatches.extend(
        _compare_amount_delta(
            source_family="payout_dry_run",
            source_reference=instruction_id,
            comparison_family="payout_dry_run",
            metric_key="completed_payout_amount",
            expected_value=_to_decimal(liability_totals.get("completed_payout_amount", 0)),
            observed_value=_to_decimal(observation.get("observed_completed_payout_amount")),
            tolerance_map=tolerance_map,
            mismatch_code="payout_dry_run_completed_payout_amount_delta_exceeded",
            message=(
                "Observed dry-run completed payout amount differs from canonical "
                "settlement liability beyond tolerance."
            ),
        )
    )
    mismatches.extend(
        _compare_amount_delta(
            source_family="payout_dry_run",
            source_reference=instruction_id,
            comparison_family="payout_dry_run",
            metric_key="outstanding_statement_liability_amount",
            expected_value=_to_decimal(liability_totals.get("outstanding_statement_liability_amount", 0)),
            observed_value=_to_decimal(observation.get("observed_outstanding_statement_liability_amount")),
            tolerance_map=tolerance_map,
            mismatch_code="payout_dry_run_outstanding_liability_amount_delta_exceeded",
            message=(
                "Observed dry-run outstanding liability differs from canonical "
                "settlement liability beyond tolerance."
            ),
        )
    )
    mismatches = _approve_mismatches(mismatches=mismatches, approved_divergences=approved_divergences)
    return (
        {
            "payout_instruction_id": instruction_id,
            "partner_account_id": canonical_view.get("partner_account_id"),
            "status": "green" if not mismatches else "red",
            "mismatch_codes": [item.code for item in mismatches],
            "blocking_mismatch_codes": [item.code for item in mismatches if item.severity == "blocking"],
            "tolerated_mismatch_codes": [item.code for item in mismatches if item.approved],
            "canonical_payout_view": canonical_view,
            "canonical_dry_run_execution_ids": [str(item["id"]) for item in dry_run_executions if item.get("id")],
            "dry_run_observation": observation,
        },
        mismatches,
    )


def _build_partner_export_view(
    *,
    export_key: str,
    observation: dict[str, Any],
    canonical_row: dict[str, Any] | None,
    tolerance_map: dict[tuple[str, str], Decimal],
    approved_divergences: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[SettlementShadowMismatch]]:
    partner_account_id = _string_or_none(observation.get("partner_account_id"))
    mismatches: list[SettlementShadowMismatch] = []
    if canonical_row is None:
        mismatches.extend(
            _approve_mismatches(
                mismatches=[
                    SettlementShadowMismatch(
                        code="partner_export_missing_partner_row",
                        severity="blocking",
                        source_family="partner_export",
                        source_reference=export_key,
                        message="Partner export observation does not map to a canonical partner reporting mart row.",
                        details={"partner_account_id": partner_account_id},
                    )
                ],
                approved_divergences=approved_divergences,
            )
        )
        return (
            {
                "export_key": export_key,
                "partner_account_id": partner_account_id,
                "status": "missing",
                "mismatch_codes": [item.code for item in mismatches],
                "blocking_mismatch_codes": [item.code for item in mismatches if item.severity == "blocking"],
                "tolerated_mismatch_codes": [item.code for item in mismatches if item.approved],
                "export_status": _string_or_none(observation.get("export_status")),
                "canonical_partner_reporting_row": None,
            },
            mismatches,
        )

    observed_paid_conversion_count = _int_or_none(observation.get("observed_paid_conversion_count")) or 0
    expected_paid_conversion_count = int(canonical_row.get("paid_conversion_count", 0))
    if observed_paid_conversion_count != expected_paid_conversion_count:
        mismatches.append(
            SettlementShadowMismatch(
                code="partner_export_paid_conversion_count_mismatch",
                severity="blocking",
                source_family="partner_export",
                source_reference=export_key,
                message="Partner export paid-conversion count differs from canonical reporting truth.",
                details={
                    "expected_paid_conversion_count": expected_paid_conversion_count,
                    "observed_paid_conversion_count": observed_paid_conversion_count,
                },
            )
        )

    mismatches.extend(
        _compare_amount_delta(
            source_family="partner_export",
            source_reference=export_key,
            comparison_family="partner_export",
            metric_key="available_earnings_amount",
            expected_value=_to_decimal(canonical_row.get("available_earnings_amount")),
            observed_value=_to_decimal(observation.get("observed_available_earnings_amount")),
            tolerance_map=tolerance_map,
            mismatch_code="partner_export_available_earnings_amount_mismatch",
            message=(
                "Partner export available earnings amount differs from canonical "
                "partner reporting beyond tolerance."
            ),
        )
    )
    mismatches.extend(
        _compare_amount_delta(
            source_family="partner_export",
            source_reference=export_key,
            comparison_family="partner_export",
            metric_key="statement_liability_amount",
            expected_value=_to_decimal(canonical_row.get("statement_liability_amount")),
            observed_value=_to_decimal(observation.get("observed_statement_liability_amount")),
            tolerance_map=tolerance_map,
            mismatch_code="partner_export_statement_liability_amount_mismatch",
            message=(
                "Partner export statement liability amount differs from canonical "
                "partner reporting beyond tolerance."
            ),
        )
    )

    observed_currency_codes = _sorted_strings(observation.get("observed_currency_codes") or [])
    expected_currency_codes = _sorted_strings(canonical_row.get("currency_codes") or [])
    if observed_currency_codes != expected_currency_codes:
        mismatches.append(
            SettlementShadowMismatch(
                code="partner_export_currency_codes_mismatch",
                severity="blocking",
                source_family="partner_export",
                source_reference=export_key,
                message="Partner export currency coverage differs from canonical partner reporting.",
                details={
                    "expected_currency_codes": expected_currency_codes,
                    "observed_currency_codes": observed_currency_codes,
                },
            )
        )

    mismatches = _approve_mismatches(mismatches=mismatches, approved_divergences=approved_divergences)
    return (
        {
            "export_key": export_key,
            "partner_account_id": partner_account_id,
            "status": "green" if not mismatches else "red",
            "mismatch_codes": [item.code for item in mismatches],
            "blocking_mismatch_codes": [item.code for item in mismatches if item.severity == "blocking"],
            "tolerated_mismatch_codes": [item.code for item in mismatches if item.approved],
            "export_status": _string_or_none(observation.get("export_status")),
            "canonical_partner_reporting_row": canonical_row,
        },
        mismatches,
    )


def _unique_observations_by_key(
    *,
    rows: list[dict[str, Any]],
    key_field: str,
    duplicate_code: str,
    source_family: str,
    source_label: str,
    mismatches: list[SettlementShadowMismatch],
) -> dict[str, dict[str, Any]]:
    observations_by_key: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = _string_or_none(row.get(key_field))
        if key is None:
            continue
        if key in observations_by_key:
            mismatches.append(
                SettlementShadowMismatch(
                    code=duplicate_code,
                    severity="blocking",
                    source_family=source_family,
                    source_reference=key,
                    message=f"More than one {source_label} was provided for the same canonical object.",
                    details={},
                )
            )
        observations_by_key[key] = row
    return observations_by_key


def _build_amount_tolerance_map(
    *, amount_tolerances: list[dict[str, Any]], metadata: dict[str, Any]
) -> dict[tuple[str, str], Decimal]:
    tolerance_map: dict[tuple[str, str], Decimal] = {}
    default_tolerance = _decimal_or_none(metadata.get("default_max_amount_delta"))
    if default_tolerance is not None:
        for comparison_family, metric_keys in {
            "statement": ("available_amount", "reserve_amount", "adjustment_net_amount"),
            "liability": (
                "outstanding_statement_liability_amount",
                "completed_payout_amount",
                "total_active_reserve_amount",
            ),
            "payout_dry_run": ("completed_payout_amount", "outstanding_statement_liability_amount"),
            "partner_export": ("available_earnings_amount", "statement_liability_amount"),
        }.items():
            for metric_key in metric_keys:
                tolerance_map[(comparison_family, metric_key)] = default_tolerance

    for row in amount_tolerances:
        comparison_family = _string_or_none(row.get("comparison_family"))
        metric_key = _string_or_none(row.get("metric_key"))
        max_delta_amount = _decimal_or_none(row.get("max_delta_amount"))
        if comparison_family is None or metric_key is None or max_delta_amount is None:
            continue
        tolerance_map[(comparison_family, metric_key)] = max_delta_amount
    return tolerance_map


def _compare_amount_delta(
    *,
    source_family: str,
    source_reference: str,
    comparison_family: str,
    metric_key: str,
    expected_value: Decimal,
    observed_value: Decimal,
    tolerance_map: dict[tuple[str, str], Decimal],
    mismatch_code: str,
    message: str,
) -> list[SettlementShadowMismatch]:
    tolerance = tolerance_map.get((comparison_family, metric_key), Decimal("0.00"))
    delta = abs(observed_value - expected_value)
    if delta <= tolerance:
        return []
    return [
        SettlementShadowMismatch(
            code=mismatch_code,
            severity="blocking",
            source_family=source_family,
            source_reference=source_reference,
            message=message,
            details={
                "metric_key": metric_key,
                "expected_value": float(expected_value),
                "observed_value": float(observed_value),
                "delta_amount": float(delta),
                "max_delta_amount": float(tolerance),
            },
        )
    ]


def _approve_mismatches(
    *, mismatches: list[SettlementShadowMismatch], approved_divergences: list[dict[str, Any]]
) -> list[SettlementShadowMismatch]:
    approved: list[SettlementShadowMismatch] = []
    for mismatch in mismatches:
        if mismatch.code in _WARNING_ONLY_CODES:
            approved.append(mismatch)
            continue
        approval_reference = _match_approved_divergence(
            mismatch=mismatch,
            approved_divergences=approved_divergences,
        )
        if approval_reference is None:
            approved.append(mismatch)
            continue
        approved.append(
            SettlementShadowMismatch(
                code=mismatch.code,
                severity="warning",
                source_family=mismatch.source_family,
                source_reference=mismatch.source_reference,
                message=mismatch.message,
                details=mismatch.details,
                approved=True,
                approval_reference=approval_reference,
            )
        )
    return approved


def _match_approved_divergence(
    *, mismatch: SettlementShadowMismatch, approved_divergences: list[dict[str, Any]]
) -> str | None:
    for row in approved_divergences:
        if _string_or_none(row.get("code")) != mismatch.code:
            continue
        approved_source_family = _string_or_none(row.get("source_family"))
        approved_source_reference = _string_or_none(row.get("source_reference"))
        if approved_source_family not in {None, mismatch.source_family}:
            continue
        if approved_source_reference not in {None, mismatch.source_reference}:
            continue
        return str(row.get("approval_reference") or row.get("id") or mismatch.code)
    return None


def _payout_executions_by_instruction(rows: Any) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows or []:
        materialized = dict(row)
        if str(materialized.get("execution_mode")) != "dry_run":
            continue
        instruction_id = _string_or_none(materialized.get("payout_instruction_id"))
        if instruction_id is None:
            continue
        grouped[instruction_id].append(materialized)
    for instruction_id in grouped:
        grouped[instruction_id] = sorted(
            grouped[instruction_id],
            key=lambda item: (
                _normalize_timestamp(item.get("created_at")),
                str(item.get("id", "")),
            ),
        )
    return grouped


def _sorted_rows(rows: Any) -> list[dict[str, Any]]:
    materialized = [dict(item) for item in rows or []]
    return sorted(
        materialized,
        key=lambda item: (
            str(item.get("source_family") or item.get("comparison_family") or ""),
            str(
                item.get("statement_id")
                or item.get("partner_account_id")
                or item.get("payout_instruction_id")
                or item.get("export_key")
                or item.get("id")
                or ""
            ),
        ),
    )


def _sorted_strings(values: Any) -> list[str]:
    return sorted(str(item) for item in values or [] if item is not None)


def _int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _decimal_or_none(value: Any) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


def _to_decimal(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def _normalize_timestamp(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    if text.endswith("Z"):
        return text[:-1] + "+00:00"
    return text
