from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from src.application.use_cases.growth_code_sets.snapshots import attach_growth_checkout_integrity

ORDER_CODE_APPLICATION_SNAPSHOT_VERSION = "order_code_application.v6"


def build_legacy_quote_application(quote_snapshot: dict[str, Any]) -> dict[str, Any] | None:
    code_resolution = _dict_or_empty(quote_snapshot.get("code_resolution"))
    growth_code_id = _uuid_or_none(code_resolution.get("growth_code_id"))
    if growth_code_id is None or code_resolution.get("accepted") is not True:
        return None

    discount_snapshot = matching_discount_snapshot(quote_snapshot) or {}
    code_ref = safe_code_ref(quote_snapshot, discount_snapshot)
    policy_snapshot = _dict_or_empty(code_resolution.get("policy_snapshot"))
    role = str(code_resolution.get("code_type") or discount_snapshot.get("type") or "growth_code")
    discount = {
        "source_amount": _money_string(discount_snapshot.get("source_amount") or discount_snapshot.get("amount")),
        "source_currency": discount_snapshot.get("source_currency") or quote_snapshot.get("currency_code"),
        "target_amount": _money_string(discount_snapshot.get("target_amount") or discount_snapshot.get("amount")),
        "target_currency": discount_snapshot.get("target_currency") or quote_snapshot.get("currency_code"),
        "applied_amount": _money_string(discount_snapshot.get("applied_amount") or discount_snapshot.get("amount")),
    }
    fx_payload = discount_snapshot.get("fx_conversion")
    if isinstance(fx_payload, dict):
        discount["fx_conversion"] = deepcopy(fx_payload)
    fx_conversion_id = _string_or_none(discount_snapshot.get("fx_conversion_id"))
    if fx_conversion_id is not None:
        discount["fx_conversion_id"] = fx_conversion_id
    return {
        "position_entered": 0,
        "canonical_order": 0,
        "growth_code_id": str(growth_code_id),
        "masked_code": masked_code(code_ref),
        "roles": [role],
        "status": "accepted",
        "policy_version_id": _string_or_none(
            discount_snapshot.get("policy_version_id") or policy_snapshot.get("policy_version_id")
        ),
        "rule_checksum": policy_snapshot.get("rule_checksum"),
        "discount": discount,
        "benefits": deepcopy(policy_snapshot.get("benefits") or []),
        "reservation_id": _string_or_none(code_resolution.get("reservation_id")),
        "risk_decision_id": _string_or_none(code_resolution.get("risk_decision_id")),
        "fx_conversion_id": fx_conversion_id,
        "code_ref": code_ref,
        "legacy_code_type": role,
        "legacy_code_id": _string_or_none(
            code_resolution.get("promo_code_id") or code_resolution.get("partner_code_id")
        ),
        "private_access": deepcopy(quote_snapshot.get("private_catalog") or {}),
        "evaluation_trace": {"source": "quote_snapshot", "schema_version": "single_legacy.v1"},
    }


def attach_code_set_to_quote_snapshot(
    quote_snapshot: dict[str, Any],
    *,
    code_set_id: UUID,
    code_set_hash: str,
    applications: list[dict[str, Any]],
    reservation_group_id: UUID | None,
    acceptance_mode: str,
    producer: str,
) -> dict[str, Any]:
    prepared = deepcopy(quote_snapshot)
    prepared["code_set_id"] = str(code_set_id)
    prepared["code_set_hash"] = code_set_hash
    prepared["reservation_group_id"] = str(reservation_group_id) if reservation_group_id else None
    prepared["code_set"] = {
        "id": str(code_set_id),
        "hash": code_set_hash,
        "acceptance_mode": acceptance_mode,
        "applications": deepcopy(applications),
    }
    code_resolution = _dict_or_empty(prepared.get("code_resolution"))
    if code_resolution:
        code_resolution["reservation_group_id"] = str(reservation_group_id) if reservation_group_id else None
        prepared["code_resolution"] = code_resolution
    return attach_growth_checkout_integrity(prepared, producer=producer)


def code_set_hash_for_applications(applications: list[dict[str, Any]]) -> str:
    if len(applications) == 1:
        application = applications[0]
        code_ref = _dict_or_empty(application.get("code_ref"))
        code_hash = code_ref.get("code_hash") or application.get("growth_code_id")
        return hashlib.sha256(f"single-legacy:{code_hash}".encode()).hexdigest()
    payload = [
        {
            "growth_code_id": application.get("growth_code_id"),
            "code_hash": _dict_or_empty(application.get("code_ref")).get("code_hash"),
            "roles": sorted(str(role) for role in application.get("roles") or []),
            "policy_version_id": application.get("policy_version_id"),
        }
        for application in applications
    ]
    encoded = json.dumps(sorted(payload, key=lambda item: str(item.get("growth_code_id"))), sort_keys=True).encode()
    return hashlib.sha256(encoded).hexdigest()


