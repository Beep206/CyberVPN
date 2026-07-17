from __future__ import annotations

import asyncio
import base64
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_PATH = REPO_ROOT / "scripts/remnawave/apply-premium-smart-ru-server-routing.py"
POLICY_PATH = REPO_ROOT / "scripts/remnawave/policies/premium_smart_ru.yaml"

sys.path.insert(0, str(REPO_ROOT))

from scripts.remnawave.policy_compiler.compiler import build_outputs  # noqa: E402
from scripts.remnawave.policy_compiler.renderers import (  # noqa: E402
    LEGACY_HEADER_NAME,
    XRAY_SERVER_NAME,
)


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("premium_smart_ru_server_routing", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _base_config() -> dict[str, object]:
    return {
        "inbounds": [
            {"tag": "UNMANAGED_INBOUND", "protocol": "dokodemo-door"},
            {"tag": "VLESS_REALITY_443", "protocol": "vless"},
            {"tag": "VLESS_XHTTP_REALITY_8443", "protocol": "vless"},
        ],
        "outbounds": [
            {"tag": "DIRECT", "protocol": "freedom"},
            {"tag": "BLOCK", "protocol": "blackhole"},
        ],
    }


def _contaminated_torrent_policy_config() -> dict[str, object]:
    config = _base_config()
    outbounds = config["outbounds"]
    assert isinstance(outbounds, list)
    outbounds.append({"tag": "innocent-sink", "protocol": "blackhole"})
    config["routing"] = {
        "domainStrategy": "IPIfNonMatch",
        "rules": [
            {
                "type": "field",
                "ruleTag": "block_bittorrent_protocol",
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
                "process": ["qbittorrent.exe"],
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
                "domain": ["domain:rutracker.org", "domain:malware.test"],
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


def _assert_protocol_only_torrent_policy_sanitized(config: dict[str, object]) -> None:
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
        if isinstance(rule, dict) and str(rule.get("outboundTag")).casefold() == "block"
        for domain in rule.get("domain", [])
    }
    assert "domain:rutracker.org" not in blocked_domains
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


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else [value]


def _iter_dicts(value: object) -> object:
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from _iter_dicts(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_dicts(item)


def _assert_no_manual_torrent_protocol_or_process(rules: list[object]) -> None:
    for item in _iter_dicts(rules):
        assert isinstance(item, dict)
        protocols = _as_list(item.get("protocol"))
        processes = _as_list(item.get("process"))
        assert not any(str(protocol).casefold() == "bittorrent" for protocol in protocols)
        assert not any("torrent" in str(process).casefold() for process in processes)


def _profile_inbounds() -> list[dict[str, str]]:
    return [
        {"tag": "VLESS_REALITY_443", "uuid": "base-raw"},
        {"tag": "VLESS_XHTTP_REALITY_8443", "uuid": "base-xhttp"},
        {"tag": "MSK_SMART_RU_BRIDGE_9443", "uuid": "base-bridge"},
    ]


def _compiled_artifacts() -> tuple[dict[str, object], str]:
    _policy, outputs = build_outputs(POLICY_PATH)
    server = json.loads(outputs[XRAY_SERVER_NAME])
    legacy = json.loads(outputs[LEGACY_HEADER_NAME])
    return server, legacy["value"]


EXPECTED_CATALOG_RULE_DOMAINS = [
    "domain:1337x.to",
    "domain:eztv.re",
    "domain:kinozal.tv",
    "domain:limetorrents.lol",
    "domain:nnmclub.to",
    "domain:rutracker.org",
    "domain:rutor.info",
    "domain:thepiratebay.org",
    "domain:torrentdownload.info",
    "domain:torrentgalaxy.to",
    "domain:yts.mx",
]


def _task1_node_runtime() -> dict[str, object]:
    return {
        "isConnected": True,
        "isDisabled": False,
        "isConnecting": False,
        "versions": {"node": "2.8.0", "xray": "26.6.27"},
        "system": {"info": {"platform": "linux", "release": "6.8.0-79-generic"}},
    }


def _task1_plugin_nodes(
    module: ModuleType,
    active_plugin_uuid: str = "task1-plugin",
) -> list[dict[str, object]]:
    return [
        {
            **_task1_node_runtime(),
            "uuid": "de-node",
            "name": module.DE_NODE_NAME,
            "address": module.DE_NODE_ADDRESS,
            "activePluginUuid": active_plugin_uuid,
        },
        {
            **_task1_node_runtime(),
            "uuid": "nl-node",
            "name": module.NL_NODE_NAME,
            "address": module.NL_NODE_ADDRESS,
            "activePluginUuid": active_plugin_uuid,
        },
        {
            **_task1_node_runtime(),
            "uuid": "moscow-node",
            "name": module.MOSCOW_NODE_NAME,
            "address": module.MOSCOW_NODE_ADDRESS,
            "activePluginUuid": active_plugin_uuid,
        },
        {
            **_task1_node_runtime(),
            "uuid": "spb-node",
            "name": module.SPB_NODE_NAME,
            "address": module.SPB_NODE_ADDRESS,
            "activePluginUuid": active_plugin_uuid,
        },
    ]


def _task1_plugin(
    module: ModuleType,
    *,
    plugin_uuid: str = "task1-plugin",
    enabled: bool = True,
    ignore_ips: list[str] | None = None,
    ignore_user_ids: list[int] | None = None,
    block_duration: int = 86400,
) -> dict[str, object]:
    return {
        "uuid": plugin_uuid,
        "name": module.EXPECTED_TASK1_NODE_PLUGIN_NAME,
        "viewPosition": 202,
        "pluginConfig": {
            "ingressFilter": {"enabled": False, "blockedIps": []},
            "egressFilter": {
                "enabled": True,
                "blockedIps": ["ext:tor-exit-nodes", "ext:tor-relays"],
                "blockedPorts": [25, 465, 587],
            },
            "torrentBlocker": {
                "enabled": enabled,
                "ignoreLists": {
                    "ip": [] if ignore_ips is None else ignore_ips,
                    "userId": [] if ignore_user_ids is None else ignore_user_ids,
                },
                "blockDuration": block_duration,
            },
            "connectionDrop": {"enabled": False, "whitelistIps": []},
            "sharedLists": [
                {"name": "ext:tor-exit-nodes", "type": "ipList", "items": []},
                {"name": "ext:tor-relays", "type": "ipList", "items": []},
            ],
        },
    }


def _validate_task1_plugin_preflight(
    module: ModuleType,
    nodes: list[dict[str, object]],
    plugins: list[dict[str, object]],
) -> dict[str, object]:
    return module.validate_torrent_blocker_preflight(
        nodes,
        plugins,
        expected_node_addresses=module.TASK1_PLUGIN_GUARDED_NODE_ADDRESSES,
        expected_plugin_name=module.EXPECTED_TASK1_NODE_PLUGIN_NAME,
        block_duration=module.EXPECTED_TASK1_TORRENT_BLOCKER_DURATION,
    )


def _write_policy_artifact_dir(tmp_path: Path, server: dict[str, object]) -> Path:
    _policy, outputs = build_outputs(POLICY_PATH)
    manifest = json.loads(outputs["manifest.json"])
    artifact_dir = tmp_path / "policy-artifacts"
    artifact_dir.mkdir()

    server_bytes = json.dumps(server, sort_keys=True, separators=(",", ":")).encode()
    legacy_output = outputs[LEGACY_HEADER_NAME]
    legacy_bytes = legacy_output if isinstance(legacy_output, bytes) else legacy_output.encode()
    (artifact_dir / XRAY_SERVER_NAME).write_bytes(server_bytes)
    (artifact_dir / LEGACY_HEADER_NAME).write_bytes(legacy_bytes)
    for name, content in (
        (XRAY_SERVER_NAME, server_bytes),
        (LEGACY_HEADER_NAME, legacy_bytes),
    ):
        manifest["artifacts"][name]["bytes"] = len(content)
        manifest["artifacts"][name]["sha256"] = hashlib.sha256(content).hexdigest()
    (artifact_dir / "manifest.json").write_text(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return artifact_dir


def test_policy_artifact_loader_accepts_plugin_owned_torrent_block(tmp_path: Path) -> None:
    module = _load_module()
    server, _legacy_header = _compiled_artifacts()
    artifact_dir = _write_policy_artifact_dir(tmp_path, server)

    loaded_server, _legacy = module._load_policy_artifacts(artifact_dir)

    assert loaded_server["nodePluginPolicy"]["torrentBlocker"] == {
        "required": True,
        "protocol": "bittorrent",
        "injectedRulePosition": "first",
    }
    _assert_no_manual_torrent_protocol_or_process(loaded_server["rules"])


def test_task1_node_plugin_preflight_accepts_expected_runtime_plugin() -> None:
    module = _load_module()

    result = _validate_task1_plugin_preflight(
        module,
        _task1_plugin_nodes(module),
        [_task1_plugin(module)],
    )

    assert result == {
        "pluginName": module.EXPECTED_TASK1_NODE_PLUGIN_NAME,
        "nodeCount": 4,
        "blockDuration": 86400,
    }


def test_task1_node_plugin_preflight_loads_official_detail_response() -> None:
    module = _load_module()
    plugin_uuid = "11111111-1111-4111-8111-111111111111"
    plugin = _task1_plugin(module, plugin_uuid=plugin_uuid)
    calls: list[tuple[str, str]] = []

    class FakeRemnawaveApi:
        async def request(self, method: str, path: str) -> object:
            calls.append((method, path))
            if path == "/node-plugins":
                return {
                    "nodePlugins": [
                        {
                            "uuid": plugin_uuid,
                            "name": module.EXPECTED_TASK1_NODE_PLUGIN_NAME,
                        }
                    ]
                }
            if path == f"/node-plugins/{plugin_uuid}":
                return plugin
            raise AssertionError(f"unexpected request {method} {path}")

    result = asyncio.run(
        module._task1_torrent_blocker_preflight(
            FakeRemnawaveApi(),
            nodes=_task1_plugin_nodes(
                module,
                active_plugin_uuid=plugin_uuid,
            ),
        )
    )

    assert result["nodeCount"] == 4
    assert calls == [
        ("GET", "/node-plugins"),
        ("GET", f"/node-plugins/{plugin_uuid}"),
    ]


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("missing_active_plugin_uuid", "activePluginUuid"),
        ("wrong_plugin", "must have active plugin"),
        ("disconnected_node", "must be connected"),
        ("disabled_node", "must not be disabled"),
        ("connecting_node", "must not be connecting"),
        ("missing_runtime_versions", "missing runtime versions"),
        ("old_node_version", "Node version is too old"),
        ("old_xray_version", "Xray Core version is too old"),
        ("old_kernel_version", "kernel version is too old"),
        ("non_linux_node", "must run Linux"),
        ("disabled_torrent_blocker", "torrentBlocker"),
        ("nonempty_ignore_list", "torrentBlocker"),
        ("wrong_block_duration", "torrentBlocker"),
        ("missing_expected_address", "address preflight"),
        ("conflicting_active_plugin_alias", "conflicting activePluginUuid"),
        ("conflicting_plugin_config_alias", "conflicting pluginConfig"),
        ("missing_plugin_uuid", "uuid"),
        ("missing_plugin_config", "pluginConfig"),
        ("missing_torrent_blocker", "torrentBlocker"),
        ("zero_expected_plugins", "Expected exactly one"),
        ("duplicate_expected_plugins", "Expected exactly one"),
    ],
)
def test_task1_node_plugin_preflight_fails_closed_on_invalid_runtime_plugin_state(
    mutation: str,
    message: str,
) -> None:
    module = _load_module()
    nodes = _task1_plugin_nodes(module)
    plugin = _task1_plugin(module)
    plugins = [plugin]

    if mutation == "missing_active_plugin_uuid":
        nodes[0].pop("activePluginUuid")
    elif mutation == "wrong_plugin":
        nodes[0]["activePluginUuid"] = "other-plugin"
    elif mutation == "disconnected_node":
        nodes[0]["isConnected"] = False
    elif mutation == "disabled_node":
        nodes[0]["isDisabled"] = True
    elif mutation == "connecting_node":
        nodes[0]["isConnecting"] = True
    elif mutation == "missing_runtime_versions":
        nodes[0].pop("versions")
    elif mutation in {"old_node_version", "old_xray_version"}:
        versions = nodes[0]["versions"]
        assert isinstance(versions, dict)
        versions["node" if mutation == "old_node_version" else "xray"] = "1.0.0"
    elif mutation in {"old_kernel_version", "non_linux_node"}:
        system = nodes[0]["system"]
        assert isinstance(system, dict)
        info = system["info"]
        assert isinstance(info, dict)
        if mutation == "old_kernel_version":
            info["release"] = "4.19.0"
        else:
            info["platform"] = "win32"
    elif mutation == "disabled_torrent_blocker":
        plugin = _task1_plugin(module, enabled=False)
        plugins = [plugin]
    elif mutation == "nonempty_ignore_list":
        plugin = _task1_plugin(module, ignore_ips=["203.0.113.10"])
        plugins = [plugin]
    elif mutation == "wrong_block_duration":
        plugin = _task1_plugin(module, block_duration=3600)
        plugins = [plugin]
    elif mutation == "missing_expected_address":
        nodes = nodes[:-1]
    elif mutation == "conflicting_active_plugin_alias":
        nodes[0]["active_plugin_uuid"] = "other-plugin"
    else:
        if mutation == "conflicting_plugin_config_alias":
            plugin["plugin_config"] = {"torrentBlocker": {"enabled": False}}
        elif mutation == "missing_plugin_uuid":
            plugin.pop("uuid")
        elif mutation == "missing_plugin_config":
            plugin.pop("pluginConfig")
        elif mutation == "missing_torrent_blocker":
            plugin_config = plugin["pluginConfig"]
            assert isinstance(plugin_config, dict)
            plugin_config.pop("torrentBlocker")
        elif mutation == "zero_expected_plugins":
            plugin["name"] = "OTHER_PLUGIN"
        else:
            plugins = [plugin, {**plugin, "uuid": "task1-plugin-duplicate"}]

    with pytest.raises(RuntimeError, match=message):
        _validate_task1_plugin_preflight(module, nodes, plugins)


def test_task1_node_plugin_preflight_rejects_non_object_collections() -> None:
    module = _load_module()

    with pytest.raises(RuntimeError, match="Node collection must be a list"):
        module.validate_torrent_blocker_preflight(
            tuple(_task1_plugin_nodes(module)),
            [_task1_plugin(module)],
            expected_node_addresses=module.TASK1_PLUGIN_GUARDED_NODE_ADDRESSES,
            expected_plugin_name=module.EXPECTED_TASK1_NODE_PLUGIN_NAME,
        )

    with pytest.raises(RuntimeError, match="non-object item"):
        module.validate_torrent_blocker_preflight(
            [*_task1_plugin_nodes(module), "not-a-node"],
            [_task1_plugin(module)],
            expected_node_addresses=module.TASK1_PLUGIN_GUARDED_NODE_ADDRESSES,
            expected_plugin_name=module.EXPECTED_TASK1_NODE_PLUGIN_NAME,
        )


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("missing_node_plugin_policy", "delegate BitTorrent"),
        ("manual_protocol_block", "manual torrent enforcement"),
        ("manual_process_block", "manual torrent enforcement"),
        ("manual_catalog_domain_block", "manual torrent enforcement"),
        ("manual_catalog_keyword_block", "manual torrent enforcement"),
        ("manual_catalog_regexp_block", "manual torrent enforcement"),
    ],
)
def test_policy_artifact_loader_rejects_manual_torrent_enforcement(
    tmp_path: Path,
    mutation: str,
    message: str,
) -> None:
    module = _load_module()
    server, _legacy_header = _compiled_artifacts()
    server = json.loads(json.dumps(server))
    if mutation == "missing_node_plugin_policy":
        server["nodePluginPolicy"]["torrentBlocker"] = {"required": True}
    elif mutation == "manual_protocol_block":
        server["rules"].append(
            {
                "id": "manual_bittorrent_protocol",
                "action": "block",
                "matches": [{"protocol": ["bittorrent"]}],
            }
        )
    elif mutation == "manual_process_block":
        server["rules"].append(
            {
                "id": "manual_torrent_process",
                "action": "block",
                "matches": [{"process": ["qbittorrent.exe"]}],
            }
        )
    elif mutation == "manual_catalog_domain_block":
        server["rules"].append(
            {
                "id": "manual_torrent_catalog",
                "action": "block",
                "matches": [{"domain": ["domain:rutracker.org"]}],
            }
        )
    elif mutation == "manual_catalog_keyword_block":
        server["rules"].append(
            {
                "id": "manual_torrent_catalog_keyword",
                "action": "block",
                "matches": [{"domain": "keyword:rutor"}],
            }
        )
    else:
        server["rules"].append(
            {
                "id": "manual_torrent_catalog_regexp",
                "action": "BLOCK",
                "matches": [{"domain": [r"regexp:.*rutracker\.org$"]}],
            }
        )
    artifact_dir = _write_policy_artifact_dir(tmp_path, server)

    with pytest.raises(RuntimeError, match=message):
        module._load_policy_artifacts(artifact_dir)


def test_rejects_replacing_active_task2_de_superset_profile() -> None:
    module = _load_module()
    node = {
        "configProfile": {
            "activeConfigProfileUuid": "task2-de-profile",
            "activeInbounds": [],
        }
    }
    profiles = [
        {
            "uuid": "task2-de-profile",
            "name": module.TASK2_DE_SUPERSET_PROFILE_NAME,
        }
    ]

    with pytest.raises(RuntimeError, match="Task2 DE superset profile"):
        module._reject_active_task2_de_superset(node, profiles)


def test_allows_task1_apply_when_task2_de_superset_is_not_active() -> None:
    module = _load_module()
    node = {
        "configProfile": {
            "activeConfigProfileUuid": "task1-de-profile",
            "activeInbounds": [],
        }
    }
    profiles = [
        {
            "uuid": "task2-de-profile",
            "name": module.TASK2_DE_SUPERSET_PROFILE_NAME,
        }
    ]

    module._reject_active_task2_de_superset(node, profiles)


def test_build_config_isolates_bridge_and_enforces_ordered_policy() -> None:
    module = _load_module()
    base_config = module._build_base_config(_base_config())
    policy_artifact, _legacy_header = _compiled_artifacts()

    config = module._build_config(
        base_config,
        "bridge-password",
        "2001:db8::1",
        policy_artifact,
        frankfurt_listen="2001:db8::2",
    )

    assert [item["tag"] for item in config["inbounds"]] == [
        "DE_SMART_REALITY_443",
        "DE_SMART_XHTTP_REALITY_8443",
        "DE_SMART_GLOBAL_BRIDGE_9443",
    ]
    for inbound in config["inbounds"]:
        sniffing = inbound["sniffing"]
        assert sniffing["enabled"] is True
        assert {"http", "tls", "quic"}.issubset(set(sniffing["destOverride"]))
        assert sniffing["routeOnly"] is True
    global_bridge_inbound = next(item for item in config["inbounds"] if item["tag"] == "DE_SMART_GLOBAL_BRIDGE_9443")
    assert global_bridge_inbound["listen"] == "2001:db8::2"
    bridge = next(item for item in config["outbounds"] if item["tag"] == "RU_MSK_BRIDGE")
    assert bridge["settings"]["servers"] == [
        {
            "address": "2001:db8::1",
            "port": 9443,
            "password": "bridge-password",
            "method": "chacha20-ietf-poly1305",
            "level": 0,
        }
    ]

    rules = config["routing"]["rules"]
    assert len(rules) == 14
    assert [rule["outboundTag"] for rule in rules] == [
        "DIRECT",
        "DIRECT",
        "DIRECT",
        "DIRECT",
        "BLOCK",
        "BLOCK",
        "BLOCK",
        "BLOCK",
        "DIRECT",
        "DIRECT",
        "RU_MSK_BRIDGE",
        "RU_MSK_BRIDGE",
        "RU_MSK_BRIDGE",
        "DIRECT",
    ]
    _assert_no_manual_torrent_protocol_or_process(rules)
    assert "geosite:category-ads-all" in rules[4]["domain"]
    assert "domain:torproject.org" in rules[5]["domain"]
    assert rules[6]["network"] == "udp"
    assert rules[6]["port"] == "443,853"
    assert rules[7] == {
        "network": "tcp",
        "port": "25,465,587",
        "ruleTag": "block_smtp_abuse",
        "inboundTag": ["DE_SMART_REALITY_443", "DE_SMART_XHTTP_REALITY_8443"],
        "outboundTag": "BLOCK",
    }
    catalog_rule = next(rule for rule in rules if rule["ruleTag"] == "route_catalog_exceptions")
    assert catalog_rule["domain"] == EXPECTED_CATALOG_RULE_DOMAINS
    assert rules.index(catalog_rule) < next(index for index, rule in enumerate(rules) if rule["outboundTag"] == "BLOCK")
    eu_rules = [rule for rule in rules if rule["ruleTag"] == "route_eu_exceptions"]
    assert "geosite:youtube" in eu_rules[0]["domain"]
    assert not any(domain in eu_rules[0]["domain"] for domain in catalog_rule["domain"])
    ru_service_rule = next(rule for rule in rules if rule["ruleTag"] == "route_ru_services")
    assert "domain:ozon.ru" in ru_service_rule["domain"]
    broad_ru_rules = [rule for rule in rules if rule["ruleTag"] == "route_broad_ru"]
    assert broad_ru_rules[0]["domain"] == ["geosite:category-ru"]
    assert broad_ru_rules[1]["ip"] == ["geoip:ru"]
    assert rules[-1] == {
        "network": "tcp,udp",
        "ruleTag": "route_final_eu",
        "inboundTag": ["DE_SMART_REALITY_443", "DE_SMART_XHTTP_REALITY_8443"],
        "outboundTag": "DIRECT",
    }


def test_build_moscow_global_config_scopes_customer_routing_and_bridge_falls_direct() -> None:
    module = _load_module()
    base_config = module._build_base_config(_base_config())
    policy_artifact, _legacy_header = _compiled_artifacts()

    config = module._build_moscow_global_config(
        base_config,
        "global-password",
        "2a0b:4140:ba84::2",
        policy_artifact,
        moscow_listen="2001:db8::3",
    )

    assert [item["tag"] for item in config["inbounds"]] == [
        "MSK_SMART_REALITY_443",
        "MSK_SMART_XHTTP_REALITY_8443",
        "MSK_SMART_RU_BRIDGE_V2_9443",
    ]
    for inbound in config["inbounds"]:
        sniffing = inbound["sniffing"]
        assert sniffing["enabled"] is True
        assert {"http", "tls", "quic"}.issubset(set(sniffing["destOverride"]))
        assert sniffing["routeOnly"] is True
    moscow_bridge_inbound = next(item for item in config["inbounds"] if item["tag"] == "MSK_SMART_RU_BRIDGE_V2_9443")
    assert moscow_bridge_inbound["listen"] == "2001:db8::3"
    assert [item["tag"] for item in config["outbounds"]] == [
        "DIRECT",
        "BLOCK",
        "DE_GLOBAL_BRIDGE",
    ]
    bridge = config["outbounds"][2]
    assert bridge["settings"]["servers"] == [
        {
            "address": "2a0b:4140:ba84::2",
            "port": 9443,
            "password": "global-password",
            "method": "chacha20-ietf-poly1305",
            "level": 0,
        }
    ]

    rules = config["routing"]["rules"]
    assert len(rules) == 14
    assert [rule["outboundTag"] for rule in rules] == [
        "DIRECT",
        "DIRECT",
        "DIRECT",
        "DE_GLOBAL_BRIDGE",
        "BLOCK",
        "BLOCK",
        "BLOCK",
        "BLOCK",
        "DE_GLOBAL_BRIDGE",
        "DE_GLOBAL_BRIDGE",
        "DIRECT",
        "DIRECT",
        "DIRECT",
        "DE_GLOBAL_BRIDGE",
    ]
    assert all(rule["inboundTag"] == ["MSK_SMART_REALITY_443", "MSK_SMART_XHTTP_REALITY_8443"] for rule in rules)
    _assert_no_manual_torrent_protocol_or_process(rules)
    assert rules[7] == {
        "network": "tcp",
        "port": "25,465,587",
        "ruleTag": "block_smtp_abuse",
        "inboundTag": ["MSK_SMART_REALITY_443", "MSK_SMART_XHTTP_REALITY_8443"],
        "outboundTag": "BLOCK",
    }
    assert "MSK_SMART_RU_BRIDGE_V2_9443" not in {tag for rule in rules for tag in rule["inboundTag"]}
    catalog_rule = next(rule for rule in rules if rule["ruleTag"] == "route_catalog_exceptions")
    assert catalog_rule["domain"] == EXPECTED_CATALOG_RULE_DOMAINS
    assert rules.index(catalog_rule) < next(index for index, rule in enumerate(rules) if rule["outboundTag"] == "BLOCK")
    eu_rules = [rule for rule in rules if rule["ruleTag"] == "route_eu_exceptions"]
    assert "geosite:youtube" in eu_rules[0]["domain"]
    assert not any(domain in eu_rules[0]["domain"] for domain in catalog_rule["domain"])
    ru_service_rule = next(rule for rule in rules if rule["ruleTag"] == "route_ru_services")
    assert "domain:ozon.ru" in ru_service_rule["domain"]
    broad_ru_rules = [rule for rule in rules if rule["ruleTag"] == "route_broad_ru"]
    assert broad_ru_rules[0]["domain"] == ["geosite:category-ru"]
    assert broad_ru_rules[1]["ip"] == ["geoip:ru"]
    assert rules[-1]["network"] == "tcp,udp"
    assert rules[-1]["outboundTag"] == "DE_GLOBAL_BRIDGE"


def test_frankfurt_host_shape_requires_one_raw_and_one_xhttp() -> None:
    module = _load_module()
    raw_uuid = "00000000-0000-4000-8000-000000000001"
    xhttp_uuid = "00000000-0000-4000-8000-000000000002"
    hosts = [
        {"port": 2053, "isDisabled": False, "inbound": {"configProfileInboundUuid": raw_uuid}},
        {
            "port": 2083,
            "excludeFromSubscriptionTypes": [],
            "inbound": {"configProfileInboundUuid": xhttp_uuid},
        },
    ]
    inbound_tags = {
        raw_uuid: "DE_SMART_REALITY_443",
        xhttp_uuid: "DE_SMART_XHTTP_REALITY_8443",
    }

    module._validate_frankfurt_host_shape(hosts, inbound_tag_by_uuid=inbound_tags)

    with pytest.raises(RuntimeError, match="exactly one RAW and one XHTTP"):
        module._validate_frankfurt_host_shape(
            [
                {"port": 2053, "inbound": {"configProfileInboundUuid": raw_uuid}},
                {"port": 2053, "inbound": {"configProfileInboundUuid": xhttp_uuid}},
            ],
            inbound_tag_by_uuid={raw_uuid: "DE_SMART_REALITY_443", xhttp_uuid: "VLESS_REALITY_443"},
        )

    with pytest.raises(RuntimeError, match="unknown config-profile inbound"):
        module._validate_frankfurt_host_shape(hosts, inbound_tag_by_uuid={raw_uuid: "VLESS_REALITY_443"})


def test_moscow_host_shape_and_bridge_host_guard() -> None:
    module = _load_module()
    raw_uuid = "00000000-0000-4000-8000-000000000011"
    xhttp_uuid = "00000000-0000-4000-8000-000000000012"
    bridge_uuid = "00000000-0000-4000-8000-000000000013"
    hosts = [
        {"inbound": {"configProfileInboundUuid": raw_uuid}},
        {"inbound": {"configProfileInboundUuid": xhttp_uuid}},
    ]

    module._validate_moscow_host_shape(
        hosts,
        inbound_tag_by_uuid={
            raw_uuid: "VLESS_REALITY_443",
            xhttp_uuid: "VLESS_XHTTP_REALITY_8443",
        },
    )

    with pytest.raises(RuntimeError, match="Moscow hosts must contain exactly one RAW and one XHTTP"):
        module._validate_moscow_host_shape(
            hosts,
            inbound_tag_by_uuid={
                raw_uuid: "VLESS_REALITY_443",
                xhttp_uuid: "VLESS_REALITY_443",
            },
        )

    with pytest.raises(RuntimeError, match="Moscow host port does not match its inbound tag"):
        module._validate_moscow_host_shape(
            [
                {"port": 2083, "inbound": {"configProfileInboundUuid": raw_uuid}},
                {"port": 2083, "inbound": {"configProfileInboundUuid": xhttp_uuid}},
            ],
            inbound_tag_by_uuid={
                raw_uuid: "VLESS_REALITY_443",
                xhttp_uuid: "VLESS_XHTTP_REALITY_8443",
            },
        )

    with pytest.raises(RuntimeError, match="Moscow host must be enabled"):
        module._validate_moscow_host_shape(
            [
                {"port": 2053, "is_disabled": True, "inbound": {"configProfileInboundUuid": raw_uuid}},
                {"port": 2083, "inbound": {"configProfileInboundUuid": xhttp_uuid}},
            ],
            inbound_tag_by_uuid={
                raw_uuid: "VLESS_REALITY_443",
                xhttp_uuid: "VLESS_XHTTP_REALITY_8443",
            },
        )

    with pytest.raises(RuntimeError, match="Moscow host must not be excluded from XRAY_BASE64"):
        module._validate_moscow_host_shape(
            [
                {
                    "port": 2053,
                    "exclude_from_subscription_types": ["XRAY_BASE64"],
                    "inbound": {"configProfileInboundUuid": raw_uuid},
                },
                {"port": 2083, "inbound": {"configProfileInboundUuid": xhttp_uuid}},
            ],
            inbound_tag_by_uuid={
                raw_uuid: "VLESS_REALITY_443",
                xhttp_uuid: "VLESS_XHTTP_REALITY_8443",
            },
        )

    module._validate_no_public_bridge_hosts(
        hosts,
        {"inbounds": [{"tag": "MSK_SMART_RU_BRIDGE_9443", "uuid": bridge_uuid}]},
    )
    with pytest.raises(RuntimeError, match="Bridge inbounds must not have public Remnawave hosts"):
        module._validate_no_public_bridge_hosts(
            [{"inbound": {"configProfileInboundUuid": bridge_uuid}}],
            {"inbounds": [{"tag": "MSK_SMART_RU_BRIDGE_9443", "uuid": bridge_uuid}]},
        )


def test_bridge_isolation_helpers_keep_customer_squad_free_of_bridge_inbounds() -> None:
    module = _load_module()

    assert module._isolated_squad_inbounds("bridge-inbound") == ["bridge-inbound"]
    assert module._isolated_user_squads("bridge-squad") == ["bridge-squad"]

    profiles = [
        {
            "inbounds": [
                {"tag": "VLESS_REALITY_443", "uuid": "moscow-raw"},
                {"tag": "VLESS_XHTTP_REALITY_8443", "uuid": "moscow-xhttp"},
                {"tag": "MSK_SMART_RU_BRIDGE_9443", "uuid": "moscow-bridge"},
                {"tag": "MSK_SMART_RU_BRIDGE_V2_9443", "uuid": "moscow-bridge-v2"},
            ]
        },
        {
            "inbounds": [
                {"tag": "DE_SMART_REALITY_443", "uuid": "de-raw"},
                {"tag": "DE_SMART_XHTTP_REALITY_8443", "uuid": "de-xhttp"},
                {"tag": "DE_SMART_GLOBAL_BRIDGE_9443", "uuid": "de-bridge"},
            ]
        },
    ]
    bridge_inbounds = module._bridge_inbound_uuids_from_profiles(*profiles)
    assert bridge_inbounds == {"moscow-bridge", "moscow-bridge-v2", "de-bridge"}

    desired = module._desired_customer_squad_inbounds(
        ["legacy-customer", "moscow-bridge", "moscow-bridge-v2", "de-bridge", "de-raw"],
        ["moscow-raw", "moscow-xhttp", "de-raw", "de-xhttp"],
        bridge_inbounds,
    )
    assert desired == ["legacy-customer", "de-raw", "moscow-raw", "moscow-xhttp", "de-xhttp"]
    assert "moscow-bridge" not in desired
    assert "de-bridge" not in desired


def test_dry_run_reports_reverse_bridge_and_does_not_mutate(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _load_module()
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
            self.calls.append((method, path))
            if method != "GET":
                raise AssertionError(f"dry-run mutated through {method} {path}")
            if path == "/node-plugins":
                return {"nodePlugins": [_task1_plugin(module)]}
            if path == "/config-profiles":
                return {"configProfiles": [{"name": module.BASE_PROFILE_NAME, "uuid": "base-profile"}]}
            if path == "/config-profiles/base-profile":
                return {
                    "uuid": "base-profile",
                    "name": module.BASE_PROFILE_NAME,
                    "config": _base_config(),
                    "inbounds": _profile_inbounds(),
                }
            if path == "/nodes":
                return {
                    "nodes": [
                        {
                            **_task1_node_runtime(),
                            "uuid": "de-node",
                            "address": module.DE_NODE_ADDRESS,
                            "configProfile": {
                                "activeConfigProfileUuid": "old-de-profile",
                                "activeInbounds": [],
                            },
                            "activePluginUuid": "task1-plugin",
                        },
                        {
                            **_task1_node_runtime(),
                            "uuid": "nl-node",
                            "address": module.NL_NODE_ADDRESS,
                            "name": module.NL_NODE_NAME,
                            "configProfile": {
                                "activeConfigProfileUuid": "old-nl-profile",
                                "activeInbounds": [],
                            },
                            "activePluginUuid": "task1-plugin",
                        },
                        {
                            **_task1_node_runtime(),
                            "uuid": "moscow-node",
                            "address": module.MOSCOW_NODE_ADDRESS,
                            "name": module.MOSCOW_NODE_NAME,
                            "configProfile": {
                                "activeConfigProfileUuid": "old-msk-profile",
                                "activeInbounds": [],
                            },
                            "activePluginUuid": "task1-plugin",
                        },
                        {
                            **_task1_node_runtime(),
                            "uuid": "spb-node",
                            "address": module.SPB_NODE_ADDRESS,
                            "name": module.SPB_NODE_NAME,
                            "configProfile": {
                                "activeConfigProfileUuid": "old-spb-profile",
                                "activeInbounds": [],
                            },
                            "activePluginUuid": "task1-plugin",
                        },
                    ]
                }
            if path == "/hosts":
                return {
                    "hosts": [
                        {
                            "uuid": "host-raw",
                            "address": module.DE_PUBLIC_HOST,
                            "remark": "DE Frankfurt RAW",
                            "inbound": {"configProfileInboundUuid": "base-raw"},
                        },
                        {
                            "uuid": "host-xhttp",
                            "address": module.DE_PUBLIC_HOST,
                            "remark": "DE Frankfurt XHTTP",
                            "inbound": {"configProfileInboundUuid": "base-xhttp"},
                        },
                        {
                            "uuid": "moscow-host-raw",
                            "address": module.MOSCOW_PUBLIC_HOST,
                            "remark": "RU Moscow Reality",
                            "inbound": {"configProfileInboundUuid": "base-raw"},
                        },
                        {
                            "uuid": "moscow-host-xhttp",
                            "address": module.MOSCOW_PUBLIC_HOST,
                            "remark": "RU Moscow XHTTP",
                            "inbound": {"configProfileInboundUuid": "base-xhttp"},
                        },
                        {
                            "uuid": "incy-de-raw",
                            "address": module.DE_PUBLIC_HOST,
                            "remark": "CyberVPN INCY DE RAW",
                            "isHidden": True,
                            "tags": ["PREMIUM_SMART_RU_INCY_DE_RAW"],
                        },
                        {
                            "uuid": "incy-virtual",
                            "address": module.DE_PUBLIC_HOST,
                            "remark": "CyberVPN Premium Smart RU",
                            "isHidden": False,
                            "tags": ["PREMIUM_SMART_RU_INCY_VIRTUAL"],
                        },
                        {
                            "uuid": "incy-msk-raw",
                            "address": module.MOSCOW_PUBLIC_HOST,
                            "remark": "CyberVPN INCY Moscow RAW",
                            "isHidden": True,
                            "tags": ["PREMIUM_SMART_RU_INCY_MSK_RAW"],
                        },
                    ]
                }
            if path == "/internal-squads":
                return {
                    "internalSquads": [
                        {
                            "uuid": "smart-squad",
                            "name": module.SMART_SQUAD_NAME,
                            "inbounds": [],
                        }
                    ]
                }
            if path == "/external-squads":
                return {
                    "externalSquads": [
                        {
                            "uuid": "external-squad",
                            "name": module.EXTERNAL_SQUAD_NAME,
                            "responseHeaders": {"x-existing": "keep"},
                        }
                    ]
                }
            if path in {
                f"/users/by-username/{module.BRIDGE_USERNAME}",
                f"/users/by-username/{module.GLOBAL_BRIDGE_USERNAME}",
            }:
                return None
            raise AssertionError(f"unexpected request {method} {path}")

        async def close(self) -> None:
            self.closed = True

    monkeypatch.setattr(module, "RemnawaveApi", FakeRemnawaveApi)
    monkeypatch.setattr(module, "_load_policy_artifacts", _compiled_artifacts)
    monkeypatch.setenv("REMNAWAVE_TOKEN", "unit-test-token")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "apply-premium-smart-ru-server-routing.py",
            "--rollback-manifest",
            str(tmp_path / "rollback.json"),
        ],
    )

    args = module._parse_args()
    result = asyncio.run(module._run(args))

    assert args.global_bridge_squad == module.GLOBAL_BRIDGE_SQUAD_NAME
    assert args.global_bridge_username == module.GLOBAL_BRIDGE_USERNAME
    assert args.frankfurt_upstream_address == module.FRANKFURT_UPSTREAM_ADDRESS
    assert args.moscow_public_host == module.MOSCOW_PUBLIC_HOST
    assert result == {
        "mode": "dry-run",
        "bridgeUser": "create",
        "bridgeSquad": "create",
        "reverseBridgeUser": "create",
        "reverseBridgeSquad": "create",
        "baseProfile": "update",
        "deProfile": "create",
        "moscowProfile": "create",
        "bridgeProtocol": "shadowsocks",
        "bridgePort": 9443,
        "reverseBridgeInboundTag": "DE_SMART_GLOBAL_BRIDGE_9443",
        "reverseBridgeOutboundTag": "DE_GLOBAL_BRIDGE",
        "reverseBridgeEndpointAddress": "2a0b:4140:ba84::2",
        "reverseBridgeEndpointPort": 9443,
        "reverseBridgePublicHost": "none",
        "incyRoutingHeader": "update",
        "frankfurtHostCount": 2,
        "moscowHostCount": 2,
        "nodePluginPreflight": {
            "pluginName": module.EXPECTED_TASK1_NODE_PLUGIN_NAME,
            "nodeCount": 4,
            "blockDuration": 86400,
        },
        "deProfileInboundCount": 3,
        "moscowProfileInboundCount": 3,
        "directDomainCount": module._policy_domain_count(_compiled_artifacts()[0], "eu"),
        "ruDomainCount": module._policy_domain_count(_compiled_artifacts()[0], "ru"),
        "routingRuleCount": 14,
        "moscowRoutingRuleCount": 14,
    }
    assert len(instances) == 1
    assert instances[0].trusted_proxy_headers is False
    assert all(method == "GET" for method, _path in instances[0].calls)
    assert not (tmp_path / "rollback.json").exists()


