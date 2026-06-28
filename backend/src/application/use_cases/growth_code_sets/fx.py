"""Immutable FX conversion helpers for Growth Codes v6 fixed discounts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from uuid import UUID

MINOR_UNITS = {
    "USD": 2,
    "EUR": 2,
    "RUB": 2,
    "GBP": 2,
    "JPY": 0,
    "KRW": 0,
    "XTR": 0,
}


class FxConversionError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class FxRateSnapshot:
    rate_id: UUID
    provider: str
    provider_priority: int
    source_currency: str
    target_currency: str
    rate: Decimal
    fetched_at: datetime
    expires_at: datetime
    rounding_mode: str = "ROUND_HALF_UP"
    managed_xtr: bool = False
    source_type: str = "provider"
    configured_rate_version: str | None = None
    provider_enabled: bool = True

    def to_payload(self) -> dict[str, Any]:
        return {
            "rate_id": str(self.rate_id),
            "provider": self.provider,
            "provider_priority": self.provider_priority,
            "source_currency": self.source_currency,
            "target_currency": self.target_currency,
            "rate": str(self.rate),
            "fetched_at": _iso_utc(self.fetched_at),
            "expires_at": _iso_utc(self.expires_at),
            "rounding_mode": self.rounding_mode,
            "managed_xtr": self.managed_xtr,
            "source_type": self.source_type,
            "configured_rate_version": self.configured_rate_version,
            "provider_enabled": self.provider_enabled,
        }


@dataclass(frozen=True)
class FixedDiscountConversion:
    source_amount: Decimal
    source_currency: str
    target_amount: Decimal
    target_currency: str
    applied_amount: Decimal
    rate_snapshot: dict[str, Any] | None
    conversion_checksum: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "source_amount": str(self.source_amount),
            "source_currency": self.source_currency,
            "target_amount": str(self.target_amount),
            "target_currency": self.target_currency,
            "applied_amount": str(self.applied_amount),
            "rate_snapshot": self.rate_snapshot,
            "conversion_checksum": self.conversion_checksum,
        }


def convert_fixed_discount(
    *,
    source_amount: Decimal,
    source_currency: str,
    quote_currency: str,
    discountable_amount: Decimal,
    rate_snapshots: list[FxRateSnapshot],
    now: datetime | None = None,
) -> FixedDiscountConversion:
    """Convert a fixed discount once and return an immutable conversion snapshot."""

    source_currency = _normalize_currency(source_currency)
    quote_currency = _normalize_currency(quote_currency)
    if source_amount < Decimal("0") or discountable_amount < Decimal("0"):
        raise FxConversionError("FX_AMOUNT_NEGATIVE")
    now_utc = _normalize_utc(now or datetime.now(UTC))
    if source_currency == quote_currency:
        target_amount = _round_minor(source_amount, quote_currency)
        applied_amount = min(target_amount, _round_minor(discountable_amount, quote_currency))
        payload: dict[str, Any] = {
            "source_amount": str(source_amount),
            "source_currency": source_currency,
            "target_amount": str(target_amount),
            "target_currency": quote_currency,
            "applied_amount": str(applied_amount),
            "rate_snapshot": None,
        }
        return FixedDiscountConversion(
            source_amount=source_amount,
            source_currency=source_currency,
            target_amount=target_amount,
            target_currency=quote_currency,
            applied_amount=applied_amount,
            rate_snapshot=None,
            conversion_checksum=_checksum(payload),
        )

    rate = _select_rate(
        source_currency=source_currency,
        target_currency=quote_currency,
        rate_snapshots=rate_snapshots,
        now=now_utc,
    )
    if "XTR" in {source_currency, quote_currency} and not rate.managed_xtr:
        raise FxConversionError("FX_XTR_MANAGED_RATE_REQUIRED")
    target_amount = _round_minor(source_amount * rate.rate, quote_currency)
    applied_amount = min(target_amount, _round_minor(discountable_amount, quote_currency))
    rate_payload = rate.to_payload()
    conversion_payload: dict[str, Any] = {
        "source_amount": str(source_amount),
        "source_currency": source_currency,
        "target_amount": str(target_amount),
        "target_currency": quote_currency,
        "applied_amount": str(applied_amount),
        "rate_snapshot": rate_payload,
    }
    return FixedDiscountConversion(
        source_amount=source_amount,
        source_currency=source_currency,
        target_amount=target_amount,
        target_currency=quote_currency,
        applied_amount=applied_amount,
        rate_snapshot=rate_payload,
        conversion_checksum=_checksum(conversion_payload),
    )


def rate_snapshots_from_policy_snapshot(snapshot: dict[str, Any] | None) -> list[FxRateSnapshot]:
    """Parse versioned FX rate snapshots embedded in a policy snapshot."""

    payloads = _rate_payloads_from_snapshot(snapshot or {})
    rates: list[FxRateSnapshot] = []
    for payload in payloads:
        if not isinstance(payload, dict):
            raise FxConversionError("FX_RATE_SNAPSHOT_INVALID")
        rate_id = payload.get("rate_id") or payload.get("id") or payload.get("fx_rate_snapshot_id")
        provider = payload.get("provider") or payload.get("provider_key") or payload.get("source")
        source_currency = payload.get("source_currency") or payload.get("base_currency")
        target_currency = payload.get("target_currency") or payload.get("quote_currency")
        fetched_at = payload.get("fetched_at") or payload.get("observed_at")
        expires_at = payload.get("expires_at") or payload.get("valid_until")
        if not all((rate_id, provider, source_currency, target_currency, payload.get("rate"), fetched_at, expires_at)):
            raise FxConversionError("FX_RATE_SNAPSHOT_INVALID")
        rates.append(
            FxRateSnapshot(
                rate_id=UUID(str(rate_id)),
                provider=str(provider),
                provider_priority=_positive_int(
                    payload.get("provider_priority") or payload.get("priority"), default=100
                ),
                source_currency=_normalize_currency(str(source_currency)),
                target_currency=_normalize_currency(str(target_currency)),
                rate=Decimal(str(payload["rate"])),
                fetched_at=_parse_datetime(str(fetched_at)),
                expires_at=_parse_datetime(str(expires_at)),
                rounding_mode=str(payload.get("rounding_mode") or "ROUND_HALF_UP"),
                managed_xtr=bool(payload.get("managed_xtr")),
                source_type=str(payload.get("source_type") or payload.get("conversion_mode") or "provider"),
                configured_rate_version=(
                    str(payload.get("configured_rate_version"))
                    if payload.get("configured_rate_version") not in (None, "")
                    else None
                ),
                provider_enabled=bool(payload.get("provider_enabled", True)),
            )
        )
    return rates


def conversion_mode_from_payload(rate_snapshot: dict[str, Any] | None) -> str:
    if rate_snapshot is None:
        return "same_currency"
    source_type = str(rate_snapshot.get("source_type") or "").strip().lower()
    if source_type in {"configured", "pricebook", "provider", "managed_xtr"}:
        return source_type
    return "market"


def minor_units_for_currency(currency: str) -> int:
    return MINOR_UNITS.get(_normalize_currency(currency), 2)


def _select_rate(
    *,
    source_currency: str,
    target_currency: str,
    rate_snapshots: list[FxRateSnapshot],
    now: datetime,
) -> FxRateSnapshot:
    candidates = [
        rate
        for rate in rate_snapshots
        if _normalize_currency(rate.source_currency) == source_currency
        and _normalize_currency(rate.target_currency) == target_currency
        and _normalize_utc(rate.fetched_at) <= now
        and _normalize_utc(rate.expires_at) >= now
        and (rate.source_type != "provider" or rate.provider_enabled)
    ]
    if not candidates:
        raise FxConversionError("FX_RATE_UNAVAILABLE")
    return sorted(
        candidates,
        key=lambda item: (item.provider_priority, -_normalize_utc(item.fetched_at).timestamp()),
    )[0]


def _round_minor(amount: Decimal, currency: str) -> Decimal:
    minor_units = minor_units_for_currency(currency)
    quant = Decimal("1") if minor_units == 0 else Decimal("1").scaleb(-minor_units)
    return amount.quantize(quant, rounding=ROUND_HALF_UP)


def _normalize_currency(value: str) -> str:
    normalized = value.strip().upper()
    if len(normalized) < 3 or len(normalized) > 12:
        raise FxConversionError("FX_CURRENCY_INVALID")
    return normalized


def _normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _parse_datetime(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise FxConversionError("FX_RATE_SNAPSHOT_INVALID") from exc
    return _normalize_utc(parsed)


def _iso_utc(value: datetime) -> str:
    return _normalize_utc(value).isoformat()


def _checksum(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _rate_payloads_from_snapshot(snapshot: dict[str, Any]) -> list[Any]:
    direct = snapshot.get("fx_rate_snapshots")
    if isinstance(direct, list):
        return direct
    fx_payload = snapshot.get("fx")
    if isinstance(fx_payload, dict):
        nested = fx_payload.get("rate_snapshots") or fx_payload.get("rates")
        if isinstance(nested, list):
            return nested
    return []


def _positive_int(value: object, *, default: int) -> int:
    if value in (None, ""):
        return default
    if isinstance(value, bool) or not isinstance(value, int | str | bytes | bytearray):
        raise FxConversionError("FX_RATE_SNAPSHOT_INVALID")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise FxConversionError("FX_RATE_SNAPSHOT_INVALID") from exc
    if parsed <= 0:
        raise FxConversionError("FX_RATE_SNAPSHOT_INVALID")
    return parsed
