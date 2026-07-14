from __future__ import annotations

import argparse
import asyncio
import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_PATH = REPO_ROOT / "scripts/remnawave/safe-torrent-blocker-self-test.py"
TEST_RUN_TAG = f"TASK2_SYNTHETIC_SAFE_PROBE:{'a' * 32}"

sys.path.insert(0, str(REPO_ROOT))


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("safe_torrent_blocker_self_test", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _plugin_config() -> dict[str, Any]:
    return {
        "ingressFilter": {"enabled": False, "blockedIps": ["198.51.100.10"]},
        "egressFilter": {
            "enabled": True,
            "blockedIps": ["ext:tor-exit-nodes"],
            "blockedPorts": [25, 465, 587],
            "extraEgressField": {"preserve": True},
        },
        "torrentBlocker": {
            "enabled": True,
            "ignoreLists": {"ip": ["203.0.113.9"], "userId": [777]},
            "blockDuration": 86400,
            "includeRuleTags": ["existing-safe-tag"],
            "unknownTorrentBlockerField": ["must", "stay"],
        },
        "connectionDrop": {"enabled": True, "whitelistIps": ["192.0.2.44"]},
        "sharedLists": [{"name": "ext:tor-exit-nodes", "type": "ipList", "items": ["192.0.2.0/24"]}],
        "futurePluginField": {"nested": {"preserved": ["yes"]}},
    }


def _node(plugin_uuid: str = "plugin-1") -> dict[str, Any]:
    return {
        "uuid": "node-1",
        "name": "DE synthetic node",
        "address": "198.51.100.20",
        "activePluginUuid": plugin_uuid,
        "isConnected": True,
        "isConnecting": False,
        "isDisabled": False,
        "lastStatusChange": "2026-07-14T00:00:00.000Z",
        "configProfile": {"activeConfigProfileUuid": "profile-1", "activeInbounds": []},
    }


def _profile(tag: str = "TASK2_SYNTHETIC_SAFE_PROBE") -> dict[str, Any]:
    return {
        "uuid": "profile-1",
        "name": "Synthetic profile",
        "config": {
            "inbounds": [
                {
                    "tag": "TASK2_SYNTHETIC_INBOUND",
                    "protocol": "vless",
                    "port": 443,
                }
            ],
            "routing": {
                "rules": [
                    {
                        "type": "field",
                        "ruleTag": tag,
                        "domain": ["domain:task2-synthetic.invalid"],
                        "outboundTag": "DIRECT",
                    }
                ]
            },
        },
    }


def _profile_without_dedicated_rule() -> dict[str, Any]:
    profile = _profile(tag="task2-route-evidence-matched")
    profile["config"]["routing"]["rules"] = [
        {
            "type": "field",
            "ruleTag": "task2-management-private-self-block",
            "ip": ["geoip:private"],
            "outboundTag": "BLOCK",
        },
        {
            "type": "field",
            "ruleTag": "task2-ipv6-policy-block",
            "network": "tcp",
            "outboundTag": "BLOCK",
        },
        *profile["config"]["routing"]["rules"],
        {
            "type": "field",
            "ruleTag": "task2-route-evidence-unmatched",
            "domain": ["full:route-evidence-unmatched.invalid"],
            "outboundTag": "DIRECT",
        },
        {
            "type": "field",
            "ruleTag": "task2-final-spb-direct",
            "outboundTag": "DIRECT",
        },
    ]
    return profile


def _report(
    *,
    report_id: int = 101,
    user_uuid: str = "user-synthetic-1",
    username: str = "task2-synthetic-user",
    source_ip: str = "198.51.100.77",
    blocked: bool = True,
    protocol: str = "http",
) -> dict[str, Any]:
    return {
        "id": report_id,
        "userId": 2,
        "nodeId": 10,
        "user": {"uuid": user_uuid, "username": username},
        "node": {"uuid": "node-1", "name": "DE synthetic node", "countryCode": "DE"},
        "report": {
            "actionReport": {
                "blocked": blocked,
                "ip": source_ip,
                "blockDuration": 60,
                "willUnblockAt": "2026-07-14T00:01:00Z",
                "userId": "2",
                "processedAt": "2026-07-14T00:00:00Z",
            },
            "xrayReport": {
                "email": "2",
                "level": 0,
                "protocol": protocol,
                "network": "tcp",
                "source": f"{source_ip}:42000",
                "destination": "10.0.0.5:443",
                "routeTarget": None,
                "originalTarget": "tcp:10.0.0.5:443",
                "inboundTag": "TASK2_SYNTHETIC_INBOUND",
                "inboundName": "safe-probe",
                "inboundLocal": "127.0.0.1:443",
                "outboundTag": "DIRECT",
                "ts": 1780000000,
            },
        },
        "createdAt": "2026-07-14T00:00:00Z",
    }


class FakeRemnawaveApi:
    instances: list[FakeRemnawaveApi] = []
    report_after_trigger = True
    fail_unblock = False
    fail_restore = False
    fail_profile_restore = False
    fail_patch_after_mutation = False
    malformed_executor_response = False
    runtime_transition_delay_polls = 0
    runtime_transition_fail_numbers: set[int] = set()
    profile_drift_after_plugin_sync = False
    initial_profile: dict[str, Any] | None = None

    def __init__(
        self,
        base_url: str,
        token: str,
        *,
        allowed_hosts: list[str],
        trusted_proxy_headers: bool = False,
    ) -> None:
        self.base_url = base_url
        self.token = token
        self.allowed_hosts = allowed_hosts
        self.trusted_proxy_headers = trusted_proxy_headers
        self.original_config = _plugin_config()
        self.plugin = {
            "uuid": "plugin-1",
            "viewPosition": 1,
            "name": "CYBERVPN_PREMIUM_SMART_RU_ABUSE_PROTECTION",
            "pluginConfig": copy.deepcopy(self.original_config),
        }
        self.nodes = [_node()]
        self.profile = copy.deepcopy(FakeRemnawaveApi.initial_profile or _profile())
        self.original_profile_config = copy.deepcopy(self.profile["config"])
        self.reports: list[dict[str, Any]] = []
        self.calls: list[tuple[str, str, Any]] = []
        self.closed = False
        self.triggered = False
        self.runtime_transition_generation = 0
        self.pending_runtime_transition: int | None = None
        self.runtime_transition_poll_count = 0
        self.profile_drift_injected = False
        FakeRemnawaveApi.instances.append(self)

    def _advance_runtime_transition(self) -> None:
        generation = self.pending_runtime_transition
        if generation is None:
            return
        self.runtime_transition_poll_count += 1
        if generation in self.runtime_transition_fail_numbers:
            return
        if self.runtime_transition_poll_count <= self.runtime_transition_delay_polls:
            return
        self.nodes[0]["isConnected"] = True
        self.nodes[0]["isConnecting"] = False
        self.nodes[0]["lastStatusChange"] = f"2026-07-14T00:00:{generation:02d}.000Z"
        self.pending_runtime_transition = None

    async def request(self, method: str, path: str, **kwargs: Any) -> Any:
        self.calls.append((method, path, copy.deepcopy(kwargs.get("json"))))
        if path == "/node-plugins" and method == "GET":
            return {"total": 1, "nodePlugins": [copy.deepcopy(self.plugin)]}
        if path == "/node-plugins/plugin-1" and method == "GET":
            if (
                self.profile_drift_after_plugin_sync
                and not self.profile_drift_injected
                and self.plugin["pluginConfig"]["torrentBlocker"].get("includeRuleTags") == [TEST_RUN_TAG]
            ):
                self.profile["config"]["routing"]["rules"].append(
                    {
                        "type": "field",
                        "ruleTag": "concurrent-production-safety-fix",
                        "domain": ["full:concurrent-safety.invalid"],
                        "outboundTag": "BLOCK",
                    }
                )
                self.profile_drift_injected = True
            return copy.deepcopy(self.plugin)
        if path == "/node-plugins" and method == "PATCH":
            payload = kwargs["json"]
            assert payload["uuid"] == "plugin-1"
            if self.fail_restore and payload["pluginConfig"] == self.original_config:
                raise RuntimeError("restore failed with token=secret")
            self.plugin["pluginConfig"] = copy.deepcopy(payload["pluginConfig"])
            if self.fail_patch_after_mutation and payload["pluginConfig"] != self.original_config:
                self.fail_patch_after_mutation = False
                raise RuntimeError("patch response lost after mutation token=secret")
            return copy.deepcopy(self.plugin)
        if path == "/nodes" and method == "GET":
            self._advance_runtime_transition()
            return {"nodes": copy.deepcopy(self.nodes)}
        if path == "/config-profiles/profile-1" and method == "GET":
            return copy.deepcopy(self.profile)
        if path == "/config-profiles" and method == "PATCH":
            payload = kwargs["json"]
            assert payload["uuid"] == "profile-1"
            if self.fail_profile_restore and payload["config"] == self.original_profile_config:
                raise RuntimeError("profile restore failed token=secret")
            self.profile["config"] = copy.deepcopy(payload["config"])
            if isinstance(payload.get("name"), str):
                self.profile["name"] = payload["name"]
            self.runtime_transition_generation += 1
            self.pending_runtime_transition = self.runtime_transition_generation
            self.runtime_transition_poll_count = 0
            self.nodes[0]["isConnected"] = False
            self.nodes[0]["isConnecting"] = True
            return copy.deepcopy(self.profile)
        if path == "/node-plugins/torrent-blocker" and method == "GET":
            if self.triggered and self.report_after_trigger and not self.reports:
                self.reports.append(_report())
            return {"records": copy.deepcopy(self.reports), "total": len(self.reports)}
        if path == "/node-plugins/executor" and method == "POST":
            if self.fail_unblock:
                raise RuntimeError("unblock failed for 198.51.100.77 token=secret")
            if self.malformed_executor_response:
                return ["not", "an", "ack"]
            return {"eventSent": True}
        raise AssertionError(f"unexpected request {method} {path}")

    async def close(self) -> None:
        self.closed = True


def _args(module: ModuleType, *, apply: bool = False) -> argparse.Namespace:
    return argparse.Namespace(
        apply=apply,
        remnawave_url="http://remnawave:3000",
        allow_remnawave_host=["remnawave", "localhost", "127.0.0.1", "::1"],
        trusted_proxy_headers=False,
        plugin_name="CYBERVPN_PREMIUM_SMART_RU_ABUSE_PROTECTION",
        synthetic_rule_tag="TASK2_SYNTHETIC_SAFE_PROBE",
        node_uuid=["node-1"],
        temporary_profile_rule=False,
        profile_inbound_tag=[],
        target_nodes_json=json.dumps({"target": "specificNodes", "nodeUuids": ["node-1"]}),
        trigger_command_json=json.dumps(
            [
                str(module.TEST_TRIGGER_EXECUTABLE),
                "--target",
                "http://task2-synthetic.invalid",
            ]
        ),
        trigger_executable_sha256=module.TEST_TRIGGER_EXECUTABLE_SHA256,
        absence_check_command_json=None,
        absence_check_executable_sha256=None,
        unblock_command_json=None,
        expected_user_uuid="user-synthetic-1",
        expected_username="task2-synthetic-user",
        expected_action_user_id="2",
        expected_xray_user="task2-synthetic-user",
        expected_xray_tid="task2-tenant",
        expected_source_ip="198.51.100.77",
        expected_destination_ip="10.0.0.5",
        expected_destination_port=443,
        sync_timeout_seconds=0.01,
        sync_poll_interval_seconds=0.0,
        report_timeout_seconds=0.01,
        report_poll_interval_seconds=0.0,
        report_page_size=10,
        trigger_timeout_seconds=1.0,
        confirm_apply=module.APPLY_CONFIRMATION if apply else None,
        confirm_no_live_traffic=module.NO_LIVE_TRAFFIC_CONFIRMATION if apply else None,
        confirm_restore=module.RESTORE_CONFIRMATION if apply else None,
    )


def _temporary_profile_rule_args(module: ModuleType, *, apply: bool = False) -> argparse.Namespace:
    args = _args(module, apply=apply)
    args.temporary_profile_rule = True
    args.profile_inbound_tag = ["TASK2_SYNTHETIC_INBOUND"]
    args.expected_xray_user = "task2-tenant"
    args.expected_xray_tid = "task2-tenant"
    return args


def _production_apply_args(module: ModuleType) -> argparse.Namespace:
    FakeRemnawaveApi.initial_profile = _profile_without_dedicated_rule()
    return _temporary_profile_rule_args(module, apply=True)


@pytest.fixture
def module(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> ModuleType:
    loaded = _load_module()
    approved_root = tmp_path / "approved-probes"
    approved_root.mkdir(mode=0o755)
    trigger_executable = (approved_root / "safe-probe").resolve()
    trigger_executable.write_bytes(b"cybervpn-safe-probe-test-v1")
    absence_executable = (approved_root / "safe-absence").resolve()
    absence_executable.write_bytes(b"cybervpn-safe-absence-test-v1")
    trigger_executable.chmod(0o555)
    absence_executable.chmod(0o555)
    loaded.TEST_TRIGGER_EXECUTABLE = trigger_executable
    loaded.TEST_TRIGGER_EXECUTABLE_SHA256 = hashlib.sha256(trigger_executable.read_bytes()).hexdigest()
    loaded.TEST_ABSENCE_EXECUTABLE = absence_executable
    loaded.TEST_ABSENCE_EXECUTABLE_SHA256 = hashlib.sha256(absence_executable.read_bytes()).hexdigest()
    manifest_path = tmp_path / "safe-probe-manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema": loaded.PROBE_MANIFEST_SCHEMA,
                "helpers": {
                    str(trigger_executable): loaded.TEST_TRIGGER_EXECUTABLE_SHA256,
                    str(absence_executable): loaded.TEST_ABSENCE_EXECUTABLE_SHA256,
                },
            }
        ),
        encoding="utf-8",
    )
    manifest_path.chmod(0o444)
    loaded.APPROVED_PROBE_ROOTS = (approved_root,)
    loaded.APPROVED_PROBE_MANIFEST_PATH = manifest_path
    FakeRemnawaveApi.instances = []
    FakeRemnawaveApi.report_after_trigger = True
    FakeRemnawaveApi.fail_unblock = False
    FakeRemnawaveApi.fail_restore = False
    FakeRemnawaveApi.fail_profile_restore = False
    FakeRemnawaveApi.fail_patch_after_mutation = False
    FakeRemnawaveApi.malformed_executor_response = False
    FakeRemnawaveApi.runtime_transition_delay_polls = 0
    FakeRemnawaveApi.runtime_transition_fail_numbers = set()
    FakeRemnawaveApi.profile_drift_after_plugin_sync = False
    FakeRemnawaveApi.initial_profile = None
    monkeypatch.setattr(loaded, "RemnawaveApi", FakeRemnawaveApi)
    monkeypatch.setattr(
        loaded,
        "_utc_now",
        lambda: datetime(2026, 7, 14, 0, 0, 0, tzinfo=UTC),
    )
    monkeypatch.setenv("REMNAWAVE_TOKEN", "unit-test-remnawave-token")
    monkeypatch.setenv("CYBERVPN_SAFE_TORRENT_BLOCKER_ENV", "production-synthetic")
    monkeypatch.setattr(loaded.secrets, "token_hex", lambda size: "a" * (size * 2))

    def fake_probe(command: list[str], timeout_seconds: float) -> subprocess.CompletedProcess[bytes]:
        assert Path(command[0]).name == "safe-probe"
        assert command[1:] == ["--target", "http://task2-synthetic.invalid"]
        assert timeout_seconds == 1.0
        FakeRemnawaveApi.instances[-1].triggered = True
        return subprocess.CompletedProcess(command, 0, stdout=b"source=198.51.100.77 token=secret", stderr=b"")

    monkeypatch.setattr(loaded, "_run_probe_command", fake_probe)
    return loaded


