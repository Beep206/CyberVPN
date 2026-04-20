"""Phase 8 shadow attribution and explainability comparison helpers."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from src.application.services.phase3_explainability_replay import build_phase3_explainability_replay_pack
from src.application.services.phase7_reporting_marts import build_phase7_reporting_marts_pack

REPORT_VERSION = "phase8-attribution-shadow-v1"

DEFAULT_LANE_TOLERANCE = Decimal("0.00")

PRIMARY_LANE_PRECEDENCE = (
    "renewal_chain",
    "reseller_distribution",
    "creator_affiliate",
    "performance_media_buyer",
    "consumer_referral",
    "invite_gift",
)

_WARNING_ONLY_CODES = {
    "phase3_reference_not_green",
    "analytical_reference_not_green",
    "legacy_rule_path_mismatch",
}


@dataclass(frozen=True)
class AttributionShadowMismatch:
    code: str
    severity: str
    order_id: str | None
    lane_key: str | None
    message: str
    details: dict[str, Any]
    approved: bool = False
    approval_reference: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "order_id": self.order_id,
            "lane_key": self.lane_key,
            "message": self.message,
            "details": self.details,
            "approved": self.approved,
            "approval_reference": self.approval_reference,
        }


def build_phase8_attribution_shadow_pack(snapshot: dict[str, Any]) -> dict[str, Any]:
    metadata = dict(snapshot.get("metadata") or {})
    phase3_snapshot = dict(snapshot.get("phase3_snapshot") or {})
    analytical_snapshot = dict(snapshot.get("analytical_snapshot") or {})
    legacy_shadow_observations = _sorted_rows(snapshot.get("legacy_shadow_observations", []))
    approved_divergences = _sorted_rows(snapshot.get("approved_divergences", []))
    lane_tolerances = _sorted_rows(snapshot.get("lane_tolerances", []))

    phase3_report = build_phase3_explainability_replay_pack(phase3_snapshot)
    analytical_report = build_phase7_reporting_marts_pack(analytical_snapshot)

    orders = _sorted_rows(phase3_snapshot.get("orders", []))
    bindings_by_id = {
        str(binding["id"]): dict(binding)
        for binding in phase3_snapshot.get("bindings", [])
        if binding.get("id") is not None
    }
    order_cases_by_order_id = {
        str(item["order_id"]): dict(item)
        for item in phase3_report.get("order_cases", [])
        if item.get("order_id") is not None
    }
    reporting_order_rows_by_order_id = {
        str(item["order_id"]): dict(item)
        for item in analytical_report.get("order_reporting_mart", [])
        if item.get("order_id") is not None
    }

    observations_by_order_id: dict[str, dict[str, Any]] = {}
    mismatches: list[AttributionShadowMismatch] = []
    for observation in legacy_shadow_observations:
        order_id = _string_or_none(observation.get("order_id"))
        if order_id is None:
            continue
        if order_id in observations_by_order_id:
            mismatches.append(
                AttributionShadowMismatch(
                    code="duplicate_legacy_shadow_observation",
                    severity="blocking",
                    order_id=order_id,
                    lane_key=None,
                    message="More than one legacy shadow observation was provided for the same order.",
                    details={},
                )
            )
        observations_by_order_id[order_id] = observation

    analytical_status = str((analytical_report.get("reconciliation") or {}).get("status") or "unknown")
    if analytical_status == "red":
        mismatches.append(
            AttributionShadowMismatch(
                code="analytical_reference_red",
                severity="blocking",
                order_id=None,
                lane_key=None,
                message="Phase 7 analytical reference is red and cannot support Phase 8 attribution shadow sign-off.",
                details={"analytical_status": analytical_status},
            )
        )
    elif analytical_status != "green":
        mismatches.append(
            AttributionShadowMismatch(
                code="analytical_reference_not_green",
                severity="warning",
                order_id=None,
                lane_key=None,
                message="Phase 7 analytical reference is not green; read attribution shadow output with caution.",
                details={"analytical_status": analytical_status},
            )
        )

    phase3_status = str((phase3_report.get("comparison") or {}).get("status") or "unknown")
    if phase3_status == "red":
        mismatches.append(
            AttributionShadowMismatch(
                code="phase3_reference_red",
                severity="blocking",
                order_id=None,
                lane_key=None,
                message=(
                    "Phase 3 explainability reference is red and cannot support "
                    "Phase 8 attribution shadow sign-off."
                ),
                details={"phase3_status": phase3_status},
            )
        )
    elif phase3_status != "green":
        mismatches.append(
            AttributionShadowMismatch(
                code="phase3_reference_not_green",
                severity="warning",
                order_id=None,
                lane_key=None,
                message=(
                    "Phase 3 explainability reference is not green; shadow output "
                    "may inherit unresolved explainability drift."
                ),
                details={"phase3_status": phase3_status},
            )
        )

    tolerance_map = _build_lane_tolerance_map(lane_tolerances=lane_tolerances, metadata=metadata)
    shadow_order_views: list[dict[str, Any]] = []
    lane_accumulator: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "total_orders": 0,
            "divergent_orders": 0,
            "blocking_orders": 0,
            "tolerated_orders": 0,
            "order_ids": [],
        }
    )

    for order in orders:
        order_id = str(order["id"])
        order_case = order_cases_by_order_id.get(order_id)
        if order_case is None:
            continue
        lane_key = _resolve_primary_lane(order_case.get("lane_views") or {})
        lane_accumulator[lane_key]["total_orders"] += 1
        lane_accumulator[lane_key]["order_ids"].append(order_id)

        legacy_observation = observations_by_order_id.pop(order_id, None)
        reporting_row = reporting_order_rows_by_order_id.get(order_id)
        canonical_reference = dict(order_case.get("reference_attribution_result") or {})
        persisted_result = dict(order_case.get("persisted_attribution_result") or {})
        renewal_summary = dict(order_case.get("renewal_summary") or {})
        canonical_binding = _resolve_canonical_binding(
            order_case=order_case,
            bindings_by_id=bindings_by_id,
        )

        order_mismatches = _compare_shadow_order(
            order_id=order_id,
            lane_key=lane_key,
            canonical_reference=canonical_reference,
            persisted_result=persisted_result,
            canonical_binding=canonical_binding,
            renewal_summary=renewal_summary,
            legacy_observation=legacy_observation,
            reporting_row=reporting_row,
            approved_divergences=approved_divergences,
        )
        mismatches.extend(order_mismatches)

        blocking_codes = [item.code for item in order_mismatches if item.severity == "blocking"]
        tolerated_codes = [item.code for item in order_mismatches if item.approved]
        all_codes = [item.code for item in order_mismatches]
        if all_codes:
            lane_accumulator[lane_key]["divergent_orders"] += 1
        if blocking_codes:
            lane_accumulator[lane_key]["blocking_orders"] += 1
        elif tolerated_codes:
            lane_accumulator[lane_key]["tolerated_orders"] += 1

        shadow_order_views.append(
            {
                "order_id": order_id,
                "shadow_lane": lane_key,
                "winner_matches": not all_codes,
                "promotion_blocking": bool(blocking_codes),
                "canonical_reference": canonical_reference or None,
                "persisted_attribution_result": persisted_result or None,
                "canonical_binding": canonical_binding,
                "renewal_summary": renewal_summary or None,
                "legacy_shadow_observation": legacy_observation,
                "reporting_mart_reference": (
                    {
                        "partner_account_id": reporting_row.get("partner_account_id"),
                        "partner_code_id": reporting_row.get("partner_code_id"),
                        "owner_type": reporting_row.get("owner_type"),
                        "owner_source": reporting_row.get("owner_source"),
                        "is_renewal": reporting_row.get("is_renewal"),
                        "is_paid_conversion": reporting_row.get("is_paid_conversion"),
                    }
                    if reporting_row is not None
                    else None
                ),
                "mismatch_codes": all_codes,
                "blocking_mismatch_codes": blocking_codes,
                "tolerated_mismatch_codes": tolerated_codes,
            }
        )

    for order_id in sorted(observations_by_order_id):
        legacy_observation = observations_by_order_id[order_id]
        lane_key = str(legacy_observation.get("lane_key") or "unknown")
        mismatches.append(
            _approve_mismatch(
                mismatch=AttributionShadowMismatch(
                    code="unexpected_legacy_shadow_observation_without_canonical_order",
                    severity="blocking",
                    order_id=order_id,
                    lane_key=lane_key,
                    message="Legacy shadow observation references an order missing from canonical replay inputs.",
                    details={},
                ),
                approved_divergences=approved_divergences,
            )
        )

    lane_divergence_views = _build_lane_divergence_views(
        lane_accumulator=lane_accumulator,
        tolerance_map=tolerance_map,
        approved_divergences=approved_divergences,
        mismatches=mismatches,
    )

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
            "orders": len(orders),
            "legacy_shadow_observations": len(legacy_shadow_observations),
            "approved_divergences": len(approved_divergences),
            "lane_tolerances": len(lane_tolerances),
        },
        "phase3_reference": {
            "status": phase3_status,
            "comparison": phase3_report.get("comparison", {}),
        },
        "analytical_reference": {
            "status": analytical_status,
            "reconciliation": analytical_report.get("reconciliation", {}),
            "order_reporting_mart_count": len(analytical_report.get("order_reporting_mart", [])),
        },
        "shadow_order_views": shadow_order_views,
        "lane_divergence_views": lane_divergence_views,
        "pilot_promotion_gate": {
            "status": status,
            "blocking_lanes": sorted(
                {
                    item["lane_key"]
                    for item in lane_divergence_views
                    if not item.get("within_tolerance", False) or item.get("blocking_orders", 0) > 0
                }
            ),
            "tolerated_lanes": sorted(
                {item["lane_key"] for item in lane_divergence_views if item.get("tolerated_orders", 0) > 0}
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


def _compare_shadow_order(
    *,
    order_id: str,
    lane_key: str,
    canonical_reference: dict[str, Any],
    persisted_result: dict[str, Any],
    canonical_binding: dict[str, Any] | None,
    renewal_summary: dict[str, Any],
    legacy_observation: dict[str, Any] | None,
    reporting_row: dict[str, Any] | None,
    approved_divergences: list[dict[str, Any]],
) -> list[AttributionShadowMismatch]:
    mismatches: list[AttributionShadowMismatch] = []

    if legacy_observation is None:
        return [
            _approve_mismatch(
                mismatch=AttributionShadowMismatch(
                    code="missing_legacy_shadow_observation",
                    severity="blocking",
                    order_id=order_id,
                    lane_key=lane_key,
                    message="Canonical order is missing a legacy/reference shadow observation.",
                    details={},
                ),
                approved_divergences=approved_divergences,
            )
        ]

    canonical_owner_type = str(canonical_reference.get("owner_type") or "none")
    legacy_owner_type = str(legacy_observation.get("legacy_owner_type") or "none")
    canonical_owner_source = _string_or_none(canonical_reference.get("owner_source"))
    legacy_owner_source = _string_or_none(legacy_observation.get("legacy_owner_source"))
    canonical_partner_account_id = _string_or_none(canonical_reference.get("partner_account_id"))
    legacy_partner_account_id = _string_or_none(legacy_observation.get("legacy_partner_account_id"))
    canonical_partner_code_id = _string_or_none(canonical_reference.get("partner_code_id"))
    legacy_partner_code_id = _string_or_none(legacy_observation.get("legacy_partner_code_id"))

    if legacy_owner_type != canonical_owner_type:
        mismatches.append(
            AttributionShadowMismatch(
                code="legacy_owner_type_mismatch",
                severity="blocking",
                order_id=order_id,
                lane_key=lane_key,
                message="Legacy/reference owner type differs from canonical attribution replay.",
                details={
                    "legacy_owner_type": legacy_owner_type,
                    "canonical_owner_type": canonical_owner_type,
                },
            )
        )
    if legacy_owner_source != canonical_owner_source:
        mismatches.append(
            AttributionShadowMismatch(
                code="legacy_owner_source_mismatch",
                severity="blocking",
                order_id=order_id,
                lane_key=lane_key,
                message="Legacy/reference owner source differs from canonical attribution replay.",
                details={
                    "legacy_owner_source": legacy_owner_source,
                    "canonical_owner_source": canonical_owner_source,
                },
            )
        )
    if legacy_partner_account_id != canonical_partner_account_id:
        mismatches.append(
            AttributionShadowMismatch(
                code="legacy_partner_account_mismatch",
                severity="blocking",
                order_id=order_id,
                lane_key=lane_key,
                message="Legacy/reference partner account differs from canonical attribution replay.",
                details={
                    "legacy_partner_account_id": legacy_partner_account_id,
                    "canonical_partner_account_id": canonical_partner_account_id,
                },
            )
        )
    if legacy_partner_code_id != canonical_partner_code_id:
        mismatches.append(
            AttributionShadowMismatch(
                code="legacy_partner_code_mismatch",
                severity="blocking",
                order_id=order_id,
                lane_key=lane_key,
                message="Legacy/reference partner code differs from canonical attribution replay.",
                details={
                    "legacy_partner_code_id": legacy_partner_code_id,
                    "canonical_partner_code_id": canonical_partner_code_id,
                },
            )
        )

    canonical_rule_path = [str(item) for item in canonical_reference.get("rule_path") or []]
    legacy_rule_path = [str(item) for item in legacy_observation.get("legacy_rule_path") or []]
    if legacy_rule_path and legacy_rule_path != canonical_rule_path:
        mismatches.append(
            AttributionShadowMismatch(
                code="legacy_rule_path_mismatch",
                severity="warning",
                order_id=order_id,
                lane_key=lane_key,
                message="Legacy/reference explainability rule path differs from canonical replay rule path.",
                details={
                    "legacy_rule_path": legacy_rule_path,
                    "canonical_rule_path": canonical_rule_path,
                },
            )
        )

    mismatches.extend(
        _compare_binding_shadow(
            order_id=order_id,
            lane_key=lane_key,
            canonical_binding=canonical_binding,
            legacy_observation=legacy_observation,
        )
    )
    mismatches.extend(
        _compare_renewal_shadow(
            order_id=order_id,
            lane_key=lane_key,
            renewal_summary=renewal_summary,
            legacy_observation=legacy_observation,
        )
    )
    mismatches.extend(
        _compare_reporting_reference(
            order_id=order_id,
            lane_key=lane_key,
            canonical_reference=canonical_reference,
            persisted_result=persisted_result,
            reporting_row=reporting_row,
        )
    )

    return [_approve_mismatch(mismatch=item, approved_divergences=approved_divergences) for item in mismatches]


def _compare_binding_shadow(
    *,
    order_id: str,
    lane_key: str,
    canonical_binding: dict[str, Any] | None,
    legacy_observation: dict[str, Any],
) -> list[AttributionShadowMismatch]:
    mismatches: list[AttributionShadowMismatch] = []
    legacy_binding_type = _string_or_none(legacy_observation.get("legacy_binding_type"))
    legacy_binding_partner_account_id = _string_or_none(legacy_observation.get("legacy_binding_partner_account_id"))
    legacy_binding_partner_code_id = _string_or_none(legacy_observation.get("legacy_binding_partner_code_id"))

    legacy_has_binding = any(
        value is not None
        for value in (
            legacy_binding_type,
            legacy_binding_partner_account_id,
            legacy_binding_partner_code_id,
        )
    )
    if canonical_binding is None and legacy_has_binding:
        return [
            AttributionShadowMismatch(
                code="legacy_binding_reference_unexpected",
                severity="blocking",
                order_id=order_id,
                lane_key=lane_key,
                message=(
                    "Legacy/reference shadow includes binding context, but canonical "
                    "replay selected no winning binding."
                ),
                details={},
            )
        ]
    if canonical_binding is not None and not legacy_has_binding:
        return [
            AttributionShadowMismatch(
                code="legacy_binding_reference_missing",
                severity="blocking",
                order_id=order_id,
                lane_key=lane_key,
                message=(
                    "Canonical replay selected a winning binding, but "
                    "legacy/reference shadow omitted binding context."
                ),
                details={"canonical_binding_id": canonical_binding.get("id")},
            )
        ]
    if canonical_binding is None:
        return []

    canonical_binding_type = _string_or_none(canonical_binding.get("binding_type"))
    canonical_partner_account_id = _string_or_none(canonical_binding.get("partner_account_id"))
    canonical_partner_code_id = _string_or_none(canonical_binding.get("partner_code_id"))
    if legacy_binding_type != canonical_binding_type:
        mismatches.append(
            AttributionShadowMismatch(
                code="legacy_binding_type_mismatch",
                severity="blocking",
                order_id=order_id,
                lane_key=lane_key,
                message="Legacy/reference binding type differs from canonical winning binding.",
                details={
                    "legacy_binding_type": legacy_binding_type,
                    "canonical_binding_type": canonical_binding_type,
                },
            )
        )
    if legacy_binding_partner_account_id != canonical_partner_account_id:
        mismatches.append(
            AttributionShadowMismatch(
                code="legacy_binding_partner_account_mismatch",
                severity="blocking",
                order_id=order_id,
                lane_key=lane_key,
                message="Legacy/reference binding partner account differs from canonical winning binding.",
                details={
                    "legacy_binding_partner_account_id": legacy_binding_partner_account_id,
                    "canonical_binding_partner_account_id": canonical_partner_account_id,
                },
            )
        )
    if legacy_binding_partner_code_id != canonical_partner_code_id:
        mismatches.append(
            AttributionShadowMismatch(
                code="legacy_binding_partner_code_mismatch",
                severity="blocking",
                order_id=order_id,
                lane_key=lane_key,
                message="Legacy/reference binding partner code differs from canonical winning binding.",
                details={
                    "legacy_binding_partner_code_id": legacy_binding_partner_code_id,
                    "canonical_binding_partner_code_id": canonical_partner_code_id,
                },
            )
        )
    return mismatches


def _compare_renewal_shadow(
    *,
    order_id: str,
    lane_key: str,
    renewal_summary: dict[str, Any],
    legacy_observation: dict[str, Any],
) -> list[AttributionShadowMismatch]:
    mismatches: list[AttributionShadowMismatch] = []
    legacy_renewal_owner_type = _string_or_none(legacy_observation.get("legacy_renewal_effective_owner_type"))
    legacy_renewal_owner_source = _string_or_none(legacy_observation.get("legacy_renewal_effective_owner_source"))
    legacy_renewal_partner_account_id = _string_or_none(legacy_observation.get("legacy_renewal_partner_account_id"))
    legacy_renewal_partner_code_id = _string_or_none(legacy_observation.get("legacy_renewal_partner_code_id"))
    legacy_has_renewal = any(
        value is not None
        for value in (
            legacy_renewal_owner_type,
            legacy_renewal_owner_source,
            legacy_renewal_partner_account_id,
            legacy_renewal_partner_code_id,
        )
    )
    canonical_has_renewal = bool(renewal_summary)
    if canonical_has_renewal and not legacy_has_renewal:
        return [
            AttributionShadowMismatch(
                code="legacy_renewal_reference_missing",
                severity="blocking",
                order_id=order_id,
                lane_key=lane_key,
                message=(
                    "Canonical replay includes renewal ownership, but legacy/"
                    "reference shadow omitted renewal ownership context."
                ),
                details={},
            )
        ]
    if not canonical_has_renewal and legacy_has_renewal:
        return [
            AttributionShadowMismatch(
                code="legacy_renewal_reference_unexpected",
                severity="blocking",
                order_id=order_id,
                lane_key=lane_key,
                message=(
                    "Legacy/reference shadow includes renewal ownership for an "
                    "order without canonical renewal lineage."
                ),
                details={},
            )
        ]
    if not canonical_has_renewal:
        return []

    canonical_owner_type = _string_or_none(renewal_summary.get("effective_owner_type"))
    canonical_owner_source = _string_or_none(renewal_summary.get("effective_owner_source"))
    canonical_partner_account_id = _string_or_none(renewal_summary.get("effective_partner_account_id"))
    canonical_partner_code_id = _string_or_none(renewal_summary.get("effective_partner_code_id"))

    if legacy_renewal_owner_type != canonical_owner_type:
        mismatches.append(
            AttributionShadowMismatch(
                code="legacy_renewal_owner_type_mismatch",
                severity="blocking",
                order_id=order_id,
                lane_key=lane_key,
                message="Legacy/reference renewal owner type differs from canonical renewal ownership.",
                details={
                    "legacy_renewal_effective_owner_type": legacy_renewal_owner_type,
                    "canonical_renewal_effective_owner_type": canonical_owner_type,
                },
            )
        )
    if legacy_renewal_owner_source != canonical_owner_source:
        mismatches.append(
            AttributionShadowMismatch(
                code="legacy_renewal_owner_source_mismatch",
                severity="blocking",
                order_id=order_id,
                lane_key=lane_key,
                message="Legacy/reference renewal owner source differs from canonical renewal ownership.",
                details={
                    "legacy_renewal_effective_owner_source": legacy_renewal_owner_source,
                    "canonical_renewal_effective_owner_source": canonical_owner_source,
                },
            )
        )
    if legacy_renewal_partner_account_id != canonical_partner_account_id:
        mismatches.append(
            AttributionShadowMismatch(
                code="legacy_renewal_partner_account_mismatch",
                severity="blocking",
                order_id=order_id,
                lane_key=lane_key,
                message="Legacy/reference renewal partner account differs from canonical renewal ownership.",
                details={
                    "legacy_renewal_partner_account_id": legacy_renewal_partner_account_id,
                    "canonical_renewal_partner_account_id": canonical_partner_account_id,
                },
            )
        )
    if legacy_renewal_partner_code_id != canonical_partner_code_id:
        mismatches.append(
            AttributionShadowMismatch(
                code="legacy_renewal_partner_code_mismatch",
                severity="blocking",
                order_id=order_id,
                lane_key=lane_key,
                message="Legacy/reference renewal partner code differs from canonical renewal ownership.",
                details={
                    "legacy_renewal_partner_code_id": legacy_renewal_partner_code_id,
                    "canonical_renewal_partner_code_id": canonical_partner_code_id,
                },
            )
        )
    return mismatches


def _compare_reporting_reference(
    *,
    order_id: str,
    lane_key: str,
    canonical_reference: dict[str, Any],
    persisted_result: dict[str, Any],
    reporting_row: dict[str, Any] | None,
) -> list[AttributionShadowMismatch]:
    if reporting_row is None:
        return [
            AttributionShadowMismatch(
                code="canonical_shadow_order_missing_from_reporting_mart",
                severity="blocking",
                order_id=order_id,
                lane_key=lane_key,
                message="Canonical shadow order is missing from the Phase 7 order reporting mart reference.",
                details={},
            )
        ]

    canonical_owner_type = str(canonical_reference.get("owner_type") or persisted_result.get("owner_type") or "none")
    canonical_owner_source = _string_or_none(
        canonical_reference.get("owner_source") or persisted_result.get("owner_source")
    )
    canonical_partner_account_id = _string_or_none(
        canonical_reference.get("partner_account_id") or persisted_result.get("partner_account_id")
    )

    mismatches: list[AttributionShadowMismatch] = []
    if str(reporting_row.get("owner_type") or "none") != canonical_owner_type:
        mismatches.append(
            AttributionShadowMismatch(
                code="reporting_mart_owner_type_mismatch",
                severity="blocking",
                order_id=order_id,
                lane_key=lane_key,
                message="Phase 7 reporting mart owner type differs from canonical attribution shadow reference.",
                details={
                    "reporting_owner_type": reporting_row.get("owner_type"),
                    "canonical_owner_type": canonical_owner_type,
                },
            )
        )
    if _string_or_none(reporting_row.get("owner_source")) != canonical_owner_source:
        mismatches.append(
            AttributionShadowMismatch(
                code="reporting_mart_owner_source_mismatch",
                severity="blocking",
                order_id=order_id,
                lane_key=lane_key,
                message="Phase 7 reporting mart owner source differs from canonical attribution shadow reference.",
                details={
                    "reporting_owner_source": reporting_row.get("owner_source"),
                    "canonical_owner_source": canonical_owner_source,
                },
            )
        )
    if _string_or_none(reporting_row.get("partner_account_id")) != canonical_partner_account_id:
        mismatches.append(
            AttributionShadowMismatch(
                code="reporting_mart_partner_account_mismatch",
                severity="blocking",
                order_id=order_id,
                lane_key=lane_key,
                message="Phase 7 reporting mart partner account differs from canonical attribution shadow reference.",
                details={
                    "reporting_partner_account_id": reporting_row.get("partner_account_id"),
                    "canonical_partner_account_id": canonical_partner_account_id,
                },
            )
        )
    return mismatches


def _build_lane_divergence_views(
    *,
    lane_accumulator: dict[str, dict[str, Any]],
    tolerance_map: dict[str, Decimal],
    approved_divergences: list[dict[str, Any]],
    mismatches: list[AttributionShadowMismatch],
) -> list[dict[str, Any]]:
    mismatch_codes_by_lane: dict[str, list[str]] = defaultdict(list)
    for mismatch in mismatches:
        if mismatch.lane_key:
            mismatch_codes_by_lane[mismatch.lane_key].append(mismatch.code)

    lane_views: list[dict[str, Any]] = []
    for lane_key in sorted(lane_accumulator):
        accumulator = lane_accumulator[lane_key]
        total_orders = int(accumulator["total_orders"])
        divergent_orders = int(accumulator["divergent_orders"])
        blocking_orders = int(accumulator["blocking_orders"])
        tolerated_orders = int(accumulator["tolerated_orders"])
        divergence_rate = (
            (Decimal(divergent_orders) / Decimal(total_orders)).quantize(Decimal("0.0001"))
            if total_orders
            else Decimal("0.0000")
        )
        max_divergence_rate = tolerance_map.get(lane_key)
        if max_divergence_rate is None:
            mismatch = _approve_mismatch(
                mismatch=AttributionShadowMismatch(
                    code="lane_divergence_tolerance_missing",
                    severity="blocking",
                    order_id=None,
                    lane_key=lane_key,
                    message="Lane-specific divergence tolerance is missing for pilot promotion evaluation.",
                    details={},
                ),
                approved_divergences=approved_divergences,
            )
            mismatches.append(mismatch)
            mismatch_codes_by_lane[lane_key].append(mismatch.code)
            max_divergence_rate = DEFAULT_LANE_TOLERANCE

        within_tolerance = divergence_rate <= max_divergence_rate
        if not within_tolerance:
            mismatch = _approve_mismatch(
                mismatch=AttributionShadowMismatch(
                    code="lane_divergence_rate_exceeded",
                    severity="blocking",
                    order_id=None,
                    lane_key=lane_key,
                    message="Observed attribution divergence rate exceeds the approved pilot threshold for this lane.",
                    details={
                        "divergence_rate": str(divergence_rate),
                        "max_divergence_rate": str(max_divergence_rate),
                    },
                ),
                approved_divergences=approved_divergences,
            )
            mismatches.append(mismatch)
            mismatch_codes_by_lane[lane_key].append(mismatch.code)

        lane_views.append(
            {
                "lane_key": lane_key,
                "order_ids": sorted(accumulator["order_ids"]),
                "total_orders": total_orders,
                "divergent_orders": divergent_orders,
                "blocking_orders": blocking_orders,
                "tolerated_orders": tolerated_orders,
                "divergence_rate": str(divergence_rate),
                "max_divergence_rate": str(max_divergence_rate),
                "within_tolerance": within_tolerance,
                "mismatch_codes": sorted(set(mismatch_codes_by_lane[lane_key])),
            }
        )
    return lane_views


def _approve_mismatch(
    *,
    mismatch: AttributionShadowMismatch,
    approved_divergences: list[dict[str, Any]],
) -> AttributionShadowMismatch:
    approval_reference = _match_approved_divergence(
        code=mismatch.code,
        order_id=mismatch.order_id,
        lane_key=mismatch.lane_key,
        approved_divergences=approved_divergences,
    )
    if approval_reference is None or mismatch.code in _WARNING_ONLY_CODES:
        return mismatch
    return AttributionShadowMismatch(
        code=mismatch.code,
        severity="warning",
        order_id=mismatch.order_id,
        lane_key=mismatch.lane_key,
        message=mismatch.message,
        details=mismatch.details,
        approved=True,
        approval_reference=approval_reference,
    )


def _match_approved_divergence(
    *,
    code: str,
    order_id: str | None,
    lane_key: str | None,
    approved_divergences: list[dict[str, Any]],
) -> str | None:
    for item in approved_divergences:
        if str(item.get("code") or "") != code:
            continue
        approved_order_id = _string_or_none(item.get("order_id"))
        approved_lane_key = _string_or_none(item.get("lane_key"))
        if approved_order_id not in {None, order_id}:
            continue
        if approved_lane_key not in {None, lane_key}:
            continue
        return str(item.get("approval_reference") or item.get("id") or code)
    return None


def _build_lane_tolerance_map(
    *,
    lane_tolerances: list[dict[str, Any]],
    metadata: dict[str, Any],
) -> dict[str, Decimal]:
    tolerance_map: dict[str, Decimal] = {}
    default_tolerance = _decimal_or_none(metadata.get("default_max_divergence_rate"))
    if default_tolerance is not None:
        for lane_key in PRIMARY_LANE_PRECEDENCE:
            tolerance_map[lane_key] = default_tolerance
        tolerance_map["direct_store"] = default_tolerance

    for item in lane_tolerances:
        lane_key = _string_or_none(item.get("lane_key"))
        max_divergence_rate = _decimal_or_none(item.get("max_divergence_rate"))
        if lane_key is None or max_divergence_rate is None:
            continue
        tolerance_map[lane_key] = max_divergence_rate
    return tolerance_map


def _resolve_canonical_binding(
    *,
    order_case: dict[str, Any],
    bindings_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    reference_attribution = dict(order_case.get("reference_attribution_result") or {})
    binding_id = _string_or_none(reference_attribution.get("winning_binding_id"))
    if binding_id is None:
        return None
    binding = bindings_by_id.get(binding_id)
    if binding is None:
        return {
            "id": binding_id,
            "binding_type": None,
            "partner_account_id": None,
            "partner_code_id": None,
        }
    return {
        "id": binding_id,
        "binding_type": binding.get("binding_type"),
        "partner_account_id": binding.get("partner_account_id"),
        "partner_code_id": binding.get("partner_code_id"),
    }


def _resolve_primary_lane(lane_views: dict[str, Any]) -> str:
    for lane_key in PRIMARY_LANE_PRECEDENCE:
        lane_view = dict(lane_views.get(lane_key) or {})
        if bool(lane_view.get("active")):
            return lane_key
    return "direct_store"


def _sorted_rows(rows: Any) -> list[dict[str, Any]]:
    materialized = [dict(item) for item in rows or []]
    return sorted(
        materialized,
        key=lambda item: (
            str(item.get("lane_key") or ""),
            str(item.get("order_id") or item.get("id") or ""),
            str(item.get("approval_reference") or ""),
        ),
    )


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    string_value = str(value).strip()
    return string_value or None


def _decimal_or_none(value: Any) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))
