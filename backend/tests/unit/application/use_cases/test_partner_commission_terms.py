from __future__ import annotations

import uuid
from decimal import Decimal

import pytest

from src.application.use_cases.settlement.commission_terms import (
    PARTNER_EARNING_SNAPSHOT_INCOMPLETE_CODE,
    PartnerCommissionTerms,
    PartnerEarningSnapshotIncompleteError,
    calculate_partner_earning_amounts,
    extract_partner_commission_terms,
    round_currency_amount,
)


def _policy_snapshot(
    *,
    account_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    code_id: uuid.UUID | None = None,
    contract_id: uuid.UUID | None = None,
    overrides: dict[str, object] | None = None,
) -> tuple[dict, uuid.UUID | None, uuid.UUID | None, uuid.UUID | None, uuid.UUID]:
    resolved_contract_id = contract_id or uuid.uuid4()
    snapshot = {
        "calculation_version": "partner_earning_v3",
        "commission_contract_id": str(resolved_contract_id),
        "commission_model": "base_plus_markup",
        "commission_pct": "7.50",
        "markup_pct": "12.50",
        "markup_cap_amount": None,
        "payout_hold_days": 17,
        "currency_code": "USD",
        "currency_policy": {"minor_unit": 2},
        "rounding_mode": "ROUND_HALF_UP",
        "renewal_policy": {"eligible": True},
        "refund_policy": {"clawback": "manual_review"},
        "contract_version": 3,
        "contract_status": "active",
        "partner_account_id": str(account_id) if account_id else None,
        "partner_user_id": str(user_id) if user_id else None,
        "partner_code_id": str(code_id) if code_id else None,
        "owner_type": "affiliate",
        "snapshot_complete": True,
        "missing_terms": [],
    }
    snapshot.update(overrides or {})
    return (
        {"commercial_policy_snapshot": {"commission_contract_snapshot": snapshot}},
        account_id,
        user_id,
        code_id,
        resolved_contract_id,
    )


def test_extract_partner_commission_terms_calculates_with_decimal_rounding() -> None:
    account_id = uuid.uuid4()
    user_id = uuid.uuid4()
    code_id = uuid.uuid4()
    policy_snapshot, _, _, _, contract_id = _policy_snapshot(
        account_id=account_id,
        user_id=user_id,
        code_id=code_id,
    )

    terms = extract_partner_commission_terms(
        policy_snapshot,
        expected_partner_account_id=account_id,
        expected_partner_user_id=user_id,
        expected_partner_code_id=code_id,
        expected_owner_type="affiliate",
        expected_commission_contract_id=contract_id,
    )
    amounts = calculate_partner_earning_amounts(base_amount=Decimal("19.995"), terms=terms)

    assert amounts["commission_base_amount"] == Decimal("20.00")
    assert amounts["markup_amount"] == Decimal("2.50")
    assert amounts["commission_amount"] == Decimal("1.50")
    assert amounts["total_amount"] == Decimal("4.00")


def test_extract_partner_commission_terms_fails_closed_for_missing_snapshot() -> None:
    with pytest.raises(PartnerEarningSnapshotIncompleteError) as exc_info:
        extract_partner_commission_terms(
            {"commercial_policy_snapshot": {}},
            expected_partner_account_id=None,
            expected_partner_user_id=None,
            expected_partner_code_id=uuid.uuid4(),
            expected_owner_type="affiliate",
            expected_commission_contract_id=uuid.uuid4(),
        )

    exc = exc_info.value
    assert exc.code == PARTNER_EARNING_SNAPSHOT_INCOMPLETE_CODE
    assert "commission_contract_snapshot" in exc.missing_terms


@pytest.mark.parametrize(
    ("overrides", "expected_missing"),
    [
        ({"snapshot_complete": False, "missing_terms": ["commission_pct"]}, "commission_pct"),
        ({"contract_status": "revoked"}, "contract_status"),
        ({"rounding_mode": "ROUND_HALF_AWAY"}, "rounding_mode"),
        ({"currency_policy": None}, "currency_policy"),
        ({"commission_pct": None}, "commission_pct"),
        ({"markup_pct": "not-a-decimal"}, "markup_pct"),
    ],
)
def test_extract_partner_commission_terms_fails_closed_for_malformed_snapshot(
    overrides: dict[str, object],
    expected_missing: str,
) -> None:
    account_id = uuid.uuid4()
    user_id = uuid.uuid4()
    code_id = uuid.uuid4()
    policy_snapshot, _, _, _, contract_id = _policy_snapshot(
        account_id=account_id,
        user_id=user_id,
        code_id=code_id,
        overrides=overrides,
    )

    with pytest.raises(PartnerEarningSnapshotIncompleteError) as exc_info:
        extract_partner_commission_terms(
            policy_snapshot,
            expected_partner_account_id=account_id,
            expected_partner_user_id=user_id,
            expected_partner_code_id=code_id,
            expected_owner_type="affiliate",
            expected_commission_contract_id=contract_id,
        )

    assert expected_missing in exc_info.value.missing_terms


