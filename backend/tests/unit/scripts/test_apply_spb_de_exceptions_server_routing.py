# ruff: noqa: S101

from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.util
import json
import os
import socket
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType, SimpleNamespace

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


NODE_PLUGIN_UUID = "torrent-blocker-plugin"


def _nodes_with_torrent_blocker(module: ModuleType, nodes: list[dict[str, object]]) -> list[dict[str, object]]:
    by_address = {str(node.get("address")): dict(node) for node in nodes}
    for address, node_uuid in (
        (module.SPB_NODE_ADDRESS, "spb-node"),
        (module.DE_NODE_ADDRESS, "de-node"),
        (module.NL_NODE_ADDRESS, "nl-node"),
        (module.MOSCOW_NODE_ADDRESS, "moscow-node"),
    ):
        node = by_address.setdefault(
            address,
            {"uuid": node_uuid, "address": address, "configProfile": {}},
        )
        node["activePluginUuid"] = NODE_PLUGIN_UUID
        node["isConnected"] = True
        node["isDisabled"] = False
        node["isConnecting"] = False
        node["versions"] = {"node": "2.8.0", "xray": "26.6.27"}
        node["system"] = {"info": {"platform": "linux", "release": "6.8.0-79-generic"}}
    return list(by_address.values())


def _torrent_blocker_plugins(module: ModuleType) -> dict[str, object]:
    return {
        "nodePlugins": [
            {
                "uuid": NODE_PLUGIN_UUID,
                "name": module.EXPECTED_NODE_PLUGIN_NAME,
                "pluginConfig": {
                    "torrentBlocker": {
                        "enabled": True,
                        "ignoreLists": {"ip": [], "userId": []},
                        "blockDuration": module.EXPECTED_TORRENT_BLOCKER_DURATION,
                    }
                },
            }
        ]
    }


def _stub_published_artifact(
    monkeypatch: pytest.MonkeyPatch,
    module: ModuleType,
    manifest_path: Path,
) -> None:
    artifact = module._load_antifilter_artifact(manifest_path)
    evidence = module.PublishedArtifactEvidence(
        active_version="a" * 64,
        active_manifest_sha256=artifact.manifest_sha256,
        lkg_version="b" * 64,
        lkg_manifest_sha256="c" * 64,
        policy_sha256="d" * 64,
        source_manifest_sha256="e" * 64,
        safety_status="accepted",
    )

    def load_stub(*args: object, **kwargs: object) -> tuple[object, object]:
        return artifact, evidence

    monkeypatch.setattr(module, "_load_published_antifilter_artifact", load_stub)


def _task2_target_profile(module: ModuleType) -> dict[str, object]:
    base_config = _base_config()
    preserved_tag_map = module._preserved_inbound_tag_map(
        base_config,
        "spb",
        exclude_tags=module.SPB_CUSTOMER_INBOUND_TAG_SET | {module.BRIDGE_INBOUND_TAG},
    )
    config = module._build_spb_customer_config(
        base_config,
        "bridge-secret",
        module.DE_BRIDGE_UPSTREAM_ADDRESS,
        [],
        ipv6_policy_mode="enabled",
        task2_listen_address="10.0.0.2",
        preserved_tag_map=preserved_tag_map,
    )
    return {
        "uuid": "spb-active",
        "name": module.SPB_PROFILE_NAME,
        "config": config,
        "inbounds": [
            {
                "tag": inbound["tag"],
                "uuid": f"spb-active-{index}",
                "port": inbound["port"],
            }
            for index, inbound in enumerate(config["inbounds"], start=1)
        ],
    }


def _contaminated_supplemental_torrent_policy_config() -> dict[str, object]:
    config = _base_config()
    outbounds = config["outbounds"]
    assert isinstance(outbounds, list)
    outbounds.append({"tag": "innocent-sink", "protocol": "blackhole"})
    config["routing"] = {
        "domainStrategy": "IPIfNonMatch",
        "rules": [
            {
                "type": "field",
                "ruleTag": "legacy-bittorrent-protocol-block",
                "protocol": ["bittorrent"],
                "outboundTag": "BLOCK",
            },
            {
                "type": "field",
                "ruleTag": "plugin-shaped-manual-bittorrent-block",
                "protocol": ["bittorrent"],
                "outboundTag": "RW_TB_OUTBOUND_BLOCK",
            },
            {
                "type": "field",
                "ruleTag": "plugin-shaped-manual-catalog-block",
                "domain": ["domain:rutor.info"],
                "outboundTag": "RW_TB_OUTBOUND_BLOCK",
            },
            {
                "type": "field",
                "ruleTag": "scalar-domain-catalog-block",
                "domain": "domain:rutracker.org",
                "outboundTag": "BLOCK",
            },
            {
                "type": "field",
                "ruleTag": "scalar-full-catalog-block",
                "domain": " Full:RuTor.Info ",
                "outboundTag": "RW_TB_OUTBOUND_BLOCK",
            },
            {
                "type": "field",
                "ruleTag": "regexp-catalog-block",
                "domain": [r"regexp:.*rutracker\.org$"],
                "outboundTag": "BLOCK",
            },
            {
                "type": "field",
                "ruleTag": "keyword-catalog-block",
                "domain": "keyword:rutor",
                "outboundTag": "RW_TB_OUTBOUND_BLOCK",
            },
            {
                "type": "field",
                "ruleTag": "custom-blackhole-catalog-block",
                "domain": "keyword:rutor",
                "outboundTag": "innocent-sink",
            },
            {
                "type": "field",
                "ruleTag": "legacy-qbittorrent-process-block",
                "process": ["qbittorrent"],
                "outboundTag": "BLOCK",
            },
            {
                "type": "field",
                "ruleTag": "task2-torrent-domain-block",
                "domain": ["domain:kinozal.tv"],
                "outboundTag": "BLOCK",
            },
            {
                "type": "field",
                "ruleTag": "legacy-mixed-catalog-block",
                "domain": [
                    "domain:rutracker.org",
                    "domain:rutor.info",
                    "domain:malware.test",
                ],
                "outboundTag": "BLOCK",
            },
            {
                "type": "field",
                "ruleTag": "normal-rutracker-website-route",
                "domain": ["domain:rutracker.org"],
                "outboundTag": "DIRECT",
            },
            {
                "type": "field",
                "ruleTag": "normal-scalar-rutracker-website-route",
                "domain": "full:rutracker.org",
                "outboundTag": "DIRECT",
            },
            {
                "type": "field",
                "ruleTag": "keep-unrelated-block-domain",
                "domain": ["domain:malware.test"],
                "outboundTag": "BLOCK",
            },
            {
                "type": "field",
                "ruleTag": "keep-tor-onion-block",
                "domain": [r"regexp:\.onion$"],
                "outboundTag": "BLOCK",
            },
        ],
    }
    return config


def _assert_supplemental_torrent_policy_sanitized(config: dict[str, object]) -> None:
    inbounds = config["inbounds"]
    assert isinstance(inbounds, list)
    for inbound in inbounds:
        assert isinstance(inbound, dict)
        sniffing = inbound["sniffing"]
        assert sniffing["enabled"] is True
        assert {"http", "tls", "quic"}.issubset(set(sniffing["destOverride"]))
        assert sniffing["routeOnly"] is True

    routing = config["routing"]
    assert isinstance(routing, dict)
    rules = routing["rules"]
    assert isinstance(rules, list)
    rules_json = json.dumps(rules, sort_keys=True).casefold()
    assert "bittorrent" not in rules_json
    assert "qbittorrent" not in rules_json
    assert "task2-torrent-domain-block" not in rules_json
    assert "rw_tb_outbound_block" not in rules_json
    assert "scalar-domain-catalog-block" not in rules_json
    assert "scalar-full-catalog-block" not in rules_json
    assert "regexp-catalog-block" not in rules_json
    assert "keyword-catalog-block" not in rules_json
    assert "custom-blackhole-catalog-block" not in rules_json

    blocked_domains = {
        domain
        for rule in rules
        if isinstance(rule, dict) and rule.get("outboundTag") == "BLOCK"
        for domain in rule.get("domain", [])
    }
    assert "domain:rutracker.org" not in blocked_domains
    assert "domain:rutor.info" not in blocked_domains
    assert "domain:kinozal.tv" not in blocked_domains
    assert "domain:malware.test" in blocked_domains
    assert r"regexp:\.onion$" in blocked_domains
    assert any(
        isinstance(rule, dict)
        and rule.get("ruleTag") == "normal-rutracker-website-route"
        and rule.get("outboundTag") == "DIRECT"
        and rule.get("domain") == ["domain:rutracker.org"]
        for rule in rules
    )
    assert any(
        isinstance(rule, dict)
        and rule.get("ruleTag") == "normal-scalar-rutracker-website-route"
        and rule.get("outboundTag") == "DIRECT"
        and rule.get("domain") == "full:rutracker.org"
        for rule in rules
    )


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
        artifact_store=tmp_path / "published-store",
        artifact_policy=tmp_path / "production-policy.json",
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
        spb_connect_address=module.SPB_CONNECT_ADDRESS,
        spb_preserved_listen_address="10.0.0.1",
        spb_task2_listen_address="10.0.0.2",
        de_bridge_upstream_address=module.DE_BRIDGE_UPSTREAM_ADDRESS,
        customer_squad=module.CUSTOMER_SQUAD_NAME,
        external_squad=module.EXTERNAL_SQUAD_NAME,
        bridge_squad=module.BRIDGE_SQUAD_NAME,
        bridge_username=module.BRIDGE_USERNAME,
        task2_route_evidence_enabled="false",
        task2_xray_webhook_secret="",
        task2_synthetic_user="",
        task2_synthetic_xray_email="",
        task2_route_evidence_webhook_url=module.TASK2_ROUTE_EVIDENCE_WEBHOOK_URL,
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


