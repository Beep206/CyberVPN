# ruff: noqa: S101

from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.util
import json
import socket
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_PATH = REPO_ROOT / "scripts/remnawave/apply-spb-de-exceptions-server-routing.py"


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("spb_de_exceptions_server_routing", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _base_config(*, listen: str | None = "10.0.0.1") -> dict[str, object]:
    raw_inbound: dict[str, object] = {
        "tag": "VLESS_REALITY_443",
        "protocol": "vless",
        "port": 443,
        "streamSettings": {"network": "raw"},
    }
    xhttp_inbound: dict[str, object] = {
        "tag": "VLESS_XHTTP_REALITY_8443",
        "protocol": "vless",
        "port": 8443,
        "streamSettings": {
            "network": "xhttp",
            "xhttpSettings": {"path": "/source-xhttp-path"},
        },
    }
    if listen is not None:
        raw_inbound["listen"] = listen
        xhttp_inbound["listen"] = listen
    return {
        "inbounds": [
            raw_inbound,
            xhttp_inbound,
        ],
        "outbounds": [
            {"tag": "DIRECT", "protocol": "freedom"},
            {"tag": "BLOCK", "protocol": "blackhole"},
            {"tag": "SMART_RU_DE", "protocol": "shadowsocks", "settings": {"servers": []}},
        ],
        "routing": {
            "domainStrategy": "IPIfNonMatch",
            "rules": [
                {
                    "type": "field",
                    "ruleTag": "existing-smart-ru-customer-route",
                    "inboundTag": ["VLESS_REALITY_443", "VLESS_XHTTP_REALITY_8443"],
                    "network": "tcp,udp",
                    "outboundTag": "SMART_RU_DE",
                }
            ],
        },
        "dns": {"servers": ["1.1.1.1"]},
        "policy": {"levels": {"0": {"handshake": 4}}},
        "log": {"loglevel": "warning"},
    }


def _base_profile(uuid: str, name: str) -> dict[str, object]:
    return {
        "uuid": uuid,
        "name": name,
        "config": _base_config(),
        "inbounds": [
            {"tag": "VLESS_REALITY_443", "uuid": f"{uuid}-raw", "port": 443},
            {"tag": "VLESS_XHTTP_REALITY_8443", "uuid": f"{uuid}-xhttp", "port": 8443},
        ],
    }


def _write_artifact(
    tmp_path: Path,
    module: ModuleType,
    *,
    ipv6_mode: str = "disabled",
    include_ipv6: bool = False,
) -> Path:
    artifact_dir = tmp_path / "artifacts" / "antifilter"
    artifact_dir.mkdir(parents=True)
    rules = [{"ruleTag": "fixture-ipv4", "family": "ipv4", "ip": ["8.8.8.0/24"]}]
    if include_ipv6:
        rules.append({"ruleTag": "fixture-ipv6", "family": "ipv6", "ip": ["2001:4860:4860::/48"]})
    rules = {
        "rules": rules,
        "ipv6Policy": {
            "mode": ipv6_mode,
            "unmatched": "normal_profile_policy" if ipv6_mode == "enabled" else "profile_disabled",
        },
    }
    rules_path = artifact_dir / "xray-rules.json"
    rules_bytes = json.dumps(rules, sort_keys=True).encode()
    ipv6_count = 1 if include_ipv6 else 0
    rules_path.write_bytes(rules_bytes)
    manifest = {
        "schemaVersion": 1,
        "product": module.PRODUCT_CODE,
        "generatedAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "ipv6Policy": {"mode": ipv6_mode, "reason": "unit test policy"},
        "union": {
            "prefixCount": 1 + ipv6_count,
            "families": {"ipv4": 1, "ipv6": ipv6_count},
            "sha256": hashlib.sha256(b"canonical-cidr").hexdigest(),
        },
        "artifacts": {
            "xrayRulesPath": "xray-rules.json",
            "xrayRulesSha256": hashlib.sha256(rules_bytes).hexdigest(),
        },
    }
    manifest_path = artifact_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest_path


def _args(tmp_path: Path, manifest_path: Path, module: ModuleType) -> argparse.Namespace:
    return argparse.Namespace(
        apply=False,
        rollback=False,
        artifact_manifest=manifest_path,
        xray_rules_artifact=None,
        max_artifact_age_hours=72,
        remnawave_url="http://remnawave:3000",
        spb_base_profile=module.SPB_BASE_PROFILE_NAME,
        de_base_profile=module.DE_BASE_PROFILE_NAME,
        spb_profile=module.SPB_PROFILE_NAME,
        de_bridge_profile=module.DE_BRIDGE_PROFILE_NAME,
        spb_node_address=module.SPB_NODE_ADDRESS,
        de_node_address=module.DE_NODE_ADDRESS,
        spb_public_host=module.SPB_PUBLIC_HOST,
        spb_preserved_listen_address="10.0.0.1",
        spb_task2_listen_address="10.0.0.2",
        de_bridge_upstream_address=module.DE_BRIDGE_UPSTREAM_ADDRESS,
        customer_squad=module.CUSTOMER_SQUAD_NAME,
        external_squad=module.EXTERNAL_SQUAD_NAME,
        bridge_squad=module.BRIDGE_SQUAD_NAME,
        bridge_username=module.BRIDGE_USERNAME,
        skip_local_socket_preflight=True,
        allow_remnawave_host=["remnawave", "localhost", "127.0.0.1", "::1"],
        trusted_proxy_headers=False,
        rollback_manifest=tmp_path / "rollback.json",
    )


def test_operator_object_names_fit_remnawave_2_8_0_limits() -> None:
    module = _load_module()

    assert len(module.SPB_PROFILE_NAME) <= 30
    assert len(module.DE_BRIDGE_PROFILE_NAME) <= 30
    for spec in module.SPB_PUBLIC_HOST_SPECS:
        assert len(spec["remark"]) <= 40
        assert len(spec["host_tag"]) <= 36


def test_artifact_loader_validates_manifest_rules_and_checksum(tmp_path: Path) -> None:
    module = _load_module()
    manifest_path = _write_artifact(tmp_path, module)

    artifact = module._load_antifilter_artifact(manifest_path)

    assert artifact.union_prefix_count == 1
    assert artifact.union_ipv6_prefix_count == 0
    assert artifact.ipv6_policy_mode == "disabled"
    assert artifact.rules_path.name == "xray-rules.json"
    assert artifact.raw_rules[0]["ip"] == ["8.8.8.0/24"]

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifacts"]["xrayRulesSha256"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(RuntimeError, match="checksum mismatch"):
        module._load_antifilter_artifact(manifest_path)


def test_artifact_loader_rejects_wrong_product_empty_union_and_path_escape(tmp_path: Path) -> None:
    module = _load_module()
    manifest_path = _write_artifact(tmp_path, module)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    manifest["product"] = "premium_smart_ru"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(RuntimeError, match="product"):
        module._load_antifilter_artifact(manifest_path)

    manifest["product"] = module.PRODUCT_CODE
    manifest["union"]["prefixCount"] = 0
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(RuntimeError, match="positive"):
        module._load_antifilter_artifact(manifest_path)

    manifest["union"]["prefixCount"] = 1
    manifest["artifacts"]["xrayRulesPath"] = "../xray-rules.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(RuntimeError, match="under the manifest directory"):
        module._load_antifilter_artifact(manifest_path)

    manifest_path = _write_artifact(tmp_path / "enabled-empty", module, ipv6_mode="enabled")
    with pytest.raises(RuntimeError, match="IPv6 policy is enabled"):
        module._load_antifilter_artifact(manifest_path)

    mismatch_manifest = _write_artifact(tmp_path / "enabled-mismatch", module)
    manifest = json.loads(mismatch_manifest.read_text(encoding="utf-8"))
    manifest["ipv6Policy"]["mode"] = "enabled"
    manifest["union"]["families"]["ipv6"] = 1
    manifest["union"]["prefixCount"] = 2
    mismatch_manifest.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(RuntimeError, match="does not match the Xray artifact"):
        module._load_antifilter_artifact(mismatch_manifest)

    enabled_manifest = _write_artifact(tmp_path / "enabled-ok", module, ipv6_mode="enabled", include_ipv6=True)
    enabled_artifact = module._load_antifilter_artifact(enabled_manifest)
    assert enabled_artifact.ipv6_policy_mode == "enabled"
    assert enabled_artifact.union_ipv6_prefix_count == 1


def test_builds_bridge_and_spb_profile_with_fail_closed_exception_order() -> None:
    module = _load_module()
    artifact_rules = [
        {"ruleTag": "fixture-ipv4", "ip": ["8.8.8.1/24"]},
    ]

    de_config = module._build_de_bridge_config(_base_config())
    rebuilt_de_config = module._build_de_bridge_config(de_config)
    assert [item["tag"] for item in de_config["inbounds"]] == [
        "VLESS_REALITY_443",
        "VLESS_XHTTP_REALITY_8443",
        "DE_SPB_EXCEPTIONS_BRIDGE_9444",
    ]
    assert [item["tag"] for item in rebuilt_de_config["inbounds"]].count("DE_SPB_EXCEPTIONS_BRIDGE_9444") == 1
    assert de_config["outbounds"] == _base_config()["outbounds"]
    bridge_inbound = de_config["inbounds"][-1]
    assert bridge_inbound["tag"] == "DE_SPB_EXCEPTIONS_BRIDGE_9444"
    assert bridge_inbound["port"] == 9444
    assert bridge_inbound["listen"] == "2a0b:4140:ba84::2"
    assert bridge_inbound["protocol"] == "shadowsocks"
    assert bridge_inbound["settings"]["method"] == "chacha20-ietf-poly1305"
    assert bridge_inbound["settings"]["network"] == "tcp,udp"
    assert [rule["ruleTag"] for rule in de_config["routing"]["rules"]] == [
        "task2-de-bridge-management-block",
        "task2-de-bridge-direct",
        "existing-smart-ru-customer-route",
    ]
    assert all(rule["inboundTag"] == ["DE_SPB_EXCEPTIONS_BRIDGE_9444"] for rule in de_config["routing"]["rules"][:2])
    assert de_config["dns"] == _base_config()["dns"]
    assert de_config["policy"] == _base_config()["policy"]
    assert de_config["log"] == _base_config()["log"]

    spb_config = module._build_spb_customer_config(
        _base_config(),
        "unit-test-bridge-password",
        "203.0.113.10",
        artifact_rules,
        ipv6_policy_mode="disabled",
        task2_listen_address="10.0.0.2",
        shared_xhttp_path="/source-xhttp-path",
    )

    assert [item["tag"] for item in spb_config["inbounds"]] == [
        "VLESS_REALITY_443",
        "VLESS_XHTTP_REALITY_8443",
        "SPB_EXCEPTIONS_REALITY_443",
        "SPB_EXCEPTIONS_XHTTP_REALITY_8443",
    ]
    assert spb_config["inbounds"][0]["listen"] == "10.0.0.1"
    assert spb_config["inbounds"][1]["listen"] == "10.0.0.1"
    assert spb_config["inbounds"][2]["listen"] == "10.0.0.2"
    assert spb_config["inbounds"][3]["listen"] == "10.0.0.2"
    assert spb_config["inbounds"][2]["port"] == module.SPB_TASK2_RAW_PORT
    assert spb_config["inbounds"][3]["port"] == module.SPB_TASK2_XHTTP_PORT
    assert (
        spb_config["inbounds"][3]["streamSettings"]["xhttpSettings"]["path"]
        == "/source-xhttp-path"
    )
    assert [item["tag"] for item in spb_config["outbounds"]] == [
        "DIRECT",
        "BLOCK",
        "SMART_RU_DE",
        "DE_EXCEPTIONS_BRIDGE",
    ]
    bridge_outbound = spb_config["outbounds"][-1]
    assert bridge_outbound["settings"]["servers"] == [
        {
            "address": "203.0.113.10",
            "port": 9444,
            "password": "unit-test-bridge-password",
            "method": "chacha20-ietf-poly1305",
            "level": 0,
        }
    ]


def test_preserved_inbounds_are_globally_unique_and_routing_references_follow() -> None:
    module = _load_module()
    base = _base_config()
    artifact_rules = [{"ruleTag": "fixture-ipv4", "ip": ["8.8.8.0/24"]}]

    de_mapping = module._preserved_inbound_tag_map(
        base,
        "de",
        exclude_tags={module.BRIDGE_INBOUND_TAG},
    )
    spb_mapping = module._preserved_inbound_tag_map(
        base,
        "spb",
        exclude_tags=module.SPB_CUSTOMER_INBOUND_TAG_SET | {module.BRIDGE_INBOUND_TAG},
    )
    assert set(de_mapping).isdisjoint(set(de_mapping.values()))
    assert set(spb_mapping).isdisjoint(set(spb_mapping.values()))
    assert set(de_mapping.values()).isdisjoint(set(spb_mapping.values()))
    assert all(
        len(tag) <= module.REMNAWAVE_INBOUND_TAG_MAX_LENGTH for tag in [*de_mapping.values(), *spb_mapping.values()]
    )

    de_config = module._build_de_bridge_config(base, de_mapping)
    assert {item["tag"] for item in de_config["inbounds"]} == {
        *de_mapping.values(),
        module.BRIDGE_INBOUND_TAG,
    }
    assert de_config["routing"]["rules"][-1]["inboundTag"] == [
        de_mapping["VLESS_REALITY_443"],
        de_mapping["VLESS_XHTTP_REALITY_8443"],
    ]

    spb_config = module._build_spb_customer_config(
        base,
        "unit-test-bridge-password",
        "203.0.113.10",
        artifact_rules,
        ipv6_policy_mode="disabled",
        task2_listen_address="10.0.0.2",
        preserved_tag_map=spb_mapping,
    )
    spb_tags = {item["tag"] for item in spb_config["inbounds"]}
    assert set(spb_mapping.values()).issubset(spb_tags)
    assert module.SPB_CUSTOMER_INBOUND_TAG_SET.issubset(spb_tags)
    assert spb_config["routing"]["rules"][-1]["inboundTag"] == [
        spb_mapping["VLESS_REALITY_443"],
        spb_mapping["VLESS_XHTTP_REALITY_8443"],
    ]

    rerun_mapping = module._preserved_inbound_tag_map(
        spb_config,
        "spb",
        exclude_tags=module.SPB_CUSTOMER_INBOUND_TAG_SET | {module.BRIDGE_INBOUND_TAG},
    )
    assert all(source == target for source, target in rerun_mapping.items())

    rules = spb_config["routing"]["rules"]
    assert [rule["ruleTag"] for rule in rules] == [
        "task2-management-private-self-block",
        "task2-bridge-inbound-isolation-block",
        "task2-bittorrent-protocol-block",
        "task2-torrent-domain-block",
        "task2-ads-trackers-block",
        "task2-tor-best-effort-block",
        "task2-smtp-abuse-port-block",
        "task2-ipv6-policy-block",
        "fixture-ipv4",
        "task2-final-spb-direct",
        "existing-smart-ru-customer-route",
    ]
    assert rules[7] == {
        "type": "field",
        "inboundTag": ["SPB_EXCEPTIONS_REALITY_443", "SPB_EXCEPTIONS_XHTTP_REALITY_8443"],
        "ruleTag": "task2-ipv6-policy-block",
        "ip": ["::/0"],
        "outboundTag": "BLOCK",
    }
    assert rules[8]["outboundTag"] == "DE_EXCEPTIONS_BRIDGE"
    assert rules[8]["network"] == "tcp,udp"
    assert rules[8]["ip"] == ["8.8.8.0/24"]
    assert rules[9] == {
        "type": "field",
        "ruleTag": "task2-final-spb-direct",
        "inboundTag": ["SPB_EXCEPTIONS_REALITY_443", "SPB_EXCEPTIONS_XHTTP_REALITY_8443"],
        "network": "tcp,udp",
        "outboundTag": "DIRECT",
    }
    assert rules[-1]["ruleTag"] == "existing-smart-ru-customer-route"
    assert rules[-1]["inboundTag"] == [
        spb_mapping["VLESS_REALITY_443"],
        spb_mapping["VLESS_XHTTP_REALITY_8443"],
    ]
    assert rules[-1]["outboundTag"] == "SMART_RU_DE"
    existing_customer_tags = {"VLESS_REALITY_443", "VLESS_XHTTP_REALITY_8443"}
    for rule in rules[:-1]:
        inbound_tags = rule.get("inboundTag") or []
        assert existing_customer_tags.isdisjoint(set(inbound_tags))
    assert spb_config["dns"]["queryStrategy"] == "UseIPv4"
    assert spb_config["routing"]["domainStrategy"] == "IPOnDemand"
    assert spb_config["dns"]["servers"] == ["1.1.1.1"]
    assert spb_config["policy"] == _base_config()["policy"]
    assert spb_config["log"] == _base_config()["log"]

    base_without_dns_servers = _base_config()
    base_without_dns_servers["dns"] = {"queryStrategy": "UseIP"}
    config_with_dns_fallback = module._build_spb_customer_config(
        base_without_dns_servers,
        "unit-test-bridge-password",
        "203.0.113.10",
        artifact_rules,
        ipv6_policy_mode="fallback_block",
        task2_listen_address="10.0.0.2",
    )
    assert config_with_dns_fallback["dns"]["servers"] == ["localhost"]

    rebuilt_spb_config = module._build_spb_customer_config(
        spb_config,
        "unit-test-bridge-password-2",
        "203.0.113.10",
        artifact_rules,
        ipv6_policy_mode="disabled",
        task2_listen_address="10.0.0.2",
    )
    rebuilt_rule_tags = [rule["ruleTag"] for rule in rebuilt_spb_config["routing"]["rules"]]
    assert rebuilt_rule_tags.count("task2-bridge-inbound-isolation-block") == 1
    assert rebuilt_rule_tags.count("fixture-ipv4") == 1
    assert rebuilt_rule_tags.count("task2-final-spb-direct") == 1


def test_expanded_task2_exception_rule_is_replaced_on_rerun() -> None:
    module = _load_module()
    rule = {
        "type": "field",
        "ruleTag": "antifilter-bgp-fixture",
        "inboundTag": [
            "T2S_VLESS_REALITY_443_3cdea442",
            "T2S_VLESS_XHTTP_REALITY_844_1ec63bc1",
            *module.SPB_CUSTOMER_INBOUND_TAGS,
        ],
        "ip": ["8.8.8.0/24"],
        "outboundTag": module.BRIDGE_OUTBOUND_TAG,
    }

    assert module._is_task2_spb_rule(rule) is True


def test_shared_spb_profile_allows_dedicated_task2_ports_without_listener_collision() -> None:
    module = _load_module()

    spb_config = module._build_spb_customer_config(
        _base_config(listen=None),
        "unit-test-bridge-password",
        "203.0.113.10",
        [{"ruleTag": "fixture-ipv4", "ip": ["8.8.8.0/24"]}],
        ipv6_policy_mode="disabled",
        task2_listen_address=None,
    )

    module._validate_no_active_listener_conflicts(
        spb_config,
        [
            "VLESS_REALITY_443",
            "VLESS_XHTTP_REALITY_8443",
            *module.SPB_CUSTOMER_INBOUND_TAGS,
        ],
        label="SPB dedicated-port Task2 profile",
    )
    assert {
        int(inbound["port"])
        for inbound in spb_config["inbounds"]
        if inbound["tag"] in module.SPB_CUSTOMER_INBOUND_TAG_SET
    } == {module.SPB_TASK2_RAW_PORT, module.SPB_TASK2_XHTTP_PORT}

    isolated_config = module._build_spb_customer_config(
        _base_config(listen="10.0.0.1"),
        "unit-test-bridge-password",
        "203.0.113.10",
        [{"ruleTag": "fixture-ipv4", "ip": ["8.8.8.0/24"]}],
        ipv6_policy_mode="disabled",
        task2_listen_address="10.0.0.2",
    )
    module._validate_no_active_listener_conflicts(
        isolated_config,
        [
            "VLESS_REALITY_443",
            "VLESS_XHTTP_REALITY_8443",
            *module.SPB_CUSTOMER_INBOUND_TAGS,
        ],
        label="SPB shared Task2 profile",
    )

    preserved_tags = ["VLESS_REALITY_443", "VLESS_XHTTP_REALITY_8443"]
    pinned_base = module._pin_preserved_spb_listeners(
        _base_config(listen=None),
        preserved_tags,
        "193.233.91.99",
    )
    ipv6_task2_config = module._build_spb_customer_config(
        pinned_base,
        "unit-test-bridge-password",
        "203.0.113.10",
        [{"ruleTag": "fixture-ipv4", "ip": ["8.8.8.0/24"]}],
        ipv6_policy_mode="disabled",
        task2_listen_address="2a01:e5c0:1368::3",
    )
    module._validate_no_active_listener_conflicts(
        ipv6_task2_config,
        [*preserved_tags, *module.SPB_CUSTOMER_INBOUND_TAGS],
        label="SPB shared Task2 profile",
    )
    listeners = {inbound["tag"]: inbound.get("listen") for inbound in ipv6_task2_config["inbounds"]}
    assert listeners["VLESS_REALITY_443"] == "193.233.91.99"
    assert listeners["VLESS_XHTTP_REALITY_8443"] == "193.233.91.99"
    assert listeners["SPB_EXCEPTIONS_REALITY_443"] == "2a01:e5c0:1368::3"
    assert listeners["SPB_EXCEPTIONS_XHTTP_REALITY_8443"] == "2a01:e5c0:1368::3"

    with pytest.raises(RuntimeError, match="different concrete listen address"):
        module._pin_preserved_spb_listeners(
            _base_config(listen="193.233.91.99"),
            preserved_tags,
            "193.233.91.100",
        )


def test_ipv6_enabled_requires_artifact_and_does_not_insert_fallback_block() -> None:
    module = _load_module()
    spb_config = module._build_spb_customer_config(
        _base_config(),
        "unit-test-bridge-password",
        "203.0.113.10",
        [{"ruleTag": "fixture-ipv6", "ip": ["2001:4860:4860::/48"]}],
        ipv6_policy_mode="enabled",
        task2_listen_address="10.0.0.2",
    )

    rule_tags = [rule["ruleTag"] for rule in spb_config["routing"]["rules"]]
    assert "task2-ipv6-policy-block" not in rule_tags
    assert spb_config["dns"] == _base_config()["dns"]


@pytest.mark.parametrize("bad_ip", ["0.0.0.0/0", "::/0", "10.0.0.0/8", "193.233.91.99/32", "not-a-cidr"])
def test_exception_rules_reject_wildcard_management_and_invalid_cidrs(bad_ip: str) -> None:
    module = _load_module()

    with pytest.raises(RuntimeError):
        module._normalize_exception_rules([{"ruleTag": "bad", "ip": [bad_ip]}])


def test_bridge_port_public_host_and_user_isolation_guards() -> None:
    module = _load_module()

    module._validate_bridge_port_available([{"inbounds": [{"tag": module.BRIDGE_INBOUND_TAG, "port": 9444}]}])
    with pytest.raises(RuntimeError, match="already used"):
        module._validate_bridge_port_available([{"inbounds": [{"tag": "OTHER_BRIDGE", "port": 9444}]}])

    profile = {"inbounds": [{"tag": module.BRIDGE_INBOUND_TAG, "uuid": "bridge-inbound"}]}
    module._validate_no_public_bridge_hosts([], profile)
    for host in (
        {"inbound": {"configProfileInboundUuid": "bridge-inbound"}},
        {"inbound": {"uuid": "bridge-inbound"}},
        {"inboundUuid": "bridge-inbound"},
        {"inbound_uuid": "bridge-inbound"},
        {"configProfileInboundUuid": "bridge-inbound"},
        {"config_profile_inbound_uuid": "bridge-inbound"},
    ):
        with pytest.raises(RuntimeError, match="public Remnawave Host"):
            module._validate_no_public_bridge_hosts([host], profile)

    module._validate_local_bridge_socket_available(0)
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        with pytest.raises(RuntimeError, match="already in use"):
            module._validate_local_bridge_socket_available(listener.getsockname()[1])
    finally:
        listener.close()

    module._validate_existing_bridge_user_isolation(
        {"activeInternalSquads": ["bridge-squad"], "externalSquadUuid": None},
        {"uuid": "bridge-squad"},
    )
    with pytest.raises(RuntimeError, match="non-bridge squad"):
        module._validate_existing_bridge_user_isolation(
            {"activeInternalSquads": ["bridge-squad", "customer-squad"]},
            {"uuid": "bridge-squad"},
        )
    with pytest.raises(RuntimeError, match="external squad"):
        module._validate_existing_bridge_user_isolation(
            {"activeInternalSquads": ["bridge-squad"], "externalSquadUuid": "external"},
            {"uuid": "bridge-squad"},
        )
    module._validate_bridge_squad_inbound_isolation(
        {"uuid": "bridge-squad", "inbounds": ["bridge-inbound"]},
        {"bridge-inbound"},
    )
    with pytest.raises(RuntimeError, match="non-bridge inbound"):
        module._validate_bridge_squad_inbound_isolation(
            {"uuid": "bridge-squad", "inbounds": ["customer-inbound"]},
            {"bridge-inbound"},
        )


def test_dry_run_is_read_only_and_does_not_write_manifest(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _load_module()
    manifest_path = _write_artifact(tmp_path, module)
    instances = []

    class FakeRemnawaveApi:
        def __init__(
            self,
            base_url: str,
            token: str,
            *,
            trusted_proxy_headers: bool = False,
        ) -> None:
            self.base_url = base_url
            self.token = token
            self.trusted_proxy_headers = trusted_proxy_headers
            self.calls: list[tuple[str, str]] = []
            instances.append(self)

        async def request(self, method: str, path: str, **kwargs: object) -> object:
            assert kwargs == {}
            if method != "GET":
                raise AssertionError(f"dry-run mutated through {method} {path}")
            self.calls.append((method, path))
            if path == "/config-profiles":
                return {
                    "configProfiles": [
                        {"uuid": "spb-base", "name": module.SPB_BASE_PROFILE_NAME},
                        {"uuid": "de-base", "name": module.DE_BASE_PROFILE_NAME},
                    ]
                }
            if path == "/config-profiles/spb-base":
                return _base_profile("spb-base", module.SPB_BASE_PROFILE_NAME)
            if path == "/config-profiles/de-base":
                return _base_profile("de-base", module.DE_BASE_PROFILE_NAME)
            if path == "/nodes":
                return {
                    "nodes": [
                        {"uuid": "spb-node", "address": module.SPB_NODE_ADDRESS, "configProfile": {}},
                        {"uuid": "de-node", "address": module.DE_NODE_ADDRESS, "configProfile": {}},
                    ]
                }
            if path == "/hosts":
                return {"hosts": []}
            if path == "/internal-squads":
                return {
                    "internalSquads": [{"uuid": "customer-squad", "name": module.CUSTOMER_SQUAD_NAME, "inbounds": []}]
                }
            if path == "/external-squads":
                return {
                    "externalSquads": [
                        {
                            "uuid": "external-squad",
                            "name": module.EXTERNAL_SQUAD_NAME,
                            "responseHeaders": {},
                        }
                    ]
                }
            if path == f"/users/by-username/{module.BRIDGE_USERNAME}":
                return None
            raise AssertionError(f"unexpected request {method} {path}")

        async def close(self) -> None:
            self.closed = True

    monkeypatch.setattr(module, "RemnawaveApi", FakeRemnawaveApi)
    monkeypatch.setenv("REMNAWAVE_TOKEN", "unit-test-token")

    result = asyncio.run(module._run(_args(tmp_path, manifest_path, module)))

    assert result["mode"] == "dry-run"
    assert result["product"] == "premium_spb_de_exceptions"
    assert result["bridgePort"] == 9444
    assert result["bridgePortFree"] is True
    assert result["bridgeSocketPreflight"] == "skipped"
    assert result["bridgePublicHost"] == "none"
    assert result["spbPublicHost"] == module.SPB_PUBLIC_HOST
    assert result["spbPublicHostCount"] == 2
    assert result["spbTask2ListenAddress"] == "10.0.0.2"
    assert result["ipv6PolicyMode"] == "disabled"
    assert result["artifactUnionIpv6PrefixCount"] == 0
    assert result["bridgeInboundTag"] == "DE_SPB_EXCEPTIONS_BRIDGE_9444"
    assert result["bridgeOutboundTag"] == "DE_EXCEPTIONS_BRIDGE"
    assert result["restartOrder"] == ["de", "spb"]
    assert not (tmp_path / "rollback.json").exists()
    assert len(instances) == 1
    assert instances[0].trusted_proxy_headers is False
    assert all(method == "GET" for method, _path in instances[0].calls)


def test_dry_run_rejects_contaminated_bridge_squad_before_mutation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _load_module()
    manifest_path = _write_artifact(tmp_path, module)

    class FakeRemnawaveApi:
        def __init__(
            self,
            base_url: str,
            token: str,
            *,
            trusted_proxy_headers: bool = False,
        ) -> None:
            self.calls: list[tuple[str, str]] = []

        async def request(self, method: str, path: str, **kwargs: object) -> object:
            if method != "GET":
                raise AssertionError(f"dry-run mutated through {method} {path}")
            self.calls.append((method, path))
            if path == "/config-profiles":
                return {
                    "configProfiles": [
                        {"uuid": "spb-base", "name": module.SPB_BASE_PROFILE_NAME},
                        {"uuid": "de-base", "name": module.DE_BASE_PROFILE_NAME},
                    ]
                }
            if path == "/config-profiles/spb-base":
                return _base_profile("spb-base", module.SPB_BASE_PROFILE_NAME)
            if path == "/config-profiles/de-base":
                return _base_profile("de-base", module.DE_BASE_PROFILE_NAME)
            if path == "/nodes":
                return {
                    "nodes": [
                        {
                            "uuid": "spb-node",
                            "address": module.SPB_NODE_ADDRESS,
                            "configProfile": {},
                        },
                        {
                            "uuid": "de-node",
                            "address": module.DE_NODE_ADDRESS,
                            "configProfile": {},
                        },
                    ]
                }
            if path == "/hosts":
                return {"hosts": []}
            if path == "/internal-squads":
                return {
                    "internalSquads": [
                        {
                            "uuid": "customer-squad",
                            "name": module.CUSTOMER_SQUAD_NAME,
                            "inbounds": [],
                        },
                        {
                            "uuid": "bridge-squad",
                            "name": module.BRIDGE_SQUAD_NAME,
                            "inbounds": ["customer-inbound"],
                        },
                    ]
                }
            if path == "/external-squads":
                return {
                    "externalSquads": [
                        {
                            "uuid": "external-squad",
                            "name": module.EXTERNAL_SQUAD_NAME,
                            "responseHeaders": {},
                        }
                    ]
                }
            if path == f"/users/by-username/{module.BRIDGE_USERNAME}":
                return None
            raise AssertionError(f"unexpected request {method} {path}")

        async def close(self) -> None:
            self.closed = True

    monkeypatch.setattr(module, "RemnawaveApi", FakeRemnawaveApi)
    monkeypatch.setenv("REMNAWAVE_TOKEN", "unit-test-token")

    with pytest.raises(RuntimeError, match="non-bridge inbound"):
        asyncio.run(module._run(_args(tmp_path, manifest_path, module)))

    assert not (tmp_path / "rollback.json").exists()


def test_apply_assigns_customer_squad_only_spb_public_inbounds_and_hosts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _load_module()
    manifest_path = _write_artifact(tmp_path, module)
    de_mapping = module._preserved_inbound_tag_map(_base_config(), "de", exclude_tags={module.BRIDGE_INBOUND_TAG})
    spb_mapping = module._preserved_inbound_tag_map(
        _base_config(),
        "spb",
        exclude_tags=module.SPB_CUSTOMER_INBOUND_TAG_SET | {module.BRIDGE_INBOUND_TAG},
    )
    captured: dict[str, list[dict[str, object]]] = {
        "customer_squad": [],
        "hosts": [],
        "host_patches": [],
        "nodes": [],
    }

    class FakeRemnawaveApi:
        def __init__(
            self,
            base_url: str,
            token: str,
            *,
            trusted_proxy_headers: bool = False,
        ) -> None:
            self.base_url = base_url
            self.token = token
            self.trusted_proxy_headers = trusted_proxy_headers
            self.hosts: list[dict[str, object]] = [
                    {
                        "uuid": "old-spb-host",
                        "remark": "Existing SPB customer RAW",
                        "inbound": {"configProfileInboundUuid": "spb-base-raw"},
                        "excludedInternalSquads": ["customer-squad"],
                    },
                {
                    "uuid": "old-spb-xhttp-host",
                        "remark": "Existing SPB customer XHTTP",
                        "inbound": {"configProfileInboundUuid": "spb-base-xhttp"},
                        "excludedInternalSquads": ["customer-squad"],
                },
                {
                    "uuid": "old-de-host",
                    "remark": "Existing DE customer RAW",
                    "inbound": {"configProfileInboundUuid": "de-base-raw"},
                },
                {
                    "uuid": "old-de-xhttp-host",
                    "remark": "Existing DE customer XHTTP",
                    "inbound": {"configProfileInboundUuid": "de-base-xhttp"},
                },
            ]
            self.configs: dict[str, dict[str, object]] = {}

        async def request(self, method: str, path: str, **kwargs: object) -> object:
            body = kwargs.get("json")
            if path == "/config-profiles" and method == "GET":
                return {
                    "configProfiles": [
                        {"uuid": "spb-base", "name": module.SPB_BASE_PROFILE_NAME},
                        {"uuid": "de-base", "name": module.DE_BASE_PROFILE_NAME},
                    ]
                }
            if path == "/config-profiles/spb-base" and method == "GET":
                return _base_profile("spb-base", module.SPB_BASE_PROFILE_NAME)
            if path == "/config-profiles/de-base" and method == "GET":
                return _base_profile("de-base", module.DE_BASE_PROFILE_NAME)
            if path == "/nodes" and method == "GET":
                return {
                    "nodes": [
                        {
                            "uuid": "spb-node",
                            "address": module.SPB_NODE_ADDRESS,
                            "configProfile": {
                                "activeConfigProfileUuid": "spb-base",
                                "activeInbounds": [{"uuid": "spb-base-raw"}, {"uuid": "spb-base-xhttp"}],
                            },
                        },
                        {
                            "uuid": "de-node",
                            "address": module.DE_NODE_ADDRESS,
                            "configProfile": {
                                "activeConfigProfileUuid": "de-base",
                                "activeInbounds": [{"uuid": "de-base-raw"}, {"uuid": "de-base-xhttp"}],
                            },
                        },
                    ]
                }
            if path == "/hosts" and method == "GET":
                return {"hosts": self.hosts}
            if path == "/internal-squads" and method == "GET":
                return {
                    "internalSquads": [{"uuid": "customer-squad", "name": module.CUSTOMER_SQUAD_NAME, "inbounds": []}]
                }
            if path == "/external-squads" and method == "GET":
                return {
                    "externalSquads": [
                        {"uuid": "external-squad", "name": module.EXTERNAL_SQUAD_NAME, "responseHeaders": {}}
                    ]
                }
            if path == f"/users/by-username/{module.BRIDGE_USERNAME}" and method == "GET":
                return None
            if path == "/config-profiles" and method == "POST":
                assert isinstance(body, dict)
                if body["name"] == module.DE_BRIDGE_PROFILE_NAME:
                    profile = {
                        "uuid": "de-bridge-profile",
                        "name": body["name"],
                        "config": body["config"],
                        "inbounds": [
                            {"tag": de_mapping["VLESS_REALITY_443"], "uuid": "de-raw-clone", "port": 443},
                            {"tag": de_mapping["VLESS_XHTTP_REALITY_8443"], "uuid": "de-xhttp-clone", "port": 8443},
                            {"tag": module.BRIDGE_INBOUND_TAG, "uuid": "bridge-inbound", "port": 9444},
                        ],
                    }
                    self.configs["de-bridge-profile"] = profile
                    return {"uuid": "de-bridge-profile"}
                if body["name"] == module.SPB_PROFILE_NAME:
                    config_inbounds = {item["tag"]: item for item in body["config"]["inbounds"]}
                    assert config_inbounds[spb_mapping["VLESS_REALITY_443"]]["listen"] == "10.0.0.1"
                    assert config_inbounds[spb_mapping["VLESS_XHTTP_REALITY_8443"]]["listen"] == "10.0.0.1"
                    assert config_inbounds["SPB_EXCEPTIONS_REALITY_443"]["listen"] == "10.0.0.2"
                    assert config_inbounds["SPB_EXCEPTIONS_XHTTP_REALITY_8443"]["listen"] == "10.0.0.2"
                    routing_rules = body["config"]["routing"]["rules"]
                    task2_rules = [
                        rule
                        for rule in routing_rules
                        if str(rule.get("ruleTag") or "").startswith("task2-")
                    ]
                    assert task2_rules[-1]["inboundTag"] == [
                        "SPB_EXCEPTIONS_REALITY_443",
                        "SPB_EXCEPTIONS_XHTTP_REALITY_8443",
                    ]
                    exception_rule = next(
                        rule for rule in routing_rules if rule.get("ruleTag") == "fixture-ipv4"
                    )
                    assert exception_rule["inboundTag"] == task2_rules[-1]["inboundTag"]
                    profile = {
                        "uuid": "spb-profile",
                        "name": body["name"],
                        "config": body["config"],
                        "inbounds": [
                            {"tag": spb_mapping["VLESS_REALITY_443"], "uuid": "spb-raw-clone", "port": 443},
                            {"tag": spb_mapping["VLESS_XHTTP_REALITY_8443"], "uuid": "spb-xhttp-clone", "port": 8443},
                            {
                                "tag": "SPB_EXCEPTIONS_REALITY_443",
                                "uuid": "spb-task2-raw",
                                "port": module.SPB_TASK2_RAW_PORT,
                            },
                            {
                                "tag": "SPB_EXCEPTIONS_XHTTP_REALITY_8443",
                                "uuid": "spb-task2-xhttp",
                                "port": module.SPB_TASK2_XHTTP_PORT,
                            },
                        ],
                    }
                    self.configs["spb-profile"] = profile
                    return {"uuid": "spb-profile"}
            if path == "/config-profiles/de-bridge-profile" and method == "GET":
                return self.configs["de-bridge-profile"]
            if path == "/config-profiles/spb-profile" and method == "GET":
                return self.configs["spb-profile"]
            if path == "/internal-squads" and method == "POST":
                return {"uuid": "bridge-squad", "name": module.BRIDGE_SQUAD_NAME, "inbounds": body["inbounds"]}
            if path == "/users" and method == "POST":
                return {
                    "uuid": "bridge-user",
                    "username": module.BRIDGE_USERNAME,
                    "ssPassword": "unit-test-ss-password",
                    "activeInternalSquads": body["activeInternalSquads"],
                    "externalSquadUuid": None,
                }
            if path == "/hosts" and method == "POST":
                assert isinstance(body, dict)
                host = {**body, "uuid": f"host-{len(self.hosts) + 1}"}
                self.hosts.append(host)
                captured["hosts"].append(host)
                return host
            if path == "/hosts" and method == "PATCH":
                assert isinstance(body, dict)
                captured["host_patches"].append(body)
                for host in self.hosts:
                    if host["uuid"] == body["uuid"]:
                        host.update(body)
                        break
                return body
            if path == "/internal-squads" and method == "PATCH":
                assert isinstance(body, dict)
                if body["uuid"] == "customer-squad":
                    captured["customer_squad"].append(body)
                return body
            if path == "/external-squads" and method == "PATCH":
                return body
            if path == "/nodes" and method == "PATCH":
                assert isinstance(body, dict)
                captured["nodes"].append(body)
                return body
            if path in {"/nodes/de-node/actions/restart", "/nodes/spb-node/actions/restart"} and method == "POST":
                return {}
            raise AssertionError(f"unexpected request {method} {path}")

        async def close(self) -> None:
            self.closed = True

    args = _args(tmp_path, manifest_path, module)
    args.apply = True
    monkeypatch.setattr(module, "RemnawaveApi", FakeRemnawaveApi)
    monkeypatch.setenv("REMNAWAVE_TOKEN", "unit-test-token")

    result = asyncio.run(module._run(args))

    assert result["status"] == "applied"
    assert captured["customer_squad"] == [
        {
            "uuid": "customer-squad",
            "inbounds": [
                "spb-task2-raw",
                "spb-task2-xhttp",
            ],
        }
    ]
    assert captured["hosts"]
    assert {host["address"] for host in captured["hosts"]} == {module.SPB_PUBLIC_HOST}
    xhttp_host = next(
        host for host in captured["hosts"] if host["port"] == module.SPB_TASK2_XHTTP_PORT
    )
    assert xhttp_host["path"] == "/source-xhttp-path"
    assert {host["inbound"]["configProfileInboundUuid"] for host in captured["hosts"]} == {
        "spb-task2-raw",
        "spb-task2-xhttp",
    }
    patched_hosts = {patch["uuid"]: patch["inbound"]["configProfileInboundUuid"] for patch in captured["host_patches"]}
    assert patched_hosts["old-spb-host"] == "spb-raw-clone"
    assert patched_hosts["old-spb-xhttp-host"] == "spb-xhttp-clone"
    assert patched_hosts["old-de-host"] == "de-raw-clone"
    assert patched_hosts["old-de-xhttp-host"] == "de-xhttp-clone"
    spb_host_patches = [
        patch
        for patch in captured["host_patches"]
        if patch["uuid"] in {"old-spb-host", "old-spb-xhttp-host"}
    ]
    assert all(patch["excludedInternalSquads"] == [] for patch in spb_host_patches)
    assert "bridge-inbound" not in {host["inbound"]["configProfileInboundUuid"] for host in captured["hosts"]}
    de_node_patch = next(item for item in captured["nodes"] if item["uuid"] == "de-node")
    assert de_node_patch["configProfile"]["activeInbounds"] == [
        "de-raw-clone",
        "de-xhttp-clone",
        "bridge-inbound",
    ]
    spb_node_patch = next(item for item in captured["nodes"] if item["uuid"] == "spb-node")
    assert spb_node_patch["configProfile"]["activeInbounds"] == [
        "spb-raw-clone",
        "spb-xhttp-clone",
        "spb-task2-raw",
        "spb-task2-xhttp",
    ]


def test_manifest_path_mode_and_secret_guard(tmp_path: Path) -> None:
    module = _load_module()

    with pytest.raises(RuntimeError, match="\\.codex"):
        module._validate_manifest_path(REPO_ROOT / ".codex" / "rollback.json")
    with pytest.raises(RuntimeError, match="\\.codex"):
        module._validate_manifest_path(tmp_path / ".codex" / "rollback.json")

    manifest_path = module._validate_manifest_path(tmp_path / "rollback.json")
    module._write_manifest(manifest_path, {"version": 1, "phase": "planned"})
    assert module._read_manifest(manifest_path) == {"version": 1, "phase": "planned"}

    sensitive_path = tmp_path / "sensitive-local-rollback.json"
    sensitive_payload = {
        "version": 1,
        "phase": "planned",
        "profile": {"config": {"outbounds": [{"settings": {"servers": [{"password": "local-rollback-only"}]}}]}},
    }
    module._write_manifest(
        sensitive_path,
        sensitive_payload,
    )
    assert module._read_manifest(sensitive_path) == sensitive_payload

    manifest_path.write_text(json.dumps({"version": 2}), encoding="utf-8")
    with pytest.raises(RuntimeError, match="version"):
        module._read_manifest(manifest_path)


def test_host_snapshots_restore_only_inbound_identity() -> None:
    module = _load_module()
    host = {
        "uuid": "host-uuid",
        "remark": "Existing shared Host",
        "address": "shared.example.test",
        "inbound": {
            "configProfileUuid": "old-profile",
            "configProfileInboundUuid": "old-inbound",
        },
        "excludeFromSubscriptionTypes": ["XRAY_JSON"],
        "unknownRemnawaveField": {"keep": True},
    }
    snapshot = module._safe_host_snapshot(host)
    snapshot["unknownRemnawaveField"]["keep"] = False
    assert host["unknownRemnawaveField"]["keep"] is True

    class FakeRemnawaveApi:
        def __init__(self) -> None:
            self.calls: list[dict[str, object]] = []

        async def request(self, method: str, path: str, **kwargs: object) -> object:
            assert (method, path) == ("PATCH", "/hosts")
            self.calls.append(kwargs["json"])
            return kwargs["json"]

    api = FakeRemnawaveApi()
    asyncio.run(module._restore_host_snapshots(api, [host]))

    assert api.calls == [
        {
            "uuid": "host-uuid",
            "inbound": {
                "configProfileUuid": "old-profile",
                "configProfileInboundUuid": "old-inbound",
            },
            "excludedInternalSquads": [],
        }
    ]


def test_rollback_restores_snapshot_when_first_mutation_response_is_ambiguous(
    tmp_path: Path,
) -> None:
    module = _load_module()

    class CaptureRollbackApi:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str, object]] = []

        async def request(self, method: str, path: str, **kwargs: object) -> object:
            self.calls.append((method, path, kwargs.get("json")))
            if (method, path) in {("GET", "/hosts"), ("GET", "/config-profiles")}:
                return {"hosts": [], "configProfiles": []}
            return {}

    manifest = {
        "version": 1,
        "phase": "rollback_failed",
        "failurePhase": "mutation_started",
        "failureClass": "HTTPStatusError",
        "spbProfile": {
            "uuid": "spb-profile",
            "name": "SPB",
            "config": {"inbounds": []},
        },
        "spbProfileName": module.SPB_PROFILE_NAME,
        "deBridgeProfile": {
            "uuid": "de-profile",
            "name": "DE Bridge",
            "config": {"inbounds": []},
        },
        "deBridgeProfileName": module.DE_BRIDGE_PROFILE_NAME,
        "bridgeUser": {
            "uuid": "bridge-user",
            "activeInternalSquads": [],
            "externalSquadUuid": None,
        },
        "bridgeUsername": module.BRIDGE_USERNAME,
        "bridgeSquad": {"uuid": "bridge-squad", "inbounds": []},
        "bridgeSquadName": module.BRIDGE_SQUAD_NAME,
        "spbHostRemarks": [],
    }
    manifest_path = tmp_path / "rollback.json"
    api = CaptureRollbackApi()

    result = asyncio.run(module._rollback(api, manifest, manifest_path))

    assert ("PATCH", "/config-profiles") in [call[:2] for call in api.calls]
    assert result == {"mode": "rollback", "status": "rolled_back"}
    assert json.loads(manifest_path.read_text(encoding="utf-8"))["phase"] == "rolled_back"


