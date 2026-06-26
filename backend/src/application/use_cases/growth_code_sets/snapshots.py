"""Versioned Growth Codes v6 checkout snapshot helpers."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

GROWTH_CHECKOUT_SNAPSHOT_VERSION = "growth-checkout.v3"
GROWTH_CHECKOUT_INTEGRITY_KEY = "snapshot_integrity"
GROWTH_CHECKOUT_PRODUCER = "cybervpn-backend"

_KNOWN_REQUIRED_FIELDS = frozenset(
    {
        "snapshot_version",
        "code_set",
        "private_catalog",
        "risk",
        "fx",
        "pricing",
        "reservation_group_id",
    }
)


class SnapshotIntegrityError(ValueError):
    """Raised when a persisted checkout snapshot fails integrity validation."""


def attach_growth_checkout_integrity(
    snapshot: dict[str, Any],
    *,
    created_at: datetime | None = None,
    producer: str = GROWTH_CHECKOUT_PRODUCER,
) -> dict[str, Any]:
    """Return a snapshot copy with a stable v3 checksum envelope."""

    prepared = deepcopy(snapshot)
    prepared.pop(GROWTH_CHECKOUT_INTEGRITY_KEY, None)
    prepared[GROWTH_CHECKOUT_INTEGRITY_KEY] = {
        "schema_version": GROWTH_CHECKOUT_SNAPSHOT_VERSION,
        "checksum": _checksum_snapshot_payload(prepared),
        "created_at": (created_at or datetime.now(UTC)).isoformat(),
        "producer": producer,
        "required_fields": sorted(_KNOWN_REQUIRED_FIELDS),
    }
    return prepared


def validate_growth_checkout_integrity(snapshot: dict[str, Any]) -> None:
    """Fail closed when a v3 snapshot envelope is unsupported or modified."""

    integrity = snapshot.get(GROWTH_CHECKOUT_INTEGRITY_KEY)
    if integrity is None:
        return
    if not isinstance(integrity, dict):
        raise SnapshotIntegrityError("SNAPSHOT_INTEGRITY_ERROR")
    if integrity.get("schema_version") != GROWTH_CHECKOUT_SNAPSHOT_VERSION:
        raise SnapshotIntegrityError("SNAPSHOT_INTEGRITY_ERROR")
    required_fields = integrity.get("required_fields")
    if not isinstance(required_fields, list):
        raise SnapshotIntegrityError("SNAPSHOT_INTEGRITY_ERROR")
    unknown_required = {str(field) for field in required_fields} - _KNOWN_REQUIRED_FIELDS
    if unknown_required:
        raise SnapshotIntegrityError("SNAPSHOT_INTEGRITY_ERROR")
    expected_checksum = integrity.get("checksum")
    if not isinstance(expected_checksum, str) or not expected_checksum:
        raise SnapshotIntegrityError("SNAPSHOT_INTEGRITY_ERROR")
    if _checksum_snapshot_payload(snapshot) != expected_checksum:
        raise SnapshotIntegrityError("SNAPSHOT_INTEGRITY_ERROR")


def build_growth_checkout_v3_snapshot(
    *,
    quote_snapshot: dict[str, Any],
    context_snapshot: dict[str, Any],
    request_snapshot: dict[str, Any],
) -> dict[str, Any]:
    """Build the immutable v3 execution snapshot from the quote payload."""

    code_resolution = _dict_or_empty(quote_snapshot.get("code_resolution"))
    discount_lines = [_dict_or_empty(line) for line in quote_snapshot.get("discounts") or [] if isinstance(line, dict)]
    applications = _build_application_lines(
        code_resolution=code_resolution,
        discount_lines=discount_lines,
        quote_snapshot=quote_snapshot,
    )
    growth_effects = _build_growth_effects(
        code_resolution=code_resolution,
        discount_lines=discount_lines,
        quote_snapshot=quote_snapshot,
    )
    reservation_group_id = code_resolution.get("reservation_group_id") or code_resolution.get("reservation_id")
    snapshot = {
        "snapshot_version": GROWTH_CHECKOUT_SNAPSHOT_VERSION,
        "code_set": {
            "id": quote_snapshot.get("code_set_id"),
            "hash": _code_set_hash(quote_snapshot=quote_snapshot, applications=applications),
            "acceptance_mode": "single_legacy_code" if applications else "none",
            "applications": applications,
        },
        "private_catalog": _dict_or_empty(quote_snapshot.get("private_catalog")),
        "risk": {
            "aggregate_action": code_resolution.get("risk_action") or "allow",
            "decision_ids": _compact_list(
                [
                    code_resolution.get("risk_decision_id"),
                    quote_snapshot.get("risk_decision_id"),
                ]
            ),
        },
        "fx": {
            "conversion_ids": _compact_list(
                [
                    line.get("fx_conversion_id")
                    for line in discount_lines
                    if isinstance(line.get("fx_conversion_id"), str)
                ]
            ),
        },
        "pricing": {
            "base_price": _money_string(quote_snapshot.get("base_price")),
            "discount_lines": deepcopy(discount_lines),
            "total_discount": _money_string(quote_snapshot.get("discount_amount")),
            "wallet_amount": _money_string(quote_snapshot.get("wallet_amount")),
            "gateway_amount": _money_string(quote_snapshot.get("gateway_amount")),
            "currency": quote_snapshot.get("currency_code")
            or request_snapshot.get("currency")
            or context_snapshot.get("currency_code"),
            "is_zero_gateway": bool(quote_snapshot.get("is_zero_gateway", False)),
        },
        "reservation_group_id": str(reservation_group_id) if reservation_group_id else None,
        "growth_effects": growth_effects,
    }
    return attach_growth_checkout_integrity(snapshot)


def read_growth_checkout_v3_snapshot(snapshot: dict[str, Any]) -> dict[str, Any] | None:
    """Return a verified v3 snapshot from order pricing data, if present."""

    candidate = snapshot.get("growth_checkout_snapshot")
    if not isinstance(candidate, dict):
        return None
    validate_growth_checkout_integrity(candidate)
    if candidate.get("snapshot_version") != GROWTH_CHECKOUT_SNAPSHOT_VERSION:
        raise SnapshotIntegrityError("SNAPSHOT_INTEGRITY_ERROR")
    for required_field in _KNOWN_REQUIRED_FIELDS:
        if required_field not in candidate:
            raise SnapshotIntegrityError("SNAPSHOT_INTEGRITY_ERROR")
    return deepcopy(candidate)


def canonical_growth_checkout_snapshot(snapshot: dict[str, Any] | None) -> dict[str, Any]:
    """Return a drift-safe copy that ignores integrity envelope metadata."""

    prepared = deepcopy(snapshot or {})
    prepared.pop(GROWTH_CHECKOUT_INTEGRITY_KEY, None)
    return prepared


def _checksum_snapshot_payload(snapshot: dict[str, Any]) -> str:
    canonical = canonical_growth_checkout_snapshot(snapshot)
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _build_application_lines(
    *,
    code_resolution: dict[str, Any],
    discount_lines: list[dict[str, Any]],
    quote_snapshot: dict[str, Any],
) -> list[dict[str, Any]]:
    growth_code_id = code_resolution.get("growth_code_id")
    if not growth_code_id:
        return []
    discount = discount_lines[0] if discount_lines else {}
    code_ref = _dict_or_empty(discount.get("code_ref") or quote_snapshot.get("code_input_ref"))
    policy_snapshot = _dict_or_empty(code_resolution.get("policy_snapshot"))
    return [
        {
            "growth_code_id": str(growth_code_id),
            "masked_code": _masked_code(code_ref),
            "roles": _compact_list([code_resolution.get("code_type") or discount.get("type") or "discount"]),
            "status": "accepted"
            if code_resolution.get("accepted") is True
            else str(code_resolution.get("result") or "unknown"),
            "policy_version_id": str(
                discount.get("policy_version_id") or policy_snapshot.get("policy_version_id") or ""
            )
            or None,
            "rule_checksum": policy_snapshot.get("rule_checksum"),
            "discount": {
                "source_amount": _money_string(discount.get("source_amount") or discount.get("amount")),
                "source_currency": discount.get("source_currency") or quote_snapshot.get("currency_code"),
                "target_amount": _money_string(discount.get("target_amount") or discount.get("amount")),
                "target_currency": discount.get("target_currency") or quote_snapshot.get("currency_code"),
                "applied_amount": _money_string(discount.get("applied_amount") or discount.get("amount")),
            },
            "benefits": deepcopy(policy_snapshot.get("benefits") or []),
            "reservation_id": str(code_resolution.get("reservation_id") or "") or None,
            "risk_decision_id": str(code_resolution.get("risk_decision_id") or "") or None,
            "code_ref": code_ref,
        }
    ]


def _build_growth_effects(
    *,
    code_resolution: dict[str, Any],
    discount_lines: list[dict[str, Any]],
    quote_snapshot: dict[str, Any],
) -> dict[str, Any]:
    discount = discount_lines[0] if discount_lines else {}
    policy_snapshot = _dict_or_empty(code_resolution.get("policy_snapshot"))
    gateway_amount = _decimal_or_zero(quote_snapshot.get("gateway_amount"))
    return {
        "growth_code_id": code_resolution.get("growth_code_id"),
        "campaign_id": code_resolution.get("campaign_id") or policy_snapshot.get("campaign_id"),
        "policy_version_id": discount.get("policy_version_id") or policy_snapshot.get("policy_version_id"),
        "reservation_id": code_resolution.get("reservation_id"),
        "normalized_code_hash": _dict_or_empty(quote_snapshot.get("code_input_ref")).get("code_hash"),
        "code_type": code_resolution.get("code_type"),
        "discount": {
            "type": discount.get("type") or code_resolution.get("code_type"),
            "value": str(discount.get("value") or discount.get("amount") or "0"),
            "scope": discount.get("scope") or "order_total",
            "discountable_amount": _money_string(quote_snapshot.get("displayed_price")),
            "discount_amount": _money_string(quote_snapshot.get("discount_amount")),
        },
        "benefits": deepcopy(policy_snapshot.get("benefits") or []),
        "settlement": {
            "gross_amount": _money_string(quote_snapshot.get("displayed_price")),
            "net_customer_paid_amount": _money_string(gateway_amount),
            "commissionable_amount": _money_string(quote_snapshot.get("commission_base_amount")),
            "gateway_amount": _money_string(gateway_amount),
            "requires_external_payment": gateway_amount > Decimal("0"),
            "settlement_mode": "internal_zero" if gateway_amount <= Decimal("0") else "external_payment",
        },
    }


def _dict_or_empty(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _money_string(value: object) -> str:
    return str(_decimal_or_zero(value).quantize(Decimal("0.01")))


def _decimal_or_zero(value: object) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    return Decimal(str(value))


def _compact_list(values: list[object]) -> list[str]:
    return [str(value) for value in values if value not in (None, "")]


def _masked_code(code_ref: dict[str, Any]) -> str:
    prefix = str(code_ref.get("code_prefix") or "***")[:12]
    code_hash = str(code_ref.get("code_hash") or "")
    suffix = code_hash[:8] if code_hash else "unknown"
    return f"{prefix}...{suffix}"[:32]


def _code_set_hash(*, quote_snapshot: dict[str, Any], applications: list[dict[str, Any]]) -> str | None:
    existing = quote_snapshot.get("code_set_hash")
    if existing:
        return str(existing)
    if not applications:
        return None
    encoded = json.dumps(applications, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