def test_apply_rejects_plugin_preflight_failure_before_any_mutation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _load_module()
    instances = []

    class FakeRemnawaveApi:
        def __init__(
            self,
            base_url: str,
            token: str,
            *,
            trusted_proxy_headers: bool = False,
        ) -> None:
            self.calls: list[tuple[str, str]] = []
            instances.append(self)

        async def request(self, method: str, path: str, **kwargs: object) -> object:
            self.calls.append((method, path))
            assert kwargs == {}
            if method != "GET":
                raise AssertionError(f"plugin preflight failure mutated through {method} {path}")
            if path == "/nodes":
                return {"nodes": _task1_plugin_nodes(module, active_plugin_uuid="other-plugin")}
            if path == "/node-plugins":
                return {"nodePlugins": [_task1_plugin(module)]}
            raise AssertionError(f"planning continued after plugin preflight failure through {method} {path}")

        async def close(self) -> None:
            self.closed = True

    monkeypatch.setattr(module, "RemnawaveApi", FakeRemnawaveApi)
    monkeypatch.setattr(module, "_load_policy_artifacts", _compiled_artifacts)
    monkeypatch.setenv("REMNAWAVE_TOKEN", "unit-test-token")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "apply-premium-smart-ru-server-routing.py",
            "--apply",
            "--rollback-manifest",
            str(tmp_path / "rollback.json"),
        ],
    )

    args = module._parse_args()
    with pytest.raises(RuntimeError, match="must have active plugin"):
        asyncio.run(module._run(args))

    assert len(instances) == 1
    assert instances[0].calls == [
        ("GET", "/nodes"),
        ("GET", "/node-plugins"),
    ]
    assert not (tmp_path / "rollback.json").exists()


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
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "apply-premium-smart-ru-server-routing.py",
            "--rollback",
            "--rollback-manifest",
            str(tmp_path / "rollback.json"),
        ],
    )

    args = module._parse_args()
    result = asyncio.run(module._run(args))

    assert result == {"mode": "rollback", "status": "rolled_back"}
    assert len(instances) == 1
    assert instances[0].calls == []
    assert instances[0].closed is True


