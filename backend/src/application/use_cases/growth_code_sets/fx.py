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
    ]
    if not candidates:
        raise FxConversionError("FX_RATE_UNAVAILABLE")
    return sorted(
        candidates,
        key=lambda item: (item.provider_priority, -_normalize_utc(item.fetched_at).timestamp()),
    )[0]


def _round_minor(amount: Decimal, currency: str) -> Decimal:
    minor_units = MINOR_UNITS.get(currency, 2)
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


def _iso_utc(value: datetime) -> str:
    return _normalize_utc(value).isoformat()


def _checksum(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
