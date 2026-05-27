"""Unit tests for public add-on catalog endpoint."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.presentation.api.v1.addons import routes as addon_routes


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
async def test_public_addon_catalog_returns_empty_when_stage1_addons_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    addon = _build_addon()

    class FakeAddonRepo:
        def __init__(self, _db) -> None:
            pass

        async def list_catalog(self, **kwargs):
            assert kwargs == {"active_only": True, "sale_channel": "web"}
            return [addon]

    monkeypatch.setattr(addon_routes.settings, "stage1_addons_enabled", False)
    monkeypatch.setattr(addon_routes, "PlanAddonRepository", FakeAddonRepo)

    response = await addon_routes.list_addon_catalog(channel="web", db=object())

    assert response == []


@pytest.mark.asyncio
async def test_public_addon_catalog_returns_approved_addons_when_stage1_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    valid = _build_addon(code="extra_device")
    ru_traffic = _build_addon(
        code="ru_traffic_30gb",
        display_name="+30 GB Russia traffic",
        price_usd=Decimal("2.00"),
        price_rub=Decimal("199.00"),
        max_quantity_by_plan={"ru_start": 10, "ru_basic": 10, "plus": 0},
        delta_entitlements={"traffic_limit_bytes": 30 * 1024**3},
    )
    unknown = _build_addon(code="priority_support")

    class FakeAddonRepo:
        def __init__(self, _db) -> None:
            pass

        async def list_catalog(self, **_kwargs):
            return [unknown, valid, ru_traffic]

    monkeypatch.setattr(addon_routes.settings, "stage1_addons_enabled", True)
    monkeypatch.setattr(addon_routes, "PlanAddonRepository", FakeAddonRepo)

    response = await addon_routes.list_addon_catalog(channel="web", db=object())

    assert [addon.code for addon in response] == ["extra_device", "ru_traffic_30gb"]