@pytest.mark.parametrize(
    "url,allowed_hosts",
    [
        ("http://panel.example", ["panel.example"]),
        ("http://panel.example/api", ["panel.example"]),
    ],
)
def test_remnawave_url_rejects_external_plaintext_http(
    url: str,
    allowed_hosts: list[str],
) -> None:
    module = _load_module()

    with pytest.raises(RuntimeError, match="must use https"):
        module._validate_remnawave_url(url, allowed_hosts)


@pytest.mark.parametrize(
    "url",
    [
        "http://remnawave:3000",
        "http://localhost:3000/api",
        "http://127.0.0.1:3000",
        "http://[::1]:3000",
        "https://panel.example/api",
    ],
)
def test_remnawave_url_accepts_internal_http_and_external_https(url: str) -> None:
    module = _load_module()
    hostname = url.split("//", 1)[1].split("/", 1)[0].split(":", 1)[0].strip("[]")
    if "[::1]" in url:
        hostname = "::1"

    module._validate_remnawave_url(url, [hostname])


@pytest.mark.parametrize(
    "url",
    [
        "https://user:secret@panel.example/api",
        "https://panel.example/api?token=secret",
        "https://panel.example/api#secret",
        "https://panel.example/not-api",
    ],
)
def test_remnawave_url_rejects_credential_and_ambiguous_url_parts(url: str) -> None:
    module = _load_module()

    with pytest.raises(RuntimeError):
        module._validate_remnawave_url(url, ["panel.example"])


