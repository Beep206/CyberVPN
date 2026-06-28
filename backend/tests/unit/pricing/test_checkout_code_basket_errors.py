from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.application.use_cases.growth_code_sets.exceptions import CodeSetRejectedError
from src.application.use_cases.growth_codes.hashing import hash_growth_code
from src.application.use_cases.growth_codes.resolve_code import GrowthCodeResolutionOutcome
from src.application.use_cases.payments import checkout as checkout_module
from src.application.use_cases.payments.checkout import CheckoutUseCase
from src.domain.enums import GrowthCodeActionContext, GrowthCodeResolutionStatus, GrowthCodeType


@pytest.mark.asyncio
async def test_code_basket_rejection_preserves_safe_per_code_applications() -> None:
    use_case = CheckoutUseCase(AsyncMock())
    growth_code_id = uuid4()
    promo_code_id = uuid4()
    use_case._growth_codes = SimpleNamespace(
        execute=AsyncMock(
            return_value=GrowthCodeResolutionOutcome(
                accepted=True,
                code_type=GrowthCodeType.PROMO,
                action_context=GrowthCodeActionContext.CHECKOUT,
                result=GrowthCodeResolutionStatus.ACCEPTED,
                user_message_key="growth_codes.promo.accepted",
                growth_code_id=growth_code_id,
                promo_code_id=promo_code_id,
            )
        )
    )
    use_case._discount_candidate_for_resolution = AsyncMock(
        return_value=checkout_module._BasketDiscountCandidate(
            code="SAVE10",
            code_hash=hash_growth_code("SAVE10"),
            discount_type="promo_percent",
            discount_kind="percent",
            source_amount=Decimal("10"),
            strategy="percent",
        )
    )

    with pytest.raises(CodeSetRejectedError) as exc_info:
        await use_case._evaluate_code_basket(
            normalized_codes=[
                (0, "SAVE10", "accepted-slot"),
                (1, "SAVE10", "duplicate-slot"),
            ],
            user_id=uuid4(),
            plan=SimpleNamespace(id=uuid4()),
            displayed_price=Decimal("100.00"),
            base_price=Decimal("100.00"),
            existing_partner_code_present=False,
            storefront_id=None,
            sale_channel="web",
            currency="USD",
        )

    assert exc_info.value.code == "CODE_SET_REJECTED"
    assert len(exc_info.value.applications) == 2
    accepted, rejected = exc_info.value.applications
    assert accepted["client_slot_id"] == "accepted-slot"
    assert accepted["status"] == "accepted"
    assert accepted["roles"] == ["discount"]
    assert accepted["growth_code_id"] == str(growth_code_id)
    assert rejected["client_slot_id"] == "duplicate-slot"
    assert rejected["status"] == "rejected"
    assert rejected["reject_reason"] == "duplicate_code"
    assert rejected["user_message_key"] == "growth_codes.code.duplicate"
    assert "SAVE10" not in str(exc_info.value.applications)
