from __future__ import annotations

import json
from copy import deepcopy
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest

from src.application.vpn_testing.generated_subscription_checker import (
    EXPECTED_PREMIUM_SMART_RU_TRANSPORT_PROFILE_COUNT,
    PREMIUM_SMART_RU_MIHOMO_GROUPS,
    build_subscription_dry_run,
    generated_mihomo_artifact_summary,
    generated_subscription_checks,
)
from src.config.settings import settings

NODE_HOSTS = (
    "de-relay.cyber-vpn.org",
    "nl-4.cyber-vpn.org",
    "msk-relay.cyber-vpn.org",
    "ru-spb-3.cyber-vpn.org",
)
RAW_PORTS = (2053, 443, 2053, 443)
XHTTP_PORTS = (2083, 8443, 2083, 8443)


@pytest.fixture
def smart_ru_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "remnawave_smart_ru_plan_codes", "premium_smart_ru")
    monkeypatch.setattr(settings, "remnawave_smart_ru_internal_squad_uuid", str(uuid4()))
    monkeypatch.setattr(settings, "remnawave_smart_ru_external_squad_uuid", str(uuid4()))
    monkeypatch.setattr(settings, "remnawave_smart_ru_subscription_template_name", "CyberVPN Premium Smart RU")
    monkeypatch.setattr(settings, "vpn_tester_synthetic_users_enabled", False)


def _premium_smart_ru_plan() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        name="premium_smart_ru_30",
        plan_code="premium_smart_ru",
        connection_modes=["standard", "stealth", "smart_routing"],
        server_pool=["premium_smart_ru"],
    )


def _valid_raw_proxy(index: int) -> dict[str, Any]:
    host = NODE_HOSTS[index]
    return {
        "name": f"raw-{index}",
        "type": "vless",
        "server": host,
        "port": RAW_PORTS[index],
        "network": "tcp",
        "tls": True,
        "flow": "xtls-rprx-vision",
        "servername": host,
        "reality-opts": {
            "public-key": f"raw-public-key-{index}",
            "short-id": f"{index:02x}",
        },
    }


def _valid_xhttp_proxy(index: int) -> dict[str, Any]:
    host = NODE_HOSTS[index]
    return {
        "name": f"xhttp-{index}",
        "type": "vless",
        "server": host,
        "port": XHTTP_PORTS[index],
        "network": "xhttp",
        "tls": True,
        "sni": host,
        "reality-opts": {
            "public-key": f"xhttp-public-key-{index}",
            "short-id": f"{index:02x}",
        },
    }


def _generated_mihomo_artifact(
    *,
    raw_count: int = EXPECTED_PREMIUM_SMART_RU_TRANSPORT_PROFILE_COUNT,
    xhttp_count: int = EXPECTED_PREMIUM_SMART_RU_TRANSPORT_PROFILE_COUNT,
    include_all_groups: bool = True,
) -> dict[str, Any]:
    groups = list(PREMIUM_SMART_RU_MIHOMO_GROUPS)
    if not include_all_groups:
        groups.remove("🇳🇱 NL Auto")
    proxies = [
        *[_valid_raw_proxy(index) for index in range(raw_count)],
        *[_valid_xhttp_proxy(index) for index in range(xhttp_count)],
    ]
    return {
        "proxies": proxies,
        "proxy-groups": [
            {
                "name": name,
                "type": "select",
                "proxies": [proxy["name"] for proxy in proxies],
            }
            for name in groups
        ],
        "rules": ["MATCH,🌍 World / EU"],
    }


