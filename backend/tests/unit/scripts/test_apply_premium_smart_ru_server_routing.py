from __future__ import annotations

import asyncio
import base64
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


def test_build_config_isolates_bridge_and_enforces_ordered_policy() -> None:
    module = _load_module()
    base_config = module._build_base_config(_base_config())
    policy_artifact, _legacy_header = _compiled_artifacts()

    config = module._build_config(base_config, "bridge-password", "2001:db8::1", policy_artifact)

    assert [item["tag"] for item in config["inbounds"]] == [
        "DE_SMART_REALITY_443",
        "DE_SMART_XHTTP_REALITY_8443",
        "DE_SMART_GLOBAL_BRIDGE_9443",
    ]
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
        "BLOCK",
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
    assert "domain:yts.mx" in rules[4]["domain"]
    assert "geosite:category-ads-all" in rules[5]["domain"]
    assert "domain:torproject.org" in rules[6]["domain"]
    assert rules[7]["network"] == "udp"
    assert rules[7]["port"] == "443,853"
    eu_rules = [rule for rule in rules if rule["ruleTag"] == "route_eu_exceptions"]
    assert "geosite:youtube" in eu_rules[0]["domain"]
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
    )

    assert [item["tag"] for item in config["inbounds"]] == [
        "MSK_SMART_REALITY_443",
        "MSK_SMART_XHTTP_REALITY_8443",
        "MSK_SMART_RU_BRIDGE_V2_9443",
    ]
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
        "BLOCK",
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
    assert "MSK_SMART_RU_BRIDGE_V2_9443" not in {tag for rule in rules for tag in rule["inboundTag"]}
    eu_rules = [rule for rule in rules if rule["ruleTag"] == "route_eu_exceptions"]
    assert "geosite:youtube" in eu_rules[0]["domain"]
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
                            "uuid": "de-node",
                            "address": module.DE_NODE_ADDRESS,
                            "configProfile": {
                                "activeConfigProfileUuid": "old-de-profile",
                                "activeInbounds": [],
                            },
                        },
                        {
                            "uuid": "moscow-node",
                            "address": module.MOSCOW_NODE_ADDRESS,
                            "name": module.MOSCOW_NODE_NAME,
                            "configProfile": {
                                "activeConfigProfileUuid": "old-msk-profile",
                                "activeInbounds": [],
                            },
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
    assert "domain:yts.mx" in incy_routing["BlockSites"]
    assert "domain:scorecardresearch.com" in incy_routing["BlockSites"]
    assert "domain:torproject.org" in incy_routing["BlockSites"]


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
    assert "if isinstance(apply_error, RuntimeError):" in source
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
def test_manifest_read_refuses_world_writable_parent(tmp_path: Path) -> None:
    module = _load_module()
    unsafe_parent = tmp_path / "unsafe-read"
    unsafe_parent.mkdir(mode=0o700)
    manifest = unsafe_parent / "rollback.json"
    module._write_manifest(manifest, {"version": 3})
    unsafe_parent.chmod(0o777)

    with pytest.raises(RuntimeError, match="must not be world-writable"):
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
def test_manifest_write_refuses_permissive_target_and_world_writable_parent(
    tmp_path: Path,
) -> None:
    module = _load_module()
    permissive_target = tmp_path / "permissive.json"
    permissive_target.write_text("{}", encoding="utf-8")
    permissive_target.chmod(0o644)
    with pytest.raises(RuntimeError, match="permissions must be 0600"):
        module._write_manifest(permissive_target, {"version": 3})

    unsafe_parent = tmp_path / "unsafe"
    unsafe_parent.mkdir(mode=0o777)
    unsafe_parent.chmod(0o777)
    with pytest.raises(RuntimeError, match="must not be world-writable"):
        module._write_manifest(unsafe_parent / "rollback.json", {"version": 3})