def test_dry_run_reports_plan_without_mutating(module: ModuleType) -> None:
    result = asyncio.run(module._run(_args(module, apply=False)))
    api = FakeRemnawaveApi.instances[0]

    assert result["status"] == "dry_run"
    assert result["mode"] == "dry-run"
    assert result["plannedMutation"] == {
        "pluginConfigPatch": "pluginConfig.torrentBlocker.includeRuleTags",
        "includeRuleTagsCount": 1,
        "temporaryIncludeRuleTagsReplacement": True,
        "selectedRuleWebhookScopeOnlyWhileEnabled": True,
        "temporaryProfileRule": False,
    }
    assert result["proofScope"] == {
        "plumbing": "webhook_to_nftables_to_report",
        "bitTorrentRecognition": False,
        "perNodeProtocolRecognition": False,
    }
    assert result["plugin"]["preStateHashBackupCaptured"] is True
    assert result["plugin"]["bitTorrentRecognitionProven"] is False
    assert result["plugin"]["perNodeProtocolRecognitionProven"] is False
    assert api.plugin["pluginConfig"] == api.original_config
    assert all(method == "GET" for method, _path, _json in api.calls)
    assert api.closed is True


def test_temporary_profile_rule_dry_run_snapshots_without_mutating(
    module: ModuleType,
) -> None:
    FakeRemnawaveApi.initial_profile = _profile_without_dedicated_rule()

    result = asyncio.run(module._run(_temporary_profile_rule_args(module, apply=False)))
    api = FakeRemnawaveApi.instances[0]

    assert result["status"] == "dry_run"
    assert result["plannedMutation"]["temporaryProfileRule"] is True
    assert result["profileRule"]["mode"] == "temporary_profile_rule"
    assert result["profileRule"]["preStateHashBackupCaptured"] is True
    assert result["profileRule"]["temporaryRule"] == {
        "ruleTagSha256": module._text_hash(TEST_RUN_TAG),
        "domain": "full:task2-synthetic.invalid",
        "network": "tcp",
        "outboundTag": "DIRECT",
        "inboundTagCount": 1,
        "expectedXrayUserSha256": module._sensitive_hash("task2-tenant"),
        "expectedXrayTidSha256": module._sensitive_hash("task2-tenant"),
    }
    assert api.profile["config"] == api.original_profile_config
    assert not any((method, path) == ("PATCH", "/config-profiles") for method, path, _json in api.calls)
    assert not any((method, path) == ("PATCH", "/node-plugins") for method, path, _json in api.calls)


def test_temporary_profile_rule_apply_inserts_scoped_rule_and_restores(
    module: ModuleType,
) -> None:
    FakeRemnawaveApi.initial_profile = _profile_without_dedicated_rule()

    result = asyncio.run(module._run(_temporary_profile_rule_args(module, apply=True)))
    api = FakeRemnawaveApi.instances[0]
    profile_patches = [
        payload for method, path, payload in api.calls if (method, path) == ("PATCH", "/config-profiles")
    ]
    touched_user_or_squad_paths = [
        path
        for _method, path, _payload in api.calls
        if path.startswith("/users") or path.startswith("/internal-squads")
    ]

    assert result["status"] == "passed"
    assert result["profileRule"]["patched"] is True
    assert result["profileRule"]["sync"]["status"] == "observed"
    profile_restore = result["cleanup"]["profileRestore"]
    assert profile_restore["status"] == "verified"
    assert profile_restore["restoredConfigSha256"] == module._json_hash(api.original_profile_config)
    assert profile_restore["hashEqualsPreState"] is True
    assert profile_restore["runtimeTransition"]["status"] == "observed"
    assert profile_restore["runtimeTransition"]["finalConnected"] is True
    assert profile_restore["runtimeTransition"]["finalConnecting"] is False
    assert len(profile_patches) == 2
    patched_rules = profile_patches[0]["config"]["routing"]["rules"]
    assert patched_rules[:2] == api.original_profile_config["routing"]["rules"][:2]
    assert patched_rules[3:] == api.original_profile_config["routing"]["rules"][2:]
    assert all(rule["outboundTag"] == "BLOCK" for rule in patched_rules[:2])
    assert patched_rules[2] == {
        "type": "field",
        "ruleTag": TEST_RUN_TAG,
        "inboundTag": ["TASK2_SYNTHETIC_INBOUND"],
        "domain": ["full:task2-synthetic.invalid"],
        "network": "tcp",
        "user": ["task2-tenant"],
        "outboundTag": "DIRECT",
    }
    catch_all_index = next(
        index for index, rule in enumerate(patched_rules) if rule["ruleTag"] == "task2-final-spb-direct"
    )
    assert catch_all_index > 2
    assert profile_patches[1]["config"] == api.original_profile_config
    assert api.profile["config"] == api.original_profile_config
    assert touched_user_or_squad_paths == []