def test_spb_connect_address_requires_literal_ipv4() -> None:
    module = _load_module()

    assert module._validate_spb_connect_address("193.233.91.99", node_address="193.233.91.99") == "193.233.91.99"
    with pytest.raises(RuntimeError, match="literal IPv4"):
        module._validate_spb_connect_address("spb-exceptions.cyber-vpn.org", node_address="193.233.91.99")
    with pytest.raises(RuntimeError, match="literal IPv4"):
        module._validate_spb_connect_address("2a01:e5c0:1368::3", node_address="193.233.91.99")
    with pytest.raises(RuntimeError, match="literal IPv4"):
        module._validate_spb_connect_address("127.0.0.1", node_address="127.0.0.1")
    with pytest.raises(RuntimeError, match="literal IPv4"):
        module._validate_spb_connect_address("224.0.0.1", node_address="224.0.0.1")
    with pytest.raises(RuntimeError, match="selected SPB node"):
        module._validate_spb_connect_address("193.233.91.99", node_address="203.0.113.10")


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


def test_published_artifact_binding_uses_only_active_pointer_selection(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _load_module()
    manifest_path = _write_artifact(tmp_path, module)
    manifest_sha256 = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    policy = object()
    published = SimpleNamespace(
        active_pointer=SimpleNamespace(
            version="a" * 64,
            manifest_sha256=manifest_sha256,
        ),
        lkg_pointer=SimpleNamespace(
            version="b" * 64,
            manifest_sha256="c" * 64,
        ),
        version_dir=manifest_path.parent,
        manifest={"safety": {"status": "accepted", "reasons": []}},
        policy_sha256="d" * 64,
        source_manifest_sha256="e" * 64,
    )
    monkeypatch.setattr(module, "load_antifilter_policy", lambda path: policy)
    monkeypatch.setattr(
        module,
        "load_published_active_candidate",
        lambda store, *, policy: published,
    )

    artifact, evidence = module._load_published_antifilter_artifact(
        tmp_path / "published-store",
        tmp_path / "production-policy.json",
        expected_manifest_path=manifest_path,
        rules_path=None,
        max_age_hours=72,
    )

    assert artifact.manifest_path == manifest_path.resolve()
    assert evidence.active_manifest_sha256 == manifest_sha256
    assert evidence.active_version == "a" * 64
    assert evidence.lkg_version == "b" * 64
    assert evidence.safety_status == "accepted"

    with pytest.raises(RuntimeError, match="not the published active manifest"):
        module._load_published_antifilter_artifact(
            tmp_path / "published-store",
            tmp_path / "production-policy.json",
            expected_manifest_path=tmp_path / "unpublished" / "manifest.json",
            rules_path=None,
            max_age_hours=72,
        )


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
    assert spb_config["inbounds"][3]["streamSettings"]["xhttpSettings"]["path"] == "/source-xhttp-path"
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


def test_task2_route_evidence_disabled_by_default_emits_no_webhooks() -> None:
    module = _load_module()

    config = module._build_spb_customer_config(
        _base_config(),
        "unit-test-bridge-password",
        "203.0.113.10",
        [{"ruleTag": "fixture-ipv4", "ip": ["8.8.8.0/24"]}],
        ipv6_policy_mode="disabled",
        task2_listen_address="10.0.0.2",
    )

    assert all("webhook" not in rule for rule in config["routing"]["rules"])
    assert all("user" not in rule for rule in config["routing"]["rules"])


def test_task2_route_evidence_config_is_all_or_none_and_https_only(tmp_path: Path) -> None:
    module = _load_module()
    args = _args(tmp_path, tmp_path / "manifest.json", module)

    assert module._task2_route_evidence_config(args) == module.Task2RouteEvidenceConfig(enabled=False)

    args.task2_route_evidence_enabled = "true"
    with pytest.raises(RuntimeError, match="synthetic user"):
        module._task2_route_evidence_config(args)

    args.task2_synthetic_user = "task2_probe"
    with pytest.raises(RuntimeError, match="webhook secret"):
        module._task2_route_evidence_config(args)

    args.task2_xray_webhook_secret = "unit-test-secret"
    args.task2_route_evidence_webhook_url = module.TASK2_ROUTE_EVIDENCE_WEBHOOK_URL.replace("https://", "http://")
    with pytest.raises(RuntimeError, match="HTTPS"):
        module._task2_route_evidence_config(args)

    args.task2_route_evidence_webhook_url = (
        "https://api.cyber-vpn.net/api/v1/admin/vpn-tester/internal/task2/route-evidence/xray-routing-webhook"
    )
    with pytest.raises(RuntimeError, match="host"):
        module._task2_route_evidence_config(args)

    args.task2_route_evidence_webhook_url = module.TASK2_ROUTE_EVIDENCE_WEBHOOK_URL
    config = module._task2_route_evidence_config(args)
    assert config.enabled is True
    assert config.synthetic_user == "task2_probe"
    assert config.synthetic_xray_email == ""
    assert config.webhook_url == module.TASK2_ROUTE_EVIDENCE_WEBHOOK_URL

    args.task2_synthetic_xray_email = "0042"
    with pytest.raises(RuntimeError, match="positive decimal tId"):
        module._task2_route_evidence_config(args)

    args.task2_synthetic_xray_email = "42"
    assert module._task2_route_evidence_config(args).synthetic_xray_email == "42"


def test_task2_route_evidence_parser_uses_exact_env_names(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_module()
    monkeypatch.setenv("VPN_TESTER_TASK2_ROUTE_EVIDENCE_ENABLED", "true")
    monkeypatch.setenv("VPN_TESTER_TASK2_XRAY_WEBHOOK_SECRET", "env-secret")
    monkeypatch.setenv("VPN_TESTER_TASK2_SYNTHETIC_USER", "env_task2_probe")
    monkeypatch.setenv("VPN_TESTER_TASK2_SYNTHETIC_XRAY_EMAIL", "42")
    monkeypatch.setattr(sys, "argv", ["apply-spb-de-exceptions-server-routing.py"])

    args = module._parse_args()

    assert args.task2_route_evidence_enabled == "true"
    assert args.task2_xray_webhook_secret == "env-secret"
    assert args.task2_synthetic_user == "env_task2_probe"
    assert args.task2_synthetic_xray_email == "42"
    assert args.task2_route_evidence_webhook_url == module.TASK2_ROUTE_EVIDENCE_WEBHOOK_URL


def test_task2_synthetic_user_tag_fits_remnawave_2_8_contract() -> None:
    module = _load_module()

    assert module.TASK2_SYNTHETIC_USER_TAG == "TASK2_ROUTE_TEST"
    assert len(module.TASK2_SYNTHETIC_USER_TAG) <= 16


def test_task2_route_evidence_webhooks_are_synthetic_only_and_ordered() -> None:
    module = _load_module()
    route_evidence = module.Task2RouteEvidenceConfig(
        enabled=True,
        synthetic_user="task2_probe_username",
        synthetic_xray_email="42",
        webhook_url=module.TASK2_ROUTE_EVIDENCE_WEBHOOK_URL,
        webhook_secret="unit-test-secret",
    )

    config = module._build_spb_customer_config(
        _base_config(),
        "unit-test-bridge-password",
        "203.0.113.10",
        [
            {"ruleTag": "fixture-ipv4", "ip": ["8.8.8.0/24"]},
            {"ruleTag": "fixture-ipv4-alt", "ip": ["9.9.9.0/24"]},
        ],
        ipv6_policy_mode="disabled",
        task2_listen_address="10.0.0.2",
        route_evidence=route_evidence,
    )

    rules = config["routing"]["rules"]
    tags = [rule["ruleTag"] for rule in rules]
    synthetic_tags = [
        "task2-route-evidence-matched-0001-fixture-ipv4",
        "task2-route-evidence-matched-0002-fixture-ipv4-alt",
        "task2-route-evidence-unmatched-direct",
    ]
    synthetic_rules = [rules[tags.index(tag)] for tag in synthetic_tags]
    assert module.TASK2_XRAY_WEBHOOK_DEDUPLICATION_SECONDS == 0
    assert tags.index("task2-management-private-self-block") < tags.index(synthetic_tags[0])
    assert tags.index("task2-ipv6-policy-block") < tags.index(synthetic_tags[0])
    assert tags.index(synthetic_tags[-1]) < tags.index("fixture-ipv4")
    assert tags.index("fixture-ipv4-alt") < tags.index("task2-final-spb-direct")
    assert synthetic_rules[0]["outboundTag"] == module.BRIDGE_OUTBOUND_TAG
    assert synthetic_rules[0]["ip"] == ["8.8.8.0/24"]
    assert synthetic_rules[1]["outboundTag"] == module.BRIDGE_OUTBOUND_TAG
    assert synthetic_rules[2]["outboundTag"] == "DIRECT"
    assert synthetic_rules[2]["network"] == "tcp,udp"

    for rule in synthetic_rules:
        assert rule["user"] == ["42"]
        assert rule["webhook"] == {
            "url": module.TASK2_ROUTE_EVIDENCE_WEBHOOK_URL,
            "deduplication": module.TASK2_XRAY_WEBHOOK_DEDUPLICATION_SECONDS,
            "headers": {module.TASK2_XRAY_WEBHOOK_AUTH_HEADER: "unit-test-secret"},
        }

    ordinary_rules = [rule for rule in rules if rule["ruleTag"] not in synthetic_tags]
    assert ordinary_rules[-2]["ruleTag"] == "task2-final-spb-direct"
    assert all("webhook" not in rule for rule in ordinary_rules)
    assert all("user" not in rule for rule in ordinary_rules)


def test_task2_route_evidence_user_matcher_uses_exact_remnawave_tid() -> None:
    module = _load_module()
    route_evidence = module.Task2RouteEvidenceConfig(
        enabled=True,
        synthetic_user="task2_probe_username",
        synthetic_xray_email="42",
        webhook_url=module.TASK2_ROUTE_EVIDENCE_WEBHOOK_URL,
        webhook_secret="unit-test-secret",
    )
    remnawave_user = {
        "uuid": "550e8400-e29b-41d4-a716-446655440000",
        "shortUuid": "SHORT123",
        "username": "task2_probe_username",
        "tId": 42,
        "vlessUuid": "550e8400-e29b-41d4-a716-446655440002",
        "tag": module.TASK2_SYNTHETIC_USER_TAG,
    }

    module._validate_existing_task2_synthetic_user(
        remnawave_user,
        expected_username=route_evidence.synthetic_user,
    )
    bound = module._bind_task2_synthetic_xray_email(route_evidence, remnawave_user)
    rules = module._task2_route_evidence_rules(
        [
            {
                "ruleTag": "fixture-ipv4",
                "inboundTag": module.SPB_CUSTOMER_INBOUND_TAGS,
                "ip": ["8.8.8.0/24"],
                "outboundTag": module.BRIDGE_OUTBOUND_TAG,
            }
        ],
        module.SPB_CUSTOMER_INBOUND_TAGS,
        bound,
    )

    assert remnawave_user["username"] != remnawave_user["shortUuid"]
    assert remnawave_user["username"] != remnawave_user["vlessUuid"]
    assert rules[0]["user"] == ["42"]
    assert rules[0]["user"] != [remnawave_user["username"]]
    assert rules[0]["user"] != [remnawave_user["shortUuid"]]
    assert rules[0]["user"] != [remnawave_user["vlessUuid"]]

    with pytest.raises(RuntimeError, match="does not match"):
        module._bind_task2_synthetic_xray_email(
            module.Task2RouteEvidenceConfig(
                enabled=True,
                synthetic_user="task2_probe_username",
                synthetic_xray_email="43",
            ),
            remnawave_user,
        )


def test_task2_route_evidence_rejects_missing_remnawave_tid() -> None:
    module = _load_module()
    route_evidence = module.Task2RouteEvidenceConfig(
        enabled=True,
        synthetic_user="task2_probe_username",
    )

    with pytest.raises(RuntimeError, match="positive tId"):
        module._bind_task2_synthetic_xray_email(
            route_evidence,
            {
                "uuid": "550e8400-e29b-41d4-a716-446655440000",
                "username": "task2_probe_username",
                "tag": module.TASK2_SYNTHETIC_USER_TAG,
            },
        )


def test_task1_bridge_listeners_are_rebound_to_node_owned_ipv6_addresses() -> None:
    module = _load_module()
    de_base = _base_config()
    de_base["inbounds"].append(
        {
            "tag": module.TASK1_DE_GLOBAL_BRIDGE_INBOUND_TAG,
            "port": module.TASK1_BRIDGE_PORT,
            "listen": "0.0.0.0",
            "protocol": "shadowsocks",
            "settings": {"clients": [], "network": "tcp,udp"},
        }
    )

    de_config = module._build_de_bridge_config(de_base)
    task1_de_bridge = next(
        inbound for inbound in de_config["inbounds"] if inbound["tag"] == module.TASK1_DE_GLOBAL_BRIDGE_INBOUND_TAG
    )
    assert task1_de_bridge["listen"] == module.DE_BRIDGE_LISTEN_ADDRESS

    moscow_config = {
        "inbounds": [
            {
                "tag": "MSK_SMART_RU_BRIDGE_V2_9443",
                "port": module.TASK1_BRIDGE_PORT,
                "listen": "0.0.0.0",
                "protocol": "shadowsocks",
                "settings": {"clients": [], "network": "tcp,udp"},
            }
        ],
        "routing": {"rules": []},
    }
    sanitized = module._sanitize_supplemental_torrent_policy_config(moscow_config)
    assert sanitized["inbounds"][0]["listen"] == module.TASK1_MOSCOW_BRIDGE_LISTEN_ADDRESS


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
    for inbound in spb_config["inbounds"]:
        if inbound["tag"] not in module.SPB_CUSTOMER_INBOUND_TAG_SET:
            continue
        sniffing = inbound["sniffing"]
        assert sniffing["enabled"] is True
        assert {"http", "tls", "quic"}.issubset(set(sniffing["destOverride"]))
        assert sniffing["routeOnly"] is True
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
        "task2-ads-trackers-block",
        "task2-tor-best-effort-block",
        "task2-smtp-abuse-port-block",
        "task2-ipv6-policy-block",
        "fixture-ipv4",
        "task2-final-spb-direct",
        "existing-smart-ru-customer-route",
    ]
    assert not any("bittorrent" in json.dumps(rule, sort_keys=True).lower() for rule in rules)
    assert not any("torrent" in json.dumps(rule, sort_keys=True).lower() for rule in rules)
    assert rules[5] == {
        "type": "field",
        "inboundTag": ["SPB_EXCEPTIONS_REALITY_443", "SPB_EXCEPTIONS_XHTTP_REALITY_8443"],
        "ruleTag": "task2-ipv6-policy-block",
        "ip": ["::/0"],
        "outboundTag": "BLOCK",
    }
    assert rules[6]["outboundTag"] == "DE_EXCEPTIONS_BRIDGE"
    assert rules[6]["network"] == "tcp,udp"
    assert rules[6]["ip"] == ["8.8.8.0/24"]
    assert rules[7] == {
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
    assert spb_config["dns"]["servers"] == [
        "https+local://1.1.1.1/dns-query",
        "https+local://8.8.8.8/dns-query",
    ]
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
    assert config_with_dns_fallback["dns"]["servers"] == [
        "https+local://1.1.1.1/dns-query",
        "https+local://8.8.8.8/dns-query",
    ]

    base_with_local_dns = _base_config()
    base_with_local_dns["dns"] = {"servers": ["localhost"], "queryStrategy": "UseIP"}
    config_with_local_dns = module._build_spb_customer_config(
        base_with_local_dns,
        "unit-test-bridge-password",
        "203.0.113.10",
        artifact_rules,
        ipv6_policy_mode="fallback_block",
        task2_listen_address="10.0.0.2",
    )
    assert config_with_local_dns["dns"]["servers"] == [
        "https+local://1.1.1.1/dns-query",
        "https+local://8.8.8.8/dns-query",
    ]

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


def test_extend_preserved_squads_adds_rebuilt_clone_inbounds_without_removing_originals() -> None:
    module = _load_module()
    source_profile = _base_profile("spb-base", module.SPB_BASE_PROFILE_NAME)
    tag_map = module._preserved_inbound_tag_map(
        source_profile["config"],
        "spb",
        exclude_tags=module.SPB_CUSTOMER_INBOUND_TAG_SET | {module.BRIDGE_INBOUND_TAG},
    )
    target_profile = {
        "uuid": "rebuilt-spb-profile",
        "name": module.SPB_PROFILE_NAME,
        "inbounds": [
            {
                "tag": tag_map["VLESS_REALITY_443"],
                "uuid": "rebuilt-spb-raw-clone",
                "port": 443,
            },
            {
                "tag": tag_map["VLESS_XHTTP_REALITY_8443"],
                "uuid": "rebuilt-spb-xhttp-clone",
                "port": 8443,
            },
        ],
    }
    squad = {
        "uuid": "premium-smart-ru-squad",
        "name": "CYBERVPN_PREMIUM_SMART_RU_NODES",
        "inbounds": [
            {"uuid": "spb-base-raw"},
            {"uuid": "spb-base-xhttp"},
        ],
    }
    snapshots = module._preserved_squad_snapshots(
        [squad],
        source_profile,
        ["VLESS_REALITY_443", "VLESS_XHTTP_REALITY_8443"],
    )
    assert snapshots == [
        {
            "uuid": "premium-smart-ru-squad",
            "name": "CYBERVPN_PREMIUM_SMART_RU_NODES",
            "inbounds": ["spb-base-raw", "spb-base-xhttp"],
        }
    ]

    class FakeRemnawaveApi:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str, object]] = []

        async def request(self, method: str, path: str, **kwargs: object) -> object:
            self.calls.append((method, path, kwargs.get("json")))
            return kwargs.get("json") or {}

    api = FakeRemnawaveApi()
    asyncio.run(
        module._extend_preserved_squads(
            api,
            snapshots,
            [
                (
                    source_profile,
                    target_profile,
                    tag_map,
                    ["VLESS_REALITY_443", "VLESS_XHTTP_REALITY_8443"],
                )
            ],
        )
    )

    assert api.calls == [
        (
            "PATCH",
            "/internal-squads",
            {
                "uuid": "premium-smart-ru-squad",
                "inbounds": [
                    "spb-base-raw",
                    "spb-base-xhttp",
                    "rebuilt-spb-raw-clone",
                    "rebuilt-spb-xhttp-clone",
                ],
            },
        )
    ]
    assert snapshots[0]["inbounds"] == ["spb-base-raw", "spb-base-xhttp"]


