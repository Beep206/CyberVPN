import json
from decimal import Decimal
from typing import cast
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.payments.checkout import CheckoutAppliedDiscount, CheckoutResult
from src.presentation.api.v1.payments.routes import _build_quote, _serialize_quote
from src.presentation.api.v1.payments.schemas import CheckoutQuoteRequest


@pytest.mark.asyncio
async def test_legacy_checkout_quote_rejects_private_catalog_grant_without_quote_session() -> None:
    request = CheckoutQuoteRequest(
        plan_id=uuid4(),
        private_catalog_grant_id=uuid4(),
        channel="web",
    )

    with pytest.raises(HTTPException) as exc_info:
        await _build_quote(body=request, db=cast(AsyncSession, object()), user_id=uuid4())

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "PRIVATE_CATALOG_GRANT_REQUIRES_QUOTE_SESSION"


def test_legacy_checkout_quote_serialization_redacts_raw_code_material() -> None:
    plan_id = uuid4()
    result = CheckoutResult(
        base_price=Decimal("100"),
        addon_amount=Decimal("0"),
        displayed_price=Decimal("90"),
        discount_amount=Decimal("10"),
        wallet_amount=Decimal("0"),
        gateway_amount=Decimal("90"),
        partner_markup=Decimal("0"),
        is_zero_gateway=False,
        plan_id=plan_id,
        entitlements_snapshot={
            "status": "quoted",
            "effective_entitlements": {
                "device_limit": 5,
                "traffic_policy": "unlimited",
                "display_traffic_label": "Unlimited",
                "connection_modes": ["standard"],
                "server_pool": ["shared"],
                "support_sla": "standard",
                "dedicated_ip_count": 0,
            },
            "invite_bundle": {},
            "is_trial": False,
        },
        discounts=[CheckoutAppliedDiscount(discount_type="promo", code="SecretPromo10", amount=Decimal("10"))],
        code_input="SecretPromo10",
    )

    response = _serialize_quote(result)
    payload = response.model_dump(mode="json")
    encoded = json.dumps(payload)

    assert payload["code_input"] != "SecretPromo10"
    assert payload["code_input_ref"]["redacted"] is True
    assert payload["discounts"][0]["code"] != "SecretPromo10"
    assert payload["discounts"][0]["code_ref"]["redacted"] is True
    assert "SecretPromo10" not in encoded
    assert "SECRETPROMO10" not in encoded
