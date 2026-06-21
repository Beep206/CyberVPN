from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import ROUND_DOWN, ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any
from uuid import UUID

from src.infrastructure.database.models.partner_model import PartnerCodeModel, PartnerCommissionContractModel

PARTNER_EARNING_SNAPSHOT_VERSION = "partner_earning_v3"
PARTNER_EARNING_SNAPSHOT_INCOMPLETE_CODE = "PARTNER_EARNING_SNAPSHOT_INCOMPLETE"

_COMMISSION_CONTRACT_NAMESPACE = UUID("b8174d0e-5d20-458a-a03f-9f978d2c6f13")
_ROUNDING_MODES = {
    "ROUND_HALF_UP": ROUND_HALF_UP,
    "ROUND_HALF_EVEN": ROUND_HALF_EVEN,
    "ROUND_DOWN": ROUND_DOWN,
}


class PartnerEarningSnapshotIncompleteError(Exception):
    def __init__(self, missing_terms: list[str]) -> None:
        self.code = PARTNER_EARNING_SNAPSHOT_INCOMPLETE_CODE
        self.missing_terms = sorted(set(missing_terms))
        super().__init__("Partner earning snapshot is incomplete.")


@dataclass(frozen=True)
class PartnerCommissionTerms:
    commission_contract_id: UUID
    partner_account_id: UUID | None
    partner_user_id: UUID | None
    partner_code_id: UUID | None
    owner_type: str
    commission_model: str
    commission_pct: Decimal
    markup_pct: Decimal
    markup_cap_amount: Decimal | None
    payout_hold_days: int
    currency_code: str
    currency_policy: dict[str, Any]
    rounding_mode: str
    renewal_policy: dict[str, Any]
    refund_policy: dict[str, Any]
    contract_version: int
    contract_status: str
    snapshot: dict[str, Any]


def deterministic_commission_contract_id(partner_code_id: UUID) -> UUID:
    return uuid.uuid5(_COMMISSION_CONTRACT_NAMESPACE, f"partner_code:{partner_code_id}:commission-contract:v1")


def build_commission_contract_model(
    *,
    code_model: PartnerCodeModel,
    commission_pct: Decimal,
    payout_hold_days: int,
    source: str,
    now: datetime | None = None,
    currency_code: str = "USD",
    contract_id: UUID | None = None,
) -> PartnerCommissionContractModel:
    effective_from = _coerce_utc(now or datetime.now(UTC))
    contract = PartnerCommissionContractModel(
        id=contract_id or deterministic_commission_contract_id(code_model.id),
        partner_account_id=code_model.partner_account_id,
        partner_user_id=code_model.partner_user_id,
        partner_code_id=code_model.id,
        owner_type=str(code_model.owner_type or "affiliate"),
        contract_status="active",
        commission_model="base_plus_markup",
        commission_pct=_decimal(commission_pct, field="commission_pct"),
        markup_pct=_decimal(code_model.markup_pct or 0, field="markup_pct"),
        markup_cap_amount=None,
        payout_hold_days=max(int(payout_hold_days), 0),
        currency_code=_normalize_currency(currency_code),
        currency_policy={"minor_unit": 2},
        rounding_mode="ROUND_HALF_UP",
        renewal_policy={"eligible": True, "source": source},
        refund_policy={"clawback": "manual_review", "source": source},
        source=source,
        version=int(code_model.version or 1),
        effective_from=effective_from,
    )
    contract.terms_snapshot = build_commission_contract_snapshot(contract, snapshot_source=source)
    return contract