def test_find_base_profile_ref_falls_back_to_active_target() -> None:
    module = _load_module()
    profiles = [
        {"uuid": "spb-active", "name": module.SPB_PROFILE_NAME},
        {"uuid": "de-base", "name": module.DE_BASE_PROFILE_NAME},
    ]

    assert module._find_base_profile_ref(
        profiles,
        module.SPB_BASE_PROFILE_NAME,
        module.SPB_PROFILE_NAME,
    ) == {"uuid": "spb-active", "name": module.SPB_PROFILE_NAME}
    assert module._find_base_profile_ref(
        profiles,
        module.DE_BASE_PROFILE_NAME,
        module.DE_BRIDGE_PROFILE_NAME,
    ) == {"uuid": "de-base", "name": module.DE_BASE_PROFILE_NAME}


def test_spb_fallback_source_requires_current_valid_task2_target() -> None:
    module = _load_module()
    target = _task2_target_profile(module)
    node = {
        "configProfile": {
            "activeConfigProfileUuid": target["uuid"],
            "activeInbounds": [],
        }
    }

    module._validate_spb_source_profile_selection(
        target,
        target,
        target,
        node,
        preferred_base_found=False,
    )

    unrelated = json.loads(json.dumps(target))
    unrelated["uuid"] = "maintenance-profile"
    unrelated["name"] = "SPB maintenance"
    node["configProfile"]["activeConfigProfileUuid"] = unrelated["uuid"]
    with pytest.raises(RuntimeError, match="currently active Task2 target profile"):
        module._validate_spb_source_profile_selection(
            unrelated,
            target,
            target,
            node,
            preferred_base_found=False,
        )


