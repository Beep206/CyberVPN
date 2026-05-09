"""S1 paid plan catalog and visibility checks."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.application.services.pricing_catalog_seed import build_plan_seed_specs
from src.application.services.stage1_plan_policy import (
    S1_PAID_PLAN_CODES,
    S1_PAID_PLAN_DURATIONS,
    S1_PRIVATE_PLAN_CODES,
    filter_stage1_public_paid_plans,
)
from src.application.use_cases.payments import checkout as checkout_module
from src.application.use_cases.payments.checkout import CheckoutAddonInput, CheckoutUseCase


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
        "sale_channels": ["web", "miniapp", "telegram_bot", "admin"],
        "traffic_policy": {"mode": "fair_use", "display_label": "Unlimited"},
        "connection_modes": ["standard", "stealth"],
        "server_pool": ["shared_plus"],
        "support_sla": "standard",
        "dedicated_ip": {"included": 0, "eligible": True},
        "invite_bundle": {"count": 2, "friend_days": 14, "expiry_days": 60},
        "is_active": True,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _build_addon(**overrides):
    base = {
        "id": uuid4(),
        "code": "extra_device",
        "display_name": "+1 device",
        "is_active": True,
        "sale_channels": ["web", "miniapp", "telegram_bot", "admin"],
        "quantity_step": 1,
        "is_stackable": True,
        "requires_location": False,
        "price_usd": Decimal("6.00"),
        "max_quantity_by_plan": {"plus": 3},
        "delta_entitlements": {"device_limit": 1},
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_stage1_seed_exposes_only_four_public_families_and_four_terms() -> None:
    specs = build_plan_seed_specs()
    public_specs = [spec for spec in specs if spec.catalog_visibility == "public" and spec.is_active]

    assert len(public_specs) == len(S1_PAID_PLAN_CODES) * len(S1_PAID_PLAN_DURATIONS)
    assert {spec.plan_code for spec in public_specs} == set(S1_PAID_PLAN_CODES)
    assert {spec.duration_days for spec in public_specs} == set(S1_PAID_PLAN_DURATIONS)
    assert 180 in {spec.duration_days for spec in public_specs}
    assert all(spec.price_usd > Decimal("0") for spec in public_specs)


def test_stage1_seed_keeps_private_families_hidden_and_admin_only() -> None:
    specs = build_plan_seed_specs()
    private_specs = [spec for spec in specs if spec.plan_code in S1_PRIVATE_PLAN_CODES]

    assert len(private_specs) == len(S1_PRIVATE_PLAN_CODES) * len(S1_PAID_PLAN_DURATIONS)
    assert {spec.catalog_visibility for spec in private_specs} == {"hidden"}
    assert all(spec.sale_channels == ["admin"] for spec in private_specs)


def test_stage1_public_filter_removes_hidden_internal_and_unsupported_periods() -> None:
    valid = _build_plan(plan_code="basic", duration_days=30, name="basic_30")
    unsupported_period = _build_plan(plan_code="basic", duration_days=60, name="basic_60")
    hidden = _build_plan(plan_code="start", catalog_visibility="hidden", duration_days=30, name="start_30")
    hidden_public_family = _build_plan(
        plan_code="basic",
        catalog_visibility="hidden",
        duration_days=30,
        name="basic_30",
    )
    inactive = _build_plan(plan_code="plus", duration_days=365, is_active=False, name="plus_365")
    wrong_channel = _build_plan(
        plan_code="pro",
        duration_days=365,
        name="pro_365",
        sale_channels=["telegram_bot"],
    )

    filtered = filter_stage1_public_paid_plans(
        [unsupported_period, hidden, hidden_public_family, valid, inactive, wrong_channel],
        sale_channel="web",
    )

    assert filtered == [valid]


@pytest.mark.asyncio
@pytest.mark.parametrize("duration_days", S1_PAID_PLAN_DURATIONS)
async def test_stage1_checkout_accepts_public_paid_beta_terms(duration_days: int) -> None:
    session = SimpleNamespace(get=AsyncMock(return_value=None))
    use_case = CheckoutUseCase(session)
    plan = _build_plan(duration_days=duration_days, name=f"plus_{duration_days}")

    use_case._plan_repo = SimpleNamespace(get_by_id=AsyncMock(return_value=plan))
    use_case._addon_repo = SimpleNamespace(get_by_codes=AsyncMock(return_value=[]))
    use_case._promo_repo = SimpleNamespace(get_active_by_code=AsyncMock(return_value=None))
    use_case._wallet = SimpleNamespace(
        get_balance=AsyncMock(return_value=SimpleNamespace(balance=Decimal("0"), frozen=Decimal("0")))
    )

    result = await use_case.execute(user_id=uuid4(), plan_id=plan.id, sale_channel="web")

    assert result.plan_name == f"plus_{duration_days}"
    assert result.duration_days == duration_days
    assert result.base_price == Decimal("79.00")
    assert result.entitlements_snapshot["period_days"] == duration_days


@pytest.mark.asyncio
async def test_stage1_checkout_rejects_public_unsupported_duration() -> None:
    session = SimpleNamespace(get=AsyncMock(return_value=None))
    use_case = CheckoutUseCase(session)
    unsupported = _build_plan(duration_days=60, name="plus_60")

    use_case._plan_repo = SimpleNamespace(get_by_id=AsyncMock(return_value=unsupported))

    with pytest.raises(ValueError, match="S1 beta paid catalog"):
        await use_case.execute(user_id=uuid4(), plan_id=unsupported.id, sale_channel="web")


@pytest.mark.asyncio
async def test_stage1_checkout_rejects_addon_lines_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(checkout_module.settings, "stage1_addons_enabled", False)
    session = SimpleNamespace(get=AsyncMock(return_value=None))
    use_case = CheckoutUseCase(session)
    plan = _build_plan()

    use_case._plan_repo = SimpleNamespace(get_by_id=AsyncMock(return_value=plan))

    with pytest.raises(ValueError, match="Add-ons are disabled for S1 beta"):
        await use_case.execute(
            user_id=uuid4(),
            plan_id=plan.id,
            sale_channel="web",
            addons=[CheckoutAddonInput(code="extra_device", qty=1)],
        )


@pytest.mark.asyncio
async def test_stage1_checkout_allows_addon_lines_only_when_flag_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(checkout_module.settings, "stage1_addons_enabled", True)
    session = SimpleNamespace(get=AsyncMock(return_value=None))
    use_case = CheckoutUseCase(session)
    plan = _build_plan()
    addon = _build_addon()

    use_case._addon_repo = SimpleNamespace(get_by_codes=AsyncMock(return_value=[addon]))

    lines = await use_case._resolve_addons(
        plan=plan,
        addon_inputs=[CheckoutAddonInput(code="extra_device", qty=1)],
        sale_channel="web",
    )

    assert lines[0].code == "extra_device"
    assert lines[0].total_price == Decimal("6.00")
