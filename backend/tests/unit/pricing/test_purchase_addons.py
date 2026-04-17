from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.application.use_cases.payments.checkout import CheckoutAddonInput
from src.application.use_cases.subscriptions.purchase_addons import (
    PurchaseAddonsUseCase,
)


@pytest.mark.asyncio
async def test_purchase_addons_builds_quote_from_active_subscription() -> None:
    session = SimpleNamespace()
    use_case = PurchaseAddonsUseCase(session)
    plan_id = uuid4()

    use_case._payments = SimpleNamespace(
        get_latest_active_plan_payment=AsyncMock(
            return_value=SimpleNamespace(
                plan_id=plan_id,
                subscription_days=365,
                created_at=datetime.now(UTC) - timedelta(days=30),
            )
        )
    )
    plan = SimpleNamespace(
        id=plan_id,
        name="plus_365",
        plan_code="plus",
        display_name="Plus",
        duration_days=365,
        device_limit=5,
        traffic_policy={"mode": "fair_use", "display_label": "Unlimited"},
        connection_modes=["standard", "stealth"],
        server_pool=["shared_plus"],
        support_sla="standard",
        dedicated_ip={"included": 0, "eligible": True},
        invite_bundle={"count": 1, "friend_days": 14, "expiry_days": 60},
    )
    use_case._plans = SimpleNamespace(get_by_id=AsyncMock(return_value=plan))
    use_case._promo_repo = SimpleNamespace(get_active_by_code=AsyncMock(return_value=None))
    use_case._wallet = SimpleNamespace(
        get_balance=AsyncMock(return_value=SimpleNamespace(balance=Decimal("20.00"), frozen=Decimal("0")))
    )
    use_case._entitlements = SimpleNamespace(
        list_active_addon_lines=AsyncMock(
            return_value=[
                {
                    "code": "extra_device",
                    "qty": 1,
                    "location_code": None,
                    "delta_entitlements": {"device_limit": 1},
                }
            ]
        )
    )
    addon_line = SimpleNamespace(
        addon_id=uuid4(),
        code="extra_device",
        display_name="+1 device",
        qty=2,
        unit_price=Decimal("5.00"),
        total_price=Decimal("10.00"),
        location_code=None,
        delta_entitlements={"device_limit": 1},
    )
    use_case._checkout = SimpleNamespace(
        _resolve_addons=AsyncMock(return_value=[addon_line]),
    )

    result = await use_case.execute(
        user_id=uuid4(),
        addons=[CheckoutAddonInput(code="extra_device", qty=2)],
        use_wallet=Decimal("4.00"),
        sale_channel="web",
    )

    assert result.base_price == Decimal("0")
    assert result.addon_amount == Decimal("10.00")
    assert result.wallet_amount == Decimal("4.00")
    assert result.gateway_amount == Decimal("6.00")
    assert result.entitlements_snapshot["effective_entitlements"]["device_limit"] == 8
    assert result.duration_days >= 300