def test_spb_fallback_source_rejects_incomplete_task2_transport_contract() -> None:
    module = _load_module()
    target = _task2_target_profile(module)
    target["config"]["inbounds"] = [
        inbound for inbound in target["config"]["inbounds"] if inbound["tag"] != "SPB_EXCEPTIONS_XHTTP_REALITY_8443"
    ]
    target["inbounds"] = [
        inbound for inbound in target["inbounds"] if inbound["tag"] != "SPB_EXCEPTIONS_XHTTP_REALITY_8443"
    ]
    node = {
        "configProfile": {
            "activeConfigProfileUuid": target["uuid"],
            "activeInbounds": [],
        }
    }

    with pytest.raises(RuntimeError, match="missing dedicated RAW/XHTTP inbounds"):
        module._validate_spb_source_profile_selection(
            target,
            target,
            target,
            node,
            preferred_base_found=False,
        )


def test_manifest_write_is_atomic_private_and_replaces_safe_checkpoint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_module()
    manifest_path = tmp_path / "private" / "rollback.json"
    replace_calls: list[tuple[Path, Path]] = []
    real_replace = module.os.replace

    def recording_replace(source: Path, target: Path) -> None:
        replace_calls.append((Path(source), Path(target)))
        real_replace(source, target)

    monkeypatch.setattr(module.os, "replace", recording_replace)
    module._write_manifest(manifest_path, {"version": 1, "phase": "planned"})
    module._write_manifest(manifest_path, {"version": 1, "phase": "applied"})

    assert module._read_manifest(manifest_path)["phase"] == "applied"
    assert len(replace_calls) == 2
    assert all(source.parent == manifest_path.parent for source, _ in replace_calls)
    assert all(target == manifest_path for _, target in replace_calls)
    assert not list(manifest_path.parent.glob(".rollback.json.*.tmp"))
    if module.os.name != "nt":
        assert manifest_path.stat().st_mode & 0o777 == 0o600


def test_failure_reason_never_persists_runtime_error_details() -> None:
    module = _load_module()
    sensitive = RuntimeError("Bearer secret-token ssPassword=secret https://example.invalid/sub/customer 203.0.113.7")

    assert module._safe_failure_reason(sensitive) == "runtime_validation_failed"
    assert module._safe_failure_reason(ValueError("not recorded")) is None


def test_manifest_write_refuses_unsafe_preexisting_targets(tmp_path: Path) -> None:
    module = _load_module()

    directory_target = tmp_path / "directory-target.json"
    directory_target.mkdir()
    with pytest.raises(RuntimeError, match="regular file"):
        module._write_manifest(directory_target, {"version": 1})

    original = tmp_path / "original.json"
    original.write_text("{}", encoding="utf-8")
    original.chmod(0o600)
    hardlink = tmp_path / "hardlink.json"
    module.os.link(original, hardlink)
    with pytest.raises(RuntimeError, match="hard links"):
        module._write_manifest(hardlink, {"version": 1})


def test_manifest_read_rejects_target_swap_after_validation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_module()
    manifest = tmp_path / "rollback.json"
    replacement = tmp_path / "replacement.json"
    module._write_manifest(manifest, {"version": 1, "phase": "planned"})
    module._write_manifest(replacement, {"version": 1, "phase": "attacker"})
    real_open = module.os.open
    swapped = False

    def swapping_open(path: Path, flags: int, mode: int = 0o777) -> int:
        nonlocal swapped
        if Path(path) == manifest and not swapped:
            swapped = True
            module.os.replace(replacement, manifest)
        return real_open(path, flags, mode)

    monkeypatch.setattr(module.os, "open", swapping_open)

    with pytest.raises(RuntimeError, match="changed while it was being opened"):
        module._read_manifest(manifest)


@pytest.mark.skipif(os.name == "nt", reason="POSIX ownership and mode contract")
@pytest.mark.parametrize("unsafe_mode", [0o720, 0o770, 0o777])
def test_manifest_read_refuses_group_or_world_writable_parent(tmp_path: Path, unsafe_mode: int) -> None:
    module = _load_module()
    unsafe_parent = tmp_path / "unsafe-read"
    unsafe_parent.mkdir(mode=0o700)
    manifest = unsafe_parent / "rollback.json"
    module._write_manifest(manifest, {"version": 1})
    unsafe_parent.chmod(unsafe_mode)

    with pytest.raises(RuntimeError, match="must not be group- or world-writable"):
        module._read_manifest(manifest)


def test_manifest_write_refuses_symlink_target(tmp_path: Path) -> None:
    module = _load_module()
    target = tmp_path / "target.json"
    target.write_text("{}", encoding="utf-8")
    link = tmp_path / "rollback.json"
    try:
        link.symlink_to(target)
    except OSError as exc:
        pytest.skip(f"symlinks unavailable: {exc}")

    with pytest.raises(RuntimeError, match="regular file"):
        module._write_manifest(link, {"version": 1})
    assert target.read_text(encoding="utf-8") == "{}"


@pytest.mark.skipif(os.name == "nt", reason="POSIX ownership and mode contract")
@pytest.mark.parametrize("unsafe_mode", [0o720, 0o770, 0o777])
def test_manifest_write_refuses_permissive_target_and_group_or_world_writable_parent(
    tmp_path: Path, unsafe_mode: int
) -> None:
    module = _load_module()
    permissive_target = tmp_path / "permissive.json"
    permissive_target.write_text("{}", encoding="utf-8")
    permissive_target.chmod(0o644)
    with pytest.raises(RuntimeError, match="permissions must be 0600"):
        module._write_manifest(permissive_target, {"version": 1})

    unsafe_parent = tmp_path / "unsafe"
    unsafe_parent.mkdir(mode=0o700)
    unsafe_parent.chmod(unsafe_mode)
    with pytest.raises(RuntimeError, match="must not be group- or world-writable"):
        module._write_manifest(unsafe_parent / "rollback.json", {"version": 1})


def test_task2_node_plugin_preflight_loads_official_detail_response() -> None:
    module = _load_module()
    plugin_uuid = "22222222-2222-4222-8222-222222222222"
    nodes = _nodes_with_torrent_blocker(module, [])
    for node in nodes:
        node["activePluginUuid"] = plugin_uuid
    plugin = _torrent_blocker_plugins(module)["nodePlugins"][0]
    assert isinstance(plugin, dict)
    plugin = {**plugin, "uuid": plugin_uuid}
    calls: list[tuple[str, str]] = []

    class FakeRemnawaveApi:
        async def request(self, method: str, path: str) -> object:
            calls.append((method, path))
            if path == "/node-plugins":
                return {
                    "nodePlugins": [
                        {
                            "uuid": plugin_uuid,
                            "name": module.EXPECTED_NODE_PLUGIN_NAME,
                        }
                    ]
                }
            if path == f"/node-plugins/{plugin_uuid}":
                return plugin
            raise AssertionError(f"unexpected request {method} {path}")

    result = asyncio.run(
        module._task2_torrent_blocker_preflight(
            FakeRemnawaveApi(),
            nodes=nodes,
        )
    )

    assert result["nodeCount"] == 4
    assert calls == [
        ("GET", "/node-plugins"),
        ("GET", f"/node-plugins/{plugin_uuid}"),
    ]