def test_rollback_restores_spb_before_de_and_is_idempotent(tmp_path: Path) -> None:
    module = _load_module()

    class FakeRemnawaveApi:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str, object]] = []

        async def request(self, method: str, path: str, **kwargs: object) -> object:
            self.calls.append((method, path, kwargs.get("json")))
            if (method, path) == ("GET", "/config-profiles"):
                return {"configProfiles": []}
            return {}

    manifest = {
        "version": 1,
        "phase": "applied",
        "product": module.PRODUCT_CODE,
        "spbProfile": {"uuid": "spb-profile", "name": "SPB", "config": {}},
        "spbProfileName": module.SPB_PROFILE_NAME,
        "deBridgeProfile": {"uuid": "de-profile", "name": "DE Bridge", "config": {}},
        "deBridgeProfileName": module.DE_BRIDGE_PROFILE_NAME,
        "spbNode": {"uuid": "spb-node", "configProfile": {"activeConfigProfileUuid": "old-spb"}},
        "deNode": {"uuid": "de-node", "configProfile": {"activeConfigProfileUuid": "old-de"}},
        "customerSquad": {"uuid": "customer-squad", "inbounds": ["old-raw"]},
        "externalSquad": {"uuid": "external-squad", "responseHeaders": {}},
        "bridgeSquad": {"uuid": "bridge-squad", "inbounds": []},
        "bridgeSquadName": module.BRIDGE_SQUAD_NAME,
        "bridgeUser": {"uuid": "bridge-user", "activeInternalSquads": [], "externalSquadUuid": None},
        "bridgeUsername": module.BRIDGE_USERNAME,
        "spbRemappedHosts": [
            {
                "uuid": "spb-remapped-host",
                "inbound": {
                    "configProfileUuid": "old-spb-profile",
                    "configProfileInboundUuid": "old-spb-raw",
                },
            }
        ],
        "deRemappedHosts": [
            {
                "uuid": "de-remapped-host",
                "inbound": {
                    "configProfileUuid": "old-de-profile",
                    "configProfileInboundUuid": "old-de-raw",
                },
            }
        ],
    }
    api = FakeRemnawaveApi()
    manifest_path = tmp_path / "rollback.json"

    result = asyncio.run(module._rollback(api, manifest, manifest_path))

    restart_calls = [call for call in api.calls if call[0] == "POST"]
    assert restart_calls == [
        ("POST", "/nodes/spb-node/actions/restart", {"forceRestart": True}),
        ("POST", "/nodes/de-node/actions/restart", {"forceRestart": True}),
    ]
    spb_restart_index = api.calls.index(restart_calls[0])
    de_restart_index = api.calls.index(restart_calls[1])
    spb_host_restore_index = next(
        index
        for index, call in enumerate(api.calls)
        if call[0:2] == ("PATCH", "/hosts") and call[2]["uuid"] == "spb-remapped-host"
    )
    de_host_restore_index = next(
        index
        for index, call in enumerate(api.calls)
        if call[0:2] == ("PATCH", "/hosts") and call[2]["uuid"] == "de-remapped-host"
    )
    spb_profile_restore_index = next(
        index
        for index, call in enumerate(api.calls)
        if call[0:2] == ("PATCH", "/config-profiles") and call[2]["uuid"] == "spb-profile"
    )
    de_profile_restore_index = next(
        index
        for index, call in enumerate(api.calls)
        if call[0:2] == ("PATCH", "/config-profiles") and call[2]["uuid"] == "de-profile"
    )
    bridge_user_restore_index = next(index for index, call in enumerate(api.calls) if call[0:2] == ("PATCH", "/users"))
    assert spb_host_restore_index < spb_profile_restore_index < spb_restart_index
    assert spb_restart_index < bridge_user_restore_index
    assert bridge_user_restore_index < de_host_restore_index < de_profile_restore_index < de_restart_index
    assert result == {"mode": "rollback", "status": "rolled_back"}
    assert json.loads(manifest_path.read_text(encoding="utf-8"))["phase"] == "rolled_back"

    result_again = asyncio.run(module._rollback(api, {"version": 1, "phase": "rolled_back"}, manifest_path))
    assert result_again == {"mode": "rollback", "status": "already_rolled_back"}


