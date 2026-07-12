from decimal import Decimal

from src.application.services.pricing_catalog_seed import (
    build_addon_seed_specs,
    build_plan_seed_specs,
)
from src.application.services.stage1_plan_policy import S1_PAID_PLAN_DURATIONS, S1_PAID_PLAN_POLICY_ID


def test_plan_seed_contains_full_canonical_matrix() -> None:
    specs = build_plan_seed_specs()

    assert len(specs) == 44
    assert {spec.plan_code for spec in specs} == {
        "start",
        "ru_start",
        "ru_basic",
        "premium_smart_ru",
        "premium_spb_de_exceptions",
        "basic",
        "plus",
        "pro",
        "max",
        "test",
        "development",
    }
    assert {spec.duration_days for spec in specs} == set(S1_PAID_PLAN_DURATIONS)


def test_public_plan_seed_matches_stage1_beta_matrix() -> None:
    public_specs = [spec for spec in build_plan_seed_specs() if spec.catalog_visibility == "public" and spec.is_active]

    assert len(public_specs) == 16
    assert {spec.plan_code for spec in public_specs} == {"basic", "plus", "pro", "max"}
    assert {spec.duration_days for spec in public_specs} == {30, 90, 180, 365}
    assert all("web" in spec.sale_channels for spec in public_specs)
    assert all("miniapp" in spec.sale_channels for spec in public_specs)
    assert all("telegram_bot" in spec.sale_channels for spec in public_specs)
    assert all(spec.price_usd > Decimal("0") for spec in public_specs)
    assert all(spec.features["bootstrap_seed_version"] == S1_PAID_PLAN_POLICY_ID for spec in public_specs)


def test_plan_seed_matches_public_and_hidden_examples() -> None:
    specs = {spec.name: spec for spec in build_plan_seed_specs()}

    assert specs["plus_365"].price_usd == Decimal("79.00")
    assert specs["plus_365"].catalog_visibility == "public"
    assert specs["plus_365"].device_limit == 5
    assert specs["plus_365"].invite_bundle == {"count": 2, "friend_days": 14, "expiry_days": 60}

    assert specs["plus_180"].price_usd == Decimal("39.99")
    assert specs["plus_180"].catalog_visibility == "public"
    assert specs["plus_180"].invite_bundle == {"count": 1, "friend_days": 7, "expiry_days": 30}

    assert specs["max_365"].price_usd == Decimal("99.00")
    assert specs["max_365"].dedicated_ip == {"included": 1, "eligible": True}
    assert specs["max_365"].support_sla == "vip"

    assert specs["start_365"].catalog_visibility == "hidden"
    assert specs["start_365"].device_limit == 1
    assert specs["start_365"].invite_bundle == {"count": 1, "friend_days": 7, "expiry_days": 30}

    assert specs["ru_start_30"].display_name == "Россия Старт"
    assert specs["ru_start_30"].catalog_visibility == "hidden"
    assert specs["ru_start_30"].sale_channels == ["admin"]
    assert specs["ru_start_30"].device_limit == 1
    assert specs["ru_start_30"].traffic_limit_bytes == 30 * 1024**3
    assert specs["ru_start_30"].features["remnawave_subscription_template"] == "Mihomo (RU bundle)"
    assert specs["ru_start_30"].features["remnawave_subscription_template_scope"] == "mihomo_only"

    assert specs["ru_basic_30"].display_name == "Россия Базовый"
    assert specs["ru_basic_30"].catalog_visibility == "hidden"
    assert specs["ru_basic_30"].sale_channels == ["admin"]
    assert specs["ru_basic_30"].device_limit == 2
    assert specs["ru_basic_30"].traffic_limit_bytes == 60 * 1024**3
    assert specs["ru_basic_30"].features["traffic_per_device_gib"] == 30
    assert specs["ru_basic_30"].features["remnawave_external_squad"] == "S1_RU_BUNDLE"
    assert specs["ru_basic_30"].features["remnawave_subscription_template"] == "Mihomo (RU bundle)"

    assert specs["premium_smart_ru_30"].display_name == "Premium Smart RU"
    assert specs["premium_smart_ru_30"].catalog_visibility == "hidden"
    assert specs["premium_smart_ru_30"].sale_channels == ["admin"]
    assert specs["premium_smart_ru_30"].device_limit == 5
    assert specs["premium_smart_ru_30"].price_usd == Decimal("0.00")
    assert specs["premium_smart_ru_30"].traffic_policy["mode"] == "fair_use"
    assert specs["premium_smart_ru_30"].connection_modes == ["standard", "stealth", "smart_routing"]
    assert specs["premium_smart_ru_30"].server_pool == ["premium_smart_ru"]
    assert specs["premium_smart_ru_30"].support_sla == "priority"
    assert specs["premium_smart_ru_30"].features["price_status"] == "TODO_OWNER_APPROVAL"
    assert specs["premium_smart_ru_30"].features["remnawave_external_squad"] == "CYBERVPN_PREMIUM_SMART_RU"
    assert specs["premium_smart_ru_30"].features["remnawave_subscription_template"] == "CyberVPN Premium Smart RU"
    assert (
        specs["premium_smart_ru_30"].features["remnawave_subscription_template_scope"]
        == "product_scoped_multi_client"
    )
    assert specs["premium_smart_ru_30"].features["torrent_policy"] == "blocked"
    assert specs["premium_smart_ru_30"].features["tor_policy"] == "blocked"

    assert specs["premium_spb_de_exceptions_30"].display_name == "Premium SPB + DE Exceptions"
    assert specs["premium_spb_de_exceptions_30"].catalog_visibility == "hidden"
    assert specs["premium_spb_de_exceptions_30"].sale_channels == ["admin"]
    assert specs["premium_spb_de_exceptions_30"].device_limit == 5
    assert specs["premium_spb_de_exceptions_30"].price_usd == Decimal("0.00")
    assert specs["premium_spb_de_exceptions_30"].traffic_policy["enforcement_profile"] == ("premium_spb_de_exceptions")
    assert specs["premium_spb_de_exceptions_30"].connection_modes == [
        "standard",
        "stealth",
        "server_side_de_exceptions",
    ]
    assert specs["premium_spb_de_exceptions_30"].server_pool == ["premium_spb_de_exceptions"]
    assert specs["premium_spb_de_exceptions_30"].support_sla == "priority"
    assert specs["premium_spb_de_exceptions_30"].features["default_egress"] == "spb"
    assert specs["premium_spb_de_exceptions_30"].features["exception_egress"] == "de"
    assert specs["premium_spb_de_exceptions_30"].features["fail_closed_for_matched_exceptions"] is True
    assert specs["premium_spb_de_exceptions_30"].features["remnawave_external_squad"] == ("CYBERVPN_SPB_DE_EXCEPTIONS")
    assert specs["premium_spb_de_exceptions_30"].features["remnawave_internal_squad"] == ("CYBERVPN_SPB_DE_NODES")
    assert specs["premium_spb_de_exceptions_30"].features["remnawave_config_profile"] == (
        "S1 SPB DE Exceptions"
    )
    assert specs["premium_spb_de_exceptions_30"].features["remnawave_policy_version"] == (
        "premium_spb_de_exceptions.v1"
    )
    assert specs["premium_spb_de_exceptions_30"].features["torrent_policy"] == "blocked"
    assert specs["premium_spb_de_exceptions_30"].features["tor_policy"] == "blocked"
    assert (
        specs["premium_spb_de_exceptions_30"].features["remnawave_external_squad"]
        != (specs["premium_smart_ru_30"].features["remnawave_external_squad"])
    )

    assert specs["test_365"].connection_modes[-1] == "experimental"
    assert specs["test_365"].invite_bundle == {"count": 3, "friend_days": 14, "expiry_days": 60}

    assert specs["development_365"].device_limit == 999
    assert specs["development_365"].price_usd == Decimal("0.00")
    assert specs["development_365"].support_sla == "internal"