def test_rollback_does_not_require_plugin_preflight(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _load_module()
    instances = []
    rollback_manifest = {"version": 3, "phase": "applied"}

    class FakeRemnawaveApi:
        def __init__(
            self,
            base_url: str,
            token: str,
            *,
            trusted_proxy_headers: bool = False,
        ) -> None:
            self.calls: list[tuple[str, str]] = []
            self.closed = False
            instances.append(self)

        async def request(self, method: str, path: str, **kwargs: object) -> object:
            self.calls.append((method, path))
            raise AssertionError(f"rollback unexpectedly queried plugin API through {method} {path}")

        async def close(self) -> None:
            self.closed = True

    async def fake_rollback(api: object, manifest: dict[str, object], manifest_path: Path) -> dict[str, str]:
        assert api is instances[0]
        assert manifest == rollback_manifest
        assert manifest_path == tmp_path / "rollback.json"
        return {"mode": "rollback", "status": "rolled_back"}

    monkeypatch.setattr(module, "RemnawaveApi", FakeRemnawaveApi)
    monkeypatch.setattr(module, "_read_manifest", lambda _path: rollback_manifest)
    monkeypatch.setattr(module, "_rollback", fake_rollback)
    monkeypatch.setenv("REMNAWAVE_TOKEN", "unit-test-token")

    args = _args(tmp_path, tmp_path / "unused-artifact.json", module)
    args.rollback = True
    args.rollback_manifest = tmp_path / "rollback.json"

    result = asyncio.run(module._run(args))

    assert result == {"mode": "rollback", "status": "rolled_back"}
    assert len(instances) == 1
    assert instances[0].calls == []
    assert instances[0].closed is True


def test_apply_fails_before_mutation_when_node_plugin_assignment_is_invalid(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _load_module()
    manifest_path = _write_artifact(tmp_path, module)
    _stub_published_artifact(monkeypatch, module, manifest_path)
    nodes = _nodes_with_torrent_blocker(
        module,
        [
            {"uuid": "spb-node", "address": module.SPB_NODE_ADDRESS, "configProfile": {}},
            {"uuid": "de-node", "address": module.DE_NODE_ADDRESS, "configProfile": {}},
        ],
    )
    next(node for node in nodes if node["address"] == module.DE_NODE_ADDRESS)["activePluginUuid"] = "wrong-plugin"
    calls: list[tuple[str, str]] = []

    class FakeRemnawaveApi:
        def __init__(
            self,
            base_url: str,
            token: str,
            *,
            trusted_proxy_headers: bool = False,
        ) -> None:
            self.base_url = base_url

        async def request(self, method: str, path: str, **kwargs: object) -> object:
            calls.append((method, path))
            if method != "GET" or kwargs:
                raise AssertionError(f"preflight mutated through {method} {path}")
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
                return {"nodes": nodes}
            if path == "/node-plugins":
                return _torrent_blocker_plugins(module)
            raise AssertionError(f"unexpected request {method} {path}")

        async def close(self) -> None:
            return None

    monkeypatch.setattr(module, "RemnawaveApi", FakeRemnawaveApi)
    monkeypatch.setenv("REMNAWAVE_TOKEN", "unit-test-token")
    args = _args(tmp_path, manifest_path, module)
    args.apply = True

    with pytest.raises(RuntimeError, match="must have active plugin"):
        asyncio.run(module._run(args))

    assert calls
    assert all(method == "GET" for method, _path in calls)
    assert not args.rollback_manifest.exists()


def test_dry_run_is_read_only_and_does_not_write_manifest(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _load_module()
    manifest_path = _write_artifact(tmp_path, module)
    _stub_published_artifact(monkeypatch, module, manifest_path)
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
                    "nodes": _nodes_with_torrent_blocker(
                        module,
                        [
                            {"uuid": "spb-node", "address": module.SPB_NODE_ADDRESS, "configProfile": {}},
                            {"uuid": "de-node", "address": module.DE_NODE_ADDRESS, "configProfile": {}},
                        ],
                    )
                }
            if path == "/node-plugins":
                return _torrent_blocker_plugins(module)
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
    assert result["spbConnectAddress"] == module.SPB_CONNECT_ADDRESS
    assert result["spbPublicHostCount"] == 2
    assert result["spbTask2ListenAddress"] == "10.0.0.2"
    assert result["ipv6PolicyMode"] == "disabled"
    assert result["artifactUnionIpv6PrefixCount"] == 0
    assert result["artifactActiveVersion"] == "a" * 64
    assert result["artifactLastKnownGoodVersion"] == "b" * 64
    assert result["artifactPolicySha256"] == "d" * 64
    assert result["artifactSourceManifestSha256"] == "e" * 64
    assert result["artifactSafetyStatus"] == "accepted"
    assert result["nodePluginPreflight"] == {
        "pluginName": module.EXPECTED_NODE_PLUGIN_NAME,
        "nodeCount": 4,
        "blockDuration": module.EXPECTED_TORRENT_BLOCKER_DURATION,
    }
    assert result["bridgeInboundTag"] == "DE_SPB_EXCEPTIONS_BRIDGE_9444"
    assert result["bridgeOutboundTag"] == "DE_EXCEPTIONS_BRIDGE"
    assert result["restartOrder"] == ["supplemental", "de", "spb"]
    assert not (tmp_path / "rollback.json").exists()
    assert len(instances) == 1
    assert instances[0].trusted_proxy_headers is False
    assert all(method == "GET" for method, _path in instances[0].calls)


def test_dry_run_route_evidence_redacts_secret_url_and_user_identifiers(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _load_module()
    manifest_path = _write_artifact(tmp_path, module)
    _stub_published_artifact(monkeypatch, module, manifest_path)

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
                    "nodes": _nodes_with_torrent_blocker(
                        module,
                        [
                            {"uuid": "spb-node", "address": module.SPB_NODE_ADDRESS, "configProfile": {}},
                            {"uuid": "de-node", "address": module.DE_NODE_ADDRESS, "configProfile": {}},
                        ],
                    )
                }
            if path == "/node-plugins":
                return _torrent_blocker_plugins(module)
            if path == "/hosts":
                return {"hosts": []}
            if path == "/internal-squads":
                return {
                    "internalSquads": [{"uuid": "customer-squad", "name": module.CUSTOMER_SQUAD_NAME, "inbounds": []}]
                }
            if path == "/external-squads":
                return {
                    "externalSquads": [
                        {"uuid": "external-squad", "name": module.EXTERNAL_SQUAD_NAME, "responseHeaders": {}}
                    ]
                }
            if path == f"/users/by-username/{module.BRIDGE_USERNAME}":
                return None
            if path == "/users/by-username/task2_probe_username":
                return {
                    "uuid": "probe-user-uuid",
                    "shortUuid": "PROBE123",
                    "username": "task2_probe_username",
                    "tId": 42,
                    "vlessUuid": "550e8400-e29b-41d4-a716-446655440002",
                    "ssPassword": "secret-ss-password",
                    "subscriptionUrl": "https://vpn.example.com/sub/task2_probe_username",
                    "tag": module.TASK2_SYNTHETIC_USER_TAG,
                    "activeInternalSquads": [{"uuid": "customer-squad"}],
                    "externalSquadUuid": None,
                }
            raise AssertionError(f"unexpected request {method} {path}")

        async def close(self) -> None:
            self.closed = True

    args = _args(tmp_path, manifest_path, module)
    args.task2_route_evidence_enabled = "true"
    args.task2_synthetic_user = "task2_probe_username"
    args.task2_xray_webhook_secret = "unit-test-webhook-secret"
    monkeypatch.setattr(module, "RemnawaveApi", FakeRemnawaveApi)
    monkeypatch.setenv("REMNAWAVE_TOKEN", "unit-test-token")

    result = asyncio.run(module._run(args))
    result_json = json.dumps(result, sort_keys=True)

    assert result["task2RouteEvidence"] == "enabled"
    assert result["task2SyntheticProbeUser"] == "patch"
    assert not (tmp_path / "rollback.json").exists()
    for forbidden in (
        "unit-test-webhook-secret",
        module.TASK2_ROUTE_EVIDENCE_WEBHOOK_URL,
        "task2_probe_username",
        "probe-user-uuid",
        "PROBE123",
        '"42"',
        "550e8400-e29b-41d4-a716-446655440002",
        "secret-ss-password",
        "https://vpn.example.com/sub/task2_probe_username",
    ):
        assert forbidden not in result_json


def test_dry_run_rejects_contaminated_bridge_squad_before_mutation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _load_module()
    manifest_path = _write_artifact(tmp_path, module)
    _stub_published_artifact(monkeypatch, module, manifest_path)

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
                    "nodes": _nodes_with_torrent_blocker(
                        module,
                        [
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
                        ],
                    )
                }
            if path == "/node-plugins":
                return _torrent_blocker_plugins(module)
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
    _stub_published_artifact(monkeypatch, module, manifest_path)
    de_base_profile = _base_profile("de-base", module.DE_BASE_PROFILE_NAME)
    de_base_profile["config"] = _contaminated_supplemental_torrent_policy_config()
    moscow_profile = _base_profile("moscow-profile", module.TASK1_MOSCOW_PROFILE_NAME)
    moscow_profile["config"] = _contaminated_supplemental_torrent_policy_config()
    de_mapping = module._preserved_inbound_tag_map(
        de_base_profile["config"], "de", exclude_tags={module.BRIDGE_INBOUND_TAG}
    )
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
        "users": [],
    }
    supplemental_profile_patches: list[dict[str, object]] = []
    restart_paths: list[str] = []

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
                    "inbound": {
                        "configProfileUuid": "spb-base",
                        "configProfileInboundUuid": "spb-base-raw",
                    },
                    "excludedInternalSquads": ["customer-squad"],
                },
                {
                    "uuid": "old-spb-xhttp-host",
                    "remark": "Existing SPB customer XHTTP",
                    "inbound": {
                        "configProfileUuid": "spb-base",
                        "configProfileInboundUuid": "spb-base-xhttp",
                    },
                    "excludedInternalSquads": ["customer-squad"],
                },
                {
                    "uuid": "old-de-host",
                    "remark": "Existing DE customer RAW",
                    "inbound": {
                        "configProfileUuid": "de-base",
                        "configProfileInboundUuid": "de-base-raw",
                    },
                },
                {
                    "uuid": "old-de-xhttp-host",
                    "remark": "Existing DE customer XHTTP",
                    "inbound": {
                        "configProfileUuid": "de-base",
                        "configProfileInboundUuid": "de-base-xhttp",
                    },
                },
            ]
            self.configs: dict[str, dict[str, object]] = {
                "de-base": de_base_profile,
                "moscow-profile": moscow_profile,
            }

        async def request(self, method: str, path: str, **kwargs: object) -> object:
            body = kwargs.get("json")
            if path == "/config-profiles" and method == "GET":
                return {
                    "configProfiles": [
                        {"uuid": "spb-base", "name": module.SPB_BASE_PROFILE_NAME},
                        {"uuid": "de-base", "name": module.DE_BASE_PROFILE_NAME},
                        {"uuid": "moscow-profile", "name": module.TASK1_MOSCOW_PROFILE_NAME},
                    ]
                }
            if path == "/config-profiles/spb-base" and method == "GET":
                return _base_profile("spb-base", module.SPB_BASE_PROFILE_NAME)
            if path == "/config-profiles/de-base" and method == "GET":
                return self.configs["de-base"]
            if path == "/config-profiles/moscow-profile" and method == "GET":
                return self.configs["moscow-profile"]
            if path == "/nodes" and method == "GET":
                return {
                    "nodes": _nodes_with_torrent_blocker(
                        module,
                        [
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
                            {
                                "uuid": "nl-node",
                                "address": "138.16.140.44",
                                "configProfile": {
                                    "activeConfigProfileUuid": "de-base",
                                    "activeInbounds": [{"uuid": "de-base-raw"}, {"uuid": "de-base-xhttp"}],
                                },
                            },
                            {
                                "uuid": "moscow-node",
                                "address": "178.159.94.225",
                                "configProfile": {
                                    "activeConfigProfileUuid": "moscow-profile",
                                    "activeInbounds": [
                                        {"uuid": "moscow-profile-raw"},
                                        {"uuid": "moscow-profile-xhttp"},
                                    ],
                                },
                            },
                        ],
                    )
                }
            if path == "/node-plugins" and method == "GET":
                return _torrent_blocker_plugins(module)
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
            if path == "/users/by-username/task2_probe_username" and method == "GET":
                return None
            if path == "/config-profiles" and method == "PATCH":
                assert isinstance(body, dict)
                assert body["uuid"] in {"de-base", "moscow-profile"}
                supplemental_profile_patches.append(body)
                _assert_supplemental_torrent_policy_sanitized(body["config"])
                self.configs[body["uuid"]] = {
                    **self.configs[body["uuid"]],
                    "name": body["name"],
                    "config": body["config"],
                }
                return {"uuid": body["uuid"]}
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
                        rule for rule in routing_rules if str(rule.get("ruleTag") or "").startswith("task2-")
                    ]
                    synthetic_rules = [
                        rule
                        for rule in task2_rules
                        if str(rule.get("ruleTag") or "").startswith("task2-route-evidence-")
                    ]
                    assert [rule["ruleTag"] for rule in synthetic_rules] == [
                        "task2-route-evidence-matched-0001-fixture-ipv4",
                        "task2-route-evidence-unmatched-direct",
                    ]
                    assert synthetic_rules[0]["outboundTag"] == module.BRIDGE_OUTBOUND_TAG
                    assert synthetic_rules[1]["outboundTag"] == "DIRECT"
                    assert all(rule["user"] == ["42"] for rule in synthetic_rules)
                    assert all(
                        rule["webhook"]["url"] == module.TASK2_ROUTE_EVIDENCE_WEBHOOK_URL for rule in synthetic_rules
                    )
                    assert all(
                        rule["webhook"]["headers"]
                        == {module.TASK2_XRAY_WEBHOOK_AUTH_HEADER: "unit-test-webhook-secret"}
                        for rule in synthetic_rules
                    )
                    ordinary_task2_rules = [rule for rule in task2_rules if rule not in synthetic_rules]
                    assert all("webhook" not in rule for rule in ordinary_task2_rules)
                    assert all("user" not in rule for rule in ordinary_task2_rules)
                    assert task2_rules[-1]["inboundTag"] == [
                        "SPB_EXCEPTIONS_REALITY_443",
                        "SPB_EXCEPTIONS_XHTTP_REALITY_8443",
                    ]
                    exception_rule = next(rule for rule in routing_rules if rule.get("ruleTag") == "fixture-ipv4")
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
                assert isinstance(body, dict)
                if body["username"] == "task2_probe_username":
                    captured["users"].append(body)
                    return {
                        "uuid": "task2-probe-user",
                        "shortUuid": "PROBE123",
                        "username": body["username"],
                        "tId": 42,
                        "vlessUuid": body["vlessUuid"],
                        "activeInternalSquads": body["activeInternalSquads"],
                        "externalSquadUuid": None,
                    }
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
            if path.endswith("/actions/restart") and method == "POST":
                restart_paths.append(path)
                return {}
            raise AssertionError(f"unexpected request {method} {path}")

        async def close(self) -> None:
            self.closed = True

    args = _args(tmp_path, manifest_path, module)
    args.apply = True
    args.task2_route_evidence_enabled = "true"
    args.task2_synthetic_user = "task2_probe_username"
    args.task2_xray_webhook_secret = "unit-test-webhook-secret"
    monkeypatch.setattr(module, "RemnawaveApi", FakeRemnawaveApi)
    monkeypatch.setenv("REMNAWAVE_TOKEN", "unit-test-token")

    result = asyncio.run(module._run(args))

    assert result["status"] == "applied"
    assert result["task2RouteEvidence"] == "enabled"
    assert result["task2SyntheticProbeUser"] == "create"
    assert result["supplementalTorrentPolicyProfiles"] == [
        {
            "name": module.DE_BASE_PROFILE_NAME,
            "action": "update",
            "activeNodeCount": 2,
        },
        {
            "name": module.TASK1_MOSCOW_PROFILE_NAME,
            "action": "update",
            "activeNodeCount": 1,
        },
    ]
    assert result["restartOrder"] == ["supplemental", "de", "spb"]
    result_json = json.dumps(result, sort_keys=True)
    assert "unit-test-webhook-secret" not in result_json
    assert "task2_probe_username" not in result_json
    assert "task2-probe-user" not in result_json
    assert [patch["uuid"] for patch in supplemental_profile_patches] == ["de-base", "moscow-profile"]
    assert restart_paths == [
        "/nodes/moscow-node/actions/restart",
        "/nodes/nl-node/actions/restart",
        "/nodes/de-node/actions/restart",
        "/nodes/spb-node/actions/restart",
    ]
    assert captured["users"] == [
        {
            "username": "task2_probe_username",
            "status": "ACTIVE",
            "vlessUuid": captured["users"][0]["vlessUuid"],
            "trafficLimitBytes": 0,
            "trafficLimitStrategy": "NO_RESET",
            "expireAt": "2099-12-31T23:59:59.000Z",
            "description": module.TASK2_SYNTHETIC_USER_DESCRIPTION,
            "tag": module.TASK2_SYNTHETIC_USER_TAG,
            "activeInternalSquads": ["customer-squad"],
            "externalSquadUuid": None,
        }
    ]
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
    assert {host["address"] for host in captured["hosts"]} == {module.SPB_CONNECT_ADDRESS}
    xhttp_host = next(host for host in captured["hosts"] if host["port"] == module.SPB_TASK2_XHTTP_PORT)
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
        patch for patch in captured["host_patches"] if patch["uuid"] in {"old-spb-host", "old-spb-xhttp-host"}
    ]
    assert all(patch["excludedInternalSquads"] == [] for patch in spb_host_patches)
    assert "bridge-inbound" not in {host["inbound"]["configProfileInboundUuid"] for host in captured["hosts"]}
    assert not any(
        str(host.get("remark", "")).casefold().find("probe") >= 0
        or str(host.get("remark", "")).casefold().find("synthetic") >= 0
        for host in captured["hosts"]
    )
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

    manifest = json.loads(args.rollback_manifest.read_text(encoding="utf-8"))
    supplemental_snapshots = manifest["supplementalTorrentPolicyProfiles"]
    assert [
        {
            "uuid": snapshot["uuid"],
            "name": snapshot["name"],
            "activeNodeUuids": snapshot["activeNodeUuids"],
        }
        for snapshot in supplemental_snapshots
    ] == [
        {
            "uuid": "de-base",
            "name": module.DE_BASE_PROFILE_NAME,
            "activeNodeUuids": ["de-node", "nl-node"],
        },
        {
            "uuid": "moscow-profile",
            "name": module.TASK1_MOSCOW_PROFILE_NAME,
            "activeNodeUuids": ["moscow-node"],
        },
    ]
    assert "bittorrent" in json.dumps(supplemental_snapshots[0]["config"], sort_keys=True).casefold()
    assert "qbittorrent" in json.dumps(supplemental_snapshots[1]["config"], sort_keys=True).casefold()

    class FakeRollbackApi:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str, object]] = []

        async def request(self, method: str, path: str, **kwargs: object) -> object:
            self.calls.append((method, path, kwargs.get("json")))
            if (method, path) == ("GET", "/hosts"):
                return {"hosts": []}
            if (method, path) == ("GET", "/config-profiles"):
                return {"configProfiles": []}
            if (method, path) == ("GET", "/internal-squads"):
                return {"internalSquads": []}
            if path == f"/users/by-username/{module.BRIDGE_USERNAME}" and method == "GET":
                return None
            return kwargs.get("json") or {}

    rollback_api = FakeRollbackApi()
    rollback_result = asyncio.run(module._rollback(rollback_api, manifest, args.rollback_manifest))
    supplemental_restore_patches = [
        call
        for call in rollback_api.calls
        if call[0:2] == ("PATCH", "/config-profiles") and call[2]["uuid"] in {"de-base", "moscow-profile"}
    ]
    assert [call[2]["uuid"] for call in supplemental_restore_patches] == ["de-base", "moscow-profile"]
    _assert_supplemental_torrent_policy_sanitized(supplemental_restore_patches[0][2]["config"])
    _assert_supplemental_torrent_policy_sanitized(supplemental_restore_patches[1][2]["config"])
    assert supplemental_restore_patches[0][2]["config"] != supplemental_snapshots[0]["config"]
    assert supplemental_restore_patches[1][2]["config"] != supplemental_snapshots[1]["config"]
    rollback_restart_paths = [call[1] for call in rollback_api.calls if call[0] == "POST"]
    assert "/nodes/nl-node/actions/restart" in rollback_restart_paths
    assert "/nodes/moscow-node/actions/restart" in rollback_restart_paths
    assert rollback_result == {"mode": "rollback", "status": "rolled_back"}

    call_count_after_rollback = len(rollback_api.calls)
    result_again = asyncio.run(
        module._rollback(rollback_api, {"version": 1, "phase": "rolled_back"}, args.rollback_manifest)
    )
    assert result_again == {"mode": "rollback", "status": "already_rolled_back"}
    assert len(rollback_api.calls) == call_count_after_rollback


