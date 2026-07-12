from __future__ import annotations

import json
from typing import Any

from src.application.vpn_testing.suite_loader import load_default_route_registries, load_default_suites

EXPECTED_ANTIFILTER_COMMUNITIES = {
    "rkn": {"65444:100"},
    "meta": {"65444:700"},
    "twitter_x": {"65444:710"},
    "netflix": {"65444:720"},
    "cloudfront": {"65444:730"},
    "microsoft": {"65444:740"},
    "amazon": {"65444:750"},
    "openai": {"65444:760"},
    "youtube": {"65444:770"},
    "google": {"65444:780"},
    "telegram": {"65444:790"},
    "discord": {"65444:800"},
    "custom_networks": {"65444:65444"},
}


def _suite() -> dict[str, Any]:
    return next(suite for suite in load_default_suites() if suite["suite_key"] == "premium_spb_de_exceptions_v1")


def _registry() -> dict[str, Any]:
    return next(
        registry
        for registry in load_default_route_registries()
        if registry["registry_key"] == "premium_spb_de_exceptions_v1"
    )


def test_default_loader_registers_premium_spb_de_exceptions_suite_and_registry() -> None:
    suite = _suite()
    registry = _registry()

    assert suite["target_plan_codes"] == ["premium_spb_de_exceptions"]
    assert suite["required_connection_modes"] == ["standard", "stealth", "server_side_de_exceptions"]
    assert suite["required_server_pool"] == ["premium_spb_de_exceptions"]
    assert suite["required_route_registry"] == "premium_spb_de_exceptions_v1"
    assert registry["suite_key"] == suite["suite_key"]


def test_premium_spb_de_exceptions_suite_declares_authoritative_route_contract_without_runtime_claims() -> None:
    metadata = _suite()["metadata"]
    route_semantics = metadata["route_semantics"]

    assert metadata["authoritative_routing"] == "server_side_spb_xray"
    assert metadata["runtime_evidence_status"] == "not_claimed"
    assert metadata["runtime_evidence_required"] is True
    assert metadata["customer_subscription_inbounds"] == [
        "SPB_EXCEPTIONS_REALITY_443",
        "SPB_EXCEPTIONS_XHTTP_REALITY_8443",
    ]
    assert metadata["runtime_routing_ingress"] == {
        "dedicated_ipv4_tags": [
            "SPB_EXCEPTIONS_REALITY_443",
            "SPB_EXCEPTIONS_XHTTP_REALITY_8443",
        ],
        "ports": {"raw": 4443, "xhttp": 8444},
        "expected_total_inbound_tags": 2,
        "shared_with_other_products": False,
    }
    assert route_semantics["unmatched_default"] == {
        "expected_outbound": "DIRECT",
        "expected_egress_region": "SPB",
        "bridge_down_behavior": "continues_direct",
    }
    assert route_semantics["matched_exception"] == {
        "expected_outbound": "DE_EXCEPTIONS_BRIDGE",
        "expected_egress_country": "DE",
        "bridge_down_behavior": "fail_closed",
        "forbidden_fallback_outbound": "DIRECT",
    }
    assert metadata["runtime_matrix"]["client_transports"] == ["raw", "xhttp"]
    assert metadata["runtime_matrix"]["networks"] == ["tcp", "udp"]
    assert "dns_leak_expectation" in metadata["runtime_matrix"]
    assert "ipv6_leak_expectation" in metadata["runtime_matrix"]


def test_premium_spb_de_exceptions_registry_covers_authoritative_exception_categories() -> None:
    suite_categories = {item["key"]: set(item["communities"]) for item in _suite()["metadata"]["antifilter_categories"]}
    matched_routes = [
        route for route in _registry()["routes"] if route["metadata"].get("traffic_class") == "matched_exception"
    ]
    category_routes = [route for route in matched_routes if "category" in route["metadata"]]
    routed_categories = {
        route["metadata"]["category"]: set(route["metadata"]["communities"])
        for route in matched_routes
        if "category" in route["metadata"]
    }

    assert suite_categories == EXPECTED_ANTIFILTER_COMMUNITIES
    assert routed_categories == EXPECTED_ANTIFILTER_COMMUNITIES
    assert {route["metadata"]["probe_network"] for route in category_routes} == {
        "tcp",
        "udp",
    }
    assert all(route["country_code"] == "DE" for route in category_routes)
    assert all(route["metadata"]["expected_outbound"] == "DE_EXCEPTIONS_BRIDGE" for route in category_routes)
    assert all(route["metadata"]["expected_egress_country"] == "DE" for route in category_routes)
    assert all(route["metadata"]["membership"] == "must_be_in_compiled_union" for route in category_routes)
    assert all(route["metadata"]["bridge_down_behavior"] == "fail_closed" for route in category_routes)
    assert all(route["metadata"]["forbidden_outbound_on_bridge_down"] == "DIRECT" for route in category_routes)


