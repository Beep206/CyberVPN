from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.application.use_cases.growth_codes import GrowthCodeResolutionOutcome
from src.application.use_cases.payments.checkout import CheckoutAddonInput, CheckoutUseCase
from src.application.use_cases.subscriptions import purchase_addons as purchase_addons_module
from src.application.use_cases.subscriptions.purchase_addons import (
    PurchaseAddonsUseCase,
)
from src.domain.enums import GrowthCodeActionContext, GrowthCodeResolutionStatus, GrowthCodeType


@pytest.mark.asyncio
async def test_purchase_addons_rejects_when_stage1_addons_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(purchase_addons_module.settings, "stage1_addons_enabled", False)
    use_case = PurchaseAddonsUseCase(SimpleNamespace())

    with pytest.raises(ValueError, match="Add-ons are disabled for S1 beta"):
        await use_case.execute(
            user_id=uuid4(),
            addons=[CheckoutAddonInput(code="extra_device", qty=1)],
        )


@pytest.mark.asyncio
async def test_purchase_addons_builds_quote_from_active_subscription(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(purchase_addons_module.settings, "stage1_addons_enabled", True)
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


@pytest.mark.asyncio
async def test_resolve_addons_uses_rub_catalog_price(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(purchase_addons_module.settings, "stage1_addons_enabled", True)
    use_case = CheckoutUseCase(SimpleNamespace())
    addon_id = uuid4()
    addon = SimpleNamespace(
        id=addon_id,
        code="ru_traffic_30gb",
        display_name="+30 GB Russia traffic",
        price_usd=Decimal("2.00"),
        price_rub=Decimal("199.00"),
        is_active=True,
        sale_channels=["web"],
        quantity_step=1,
        is_stackable=True,
        requires_location=False,
        delta_entitlements={"traffic_limit_bytes": 30 * 1024**3},
        max_quantity_by_plan={"ru_start": 10},
    )
    plan = SimpleNamespace(
        id=uuid4(),
        plan_code="ru_start",
        is_active=True,
        dedicated_ip={},
    )
    use_case._addon_repo = SimpleNamespace(get_by_codes=AsyncMock(return_value=[addon]))

    lines = await use_case._resolve_addons(
        plan=plan,
        addon_inputs=[CheckoutAddonInput(code="ru_traffic_30gb", qty=2)],
        sale_channel="web",
        currency="RUB",
    )

    assert lines[0].unit_price == Decimal("199.00")
    assert lines[0].total_price == Decimal("398.00")


@pytest.mark.asyncio
async def test_purchase_addons_uses_growth_code_resolver_for_promo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(purchase_addons_module.settings, "stage1_addons_enabled", True)
    monkeypatch.setattr(purchase_addons_module.settings, "checkout_code_discounts_enabled", True)
    session = SimpleNamespace()
    use_case = PurchaseAddonsUseCase(session)
    user_id = uuid4()
    plan_id = uuid4()
    promo_id = uuid4()

    use_case._payments = SimpleNamespace(
        get_latest_active_plan_payment=AsyncMock(
            return_value=SimpleNamespace(
                plan_id=plan_id,
                subscription_days=30,
                created_at=datetime.now(UTC) - timedelta(days=1),
            )
        )
    )
    plan = SimpleNamespace(
        id=plan_id,
        name="ru_start_30d",
        plan_code="ru_start",
        display_name="RU Start",
        duration_days=30,
        device_limit=1,
        traffic_policy={"mode": "quota", "display_label": "30 GB"},
        connection_modes=["standard"],
        server_pool=["ru"],
        support_sla="standard",
        dedicated_ip={},
        invite_bundle={},
    )
    use_case._plans = SimpleNamespace(get_by_id=AsyncMock(return_value=plan))
    use_case._entitlements = SimpleNamespace(list_active_addon_lines=AsyncMock(return_value=[]))
    use_case._wallet = SimpleNamespace(
        get_balance=AsyncMock(return_value=SimpleNamespace(balance=Decimal("0"), frozen=Decimal("0")))
    )
    addon_line = SimpleNamespace(
        addon_id=uuid4(),
        code="ru_traffic_30gb",
        display_name="+30 GB Russia traffic",
        qty=1,
        unit_price=Decimal("199.00"),
        total_price=Decimal("199.00"),
        location_code=None,
        delta_entitlements={"traffic_limit_bytes": 30 * 1024**3},
    )
    use_case._checkout = SimpleNamespace(_resolve_addons=AsyncMock(return_value=[addon_line]))
    use_case._growth_codes = SimpleNamespace(
        execute=AsyncMock(
            return_value=GrowthCodeResolutionOutcome(
                accepted=True,
                code_type=GrowthCodeType.PROMO,
                action_context=GrowthCodeActionContext.CHECKOUT,
                result=GrowthCodeResolutionStatus.ACCEPTED,
                user_message_key="growth_codes.promo.accepted",
                promo_code_id=promo_id,
                resolved_code_id=promo_id,
                growth_code_id=uuid4(),
            )
        )
    )
    use_case._promo_repo = SimpleNamespace(
        get_active_by_code=AsyncMock(
            return_value=SimpleNamespace(
                id=promo_id,
                discount_type="percent",
                discount_value=10,
            )
        )
    )

    result = await use_case.execute(
        user_id=user_id,
        addons=[CheckoutAddonInput(code="ru_traffic_30gb", qty=1)],
        promo_code="RUB10",
        currency="RUB",
    )

    use_case._growth_codes.execute.assert_awaited_once()
    _, kwargs = use_case._growth_codes.execute.await_args
    assert kwargs["amount"] == Decimal("199.00")
    assert kwargs["plan_id"] == plan_id
    assert result.promo_code_id == promo_id
    assert result.discount_amount == Decimal("19.900")
    assert result.code_resolution is not None