def test_apply_reapply_uses_named_spb_base_when_active_profile_is_task2_only(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _load_module()
    manifest_path = _write_artifact(tmp_path, module)
    _stub_published_artifact(monkeypatch, module, manifest_path)
    saved_spb_base_name = "Saved SPB Smart RU 443 8443"
    saved_spb_base = _base_profile("saved-spb-base", saved_spb_base_name)
    de_base = _base_profile("de-base", module.DE_BASE_PROFILE_NAME)
    spb_mapping = module._preserved_inbound_tag_map(
        saved_spb_base["config"],
        "spb",
        exclude_tags=module.SPB_CUSTOMER_INBOUND_TAG_SET | {module.BRIDGE_INBOUND_TAG},
    )
    de_mapping = module._preserved_inbound_tag_map(
        de_base["config"],
        "de",
        exclude_tags={module.BRIDGE_INBOUND_TAG},
    )
    active_task2_only_profile = {
        "uuid": "spb-task2-only-profile",
        "name": module.SPB_PROFILE_NAME,
        "config": {
            "inbounds": [
                {
                    "tag": "SPB_EXCEPTIONS_REALITY_443",
                    "protocol": "vless",
                    "port": module.SPB_TASK2_RAW_PORT,
                    "listen": "10.0.0.2",
                    "streamSettings": {"network": "raw"},
                },
                {
                    "tag": "SPB_EXCEPTIONS_XHTTP_REALITY_8443",
                    "protocol": "vless",
                    "port": module.SPB_TASK2_XHTTP_PORT,
                    "listen": "10.0.0.2",
                    "streamSettings": {
                        "network": "xhttp",
                        "xhttpSettings": {"path": "/spb-de-exceptions-xhttp"},
                    },
                },
            ],
            "outbounds": [
                {"tag": "DIRECT", "protocol": "freedom"},
                {"tag": "BLOCK", "protocol": "blackhole"},
                {"tag": module.BRIDGE_OUTBOUND_TAG, "protocol": "shadowsocks"},
            ],
            "routing": {
                "rules": [
                    {
                        "type": "field",
                        "ruleTag": "task2-final-spb-direct",
                        "inboundTag": list(module.SPB_CUSTOMER_INBOUND_TAGS),
                        "network": "tcp,udp",
                        "outboundTag": "DIRECT",
                    }
                ]
            },
        },
        "inbounds": [
            {
                "tag": "SPB_EXCEPTIONS_REALITY_443",
                "uuid": "current-spb-task2-raw",
                "port": module.SPB_TASK2_RAW_PORT,
            },
            {
                "tag": "SPB_EXCEPTIONS_XHTTP_REALITY_8443",
                "uuid": "current-spb-task2-xhttp",
                "port": module.SPB_TASK2_XHTTP_PORT,
            },
        ],
    }
    captured: dict[str, object] = {"spb_profile_patch": None, "nodes": []}

    class FakeRemnawaveApi:
        def __init__(
            self,
            base_url: str,
            token: str,
            *,
            trusted_proxy_headers: bool = False,
        ) -> None:
            self.configs: dict[str, dict[str, object]] = {
                "saved-spb-base": saved_spb_base,
                "de-base": de_base,
                "spb-task2-only-profile": active_task2_only_profile,
            }
            self.hosts: list[dict[str, object]] = []

        async def request(self, method: str, path: str, **kwargs: object) -> object:
            body = kwargs.get("json")
            if path == "/config-profiles" and method == "GET":
                return {
                    "configProfiles": [
                        {"uuid": "saved-spb-base", "name": saved_spb_base_name},
                        {"uuid": "de-base", "name": module.DE_BASE_PROFILE_NAME},
                        {"uuid": "spb-task2-only-profile", "name": module.SPB_PROFILE_NAME},
                    ]
                }
            if path.startswith("/config-profiles/") and method == "GET":
                return self.configs[path.rsplit("/", 1)[-1]]
            if path == "/nodes" and method == "GET":
                return {
                    "nodes": _nodes_with_torrent_blocker(
                        module,
                        [
                            {
                                "uuid": "spb-node",
                                "address": module.SPB_NODE_ADDRESS,
                                "configProfile": {
                                    "activeConfigProfileUuid": "spb-task2-only-profile",
                                    "activeInbounds": [
                                        {"uuid": "current-spb-task2-raw"},
                                        {"uuid": "current-spb-task2-xhttp"},
                                    ],
                                },
                            },
                            {
                                "uuid": "de-node",
                                "address": module.DE_NODE_ADDRESS,
                                "configProfile": {
                                    "activeConfigProfileUuid": "de-base",
                                    "activeInbounds": [
                                        {"uuid": "de-base-raw"},
                                        {"uuid": "de-base-xhttp"},
                                    ],
                                },
                            },
                        ],
                    )
                }
            if path == "/node-plugins" and method == "GET":
                return _torrent_blocker_plugins(module)
            if path == "/hosts" and method == "GET":
                return {"hosts": self.hosts}
            if path == "/internal-squads" and method == "GET":
                return {
                    "internalSquads": [{"uuid": "customer-squad", "name": module.CUSTOMER_SQUAD_NAME, "inbounds": []}]
                }
            if path == "/external-squads" and method == "GET":
                return {
                    "externalSquads": [
                        {
                            "uuid": "external-squad",
                            "name": module.EXTERNAL_SQUAD_NAME,
                            "responseHeaders": {},
                        }
                    ]
                }
            if path == f"/users/by-username/{module.BRIDGE_USERNAME}" and method == "GET":
                return None
            if path == "/config-profiles" and method == "POST":
                assert isinstance(body, dict)
                assert body["name"] == module.DE_BRIDGE_PROFILE_NAME
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
            if path == "/config-profiles" and method == "PATCH":
                assert isinstance(body, dict)
                if body["uuid"] == "de-base":
                    self.configs["de-base"] = {
                        **self.configs["de-base"],
                        "name": body["name"],
                        "config": body["config"],
                    }
                    return {"uuid": "de-base"}
                assert body["uuid"] == "spb-task2-only-profile"
                captured["spb_profile_patch"] = body
                profile = {
                    "uuid": "spb-task2-only-profile",
                    "name": body["name"],
                    "config": body["config"],
                    "inbounds": [
                        {"tag": spb_mapping["VLESS_REALITY_443"], "uuid": "rebuilt-spb-raw", "port": 443},
                        {
                            "tag": spb_mapping["VLESS_XHTTP_REALITY_8443"],
                            "uuid": "rebuilt-spb-xhttp",
                            "port": 8443,
                        },
                        {
                            "tag": "SPB_EXCEPTIONS_REALITY_443",
                            "uuid": "rebuilt-spb-task2-raw",
                            "port": module.SPB_TASK2_RAW_PORT,
                        },
                        {
                            "tag": "SPB_EXCEPTIONS_XHTTP_REALITY_8443",
                            "uuid": "rebuilt-spb-task2-xhttp",
                            "port": module.SPB_TASK2_XHTTP_PORT,
                        },
                    ],
                }
                self.configs["spb-task2-only-profile"] = profile
                return {"uuid": "spb-task2-only-profile"}
            if path == "/internal-squads" and method == "POST":
                assert isinstance(body, dict)
                return {"uuid": "bridge-squad", "name": module.BRIDGE_SQUAD_NAME, "inbounds": body["inbounds"]}
            if path == "/users" and method == "POST":
                assert isinstance(body, dict)
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
                return host
            if path == "/internal-squads" and method == "PATCH":
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
    args.spb_base_profile = saved_spb_base_name
    monkeypatch.setattr(module, "RemnawaveApi", FakeRemnawaveApi)
    monkeypatch.setenv("REMNAWAVE_TOKEN", "unit-test-token")

    result = asyncio.run(module._run(args))

    assert result["status"] == "applied"
    assert result["spbPreservedActiveInboundTags"] == [
        "VLESS_REALITY_443",
        "VLESS_XHTTP_REALITY_8443",
    ]
    spb_profile_patch = captured["spb_profile_patch"]
    assert isinstance(spb_profile_patch, dict)
    config = spb_profile_patch["config"]
    inbounds_by_tag = {item["tag"]: item for item in config["inbounds"]}
    assert inbounds_by_tag[spb_mapping["VLESS_REALITY_443"]]["port"] == 443
    assert inbounds_by_tag[spb_mapping["VLESS_XHTTP_REALITY_8443"]]["port"] == 8443
    assert inbounds_by_tag[spb_mapping["VLESS_REALITY_443"]]["listen"] == "10.0.0.1"
    assert inbounds_by_tag[spb_mapping["VLESS_XHTTP_REALITY_8443"]]["listen"] == "10.0.0.1"
    assert inbounds_by_tag["SPB_EXCEPTIONS_REALITY_443"]["port"] == module.SPB_TASK2_RAW_PORT
    assert inbounds_by_tag["SPB_EXCEPTIONS_XHTTP_REALITY_8443"]["port"] == module.SPB_TASK2_XHTTP_PORT
    assert inbounds_by_tag["SPB_EXCEPTIONS_REALITY_443"]["listen"] == "10.0.0.2"
    assert inbounds_by_tag["SPB_EXCEPTIONS_XHTTP_REALITY_8443"]["listen"] == "10.0.0.2"

    routing_rules = config["routing"]["rules"]
    preserved_rule = next(rule for rule in routing_rules if rule.get("ruleTag") == "existing-smart-ru-customer-route")
    assert preserved_rule["inboundTag"] == [
        spb_mapping["VLESS_REALITY_443"],
        spb_mapping["VLESS_XHTTP_REALITY_8443"],
    ]
    customer_task2_rules = [
        rule
        for rule in routing_rules
        if (str(rule.get("ruleTag") or "").startswith("task2-") or rule.get("ruleTag") == "fixture-ipv4")
        and rule.get("inboundTag") != [module.BRIDGE_INBOUND_TAG]
    ]
    assert customer_task2_rules
    assert all(rule["inboundTag"] == module.SPB_CUSTOMER_INBOUND_TAGS for rule in customer_task2_rules)
    spb_node_patch = next(item for item in captured["nodes"] if item["uuid"] == "spb-node")
    assert spb_node_patch["configProfile"]["activeInbounds"] == [
        "rebuilt-spb-raw",
        "rebuilt-spb-xhttp",
        "rebuilt-spb-task2-raw",
        "rebuilt-spb-task2-xhttp",
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


def test_rollback_sanitizes_restored_profiles_without_reintroducing_manual_torrent_policy(tmp_path: Path) -> None:
    module = _load_module()
    dirty_config = _contaminated_supplemental_torrent_policy_config()
    assert "bittorrent" in json.dumps(dirty_config, sort_keys=True).casefold()
    assert "qbittorrent" in json.dumps(dirty_config, sort_keys=True).casefold()

    class CaptureRollbackApi:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str, object]] = []

        async def request(self, method: str, path: str, **kwargs: object) -> object:
            self.calls.append((method, path, kwargs.get("json")))
            if (method, path) == ("GET", "/hosts"):
                return {"hosts": []}
            if (method, path) == ("GET", "/config-profiles"):
                return {"configProfiles": []}
            return kwargs.get("json") or {}

    manifest = {
        "version": 1,
        "phase": "applied",
        "product": module.PRODUCT_CODE,
        "supplementalTorrentPolicyProfiles": [
            {
                "uuid": "de-base",
                "name": module.DE_BASE_PROFILE_NAME,
                "config": dirty_config,
                "activeNodeUuids": ["nl-node"],
            },
            {
                "uuid": "moscow-profile",
                "name": module.TASK1_MOSCOW_PROFILE_NAME,
                "config": dirty_config,
                "activeNodeUuids": ["moscow-node"],
            },
        ],
        "spbProfile": {"uuid": "spb-profile", "name": "SPB", "config": dirty_config},
        "spbProfileName": module.SPB_PROFILE_NAME,
        "deBridgeProfile": {
            "uuid": "de-profile",
            "name": "DE Bridge",
            "config": dirty_config,
        },
        "deBridgeProfileName": module.DE_BRIDGE_PROFILE_NAME,
        "spbNode": {"uuid": "spb-node", "configProfile": {"activeConfigProfileUuid": "old-spb"}},
        "deNode": {"uuid": "de-node", "configProfile": {"activeConfigProfileUuid": "old-de"}},
        "bridgeUser": {"uuid": "bridge-user", "activeInternalSquads": [], "externalSquadUuid": None},
        "bridgeUsername": module.BRIDGE_USERNAME,
        "bridgeSquad": {"uuid": "bridge-squad", "inbounds": []},
        "bridgeSquadName": module.BRIDGE_SQUAD_NAME,
        "spbHostRemarks": [],
    }
    api = CaptureRollbackApi()
    manifest_path = tmp_path / "rollback.json"

    result = asyncio.run(module._rollback(api, manifest, manifest_path))

    profile_patches = [
        call[2] for call in api.calls if call[0:2] == ("PATCH", "/config-profiles") and isinstance(call[2], dict)
    ]
    assert [patch["uuid"] for patch in profile_patches] == [
        "de-base",
        "moscow-profile",
        "spb-profile",
        "de-profile",
    ]
    for patch in profile_patches:
        _assert_supplemental_torrent_policy_sanitized(patch["config"])
        assert patch["config"] != dirty_config
    restart_paths = [call[1] for call in api.calls if call[0] == "POST"]
    assert "/nodes/nl-node/actions/restart" in restart_paths
    assert "/nodes/moscow-node/actions/restart" in restart_paths
    assert result == {"mode": "rollback", "status": "rolled_back"}
    assert json.loads(manifest_path.read_text(encoding="utf-8"))["phase"] == "rolled_back"