def test_addon_seed_matches_phase1_catalog() -> None:
    addons = {spec.code: spec for spec in build_addon_seed_specs()}

    assert set(addons) == {
        "extra_device",
        "dedicated_ip",
        "ru_traffic_30gb",
        "ru_traffic_50gb",
        "ru_traffic_100gb",
    }
    assert addons["extra_device"].price_usd == Decimal("6.00")
    assert addons["extra_device"].max_quantity_by_plan["plus"] == 3
    assert addons["extra_device"].max_quantity_by_plan["premium_smart_ru"] == 3
    assert "premium_spb_de_exceptions" not in addons["extra_device"].max_quantity_by_plan
    assert addons["extra_device"].max_quantity_by_plan["development"] == 0
    assert addons["extra_device"].delta_entitlements == {"device_limit": 1}

    assert addons["dedicated_ip"].price_usd == Decimal("24.00")
    assert addons["dedicated_ip"].requires_location is True
    assert addons["dedicated_ip"].max_quantity_by_plan["ru_start"] == 0
    assert addons["dedicated_ip"].max_quantity_by_plan["ru_basic"] == 0
    assert addons["dedicated_ip"].max_quantity_by_plan["premium_smart_ru"] == 1
    assert "premium_spb_de_exceptions" not in addons["dedicated_ip"].max_quantity_by_plan
    assert addons["dedicated_ip"].max_quantity_by_plan["plus"] == 1
    assert addons["dedicated_ip"].max_quantity_by_plan["max"] == 3
    assert addons["dedicated_ip"].delta_entitlements == {"dedicated_ip_count": 1}

    assert addons["ru_traffic_30gb"].price_usd == Decimal("2.00")
    assert addons["ru_traffic_30gb"].price_rub == Decimal("199.00")
    assert addons["ru_traffic_30gb"].max_quantity_by_plan["ru_start"] == 10
    assert addons["ru_traffic_30gb"].max_quantity_by_plan["ru_basic"] == 10
    assert "premium_spb_de_exceptions" not in addons["ru_traffic_30gb"].max_quantity_by_plan
    assert addons["ru_traffic_30gb"].max_quantity_by_plan["plus"] == 0
    assert addons["ru_traffic_30gb"].delta_entitlements == {"traffic_limit_bytes": 30 * 1024**3}

    assert addons["ru_traffic_50gb"].delta_entitlements == {"traffic_limit_bytes": 50 * 1024**3}
    assert addons["ru_traffic_100gb"].delta_entitlements == {"traffic_limit_bytes": 100 * 1024**3}
    assert all("premium_spb_de_exceptions" not in spec.max_quantity_by_plan for spec in addons.values())
