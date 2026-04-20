"""Phase 4 settlement reconciliation and liability reporting helpers."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

REPORT_VERSION = "phase4-settlement-reconciliation-v1"

BLOCKING_MISMATCH_CODES = {
    "statement_snapshot_missing_event",
    "statement_snapshot_missing_reserve",
    "statement_snapshot_missing_adjustment",
    "statement_totals_mismatch",
    "statement_count_mismatch",
    "payout_instruction_without_closed_statement",
    "payout_instruction_on_superseded_statement",
    "payout_instruction_amount_mismatch",
    "payout_execution_without_instruction",
    "payout_execution_instruction_mismatch",
    "reconciled_execution_without_completed_instruction",
    "completed_instruction_without_live_terminal_execution",
    "paid_amount_exceeds_statement_liability",
}

_TERMINAL_LIVE_EXECUTION_STATUSES = {"succeeded", "reconciled"}


@dataclass(frozen=True)
class SettlementMismatch:
    code: str
    severity: str
    object_family: str
    source_reference: str
    message: str
    details: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "object_family": self.object_family,
            "source_reference": self.source_reference,
            "message": self.message,
            "details": self.details,
        }


def build_phase4_settlement_reconciliation_pack(snapshot: dict[str, Any]) -> dict[str, Any]:
    metadata = dict(snapshot.get("metadata") or {})
    earning_events = _sorted_rows(snapshot.get("earning_events", []))
    earning_holds = _sorted_rows(snapshot.get("earning_holds", []))
    reserves = _sorted_rows(snapshot.get("reserves", []))
    partner_statements = _sorted_rows(snapshot.get("partner_statements", []))
    statement_adjustments = _sorted_rows(snapshot.get("statement_adjustments", []))
    payout_instructions = _sorted_rows(snapshot.get("payout_instructions", []))
    payout_executions = _sorted_rows(snapshot.get("payout_executions", []))

    event_by_id = _rows_by_id(earning_events)
    reserve_by_id = _rows_by_id(reserves)
    adjustment_by_id = _rows_by_id(statement_adjustments)
    statement_by_id = _rows_by_id(partner_statements)
    active_holds_by_event: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for hold in earning_holds:
        if str(hold.get("hold_status")) == "active" and hold.get("earning_event_id") is not None:
            active_holds_by_event[str(hold["earning_event_id"])].append(hold)

    active_reserves_by_event: dict[str, list[dict[str, Any]]] = defaultdict(list)
    active_partner_reserves_by_account: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for reserve in reserves:
        if str(reserve.get("reserve_status")) != "active":
            continue
        if reserve.get("source_earning_event_id") is not None:
            active_reserves_by_event[str(reserve["source_earning_event_id"])].append(reserve)
        if (
            reserve.get("partner_account_id") is not None
            and str(reserve.get("reserve_scope")) == "partner_account"
        ):
            active_partner_reserves_by_account[str(reserve["partner_account_id"])].append(reserve)

    adjustments_by_statement: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for adjustment in statement_adjustments:
        partner_statement_id = _string_or_none(adjustment.get("partner_statement_id"))
        if partner_statement_id is not None:
            adjustments_by_statement[partner_statement_id].append(adjustment)

    executions_by_instruction: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for execution in payout_executions:
        instruction_id = _string_or_none(execution.get("payout_instruction_id"))
        if instruction_id is not None:
            executions_by_instruction[instruction_id].append(execution)

    mismatches: list[SettlementMismatch] = []
    statement_views: list[dict[str, Any]] = []

    for statement in partner_statements:
        statement_views.append(
            _build_statement_view(
                statement=statement,
                event_by_id=event_by_id,
                reserve_by_id=reserve_by_id,
                adjustment_by_id=adjustment_by_id,
                mismatches=mismatches,
            )
        )

    payout_views = _build_payout_views(
        payout_instructions=payout_instructions,
        payout_executions=payout_executions,
        statement_by_id=statement_by_id,
        executions_by_instruction=executions_by_instruction,
        mismatches=mismatches,
    )

    liability_views = _build_liability_views(
        earning_events=earning_events,
        active_holds_by_event=active_holds_by_event,
        active_reserves_by_event=active_reserves_by_event,
        active_partner_reserves_by_account=active_partner_reserves_by_account,
        statement_views=statement_views,
        payout_instructions=payout_instructions,
        payout_executions=payout_executions,
        mismatches=mismatches,
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
            "earning_events": len(earning_events),
            "earning_holds": len(earning_holds),
            "reserves": len(reserves),
            "partner_statements": len(partner_statements),
            "statement_adjustments": len(statement_adjustments),
            "payout_instructions": len(payout_instructions),
            "payout_executions": len(payout_executions),
        },
        "liability_views": liability_views,
        "statement_views": statement_views,
        "payout_views": payout_views,
        "reconciliation": {
            "status": status,
            "mismatch_counts": mismatch_counts,
            "mismatches": [item.to_dict() for item in mismatches],
            "blocking_mismatches": blocking_mismatches,
        },
    }


def _build_statement_view(
    *,
    statement: dict[str, Any],
    event_by_id: dict[str, dict[str, Any]],
    reserve_by_id: dict[str, dict[str, Any]],
    adjustment_by_id: dict[str, dict[str, Any]],
    mismatches: list[SettlementMismatch],
) -> dict[str, Any]:
    statement_id = str(statement["id"])
    snapshot = dict(statement.get("statement_snapshot") or {})
    totals = dict(snapshot.get("totals") or {})
    earning_event_ids = _string_list(snapshot.get("earning_event_ids"))
    held_event_ids = _string_list(snapshot.get("held_event_ids"))
    reserve_ids = _string_list(snapshot.get("reserve_ids"))
    adjustment_ids = _string_list(snapshot.get("adjustment_ids"))

    missing_event_ids = [item for item in earning_event_ids if item not in event_by_id]
    missing_reserve_ids = [item for item in reserve_ids if item not in reserve_by_id]
    missing_adjustment_ids = [item for item in adjustment_ids if item not in adjustment_by_id]
    for missing_event_id in missing_event_ids:
        mismatches.append(
            SettlementMismatch(
                code="statement_snapshot_missing_event",
                severity="blocking",
                object_family="partner_statement",
                source_reference=statement_id,
                message="Statement snapshot references an earning event that is missing from the canonical snapshot.",
                details={"missing_event_id": missing_event_id},
            )
        )
    for missing_reserve_id in missing_reserve_ids:
        mismatches.append(
            SettlementMismatch(
                code="statement_snapshot_missing_reserve",
                severity="blocking",
                object_family="partner_statement",
                source_reference=statement_id,
                message="Statement snapshot references a reserve that is missing from the canonical snapshot.",
                details={"missing_reserve_id": missing_reserve_id},
            )
        )
    for missing_adjustment_id in missing_adjustment_ids:
        mismatches.append(
            SettlementMismatch(
                code="statement_snapshot_missing_adjustment",
                severity="blocking",
                object_family="partner_statement",
                source_reference=statement_id,
                message="Statement snapshot references an adjustment that is missing from the canonical snapshot.",
                details={"missing_adjustment_id": missing_adjustment_id},
            )
        )

    earning_events = [event_by_id[item] for item in earning_event_ids if item in event_by_id]
    reserves = [reserve_by_id[item] for item in reserve_ids if item in reserve_by_id]
    adjustments = [adjustment_by_id[item] for item in adjustment_ids if item in adjustment_by_id]

    recomputed = {
        "accrual_amount": _sum_amount(earning_events, "total_amount"),
        "on_hold_amount": _sum_amount(
            [event_by_id[item] for item in held_event_ids if item in event_by_id],
            "total_amount",
        ),
        "reserve_amount": _sum_amount(reserves, "amount"),
        "adjustment_net_amount": _net_adjustment_amount(adjustments),
    }
    recomputed["available_amount"] = _round_money(
        recomputed["accrual_amount"]
        - recomputed["on_hold_amount"]
        - recomputed["reserve_amount"]
        + recomputed["adjustment_net_amount"]
    )

    count_mismatches: dict[str, dict[str, int]] = {}
    if int(statement.get("source_event_count") or 0) != len(earning_event_ids):
        count_mismatches["source_event_count"] = {
            "statement_value": int(statement.get("source_event_count") or 0),
            "recomputed_value": len(earning_event_ids),
        }
    if int(statement.get("held_event_count") or 0) != len(held_event_ids):
        count_mismatches["held_event_count"] = {
            "statement_value": int(statement.get("held_event_count") or 0),
            "recomputed_value": len(held_event_ids),
        }
    if int(statement.get("active_reserve_count") or 0) != len(reserve_ids):
        count_mismatches["active_reserve_count"] = {
            "statement_value": int(statement.get("active_reserve_count") or 0),
            "recomputed_value": len(reserve_ids),
        }
    if int(statement.get("adjustment_count") or 0) != len(adjustment_ids):
        count_mismatches["adjustment_count"] = {
            "statement_value": int(statement.get("adjustment_count") or 0),
            "recomputed_value": len(adjustment_ids),
        }
    if count_mismatches:
        mismatches.append(
            SettlementMismatch(
                code="statement_count_mismatch",
                severity="blocking",
                object_family="partner_statement",
                source_reference=statement_id,
                message="Statement count columns do not match snapshot-linked object families.",
                details=count_mismatches,
            )
        )

    amount_mismatches: dict[str, dict[str, float]] = {}
    for field_name in (
        "accrual_amount",
        "on_hold_amount",
        "reserve_amount",
        "adjustment_net_amount",
        "available_amount",
    ):
        statement_value = _round_money(statement.get(field_name, 0))
        recomputed_value = recomputed[field_name]
        snapshot_total = _round_money(totals.get(field_name, recomputed_value))
        if statement_value != recomputed_value or snapshot_total != recomputed_value:
            amount_mismatches[field_name] = {
                "statement_value": statement_value,
                "snapshot_value": snapshot_total,
                "recomputed_value": recomputed_value,
            }
    if amount_mismatches:
        mismatches.append(
            SettlementMismatch(
                code="statement_totals_mismatch",
                severity="blocking",
                object_family="partner_statement",
                source_reference=statement_id,
                message="Statement monetary columns or stored totals diverge from linked object families.",
                details=amount_mismatches,
            )
        )

    return {
        "statement_id": statement_id,
        "partner_account_id": _string_or_none(statement.get("partner_account_id")),
        "settlement_period_id": _string_or_none(statement.get("settlement_period_id")),
        "statement_status": statement.get("statement_status"),
        "statement_version": int(statement.get("statement_version") or 0),
        "is_latest_version": statement.get("superseded_by_statement_id") is None,
        "reopened_from_statement_id": _string_or_none(statement.get("reopened_from_statement_id")),
        "superseded_by_statement_id": _string_or_none(statement.get("superseded_by_statement_id")),
        "currency_code": str(statement.get("currency_code") or "USD").upper(),
        "linked_object_ids": {
            "earning_event_ids": earning_event_ids,
            "held_event_ids": held_event_ids,
            "reserve_ids": reserve_ids,
            "adjustment_ids": adjustment_ids,
        },
        "recomputed_totals": recomputed,
        "statement_totals": {
            "accrual_amount": _round_money(statement.get("accrual_amount", 0)),
            "on_hold_amount": _round_money(statement.get("on_hold_amount", 0)),
            "reserve_amount": _round_money(statement.get("reserve_amount", 0)),
            "adjustment_net_amount": _round_money(statement.get("adjustment_net_amount", 0)),
            "available_amount": _round_money(statement.get("available_amount", 0)),
        },
        "count_summary": {
            "source_event_count": int(statement.get("source_event_count") or 0),
            "held_event_count": int(statement.get("held_event_count") or 0),
            "active_reserve_count": int(statement.get("active_reserve_count") or 0),
            "adjustment_count": int(statement.get("adjustment_count") or 0),
        },
        "mismatch_codes": sorted(
            {
                item.code
                for item in mismatches
                if item.object_family == "partner_statement" and item.source_reference == statement_id
            }
        ),
    }


def _build_payout_views(
    *,
    payout_instructions: list[dict[str, Any]],
    payout_executions: list[dict[str, Any]],
    statement_by_id: dict[str, dict[str, Any]],
    executions_by_instruction: dict[str, list[dict[str, Any]]],
    mismatches: list[SettlementMismatch],
) -> list[dict[str, Any]]:
    instruction_by_id = _rows_by_id(payout_instructions)
    execution_by_instruction_id = {
        instruction_id: sorted(items, key=_row_sort_key)
        for instruction_id, items in executions_by_instruction.items()
    }
    payout_views: list[dict[str, Any]] = []

    for instruction in payout_instructions:
        instruction_id = str(instruction["id"])
        statement_id = _string_or_none(instruction.get("partner_statement_id"))
        statement = statement_by_id.get(statement_id or "")
        linked_executions = execution_by_instruction_id.get(instruction_id, [])

        if statement is None or str(statement.get("statement_status")) != "closed":
            mismatches.append(
                SettlementMismatch(
                    code="payout_instruction_without_closed_statement",
                    severity="blocking",
                    object_family="payout_instruction",
                    source_reference=instruction_id,
                    message="Payout instruction must reference an existing closed statement.",
                    details={"partner_statement_id": statement_id},
                )
            )
        else:
            if statement.get("superseded_by_statement_id") is not None:
                mismatches.append(
                    SettlementMismatch(
                        code="payout_instruction_on_superseded_statement",
                        severity="blocking",
                        object_family="payout_instruction",
                        source_reference=instruction_id,
                        message="Payout instruction may not reference a superseded statement version.",
                        details={"partner_statement_id": statement_id},
                    )
                )
            if _round_money(instruction.get("payout_amount", 0)) != _round_money(statement.get("available_amount", 0)):
                mismatches.append(
                    SettlementMismatch(
                        code="payout_instruction_amount_mismatch",
                        severity="blocking",
                        object_family="payout_instruction",
                        source_reference=instruction_id,
                        message="Payout instruction amount diverges from the linked statement available amount.",
                        details={
                            "instruction_amount": _round_money(instruction.get("payout_amount", 0)),
                            "statement_available_amount": _round_money(statement.get("available_amount", 0)),
                            "partner_statement_id": statement_id,
                        },
                    )
                )

        if str(instruction.get("instruction_status")) == "completed" and not any(
            str(item.get("execution_mode")) == "live"
            and str(item.get("execution_status")) in _TERMINAL_LIVE_EXECUTION_STATUSES
            for item in linked_executions
        ):
            mismatches.append(
                SettlementMismatch(
                    code="completed_instruction_without_live_terminal_execution",
                    severity="blocking",
                    object_family="payout_instruction",
                    source_reference=instruction_id,
                    message="Completed payout instruction must have at least one terminal live execution.",
                    details={"partner_statement_id": statement_id},
                )
            )

        payout_views.append(
            {
                "payout_instruction_id": instruction_id,
                "partner_account_id": _string_or_none(instruction.get("partner_account_id")),
                "partner_statement_id": statement_id,
                "partner_payout_account_id": _string_or_none(instruction.get("partner_payout_account_id")),
                "instruction_status": instruction.get("instruction_status"),
                "payout_amount": _round_money(instruction.get("payout_amount", 0)),
                "currency_code": str(instruction.get("currency_code") or "USD").upper(),
                "linked_execution_ids": [str(item["id"]) for item in linked_executions if item.get("id") is not None],
                "mismatch_codes": sorted(
                    {
                        item.code
                        for item in mismatches
                        if item.object_family == "payout_instruction" and item.source_reference == instruction_id
                    }
                ),
            }
        )

    for execution in payout_executions:
        execution_id = str(execution["id"])
        instruction_id = _string_or_none(execution.get("payout_instruction_id"))
        instruction = instruction_by_id.get(instruction_id or "")
        if instruction is None:
            mismatches.append(
                SettlementMismatch(
                    code="payout_execution_without_instruction",
                    severity="blocking",
                    object_family="payout_execution",
                    source_reference=execution_id,
                    message="Payout execution does not map to a canonical payout instruction.",
                    details={"payout_instruction_id": instruction_id},
                )
            )
            continue

        mismatch_details: dict[str, Any] = {}
        instruction_partner_account_id = _string_or_none(instruction.get("partner_account_id"))
        execution_partner_account_id = _string_or_none(execution.get("partner_account_id"))
        if instruction_partner_account_id != execution_partner_account_id:
            mismatch_details["partner_account_id"] = {
                "instruction_value": instruction_partner_account_id,
                "execution_value": execution_partner_account_id,
            }
        instruction_partner_statement_id = _string_or_none(instruction.get("partner_statement_id"))
        execution_partner_statement_id = _string_or_none(execution.get("partner_statement_id"))
        if instruction_partner_statement_id != execution_partner_statement_id:
            mismatch_details["partner_statement_id"] = {
                "instruction_value": instruction_partner_statement_id,
                "execution_value": execution_partner_statement_id,
            }
        if _string_or_none(instruction.get("partner_payout_account_id")) != _string_or_none(
            execution.get("partner_payout_account_id")
        ):
            mismatch_details["partner_payout_account_id"] = {
                "instruction_value": _string_or_none(instruction.get("partner_payout_account_id")),
                "execution_value": _string_or_none(execution.get("partner_payout_account_id")),
            }
        if mismatch_details:
            mismatches.append(
                SettlementMismatch(
                    code="payout_execution_instruction_mismatch",
                    severity="blocking",
                    object_family="payout_execution",
                    source_reference=execution_id,
                    message="Payout execution identity fields diverge from the linked payout instruction.",
                    details=mismatch_details,
                )
            )

        if (
            str(execution.get("execution_mode")) == "live"
            and str(execution.get("execution_status")) == "reconciled"
            and str(instruction.get("instruction_status")) != "completed"
        ):
            mismatches.append(
                SettlementMismatch(
                    code="reconciled_execution_without_completed_instruction",
                    severity="blocking",
                    object_family="payout_execution",
                    source_reference=execution_id,
                    message="Reconciled payout execution requires a completed payout instruction.",
                    details={"payout_instruction_id": instruction_id},
                )
            )

    return payout_views


def _build_liability_views(
    *,
    earning_events: list[dict[str, Any]],
    active_holds_by_event: dict[str, list[dict[str, Any]]],
    active_reserves_by_event: dict[str, list[dict[str, Any]]],
    active_partner_reserves_by_account: dict[str, list[dict[str, Any]]],
    statement_views: list[dict[str, Any]],
    payout_instructions: list[dict[str, Any]],
    payout_executions: list[dict[str, Any]],
    mismatches: list[SettlementMismatch],
) -> list[dict[str, Any]]:
    payout_execution_ids_by_instruction: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for execution in payout_executions:
        instruction_id = _string_or_none(execution.get("payout_instruction_id"))
        if instruction_id is not None:
            payout_execution_ids_by_instruction[instruction_id].append(execution)

    statements_by_partner: dict[str, list[dict[str, Any]]] = defaultdict(list)
    active_statement_event_ids_by_partner: dict[str, set[str]] = defaultdict(set)
    for statement_view in statement_views:
        partner_account_id = _string_or_none(statement_view.get("partner_account_id"))
        if partner_account_id is None:
            continue
        statements_by_partner[partner_account_id].append(statement_view)
        if bool(statement_view.get("is_latest_version")):
            active_statement_event_ids_by_partner[partner_account_id].update(
                statement_view["linked_object_ids"]["earning_event_ids"]
            )

    instructions_by_partner: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for instruction in payout_instructions:
        partner_account_id = _string_or_none(instruction.get("partner_account_id"))
        if partner_account_id is not None:
            instructions_by_partner[partner_account_id].append(instruction)

    events_by_partner: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in earning_events:
        partner_account_id = _string_or_none(event.get("partner_account_id"))
        if partner_account_id is not None:
            events_by_partner[partner_account_id].append(event)

    partner_ids = sorted(
        set(events_by_partner)
        | set(statements_by_partner)
        | set(active_partner_reserves_by_account)
        | set(instructions_by_partner)
    )

    liability_views: list[dict[str, Any]] = []
    for partner_account_id in partner_ids:
        partner_events = sorted(events_by_partner.get(partner_account_id, []), key=_row_sort_key)
        active_statement_views = [
            item for item in statements_by_partner.get(partner_account_id, []) if bool(item.get("is_latest_version"))
        ]
        covered_event_ids = active_statement_event_ids_by_partner.get(partner_account_id, set())

        accrual_amount = _sum_amount(partner_events, "total_amount")
        reversed_amount = _sum_amount(
            [item for item in partner_events if str(item.get("event_status")) == "reversed"],
            "total_amount",
        )
        on_hold_amount = _sum_amount(
            [
                item
                for item in partner_events
                if str(item.get("id")) not in covered_event_ids
                and str(item.get("event_status")) == "on_hold"
            ],
            "total_amount",
        )
        blocked_amount = _sum_amount(
            [
                item
                for item in partner_events
                if str(item.get("id")) not in covered_event_ids
                and str(item.get("event_status")) == "blocked"
            ],
            "total_amount",
        )
        available_unstatemented_events = [
            item
            for item in partner_events
            if str(item.get("id")) not in covered_event_ids
            and str(item.get("event_status")) == "available"
        ]
        available_unstatemented_amount = _sum_amount(available_unstatemented_events, "total_amount")
        active_event_reserve_amount = _round_money(
            sum(
                _sum_amount(active_reserves_by_event.get(str(item.get("id")), []), "amount")
                for item in partner_events
            )
        )
        active_partner_reserve_amount = _sum_amount(
            active_partner_reserves_by_account.get(partner_account_id, []),
            "amount",
        )

        active_statement_available_amount = _round_money(
            sum(_round_money(item["statement_totals"]["available_amount"]) for item in active_statement_views)
        )
        open_statement_available_amount = _round_money(
            sum(
                _round_money(item["statement_totals"]["available_amount"])
                for item in active_statement_views
                if str(item.get("statement_status")) == "open"
            )
        )
        closed_statement_available_amount = _round_money(
            sum(
                _round_money(item["statement_totals"]["available_amount"])
                for item in active_statement_views
                if str(item.get("statement_status")) == "closed"
            )
        )

        partner_instructions = sorted(instructions_by_partner.get(partner_account_id, []), key=_row_sort_key)
        pending_approval_amount = _sum_amount(
            [item for item in partner_instructions if str(item.get("instruction_status")) == "pending_approval"],
            "payout_amount",
        )
        approved_amount = _sum_amount(
            [item for item in partner_instructions if str(item.get("instruction_status")) == "approved"],
            "payout_amount",
        )
        completed_amount = _sum_amount(
            [item for item in partner_instructions if str(item.get("instruction_status")) == "completed"],
            "payout_amount",
        )
        live_execution_count = sum(
            1
            for instruction in partner_instructions
            for execution in payout_execution_ids_by_instruction.get(str(instruction["id"]), [])
            if str(execution.get("execution_mode")) == "live"
        )
        reconciled_execution_count = sum(
            1
            for instruction in partner_instructions
            for execution in payout_execution_ids_by_instruction.get(str(instruction["id"]), [])
            if str(execution.get("execution_mode")) == "live"
            and str(execution.get("execution_status")) == "reconciled"
        )

        adjustment_credit_amount = _round_money(
            sum(
                _round_money(item["recomputed_totals"]["adjustment_net_amount"])
                for item in active_statement_views
                if item["recomputed_totals"]["adjustment_net_amount"] > 0
            )
        )
        adjustment_net_amount = _round_money(
            sum(_round_money(item["recomputed_totals"]["adjustment_net_amount"]) for item in active_statement_views)
        )
        adjustment_debit_amount = _round_money(adjustment_credit_amount - adjustment_net_amount)
        outstanding_statement_liability_amount = _round_money(
            active_statement_available_amount + available_unstatemented_amount - completed_amount
        )
        if outstanding_statement_liability_amount < 0:
            mismatches.append(
                SettlementMismatch(
                    code="paid_amount_exceeds_statement_liability",
                    severity="blocking",
                    object_family="partner_account",
                    source_reference=partner_account_id,
                    message="Completed payout volume exceeds active statement and unstatemented available liability.",
                    details={
                        "active_statement_available_amount": active_statement_available_amount,
                        "available_unstatemented_amount": available_unstatemented_amount,
                        "completed_payout_amount": completed_amount,
                    },
                )
            )

        liability_views.append(
            {
                "partner_account_id": partner_account_id,
                "event_status_totals": {
                    "accrual_amount": accrual_amount,
                    "on_hold_amount": on_hold_amount,
                    "blocked_amount": blocked_amount,
                    "available_unstatemented_amount": available_unstatemented_amount,
                    "reversed_amount": reversed_amount,
                },
                "reserve_totals": {
                    "active_event_reserve_amount": active_event_reserve_amount,
                    "active_partner_reserve_amount": active_partner_reserve_amount,
                    "total_active_reserve_amount": _round_money(
                        active_event_reserve_amount + active_partner_reserve_amount
                    ),
                },
                "adjustment_totals": {
                    "credit_amount": adjustment_credit_amount,
                    "debit_amount": adjustment_debit_amount,
                    "net_amount": adjustment_net_amount,
                },
                "statement_totals": {
                    "active_statement_count": len(active_statement_views),
                    "open_statement_available_amount": open_statement_available_amount,
                    "closed_statement_available_amount": closed_statement_available_amount,
                    "active_statement_available_amount": active_statement_available_amount,
                },
                "payout_totals": {
                    "pending_approval_amount": pending_approval_amount,
                    "approved_amount": approved_amount,
                    "completed_amount": completed_amount,
                    "live_execution_count": live_execution_count,
                    "reconciled_execution_count": reconciled_execution_count,
                },
                "coverage": {
                    "covered_event_count": len(covered_event_ids),
                    "unstatemented_available_event_count": len(available_unstatemented_events),
                },
                "liability_totals": {
                    "available_statement_amount": active_statement_available_amount,
                    "available_unstatemented_amount": available_unstatemented_amount,
                    "completed_payout_amount": completed_amount,
                    "outstanding_statement_liability_amount": outstanding_statement_liability_amount,
                },
            }
        )

    return liability_views


def _rows_by_id(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(item["id"]): item for item in rows if item.get("id") is not None}


def _sorted_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted((dict(item) for item in rows), key=_row_sort_key)


def _row_sort_key(item: dict[str, Any]) -> tuple[str, str]:
    return (_normalize_timestamp(item.get("created_at")), str(item.get("id", "")))


def _normalize_timestamp(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    if text.endswith("Z"):
        return text[:-1] + "+00:00"
    return text


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _string_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(item) for item in values if item is not None]


def _sum_amount(rows: list[dict[str, Any]], field_name: str) -> float:
    return _round_money(sum(_decimal_from_value(item.get(field_name, 0)) for item in rows))


def _net_adjustment_amount(adjustments: list[dict[str, Any]]) -> float:
    total = Decimal("0.00")
    for adjustment in adjustments:
        amount = _decimal_from_value(adjustment.get("amount", 0))
        if str(adjustment.get("adjustment_direction")) == "credit":
            total += amount
        else:
            total -= amount
    return _round_money(total)


def _decimal_from_value(value: Any) -> Decimal:
    if value is None:
        return Decimal("0.00")
    return Decimal(str(value))


def _round_money(value: Any) -> float:
    return float(_decimal_from_value(value).quantize(Decimal("0.01")))