def test_public_host_rollback_restores_legacy_remark_by_uuid() -> None:
    module = _load_module()
    calls: list[tuple[str, str, object]] = []
    snapshot = {
        "uuid": "host-uuid",
        "remark": "CyberVPN SPB DE Reality 443",
        "address": "old.example.test",
    }

    class FakeRemnawaveApi:
        async def request(self, method: str, path: str, **kwargs: object) -> object:
            calls.append((method, path, kwargs.get("json")))
            if (method, path) == ("GET", "/hosts"):
                return {
                    "hosts": [
                        {
                            "uuid": "host-uuid",
                            "remark": "CyberVPN SPB DE Reality 4443",
                            "address": module.SPB_CONNECT_ADDRESS,
                        }
                    ]
                }
            return kwargs.get("json") or {}

    asyncio.run(module._rollback_spb_public_hosts(FakeRemnawaveApi(), {"spbHosts": [snapshot]}))

    assert calls == [
        ("GET", "/hosts", None),
        ("PATCH", "/hosts", snapshot),
    ]


def test_task2_synthetic_user_rollback_restores_existing_state_without_credentials() -> None:
    module = _load_module()
    calls: list[tuple[str, str, object]] = []

    class FakeRemnawaveApi:
        async def request(self, method: str, path: str, **kwargs: object) -> object:
            calls.append((method, path, kwargs.get("json")))
            return kwargs.get("json") or {}

    manifest = {
        "task2RouteEvidenceEnabled": True,
        "task2SyntheticUser": {
            "uuid": "probe-user",
            "username": "task2_probe_username",
            "status": "DISABLED",
            "trafficLimitBytes": 1234,
            "trafficLimitStrategy": "MONTH",
            "expireAt": "2028-01-01T00:00:00.000Z",
            "description": "old description",
            "tag": "OLD_TAG",
            "activeInternalSquads": ["old-squad"],
            "externalSquadUuid": "old-external-squad",
            "shortUuid": "MUST_NOT_PATCH",
            "vlessUuid": "550e8400-e29b-41d4-a716-446655440002",
            "ssPassword": "MUST_NOT_PATCH",
            "subscriptionUrl": "https://vpn.example.com/sub/task2_probe_username",
        },
    }

    asyncio.run(module._restore_or_delete_task2_synthetic_user(FakeRemnawaveApi(), manifest))

    assert calls == [
        (
            "PATCH",
            "/users",
            {
                "uuid": "probe-user",
                "activeInternalSquads": ["old-squad"],
                "externalSquadUuid": "old-external-squad",
                "status": "DISABLED",
                "trafficLimitBytes": 1234,
                "trafficLimitStrategy": "MONTH",
                "expireAt": "2028-01-01T00:00:00.000Z",
                "description": "old description",
                "tag": "OLD_TAG",
            },
        )
    ]