@pytest.mark.parametrize(
    ("expectation", "expected_missing"),
    [
        ("partner_account_id", "partner_account_id_mismatch"),
        ("partner_user_id", "partner_user_id_mismatch"),
        ("partner_code_id", "partner_code_id_mismatch"),
        ("commission_contract_id", "commission_contract_id_mismatch"),
        ("owner_type", "owner_type_mismatch"),
    ],
)
def test_extract_partner_commission_terms_fails_closed_for_identity_mismatch(
    expectation: str,
    expected_missing: str,
) -> None:
    account_id = uuid.uuid4()
    user_id = uuid.uuid4()
    code_id = uuid.uuid4()
    policy_snapshot, _, _, _, contract_id = _policy_snapshot(
        account_id=account_id,
        user_id=user_id,
        code_id=code_id,
    )

    with pytest.raises(PartnerEarningSnapshotIncompleteError) as exc_info:
        extract_partner_commission_terms(
            policy_snapshot,
            expected_partner_account_id=uuid.uuid4() if expectation == "partner_account_id" else account_id,
            expected_partner_user_id=uuid.uuid4() if expectation == "partner_user_id" else user_id,
            expected_partner_code_id=uuid.uuid4() if expectation == "partner_code_id" else code_id,
            expected_owner_type="performance" if expectation == "owner_type" else "affiliate",
            expected_commission_contract_id=uuid.uuid4() if expectation == "commission_contract_id" else contract_id,
        )

    assert expected_missing in exc_info.value.missing_terms


@pytest.mark.parametrize(
    ("minor_unit", "rounding_mode", "currency_code", "amount", "expected"),
    [
        (0, "ROUND_HALF_UP", "XTR", "19.5", Decimal("20")),
        (0, "ROUND_HALF_EVEN", "XTR", "20.5", Decimal("20")),
        (2, "ROUND_DOWN", "USD", "19.999", Decimal("19.99")),
        (2, "ROUND_HALF_UP", "EUR", "19.995", Decimal("20.00")),
        (6, "ROUND_HALF_UP", "USD", "1.2345675", Decimal("1.234568")),
        (8, "ROUND_HALF_UP", "USD", "0.123456785", Decimal("0.12345679")),
    ],
)
def test_round_currency_amount_honors_minor_units_and_rounding_modes(
    minor_unit: int,
    rounding_mode: str,
    currency_code: str,
    amount: str,
    expected: Decimal,
) -> None:
    assert (
        round_currency_amount(
            Decimal(amount),
            currency_code,
            {"minor_unit": minor_unit},
            rounding_mode,
        )
        == expected
    )


def test_calculate_partner_earning_amounts_applies_markup_cap_with_decimal_precision() -> None:
    terms = PartnerCommissionTerms(
        commission_contract_id=uuid.uuid4(),
        partner_account_id=None,
        partner_user_id=uuid.uuid4(),
        partner_code_id=uuid.uuid4(),
        owner_type="affiliate",
        commission_model="base_plus_markup",
        commission_pct=Decimal("1.25"),
        markup_pct=Decimal("50"),
        markup_cap_amount=Decimal("3.33333333"),
        payout_hold_days=0,
        currency_code="XTR",
        currency_policy={"minor_unit": 8},
        rounding_mode="ROUND_HALF_UP",
        renewal_policy={},
        refund_policy={},
        contract_version=1,
        contract_status="active",
        snapshot={},
    )

    amounts = calculate_partner_earning_amounts(base_amount=Decimal("10.000000005"), terms=terms)

    assert amounts["commission_base_amount"] == Decimal("10.00000001")
    assert amounts["markup_amount"] == Decimal("3.33333333")
    assert amounts["commission_amount"] == Decimal("0.12500000")
    assert amounts["total_amount"] == Decimal("3.45833333")