def _artifact_for_mutation(mutation: str) -> dict[str, Any]:
    if mutation == "no_raw":
        return _generated_mihomo_artifact(raw_count=0)
    if mutation == "three_raw":
        return _generated_mihomo_artifact(raw_count=3)
    if mutation == "three_xhttp":
        return _generated_mihomo_artifact(xhttp_count=3)

    artifact = _generated_mihomo_artifact()
    proxies = deepcopy(artifact["proxies"])
    artifact["proxies"] = proxies
    raw_proxy = next(proxy for proxy in proxies if proxy["name"] == "raw-0")
    xhttp_proxy = next(proxy for proxy in proxies if proxy["name"] == "xhttp-0")

    if mutation == "valid":
        return artifact
    if mutation == "raw_missing_flow":
        raw_proxy.pop("flow")
    elif mutation == "raw_missing_servername":
        raw_proxy.pop("servername", None)
        raw_proxy.pop("sni", None)
    elif mutation == "raw_missing_public_key":
        raw_proxy["reality-opts"].pop("public-key")
    elif mutation == "raw_missing_short_id":
        raw_proxy["reality-opts"].pop("short-id")
    elif mutation == "raw_wrong_port":
        raw_proxy["port"] = 8443
    elif mutation == "xhttp_wrong_port":
        xhttp_proxy["port"] = 443
    else:  # pragma: no cover - guards future table edits
        raise AssertionError(f"Unknown mutation: {mutation}")
    return artifact


def _checks_by_key(artifact: Any = None) -> dict[str, dict[str, Any]]:
    return {
        check["check_key"]: check
        for check in generated_subscription_checks(
            _premium_smart_ru_plan(),
            [],
            generated_mihomo_artifact=artifact,
        )
    }


def test_generated_subscription_requires_real_hardened_mihomo_artifact(smart_ru_settings: None) -> None:
    dry_run = build_subscription_dry_run(
        _premium_smart_ru_plan(),
        [SimpleNamespace(metadata_json={"domain": "gosuslugi.ru"})],
    )
    missing_by_key = _checks_by_key()
    by_key = _checks_by_key(_generated_mihomo_artifact())

    assert dry_run["mihomo"]["groups"] == []
    assert dry_run["mihomo"]["requires_generated_artifact"] is True
    assert missing_by_key["generated_subscription.mihomo_groups"]["status"] == "fail"
    assert missing_by_key["generated_subscription.vless_reality_raw_tcp"]["status"] == "fail"
    assert missing_by_key["generated_subscription.xhttp_transport"]["status"] == "fail"
    assert by_key["generated_subscription.synthetic_safety"]["status"] == "pass"
    assert by_key["generated_subscription.mihomo_groups"]["status"] == "pass"
    assert by_key["generated_subscription.mihomo_groups"]["details"]["missing_groups"] == []
    assert by_key["generated_subscription.vless_reality_raw_tcp"]["status"] == "pass"
    assert by_key["generated_subscription.xhttp_transport"]["status"] == "pass"
    assert by_key["generated_subscription.remnawave_assignment"]["status"] == "pass"
    assert dry_run["mihomo"]["links_redacted"] is True
    assert dry_run["xray"]["links_redacted"] is True


def test_generated_mihomo_summary_counts_only_strict_reality_profiles_and_preserves_digest() -> None:
    artifact = _generated_mihomo_artifact()
    artifact["proxies"].append(
        {
            "name": "loose-xhttp",
            "type": "vless",
            "server": "loose.example.test",
            "port": 8443,
            "network": "xhttp",
        }
    )

    summary = generated_mihomo_artifact_summary(json.dumps(artifact, ensure_ascii=False))

    assert summary["present"] is True
    assert summary["proxy_count"] == 9
    assert summary["xhttp_proxy_count"] == 4
    assert summary["vless_reality_tcp_proxy_count"] == 4
    assert isinstance(summary["sha256"], str)
    assert len(summary["sha256"]) == 64