def test_premium_spb_de_exceptions_registry_declares_spb_default_and_fail_closed_semantics() -> None:
    routes_by_key = {route["route_key"]: route for route in _registry()["routes"]}
    all_default_routes = [
        route for route in routes_by_key.values() if route["metadata"].get("traffic_class") == "unmatched_default"
    ]
    default_routes = [route for route in all_default_routes if route["route_key"].startswith("default-")]
    matched_routes = [route for route in routes_by_key.values() if route["route_key"].startswith("matched-")]
    bridge_down_matched = routes_by_key["failure-bridge-down-matched-fail-closed"]["metadata"]
    bridge_down_default = routes_by_key["failure-bridge-down-unmatched-stays-direct"]["metadata"]

    assert {
        (route["metadata"].get("transport"), route["metadata"].get("probe_network"))
        for route in default_routes
        if route["route_key"].startswith("default-")
    } == {("raw", "tcp"), ("raw", "udp"), ("xhttp", "tcp"), ("xhttp", "udp")}
    assert all(route["country_code"] == "RU" for route in default_routes)
    assert all(route["metadata"]["expected_outbound"] == "DIRECT" for route in default_routes)
    assert all(route["metadata"]["expected_egress_region"] == "SPB" for route in default_routes)
    assert all(route["metadata"]["membership"] == "must_not_be_in_compiled_union" for route in default_routes)
    assert all(route["metadata"]["bridge_down_behavior"] == "continues_direct" for route in default_routes)
    assert {(route["metadata"]["transport"], route["metadata"]["probe_network"]) for route in matched_routes} == {
        ("raw", "tcp"),
        ("raw", "udp"),
        ("xhttp", "tcp"),
        ("xhttp", "udp"),
    }
    assert all(route["metadata"]["expected_outbound"] == "DE_EXCEPTIONS_BRIDGE" for route in matched_routes)
    assert all(route["metadata"]["forbidden_outbound_on_bridge_down"] == "DIRECT" for route in matched_routes)
    assert all(route["metadata"]["required_evidence"] for route in matched_routes)
    assert bridge_down_matched["expected_failure"] == "connection_fails"
    assert bridge_down_matched["forbidden_outbound"] == "DIRECT"
    assert bridge_down_matched["bridge_down_behavior"] == "fail_closed"
    assert bridge_down_default["expected_outbound"] == "DIRECT"
    assert bridge_down_default["bridge_down_behavior"] == "continues_direct"


def test_premium_spb_de_exceptions_registry_keeps_leak_expectations_and_no_secrets_in_metadata() -> None:
    registry = _registry()
    routes_by_key = {route["route_key"]: route for route in registry["routes"]}
    serialized = json.dumps(registry, sort_keys=True)

    assert routes_by_key["leak-dns-no-policy-bypass"]["metadata"]["dns_leak_expectation"]
    assert routes_by_key["leak-ipv6-approved-or-blocked"]["metadata"]["ipv6_leak_expectation"]
    assert "runtime_transport_profiles" not in serialized
    assert "generated_mihomo_yaml" not in serialized
    assert "password" not in serialized.lower()
    assert "secret" not in serialized.lower()
    assert "token" not in serialized.lower()
    assert "private_key" not in serialized.lower()
    assert '"runtime_evidence_status": "pass"' not in serialized


def test_premium_spb_de_exceptions_registry_routes_have_supported_unique_shape() -> None:
    registry = _registry()
    route_keys = [route["route_key"] for route in registry["routes"]]

    assert len(route_keys) == len(set(route_keys))
    for route in registry["routes"]:
        assert set(route) == {"route_key", "country_code", "node_tags", "expected_modes", "metadata"}
        assert isinstance(route["route_key"], str) and route["route_key"]
        assert isinstance(route["country_code"], str) and route["country_code"]
        assert isinstance(route["node_tags"], list) and route["node_tags"]
        assert isinstance(route["expected_modes"], list) and route["expected_modes"]
        assert isinstance(route["metadata"], dict)
