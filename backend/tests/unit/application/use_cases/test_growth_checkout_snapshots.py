from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID

import pytest

from src.application.use_cases.growth_code_sets.snapshots import (
    SnapshotIntegrityError,
    attach_growth_checkout_integrity,
    build_growth_checkout_v3_snapshot,
    read_growth_checkout_v3_snapshot,
    validate_growth_checkout_integrity,
)
from src.application.use_cases.orders.snapshot_builder import build_order_snapshots
from src.application.use_cases.payment_attempts.snapshot_adapter import build_checkout_result_from_order

PLAN_ID = "00000000-0000-0000-0000-000000000101"
GROWTH_CODE_ID = "00000000-0000-0000-0000-000000000202"
POLICY_VERSION_ID = "00000000-0000-0000-0000-000000000303"
RESERVATION_ID = "00000000-0000-0000-0000-000000000404"


def _quote_snapshot() -> dict:
    return attach_growth_checkout_integrity(
        {
            "base_price": 100,
            "addon_amount": 0,
            "displayed_price": 100,
            "discount_amount": 100,
            "wallet_amount": 0,
            "gateway_amount": 0,
            "partner_markup": 0,
            "is_zero_gateway": True,
            "plan_id": PLAN_ID,
            "plan_name": "Private 100",
            "duration_days": 30,
            "promo_code_id": None,
            "partner_code_id": None,
            "commission_base_amount": 0,
            "currency_code": "USD",
            "code_input": "PRO...abcdef123456",
            "code_input_ref": {
                "redacted": True,
                "code_hash": "abcdef1234567890",
                "code_prefix": "PRO",
                "code_length": 10,
            },
            "code_resolution": {
                "accepted": True,
                "code_type": "promo",
                "action_context": "checkout",
                "result": "accepted",
                "growth_code_id": GROWTH_CODE_ID,
                "reservation_id": RESERVATION_ID,
                "policy_snapshot": {
                    "policy_version_id": POLICY_VERSION_ID,
                    "rule_checksum": "sha256:rule",
                    "benefits": [
                        {
                            "benefit_id": "00000000-0000-0000-0000-000000000505",
                            "type": "issue_invites",
                        }
                    ],
                },
            },
            "discounts": [
                {
                    "type": "promo",
                    "code": "PRO...abcdef123456",
                    "code_ref": {
                        "redacted": True,
                        "code_hash": "abcdef1234567890",
                        "code_prefix": "PRO",
                        "code_length": 10,
                    },
                    "amount": 100,
                    "policy_version_id": POLICY_VERSION_ID,
                }
            ],
            "addons": [],
            "entitlements_snapshot": {"effective_entitlements": {"device_limit": 3}},
        },
        producer="test",
    )


def test_growth_checkout_integrity_rejects_checksum_mutation() -> None:
    snapshot = _quote_snapshot()
    validate_growth_checkout_integrity(snapshot)

    snapshot["discount_amount"] = 90

    with pytest.raises(SnapshotIntegrityError, match="SNAPSHOT_INTEGRITY_ERROR"):
        validate_growth_checkout_integrity(snapshot)


def test_growth_checkout_integrity_rejects_unknown_required_field() -> None:
    snapshot = _quote_snapshot()
    snapshot["snapshot_integrity"]["required_fields"].append("future_required_field")

    with pytest.raises(SnapshotIntegrityError, match="SNAPSHOT_INTEGRITY_ERROR"):
        validate_growth_checkout_integrity(snapshot)


def test_order_snapshot_builder_preserves_v3_growth_snapshot_for_adapter() -> None:
    quote_snapshot = _quote_snapshot()
    merchant, pricing, policy = build_order_snapshots(
        quote_snapshot=quote_snapshot,
        context_snapshot={
            "offer": {"offer_key": "private-100", "display_name": "Private 100"},
            "pricebook": {"currency_code": "USD"},
            "pricebook_entry": {"visible_price": 100},
        },
        request_snapshot={"currency": "USD", "channel": "web"},
    )

    assert merchant["storefront"] == {}
    growth_snapshot = read_growth_checkout_v3_snapshot(pricing)
    assert growth_snapshot is not None
    assert growth_snapshot["snapshot_version"] == "growth-checkout.v3"
    assert growth_snapshot["code_set"]["applications"][0]["growth_code_id"] == GROWTH_CODE_ID
    assert policy["growth_effects"]["reservation_id"] == RESERVATION_ID

    order = SimpleNamespace(
        pricing_snapshot=pricing,
        entitlements_snapshot={"existing": "kept"},
    )
    result = build_checkout_result_from_order(order)

    assert result.is_zero_gateway is True
    assert result.discounts[0].amount == 100
    assert result.discounts[0].policy_version_id == UUID(POLICY_VERSION_ID)
    assert result.reservation_id == UUID(RESERVATION_ID)
    assert (
        result.entitlements_snapshot["growth_checkout_snapshot"]["code_set"]["applications"][0]["policy_version_id"]
        == POLICY_VERSION_ID
    )


def test_legacy_order_snapshot_adapter_remains_backward_compatible() -> None:
    order = SimpleNamespace(
        pricing_snapshot={
            "quote": {
                "base_price": 10,
                "addon_amount": 0,
                "displayed_price": 10,
                "discount_amount": 0,
                "wallet_amount": 0,
                "gateway_amount": 10,
                "partner_markup": 0,
                "is_zero_gateway": False,
                "plan_id": PLAN_ID,
                "duration_days": 30,
                "commission_base_amount": 10,
            }
        },
        entitlements_snapshot={},
    )

    result = build_checkout_result_from_order(order)

    assert result.plan_id == UUID(PLAN_ID)
    assert result.gateway_amount == 10
    assert result.discounts == []


def test_v3_snapshot_builder_uses_canonical_checksum() -> None:
    built = build_growth_checkout_v3_snapshot(
        quote_snapshot=_quote_snapshot(),
        context_snapshot={},
        request_snapshot={"currency": "USD"},
    )

    validate_growth_checkout_integrity(built)
    built["pricing"]["gateway_amount"] = "1.00"

    with pytest.raises(SnapshotIntegrityError, match="SNAPSHOT_INTEGRITY_ERROR"):
        validate_growth_checkout_integrity(built)
