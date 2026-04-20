"""Phase 7 analytical marts and reporting reconciliation helpers."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

REPORT_VERSION = "phase7-reporting-marts-v1"

BLOCKING_MISMATCH_CODES = {
    "attribution_result_without_order",
    "commissionability_evaluation_without_order",
    "renewal_order_without_order",
    "refund_without_order",
    "payment_dispute_without_order",
    "earning_event_without_partner_account",
    "partner_statement_without_partner_account",
    "outbox_event_missing_required_publication",
}

_REQUIRED_OUTBOX_CONSUMERS = ("analytics_mart", "operational_replay")
_PAID_ORDER_STATUSES = {"paid"}
_TERMINAL_DISPUTE_OUTCOMES = {"lost", "reversed"}


@dataclass(frozen=True)
class ReportingMismatch:
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


def build_phase7_reporting_marts_pack(snapshot: dict[str, Any]) -> dict[str, Any]:
    metadata = dict(snapshot.get("metadata") or {})
    orders = _sorted_rows(snapshot.get("orders", []))
    attribution_results = _sorted_rows(snapshot.get("order_attribution_results", []))
    commissionability_evaluations = _sorted_rows(snapshot.get("commissionability_evaluations", []))
    renewal_orders = _sorted_rows(snapshot.get("renewal_orders", []))
    refunds = _sorted_rows(snapshot.get("refunds", []))
    payment_disputes = _sorted_rows(snapshot.get("payment_disputes", []))
    earning_events = _sorted_rows(snapshot.get("earning_events", []))
    partner_statements = _sorted_rows(snapshot.get("partner_statements", []))
    outbox_events = _sorted_rows(snapshot.get("outbox_events", []))
    outbox_publications = _sorted_rows(snapshot.get("outbox_publications", []))

    order_by_id = _rows_by_id(orders)
    attribution_by_order_id: dict[str, dict[str, Any]] = {}
    evaluation_by_order_id: dict[str, dict[str, Any]] = {}
    renewal_by_order_id: dict[str, dict[str, Any]] = {}
    refunds_by_order_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    disputes_by_order_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    earning_events_by_partner: dict[str, list[dict[str, Any]]] = defaultdict(list)
    statements_by_partner: dict[str, list[dict[str, Any]]] = defaultdict(list)
    publications_by_event_id: dict[str, list[dict[str, Any]]] = defaultdict(list)

    mismatches: list[ReportingMismatch] = []

    for item in attribution_results:
        order_id = _string_or_none(item.get("order_id"))
        if order_id is None or order_id not in order_by_id:
            mismatches.append(
                ReportingMismatch(
                    code="attribution_result_without_order",
                    severity="blocking",
                    object_family="order_attribution_result",
                    source_reference=str(item.get("id", "unknown")),
                    message="Order attribution result references an order missing from the analytical snapshot.",
                    details={"order_id": order_id},
                )
            )
            continue
        attribution_by_order_id[order_id] = item

    for item in commissionability_evaluations:
        order_id = _string_or_none(item.get("order_id"))
        if order_id is None or order_id not in order_by_id:
            mismatches.append(
                ReportingMismatch(
                    code="commissionability_evaluation_without_order",
                    severity="blocking",
                    object_family="commissionability_evaluation",
                    source_reference=str(item.get("id", "unknown")),
                    message="Commissionability evaluation references an order missing from the analytical snapshot.",
                    details={"order_id": order_id},
                )
            )
            continue
        evaluation_by_order_id[order_id] = item

    for item in renewal_orders:
        order_id = _string_or_none(item.get("order_id"))
        if order_id is None or order_id not in order_by_id:
            mismatches.append(
                ReportingMismatch(
                    code="renewal_order_without_order",
                    severity="blocking",
                    object_family="renewal_order",
                    source_reference=str(item.get("id", "unknown")),
                    message="Renewal order references an order missing from the analytical snapshot.",
                    details={"order_id": order_id},
                )
            )
            continue
        renewal_by_order_id[order_id] = item

    for item in refunds:
        order_id = _string_or_none(item.get("order_id"))
        if order_id is None or order_id not in order_by_id:
            mismatches.append(
                ReportingMismatch(
                    code="refund_without_order",
                    severity="blocking",
                    object_family="refund",
                    source_reference=str(item.get("id", "unknown")),
                    message="Refund references an order missing from the analytical snapshot.",
                    details={"order_id": order_id},
                )
            )
            continue
        refunds_by_order_id[order_id].append(item)

    for item in payment_disputes:
        order_id = _string_or_none(item.get("order_id"))
        if order_id is None or order_id not in order_by_id:
            mismatches.append(
                ReportingMismatch(
                    code="payment_dispute_without_order",
                    severity="blocking",
                    object_family="payment_dispute",
                    source_reference=str(item.get("id", "unknown")),
                    message="Payment dispute references an order missing from the analytical snapshot.",
                    details={"order_id": order_id},
                )
            )
            continue
        disputes_by_order_id[order_id].append(item)

    for item in earning_events:
        partner_account_id = _string_or_none(item.get("partner_account_id"))
        if partner_account_id is None:
            mismatches.append(
                ReportingMismatch(
                    code="earning_event_without_partner_account",
                    severity="blocking",
                    object_family="earning_event",
                    source_reference=str(item.get("id", "unknown")),
                    message=(
                        "Earning event is missing partner_account_id and cannot "
                        "be mapped into partner reporting marts."
                    ),
                    details={},
                )
            )
            continue
        earning_events_by_partner[partner_account_id].append(item)

    for item in partner_statements:
        partner_account_id = _string_or_none(item.get("partner_account_id"))
        if partner_account_id is None:
            mismatches.append(
                ReportingMismatch(
                    code="partner_statement_without_partner_account",
                    severity="blocking",
                    object_family="partner_statement",
                    source_reference=str(item.get("id", "unknown")),
                    message=(
                        "Partner statement is missing partner_account_id and cannot "
                        "be mapped into reporting marts."
                    ),
                    details={},
                )
            )
            continue
        statements_by_partner[partner_account_id].append(item)

    for item in outbox_publications:
        event_id = _string_or_none(item.get("outbox_event_id"))
        if event_id is not None:
            publications_by_event_id[event_id].append(item)

    order_mart_rows: list[dict[str, Any]] = []
    qualifying_candidates_by_user: dict[str, list[tuple[datetime, str]]] = defaultdict(list)

    for order in orders:
        order_id = str(order["id"])
        attribution = attribution_by_order_id.get(order_id)
        evaluation = evaluation_by_order_id.get(order_id)
        renewal = renewal_by_order_id.get(order_id)
        order_refunds = refunds_by_order_id.get(order_id, [])
        order_disputes = disputes_by_order_id.get(order_id, [])

        if str(order.get("order_status")) == "committed" and attribution is None:
            mismatches.append(
                ReportingMismatch(
                    code="committed_order_missing_attribution_result",
                    severity="warning",
                    object_family="order",
                    source_reference=order_id,
                    message=(
                        "Committed order is missing canonical attribution result "
                        "and will degrade reporting explainability."
                    ),
                    details={},
                )
            )

        if _is_paid_order(order) and evaluation is None:
            mismatches.append(
                ReportingMismatch(
                    code="paid_order_missing_commissionability_evaluation",
                    severity="warning",
                    object_family="order",
                    source_reference=order_id,
                    message=(
                        "Paid order is missing commissionability evaluation and "
                        "cannot fully participate in payout-facing reporting."
                    ),
                    details={},
                )
            )

        has_refund = any(str(item.get("refund_status")) == "succeeded" for item in order_refunds)
        has_open_dispute = any(str(item.get("outcome_class")) == "open" for item in order_disputes)
        has_chargeback = any(str(item.get("outcome_class")) in _TERMINAL_DISPUTE_OUTCOMES for item in order_disputes)
        is_paid_conversion = _is_paid_order(order) and not has_refund and not has_chargeback
        is_renewal = renewal is not None

        partner_account_id = _string_or_none(
            (renewal or {}).get("effective_partner_account_id")
            or (attribution or {}).get("partner_account_id")
        )
        partner_code_id = _string_or_none(
            (renewal or {}).get("effective_partner_code_id")
            or (attribution or {}).get("partner_code_id")
        )
        owner_type = str(
            (renewal or {}).get("effective_owner_type")
            or (attribution or {}).get("owner_type")
            or "none"
        )
        owner_source = _string_or_none(
            (renewal or {}).get("effective_owner_source")
            or (attribution or {}).get("owner_source")
        )
        commissionability_status = _string_or_none((evaluation or {}).get("commissionability_status"))
        qualifying_candidate = (
            is_paid_conversion
            and not is_renewal
            and commissionability_status == "eligible"
            and partner_account_id is not None
        )
        if qualifying_candidate:
            qualifying_candidates_by_user[str(order.get("user_id"))].append((_as_dt(order.get("created_at")), order_id))

        order_mart_rows.append(
            {
                "order_id": order_id,
                "user_id": str(order.get("user_id")),
                "partner_account_id": partner_account_id,
                "partner_code_id": partner_code_id,
                "owner_type": owner_type,
                "owner_source": owner_source,
                "sale_channel": order.get("sale_channel"),
                "currency_code": order.get("currency_code"),
                "order_status": order.get("order_status"),
                "settlement_status": order.get("settlement_status"),
                "commissionability_status": commissionability_status,
                "is_paid_conversion": is_paid_conversion,
                "is_renewal": is_renewal,
                "has_refund": has_refund,
                "has_open_dispute": has_open_dispute,
                "has_chargeback": has_chargeback,
                "commission_base_amount": _money(order.get("commission_base_amount")),
                "displayed_price": _money(order.get("displayed_price")),
                "created_at": order.get("created_at"),
            }
        )

    qualifying_first_payment_order_ids = {
        order_id
        for scoped_candidates in qualifying_candidates_by_user.values()
        for _, order_id in [min(scoped_candidates, key=lambda item: (item[0], item[1]))]
    }
    for row in order_mart_rows:
        row["is_qualifying_first_payment"] = row["order_id"] in qualifying_first_payment_order_ids

    partner_reporting_mart = _build_partner_reporting_mart(
        order_mart_rows=order_mart_rows,
        earning_events_by_partner=earning_events_by_partner,
        statements_by_partner=statements_by_partner,
        mismatches=mismatches,
    )
    reporting_health_views = _build_reporting_health_views(
        outbox_events=outbox_events,
        publications_by_event_id=publications_by_event_id,
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
            "orders": len(orders),
            "order_attribution_results": len(attribution_results),
            "commissionability_evaluations": len(commissionability_evaluations),
            "renewal_orders": len(renewal_orders),
            "refunds": len(refunds),
            "payment_disputes": len(payment_disputes),
            "earning_events": len(earning_events),
            "partner_statements": len(partner_statements),
            "outbox_events": len(outbox_events),
            "outbox_publications": len(outbox_publications),
        },
        "order_reporting_mart": sorted(order_mart_rows, key=lambda item: item["order_id"]),
        "partner_reporting_mart": partner_reporting_mart,
        "reporting_health_views": reporting_health_views,
        "reconciliation": {
            "status": status,
            "mismatch_counts": mismatch_counts,
            "mismatches": [item.to_dict() for item in mismatches],
            "blocking_mismatches": blocking_mismatches,
        },
    }


def _build_partner_reporting_mart(
    *,
    order_mart_rows: list[dict[str, Any]],
    earning_events_by_partner: dict[str, list[dict[str, Any]]],
    statements_by_partner: dict[str, list[dict[str, Any]]],
    mismatches: list[ReportingMismatch],
) -> list[dict[str, Any]]:
    orders_by_partner: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in order_mart_rows:
        partner_account_id = _string_or_none(row.get("partner_account_id"))
        if partner_account_id is not None:
            orders_by_partner[partner_account_id].append(row)

    partner_ids = sorted(set(orders_by_partner) | set(earning_events_by_partner) | set(statements_by_partner))
    mart_rows: list[dict[str, Any]] = []
    for partner_account_id in partner_ids:
        partner_orders = orders_by_partner.get(partner_account_id, [])
        partner_events = earning_events_by_partner.get(partner_account_id, [])
        partner_statements = [
            item
            for item in statements_by_partner.get(partner_account_id, [])
            if item.get("superseded_by_statement_id") is None
        ]

        paid_orders = [item for item in partner_orders if item["is_paid_conversion"]]
        refunded_orders = [item for item in partner_orders if item["has_refund"]]
        chargeback_orders = [item for item in partner_orders if item["has_chargeback"]]
        qualifying_first = [item for item in partner_orders if item["is_qualifying_first_payment"]]
        renewal_paid = [item for item in partner_orders if item["is_paid_conversion"] and item["is_renewal"]]

        eligible_paid_orders = [
            item
            for item in partner_orders
            if item["is_paid_conversion"] and item.get("commissionability_status") == "eligible"
        ]
        if eligible_paid_orders and not partner_events:
            mismatches.append(
                ReportingMismatch(
                    code="eligible_partner_orders_missing_earning_events",
                    severity="warning",
                    object_family="partner_reporting_mart",
                    source_reference=partner_account_id,
                    message="Partner has eligible paid orders but no earning events in the analytical snapshot.",
                    details={"eligible_paid_order_count": len(eligible_paid_orders)},
                )
            )

        paid_conversion_count = len(paid_orders)
        refund_rate = _rate(len(refunded_orders), paid_conversion_count)
        chargeback_rate = _rate(len(chargeback_orders), paid_conversion_count)
        available_earnings_amount = _round_money(_sum_amount(partner_events, "available_amount"))
        statement_liability_amount = _round_money(_sum_amount(partner_statements, "available_amount"))

        mart_rows.append(
            {
                "partner_account_id": partner_account_id,
                "paid_conversion_count": paid_conversion_count,
                "qualifying_first_payment_count": len(qualifying_first),
                "renewal_paid_count": len(renewal_paid),
                "refund_count": len(refunded_orders),
                "chargeback_count": len(chargeback_orders),
                "refund_rate": refund_rate,
                "chargeback_rate": chargeback_rate,
                "paid_conversion_commission_base_amount": _round_money(
                    sum(Decimal(str(item["commission_base_amount"])) for item in paid_orders)
                ),
                "available_earnings_amount": available_earnings_amount,
                "statement_liability_amount": statement_liability_amount,
                "statement_count": len(partner_statements),
                "earning_event_count": len(partner_events),
                "currency_codes": sorted(
                    {
                        str(item.get("currency_code"))
                        for item in partner_orders + partner_statements + partner_events
                        if item.get("currency_code")
                    }
                ),
            }
        )
    return mart_rows


def _build_reporting_health_views(
    *,
    outbox_events: list[dict[str, Any]],
    publications_by_event_id: dict[str, list[dict[str, Any]]],
    mismatches: list[ReportingMismatch],
) -> dict[str, Any]:
    consumer_counts: dict[str, Counter] = defaultdict(Counter)
    family_counts: Counter = Counter()
    consumer_backlog_event_ids: dict[str, list[str]] = defaultdict(list)
    consumer_failed_event_ids: dict[str, list[str]] = defaultdict(list)

    for event in outbox_events:
        event_id = str(event["id"])
        event_family = str(event.get("event_family") or "unknown")
        family_counts[event_family] += 1

        publications = publications_by_event_id.get(event_id, [])
        present_consumers = {str(item.get("consumer_key")) for item in publications if item.get("consumer_key")}
        for required_consumer in _REQUIRED_OUTBOX_CONSUMERS:
            if required_consumer not in present_consumers:
                mismatches.append(
                    ReportingMismatch(
                        code="outbox_event_missing_required_publication",
                        severity="blocking",
                        object_family="outbox_event",
                        source_reference=event_id,
                        message=(
                            "Outbox event is missing a required consumer "
                            "publication row for analytical processing."
                        ),
                        details={"missing_consumer_key": required_consumer},
                    )
                )

        for publication in publications:
            consumer_key = str(publication.get("consumer_key") or "unknown")
            publication_status = str(publication.get("publication_status") or "unknown")
            consumer_counts[consumer_key][publication_status] += 1
            if publication_status in {"pending", "claimed", "submitted"}:
                consumer_backlog_event_ids[consumer_key].append(event_id)
            if publication_status == "failed":
                consumer_failed_event_ids[consumer_key].append(event_id)

    for consumer_key, event_ids in consumer_backlog_event_ids.items():
        if event_ids:
            mismatches.append(
                ReportingMismatch(
                    code="reporting_publication_backlog_present",
                    severity="warning",
                    object_family="outbox_publication",
                    source_reference=consumer_key,
                    message="Reporting consumer still has backlog publications pending analytical completion.",
                    details={"backlog_event_ids": sorted(set(event_ids))},
                )
            )
    for consumer_key, event_ids in consumer_failed_event_ids.items():
        if event_ids:
            mismatches.append(
                ReportingMismatch(
                    code="reporting_publication_failed",
                    severity="warning",
                    object_family="outbox_publication",
                    source_reference=consumer_key,
                    message="Reporting consumer has failed publication rows that require replay or operator attention.",
                    details={"failed_event_ids": sorted(set(event_ids))},
                )
            )

    consumer_views = [
        {
            "consumer_key": consumer_key,
            "pending_count": counts.get("pending", 0),
            "claimed_count": counts.get("claimed", 0),
            "submitted_count": counts.get("submitted", 0),
            "published_count": counts.get("published", 0),
            "failed_count": counts.get("failed", 0),
            "backlog_count": counts.get("pending", 0) + counts.get("claimed", 0) + counts.get("submitted", 0),
        }
        for consumer_key, counts in sorted(consumer_counts.items())
    ]
    family_views = [
        {"event_family": event_family, "event_count": count}
        for event_family, count in sorted(family_counts.items())
    ]
    return {
        "consumer_health_views": consumer_views,
        "family_health_views": family_views,
    }


def _sorted_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        [dict(item) for item in rows],
        key=lambda item: (
            str(item.get("created_at") or ""),
            str(item.get("updated_at") or ""),
            str(item.get("id") or ""),
        ),
    )


def _rows_by_id(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(item["id"]): item for item in rows if item.get("id") is not None}


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _money(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    return float(Decimal(str(value)))


def _round_money(value: Decimal | float) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.01")))


def _sum_amount(rows: list[dict[str, Any]], key: str) -> float:
    total = Decimal("0")
    for row in rows:
        total += Decimal(str(row.get(key) or 0))
    return _round_money(total)


def _rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return _round_money((Decimal(numerator) / Decimal(denominator)) * Decimal("100"))


def _is_paid_order(order: dict[str, Any]) -> bool:
    return str(order.get("settlement_status")) in _PAID_ORDER_STATUSES


def _as_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
    return datetime.min.replace(tzinfo=UTC)