def build_commission_contract_snapshot(
    contract: PartnerCommissionContractModel,
    *,
    snapshot_source: str = "contract_row",
    currency_code: str | None = None,
) -> dict[str, Any]:
    normalized_currency = _normalize_currency(currency_code or contract.currency_code)
    snapshot = {
        "calculation_version": PARTNER_EARNING_SNAPSHOT_VERSION,
        "commission_contract_id": str(contract.id),
        "commission_model": contract.commission_model,
        "commission_pct": _decimal_string(contract.commission_pct),
        "markup_pct": _decimal_string(contract.markup_pct),
        "markup_cap_amount": (
            _decimal_string(contract.markup_cap_amount) if contract.markup_cap_amount is not None else None
        ),
        "payout_hold_days": int(contract.payout_hold_days),
        "currency_code": normalized_currency,
        "currency_policy": _currency_policy(normalized_currency),
        "rounding_mode": contract.rounding_mode or "ROUND_HALF_UP",
        "renewal_policy": dict(contract.renewal_policy or {}),
        "refund_policy": dict(contract.refund_policy or {}),
        "contract_version": int(contract.version or 1),
        "contract_status": contract.contract_status,
        "effective_from": _iso_or_none(contract.effective_from),
        "effective_to": _iso_or_none(contract.effective_to),
        "partner_account_id": str(contract.partner_account_id) if contract.partner_account_id else None,
        "partner_user_id": str(contract.partner_user_id) if contract.partner_user_id else None,
        "partner_code_id": str(contract.partner_code_id) if contract.partner_code_id else None,
        "owner_type": contract.owner_type,
        "snapshot_complete": True,
        "missing_terms": [],
        "snapshot_source": snapshot_source,
    }
    return snapshot


def build_commission_contract_snapshot_for_code(
    *,
    code_model: PartnerCodeModel,
    commission_pct: Decimal,
    payout_hold_days: int,
    snapshot_source: str,
    contract_id: UUID | None = None,
    currency_code: str = "USD",
    now: datetime | None = None,
) -> dict[str, Any]:
    effective_from = _coerce_utc(now or datetime.now(UTC))
    resolved_contract_id = (
        contract_id
        or getattr(code_model, "commission_contract_id", None)
        or deterministic_commission_contract_id(code_model.id)
    )
    markup_pct = _decimal(getattr(code_model, "markup_pct", 0), field="markup_pct")
    normalized_currency = _normalize_currency(currency_code)
    return {
        "calculation_version": PARTNER_EARNING_SNAPSHOT_VERSION,
        "commission_contract_id": str(resolved_contract_id),
        "commission_model": "base_plus_markup",
        "commission_pct": _decimal_string(commission_pct),
        "markup_pct": _decimal_string(markup_pct),
        "markup_cap_amount": None,
        "payout_hold_days": max(int(payout_hold_days), 0),
        "currency_code": normalized_currency,
        "currency_policy": _currency_policy(normalized_currency),
        "rounding_mode": "ROUND_HALF_UP",
        "renewal_policy": {"eligible": True, "source": snapshot_source},
        "refund_policy": {"clawback": "manual_review", "source": snapshot_source},
        "contract_version": int(getattr(code_model, "version", 1) or 1),
        "contract_status": "active",
        "effective_from": effective_from.isoformat(),
        "effective_to": None,
        "partner_account_id": str(code_model.partner_account_id)
        if getattr(code_model, "partner_account_id", None)
        else None,
        "partner_user_id": str(code_model.partner_user_id) if getattr(code_model, "partner_user_id", None) else None,
        "partner_code_id": str(code_model.id),
        "owner_type": str(getattr(code_model, "owner_type", None) or "affiliate"),
        "snapshot_complete": True,
        "missing_terms": [],
        "snapshot_source": snapshot_source,
    }


def build_incomplete_commission_contract_snapshot(
    *,
    missing_terms: list[str],
    snapshot_source: str,
    commission_contract_id: UUID | None = None,
    partner_account_id: UUID | None = None,
    partner_user_id: UUID | None = None,
    partner_code_id: UUID | None = None,
    owner_type: str | None = None,
) -> dict[str, Any]:
    return {
        "calculation_version": PARTNER_EARNING_SNAPSHOT_VERSION,
        "commission_contract_id": str(commission_contract_id) if commission_contract_id else None,
        "partner_account_id": str(partner_account_id) if partner_account_id else None,
        "partner_user_id": str(partner_user_id) if partner_user_id else None,
        "partner_code_id": str(partner_code_id) if partner_code_id else None,
        "owner_type": owner_type,
        "snapshot_complete": False,
        "missing_terms": sorted(set(missing_terms)),
        "snapshot_source": snapshot_source,
    }


def attach_commission_contract_snapshot(
    policy_snapshot: dict[str, Any],
    snapshot: dict[str, Any] | None,
) -> dict[str, Any]:
    next_snapshot = dict(policy_snapshot or {})
    if snapshot:
        next_snapshot["commission_contract_snapshot"] = dict(snapshot)
    return next_snapshot