def test_temporary_profile_rule_requires_xray_user_to_equal_tid_before_api_mutation(
    module: ModuleType,
) -> None:
    args = _temporary_profile_rule_args(module, apply=True)
    args.expected_xray_user = "task2-synthetic-user"
    args.expected_xray_tid = "task2-tenant"

    with pytest.raises(module.SelfTestError) as exc_info:
        asyncio.run(module._run(args))

    assert exc_info.value.code == "expected_xray_user_must_equal_tid"
    assert FakeRemnawaveApi.instances == []


def test_temporary_profile_rule_requires_exactly_one_node_before_api_mutation(
    module: ModuleType,
) -> None:
    args = _temporary_profile_rule_args(module, apply=True)
    args.node_uuid = ["node-1", "node-2"]
    args.target_nodes_json = json.dumps({"target": "specificNodes", "nodeUuids": ["node-1", "node-2"]})

    with pytest.raises(module.SelfTestError) as exc_info:
        asyncio.run(module._run(args))

    assert exc_info.value.code == "temporary_profile_rule_requires_exactly_one_node"
    assert FakeRemnawaveApi.instances == []


def test_temporary_profile_rule_is_not_patched_when_plugin_precheck_fails(
    module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeRemnawaveApi.initial_profile = _profile_without_dedicated_rule()

    async def plugin_drift(*args: Any, **kwargs: Any) -> None:
        raise module.SelfTestError("plugin_config_concurrent_drift_before_patch", phase="preflight")

    monkeypatch.setattr(module, "_assert_plugin_config_matches", plugin_drift)

    with pytest.raises(module.SelfTestFailed) as exc_info:
        asyncio.run(module._run(_temporary_profile_rule_args(module, apply=True)))

    evidence = exc_info.value.evidence
    api = FakeRemnawaveApi.instances[0]
    profile_patches = [
        payload for method, path, payload in api.calls if (method, path) == ("PATCH", "/config-profiles")
    ]
    assert evidence["failure"]["code"] == "plugin_config_concurrent_drift_before_patch"
    assert evidence["cleanup"]["profileRestore"]["status"] == "not_required"
    assert profile_patches == []
    assert api.profile["config"] == api.original_profile_config


def test_temporary_profile_rule_aborts_restore_on_profile_drift_without_overwrite(
    module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeRemnawaveApi.initial_profile = _profile_without_dedicated_rule()
    original_fetch_profile_config = module._fetch_profile_config

    def failed_probe(command: list[str], timeout_seconds: float) -> subprocess.CompletedProcess[bytes]:
        FakeRemnawaveApi.instances[-1].triggered = True
        return subprocess.CompletedProcess(command, 9, stdout=b"", stderr=b"")

    async def drifted_profile_after_primary_failure(api: Any, profile_uuid: str) -> dict[str, Any]:
        config = await original_fetch_profile_config(api, profile_uuid)
        if FakeRemnawaveApi.instances[-1].triggered:
            drifted = copy.deepcopy(config)
            drifted["routing"]["rules"].append(
                {"type": "field", "ruleTag": "concurrent-drift", "outboundTag": "DIRECT"}
            )
            return drifted
        return config

    monkeypatch.setattr(module, "_run_probe_command", failed_probe)
    monkeypatch.setattr(module, "_fetch_profile_config", drifted_profile_after_primary_failure)

    with pytest.raises(module.SelfTestFailed) as exc_info:
        asyncio.run(module._run(_temporary_profile_rule_args(module, apply=True)))

    evidence = exc_info.value.evidence
    api = FakeRemnawaveApi.instances[0]
    profile_restore_patches = [
        payload
        for method, path, payload in api.calls
        if (method, path) == ("PATCH", "/config-profiles") and payload["config"] == api.original_profile_config
    ]
    assert evidence["failure"]["code"] == "profile_config_concurrent_drift_before_restore"
    assert evidence["cleanup"]["profileRestore"]["status"] == "failed"
    assert profile_restore_patches == []


def test_apply_requires_typed_confirmations_before_api_mutation(module: ModuleType) -> None:
    args = _args(module, apply=True)
    args.confirm_no_live_traffic = None

    with pytest.raises(module.SelfTestError) as exc_info:
        asyncio.run(module._run(args))

    assert exc_info.value.code == "missing_confirm_no_live_traffic"
    assert FakeRemnawaveApi.instances == []


def test_apply_requires_environment_marker_before_api_mutation(
    module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CYBERVPN_SAFE_TORRENT_BLOCKER_ENV")

    with pytest.raises(module.SelfTestError) as exc_info:
        asyncio.run(module._run(_args(module, apply=True)))

    assert exc_info.value.code == "production_synthetic_environment_required"
    assert FakeRemnawaveApi.instances == []


@pytest.mark.parametrize(
    "missing_field",
    ["expected_user_uuid", "expected_username", "expected_action_user_id"],
)
def test_production_apply_requires_complete_report_identity_before_api_mutation(
    module: ModuleType,
    missing_field: str,
) -> None:
    args = _production_apply_args(module)
    setattr(args, missing_field, None)

    with pytest.raises(module.SelfTestError) as exc_info:
        asyncio.run(module._run(args))

    assert exc_info.value.code == "complete_expected_identity_required"
    assert FakeRemnawaveApi.instances == []


def test_production_apply_rejects_external_synthetic_destination(
    module: ModuleType,
) -> None:
    args = _production_apply_args(module)
    args.expected_destination_ip = "203.0.113.10"

    with pytest.raises(module.SelfTestError) as exc_info:
        asyncio.run(module._run(args))

    assert exc_info.value.code == "production_synthetic_destination_must_be_internal"
    assert FakeRemnawaveApi.instances == []


@pytest.mark.parametrize("environment", ["local", "staging", "test"])
def test_apply_rejects_non_production_synthetic_environment_before_api_mutation(
    module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
) -> None:
    monkeypatch.setenv("CYBERVPN_SAFE_TORRENT_BLOCKER_ENV", environment)

    with pytest.raises(module.SelfTestError) as exc_info:
        asyncio.run(module._run(_temporary_profile_rule_args(module, apply=True)))

    assert exc_info.value.code == "production_synthetic_environment_required"
    assert FakeRemnawaveApi.instances == []


def test_production_synthetic_mode_labels_evidence_and_uses_temp_profile_rule(
    module: ModuleType,
) -> None:
    FakeRemnawaveApi.initial_profile = _profile_without_dedicated_rule()

    result = asyncio.run(module._run(_temporary_profile_rule_args(module, apply=True)))

    assert result["status"] == "passed"
    assert result["mode"] == "production_synthetic"
    assert result["applyEnvironment"] == "production_synthetic"
    assert result["profileRule"]["patched"] is True
    assert result["cleanup"]["profileRestore"]["hashEqualsPreState"] is True


def test_production_synthetic_requires_temporary_profile_rule_before_api_mutation(
    module: ModuleType,
) -> None:
    with pytest.raises(module.SelfTestError) as exc_info:
        asyncio.run(module._run(_args(module, apply=True)))

    assert exc_info.value.code == "production_synthetic_requires_temporary_profile_rule"
    assert FakeRemnawaveApi.instances == []


def test_production_synthetic_rejects_control_plane_source_ip_before_api_mutation(
    module: ModuleType,
) -> None:
    args = _temporary_profile_rule_args(module, apply=True)
    args.expected_source_ip = "45.87.41.146"

    with pytest.raises(module.SelfTestError) as exc_info:
        asyncio.run(module._run(args))

    assert exc_info.value.code == "production_synthetic_source_ip_must_not_be_control_plane"
    assert FakeRemnawaveApi.instances == []


@pytest.mark.parametrize(
    ("mutator", "expected_code"),
    [
        (lambda args: setattr(args, "sync_timeout_seconds", float("inf")), "invalid_sync_timeout_seconds"),
        (lambda args: setattr(args, "report_timeout_seconds", float("inf")), "invalid_report_timeout_seconds"),
        (lambda args: setattr(args, "trigger_timeout_seconds", 120.0), "invalid_trigger_timeout_seconds"),
        (lambda args: setattr(args, "report_page_size", 1000000000), "invalid_report_page_size"),
    ],
)
def test_apply_rejects_unbounded_controls_before_api_mutation(
    module: ModuleType,
    mutator: Any,
    expected_code: str,
) -> None:
    args = _production_apply_args(module)
    mutator(args)

    with pytest.raises(module.SelfTestError) as exc_info:
        asyncio.run(module._run(args))

    assert exc_info.value.code == expected_code
    assert FakeRemnawaveApi.instances == []


def test_known_production_remnawave_host_is_denied(module: ModuleType) -> None:
    with pytest.raises(module.SelfTestError) as exc_info:
        module._validate_remnawave_url("https://45.87.41.146", ["45.87.41.146"])

    assert exc_info.value.code == "production_remnawave_host_denied"


def test_known_production_remnawave_ipv6_prefix_is_denied(module: ModuleType) -> None:
    with pytest.raises(module.SelfTestError) as exc_info:
        module._validate_remnawave_url(
            "https://[2a0d:2787:1b:12f5::1]",
            ["2a0d:2787:1b:12f5::1"],
        )

    assert exc_info.value.code == "production_remnawave_host_denied"


@pytest.mark.parametrize(
    "hostname",
    ["cyber-vpn.net", "api.cyber-vpn.net", "admin.cyber-vpn.net", "www.cyber-vpn.net"],
)
def test_known_production_public_domains_are_denied_even_if_allowlisted(
    module: ModuleType,
    hostname: str,
) -> None:
    with pytest.raises(module.SelfTestError) as exc_info:
        module._validate_remnawave_url(f"https://{hostname}", [hostname])

    assert exc_info.value.code == "production_remnawave_host_denied"


def test_production_apply_rejects_caller_allowlisted_external_remnawave_host(
    module: ModuleType,
) -> None:
    args = _production_apply_args(module)
    args.remnawave_url = "https://attacker-remnawave.example"
    args.allow_remnawave_host.append("attacker-remnawave.example")

    with pytest.raises(module.SelfTestError) as exc_info:
        asyncio.run(module._run(args))

    assert exc_info.value.code == "safe_operator_requires_internal_remnawave_host"
    assert FakeRemnawaveApi.instances == []


def test_dry_run_rejects_caller_allowlisted_external_remnawave_host_before_token_use(
    module: ModuleType,
) -> None:
    args = _args(module, apply=False)
    args.remnawave_url = "https://attacker-remnawave.example"
    args.allow_remnawave_host.append("attacker-remnawave.example")

    with pytest.raises(module.SelfTestError) as exc_info:
        asyncio.run(module._run(args))

    assert exc_info.value.code == "safe_operator_requires_internal_remnawave_host"
    assert FakeRemnawaveApi.instances == []


def test_trusted_proxy_headers_are_sent_only_when_enabled_for_internal_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_module = _load_module()
    captured: dict[str, Any] = {}

    class CapturingAsyncClient:
        def __init__(self, **kwargs: Any) -> None:
            captured.update(kwargs)

        async def request(self, *args: Any, **kwargs: Any) -> Any:
            raise AssertionError("not used")

        async def aclose(self) -> None:
            return None

    monkeypatch.setattr(real_module.httpx, "AsyncClient", CapturingAsyncClient)

    api = real_module.RemnawaveApi(
        "http://remnawave:3000",
        "secret-token",
        allowed_hosts=["remnawave"],
        trusted_proxy_headers=True,
    )
    asyncio.run(api.close())

    assert captured["headers"] == {
        "Authorization": "Bearer secret-token",
        "X-Forwarded-Proto": "https",
        "X-Forwarded-For": "127.0.0.1",
    }
    assert captured["trust_env"] is False
    assert captured["timeout"] == real_module.httpx.Timeout(20.0, connect=5.0, read=15.0, write=10.0, pool=5.0)


def test_trusted_proxy_headers_reject_external_host_before_client_creation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_module = _load_module()
    created = False

    class CapturingAsyncClient:
        def __init__(self, **kwargs: Any) -> None:
            nonlocal created
            created = True

    monkeypatch.setattr(real_module.httpx, "AsyncClient", CapturingAsyncClient)

    with pytest.raises(real_module.SelfTestError) as exc_info:
        real_module.RemnawaveApi(
            "https://staging-remnawave.example",
            "secret-token",
            allowed_hosts=["staging-remnawave.example"],
            trusted_proxy_headers=True,
        )

    assert exc_info.value.code == "trusted_proxy_headers_require_internal_host"
    assert created is False


def test_probe_subprocess_scrubs_secrets_and_proxy_environment(
    module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_module = _load_module()
    captured: dict[str, Any] = {}

    def fake_run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        captured["command"] = command
        captured.update(kwargs)
        return subprocess.CompletedProcess(command, 0, stdout=b"", stderr=b"")

    monkeypatch.setenv("REMNAWAVE_TOKEN", "must-not-reach-helper")
    monkeypatch.setenv("HTTPS_PROXY", "http://must-not-reach-helper.invalid")
    monkeypatch.setenv("CYBERVPN_PRIVATE_SECRET", "must-not-reach-helper")
    monkeypatch.setattr(real_module.subprocess, "run", fake_run)

    result = real_module._run_probe_command(
        [str(module.TEST_TRIGGER_EXECUTABLE), "--synthetic"],
        1.0,
    )

    assert result.returncode == 0
    assert captured["shell"] is False
    assert captured["stdin"] is subprocess.DEVNULL
    assert captured["cwd"] == str(module.TEST_TRIGGER_EXECUTABLE.parent)
    environment = captured["env"]
    assert "REMNAWAVE_TOKEN" not in environment
    assert "HTTPS_PROXY" not in environment
    assert "CYBERVPN_PRIVATE_SECRET" not in environment
    assert all(key.casefold() in real_module.PROBE_ENV_ALLOWLIST for key in environment)


def test_unsafe_trigger_command_is_rejected_before_api_mutation(module: ModuleType) -> None:
    args = _args(module, apply=True)
    args.trigger_command_json = json.dumps(["aria2c", "magnet:?xt=urn:btih:bad"])

    with pytest.raises(module.SelfTestError) as exc_info:
        asyncio.run(module._run(args))

    assert exc_info.value.code == "unsafe_probe_executable"
    assert FakeRemnawaveApi.instances == []


def test_relative_allowlisted_probe_is_rejected_before_api_mutation(
    module: ModuleType,
) -> None:
    args = _production_apply_args(module)
    args.trigger_command_json = json.dumps(["safe-probe", "--target", "http://task2-synthetic.invalid"])

    with pytest.raises(module.SelfTestError) as exc_info:
        asyncio.run(module._run(args))

    assert exc_info.value.code == "probe_executable_absolute_path_required"
    assert FakeRemnawaveApi.instances == []


def test_probe_executable_hash_mismatch_is_rejected_before_api_mutation(
    module: ModuleType,
) -> None:
    args = _production_apply_args(module)
    args.trigger_executable_sha256 = "0" * 64

    with pytest.raises(module.SelfTestError) as exc_info:
        asyncio.run(module._run(args))

    assert exc_info.value.code == "probe_executable_manifest_sha256_mismatch"
    assert FakeRemnawaveApi.instances == []


def test_allowlisted_helper_outside_approved_root_is_rejected(
    module: ModuleType,
    tmp_path: Path,
) -> None:
    helper = tmp_path / "safe-probe"
    helper.write_bytes(b"caller-controlled-helper")
    helper.chmod(0o555)
    args = _production_apply_args(module)
    args.trigger_command_json = json.dumps([str(helper.resolve()), "--target", "http://task2-synthetic.invalid"])
    args.trigger_executable_sha256 = hashlib.sha256(helper.read_bytes()).hexdigest()

    with pytest.raises(module.SelfTestError) as exc_info:
        asyncio.run(module._run(args))

    assert exc_info.value.code == "probe_executable_outside_approved_root"
    assert FakeRemnawaveApi.instances == []


def test_approved_manifest_hash_must_match_helper_bytes(
    module: ModuleType,
) -> None:
    wrong_hash = "0" * 64
    module.APPROVED_PROBE_MANIFEST_PATH.chmod(0o644)
    module.APPROVED_PROBE_MANIFEST_PATH.write_text(
        json.dumps(
            {
                "schema": module.PROBE_MANIFEST_SCHEMA,
                "helpers": {
                    str(module.TEST_TRIGGER_EXECUTABLE): wrong_hash,
                    str(module.TEST_ABSENCE_EXECUTABLE): module.TEST_ABSENCE_EXECUTABLE_SHA256,
                },
            }
        ),
        encoding="utf-8",
    )
    module.APPROVED_PROBE_MANIFEST_PATH.chmod(0o444)
    args = _production_apply_args(module)
    args.trigger_executable_sha256 = wrong_hash

    with pytest.raises(module.SelfTestError) as exc_info:
        asyncio.run(module._run(args))

    assert exc_info.value.code == "probe_executable_sha256_mismatch"
    assert FakeRemnawaveApi.instances == []


def test_helper_replacement_during_validation_is_rejected(
    module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_hash = module._file_sha256

    def replace_after_hash(path: Path, *, phase: str) -> str:
        digest = original_hash(path, phase=phase)
        if path == module.TEST_TRIGGER_EXECUTABLE:
            path.chmod(0o644)
            path.write_bytes(b"replacement-after-validation-read")
            path.chmod(0o555)
        return digest

    monkeypatch.setattr(module, "_file_sha256", replace_after_hash)

    with pytest.raises(module.SelfTestError) as exc_info:
        asyncio.run(module._run(_production_apply_args(module)))

    assert exc_info.value.code == "probe_artifact_changed_during_validation"
    assert FakeRemnawaveApi.instances == []


def test_helper_replacement_during_execution_is_rejected(
    module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def replace_during_execution(command: list[str], timeout_seconds: float) -> subprocess.CompletedProcess[bytes]:
        helper = Path(command[0])
        helper.chmod(0o644)
        helper.write_bytes(b"replacement-during-execution")
        helper.chmod(0o555)
        return subprocess.CompletedProcess(command, 0, stdout=b"", stderr=b"")

    monkeypatch.setattr(module, "_run_probe_command", replace_during_execution)

    with pytest.raises(module.SelfTestFailed) as exc_info:
        asyncio.run(module._run(_production_apply_args(module)))

    evidence = exc_info.value.evidence
    assert evidence["failure"]["code"] == "probe_artifact_changed_during_execution"
    assert evidence["cleanup"]["restore"]["status"] == "verified"
    assert evidence["cleanup"]["profileRestore"]["status"] == "verified"


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX mode bits are authoritative")
def test_writable_approved_helper_is_rejected(
    module: ModuleType,
) -> None:
    module.TEST_TRIGGER_EXECUTABLE.chmod(0o755)

    with pytest.raises(module.SelfTestError) as exc_info:
        asyncio.run(module._run(_production_apply_args(module)))

    assert exc_info.value.code == "probe_artifact_must_be_read_only"
    assert FakeRemnawaveApi.instances == []


def test_allowlisted_helper_requires_safe_synthetic_target(
    module: ModuleType,
) -> None:
    args = _production_apply_args(module)
    args.trigger_command_json = json.dumps([str(module.TEST_TRIGGER_EXECUTABLE), "--target", "https://torrentz2.nz"])

    with pytest.raises(module.SelfTestError) as exc_info:
        asyncio.run(module._run(args))

    assert exc_info.value.code == "probe_target_must_be_exact_safe_synthetic_url"
    assert FakeRemnawaveApi.instances == []


def test_allowlisted_helper_rejects_extra_external_target_even_with_safe_domain(
    module: ModuleType,
) -> None:
    args = _production_apply_args(module)
    args.trigger_command_json = json.dumps(
        [
            str(module.TEST_TRIGGER_EXECUTABLE),
            "--target",
            "http://task2-synthetic.invalid",
            "--secondary",
            "https://torrentz2.nz",
        ]
    )

    with pytest.raises(module.SelfTestError) as exc_info:
        asyncio.run(module._run(args))

    assert exc_info.value.code == "probe_target_must_be_exact_safe_synthetic_url"
    assert FakeRemnawaveApi.instances == []


@pytest.mark.parametrize(
    "arguments",
    [
        ["task2-synthetic.invalid"],
        ["--target", "http://task2-synthetic.invalid/"],
        ["--target", "http://task2-synthetic.invalid/path"],
        ["--target", "http://task2-synthetic.invalid?query=1"],
        ["--target", "http://task2-synthetic.invalid#fragment"],
        ["--target", "http://task2-synthetic.invalid:80"],
        ["--target", "http://user@task2-synthetic.invalid"],
        ["--target", "https://task2-synthetic.invalid"],
        ["--target", "http://task2-synthetic.invalid", "--extra"],
    ],
)
def test_probe_target_requires_exact_argv(
    module: ModuleType,
    arguments: list[str],
) -> None:
    args = _production_apply_args(module)
    args.trigger_command_json = json.dumps([str(module.TEST_TRIGGER_EXECUTABLE), *arguments])

    with pytest.raises(module.SelfTestError) as exc_info:
        asyncio.run(module._run(args))

    assert exc_info.value.code == "probe_target_must_be_exact_safe_synthetic_url"
    assert FakeRemnawaveApi.instances == []


@pytest.mark.parametrize(
    "command",
    [
        ["powershell", "-NoProfile", "-Command", "Write-Output token=$env:REMNAWAVE_TOKEN"],
        ["curl", "https://torrentz2.nz"],
        ["nc", "203.0.113.10", "6881"],
    ],
)
def test_unapproved_probe_executable_is_rejected_before_api_mutation(
    module: ModuleType,
    command: list[str],
) -> None:
    args = _args(module, apply=True)
    args.trigger_command_json = json.dumps(command)

    with pytest.raises(module.SelfTestError) as exc_info:
        asyncio.run(module._run(args))

    assert exc_info.value.code == "probe_executable_not_allowed"
    assert FakeRemnawaveApi.instances == []


def test_unsafe_absence_check_command_is_rejected_before_api_mutation(module: ModuleType) -> None:
    args = _args(module, apply=True)
    args.absence_check_command_json = json.dumps(["safe-probe", "rutracker.org"])

    with pytest.raises(module.SelfTestError) as exc_info:
        asyncio.run(module._run(args))

    assert exc_info.value.code == "unsafe_probe_mentions_torrent_catalog"
    assert FakeRemnawaveApi.instances == []


def test_allowlisted_probe_rejects_torrent_port_before_api_mutation(module: ModuleType) -> None:
    args = _args(module, apply=True)
    args.trigger_command_json = json.dumps(["safe-probe", "--target", "203.0.113.10:6881"])

    with pytest.raises(module.SelfTestError) as exc_info:
        asyncio.run(module._run(args))

    assert exc_info.value.code == "unsafe_probe_mentions_torrent_port"
    assert FakeRemnawaveApi.instances == []


def test_torrent_catalog_rule_is_rejected_before_mutation(
    module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_request = FakeRemnawaveApi.request

    async def unsafe_catalog_profile(self: FakeRemnawaveApi, method: str, path: str, **kwargs: Any) -> Any:
        if path == "/config-profiles/profile-1" and method == "GET":
            profile = _profile()
            profile["config"]["routing"]["rules"][0]["domain"] = ["domain:rutracker.org"]
            return profile
        return await original_request(self, method, path, **kwargs)

    monkeypatch.setattr(FakeRemnawaveApi, "request", unsafe_catalog_profile)

    with pytest.raises(module.SelfTestFailed) as exc_info:
        asyncio.run(module._run(_args(module, apply=False)))

    api = FakeRemnawaveApi.instances[0]
    assert exc_info.value.evidence["failure"]["code"] == "synthetic_rule_must_use_safe_target"
    assert api.plugin["pluginConfig"] == api.original_config
    assert all(method == "GET" for method, _path, _json in api.calls)


def test_non_synthetic_target_rule_is_rejected_before_mutation(
    module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_request = FakeRemnawaveApi.request

    async def unsafe_geosite_profile(self: FakeRemnawaveApi, method: str, path: str, **kwargs: Any) -> Any:
        if path == "/config-profiles/profile-1" and method == "GET":
            profile = _profile()
            profile["config"]["routing"]["rules"][0]["domain"] = ["geosite:category-p2p"]
            return profile
        return await original_request(self, method, path, **kwargs)

    monkeypatch.setattr(FakeRemnawaveApi, "request", unsafe_geosite_profile)

    with pytest.raises(module.SelfTestFailed) as exc_info:
        asyncio.run(module._run(_args(module, apply=False)))

    api = FakeRemnawaveApi.instances[0]
    assert exc_info.value.evidence["failure"]["code"] == "synthetic_rule_must_use_safe_target"
    assert exc_info.value.evidence["cleanup"]["unblock"]["status"] == "not_started"
    assert api.plugin["pluginConfig"] == api.original_config
    assert not any((method, path) == ("POST", "/node-plugins/executor") for method, path, _json in api.calls)


def test_existing_synthetic_rule_with_attrs_is_rejected_before_mutation(
    module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_request = FakeRemnawaveApi.request

    async def attrs_profile(self: FakeRemnawaveApi, method: str, path: str, **kwargs: Any) -> Any:
        if path == "/config-profiles/profile-1" and method == "GET":
            profile = _profile()
            profile["config"]["routing"]["rules"][0]["attrs"] = "attrs['tId'] == 'task2-tenant'"
            return profile
        return await original_request(self, method, path, **kwargs)

    monkeypatch.setattr(FakeRemnawaveApi, "request", attrs_profile)

    with pytest.raises(module.SelfTestFailed) as exc_info:
        asyncio.run(module._run(_args(module, apply=False)))

    api = FakeRemnawaveApi.instances[0]
    assert exc_info.value.evidence["failure"]["code"] == "synthetic_rule_has_unsupported_fields"
    assert api.plugin["pluginConfig"] == api.original_config
    assert all(method == "GET" for method, _path, _json in api.calls)


def test_concurrent_drift_before_patch_aborts_without_mutation(
    module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_fetch = module._fetch_plugin_config

    async def drifted_config(api: Any, plugin_uuid: str) -> dict[str, Any]:
        config = await original_fetch(api, plugin_uuid)
        drifted = copy.deepcopy(config)
        drifted["torrentBlocker"]["includeRuleTags"] = ["unexpected-concurrent-tag"]
        return drifted

    monkeypatch.setattr(module, "_fetch_plugin_config", drifted_config)

    with pytest.raises(module.SelfTestFailed) as exc_info:
        asyncio.run(module._run(_production_apply_args(module)))

    evidence = exc_info.value.evidence
    api = FakeRemnawaveApi.instances[0]
    assert evidence["failure"]["code"] == "plugin_config_concurrent_drift_before_patch"
    assert evidence["cleanup"]["unblock"]["status"] == "not_required"
    assert not any((method, path) == ("PATCH", "/node-plugins") for method, path, _json in api.calls)
    assert not any((method, path) == ("POST", "/node-plugins/executor") for method, path, _json in api.calls)
    assert api.plugin["pluginConfig"] == api.original_config


def test_profile_drift_after_plugin_sync_aborts_before_profile_patch_and_restores_plugin(
    module: ModuleType,
) -> None:
    FakeRemnawaveApi.profile_drift_after_plugin_sync = True

    with pytest.raises(module.SelfTestFailed) as exc_info:
        asyncio.run(module._run(_production_apply_args(module)))

    evidence = exc_info.value.evidence
    api = FakeRemnawaveApi.instances[0]
    profile_patches = [
        payload for method, path, payload in api.calls if (method, path) == ("PATCH", "/config-profiles")
    ]
    assert evidence["failure"]["code"] == "profile_config_concurrent_drift_before_profile_patch"
    assert profile_patches == []
    assert api.profile_drift_injected is True
    assert any(
        rule.get("ruleTag") == "concurrent-production-safety-fix" for rule in api.profile["config"]["routing"]["rules"]
    )
    assert evidence["cleanup"]["restore"]["status"] == "verified"
    assert api.plugin["pluginConfig"] == api.original_config


def test_include_rule_tag_patch_preserves_every_other_plugin_field(module: ModuleType) -> None:
    original = _plugin_config()

    updated = module._plugin_config_with_include_rule_tags(original, "TASK2_SYNTHETIC_SAFE_PROBE")
    module._assert_only_include_rule_tags_changed(original, updated)

    expected = copy.deepcopy(original)
    expected["torrentBlocker"]["includeRuleTags"] = ["TASK2_SYNTHETIC_SAFE_PROBE"]
    assert updated == expected
    assert original["torrentBlocker"]["includeRuleTags"] == ["existing-safe-tag"]
    assert updated["futurePluginField"] == original["futurePluginField"]
    assert updated["egressFilter"]["extraEgressField"] == {"preserve": True}


def test_apply_success_polls_report_unblocks_and_restores_exact_config(module: ModuleType) -> None:
    result = asyncio.run(module._run(_production_apply_args(module)))
    api = FakeRemnawaveApi.instances[0]
    patches = [payload for method, path, payload in api.calls if (method, path) == ("PATCH", "/node-plugins")]
    executor_payloads = [
        payload for method, path, payload in api.calls if (method, path) == ("POST", "/node-plugins/executor")
    ]

    assert result["status"] == "passed"
    assert result["proofScope"]["bitTorrentRecognition"] is False
    assert result["report"]["newReportCount"] == 1
    assert result["report"]["record"]["blocked"] is True
    assert result["report"]["record"]["runRuleTagBinding"] == "inferred_from_unique_active_plugin_and_profile_config"
    assert result["report"]["record"]["sourceIpSha256"] == module._sensitive_hash("198.51.100.77")
    assert result["report"]["record"]["sourceIpSha256"] != module._text_hash("198.51.100.77")
    assert result["trigger"]["oneShot"] is True
    assert result["trigger"]["stdoutSha256"] == module._sensitive_hash(b"source=198.51.100.77 token=secret")
    assert result["trigger"]["stdoutSha256"] != module._text_hash(b"source=198.51.100.77 token=secret")
    assert result["trigger"]["outputDigest"] == "hmac_sha256_process_secret"
    assert result["plugin"]["runRuleTagSha256"] == module._sensitive_hash(TEST_RUN_TAG)
    assert result["profileRule"]["runtimeTransition"]["status"] == "observed"
    assert result["profileRule"]["runtimeTransition"]["finalConnected"] is True
    assert result["cleanup"]["profileRestore"]["runtimeTransition"]["status"] == "observed"
    assert result["cleanup"]["unblock"]["status"] == "sent"
    assert result["cleanup"]["restore"] == {
        "status": "verified",
        "restoredConfigSha256": module._json_hash(api.original_config),
    }
    assert len(patches) == 2
    assert patches[0]["pluginConfig"]["torrentBlocker"]["includeRuleTags"] == [TEST_RUN_TAG]
    assert patches[1]["pluginConfig"] == api.original_config
    assert executor_payloads == [
        {
            "command": {"command": "unblockIps", "ips": ["198.51.100.77"]},
            "targetNodes": {"target": "specificNodes", "nodeUuids": ["node-1"]},
        }
    ]
    assert api.plugin["pluginConfig"] == api.original_config

    mutation_calls = [
        (path, payload)
        for method, path, payload in api.calls
        if method == "PATCH" and path in {"/node-plugins", "/config-profiles"}
    ]
    assert [path for path, _payload in mutation_calls] == [
        "/node-plugins",
        "/config-profiles",
        "/node-plugins",
        "/config-profiles",
    ]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("ruleTag", TEST_RUN_TAG),
        ("routingRuleTag", [TEST_RUN_TAG]),
        ("matchedRuleTag", TEST_RUN_TAG),
    ],
)
def test_report_with_vendor_rule_tag_binds_exact_run(
    module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: Any,
) -> None:
    original_request = FakeRemnawaveApi.request

    async def report_with_rule_tag(
        self: FakeRemnawaveApi,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> Any:
        if path == "/node-plugins/torrent-blocker" and method == "GET" and self.triggered and not self.reports:
            report = _report()
            report["report"]["xrayReport"][field] = value
            self.reports.append(report)
            return {"records": copy.deepcopy(self.reports), "total": 1}
        return await original_request(self, method, path, **kwargs)

    monkeypatch.setattr(FakeRemnawaveApi, "request", report_with_rule_tag)

    result = asyncio.run(module._run(_production_apply_args(module)))

    assert result["status"] == "passed"
    assert result["report"]["record"]["runRuleTagBinding"] == "exact_report_field"
    assert result["cleanup"]["unblock"]["status"] == "sent"
    assert result["cleanup"]["restore"]["status"] == "verified"


def test_runtime_transition_poll_is_bounded_and_waits_for_reconnect(
    module: ModuleType,
) -> None:
    FakeRemnawaveApi.runtime_transition_delay_polls = 2

    result = asyncio.run(module._run(_production_apply_args(module)))

    assert result["status"] == "passed"
    assert result["profileRule"]["runtimeTransition"]["pollAttempts"] == 3
    assert result["cleanup"]["profileRestore"]["runtimeTransition"]["pollAttempts"] == 3


def test_runtime_transition_timeout_restores_profile_and_plugin(
    module: ModuleType,
) -> None:
    FakeRemnawaveApi.runtime_transition_fail_numbers = {1}

    with pytest.raises(module.SelfTestFailed) as exc_info:
        asyncio.run(module._run(_production_apply_args(module)))

    evidence = exc_info.value.evidence
    api = FakeRemnawaveApi.instances[0]
    assert evidence["failure"]["code"] == "node_runtime_transition_timeout"
    assert evidence["failure"]["phase"] == "sync"
    assert evidence["cleanup"]["restore"]["status"] == "verified"
    assert evidence["cleanup"]["profileRestore"]["status"] == "verified"
    assert api.plugin["pluginConfig"] == api.original_config
    assert api.profile["config"] == api.original_profile_config


def test_runtime_restore_transition_timeout_is_cleanup_failure(
    module: ModuleType,
) -> None:
    FakeRemnawaveApi.runtime_transition_fail_numbers = {2}

    with pytest.raises(module.SelfTestFailed) as exc_info:
        asyncio.run(module._run(_production_apply_args(module)))

    evidence = exc_info.value.evidence
    api = FakeRemnawaveApi.instances[0]
    assert evidence["failure"]["code"] == "node_runtime_restore_transition_timeout"
    assert evidence["failure"]["phase"] == "restore"
    assert evidence["cleanup"]["restore"]["status"] == "verified"
    assert evidence["cleanup"]["profileRestore"]["status"] == "failed"
    assert api.plugin["pluginConfig"] == api.original_config
    assert api.profile["config"] == api.original_profile_config


def test_absence_check_success_is_redacted_after_unblock(
    module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def probe_with_absence(command: list[str], timeout_seconds: float) -> subprocess.CompletedProcess[bytes]:
        if Path(command[0]).name == "safe-probe":
            assert command[1:] == ["--target", "http://task2-synthetic.invalid"]
            FakeRemnawaveApi.instances[-1].triggered = True
        else:
            assert Path(command[0]).name == "safe-absence"
            assert command[1:] == ["--check"]
        return subprocess.CompletedProcess(command, 0, stdout=b"198.51.100.77 token=secret", stderr=b"")

    monkeypatch.setattr(module, "_run_probe_command", probe_with_absence)
    args = _production_apply_args(module)
    args.absence_check_command_json = json.dumps([str(module.TEST_ABSENCE_EXECUTABLE), "--check"])
    args.absence_check_executable_sha256 = module.TEST_ABSENCE_EXECUTABLE_SHA256

    result = asyncio.run(module._run(args))

    assert result["status"] == "passed"
    assert result["cleanup"]["absenceCheck"]["status"] == "passed"
    assert result["cleanup"]["absenceCheck"]["outputRedacted"] is True


def test_patch_mutates_then_raises_still_restores(module: ModuleType) -> None:
    FakeRemnawaveApi.fail_patch_after_mutation = True

    with pytest.raises(module.SelfTestFailed) as exc_info:
        asyncio.run(module._run(_production_apply_args(module)))

    evidence = exc_info.value.evidence
    api = FakeRemnawaveApi.instances[0]
    restore_patches = [
        payload
        for method, path, payload in api.calls
        if (method, path) == ("PATCH", "/node-plugins") and payload["pluginConfig"] == api.original_config
    ]
    assert evidence["failure"]["code"] == "unexpected_failure"
    assert evidence["cleanup"]["unblock"]["status"] == "not_required"
    assert evidence["cleanup"]["restore"]["status"] == "verified"
    assert restore_patches
    assert api.plugin["pluginConfig"] == api.original_config


def test_pre_mutation_failure_does_not_unblock(
    module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_request = FakeRemnawaveApi.request

    async def wrong_plugin_node(self: FakeRemnawaveApi, method: str, path: str, **kwargs: Any) -> Any:
        if path == "/nodes" and method == "GET":
            node = _node(plugin_uuid="other-plugin")
            return {"nodes": [node]}
        return await original_request(self, method, path, **kwargs)

    monkeypatch.setattr(FakeRemnawaveApi, "request", wrong_plugin_node)

    with pytest.raises(module.SelfTestFailed) as exc_info:
        asyncio.run(module._run(_production_apply_args(module)))

    evidence = exc_info.value.evidence
    api = FakeRemnawaveApi.instances[0]
    assert evidence["failure"]["code"] == "selected_node_plugin_mismatch"
    assert evidence["cleanup"]["unblock"]["status"] == "not_required"
    assert not any((method, path) == ("POST", "/node-plugins/executor") for method, path, _json in api.calls)
    assert api.plugin["pluginConfig"] == api.original_config


def test_report_timeout_still_unblocks_and_restores(module: ModuleType) -> None:
    FakeRemnawaveApi.report_after_trigger = False

    with pytest.raises(module.SelfTestFailed) as exc_info:
        asyncio.run(module._run(_production_apply_args(module)))

    evidence = exc_info.value.evidence
    api = FakeRemnawaveApi.instances[0]
    assert evidence["failure"]["code"] == "report_timeout"
    assert evidence["cleanup"]["unblock"] == {
        "status": "not_required",
        "reason": "no_valid_report_observed",
    }
    assert evidence["cleanup"]["restore"]["status"] == "verified"
    assert api.plugin["pluginConfig"] == api.original_config


def test_wrong_node_report_fails(module: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    original_request = FakeRemnawaveApi.request

    async def wrong_node_report(self: FakeRemnawaveApi, method: str, path: str, **kwargs: Any) -> Any:
        if path == "/node-plugins/torrent-blocker" and method == "GET" and self.triggered and not self.reports:
            report = _report()
            report["node"]["uuid"] = "other-node"
            self.reports.append(report)
            return {"records": copy.deepcopy(self.reports), "total": 1}
        return await original_request(self, method, path, **kwargs)

    monkeypatch.setattr(FakeRemnawaveApi, "request", wrong_node_report)

    with pytest.raises(module.SelfTestFailed) as exc_info:
        asyncio.run(module._run(_production_apply_args(module)))

    evidence = exc_info.value.evidence
    api = FakeRemnawaveApi.instances[0]
    assert evidence["failure"]["code"] == "report_timeout"
    assert evidence["cleanup"]["unblock"] == {
        "status": "not_required",
        "reason": "no_valid_report_observed",
    }
    assert evidence["cleanup"]["restore"]["status"] == "verified"
    assert api.plugin["pluginConfig"] == api.original_config


@pytest.mark.parametrize(
    ("xray_source", "expected_code"),
    [
        (None, "report_xray_source_missing"),
        ("", "report_xray_source_missing"),
        ("not-an-endpoint", "report_xray_source_invalid"),
    ],
)
def test_report_requires_parseable_matching_xray_source(
    module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    xray_source: str | None,
    expected_code: str,
) -> None:
    original_request = FakeRemnawaveApi.request

    async def invalid_xray_source_report(
        self: FakeRemnawaveApi,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> Any:
        if path == "/node-plugins/torrent-blocker" and method == "GET" and self.triggered and not self.reports:
            report = _report()
            report["report"]["xrayReport"]["source"] = xray_source
            self.reports.append(report)
            return {"records": copy.deepcopy(self.reports), "total": 1}
        return await original_request(self, method, path, **kwargs)

    monkeypatch.setattr(
        FakeRemnawaveApi,
        "request",
        invalid_xray_source_report,
    )

    with pytest.raises(module.SelfTestFailed) as exc_info:
        asyncio.run(module._run(_production_apply_args(module)))

    evidence = exc_info.value.evidence
    assert evidence["failure"]["code"] == expected_code
    assert evidence["report"]["status"] == "rejected_probe_bound_report"
    assert evidence["cleanup"]["unblock"]["status"] == "sent"
    assert evidence["cleanup"]["restore"]["status"] == "verified"


def test_stale_same_identity_report_fails(module: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    original_request = FakeRemnawaveApi.request

    async def stale_report(self: FakeRemnawaveApi, method: str, path: str, **kwargs: Any) -> Any:
        if path == "/node-plugins/torrent-blocker" and method == "GET" and self.triggered and not self.reports:
            report = _report()
            report["createdAt"] = "2026-07-13T23:59:59Z"
            report["report"]["actionReport"]["processedAt"] = "2026-07-13T23:59:59Z"
            self.reports.append(report)
            return {"records": copy.deepcopy(self.reports), "total": 1}
        return await original_request(self, method, path, **kwargs)

    monkeypatch.setattr(FakeRemnawaveApi, "request", stale_report)

    with pytest.raises(module.SelfTestFailed) as exc_info:
        asyncio.run(module._run(_production_apply_args(module)))

    evidence = exc_info.value.evidence
    api = FakeRemnawaveApi.instances[0]
    assert evidence["failure"]["code"] == "report_timeout"
    assert evidence["cleanup"]["unblock"] == {
        "status": "not_required",
        "reason": "no_valid_report_observed",
    }
    assert evidence["cleanup"]["restore"]["status"] == "verified"
    assert api.plugin["pluginConfig"] == api.original_config


def test_report_with_wrong_inbound_fails_and_unblocks(module: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    original_request = FakeRemnawaveApi.request

    async def missing_marker_report(self: FakeRemnawaveApi, method: str, path: str, **kwargs: Any) -> Any:
        if path == "/node-plugins/torrent-blocker" and method == "GET" and self.triggered and not self.reports:
            report = _report()
            report["report"]["xrayReport"]["inboundTag"] = "ordinary-inbound"
            report["report"]["xrayReport"]["inboundName"] = "ordinary-probe"
            self.reports.append(report)
            return {"records": copy.deepcopy(self.reports), "total": 1}
        return await original_request(self, method, path, **kwargs)

    monkeypatch.setattr(FakeRemnawaveApi, "request", missing_marker_report)

    with pytest.raises(module.SelfTestFailed) as exc_info:
        asyncio.run(module._run(_production_apply_args(module)))

    evidence = exc_info.value.evidence
    api = FakeRemnawaveApi.instances[0]
    assert evidence["failure"]["code"] == "report_xray_inbound_tag_mismatch"
    assert evidence["report"]["status"] == "rejected_probe_bound_report"
    assert evidence["cleanup"]["unblock"]["status"] == "sent"
    assert evidence["cleanup"]["restore"]["status"] == "verified"
    assert api.plugin["pluginConfig"] == api.original_config


@pytest.mark.parametrize(
    ("field", "value", "expected_code"),
    [
        ("email", "999", "report_xray_email_mismatch"),
        ("inboundTag", "OTHER_INBOUND", "report_xray_inbound_tag_mismatch"),
        ("network", "udp", "report_xray_network_mismatch"),
        ("outboundTag", "BLOCK", "report_xray_outbound_mismatch"),
        ("ruleTag", "OTHER_RUN_TAG", "report_xray_rule_tag_mismatch"),
        ("ruleTag", "", "report_xray_rule_tag_mismatch"),
        ("ruleTag", 123, "report_xray_rule_tag_mismatch"),
        (
            "ruleTag",
            [TEST_RUN_TAG, "OTHER_RUN_TAG"],
            "report_xray_rule_tag_mismatch",
        ),
        (
            "ruleTag",
            [TEST_RUN_TAG, 123],
            "report_xray_rule_tag_mismatch",
        ),
        (
            "ruleTag",
            [TEST_RUN_TAG, ""],
            "report_xray_rule_tag_mismatch",
        ),
        ("destination", "10.0.0.6:443", "report_xray_destination_mismatch"),
        (
            "originalTarget",
            "tcp:10.0.0.6:443",
            "report_xray_original_target_mismatch",
        ),
        ("routeTarget", "tcp:10.0.0.6:443", "report_xray_route_target_mismatch"),
    ],
)
def test_probe_bound_report_requires_exact_xray_contract_and_unblocks(
    module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: Any,
    expected_code: str,
) -> None:
    original_request = FakeRemnawaveApi.request

    async def mismatched_report(
        self: FakeRemnawaveApi,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> Any:
        if path == "/node-plugins/torrent-blocker" and method == "GET" and self.triggered and not self.reports:
            report = _report()
            report["report"]["xrayReport"][field] = value
            self.reports.append(report)
            return {"records": copy.deepcopy(self.reports), "total": 1}
        return await original_request(self, method, path, **kwargs)

    monkeypatch.setattr(FakeRemnawaveApi, "request", mismatched_report)

    with pytest.raises(module.SelfTestFailed) as exc_info:
        asyncio.run(module._run(_production_apply_args(module)))

    evidence = exc_info.value.evidence
    assert evidence["failure"]["code"] == expected_code
    assert evidence["report"]["status"] == "rejected_probe_bound_report"
    assert evidence["cleanup"]["unblock"]["status"] == "sent"
    assert evidence["cleanup"]["restore"]["status"] == "verified"
    assert evidence["cleanup"]["profileRestore"]["status"] == "verified"


def test_unrelated_concurrent_report_is_ignored_when_exact_probe_report_exists(
    module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_request = FakeRemnawaveApi.request

    async def concurrent_reports(
        self: FakeRemnawaveApi,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> Any:
        if path == "/node-plugins/torrent-blocker" and method == "GET" and self.triggered and not self.reports:
            self.reports.extend(
                [
                    _report(report_id=101),
                    _report(
                        report_id=102,
                        user_uuid="unrelated-user",
                        username="unrelated-user",
                        source_ip="198.51.100.88",
                    ),
                ]
            )
            return {"records": copy.deepcopy(self.reports), "total": 2}
        return await original_request(self, method, path, **kwargs)

    monkeypatch.setattr(FakeRemnawaveApi, "request", concurrent_reports)

    result = asyncio.run(module._run(_production_apply_args(module)))

    assert result["status"] == "passed"
    assert result["report"]["newReportCount"] == 1
    assert result["cleanup"]["unblock"]["status"] == "sent"


def test_unrelated_report_one_poll_before_probe_report_is_ignored(
    module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_request = FakeRemnawaveApi.request
    report_polls = 0

    async def delayed_probe_report(
        self: FakeRemnawaveApi,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> Any:
        nonlocal report_polls
        if path == "/node-plugins/torrent-blocker" and method == "GET" and self.triggered:
            report_polls += 1
            if report_polls == 1:
                self.reports.append(
                    _report(
                        report_id=102,
                        user_uuid="unrelated-user",
                        username="unrelated-user",
                        source_ip="198.51.100.88",
                    )
                )
            elif report_polls == 2:
                self.reports.insert(0, _report(report_id=101))
            return {"records": copy.deepcopy(self.reports), "total": len(self.reports)}
        return await original_request(self, method, path, **kwargs)

    monkeypatch.setattr(FakeRemnawaveApi, "request", delayed_probe_report)

    result = asyncio.run(module._run(_production_apply_args(module)))

    assert report_polls == 2
    assert result["status"] == "passed"
    assert result["report"]["newReportCount"] == 1
    assert result["cleanup"]["unblock"]["status"] == "sent"


def test_multiple_probe_bound_reports_fail_unblock_and_restore(
    module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_request = FakeRemnawaveApi.request

    async def multiple_reports(self: FakeRemnawaveApi, method: str, path: str, **kwargs: Any) -> Any:
        if path == "/node-plugins/torrent-blocker" and method == "GET" and self.triggered and not self.reports:
            self.reports.extend([_report(report_id=101), _report(report_id=102)])
            return {"records": copy.deepcopy(self.reports), "total": 2}
        return await original_request(self, method, path, **kwargs)

    monkeypatch.setattr(FakeRemnawaveApi, "request", multiple_reports)

    with pytest.raises(module.SelfTestFailed) as exc_info:
        asyncio.run(module._run(_production_apply_args(module)))

    evidence = exc_info.value.evidence
    api = FakeRemnawaveApi.instances[0]
    assert evidence["failure"]["code"] == "multiple_probe_bound_reports"
    assert evidence["report"]["status"] == "rejected_probe_bound_report"
    assert evidence["cleanup"]["unblock"]["status"] == "sent"
    assert evidence["cleanup"]["restore"]["status"] == "verified"
    assert api.plugin["pluginConfig"] == api.original_config


def test_trigger_failure_still_unblocks_and_restores(
    module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def failed_probe(command: list[str], timeout_seconds: float) -> subprocess.CompletedProcess[bytes]:
        FakeRemnawaveApi.instances[-1].triggered = True
        return subprocess.CompletedProcess(command, 9, stdout=b"", stderr=b"token=secret 198.51.100.77")

    monkeypatch.setattr(module, "_run_probe_command", failed_probe)

    with pytest.raises(module.SelfTestFailed) as exc_info:
        asyncio.run(module._run(_production_apply_args(module)))

    evidence = exc_info.value.evidence
    api = FakeRemnawaveApi.instances[0]
    assert evidence["failure"]["code"] == "trigger_failed"
    assert evidence["report"]["status"] == "observed"
    assert evidence["cleanup"]["unblock"]["status"] == "sent"
    assert evidence["cleanup"]["restore"]["status"] == "verified"
    assert api.plugin["pluginConfig"] == api.original_config


def test_failed_helper_does_not_accept_or_unblock_unrelated_report(
    module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_request = FakeRemnawaveApi.request

    def failed_probe(command: list[str], timeout_seconds: float) -> subprocess.CompletedProcess[bytes]:
        FakeRemnawaveApi.instances[-1].triggered = True
        return subprocess.CompletedProcess(command, 9, stdout=b"", stderr=b"failed")

    async def unrelated_report(
        self: FakeRemnawaveApi,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> Any:
        if path == "/node-plugins/torrent-blocker" and method == "GET" and self.triggered and not self.reports:
            self.reports.append(
                _report(
                    user_uuid="unrelated-user",
                    username="unrelated-user",
                    source_ip="198.51.100.88",
                )
            )
            return {"records": copy.deepcopy(self.reports), "total": 1}
        return await original_request(self, method, path, **kwargs)

    monkeypatch.setattr(module, "_run_probe_command", failed_probe)
    monkeypatch.setattr(FakeRemnawaveApi, "request", unrelated_report)

    with pytest.raises(module.SelfTestFailed) as exc_info:
        asyncio.run(module._run(_production_apply_args(module)))

    evidence = exc_info.value.evidence
    assert evidence["failure"]["code"] == "trigger_failed"
    assert evidence["cleanup"]["unblock"] == {
        "status": "not_required",
        "reason": "no_valid_report_observed",
    }
    assert evidence["cleanup"]["restore"]["status"] == "verified"
    assert evidence["cleanup"]["profileRestore"]["status"] == "verified"


def test_trigger_timeout_still_recovers_report_unblocks_and_restores(
    module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def timed_out_probe(command: list[str], timeout_seconds: float) -> None:
        FakeRemnawaveApi.instances[-1].triggered = True
        raise subprocess.TimeoutExpired(command, timeout_seconds)

    monkeypatch.setattr(module, "_run_probe_command", timed_out_probe)

    with pytest.raises(module.SelfTestFailed) as exc_info:
        asyncio.run(module._run(_production_apply_args(module)))

    evidence = exc_info.value.evidence
    api = FakeRemnawaveApi.instances[0]
    assert evidence["failure"]["code"] == "trigger_timeout"
    assert evidence["report"]["status"] == "observed"
    assert evidence["cleanup"]["unblock"]["status"] == "sent"
    assert evidence["cleanup"]["restore"]["status"] == "verified"
    assert evidence["cleanup"]["profileRestore"]["status"] == "verified"
    assert api.plugin["pluginConfig"] == api.original_config
    assert api.profile["config"] == api.original_profile_config


def test_unblock_failure_is_reported_after_restore(module: ModuleType) -> None:
    FakeRemnawaveApi.fail_unblock = True

    with pytest.raises(module.SelfTestFailed) as exc_info:
        asyncio.run(module._run(_production_apply_args(module)))

    evidence = exc_info.value.evidence
    api = FakeRemnawaveApi.instances[0]
    assert evidence["failure"]["code"] == "unblock_failed"
    assert evidence["failure"]["phase"] == "unblock"
    assert evidence["cleanup"]["unblock"]["status"] == "failed"
    assert evidence["cleanup"]["restore"]["status"] == "verified"
    assert api.plugin["pluginConfig"] == api.original_config


def test_malformed_unblock_executor_response_is_failure_after_restore(
    module: ModuleType,
) -> None:
    FakeRemnawaveApi.malformed_executor_response = True

    with pytest.raises(module.SelfTestFailed) as exc_info:
        asyncio.run(module._run(_production_apply_args(module)))

    evidence = exc_info.value.evidence
    api = FakeRemnawaveApi.instances[0]
    assert evidence["failure"]["code"] == "unblock_event_not_sent"
    assert evidence["failure"]["phase"] == "unblock"
    assert evidence["cleanup"]["unblock"]["status"] == "failed"
    assert evidence["cleanup"]["restore"]["status"] == "verified"
    assert api.plugin["pluginConfig"] == api.original_config


@pytest.mark.parametrize(
    ("target_nodes", "expected_code"),
    [
        (
            {"target": "specificNodes", "nodeUuids": ["other-node"]},
            "target_nodes_must_match_selected_nodes",
        ),
        (
            {"target": "specificNodes", "nodeUuids": ["node-1", "node-1"]},
            "target_nodes_duplicate_node_uuid",
        ),
        (
            {"target": "allNodes", "nodeUuids": ["node-1"]},
            "target_nodes_must_target_specific_nodes",
        ),
        (
            {"target": "specificNodes", "nodeUuids": "node-1"},
            "target_nodes_must_use_node_uuids",
        ),
        (
            {"nodeUuids": ["node-1"]},
            "target_nodes_must_use_exact_specific_nodes_schema",
        ),
        (
            {"allNodes": True},
            "target_nodes_must_use_exact_specific_nodes_schema",
        ),
        (
            {"target": "specificNodes", "nodeUuids": ["node-1"], "allNodes": True},
            "target_nodes_must_use_exact_specific_nodes_schema",
        ),
    ],
)
def test_unblock_executor_targets_must_match_selected_nodes(
    module: ModuleType,
    target_nodes: dict[str, Any],
    expected_code: str,
) -> None:
    args = _production_apply_args(module)
    args.target_nodes_json = json.dumps(target_nodes)

    with pytest.raises(module.SelfTestFailed) as exc_info:
        asyncio.run(module._run(args))

    evidence = exc_info.value.evidence
    api = FakeRemnawaveApi.instances[0]
    assert evidence["failure"]["code"] == expected_code
    assert evidence["failure"]["phase"] == "unblock"
    assert evidence["cleanup"]["restore"]["status"] == "verified"
    assert api.plugin["pluginConfig"] == api.original_config


@pytest.mark.parametrize(
    "unblock_command",
    [
        {"type": "unblockIps", "ips": ["{{source_ip}}"]},
        {
            "command": "deleteSomethingElse",
            "comment": "unblockIps",
            "ips": ["{{source_ip}}"],
        },
        {
            "command": "unblockIps",
            "ips": ["{{source_ip}}"],
            "type": "unblockIps",
        },
    ],
)
def test_custom_unblock_command_must_match_official_schema(
    module: ModuleType,
    unblock_command: dict[str, Any],
) -> None:
    args = _production_apply_args(module)
    args.unblock_command_json = json.dumps(unblock_command)

    with pytest.raises(module.SelfTestFailed) as exc_info:
        asyncio.run(module._run(args))

    evidence = exc_info.value.evidence
    api = FakeRemnawaveApi.instances[0]
    assert evidence["failure"]["code"] == "unblock_command_must_match_official_schema"
    assert evidence["failure"]["phase"] == "unblock"
    assert evidence["cleanup"]["restore"]["status"] == "verified"
    assert api.plugin["pluginConfig"] == api.original_config


@pytest.mark.parametrize(
    "failure_mode",
    ["sync_timeout", "report_not_blocked", "trigger_failure"],
)
def test_restore_runs_for_every_failure_after_mutation(
    module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    failure_mode: str,
) -> None:
    if failure_mode == "sync_timeout":

        async def sync_timeout(*args: Any, **kwargs: Any) -> int:
            raise module.SelfTestError("node_config_sync_timeout", phase="sync")

        monkeypatch.setattr(module, "_poll_plugin_config", sync_timeout)
    elif failure_mode == "report_not_blocked":
        original_request = FakeRemnawaveApi.request

        async def report_not_blocked(self: FakeRemnawaveApi, method: str, path: str, **kwargs: Any) -> Any:
            if path == "/node-plugins/torrent-blocker" and method == "GET" and self.triggered and not self.reports:
                self.reports.append(_report(blocked=False))
                return {"records": copy.deepcopy(self.reports), "total": 1}
            return await original_request(self, method, path, **kwargs)

        monkeypatch.setattr(FakeRemnawaveApi, "request", report_not_blocked)
    else:
        monkeypatch.setattr(
            module,
            "_run_probe_command",
            lambda command, timeout_seconds: subprocess.CompletedProcess(command, 1, stdout=b"", stderr=b""),
        )

    with pytest.raises(module.SelfTestFailed):
        asyncio.run(module._run(_production_apply_args(module)))

    api = FakeRemnawaveApi.instances[0]
    restore_patches = [
        payload
        for method, path, payload in api.calls
        if (method, path) == ("PATCH", "/node-plugins") and payload["pluginConfig"] == api.original_config
    ]
    assert restore_patches, failure_mode


def test_main_outputs_sanitized_machine_readable_failure(
    module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    FakeRemnawaveApi.initial_profile = _profile_without_dedicated_rule()
    monkeypatch.setattr(
        module,
        "_run_probe_command",
        lambda command, timeout_seconds: subprocess.CompletedProcess(
            command,
            7,
            stdout=b"https://remnawave.example/api?token=secret customer@example.test",
            stderr=b"198.51.100.77 Bearer secret",
        ),
    )
    argv = [
        "--apply",
        "--synthetic-rule-tag",
        "TASK2_SYNTHETIC_SAFE_PROBE",
        "--node-uuid",
        "node-1",
        "--temporary-profile-rule",
        "--profile-inbound-tag",
        "TASK2_SYNTHETIC_INBOUND",
        "--target-nodes-json",
        json.dumps({"target": "specificNodes", "nodeUuids": ["node-1"]}),
        "--trigger-command-json",
        json.dumps(
            [
                str(module.TEST_TRIGGER_EXECUTABLE),
                "--target",
                "http://task2-synthetic.invalid",
            ]
        ),
        "--trigger-executable-sha256",
        module.TEST_TRIGGER_EXECUTABLE_SHA256,
        "--expected-user-uuid",
        "user-synthetic-1",
        "--expected-username",
        "task2-synthetic-user",
        "--expected-action-user-id",
        "2",
        "--expected-xray-user",
        "task2-tenant",
        "--expected-xray-tid",
        "task2-tenant",
        "--expected-source-ip",
        "198.51.100.77",
        "--expected-destination-ip",
        "10.0.0.5",
        "--expected-destination-port",
        "443",
        "--sync-timeout-seconds",
        "0.01",
        "--sync-poll-interval-seconds",
        "0",
        "--report-timeout-seconds",
        "0.01",
        "--report-poll-interval-seconds",
        "0",
        "--confirm-apply",
        module.APPLY_CONFIRMATION,
        "--confirm-no-live-traffic",
        module.NO_LIVE_TRAFFIC_CONFIRMATION,
        "--confirm-restore",
        module.RESTORE_CONFIRMATION,
    ]

    exit_code = module.main(argv)
    output = capsys.readouterr().out
    payload = json.loads(output)

    assert exit_code == 1
    assert payload["status"] == "failed"
    assert payload["failure"]["code"] == "trigger_failed"
    assert payload["cleanup"]["restore"]["status"] == "verified"
    forbidden = [
        "unit-test-remnawave-token",
        "https://remnawave.example",
        "customer@example.test",
        "198.51.100.77",
        "Bearer secret",
        "token=secret",
    ]
    assert not any(value in output for value in forbidden)
    assert payload["cleanup"]["unblock"] == {
        "status": "not_required",
        "reason": "no_valid_report_observed",
    }


def test_http_client_uses_trust_env_false_and_explicit_timeout() -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "trust_env=False" in source
    assert "httpx.Timeout(" in source
    assert "timeout=30.0" not in source
