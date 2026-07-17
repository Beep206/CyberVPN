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


def test_premium_smart_ru_registry_requires_raw_xhttp_route_parity() -> None:
    registry = yaml.safe_load(ROUTE_REGISTRY.read_text(encoding="utf-8"))
    routed_entries = [route for route in registry["routes"] if route["expected_modes"] != ["block"]]

    assert routed_entries
    assert all(route["expected_modes"] == ["raw", "xhttp"] for route in routed_entries)
    assert all({"raw", "xhttp"}.issubset(set(route["node_tags"])) for route in routed_entries)
    by_key = {route["route_key"]: route for route in routed_entries}
    assert by_key["default-ipv4-literal"]["metadata"]["address_family"] == "ipv4"
    assert by_key["default-ipv6-literal"]["metadata"]["address_family"] == "ipv6"


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
    assert "🧲 Torrents" not in by_key["mihomo.required_groups"]["details"]["required_groups"]
    assert by_key["mihomo.rule_order.eu_before_ru"]["status"] == "pass"
    assert by_key["mihomo.rule_order.catalog_before_block"]["status"] == "pass"
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
    assert by_key["mihomo.abuse_sentinel"]["details"]["torrent_group_names"] == []
    assert by_key["mihomo.abuse_sentinel"]["details"]["static_torrent_provider_ids"] == []
    assert by_key["mihomo.abuse_sentinel"]["details"]["torrent_rule_count"] == 0
    assert by_key["mihomo.tor_block_sentinel"]["status"] == "pass"


def test_vpn_tester_default_fixture_and_route_registry_match_hardened_template() -> None:
    fixture_text = DEFAULT_FIXTURE.read_text(encoding="utf-8")
    template_text = HARDENED_TEMPLATE.read_text(encoding="utf-8")
    registry = json.loads(ROUTE_REGISTRY.read_text(encoding="utf-8"))
    expected_groups = {route["metadata"]["expected_group"] for route in registry["routes"]}
    route_entries = [
        SimpleNamespace(route_key=route["route_key"], metadata_json=route["metadata"]) for route in registry["routes"]
    ]
    by_key = {result["check_key"]: result for result in analyze_mihomo_template(template_text, route_entries)}

    assert fixture_text == template_text
    assert "🌍 Global Auto" not in expected_groups
    assert "🌍 World / EU" in expected_groups
    assert "📺 YouTube" in expected_groups
    assert "💬 Discord" in expected_groups
    assert "➤ Telegram" in expected_groups
    assert "🤖 AI" in expected_groups
    assert "👨‍💻 Dev Services" in expected_groups
    assert "⛔ BLOCK" in expected_groups
    assert "🧲 Torrents" not in expected_groups
    for domain in ("rutracker.org", "rutor.info", "nnmclub.to", "kinozal.tv"):
        route = next(item for item in registry["routes"] if item["metadata"].get("domain") == domain)
        assert route["country_code"] == "DE"
        assert route["expected_modes"] == ["raw", "xhttp"]
        assert {"raw", "xhttp"}.issubset(set(route["node_tags"]))
        assert route["metadata"]["expected_group"] == "🌍 World / EU"
        assert route["metadata"]["expected_policy"] == "catalog-access-inline"
        assert route["metadata"]["traffic_class"] == "normal_website"
        assert route["metadata"]["live_traffic_required"] is False
    assert by_key["mihomo.route_registry.coverage"]["status"] == "pass"
    assert by_key["mihomo.route_registry.coverage"]["details"]["coverage_ratio"] >= 0.75


def test_mihomo_analyzer_rejects_static_torrent_policy_mutations() -> None:
    config = yaml.safe_load(HARDENED_TEMPLATE.read_text(encoding="utf-8"))
    config["proxy-groups"].append(
        {"name": "🧲 Torrents", "type": "select", "remnawave": {"include-proxies": False}, "proxies": ["REJECT"]}
    )
    config["rule-providers"]["torrent-websites"] = {
        "type": "http",
        "behavior": "domain",
        "format": "mrs",
        "url": "https://rules.example.invalid/torrent-websites.mrs",
        "path": "./rule-sets/torrent-websites.mrs",
    }
    config["rules"].insert(0, "RULE-SET,torrent-websites,REJECT,no-resolve")
    config["rules"].insert(1, "PROCESS-NAME-REGEX,(?i).*torrent.*,REJECT")
    config["rules"].insert(2, "RULE-SET,torrent-websites,reject,no-resolve")
    config["rules"].insert(3, "DOMAIN-SUFFIX,rutracker.org,REJECT,no-resolve")
    config["rules"].insert(
        4,
        "AND,((RULE-SET,torrent-websites),(NETWORK,tcp)),REJECT,no-resolve",
    )
    for group in config["proxy-groups"]:
        if group["name"] == "⛔ BLOCK":
            group["proxies"] = ["DIRECT"]
    results = analyze_mihomo_template(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), [])
    by_key = {result["check_key"]: result for result in results}

    assert by_key["mihomo.abuse_sentinel"]["status"] == "fail"
    assert by_key["mihomo.abuse_sentinel"]["details"]["torrent_group_names"] == ["🧲 Torrents"]
    assert by_key["mihomo.abuse_sentinel"]["details"]["static_torrent_provider_ids"] == ["torrent-websites"]
    assert by_key["mihomo.abuse_sentinel"]["details"]["torrent_rule_count"] == 5
    assert by_key["mihomo.tor_block_sentinel"]["status"] == "fail"


