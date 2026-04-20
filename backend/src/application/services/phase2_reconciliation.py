"""Phase 2 order-domain replay and reconciliation helpers."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

REPORT_VERSION = "phase2-order-reconciliation-v1"

BLOCKING_MISMATCH_CODES = {
    "orphan_refund_without_payment",
    "orphan_payment_dispute_without_payment",
    "refund_total_exceeds_payment_amount",
    "dispute_amount_exceeds_payment_amount",
    "non_completed_payment_with_refund",
}


@dataclass(frozen=True)
class ReconciliationMismatch:
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


def build_phase2_reconciliation_pack(snapshot: dict[str, Any]) -> dict[str, Any]:
    metadata = dict(snapshot.get("metadata") or {})
    payments = [dict(item) for item in snapshot.get("payments", [])]
    refunds = [dict(item) for item in snapshot.get("refunds", [])]
    payment_disputes = [dict(item) for item in snapshot.get("payment_disputes", [])]

    payment_by_id = {str(payment["id"]): payment for payment in payments}
    refunds_by_payment_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    disputes_by_payment_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    mismatches: list[ReconciliationMismatch] = []

    for refund in refunds:
        payment_id = _string_or_none(refund.get("payment_id"))
        if payment_id is None or payment_id not in payment_by_id:
            mismatches.append(
                ReconciliationMismatch(
                    code="orphan_refund_without_payment",
                    severity="blocking",
                    object_family="refund",
                    source_reference=str(refund.get("id") or "unknown-refund"),
                    message="Refund row does not map to a legacy payment record.",
                    details={"payment_id": payment_id},
                )
            )
            continue
        refunds_by_payment_id[payment_id].append(refund)

    for dispute in payment_disputes:
        payment_id = _string_or_none(dispute.get("payment_id"))
        if payment_id is None or payment_id not in payment_by_id:
            mismatches.append(
                ReconciliationMismatch(
                    code="orphan_payment_dispute_without_payment",
                    severity="blocking",
                    object_family="payment_dispute",
                    source_reference=str(dispute.get("id") or "unknown-dispute"),
                    message="Payment dispute row does not map to a legacy payment record.",
                    details={"payment_id": payment_id},
                )
            )
            continue
        disputes_by_payment_id[payment_id].append(dispute)

    replayed_orders: list[dict[str, Any]] = []
    replayed_payment_attempts: list[dict[str, Any]] = []
    replayed_refunds: list[dict[str, Any]] = []
    replayed_payment_disputes: list[dict[str, Any]] = []

    for payment in payments:
        payment_id = str(payment["id"])
        payment_status = str(payment.get("status", ""))
        displayed_amount = _decimal_from_value(payment.get("final_amount", payment.get("amount", 0)))
        payment_amount = _decimal_from_value(payment.get("amount", 0))
        refund_rows = sorted(refunds_by_payment_id.get(payment_id, []), key=_row_sort_key)
        dispute_rows = sorted(disputes_by_payment_id.get(payment_id, []), key=_row_sort_key)
        refunded_total = sum((_decimal_from_value(item.get("amount", 0)) for item in refund_rows), Decimal("0"))
        disputed_total = sum((_decimal_from_value(item.get("amount", 0)) for item in dispute_rows), Decimal("0"))

        if refund_rows and payment_status != "completed":
            mismatches.append(
                ReconciliationMismatch(
                    code="non_completed_payment_with_refund",
                    severity="blocking",
                    object_family="payment",
                    source_reference=payment_id,
                    message="Legacy payment has refund rows but is not completed.",
                    details={"payment_status": payment_status},
                )
            )
        if payment_status == "refunded" and not refund_rows:
            mismatches.append(
                ReconciliationMismatch(
                    code="payment_status_refunded_without_refund_rows",
                    severity="warning",
                    object_family="payment",
                    source_reference=payment_id,
                    message="Legacy payment is marked refunded but no refund rows were provided for replay.",
                    details={"payment_status": payment_status},
                )
            )
        if payment_status not in {"pending", "completed", "failed", "refunded"}:
            mismatches.append(
                ReconciliationMismatch(
                    code="unsupported_payment_status",
                    severity="warning",
                    object_family="payment",
                    source_reference=payment_id,
                    message="Legacy payment status is outside the canonical replay vocabulary.",
                    details={"payment_status": payment_status},
                )
            )
        if refunded_total > payment_amount:
            mismatches.append(
                ReconciliationMismatch(
                    code="refund_total_exceeds_payment_amount",
                    severity="blocking",
                    object_family="payment",
                    source_reference=payment_id,
                    message="Replay detected refund amount above the legacy payment amount.",
                    details={
                        "payment_amount": _decimal_string(payment_amount),
                        "refund_total": _decimal_string(refunded_total),
                    },
                )
            )
        if disputed_total > payment_amount and disputed_total > 0:
            mismatches.append(
                ReconciliationMismatch(
                    code="dispute_amount_exceeds_payment_amount",
                    severity="blocking",
                    object_family="payment",
                    source_reference=payment_id,
                    message="Replay detected dispute volume above the legacy payment amount.",
                    details={
                        "payment_amount": _decimal_string(payment_amount),
                        "disputed_total": _decimal_string(disputed_total),
                    },
                )
            )

        replay_order_id = f"legacy-payment:{payment_id}"
        replayed_orders.append(
            {
                "replay_order_id": replay_order_id,
                "source_payment_id": payment_id,
                "user_uuid": _string_or_none(payment.get("user_uuid")),
                "provider": payment.get("provider"),
                "currency_code": payment.get("currency"),
                "displayed_price": _decimal_string(displayed_amount),
                "settlement_status": _derive_settlement_status(
                    payment_status=payment_status,
                    refunded_total=refunded_total,
                    payment_amount=payment_amount,
                ),
                "source_status": payment_status,
                "partner_code_id": _string_or_none(payment.get("partner_code_id")),
                "promo_code_id": _string_or_none(payment.get("promo_code_id")),
                "created_at": payment.get("created_at"),
            }
        )
        replayed_payment_attempts.append(
            {
                "replay_payment_attempt_id": f"legacy-attempt:{payment_id}:1",
                "replay_order_id": replay_order_id,
                "source_payment_id": payment_id,
                "attempt_number": 1,
                "provider": payment.get("provider"),
                "status": _derive_attempt_status(payment_status),
                "displayed_amount": _decimal_string(displayed_amount),
                "external_reference": payment.get("external_id"),
            }
        )

        for refund in refund_rows:
            replayed_refunds.append(
                {
                    "replay_refund_id": f"legacy-refund:{refund['id']}",
                    "replay_order_id": replay_order_id,
                    "source_refund_id": str(refund["id"]),
                    "source_payment_id": payment_id,
                    "refund_status": str(refund.get("status", "succeeded")),
                    "amount": _decimal_string(_decimal_from_value(refund.get("amount", 0))),
                    "currency_code": refund.get("currency") or payment.get("currency"),
                    "external_reference": refund.get("external_reference"),
                }
            )

        for dispute in dispute_rows:
            replayed_payment_disputes.append(
                {
                    "replay_payment_dispute_id": f"legacy-dispute:{dispute['id']}",
                    "replay_order_id": replay_order_id,
                    "source_payment_dispute_id": str(dispute["id"]),
                    "source_payment_id": payment_id,
                    "subtype": str(dispute.get("subtype", "chargeback")),
                    "outcome_class": str(dispute.get("outcome_class", "open")),
                    "lifecycle_status": str(dispute.get("lifecycle_status", "opened")),
                    "disputed_amount": _decimal_string(_decimal_from_value(dispute.get("amount", 0))),
                    "currency_code": dispute.get("currency") or payment.get("currency"),
                    "external_reference": dispute.get("external_reference"),
                }
            )

    legacy_summary = {
        "payments": {
            "count": len(payments),
            "completed_count": sum(1 for payment in payments if str(payment.get("status")) == "completed"),
            "gross_amount_total": _decimal_string(
                sum((_decimal_from_value(item.get("amount", 0)) for item in payments), Decimal("0"))
            ),
        },
        "refunds": {
            "count": len(refunds),
            "amount_total": _decimal_string(
                sum((_decimal_from_value(item.get("amount", 0)) for item in refunds), Decimal("0"))
            ),
        },
        "payment_disputes": {
            "count": len(payment_disputes),
            "amount_total": _decimal_string(
                sum((_decimal_from_value(item.get("amount", 0)) for item in payment_disputes), Decimal("0"))
            ),
        },
    }

    replayed_summary = {
        "orders": {
            "count": len(replayed_orders),
            "gross_amount_total": _decimal_string(
                sum((Decimal(item["displayed_price"]) for item in replayed_orders), Decimal("0"))
            ),
        },
        "payment_attempts": {"count": len(replayed_payment_attempts)},
        "refunds": {
            "count": len(replayed_refunds),
            "amount_total": _decimal_string(
                sum((Decimal(item["amount"]) for item in replayed_refunds), Decimal("0"))
            ),
        },
        "payment_disputes": {
            "count": len(replayed_payment_disputes),
            "amount_total": _decimal_string(
                sum((Decimal(item["disputed_amount"]) for item in replayed_payment_disputes), Decimal("0"))
            ),
        },
    }

    count_parity = {
        "orders_vs_payments": {
            "expected": legacy_summary["payments"]["count"],
            "actual": replayed_summary["orders"]["count"],
            "matches": legacy_summary["payments"]["count"] == replayed_summary["orders"]["count"],
        },
        "payment_attempts_vs_payments": {
            "expected": legacy_summary["payments"]["count"],
            "actual": replayed_summary["payment_attempts"]["count"],
            "matches": legacy_summary["payments"]["count"] == replayed_summary["payment_attempts"]["count"],
        },
        "refunds_vs_legacy_refunds": {
            "expected": legacy_summary["refunds"]["count"]
            - _count_mismatches(mismatches, "orphan_refund_without_payment"),
            "actual": replayed_summary["refunds"]["count"],
            "matches": (
                legacy_summary["refunds"]["count"] - _count_mismatches(mismatches, "orphan_refund_without_payment")
                == replayed_summary["refunds"]["count"]
            ),
        },
        "payment_disputes_vs_legacy_payment_disputes": {
            "expected": legacy_summary["payment_disputes"]["count"]
            - _count_mismatches(mismatches, "orphan_payment_dispute_without_payment"),
            "actual": replayed_summary["payment_disputes"]["count"],
            "matches": (
                legacy_summary["payment_disputes"]["count"]
                - _count_mismatches(mismatches, "orphan_payment_dispute_without_payment")
                == replayed_summary["payment_disputes"]["count"]
            ),
        },
    }
    amount_parity = {
        "gross_amount_total": {
            "legacy": legacy_summary["payments"]["gross_amount_total"],
            "replayed": replayed_summary["orders"]["gross_amount_total"],
            "matches": (
                legacy_summary["payments"]["gross_amount_total"]
                == replayed_summary["orders"]["gross_amount_total"]
            ),
        },
        "refund_amount_total": {
            "legacy": legacy_summary["refunds"]["amount_total"],
            "replayed": replayed_summary["refunds"]["amount_total"],
            "matches": legacy_summary["refunds"]["amount_total"] == replayed_summary["refunds"]["amount_total"],
        },
        "payment_dispute_amount_total": {
            "legacy": legacy_summary["payment_disputes"]["amount_total"],
            "replayed": replayed_summary["payment_disputes"]["amount_total"],
            "matches": (
                legacy_summary["payment_disputes"]["amount_total"]
                == replayed_summary["payment_disputes"]["amount_total"]
            ),
        },
    }

    mismatch_counter = Counter(item.code for item in mismatches)
    blocking_mismatches = [item.to_dict() for item in mismatches if item.code in BLOCKING_MISMATCH_CODES]
    reconciliation_status = "green"
    if blocking_mismatches:
        reconciliation_status = "red"
    elif mismatches:
        reconciliation_status = "yellow"

    return {
        "metadata": {
            "report_version": REPORT_VERSION,
            "generated_at": _resolve_generated_at(metadata),
            "source_metadata": metadata,
        },
        "legacy_summary": legacy_summary,
        "replayed_summary": replayed_summary,
        "replayed_objects": {
            "orders": replayed_orders,
            "payment_attempts": replayed_payment_attempts,
            "refunds": replayed_refunds,
            "payment_disputes": replayed_payment_disputes,
        },
        "reconciliation": {
            "status": reconciliation_status,
            "count_parity": count_parity,
            "amount_parity": amount_parity,
            "mismatch_counts": dict(sorted(mismatch_counter.items())),
            "mismatches": [item.to_dict() for item in mismatches],
            "blocking_mismatches": blocking_mismatches,
        },
    }


def summarize_phase2_reconciliation_pack(report: dict[str, Any]) -> str:
    reconciliation = dict(report.get("reconciliation") or {})
    legacy_summary = dict(report.get("legacy_summary") or {})
    replayed_summary = dict(report.get("replayed_summary") or {})
    lines = [
        f"status: {reconciliation.get('status', 'unknown')}",
        f"legacy payments: {legacy_summary.get('payments', {}).get('count', 0)}",
        f"replayed orders: {replayed_summary.get('orders', {}).get('count', 0)}",
        f"replayed payment_attempts: {replayed_summary.get('payment_attempts', {}).get('count', 0)}",
        f"replayed refunds: {replayed_summary.get('refunds', {}).get('count', 0)}",
        f"replayed payment_disputes: {replayed_summary.get('payment_disputes', {}).get('count', 0)}",
    ]
    mismatch_counts = dict(reconciliation.get("mismatch_counts") or {})
    if mismatch_counts:
        lines.append("mismatch_counts:")
        for code, count in sorted(mismatch_counts.items()):
            lines.append(f"  - {code}: {count}")
    else:
        lines.append("mismatch_counts: none")
    return "\n".join(lines)


def _derive_settlement_status(*, payment_status: str, refunded_total: Decimal, payment_amount: Decimal) -> str:
    if refunded_total >= payment_amount and payment_amount > 0:
        return "refunded"
    if refunded_total > 0:
        return "partially_refunded"
    if payment_status == "completed":
        return "paid"
    if payment_status == "refunded":
        return "refunded"
    if payment_status == "failed":
        return "failed"
    return "pending_payment"


def _derive_attempt_status(payment_status: str) -> str:
    return {
        "completed": "succeeded",
        "refunded": "succeeded",
        "failed": "failed",
        "pending": "pending",
    }.get(payment_status, "pending")


def _decimal_from_value(value: Any) -> Decimal:
    return Decimal(str(value or 0))


def _decimal_string(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01'))}"


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _row_sort_key(row: dict[str, Any]) -> tuple[str, str]:
    return (str(row.get("created_at") or ""), str(row.get("id") or ""))


def _count_mismatches(mismatches: list[ReconciliationMismatch], code: str) -> int:
    return sum(1 for item in mismatches if item.code == code)


def _resolve_generated_at(metadata: dict[str, Any]) -> str:
    explicit = metadata.get("replay_generated_at")
    if explicit:
        return str(explicit)
    return datetime.now(UTC).isoformat()