def test_trusted_proxy_headers_are_internal_only() -> None:
    module = _load_module()

    module._validate_trusted_proxy_headers("http://remnawave:3000", True)
    module._validate_trusted_proxy_headers("https://panel.example", False)
    with pytest.raises(RuntimeError, match="local/internal"):
        module._validate_trusted_proxy_headers("https://panel.example", True)


@pytest.mark.parametrize("listen_address", ["0.0.0.0", "::", "bridge.internal"])
def test_bridge_inbound_rejects_wildcard_and_non_literal_listeners(
    listen_address: str,
) -> None:
    module = _load_module()

    with pytest.raises(RuntimeError, match="Bridge listen address"):
        module._bridge_inbound("BRIDGE", listen_address)


def test_dry_run_count_and_api_transport_are_security_bounded() -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8")

    assert 'MOSCOW_PUBLIC_HOST = "msk-relay.cyber-vpn.org"' in source
    assert '"routingRuleCount": len(planned_config["routing"]["rules"])' in source
    assert '"moscowRoutingRuleCount": len(planned_moscow_config["routing"]["rules"])' in source
    assert '"moscowHostCount": len(moscow_hosts)' in source
    assert '"reverseBridgeUser": "reuse" if global_bridge_user else "create"' in source
    assert '"reverseBridgeSquad": "update" if global_bridge_squad else "create"' in source
    assert '"reverseBridgePublicHost": "none"' in source
    assert '"routingRuleCount": 10' not in source
    assert "trust_env=False" in source
    assert "trusted_proxy_headers: bool = False" in source
    assert '"--trusted-proxy-headers"' in source
    assert '"--moscow-public-host"' in source
    _server, routing_header = _compiled_artifacts()
    incy_routing = json.loads(base64.b64decode(routing_header))
    assert incy_routing["GlobalProxy"] == "true"
    assert incy_routing["DomainStrategy"] == "AsIs"
    assert "geosite:category-ads-all" in incy_routing["BlockSites"]
    assert "domain:yts.mx" not in incy_routing["BlockSites"]
    assert "domain:rutracker.org" not in incy_routing["BlockSites"]
    assert "domain:rutor.info" not in incy_routing["BlockSites"]
    assert "domain:scorecardresearch.com" in incy_routing["BlockSites"]
    assert "domain:torproject.org" in incy_routing["BlockSites"]


