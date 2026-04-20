from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.application.use_cases.payments.checkout import (
    CheckoutAddonInput,
    CheckoutUseCase,
)


def _build_plan(**overrides):
    base = {
        "id": uuid4(),
        "name": "plus_365",
        "plan_code": "plus",
        "display_name": "Plus",
        "catalog_visibility": "public",
        "duration_days": 365,
        "device_limit": 5,
        "price_usd": Decimal("79.00"),
        "traffic_policy": {"mode": "fair_use", "display_label": "Unlimited"},
        "connection_modes": ["standard", "stealth"],
        "server_pool": ["shared_plus"],
        "support_sla": "standard",
        "dedicated_ip": {"included": 0, "eligible": True},
        "invite_bundle": {"count": 1, "friend_days": 14, "expiry_days": 60},
        "sale_channels": ["web", "miniapp", "telegram_bot", "admin"],
        "is_active": True,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _build_addon(**overrides):
    base = {
        "id": uuid4(),
        "code": "extra_device",
        "display_name": "+1 device",
        "price_usd": Decimal("5.00"),
        "delta_entitlements": {"device_limit": 1},
        "sale_channels": ["web", "miniapp", "telegram_bot", "admin"],
        "is_active": True,
        "quantity_step": 1,
        "is_stackable": True,
        "requires_location": False,
        "max_quantity_by_plan": {"plus": 3},
    }
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.mark.asyncio
async def test_checkout_quote_applies_addons_to_entitlements() -> None:
    session = SimpleNamespace(get=AsyncMock(return_value=None))
    use_case = CheckoutUseCase(session)
    plan = _build_plan()
    addon = _build_addon()

    use_case._plan_repo = SimpleNamespace(get_by_id=AsyncMock(return_value=plan))
    use_case._addon_repo = SimpleNamespace(get_by_codes=AsyncMock(return_value=[addon]))
    use_case._promo_repo = SimpleNamespace(get_active_by_code=AsyncMock(return_value=None))
    use_case._partner_repo = SimpleNamespace(get_codes_by_partner=AsyncMock(return_value=[]))
    use_case._wallet = SimpleNamespace(
        get_balance=AsyncMock(return_value=SimpleNamespace(balance=Decimal("25.00"), frozen=Decimal("0")))
    )

    result = await use_case.execute(
        user_id=uuid4(),
        plan_id=plan.id,
        addons=[CheckoutAddonInput(code="extra_device", qty=2)],
        use_wallet=Decimal("10.00"),
        sale_channel="web",
    )

    assert result.base_price == Decimal("79.00")
    assert result.addon_amount == Decimal("10.00")
    assert result.displayed_price == Decimal("89.00")
    assert result.wallet_amount == Decimal("10.00")
    assert result.gateway_amount == Decimal("79.00")
    assert result.entitlements_snapshot["effective_entitlements"]["device_limit"] == 7
    assert result.entitlements_snapshot["addons"] == [{"code": "extra_device", "qty": 2, "location_code": None}]


@pytest.mark.asyncio
async def test_checkout_quote_rejects_hidden_plan_on_public_channel() -> None:
    session = SimpleNamespace(get=AsyncMock(return_value=None))
    use_case = CheckoutUseCase(session)
    hidden_plan = _build_plan(catalog_visibility="hidden")

    use_case._plan_repo = SimpleNamespace(get_by_id=AsyncMock(return_value=hidden_plan))
    use_case._addon_repo = SimpleNamespace(get_by_codes=AsyncMock(return_value=[]))
    use_case._promo_repo = SimpleNamespace(get_active_by_code=AsyncMock(return_value=None))
    use_case._partner_repo = SimpleNamespace(get_codes_by_partner=AsyncMock(return_value=[]))
    use_case._wallet = SimpleNamespace(
        get_balance=AsyncMock(return_value=SimpleNamespace(balance=Decimal("0"), frozen=Decimal("0")))
    )

    with pytest.raises(ValueError, match="not available on this channel"):
        await use_case.execute(
            user_id=uuid4(),
            plan_id=hidden_plan.id,
            sale_channel="web",
        )


@pytest.mark.asyncio
async def test_checkout_quote_prefers_explicit_partner_code_over_legacy_bound_partner() -> None:
    partner_user_id = uuid4()
    session = SimpleNamespace(
        get=AsyncMock(
            return_value=SimpleNamespace(
                id=uuid4(),
                partner_user_id=partner_user_id,
            )
        )
    )
    use_case = CheckoutUseCase(session)
    plan = _build_plan(price_usd=Decimal("100.00"))
    explicit_code = SimpleNamespace(id=uuid4(), markup_pct=Decimal("20.00"), is_active=True)
    legacy_code = SimpleNamespace(id=uuid4(), markup_pct=Decimal("5.00"), is_active=True)

    use_case._plan_repo = SimpleNamespace(get_by_id=AsyncMock(return_value=plan))
    use_case._addon_repo = SimpleNamespace(get_by_codes=AsyncMock(return_value=[]))
    use_case._promo_repo = SimpleNamespace(get_active_by_code=AsyncMock(return_value=None))
    use_case._partner_repo = SimpleNamespace(
        get_active_code_by_code=AsyncMock(return_value=explicit_code),
        get_codes_by_partner=AsyncMock(return_value=[legacy_code]),
    )
    use_case._wallet = SimpleNamespace(
        get_balance=AsyncMock(return_value=SimpleNamespace(balance=Decimal("0"), frozen=Decimal("0")))
    )

    result = await use_case.execute(
        user_id=uuid4(),
        plan_id=plan.id,
        partner_code="NEBULA20",
        sale_channel="web",
    )

    assert result.partner_code_id == explicit_code.id
    assert result.partner_markup == Decimal("20.00")
    assert result.displayed_price == Decimal("120.00")