def with_commission_snapshot_currency(snapshot: dict[str, Any], *, currency_code: str) -> dict[str, Any]:
    normalized_currency = _normalize_currency(currency_code)
    next_snapshot = dict(snapshot or {})
    next_snapshot["currency_code"] = normalized_currency
    next_snapshot["currency_policy"] = _currency_policy(normalized_currency)
    return next_snapshot


def extract_partner_commission_terms(
    policy_snapshot: dict[str, Any] | None,
    *,
    expected_partner_account_id: UUID | None,
    expected_partner_user_id: UUID | None,
    expected_partner_code_id: UUID | None,
    expected_owner_type: str | None,
    expected_commission_contract_id: UUID | None,
) -> PartnerCommissionTerms:
    commercial_snapshot = dict((policy_snapshot or {}).get("commercial_policy_snapshot") or {})
    terms_snapshot = dict(commercial_snapshot.get("commission_contract_snapshot") or {})
    missing: list[str] = []
    if not terms_snapshot:
        missing.append("commission_contract_snapshot")
    if terms_snapshot.get("calculation_version") != PARTNER_EARNING_SNAPSHOT_VERSION:
        missing.append("calculation_version")
    if terms_snapshot.get("snapshot_complete") is not True:
        missing.extend(_list_strings(terms_snapshot.get("missing_terms")) or ["snapshot_complete"])

    contract_id = _uuid_value(terms_snapshot.get("commission_contract_id"), "commission_contract_id", missing)
    commission_pct = _decimal_value(terms_snapshot.get("commission_pct"), "commission_pct", missing)
    markup_pct = _decimal_value(terms_snapshot.get("markup_pct"), "markup_pct", missing)
    markup_cap_amount = _optional_decimal_value(terms_snapshot.get("markup_cap_amount"), "markup_cap_amount", missing)
    payout_hold_days = _int_value(terms_snapshot.get("payout_hold_days"), "payout_hold_days", missing)
    currency_code = str(terms_snapshot.get("currency_code") or "").upper()
    if not currency_code:
        missing.append("currency_code")
        currency_code = "USD"
    currency_policy = terms_snapshot.get("currency_policy")
    if not isinstance(currency_policy, dict):
        missing.append("currency_policy")
        currency_policy = {"minor_unit": 2}
    rounding_mode = str(terms_snapshot.get("rounding_mode") or "")
    if rounding_mode not in _ROUNDING_MODES:
        missing.append("rounding_mode")
        rounding_mode = "ROUND_HALF_UP"
    renewal_policy = terms_snapshot.get("renewal_policy")
    if not isinstance(renewal_policy, dict):
        missing.append("renewal_policy")
        renewal_policy = {}
    refund_policy = terms_snapshot.get("refund_policy")
    if not isinstance(refund_policy, dict):
        missing.append("refund_policy")
        refund_policy = {}
    commission_model = str(terms_snapshot.get("commission_model") or "")
    if not commission_model:
        missing.append("commission_model")

    partner_account_id = _optional_uuid_value(terms_snapshot.get("partner_account_id"), "partner_account_id", missing)
    partner_user_id = _optional_uuid_value(terms_snapshot.get("partner_user_id"), "partner_user_id", missing)
    partner_code_id = _optional_uuid_value(terms_snapshot.get("partner_code_id"), "partner_code_id", missing)
    owner_type = str(terms_snapshot.get("owner_type") or "")

    _expect_uuid("partner_account_id", partner_account_id, expected_partner_account_id, missing)
    _expect_uuid("partner_user_id", partner_user_id, expected_partner_user_id, missing)
    _expect_uuid("partner_code_id", partner_code_id, expected_partner_code_id, missing)
    _expect_uuid("commission_contract_id", contract_id, expected_commission_contract_id, missing)
    if expected_owner_type and owner_type != expected_owner_type:
        missing.append("owner_type_mismatch")

    contract_status = str(terms_snapshot.get("contract_status") or "")
    if contract_status != "active":
        missing.append("contract_status")
    contract_version = _int_value(terms_snapshot.get("contract_version"), "contract_version", missing)

    if missing:
        raise PartnerEarningSnapshotIncompleteError(missing)

    return PartnerCommissionTerms(
        commission_contract_id=contract_id,
        partner_account_id=partner_account_id,
        partner_user_id=partner_user_id,
        partner_code_id=partner_code_id,
        owner_type=owner_type,
        commission_model=commission_model,
        commission_pct=commission_pct,
        markup_pct=markup_pct,
        markup_cap_amount=markup_cap_amount,
        payout_hold_days=max(payout_hold_days, 0),
        currency_code=currency_code,
        currency_policy=dict(currency_policy),
        rounding_mode=rounding_mode,
        renewal_policy=dict(renewal_policy),
        refund_policy=dict(refund_policy),
        contract_version=contract_version,
        contract_status=contract_status,
        snapshot=dict(terms_snapshot),
    )