def test_remnawave_api_unwraps_official_nodes_and_node_plugins_envelopes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module()
    requests: list[tuple[str, str]] = []
    payloads = [
        {"response": _task1_plugin_nodes(module)},
        {
            "response": {
                "total": 1,
                "nodePlugins": [_task1_plugin(module)],
            }
        },
    ]

    class FakeResponse:
        def __init__(self, payload: object) -> None:
            self._payload = payload
            self.content = json.dumps(payload).encode()

        def raise_for_status(self) -> None:
            return None

        def json(self) -> object:
            return self._payload

    class FakeAsyncClient:
        def __init__(self, **kwargs: object) -> None:
            assert kwargs["base_url"] == "http://remnawave:3000"
            assert kwargs["headers"] == {"Authorization": "Bearer unit-test-token"}
            assert kwargs["trust_env"] is False

        async def request(self, method: str, path: str, **kwargs: object) -> FakeResponse:
            assert kwargs == {}
            requests.append((method, path))
            return FakeResponse(payloads.pop(0))

        async def aclose(self) -> None:
            return None

    monkeypatch.setattr(module.httpx, "AsyncClient", FakeAsyncClient)
    api = module.RemnawaveApi("http://remnawave:3000/api", "unit-test-token")

    nodes = asyncio.run(api.request("GET", "/nodes"))
    plugins = asyncio.run(api.request("GET", "/node-plugins"))
    asyncio.run(api.close())

    assert nodes == _task1_plugin_nodes(module)
    assert plugins == {"total": 1, "nodePlugins": [_task1_plugin(module)]}
    assert requests == [
        ("GET", "/api/nodes"),
        ("GET", "/api/node-plugins"),
    ]


