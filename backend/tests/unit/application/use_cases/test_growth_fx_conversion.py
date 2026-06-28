from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from src.application.use_cases.growth_code_sets.fx import (
    FixedDiscountConversion,
    FxConversionError,
    FxRateSnapshot,
    convert_fixed_discount,
    rate_snapshots_from_policy_snapshot,
)

NOW = datetime(2026, 6, 25, 12, 0, tzinfo=UTC)


def _rate(
    *,
    rate_id: str = "00000000-0000-0000-0000-000000000101",
    provider: str = "primary",
    priority: int = 1,
    source: str = "USD",
    target: str = "RUB",
    rate: str = "92.375",
    fetched_delta_minutes: int = -5,
    expires_delta_minutes: int = 30,
    managed_xtr: bool = False,
    provider_enabled: bool = True,
) -> FxRateSnapshot:
    return FxRateSnapshot(
        rate_id=UUID(rate_id),
        provider=provider,
        provider_priority=priority,
        source_currency=source,
        target_currency=target,
        rate=Decimal(rate),
        fetched_at=NOW + timedelta(minutes=fetched_delta_minutes),
        expires_at=NOW + timedelta(minutes=expires_delta_minutes),
        managed_xtr=managed_xtr,
        provider_enabled=provider_enabled,
    )


def test_fixed_discount_same_currency_uses_decimal_minor_units_without_rate() -> None:
    conversion = convert_fixed_discount(
        source_amount=Decimal("10.005"),
        source_currency="usd",
        quote_currency="USD",
        discountable_amount=Decimal("99.00"),
        rate_snapshots=[],
        now=NOW,
    )

    assert conversion.target_amount == Decimal("10.01")
    assert conversion.applied_amount == Decimal("10.01")
    assert conversion.rate_snapshot is None
    assert conversion.conversion_checksum


def test_fixed_discount_cross_currency_uses_primary_non_stale_rate_snapshot() -> None:
    secondary = _rate(
        rate_id="00000000-0000-0000-0000-000000000202",
        provider="secondary",
        priority=2,
        rate="100",
    )
    primary = _rate(provider="primary", priority=1, rate="92.375")

    conversion = convert_fixed_discount(
        source_amount=Decimal("10.00"),
        source_currency="USD",
        quote_currency="RUB",
        discountable_amount=Decimal("2000.00"),
        rate_snapshots=[secondary, primary],
        now=NOW,
    )

    assert conversion.target_amount == Decimal("923.75")
    assert conversion.applied_amount == Decimal("923.75")
    assert conversion.rate_snapshot is not None
    assert conversion.rate_snapshot["provider"] == "primary"
    assert conversion.rate_snapshot["rate_id"] == str(primary.rate_id)


def test_fixed_discount_caps_at_discountable_amount_and_checksum_is_stable() -> None:
    kwargs = {
        "source_amount": Decimal("10.00"),
        "source_currency": "USD",
        "quote_currency": "RUB",
        "discountable_amount": Decimal("500.00"),
        "rate_snapshots": [_rate()],
        "now": NOW,
    }

    first = convert_fixed_discount(**kwargs)
    second = convert_fixed_discount(**kwargs)

    assert isinstance(first, FixedDiscountConversion)
    assert first.target_amount == Decimal("923.75")
    assert first.applied_amount == Decimal("500.00")
    assert first.conversion_checksum == second.conversion_checksum


def test_fixed_discount_rejects_stale_or_missing_rate() -> None:
    with pytest.raises(FxConversionError) as exc:
        convert_fixed_discount(
            source_amount=Decimal("10.00"),
            source_currency="USD",
            quote_currency="RUB",
            discountable_amount=Decimal("2000.00"),
            rate_snapshots=[_rate(expires_delta_minutes=-1)],
            now=NOW,
        )

    assert exc.value.code == "FX_RATE_UNAVAILABLE"


def test_fixed_discount_rejects_disabled_provider_rate_snapshot() -> None:
    with pytest.raises(FxConversionError) as exc:
        convert_fixed_discount(
            source_amount=Decimal("10.00"),
            source_currency="USD",
            quote_currency="RUB",
            discountable_amount=Decimal("2000.00"),
            rate_snapshots=[_rate(provider="disabled-provider", provider_enabled=False)],
            now=NOW,
        )

    assert exc.value.code == "FX_RATE_UNAVAILABLE"


def test_fixed_discount_requires_managed_xtr_rate() -> None:
    with pytest.raises(FxConversionError) as exc:
        convert_fixed_discount(
            source_amount=Decimal("10.00"),
            source_currency="USD",
            quote_currency="XTR",
            discountable_amount=Decimal("1000"),
            rate_snapshots=[_rate(target="XTR", rate="50", managed_xtr=False)],
            now=NOW,
        )

    assert exc.value.code == "FX_XTR_MANAGED_RATE_REQUIRED"

    conversion = convert_fixed_discount(
        source_amount=Decimal("10.00"),
        source_currency="USD",
        quote_currency="XTR",
        discountable_amount=Decimal("1000"),
        rate_snapshots=[_rate(target="XTR", rate="50", managed_xtr=True)],
        now=NOW,
    )

    assert conversion.target_amount == Decimal("500")
    assert conversion.rate_snapshot is not None
    assert conversion.rate_snapshot["managed_xtr"] is True


def test_policy_snapshot_rate_parser_accepts_nested_versioned_rates() -> None:
    rates = rate_snapshots_from_policy_snapshot(
        {
            "fx": {
                "rate_snapshots": [
                    {
                        "id": "00000000-0000-0000-0000-00000000f012",
                        "provider_key": "pricebook-primary",
                        "priority": 1,
                        "base_currency": "EUR",
                        "quote_currency": "USD",
                        "rate": "1.0835",
                        "observed_at": NOW.isoformat(),
                        "valid_until": (NOW + timedelta(minutes=10)).isoformat(),
                        "source_type": "pricebook",
                        "configured_rate_version": "pb-2026-06-25",
                    }
                ]
            }
        }
    )

    assert len(rates) == 1
    assert rates[0].rate_id == UUID("00000000-0000-0000-0000-00000000f012")
    assert rates[0].source_currency == "EUR"
    assert rates[0].target_currency == "USD"
    assert rates[0].source_type == "pricebook"
    assert rates[0].configured_rate_version == "pb-2026-06-25"


def test_policy_snapshot_rate_parser_rejects_malformed_rate() -> None:
    with pytest.raises(FxConversionError) as exc:
        rate_snapshots_from_policy_snapshot({"fx_rate_snapshots": [{"provider": "primary"}]})

    assert exc.value.code == "FX_RATE_SNAPSHOT_INVALID"
