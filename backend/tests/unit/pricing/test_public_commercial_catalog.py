from __future__ import annotations

from dataclasses import asdict
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.application.use_cases.public_catalog import (
    ResolvePublicCatalogContextUseCase,
    ResolvePublicCommercialCatalogUseCase,
)
from src.config.settings import settings
from src.domain.entities.commercial_context import CommercialContextSignals


class FakePlanRepo:
    def __init__(self, plans):
        self.plans = plans

    async def list_catalog(self, **kwargs):  # noqa: ARG002
        return list(self.plans)


class FakeAddonRepo:
    def __init__(self, addons=()):
        self.addons = addons

    async def list_catalog(self, **kwargs):  # noqa: ARG002
        return list(self.addons)


class FakeOfferRepo:
    def __init__(self, offers=()):
        self.offers = offers

    async def list_active(self, **kwargs):  # noqa: ARG002
        return list(self.offers)


class FakePricebookRepo:
    async def list_active(self, **kwargs):  # noqa: ARG002
        return []


def _plan(**overrides):
    base = {
        "id": uuid4(),
        "name": "plus_365",
        "plan_code": "plus",
        "display_name": "Plus",
        "catalog_visibility": "public",
        "duration_days": 365,
        "traffic_limit_bytes": None,
        "device_limit": 5,
        "price_usd": Decimal("79.00"),
        "price_rub": None,
        "sale_channels": ["web", "miniapp", "telegram_bot", "admin"],
        "traffic_policy": {"mode": "fair_use", "display_label": "Unlimited"},
        "connection_modes": ["standard", "stealth"],
        "server_pool": ["shared_plus"],
        "support_sla": "standard",
        "dedicated_ip": {"included": 0, "eligible": True},
        "invite_bundle": {"count": 2, "friend_days": 14, "expiry_days": 60},
        "trial_eligible": False,
        "features": {},
        "is_active": True,
        "sort_order": 20,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.mark.asyncio
async def test_same_context_returns_same_public_catalog_cache_and_items() -> None:
    plans = [_plan(name="plus_30", duration_days=30), _plan(name="plus_365", duration_days=365)]
    use_case = ResolvePublicCommercialCatalogUseCase(
        None,
        plan_repo=FakePlanRepo(plans),
        addon_repo=FakeAddonRepo(),
        offer_repo=FakeOfferRepo(),
        pricebook_repo=FakePricebookRepo(),
    )
    signals = CommercialContextSignals(
        explicit_display_country_code="US",
        explicit_pricing_country_code="US",
        explicit_currency_code="USD",
        channel_key="web",
    )

    first = await use_case.execute(signals=signals, channel="web")
    second = await use_case.execute(signals=signals, channel="web")

    assert first.cache_key == second.cache_key
    assert first.plans == second.plans
    assert [period.duration_days for period in first.plans[0].billing_periods] == [30, 365]


@pytest.mark.asyncio
async def test_public_catalog_filters_hidden_internal_and_unsupported_plans() -> None:
    plans = [
        _plan(name="plus_365", plan_code="plus", duration_days=365),
        _plan(name="start_365", plan_code="start", catalog_visibility="hidden", sale_channels=["admin"]),
        _plan(name="development_365", plan_code="development", catalog_visibility="hidden", price_usd=Decimal("0")),
        _plan(name="plus_60", plan_code="plus", duration_days=60),
    ]
    use_case = ResolvePublicCommercialCatalogUseCase(
        None,
        plan_repo=FakePlanRepo(plans),
        addon_repo=FakeAddonRepo(),
        offer_repo=FakeOfferRepo(),
        pricebook_repo=FakePricebookRepo(),
    )

    catalog = await use_case.execute(signals=CommercialContextSignals(channel_key="web"), channel="web")

    assert [plan.plan_code for plan in catalog.plans] == ["plus"]
    assert [period.duration_days for period in catalog.plans[0].billing_periods] == [365]


@pytest.mark.asyncio
async def test_public_catalog_quote_handoff_excludes_trusted_price_inputs() -> None:
    use_case = ResolvePublicCommercialCatalogUseCase(
        None,
        plan_repo=FakePlanRepo([_plan()]),
        addon_repo=FakeAddonRepo(),
        offer_repo=FakeOfferRepo(),
        pricebook_repo=FakePricebookRepo(),
    )

    catalog = await use_case.execute(signals=CommercialContextSignals(channel_key="web"), channel="web")
    quote_payload = asdict(catalog.plans[0].billing_periods[0].quote)

    assert quote_payload.keys().isdisjoint({"price", "amount", "visible_price", "display_price"})
    assert quote_payload == {
        "plan_id": catalog.plans[0].billing_periods[0].plan_id,
        "plan_code": "plus",
        "billing_period_days": 365,
        "currency": "USD",
        "catalog_item_key": "plus_365",
        "context_cache_key": catalog.cache_key,
    }


@pytest.mark.asyncio
async def test_catalog_context_returns_payment_method_availability(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "payments_enabled", True)
    monkeypatch.setattr(settings, "telegram_stars_enabled", True)
    use_case = ResolvePublicCatalogContextUseCase(None, plan_repo=FakePlanRepo([_plan()]))

    context = await use_case.execute(
        signals=CommercialContextSignals(channel_key="telegram_bot", explicit_currency_code="USD"),
        channel="telegram_bot",
    )

    assert context.resolved.currency == "USD"
    assert context.payment_methods.available_methods == ("cryptobot", "telegram_stars")
    assert context.payment_methods.cryptobot is True
    assert context.payment_methods.telegram_stars is True