def accepted_code_set_applications(snapshot: dict[str, Any] | None) -> list[dict[str, Any]]:
    applications = code_set_applications(snapshot)
    return [application for application in applications if str(application.get("status") or "") == "accepted"]


def code_set_applications(snapshot: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(snapshot, dict):
        return []
    code_set = snapshot.get("code_set")
    if not isinstance(code_set, dict):
        return []
    raw_applications = code_set.get("applications")
    if raw_applications in (None, ()):
        return []
    if not isinstance(raw_applications, list):
        raise ValueError("SNAPSHOT_INTEGRITY_ERROR")
    applications: list[dict[str, Any]] = []
    for index, raw_application in enumerate(raw_applications):
        if not isinstance(raw_application, dict):
            raise ValueError("SNAPSHOT_INTEGRITY_ERROR")
        application = deepcopy(raw_application)
        application.setdefault("position_entered", index)
        application.setdefault("canonical_order", index)
        applications.append(application)
    return sorted(
        applications,
        key=lambda item: (
            int(item.get("canonical_order") or 0),
            str(item.get("growth_code_id") or ""),
            str(item.get("reservation_id") or ""),
        ),
    )


def reservation_ids_from_snapshot(snapshot: dict[str, Any] | None) -> list[UUID]:
    ids: list[UUID] = []
    for application in accepted_code_set_applications(snapshot):
        reservation_id = _uuid_or_none(application.get("reservation_id"))
        if reservation_id is not None and reservation_id not in ids:
            ids.append(reservation_id)
    if ids:
        return ids
    code_resolution = _dict_or_empty((snapshot or {}).get("code_resolution") if isinstance(snapshot, dict) else None)
    reservation_id = _uuid_or_none(code_resolution.get("reservation_id"))
    return [reservation_id] if reservation_id is not None else []


def build_order_code_application_snapshot(
    *,
    application: dict[str, Any],
    reservation_group_id: object,
    producer: str,
    created_at: datetime | None = None,
) -> dict[str, Any]:
    immutable_payload = {
        "application": deepcopy(application),
        "reservation_group_id": str(reservation_group_id) if reservation_group_id else None,
    }
    return {
        "snapshot_version": ORDER_CODE_APPLICATION_SNAPSHOT_VERSION,
        **immutable_payload,
        "snapshot_integrity": {
            "schema_version": ORDER_CODE_APPLICATION_SNAPSHOT_VERSION,
            "checksum": _checksum_order_application_payload(immutable_payload),
            "created_at": (created_at or datetime.now(UTC)).isoformat(),
            "producer": producer,
            "required_fields": ["application", "reservation_group_id"],
        },
    }


def matching_discount_snapshot(quote_snapshot: dict[str, Any]) -> dict[str, Any] | None:
    discounts = quote_snapshot.get("discounts")
    if not isinstance(discounts, list):
        return None
    for discount in discounts:
        if isinstance(discount, dict) and Decimal(str(discount.get("amount") or "0")) > 0:
            return deepcopy(discount)
    for discount in discounts:
        if isinstance(discount, dict):
            return deepcopy(discount)
    return None


def safe_code_ref(quote_snapshot: dict[str, Any], discount_snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
    for candidate in (
        (discount_snapshot or {}).get("code_ref"),
        quote_snapshot.get("code_input_ref"),
    ):
        if isinstance(candidate, dict):
            return {
                "redacted": bool(candidate.get("redacted", True)),
                "code_hash": candidate.get("code_hash"),
                "code_prefix": candidate.get("code_prefix"),
                "code_length": candidate.get("code_length"),
            }
    return {"redacted": True, "code_hash": None, "code_prefix": "***", "code_length": None}


def _checksum_order_application_payload(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def masked_code(code_ref: dict[str, Any]) -> str:
    prefix = str(code_ref.get("code_prefix") or "***")[:12]
    code_hash = str(code_ref.get("code_hash") or "")
    suffix = code_hash[:12] if code_hash else "unknown"
    return f"{prefix}...{suffix}"[:32]


def _dict_or_empty(value: object) -> dict[str, Any]:
    return deepcopy(value) if isinstance(value, dict) else {}


def _money_string(value: object) -> str:
    return str(Decimal(str(value or "0")).quantize(Decimal("0.01")))


def _string_or_none(value: object) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def _uuid_or_none(value: object) -> UUID | None:
    if value in (None, ""):
        return None
    return UUID(str(value))
