"""Phase 3 attribution/growth explainability replay helpers."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

REPORT_VERSION = "phase3-explainability-replay-v1"

BLOCKING_MISMATCH_CODES = {
    "missing_attribution_result",
    "unexpected_attribution_result_without_reference_owner",
    "owner_type_mismatch",
    "owner_source_mismatch",
    "partner_code_mismatch",
    "partner_account_mismatch",
}


@dataclass(frozen=True)
class ExplainabilityMismatch:
    code: str
    severity: str
    order_id: str
    message: str
    details: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "order_id": self.order_id,
            "message": self.message,
            "details": self.details,
        }


@dataclass(frozen=True)
class _SnapshotCandidate:
    owner_type: str
    owner_source: str | None
    partner_account_id: str | None
    partner_code_id: str | None
    winning_touchpoint_id: str | None
    winning_binding_id: str | None
    rule_path: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "owner_type": self.owner_type,
            "owner_source": self.owner_source,
            "partner_account_id": self.partner_account_id,
            "partner_code_id": self.partner_code_id,
            "winning_touchpoint_id": self.winning_touchpoint_id,
            "winning_binding_id": self.winning_binding_id,
            "rule_path": list(self.rule_path),
        }


def build_phase3_explainability_replay_pack(snapshot: dict[str, Any]) -> dict[str, Any]:
    metadata = dict(snapshot.get("metadata") or {})
    orders = sorted((dict(item) for item in snapshot.get("orders", [])), key=lambda item: str(item.get("id", "")))
    partner_codes = {
        str(item["id"]): dict(item)
        for item in snapshot.get("partner_codes", [])
        if item.get("id") is not None
    }
    touchpoints_by_order: dict[str, list[dict[str, Any]]] = defaultdict(list)
    bindings_by_user: dict[str, list[dict[str, Any]]] = defaultdict(list)
    attribution_results_by_order = {
        str(item["order_id"]): dict(item)
        for item in snapshot.get("attribution_results", [])
        if item.get("order_id") is not None
    }
    growth_rewards_by_order: dict[str, list[dict[str, Any]]] = defaultdict(list)
    renewal_orders_by_order = {
        str(item["order_id"]): dict(item)
        for item in snapshot.get("renewal_orders", [])
        if item.get("order_id") is not None
    }

    for touchpoint in snapshot.get("touchpoints", []):
        order_id = _string_or_none(touchpoint.get("order_id"))
        if order_id is not None:
            touchpoints_by_order[order_id].append(dict(touchpoint))

    for binding in snapshot.get("bindings", []):
        user_id = _string_or_none(binding.get("user_id"))
        if user_id is not None:
            bindings_by_user[user_id].append(dict(binding))

    for allocation in snapshot.get("growth_reward_allocations", []):
        order_id = _string_or_none(allocation.get("order_id"))
        if order_id is not None:
            growth_rewards_by_order[order_id].append(dict(allocation))

    mismatches: list[ExplainabilityMismatch] = []
    order_cases: list[dict[str, Any]] = []

    for order in orders:
        order_id = str(order["id"])
        user_id = _string_or_none(order.get("user_id"))
        storefront_id = _string_or_none(order.get("storefront_id"))
        order_touchpoints = sorted(touchpoints_by_order.get(order_id, []), key=_touchpoint_sort_key)
        order_bindings = _filter_bindings_for_scope(
            bindings=bindings_by_user.get(user_id or "", []),
            storefront_id=storefront_id,
        )
        reference_candidate = _resolve_reference_candidate(
            order_touchpoints=order_touchpoints,
            order_bindings=order_bindings,
            partner_codes=partner_codes,
        )
        persisted_result = attribution_results_by_order.get(order_id)
        order_mismatches = _compare_reference_and_persisted(
            order_id=order_id,
            reference_candidate=reference_candidate,
            persisted_result=persisted_result,
        )
        mismatches.extend(order_mismatches)

        growth_allocations = sorted(
            growth_rewards_by_order.get(order_id, []),
            key=lambda item: (
                _normalize_timestamp(item.get("allocated_at") or item.get("created_at")),
                str(item.get("id", "")),
            ),
        )
        renewal_order = renewal_orders_by_order.get(order_id)
        lane_views = _build_lane_views(
            reference_candidate=reference_candidate,
            growth_allocations=growth_allocations,
            renewal_order=renewal_order,
        )

        order_cases.append(
            {
                "order_id": order_id,
                "user_id": user_id,
                "storefront_id": storefront_id,
                "persisted_attribution_result": _persisted_result_summary(persisted_result),
                "reference_attribution_result": reference_candidate.to_dict() if reference_candidate else None,
                "growth_reward_summary": {
                    "allocation_count": len(growth_allocations),
                    "reward_types": sorted(
                        {str(item.get("reward_type")) for item in growth_allocations if item.get("reward_type")}
                    ),
                    "allocation_ids": [str(item["id"]) for item in growth_allocations if item.get("id") is not None],
                },
                "renewal_summary": (
                    {
                        "renewal_mode": renewal_order.get("renewal_mode"),
                        "renewal_sequence_number": renewal_order.get("renewal_sequence_number"),
                        "effective_owner_type": renewal_order.get("effective_owner_type"),
                        "effective_owner_source": renewal_order.get("effective_owner_source"),
                        "effective_partner_account_id": renewal_order.get("effective_partner_account_id"),
                        "effective_partner_code_id": renewal_order.get("effective_partner_code_id"),
                        "payout_eligible": bool(renewal_order.get("payout_eligible")),
                    }
                    if renewal_order is not None
                    else None
                ),
                "lane_views": lane_views,
                "winner_matches": not order_mismatches,
                "mismatch_codes": [item.code for item in order_mismatches],
            }
        )

    mismatch_counts = dict(Counter(item.code for item in mismatches))
    blocking_mismatches = [item.to_dict() for item in mismatches if item.code in BLOCKING_MISMATCH_CODES]
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
            "touchpoints": sum(len(items) for items in touchpoints_by_order.values()),
            "bindings": sum(len(items) for items in bindings_by_user.values()),
            "attribution_results": len(attribution_results_by_order),
            "growth_reward_allocations": sum(len(items) for items in growth_rewards_by_order.values()),
            "renewal_orders": len(renewal_orders_by_order),
        },
        "order_cases": order_cases,
        "comparison": {
            "status": status,
            "mismatch_counts": mismatch_counts,
            "mismatches": [item.to_dict() for item in mismatches],
            "blocking_mismatches": blocking_mismatches,
        },
    }


def _filter_bindings_for_scope(*, bindings: list[dict[str, Any]], storefront_id: str | None) -> list[dict[str, Any]]:
    filtered = []
    for binding in bindings:
        if str(binding.get("binding_status", "active")) != "active":
            continue
        binding_storefront_id = _string_or_none(binding.get("storefront_id"))
        if storefront_id is None:
            if binding_storefront_id is None:
                filtered.append(binding)
        elif binding_storefront_id in {None, storefront_id}:
            filtered.append(binding)
    return sorted(filtered, key=_binding_sort_key)


def _resolve_reference_candidate(
    *,
    order_touchpoints: list[dict[str, Any]],
    order_bindings: list[dict[str, Any]],
    partner_codes: dict[str, dict[str, Any]],
) -> _SnapshotCandidate | None:
    binding_by_type = _binding_by_type(order_bindings)
    explicit_touchpoint = _latest_touchpoint(order_touchpoints, "explicit_code")
    passive_click = _latest_touchpoint(order_touchpoints, "passive_click")

    if binding_by_type.get("manual_override") is not None:
        return _candidate_from_binding(
            binding_by_type["manual_override"],
            owner_source="manual_override",
            rule_path=["manual_override_binding_selected"],
        )
    if binding_by_type.get("contract_assignment") is not None:
        return _candidate_from_binding(
            binding_by_type["contract_assignment"],
            owner_source="contract_assignment",
            rule_path=["contract_assignment_binding_selected"],
        )
    if explicit_touchpoint is not None:
        return _candidate_from_touchpoint(
            explicit_touchpoint,
            owner_source="explicit_code",
            partner_codes=partner_codes,
            rule_path=["explicit_code_touchpoint_selected"],
        )
    if binding_by_type.get("reseller_binding") is not None:
        return _candidate_from_binding(
            binding_by_type["reseller_binding"],
            owner_source="persistent_reseller_binding",
            rule_path=["persistent_reseller_binding_selected"],
        )
    if passive_click is not None:
        return _candidate_from_touchpoint(
            passive_click,
            owner_source="passive_click",
            partner_codes=partner_codes,
            rule_path=["passive_click_touchpoint_selected"],
        )
    if binding_by_type.get("storefront_default_owner") is not None:
        return _candidate_from_binding(
            binding_by_type["storefront_default_owner"],
            owner_source="storefront_default",
            rule_path=["storefront_default_binding_selected"],
        )
    return None


def _binding_by_type(bindings: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    selected: dict[str, dict[str, Any]] = {}
    for binding in bindings:
        binding_type = str(binding.get("binding_type", ""))
        selected.setdefault(binding_type, binding)
    return selected


def _latest_touchpoint(touchpoints: list[dict[str, Any]], touchpoint_type: str) -> dict[str, Any] | None:
    matching = [item for item in touchpoints if str(item.get("touchpoint_type")) == touchpoint_type]
    if not matching:
        return None
    return sorted(matching, key=_touchpoint_sort_key)[-1]


def _candidate_from_binding(
    binding: dict[str, Any],
    *,
    owner_source: str,
    rule_path: list[str],
) -> _SnapshotCandidate:
    return _SnapshotCandidate(
        owner_type=str(binding.get("owner_type", "none")),
        owner_source=owner_source,
        partner_account_id=_string_or_none(binding.get("partner_account_id")),
        partner_code_id=_string_or_none(binding.get("partner_code_id")),
        winning_touchpoint_id=None,
        winning_binding_id=_string_or_none(binding.get("id")),
        rule_path=rule_path,
    )


def _candidate_from_touchpoint(
    touchpoint: dict[str, Any],
    *,
    owner_source: str,
    partner_codes: dict[str, dict[str, Any]],
    rule_path: list[str],
) -> _SnapshotCandidate:
    partner_code_id = _string_or_none(touchpoint.get("partner_code_id"))
    partner_code = partner_codes.get(partner_code_id or "")
    partner_account_id = _string_or_none(partner_code.get("partner_account_id")) if partner_code else None
    owner_type = "reseller" if partner_account_id is not None else "affiliate"
    resolved_rule_path = list(rule_path)
    resolved_rule_path.append(
        "owner_type_inferred_from_partner_account" if owner_type == "reseller" else "owner_type_inferred_as_affiliate"
    )
    return _SnapshotCandidate(
        owner_type=owner_type,
        owner_source=owner_source,
        partner_account_id=partner_account_id,
        partner_code_id=partner_code_id,
        winning_touchpoint_id=_string_or_none(touchpoint.get("id")),
        winning_binding_id=None,
        rule_path=resolved_rule_path,
    )


def _compare_reference_and_persisted(
    *,
    order_id: str,
    reference_candidate: _SnapshotCandidate | None,
    persisted_result: dict[str, Any] | None,
) -> list[ExplainabilityMismatch]:
    mismatches: list[ExplainabilityMismatch] = []
    if reference_candidate is not None and persisted_result is None:
        mismatches.append(
            ExplainabilityMismatch(
                code="missing_attribution_result",
                severity="blocking",
                order_id=order_id,
                message="Reference resolution found a winner but persisted attribution result is missing.",
                details={"reference_candidate": reference_candidate.to_dict()},
            )
        )
        return mismatches

    if reference_candidate is None and persisted_result is not None and persisted_result.get("owner_type") != "none":
        mismatches.append(
            ExplainabilityMismatch(
                code="unexpected_attribution_result_without_reference_owner",
                severity="blocking",
                order_id=order_id,
                message="Persisted attribution result exists but replay reference logic did not resolve a winner.",
                details={"persisted_result": _persisted_result_summary(persisted_result)},
            )
        )
        return mismatches

    if reference_candidate is None or persisted_result is None:
        return mismatches

    if str(persisted_result.get("owner_type")) != reference_candidate.owner_type:
        mismatches.append(
            ExplainabilityMismatch(
                code="owner_type_mismatch",
                severity="blocking",
                order_id=order_id,
                message="Persisted owner type differs from replay reference owner type.",
                details={
                    "persisted_owner_type": persisted_result.get("owner_type"),
                    "reference_owner_type": reference_candidate.owner_type,
                },
            )
        )
    if _string_or_none(persisted_result.get("owner_source")) != reference_candidate.owner_source:
        mismatches.append(
            ExplainabilityMismatch(
                code="owner_source_mismatch",
                severity="blocking",
                order_id=order_id,
                message="Persisted owner source differs from replay reference owner source.",
                details={
                    "persisted_owner_source": persisted_result.get("owner_source"),
                    "reference_owner_source": reference_candidate.owner_source,
                },
            )
        )
    if _string_or_none(persisted_result.get("partner_code_id")) != reference_candidate.partner_code_id:
        mismatches.append(
            ExplainabilityMismatch(
                code="partner_code_mismatch",
                severity="blocking",
                order_id=order_id,
                message="Persisted partner code differs from replay reference partner code.",
                details={
                    "persisted_partner_code_id": _string_or_none(persisted_result.get("partner_code_id")),
                    "reference_partner_code_id": reference_candidate.partner_code_id,
                },
            )
        )
    if _string_or_none(persisted_result.get("partner_account_id")) != reference_candidate.partner_account_id:
        mismatches.append(
            ExplainabilityMismatch(
                code="partner_account_mismatch",
                severity="blocking",
                order_id=order_id,
                message="Persisted partner account differs from replay reference partner account.",
                details={
                    "persisted_partner_account_id": _string_or_none(persisted_result.get("partner_account_id")),
                    "reference_partner_account_id": reference_candidate.partner_account_id,
                },
            )
        )
    return mismatches


def _build_lane_views(
    *,
    reference_candidate: _SnapshotCandidate | None,
    growth_allocations: list[dict[str, Any]],
    renewal_order: dict[str, Any] | None,
) -> dict[str, Any]:
    active_growth_reward_types = sorted(
        {
            str(item.get("reward_type"))
            for item in growth_allocations
            if str(item.get("allocation_status", "allocated")) == "allocated" and item.get("reward_type")
        }
    )
    resolved_owner_type = (
        str(renewal_order.get("effective_owner_type"))
        if renewal_order is not None and renewal_order.get("effective_owner_type") is not None
        else reference_candidate.owner_type
        if reference_candidate is not None
        else "none"
    )
    resolved_owner_source = (
        str(renewal_order.get("effective_owner_source"))
        if renewal_order is not None and renewal_order.get("effective_owner_source") is not None
        else reference_candidate.owner_source
        if reference_candidate is not None
        else None
    )

    return {
        "invite_gift": {
            "active": any(item in {"invite_reward", "gift_bonus", "bonus_days"} for item in active_growth_reward_types),
            "reward_types": [
                item for item in active_growth_reward_types if item in {"invite_reward", "gift_bonus", "bonus_days"}
            ],
        },
        "consumer_referral": {
            "active": "referral_credit" in active_growth_reward_types,
            "reward_types": [item for item in active_growth_reward_types if item == "referral_credit"],
        },
        "creator_affiliate": {
            "active": resolved_owner_type == "affiliate",
            "owner_type": resolved_owner_type,
            "owner_source": resolved_owner_source,
        },
        "performance_media_buyer": {
            "active": resolved_owner_type == "performance",
            "owner_type": resolved_owner_type,
            "owner_source": resolved_owner_source,
        },
        "reseller_distribution": {
            "active": resolved_owner_type == "reseller",
            "owner_type": resolved_owner_type,
            "owner_source": resolved_owner_source,
        },
        "renewal_chain": {
            "active": renewal_order is not None,
            "renewal_sequence_number": renewal_order.get("renewal_sequence_number") if renewal_order else None,
            "payout_eligible": bool(renewal_order.get("payout_eligible")) if renewal_order else False,
        },
    }


def _persisted_result_summary(result: dict[str, Any] | None) -> dict[str, Any] | None:
    if result is None:
        return None
    return {
        "owner_type": result.get("owner_type"),
        "owner_source": result.get("owner_source"),
        "partner_account_id": _string_or_none(result.get("partner_account_id")),
        "partner_code_id": _string_or_none(result.get("partner_code_id")),
        "winning_touchpoint_id": _string_or_none(result.get("winning_touchpoint_id")),
        "winning_binding_id": _string_or_none(result.get("winning_binding_id")),
    }


def _binding_sort_key(binding: dict[str, Any]) -> tuple[datetime, datetime, str]:
    return (
        _normalize_timestamp(binding.get("effective_from")),
        _normalize_timestamp(binding.get("created_at")),
        str(binding.get("id", "")),
    )


def _touchpoint_sort_key(touchpoint: dict[str, Any]) -> tuple[datetime, datetime, str]:
    return (
        _normalize_timestamp(touchpoint.get("occurred_at")),
        _normalize_timestamp(touchpoint.get("created_at")),
        str(touchpoint.get("id", "")),
    )


def _normalize_timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
    if isinstance(value, str) and value:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)
    return datetime(1970, 1, 1, tzinfo=UTC)


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)