def test_task2_synthetic_user_rollback_deletes_created_manifest_uuid() -> None:
    module = _load_module()
    calls: list[tuple[str, str, object]] = []

    class FakeRemnawaveApi:
        async def request(self, method: str, path: str, **kwargs: object) -> object:
            calls.append((method, path, kwargs.get("json")))
            return {}

    manifest = {
        "task2RouteEvidenceEnabled": True,
        "task2SyntheticUsername": "task2_probe_username",
        "task2SyntheticUser": None,
        "task2SyntheticUserCreatedUuid": "created-probe-user",
    }

    asyncio.run(module._restore_or_delete_task2_synthetic_user(FakeRemnawaveApi(), manifest))

    assert calls == [("DELETE", "/users/created-probe-user", None)]


def test_existing_task2_synthetic_user_collision_must_be_marked() -> None:
    module = _load_module()

    with pytest.raises(RuntimeError, match="dedicated probe"):
        module._validate_existing_task2_synthetic_user(
            {
                "uuid": "customer-user",
                "username": "task2_probe_username",
                "shortUuid": "CUSTOMER",
                "activeInternalSquads": [{"uuid": "customer-squad"}],
                "externalSquadUuid": None,
            },
            expected_username="task2_probe_username",
        )


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
        "task2RouteEvidenceEnabled": True,
        "task2SyntheticUsername": "task2_probe_username",
        "task2SyntheticUser": None,
        "task2SyntheticUserCreatedUuid": "created-probe-user",
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
    synthetic_user_delete_index = next(
        index for index, call in enumerate(api.calls) if call[0:2] == ("DELETE", "/users/created-probe-user")
    )
    assert spb_host_restore_index < spb_profile_restore_index < spb_restart_index
    assert spb_restart_index < synthetic_user_delete_index < bridge_user_restore_index
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