def test_mihomo_analyzer_allows_torrent_catalog_name_on_normal_eu_route() -> None:
    config = yaml.safe_load(HARDENED_TEMPLATE.read_text(encoding="utf-8"))
    config["rule-providers"]["torrent-catalog-routing"] = {
        "type": "inline",
        "behavior": "domain",
        "payload": ["DOMAIN-SUFFIX,torrentgalaxy.to"],
    }
    config["rules"].insert(
        config["rules"].index("MATCH,🌍 World / EU"),
        "RULE-SET,torrent-catalog-routing,🌍 World / EU",
    )

    results = analyze_mihomo_template(
        yaml.safe_dump(config, allow_unicode=True, sort_keys=False),
        [],
    )
    by_key = {result["check_key"]: result for result in results}

    assert by_key["mihomo.abuse_sentinel"]["status"] == "pass"
    assert by_key["mihomo.abuse_sentinel"]["details"]["torrent_rule_count"] == 0


def test_mihomo_analyzer_rejects_neutral_provider_with_catalog_payload_routed_to_block() -> None:
    config = yaml.safe_load(HARDENED_TEMPLATE.read_text(encoding="utf-8"))
    config["rule-providers"]["innocent-inline"] = {
        "type": "inline",
        "behavior": "classical",
        "payload": ["DOMAIN-SUFFIX,rutracker.org"],
    }
    config["rules"].insert(
        config["rules"].index("MATCH,🌍 World / EU"),
        "RULE-SET,innocent-inline,REJECT,no-resolve",
    )

    results = analyze_mihomo_template(
        yaml.safe_dump(config, allow_unicode=True, sort_keys=False),
        [],
    )
    by_key = {result["check_key"]: result for result in results}

    abuse = by_key["mihomo.abuse_sentinel"]
    assert abuse["status"] == "fail"
    assert abuse["details"]["static_torrent_provider_ids"] == ["innocent-inline"]
    assert abuse["details"]["torrent_rule_count"] == 1
    assert abuse["details"]["static_torrent_rules"] == ["RULE-SET,innocent-inline,REJECT,no-resolve"]


def test_mihomo_analyzer_rejects_regex_provider_routed_to_reject_only_alias() -> None:
    config = yaml.safe_load(HARDENED_TEMPLATE.read_text(encoding="utf-8"))
    config["proxy-groups"].append(
        {
            "name": "innocent-sink",
            "type": "select",
            "proxies": ["REJECT"],
        }
    )
    config["rule-providers"]["innocent-inline"] = {
        "type": "inline",
        "behavior": "classical",
        "payload": [
            r"DOMAIN-REGEX,.*rutracker\.org$",
            "DOMAIN-KEYWORD,rutor",
        ],
    }
    config["rules"].insert(
        config["rules"].index("MATCH,🌍 World / EU"),
        "RULE-SET,innocent-inline,innocent-sink,no-resolve",
    )

    results = analyze_mihomo_template(
        yaml.safe_dump(config, allow_unicode=True, sort_keys=False),
        [],
    )
    abuse = next(result for result in results if result["check_key"] == "mihomo.abuse_sentinel")

    assert abuse["status"] == "fail"
    assert abuse["details"]["static_torrent_provider_ids"] == ["innocent-inline"]
    assert abuse["details"]["static_torrent_rules"] == ["RULE-SET,innocent-inline,innocent-sink,no-resolve"]


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


def test_mihomo_analyzer_rejects_catalog_access_after_block_policy() -> None:
    config = yaml.safe_load(HARDENED_TEMPLATE.read_text(encoding="utf-8"))
    rules = config["rules"]
    catalog_rule = "RULE-SET,catalog-access-inline,🌍 World / EU"
    rules.remove(catalog_rule)
    first_block_index = next(index for index, rule in enumerate(rules) if rule.endswith(",⛔ BLOCK"))
    rules.insert(first_block_index + 1, catalog_rule)

    results = analyze_mihomo_template(
        yaml.safe_dump(config, allow_unicode=True, sort_keys=False),
        [],
    )
    by_key = {result["check_key"]: result for result in results}

    assert by_key["mihomo.rule_order.catalog_before_block"]["status"] == "fail"
    assert by_key["mihomo.abuse_sentinel"]["status"] == "pass"
