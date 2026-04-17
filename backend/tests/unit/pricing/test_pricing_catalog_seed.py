from decimal import Decimal

from src.application.services.pricing_catalog_seed import (
    build_addon_seed_specs,
    build_plan_seed_specs,
)


def test_plan_seed_contains_full_canonical_matrix() -> None:
    specs = build_plan_seed_specs()

    assert len(specs) == 28
    assert {spec.plan_code for spec in specs} == {
        "start",
        "basic",
        "plus",
        "pro",
        "max",
        "test",
        "development",
    }
    assert {spec.duration_days for spec in specs} == {30, 90, 180, 365}


def test_plan_seed_matches_public_and_hidden_examples() -> None:
    specs = {spec.name: spec for spec in build_plan_seed_specs()}

    assert specs["plus_365"].price_usd == Decimal("79.00")
    assert specs["plus_365"].catalog_visibility == "public"
    assert specs["plus_365"].device_limit == 5
    assert specs["plus_365"].invite_bundle == {"count": 2, "friend_days": 14, "expiry_days": 60}

    assert specs["max_365"].price_usd == Decimal("99.00")
    assert specs["max_365"].dedicated_ip == {"included": 1, "eligible": True}
    assert specs["max_365"].support_sla == "vip"

    assert specs["start_365"].catalog_visibility == "hidden"
    assert specs["start_365"].device_limit == 1
    assert specs["start_365"].invite_bundle == {"count": 1, "friend_days": 7, "expiry_days": 30}

    assert specs["test_365"].connection_modes[-1] == "experimental"
    assert specs["test_365"].invite_bundle == {"count": 3, "friend_days": 14, "expiry_days": 60}

    assert specs["development_365"].device_limit == 999
    assert specs["development_365"].price_usd == Decimal("0.00")
    assert specs["development_365"].support_sla == "internal"


def test_addon_seed_matches_phase1_catalog() -> None:
    addons = {spec.code: spec for spec in build_addon_seed_specs()}

    assert set(addons) == {"extra_device", "dedicated_ip"}
    assert addons["extra_device"].price_usd == Decimal("6.00")
    assert addons["extra_device"].max_quantity_by_plan["plus"] == 3
    assert addons["extra_device"].max_quantity_by_plan["development"] == 0
    assert addons["extra_device"].delta_entitlements == {"device_limit": 1}

    assert addons["dedicated_ip"].price_usd == Decimal("24.00")
    assert addons["dedicated_ip"].requires_location is True
    assert addons["dedicated_ip"].delta_entitlements == {"dedicated_ip_count": 1}