def test_static_moscow_host_rebind_and_rollback_manifest_evidence() -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8")

    assert '"moscowHosts": [' in source
    assert 'for host in manifest.get("moscowHosts", []):' in source
    assert "for host in moscow_hosts:" in source
    assert '"configProfileUuid": moscow_profile["uuid"]' in source
    assert "target_tag = MOSCOW_OLD_TO_NEW_TAG.get(current_tag, current_tag)" in source
    assert '"configProfileInboundUuid": moscow_tags[target_tag]' in source
    assert '_checkpoint(manifest_path, manifest, "moscow_hosts_updated")' in source
    assert "_validate_no_public_bridge_hosts(" in source
    assert 'manifest["failurePhase"] = manifest.get("phase")' in source
    assert 'manifest["failureClass"] = type(apply_error).__name__' in source
    assert "if safe_reason := _safe_failure_reason(apply_error):" in source
    assert 'json={"forceRestart": True}' in source
    assert '_checkpoint(manifest_path, manifest, "nodes_restarted")' in source


def test_existing_bridge_user_preflight_rejects_customer_squad_contamination() -> None:
    module = _load_module()
    bridge_squad = {"uuid": "bridge-squad"}

    module._validate_existing_bridge_user_isolation(
        {"activeInternalSquads": ["bridge-squad"]},
        bridge_squad,
        label="forward bridge",
    )
    with pytest.raises(RuntimeError, match="non-bridge squad assignments"):
        module._validate_existing_bridge_user_isolation(
            {"activeInternalSquads": ["bridge-squad", "customer-squad"]},
            bridge_squad,
            label="forward bridge",
        )
    with pytest.raises(RuntimeError, match="non-bridge squad assignments"):
        module._validate_existing_bridge_user_isolation(
            {"activeInternalSquads": ["customer-squad"]},
            None,
            label="reverse bridge",
        )


