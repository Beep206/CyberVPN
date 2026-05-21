"""Unit tests for Telegram bot-facing plan catalog endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.presentation.api.v1.telegram import routes as telegram_routes


def _build_plan(**overrides):
    base = {
        "id": uuid4(),
        "name": "plus_180",
        "plan_code": "plus",
        "display_name": "Plus",
        "catalog_visibility": "public",
        "duration_days": 180,
        "traffic_limit_bytes": None,
        "device_limit": 5,
        "price_usd": Decimal("39.99"),
        "price_rub": None,
        "traffic_policy": {"mode": "fair_use", "display_label": "Unlimited"},
        "connection_modes": ["standard", "stealth"],
        "server_pool": ["shared_plus"],
        "support_sla": "standard",
        "dedicated_ip": {"included": 0, "eligible": True},
        "sale_channels": ["web", "miniapp", "telegram_bot", "admin"],
        "invite_bundle": {"count": 1, "friend_days": 7, "expiry_days": 30},
        "trial_eligible": False,
        "features": {},
        "is_active": True,
        "sort_order": 20,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _build_addon(**overrides):
    base = {
        "id": uuid4(),
        "code": "extra_device",
        "display_name": "+1 device",
        "duration_mode": "inherits_subscription",
        "is_stackable": True,
        "quantity_step": 1,
        "price_usd": Decimal("6.00"),
        "price_rub": None,
        "max_quantity_by_plan": {"plus": 3},
        "delta_entitlements": {"device_limit": 1},
        "requires_location": False,
        "sale_channels": ["web", "miniapp", "telegram_bot", "admin"],
        "is_active": True,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.mark.asyncio
async def test_telegram_bot_plans_do_not_leak_private_or_out_of_scope_plans(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    public_semiannual = _build_plan(name="plus_180", duration_days=180, sort_order=20)
    public_yearly = _build_plan(name="plus_365", duration_days=365, sort_order=21)
    private_plan = _build_plan(
        name="test_365",
        plan_code="test",
        catalog_visibility="hidden",
        duration_days=365,
        sale_channels=["admin"],
        sort_order=19,
    )
    unsupported_public_plan = _build_plan(name="plus_60", duration_days=60, sort_order=18)
    wrong_channel_plan = _build_plan(name="pro_365", plan_code="pro", duration_days=365, sale_channels=["web"])

    class FakePlanRepo:
        def __init__(self, _db) -> None:
            pass

        async def list_catalog(self, **kwargs):
            assert kwargs == {
                "visibility": "public",
                "sale_channel": "telegram_bot",
                "active_only": True,
            }
            return [
                private_plan,
                unsupported_public_plan,
                wrong_channel_plan,
                public_semiannual,
                public_yearly,
            ]

    monkeypatch.setattr(telegram_routes, "_require_telegram_bot_secret", lambda _secret: None)
    monkeypatch.setattr(telegram_routes, "SubscriptionPlanRepository", FakePlanRepo)

    response = await telegram_routes.get_bot_plans(telegram_bot_secret="internal-secret", db=object())

    assert [plan.name for plan in response] == ["plus_180", "plus_365"]
    assert [plan.duration_days for plan in response] == [180, 365]


@pytest.mark.asyncio
async def test_telegram_bot_addons_catalog_is_empty_when_stage1_addons_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    addon = _build_addon()

    class FakeAddonRepo:
        def __init__(self, _db) -> None:
            pass

        async def list_catalog(self, **kwargs):
            assert kwargs == {"active_only": True, "sale_channel": "telegram_bot"}
            return [addon]

    monkeypatch.setattr(telegram_routes, "_require_telegram_bot_secret", lambda _secret: None)
    monkeypatch.setattr(telegram_routes.settings, "stage1_addons_enabled", False)
    monkeypatch.setattr(telegram_routes, "PlanAddonRepository", FakeAddonRepo)

    response = await telegram_routes.get_bot_addons_catalog(
        telegram_bot_secret="internal-secret",
        db=object(),
    )

    assert response == []


@pytest.mark.asyncio
async def test_telegram_bot_invite_codes_returns_owned_invites(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner_id = uuid4()
    invite_id = uuid4()
    created_at = datetime(2026, 5, 21, 11, 54, tzinfo=UTC)
    expires_at = datetime(2026, 5, 24, 11, 54, tzinfo=UTC)

    class FakeInviteRepo:
        def __init__(self, _db) -> None:
            pass

        async def get_by_owner(self, **kwargs):
            assert kwargs == {"owner_user_id": owner_id, "offset": 0, "limit": 50}
            return [
                SimpleNamespace(
                    id=invite_id,
                    code="OWNER123",
                    free_days=7,
                    is_used=False,
                    expires_at=expires_at,
                    created_at=created_at,
                )
            ]

    async def fake_get_mobile_user_or_404(_db, _telegram_id):
        return SimpleNamespace(id=owner_id)

    monkeypatch.setattr(telegram_routes, "_require_telegram_bot_secret", lambda _secret: None)
    monkeypatch.setattr(telegram_routes, "_get_mobile_user_or_404", fake_get_mobile_user_or_404)
    monkeypatch.setattr(telegram_routes, "InviteCodeRepository", FakeInviteRepo)

    response = await telegram_routes.get_bot_user_invite_codes(
        telegram_id=123456,
        offset=0,
        limit=50,
        telegram_bot_secret="internal-secret",
        db=object(),
    )

    assert len(response) == 1
    assert response[0].id == invite_id
    assert response[0].code == "OWNER123"
    assert response[0].free_days == 7
    assert response[0].is_used is False
