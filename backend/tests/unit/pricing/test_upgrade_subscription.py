from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.application.use_cases.subscriptions.upgrade_subscription import (
    UpgradeSubscriptionUseCase,
)


@pytest.mark.asyncio
async def test_upgrade_subscription_rejects_same_plan() -> None:
    session = SimpleNamespace()
    use_case = UpgradeSubscriptionUseCase(session)
    plan_id = uuid4()
    use_case._payments = SimpleNamespace(
        get_latest_active_plan_payment=AsyncMock(return_value=SimpleNamespace(plan_id=plan_id))
    )

    with pytest.raises(ValueError, match="matches the current subscription"):
        await use_case.execute(user_id=uuid4(), target_plan_id=plan_id)


@pytest.mark.asyncio
async def test_upgrade_subscription_merges_existing_addons_into_snapshot() -> None:
    session = SimpleNamespace()
    use_case = UpgradeSubscriptionUseCase(session)
    current_plan_id = uuid4()
    target_plan_id = uuid4()
    use_case._payments = SimpleNamespace(
        get_latest_active_plan_payment=AsyncMock(return_value=SimpleNamespace(plan_id=current_plan_id))
    )
    use_case._entitlements = SimpleNamespace(
        list_active_addon_lines=AsyncMock(
            return_value=[
                {
                    "code": "dedicated_ip",
                    "qty": 1,
                    "location_code": "de",
                    "delta_entitlements": {"dedicated_ip_count": 1},
                }
            ]
        )
    )
    plan = SimpleNamespace(
        id=target_plan_id,
        name="max_365",
        plan_code="max",
        display_name="Max",
        duration_days=365,
        device_limit=15,
        traffic_policy={"mode": "fair_use", "display_label": "Unlimited"},
        connection_modes=["standard", "stealth", "manual_config"],
        server_pool=["premium", "exclusive"],
        support_sla="vip",
        dedicated_ip={"included": 1, "eligible": True},
        invite_bundle={"count": 3, "friend_days": 14, "expiry_days": 60},
    )
    quote = SimpleNamespace(
        base_price=Decimal("129.00"),
        addon_amount=Decimal("0"),
        displayed_price=Decimal("129.00"),
        discount_amount=Decimal("0"),
        wallet_amount=Decimal("0"),
        gateway_amount=Decimal("129.00"),
        partner_markup=Decimal("0"),
        is_zero_gateway=False,
        plan_id=target_plan_id,
        promo_code_id=None,
        partner_code_id=None,
        plan_name="max_365",
        duration_days=365,
        addons=[],
        entitlements_snapshot={},
        commission_base_amount=Decimal("129.00"),
    )
    use_case._checkout = SimpleNamespace(
        execute=AsyncMock(return_value=quote),
        _plan_repo=SimpleNamespace(get_by_id=AsyncMock(return_value=plan)),
    )

    result = await use_case.execute(
        user_id=uuid4(),
        target_plan_id=target_plan_id,
        promo_code=None,
        use_wallet=Decimal("0"),
        sale_channel="web",
    )

    assert result.entitlements_snapshot["effective_entitlements"]["dedicated_ip_count"] == 2