def test_rollback_restarts_both_restored_nodes_before_marking_rolled_back(tmp_path: Path) -> None:
    module = _load_module()

    class FakeRemnawaveApi:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str, object]] = []

        async def request(self, method: str, path: str, **kwargs: object) -> object:
            self.calls.append((method, path, kwargs.get("json")))
            if (method, path) == ("GET", "/config-profiles"):
                return {
                    "configProfiles": [
                        {"uuid": "de-profile", "name": "DE"},
                        {"uuid": "moscow-profile", "name": "Moscow"},
                    ]
                }
            return {}

    manifest = {
        "version": 3,
        "smartSquad": {"uuid": "smart-squad", "inbounds": ["base-raw"]},
        "externalSquad": {"uuid": "external-squad", "responseHeaders": {}},
        "deHosts": [],
        "moscowHosts": [],
        "deNode": {"uuid": "de-node", "configProfile": {"activeConfigProfileUuid": "base-profile"}},
        "moscowNode": {
            "uuid": "moscow-node",
            "configProfile": {"activeConfigProfileUuid": "base-profile"},
        },
        "baseProfile": {"uuid": "base-profile", "name": "Base", "config": {}},
        "deProfile": {"uuid": "de-profile", "name": "DE", "config": {}},
        "deProfileName": "DE",
        "moscowProfile": {"uuid": "moscow-profile", "name": "Moscow", "config": {}},
        "moscowProfileName": "Moscow",
    }
    api = FakeRemnawaveApi()
    manifest_path = tmp_path / "rollback.json"

    result = asyncio.run(module._rollback(api, manifest, manifest_path))

    restart_calls = [call for call in api.calls if call[0] == "POST"]
    assert restart_calls == [
        ("POST", "/nodes/de-node/actions/restart", {"forceRestart": True}),
        ("POST", "/nodes/moscow-node/actions/restart", {"forceRestart": True}),
    ]
    last_profile_restore = max(
        index for index, call in enumerate(api.calls) if call[0:2] == ("PATCH", "/config-profiles")
    )
    first_restart = next(index for index, call in enumerate(api.calls) if call[0] == "POST")
    assert first_restart > last_profile_restore
    assert result == {"mode": "rollback", "status": "rolled_back"}
    assert json.loads(manifest_path.read_text(encoding="utf-8"))["phase"] == "rolled_back"


