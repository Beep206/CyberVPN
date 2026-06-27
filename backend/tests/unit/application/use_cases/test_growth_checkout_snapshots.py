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
RESERVATION_GROUP_ID = "00000000-0000-0000-0000-000000000405"
SECOND_GROWTH_CODE_ID = "00000000-0000-0000-0000-000000000406"
SECOND_RESERVATION_ID = "00000000-0000-0000-0000-000000000407"
CODE_SET_ID = "00000000-0000-0000-0000-000000000408"
RISK_DECISION_ID = "00000000-0000-0000-0000-000000000409"
FX_CONVERSION_ID = "00000000-0000-0000-0000-000000000410"
PRIVATE_GRANT_ID = "00000000-0000-0000-0000-000000000411"
BENEFIT_ID = "00000000-0000-0000-0000-000000000412"


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


def test_v3_snapshot_preserves_multi_application_ledger_and_child_reservation() -> None:
    quote_snapshot = _quote_snapshot()
    first_application = {
        "position_entered": 1,
        "canonical_order": 1,
        "growth_code_id": GROWTH_CODE_ID,
        "masked_code": "PRO...abcdef123456",
        "roles": ["promo"],
        "status": "accepted",
        "policy_version_id": POLICY_VERSION_ID,
        "discount": {
            "source_amount": "10.00",
            "source_currency": "USD",
            "target_amount": "10.00",
            "target_currency": "USD",
            "applied_amount": "10.00",
        },
        "benefits": [],
        "reservation_id": RESERVATION_ID,
    }
    second_application = {
        "position_entered": 0,
        "canonical_order": 0,
        "growth_code_id": SECOND_GROWTH_CODE_ID,
        "masked_code": "FIX...123456abcdef",
        "roles": ["promo"],
        "status": "accepted",
        "policy_version_id": None,
        "discount": {
            "source_amount": "5.00",
            "source_currency": "USD",
            "target_amount": "5.00",
            "target_currency": "USD",
            "applied_amount": "5.00",
        },
        "benefits": [],
        "reservation_id": SECOND_RESERVATION_ID,
    }
    quote_snapshot["code_set_id"] = CODE_SET_ID
    quote_snapshot["reservation_group_id"] = RESERVATION_GROUP_ID
    quote_snapshot["code_set"] = {
        "id": quote_snapshot["code_set_id"],
        "hash": "f" * 64,
        "acceptance_mode": "all_or_nothing",
        "applications": [first_application, second_application],
    }
    quote_snapshot = attach_growth_checkout_integrity(quote_snapshot, producer="test")

    built = build_growth_checkout_v3_snapshot(
        quote_snapshot=quote_snapshot,
        context_snapshot={},
        request_snapshot={"currency": "USD"},
    )
    applications = built["code_set"]["applications"]

    assert built["reservation_group_id"] == RESERVATION_GROUP_ID
    assert built["code_set"]["acceptance_mode"] == "all_or_nothing"
    assert [item["growth_code_id"] for item in applications] == [SECOND_GROWTH_CODE_ID, GROWTH_CODE_ID]

    order = SimpleNamespace(
        pricing_snapshot={"quote": quote_snapshot, "growth_checkout_snapshot": built},
        entitlements_snapshot={},
    )
    result = build_checkout_result_from_order(order)

    assert result.reservation_id == UUID(SECOND_RESERVATION_ID)
    assert all(discount.amount > 0 for discount in result.discounts)