def calculate_partner_earning_amounts(
    *,
    base_amount: Decimal,
    terms: PartnerCommissionTerms,
) -> dict[str, Decimal]:
    rounded_base = round_currency_amount(base_amount, terms.currency_code, terms.currency_policy, terms.rounding_mode)
    raw_markup = rounded_base * (terms.markup_pct / Decimal("100"))
    markup_amount = round_currency_amount(raw_markup, terms.currency_code, terms.currency_policy, terms.rounding_mode)
    if terms.markup_cap_amount is not None:
        cap = round_currency_amount(
            terms.markup_cap_amount,
            terms.currency_code,
            terms.currency_policy,
            terms.rounding_mode,
        )
        markup_amount = min(markup_amount, cap)
    commission_amount = round_currency_amount(
        rounded_base * (terms.commission_pct / Decimal("100")),
        terms.currency_code,
        terms.currency_policy,
        terms.rounding_mode,
    )
    total_amount = round_currency_amount(
        markup_amount + commission_amount,
        terms.currency_code,
        terms.currency_policy,
        terms.rounding_mode,
    )
    return {
        "commission_base_amount": rounded_base,
        "markup_amount": markup_amount,
        "commission_amount": commission_amount,
        "total_amount": total_amount,
    }


def round_currency_amount(
    amount: Decimal,
    currency_code: str,
    currency_policy: dict[str, Any] | None,
    rounding_mode: str,
) -> Decimal:
    minor_unit = int((currency_policy or {}).get("minor_unit", 2))
    if minor_unit < 0 or minor_unit > 8:
        minor_unit = 2
    quant = Decimal("1").scaleb(-minor_unit)
    rounding = _ROUNDING_MODES.get(rounding_mode, ROUND_HALF_UP)
    _ = currency_code
    return _decimal(amount, field="amount").quantize(quant, rounding=rounding)


def _decimal(value: object, *, field: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field} must be decimal-compatible") from exc


def _decimal_value(value: object, field: str, missing: list[str]) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        missing.append(field)
        return Decimal("0")


def _optional_decimal_value(value: object, field: str, missing: list[str]) -> Decimal | None:
    if value is None:
        return None
    return _decimal_value(value, field, missing)


def _decimal_string(value: object) -> str:
    return format(_decimal(value, field="decimal"), "f")


def _int_value(value: object, field: str, missing: list[str]) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        missing.append(field)
        return 0


def _uuid_value(value: object, field: str, missing: list[str]) -> UUID:
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        missing.append(field)
        return UUID(int=0)


def _optional_uuid_value(value: object, field: str, missing: list[str]) -> UUID | None:
    if value in {None, ""}:
        return None
    return _uuid_value(value, field, missing)


def _expect_uuid(field: str, actual: UUID | None, expected: UUID | None, missing: list[str]) -> None:
    if expected is None:
        return
    if actual != expected:
        missing.append(f"{field}_mismatch")


def _list_strings(value: object) -> list[str]:
    if not isinstance(value, list | tuple | set):
        return []
    return [str(item) for item in value if str(item)]


def _normalize_currency(value: object) -> str:
    normalized = str(value or "USD").upper()
    return normalized or "USD"


def _currency_policy(currency_code: str) -> dict[str, Any]:
    minor_unit_by_currency = {
        "XTR": 0,
        "USD": 2,
        "EUR": 2,
        "RUB": 2,
    }
    return {"minor_unit": minor_unit_by_currency.get(_normalize_currency(currency_code), 2)}


def _coerce_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _iso_or_none(value: datetime | None) -> str | None:
    return _coerce_utc(value).isoformat() if value is not None else None