def test_rollback_sanitizes_restored_profiles_without_reintroducing_manual_torrent_policy(tmp_path: Path) -> None:
    module = _load_module()
    dirty_config = _contaminated_torrent_policy_config()
    assert "bittorrent" in json.dumps(dirty_config, sort_keys=True).casefold()
    assert "qbittorrent" in json.dumps(dirty_config, sort_keys=True).casefold()

    class FakeRemnawaveApi:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str, object]] = []

        async def request(self, method: str, path: str, **kwargs: object) -> object:
            self.calls.append((method, path, kwargs.get("json")))
            if (method, path) == ("GET", "/config-profiles"):
                return {"configProfiles": []}
            return {}

    manifest = {
        "version": 3,
        "smartSquad": {"uuid": "smart-squad", "inbounds": ["base-raw"]},
        "externalSquad": {"uuid": "external-squad", "responseHeaders": {}},
        "deHosts": [],
        "moscowHosts": [],
        "deNode": {"uuid": "de-node", "configProfile": {"activeConfigProfileUuid": "base-profile"}},
        "moscowNode": {
            "uuid": "moscow-node",
            "configProfile": {"activeConfigProfileUuid": "base-profile"},
        },
        "baseProfile": {"uuid": "base-profile", "name": "Base", "config": dirty_config},
        "deProfile": {"uuid": "de-profile", "name": "DE", "config": dirty_config},
        "deProfileName": "DE",
        "moscowProfile": {"uuid": "moscow-profile", "name": "Moscow", "config": dirty_config},
        "moscowProfileName": "Moscow",
    }
    api = FakeRemnawaveApi()
    manifest_path = tmp_path / "rollback.json"

    result = asyncio.run(module._rollback(api, manifest, manifest_path))

    profile_patches = [
        call[2] for call in api.calls if call[0:2] == ("PATCH", "/config-profiles") and isinstance(call[2], dict)
    ]
    assert [patch["uuid"] for patch in profile_patches] == [
        "base-profile",
        "de-profile",
        "moscow-profile",
    ]
    for patch in profile_patches:
        _assert_protocol_only_torrent_policy_sanitized(patch["config"])
    assert result == {"mode": "rollback", "status": "rolled_back"}
    assert json.loads(manifest_path.read_text(encoding="utf-8"))["phase"] == "rolled_back"


def test_manifest_must_stay_outside_repository(tmp_path: Path) -> None:
    module = _load_module()

    with pytest.raises(RuntimeError, match=r"\.codex"):
        module._validate_manifest_path(REPO_ROOT / ".codex" / "rollback.json")
    with pytest.raises(RuntimeError, match=r"\.codex"):
        module._validate_manifest_path(tmp_path / ".codex" / "rollback.json")

    assert module._validate_manifest_path(tmp_path / "rollback.json") == (tmp_path / "rollback.json").resolve()


def test_default_manifest_path_uses_private_operator_root(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_module()
    monkeypatch.setattr(sys, "argv", [str(SCRIPT_PATH)])

    args = module._parse_args()

    assert args.rollback_manifest == Path("/var/lib/cybervpn/remnawave/premium-smart-ru-routing-rollback.json")


def test_rollback_manifest_accepts_reverse_bridge_manifest_version(tmp_path: Path) -> None:
    module = _load_module()
    manifest_path = tmp_path / "rollback.json"
    manifest_path.write_text(json.dumps({"version": 3}), encoding="utf-8")
    manifest_path.chmod(0o600)

    assert module._read_manifest(manifest_path) == {"version": 3}

    manifest_path.write_text(json.dumps({"version": 1}), encoding="utf-8")
    manifest_path.chmod(0o600)
    with pytest.raises(RuntimeError, match="version is not supported"):
        module._read_manifest(manifest_path)


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
    module._write_manifest(manifest_path, {"version": 3, "phase": "planned"})
    module._write_manifest(manifest_path, {"version": 3, "phase": "applied"})

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
        module._write_manifest(directory_target, {"version": 3})

    original = tmp_path / "original.json"
    original.write_text("{}", encoding="utf-8")
    original.chmod(0o600)
    hardlink = tmp_path / "hardlink.json"
    module.os.link(original, hardlink)
    with pytest.raises(RuntimeError, match="hard links"):
        module._write_manifest(hardlink, {"version": 3})


def test_manifest_read_rejects_target_swap_after_validation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_module()
    manifest = tmp_path / "rollback.json"
    replacement = tmp_path / "replacement.json"
    module._write_manifest(manifest, {"version": 3, "phase": "planned"})
    module._write_manifest(replacement, {"version": 3, "phase": "attacker"})
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
    module._write_manifest(manifest, {"version": 3})
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
        module._write_manifest(link, {"version": 3})
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
        module._write_manifest(permissive_target, {"version": 3})

    unsafe_parent = tmp_path / "unsafe"
    unsafe_parent.mkdir(mode=0o700)
    unsafe_parent.chmod(unsafe_mode)
    with pytest.raises(RuntimeError, match="must not be group- or world-writable"):
        module._write_manifest(unsafe_parent / "rollback.json", {"version": 3})