def test_rollback_restores_hosts_before_deleting_created_profiles(tmp_path: Path) -> None:
    module = _load_module()

    class FakeRemnawaveApi:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str, object]] = []

        async def request(self, method: str, path: str, **kwargs: object) -> object:
            self.calls.append((method, path, kwargs.get("json")))
            if (method, path) == ("GET", "/hosts"):
                return {"hosts": []}
            if (method, path) == ("GET", "/config-profiles"):
                return {
                    "configProfiles": [
                        {"uuid": "created-spb-profile", "name": module.SPB_PROFILE_NAME},
                        {
                            "uuid": "created-de-profile",
                            "name": module.DE_BRIDGE_PROFILE_NAME,
                        },
                    ]
                }
            return kwargs.get("json") or {}

    manifest = {
        "version": 1,
        "phase": "spb_profile_ready",
        "product": module.PRODUCT_CODE,
        "spbProfile": None,
        "spbProfileName": module.SPB_PROFILE_NAME,
        "deBridgeProfile": None,
        "deBridgeProfileName": module.DE_BRIDGE_PROFILE_NAME,
        "bridgeSquad": {"uuid": "bridge-squad", "inbounds": []},
        "bridgeSquadName": module.BRIDGE_SQUAD_NAME,
        "bridgeUser": {
            "uuid": "bridge-user",
            "activeInternalSquads": [],
            "externalSquadUuid": None,
        },
        "bridgeUsername": module.BRIDGE_USERNAME,
        "spbRemappedHosts": [
            {
                "uuid": "spb-remapped-host",
                "inbound": {
                    "configProfileUuid": "old-spb-profile",
                    "configProfileInboundUuid": "old-spb-raw",
                },
                "unknownRemnawaveField": "preserve",
            }
        ],
        "deRemappedHosts": [
            {
                "uuid": "de-remapped-host",
                "inbound": {
                    "configProfileUuid": "old-de-profile",
                    "configProfileInboundUuid": "old-de-raw",
                },
            }
        ],
        "spbHosts": [],
    }
    api = FakeRemnawaveApi()

    result = asyncio.run(module._rollback(api, manifest, tmp_path / "rollback.json"))

    spb_host_restore_index = next(
        index
        for index, call in enumerate(api.calls)
        if call[0:2] == ("PATCH", "/hosts") and call[2]["uuid"] == "spb-remapped-host"
    )
    spb_profile_delete_index = next(
        index for index, call in enumerate(api.calls) if call[0:2] == ("DELETE", "/config-profiles/created-spb-profile")
    )
    de_host_restore_index = next(
        index
        for index, call in enumerate(api.calls)
        if call[0:2] == ("PATCH", "/hosts") and call[2]["uuid"] == "de-remapped-host"
    )
    de_profile_delete_index = next(
        index for index, call in enumerate(api.calls) if call[0:2] == ("DELETE", "/config-profiles/created-de-profile")
    )
    restored_spb_host_payload = api.calls[spb_host_restore_index][2]
    assert "unknownRemnawaveField" not in restored_spb_host_payload
    assert spb_host_restore_index < spb_profile_delete_index
    assert de_host_restore_index < de_profile_delete_index
    assert result == {"mode": "rollback", "status": "rolled_back"}


def test_cli_failure_output_is_secret_safe(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    module = _load_module()
    monkeypatch.delenv("REMNAWAVE_TOKEN", raising=False)
    monkeypatch.delenv("REMNAWAVE_API_TOKEN", raising=False)
    monkeypatch.setattr(sys, "argv", ["apply-spb-de-exceptions-server-routing.py"])

    assert module.main() == 1
    captured = capsys.readouterr()
    payload = json.loads(captured.err)
    assert payload["status"] == "failed"
    assert payload["errorClass"] == "RuntimeError"
    assert "REMNAWAVE_TOKEN" not in captured.err