def test_payment_attempt_adapter_preserves_full_v6_application_context() -> None:
    quote_snapshot = _quote_snapshot()
    application = {
        "position_entered": 0,
        "canonical_order": 0,
        "growth_code_id": GROWTH_CODE_ID,
        "masked_code": "PRI...abcdef123456",
        "roles": ["discount", "benefit", "private_access"],
        "status": "accepted",
        "policy_version_id": POLICY_VERSION_ID,
        "rule_checksum": "sha256:rule-v6",
        "discount": {
            "source_amount": "12.00",
            "source_currency": "EUR",
            "target_amount": "13.20",
            "target_currency": "USD",
            "applied_amount": "13.20",
            "fx_conversion_id": FX_CONVERSION_ID,
            "fx_conversion": {
                "source_currency": "EUR",
                "target_currency": "USD",
                "source_amount": "12.00",
                "applied_amount": "13.20",
                "conversion_mode": "market_rate",
                "rate_source": "primary",
                "rate_timestamp": "2026-06-26T00:00:00+00:00",
                "rounding_mode": "ROUND_HALF_UP",
                "no_rerate": True,
                "conversion_checksum": "f" * 64,
            },
        },
        "benefits": [
            {
                "benefit_id": BENEFIT_ID,
                "type": "issue_invites",
                "reversal_policy": "revoke_if_unused",
            }
        ],
        "reservation_id": RESERVATION_ID,
        "reservation_group_id": RESERVATION_GROUP_ID,
        "risk_decision_id": RISK_DECISION_ID,
        "fx_conversion_id": FX_CONVERSION_ID,
        "private_access": {
            "grant_id": PRIVATE_GRANT_ID,
            "status": "granted",
            "target_type": "offer",
        },
        "code_ref": {
            "redacted": True,
            "code_hash": "abcdef1234567890",
            "code_prefix": "PRI",
            "code_length": 15,
        },
    }
    quote_snapshot["code_set_id"] = CODE_SET_ID
    quote_snapshot["code_set_hash"] = "e" * 64
    quote_snapshot["reservation_group_id"] = RESERVATION_GROUP_ID
    quote_snapshot["private_catalog_grant_id"] = PRIVATE_GRANT_ID
    quote_snapshot["private_catalog"] = {
        "grant_id": PRIVATE_GRANT_ID,
        "status": "granted",
        "target_type": "offer",
    }
    quote_snapshot["code_set"] = {
        "id": CODE_SET_ID,
        "hash": "e" * 64,
        "acceptance_mode": "all_or_nothing",
        "applications": [application],
    }
    quote_snapshot = attach_growth_checkout_integrity(quote_snapshot, producer="test")
    built = build_growth_checkout_v3_snapshot(
        quote_snapshot=quote_snapshot,
        context_snapshot={},
        request_snapshot={"currency": "USD"},
    )
    order = SimpleNamespace(
        pricing_snapshot={"quote": quote_snapshot, "growth_checkout_snapshot": built},
        entitlements_snapshot={},
    )

    result = build_checkout_result_from_order(order)

    assert result.code_set_id == UUID(CODE_SET_ID)
    assert result.code_set_hash == "e" * 64
    assert result.reservation_group_id == UUID(RESERVATION_GROUP_ID)
    assert result.private_catalog_grant_id == UUID(PRIVATE_GRANT_ID)
    assert result.code_set_acceptance_mode == "all_or_nothing"
    assert result.growth_checkout_snapshot is not None
    assert result.growth_checkout_snapshot["snapshot_version"] == "growth-checkout.v3"
    assert result.code_set_snapshot["applications"][0]["risk_decision_id"] == RISK_DECISION_ID
    persisted_application = result.code_set_applications[0]
    assert persisted_application["roles"] == ["discount", "benefit", "private_access"]
    assert persisted_application["reservation_id"] == RESERVATION_ID
    assert persisted_application["risk_decision_id"] == RISK_DECISION_ID
    assert persisted_application["fx_conversion_id"] == FX_CONVERSION_ID
    assert persisted_application["discount"]["fx_conversion"]["no_rerate"] is True
    assert persisted_application["private_access"]["grant_id"] == PRIVATE_GRANT_ID
    assert persisted_application["benefits"][0]["benefit_id"] == BENEFIT_ID
    assert "PRIVATE-RAW-CODE" not in str(result.growth_checkout_snapshot)


def test_payment_attempt_adapter_fails_closed_on_malformed_code_set_snapshot() -> None:
    malformed_growth_snapshot = attach_growth_checkout_integrity(
        {
            "snapshot_version": "growth-checkout.v3",
            "code_set": {
                "id": CODE_SET_ID,
                "hash": "e" * 64,
                "acceptance_mode": "all_or_nothing",
                "applications": {"unexpected": "aggregate-only"},
            },
            "private_catalog": {},
            "risk": {"aggregate_action": "allow", "decision_ids": []},
            "fx": {"conversion_ids": []},
            "pricing": {
                "base_price": "100.00",
                "discount_lines": [],
                "total_discount": "0.00",
                "wallet_amount": "0.00",
                "gateway_amount": "100.00",
                "currency": "USD",
                "is_zero_gateway": False,
            },
            "reservation_group_id": RESERVATION_GROUP_ID,
            "growth_effects": {},
        },
        producer="test",
    )
    order = SimpleNamespace(
        pricing_snapshot={"quote": _quote_snapshot(), "growth_checkout_snapshot": malformed_growth_snapshot},
        entitlements_snapshot={},
    )

    with pytest.raises(ValueError, match="SNAPSHOT_INTEGRITY_ERROR"):
        build_checkout_result_from_order(order)


def test_v3_snapshot_builds_private_catalog_application_without_raw_grant_token() -> None:
    quote_snapshot = attach_growth_checkout_integrity(
        {
            "base_price": 100,
            "addon_amount": 0,
            "displayed_price": 100,
            "discount_amount": 0,
            "wallet_amount": 0,
            "gateway_amount": 100,
            "partner_markup": 0,
            "is_zero_gateway": False,
            "plan_id": PLAN_ID,
            "plan_name": "Private",
            "duration_days": 30,
            "commission_base_amount": 100,
            "currency_code": "USD",
            "code_resolution": None,
            "discounts": [],
            "private_catalog_grant_id": PRIVATE_GRANT_ID,
            "private_catalog": {
                "grant_id": PRIVATE_GRANT_ID,
                "policy_version_id": POLICY_VERSION_ID,
                "growth_code_id": GROWTH_CODE_ID,
                "code_set_hash": "c" * 64,
                "status": "issued",
                "allowed_plan_ids": [PLAN_ID],
                "grant_token_hash": None,
            },
            "addons": [],
            "entitlements_snapshot": {"effective_entitlements": {"device_limit": 3}},
        },
        producer="test",
    )

    built = build_growth_checkout_v3_snapshot(
        quote_snapshot=quote_snapshot,
        context_snapshot={},
        request_snapshot={"currency": "USD"},
    )

    application = built["code_set"]["applications"][0]
    assert built["code_set"]["hash"] == "c" * 64
    assert application["growth_code_id"] == GROWTH_CODE_ID
    assert application["roles"] == ["catalog_access"]
    assert application["discount"]["applied_amount"] == "0.00"
    assert application["private_access"]["grant_id"] == PRIVATE_GRANT_ID
    assert application["code_ref"]["redacted"] is True
    assert "grant_token_hash" not in str(built)
    assert "PRIVATE-RAW-CODE" not in str(built)
