from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from pydantic import SecretStr

from src.application.use_cases.commerce_sessions.quote_serialization import (
    build_request_snapshot,
    restore_protected_request_code,
    serialize_checkout_result,
)
from src.application.use_cases.payments.checkout import CheckoutAppliedDiscount, CheckoutResult
from src.config.settings import settings
from src.shared.security import encryption


def test_quote_snapshots_redact_raw_checkout_codes(monkeypatch) -> None:
    monkeypatch.setattr(encryption, "_oauth_token_encryption_service", None)
    monkeypatch.setattr(settings, "oauth_token_encryption_key", SecretStr("test-key-for-encryption-32chars!"))

    request_snapshot = build_request_snapshot(
        storefront_key="default",
        pricebook_key="default-usd",
        offer_key="starter",
        plan_id=str(uuid4()),
        currency="USD",
        channel="web",
        code_input="SAVE20",
        promo_code="SAVE20",
        partner_code=None,
        use_wallet=0,
        addons=[],
    )

    assert request_snapshot["code_input"] is None
    assert request_snapshot["promo_code"] is None
    assert "SAVE20" not in str(request_snapshot)
    assert request_snapshot["code_input_ref"]["redacted"] is True
    assert request_snapshot["code_input_ref"]["encrypted_value"].startswith("enc:growth-code-snapshot:v1:")
    assert restore_protected_request_code(request_snapshot, "code_input") == "SAVE20"
    assert restore_protected_request_code(request_snapshot, "promo_code") == "SAVE20"


def test_quote_result_snapshot_uses_stable_safe_code_descriptors(monkeypatch) -> None:
    monkeypatch.setattr(encryption, "_oauth_token_encryption_service", None)
    monkeypatch.setattr(settings, "oauth_token_encryption_key", SecretStr("test-key-for-encryption-32chars!"))

    result = CheckoutResult(
        base_price=Decimal("10.00"),
        addon_amount=Decimal("0"),
        displayed_price=Decimal("10.00"),
        discount_amount=Decimal("2.00"),
        wallet_amount=Decimal("0"),
        gateway_amount=Decimal("8.00"),
        partner_markup=Decimal("0"),
        is_zero_gateway=False,
        plan_id=uuid4(),
        promo_code_id=uuid4(),
        plan_name="Starter",
        duration_days=30,
        discounts=[
            CheckoutAppliedDiscount(
                discount_type="promo",
                code="SAVE20",
                amount=Decimal("2.00"),
            )
        ],
        code_input="SAVE20",
        entitlements_snapshot={"effective_entitlements": {}},
    )

    quote_snapshot = serialize_checkout_result(result)

    assert quote_snapshot["code_input"] != "SAVE20"
    assert "SAVE20" not in str(quote_snapshot)
    assert quote_snapshot["code_input_ref"]["redacted"] is True
    assert quote_snapshot["code_input_ref"]["code_prefix"] == "SAV"
    assert quote_snapshot["code_input_ref"]["code_length"] == 6
    assert quote_snapshot["discounts"][0]["code"] != "SAVE20"
    assert quote_snapshot["discounts"][0]["code_ref"]["code_hash"] == quote_snapshot["code_input_ref"]["code_hash"]