@pytest.mark.parametrize(
    ("mutation", "raw_status", "xhttp_status", "raw_count", "xhttp_count"),
    [
        pytest.param("valid", "pass", "pass", 4, 4, id="4-raw-4-xhttp-pass"),
        pytest.param("no_raw", "fail", "pass", 0, 4, id="0-raw-4-xhttp-fails-raw"),
        pytest.param("three_raw", "fail", "pass", 3, 4, id="3-raw-4-xhttp-fails-raw"),
        pytest.param("three_xhttp", "pass", "fail", 4, 3, id="4-raw-3-xhttp-fails-xhttp"),
        pytest.param("raw_missing_flow", "fail", "pass", 3, 4, id="raw-without-flow-fails"),
        pytest.param("raw_missing_servername", "fail", "pass", 3, 4, id="raw-without-servername-fails"),
        pytest.param("raw_missing_public_key", "fail", "pass", 3, 4, id="raw-without-public-key-fails"),
        pytest.param("raw_missing_short_id", "fail", "pass", 3, 4, id="raw-without-short-id-field-fails"),
        pytest.param("raw_wrong_port", "fail", "pass", 3, 4, id="raw-wrong-port-fails"),
        pytest.param("xhttp_wrong_port", "pass", "fail", 4, 3, id="xhttp-wrong-port-fails"),
    ],
)
def test_generated_subscription_transport_mutation_cases(
    smart_ru_settings: None,
    mutation: str,
    raw_status: str,
    xhttp_status: str,
    raw_count: int,
    xhttp_count: int,
) -> None:
    by_key = _checks_by_key(_artifact_for_mutation(mutation))
    raw_check = by_key["generated_subscription.vless_reality_raw_tcp"]
    xhttp_check = by_key["generated_subscription.xhttp_transport"]
    group_check = by_key["generated_subscription.mihomo_groups"]

    assert raw_check["status"] == raw_status
    assert raw_check["details"] == {
        "expected_count": EXPECTED_PREMIUM_SMART_RU_TRANSPORT_PROFILE_COUNT,
        "actual_count": raw_count,
        "required_location_count": 4,
        "location_matrix_valid": mutation == "valid" or mutation == "three_xhttp" or mutation == "xhttp_wrong_port",
        "links_redacted": True,
    }
    assert xhttp_check["status"] == xhttp_status
    assert xhttp_check["details"]["expected_count"] == EXPECTED_PREMIUM_SMART_RU_TRANSPORT_PROFILE_COUNT
    assert xhttp_check["details"]["actual_count"] == xhttp_count
    assert xhttp_check["details"]["links_redacted"] is True
    assert group_check["details"]["vless_reality_tcp_proxy_count"] == raw_count
    assert group_check["details"]["xhttp_proxy_count"] == xhttp_count


@pytest.mark.parametrize("transport", ["raw", "xhttp"])
def test_generated_subscription_rejects_duplicate_compensated_location_matrix(
    smart_ru_settings: None,
    transport: str,
) -> None:
    artifact = _generated_mihomo_artifact()
    selected = [
        proxy
        for proxy in artifact["proxies"]
        if (str(proxy.get("network") or "tcp") == "xhttp") is (transport == "xhttp")
    ]
    selected[-1]["server"] = selected[0]["server"]
    selected[-1]["port"] = selected[0]["port"]

    by_key = _checks_by_key(artifact)
    check_key = (
        "generated_subscription.xhttp_transport"
        if transport == "xhttp"
        else "generated_subscription.vless_reality_raw_tcp"
    )

    assert by_key[check_key]["status"] == "fail"
    assert by_key[check_key]["details"]["actual_count"] == 4
    assert by_key[check_key]["details"]["location_matrix_valid"] is False


def test_generated_subscription_preserves_group_validation(smart_ru_settings: None) -> None:
    by_key = _checks_by_key(_generated_mihomo_artifact(include_all_groups=False))
    group_check = by_key["generated_subscription.mihomo_groups"]

    assert group_check["status"] == "fail"
    assert "🇳🇱 NL Auto" in group_check["details"]["missing_groups"]
    assert by_key["generated_subscription.vless_reality_raw_tcp"]["status"] == "pass"
    assert by_key["generated_subscription.xhttp_transport"]["status"] == "pass"
