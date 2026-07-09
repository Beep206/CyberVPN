from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import yaml

from src.application.vpn_testing.analyzers.mihomo import REQUIRED_GROUPS, analyze_mihomo_template

REPO_ROOT = Path(__file__).resolve().parents[5]
HARDENED_TEMPLATE = REPO_ROOT / "scripts/remnawave/templates/cybervpn-premium-smart-ru-de-primary-hardened.yaml"
DEFAULT_FIXTURE = REPO_ROOT / "backend/src/application/vpn_testing/fixtures/premium_smart_ru_mihomo_template.yaml"
ROUTE_REGISTRY = REPO_ROOT / "backend/src/application/vpn_testing/route_registry/premium_smart_ru_v2.yaml"


def test_mihomo_analyzer_accepts_hardened_premium_smart_ru_template() -> None:
    route_entries = [
        SimpleNamespace(metadata_json={"domain": "gosuslugi.ru"}),
        SimpleNamespace(metadata_json={"domain": "nalog.gov.ru"}),
        SimpleNamespace(metadata_json={"domain": "sberbank.ru"}),
        SimpleNamespace(metadata_json={"domain": "telegram.org"}),
    ]

    results = analyze_mihomo_template(HARDENED_TEMPLATE.read_text(encoding="utf-8"), route_entries)
    by_key = {result["check_key"]: result for result in results}

    assert by_key["mihomo.yaml.parse"]["status"] == "pass"
    assert by_key["mihomo.required_groups"]["status"] == "pass"
    assert by_key["mihomo.required_groups"]["details"]["required_groups"] == list(REQUIRED_GROUPS)
    assert by_key["mihomo.rule_order.eu_before_ru"]["status"] == "pass"
    assert by_key["mihomo.location_groups.filtered"]["status"] == "pass"
    assert by_key["mihomo.location_groups.filtered"]["details"]["location_filters"] == {
        "🇷🇺 RU Sites": True,
        "🇩🇪 DE Auto": True,
        "🇳🇱 NL Auto": True,
        "🇷🇺 Moscow Auto": True,
        "🇷🇺 SPB Auto": True,
    }
    assert by_key["mihomo.match.default"]["status"] == "pass"
    assert by_key["mihomo.abuse_sentinel"]["status"] == "pass"
    assert by_key["mihomo.tor_block_sentinel"]["status"] == "pass"


def test_vpn_tester_default_fixture_and_route_registry_match_hardened_template() -> None:
    fixture_text = DEFAULT_FIXTURE.read_text(encoding="utf-8")
    template_text = HARDENED_TEMPLATE.read_text(encoding="utf-8")
    registry = json.loads(ROUTE_REGISTRY.read_text(encoding="utf-8"))
    expected_groups = {route["metadata"]["expected_group"] for route in registry["routes"]}

    assert fixture_text == template_text
    assert "🌍 Global Auto" not in expected_groups
    assert "🌍 World / EU" in expected_groups
    assert "📺 YouTube" in expected_groups
    assert "💬 Discord" in expected_groups
    assert "➤ Telegram" in expected_groups
    assert "🤖 AI" in expected_groups
    assert "👨‍💻 Dev Services" in expected_groups
    assert "⛔ BLOCK" in expected_groups


def test_mihomo_analyzer_rejects_abuse_group_mutations() -> None:
    config = yaml.safe_load(HARDENED_TEMPLATE.read_text(encoding="utf-8"))
    for group in config["proxy-groups"]:
        if group["name"] == "🧲 Torrents":
            group["proxies"] = ["🌍 World / EU"]
        if group["name"] == "⛔ BLOCK":
            group["proxies"] = ["DIRECT"]
    results = analyze_mihomo_template(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), [])
    by_key = {result["check_key"]: result for result in results}

    assert by_key["mihomo.abuse_sentinel"]["status"] == "fail"
    assert by_key["mihomo.tor_block_sentinel"]["status"] == "fail"


def test_mihomo_analyzer_rejects_manual_eu_rule_after_broad_ru() -> None:
    config = yaml.safe_load(HARDENED_TEMPLATE.read_text(encoding="utf-8"))
    rules = config["rules"]
    manual_rule = next(rule for rule in rules if "manual-eu-inline" in rule)
    rules.remove(manual_rule)
    ru_index = next(index for index, rule in enumerate(rules) if "ru-services-inline" in rule)
    rules.insert(ru_index + 1, manual_rule)

    results = analyze_mihomo_template(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), [])
    by_key = {result["check_key"]: result for result in results}

    assert by_key["mihomo.rule_order.eu_before_ru"]["status"] == "fail"
    assert (
        by_key["mihomo.rule_order.eu_before_ru"]["details"]["eu_indexes"]["manual-eu-inline"][0]
        > by_key["mihomo.rule_order.eu_before_ru"]["details"]["ru_indexes"]["ru-services-inline"][0]
    )
