from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from typing import Any

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from src import main as agent


class FakeProcess:
    def __init__(self) -> None:
        self.returncode: int | None = None
        self.terminated = False
        self.killed = False
        self.communicated = False

    def terminate(self) -> None:
        self.terminated = True
        self.returncode = -15

    def kill(self) -> None:
        self.killed = True
        self.returncode = -9

    async def wait(self) -> int:
        if self.returncode is None:
            self.returncode = 0
        return self.returncode

    async def communicate(self) -> tuple[bytes, bytes]:
        self.communicated = True
        return b"", b""


def _raw_profile(index: int) -> dict[str, Any]:
    return {
        "name": f"raw-{index}",
        "location": ["DE", "NL", "RU Moscow", "RU SPB"][index],
        "node": f"node-raw-{index}",
        "server": ["de-3.cyber-vpn.org", "nl-4.cyber-vpn.org", "ru-msk-3.cyber-vpn.org", "ru-spb-3.cyber-vpn.org"][
            index
        ],
        "port": 443,
        "network": "raw",
        "uuid": f"00000000-0000-4000-8000-{index + 1:012x}",
        "flow": "xtls-rprx-vision",
        "sni": "www.google.com",
        "public_key": f"RawPublicKey{index}Abc",
        "short_id": f"{index + 1:08x}",
        "fingerprint": "chrome",
    }


def _xhttp_profile(index: int) -> dict[str, Any]:
    return {
        "name": f"xhttp-{index}",
        "location": ["DE", "NL", "RU Moscow", "RU SPB"][index],
        "node": f"node-xhttp-{index}",
        "server": ["de-3.cyber-vpn.org", "nl-4.cyber-vpn.org", "ru-msk-3.cyber-vpn.org", "ru-spb-3.cyber-vpn.org"][
            index
        ],
        "port": 8443,
        "network": "xhttp",
        "uuid": f"00000000-0000-4000-8000-{index + 11:012x}",
        "sni": "www.google.com",
        "public_key": f"XhttpPublicKey{index}Abc",
        "short_id": f"{index + 11:08x}",
        "xhttp_path": f"/xhttp/{index}",
        "xhttp_mode": "auto",
        "fingerprint": "chrome",
    }


def test_transport_profile_rejects_unapproved_destination() -> None:
    profile = _raw_profile(0)
    profile["server"] = "127.0.0.1"

    with pytest.raises(ValidationError, match="vpn_target_not_allowed"):
        agent.RuntimeTransportProfile.model_validate(profile)


@pytest.mark.parametrize(
    "secret",
    [
        "short",
        "replace-before-live-vpn-test-agent",
        "example-secret-value",
        "placeholder-agent-secret-123456",
        "changeme-runtime-agent-secret",
        "local-runtime-agent-secret-value",
    ],
)
def test_settings_reject_placeholder_or_short_agent_secret(secret: str) -> None:
    with pytest.raises(ValidationError, match="vpn_test_agent_secret_must_be_non_placeholder"):
        agent.Settings(vpn_test_agent_secret=secret)


def test_proxy_connect_timeout_allows_slow_regional_reality_handshake_within_profile_budget() -> None:
    assert agent._proxy_connect_timeout_seconds(20.0) == 10.0
    assert agent._proxy_connect_timeout_seconds(5.0) == 5.0


def _profiles() -> list[dict[str, Any]]:
    return [_raw_profile(index) for index in range(4)] + [_xhttp_profile(index) for index in range(4)]


def _request(
    profiles: list[dict[str, Any]] | None = None,
    *,
    request_scope: str = "full",
) -> agent.RuntimeCheckRequest:
    return agent.RuntimeCheckRequest.model_validate(
        {
            "run_id": "run-1",
            "suite_key": "premium_smart_ru_v1",
            "mode": "runtime",
            "runtime_mode": "proxy-only",
            "request_scope": request_scope,
            "transport_profiles": profiles or [],
        }
    )


@pytest.fixture(autouse=True)
def _settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(agent.settings, "vpn_test_agent_secret", "agent-secret")
    monkeypatch.setattr(agent.settings, "vpn_test_agent_proxy_only_enabled", True)
    monkeypatch.setattr(agent.settings, "vpn_test_agent_tun_enabled", False)
    monkeypatch.setattr(agent.settings, "vpn_test_agent_profile_timeout_seconds", 5.0)
    monkeypatch.setattr(agent.settings, "vpn_test_agent_profile_max_attempts", 3)
    monkeypatch.setattr(agent.settings, "vpn_test_agent_profile_retry_backoff_seconds", 0.0)


def _install_success_boundaries(monkeypatch: pytest.MonkeyPatch) -> list[FakeProcess]:
    processes: list[FakeProcess] = []

    async def dns_ok(_server: str, _port: int, _timeout_seconds: float) -> bool:
        return True

    async def tcp_ok(_server: str, _port: int, _timeout_seconds: float) -> bool:
        return True

    async def start_ok(config_path: Path) -> FakeProcess:
        mode = await agent.asyncio.to_thread(lambda: stat.S_IMODE(config_path.stat().st_mode))
        if os.name != "nt":
            assert mode == 0o600
        else:
            assert mode & stat.S_IWUSR
        config = await agent.asyncio.to_thread(lambda: json.loads(config_path.read_text(encoding="utf-8")))
        assert config["inbounds"][0]["listen"] == "127.0.0.1"
        assert config["inbounds"][0]["protocol"] == "socks"
        assert config["outbounds"][0]["protocol"] == "vless"
        process = FakeProcess()
        processes.append(process)
        return process

    async def port_ready(_port: int, _timeout_seconds: float) -> bool:
        return True

    async def probe_ok(_socks_port: int, _timeout_seconds: float) -> tuple[bool, bool, str | None]:
        return True, True, None

    async def country_ok(_socks_port: int, _timeout_seconds: float) -> str:
        return "DE"

    monkeypatch.setattr(agent, "_resolve_dns", dns_ok)
    monkeypatch.setattr(agent, "_tcp_connect", tcp_ok)
    monkeypatch.setattr(agent, "_start_xray", start_ok)
    monkeypatch.setattr(agent, "_wait_for_local_port", port_ready)
    monkeypatch.setattr(agent, "_probe_https_generate_204", probe_ok)
    monkeypatch.setattr(agent, "_probe_exit_country", country_ok)
    return processes


@pytest.mark.asyncio
async def test_runtime_checks_auth_rejects_missing_secret() -> None:
    with pytest.raises(HTTPException) as exc:
        await agent.runtime_checks(_request(_profiles()), x_vpn_test_agent_secret=None)

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_missing_profile_matrix_fails_as_error_not_degraded() -> None:
    response = await agent.runtime_checks(_request([]), x_vpn_test_agent_secret="agent-secret")

    assert response["status"] == "fail"
    check = response["checks"][0]
    assert check["status"] == "fail"
    assert check["severity"] == "error"
    assert "degraded" not in json.dumps(response)
    assert check["details"]["request_scope"] == "full"
    assert check["details"]["actual_profile_count"] == 0


@pytest.mark.asyncio
async def test_success_runs_all_profiles_with_proxy_only_xray_and_safe_checks(monkeypatch: pytest.MonkeyPatch) -> None:
    processes = _install_success_boundaries(monkeypatch)

    response = await agent.runtime_checks(_request(_profiles()), x_vpn_test_agent_secret="agent-secret")

    assert response["status"] == "pass"
    matrix_check = next(
        check for check in response["checks"] if check["check_key"] == "runtime.transport_profile_matrix.required"
    )
    assert matrix_check["details"]["request_scope"] == "full"
    assert matrix_check["details"]["actual_profile_count"] == 8
    assert matrix_check["details"]["actual_raw_count"] == 4
    assert matrix_check["details"]["actual_xhttp_count"] == 4
    assert matrix_check["details"]["server_matrix_valid"] is True
    assert matrix_check["details"]["raw_server_matrix_valid"] is True
    assert matrix_check["details"]["xhttp_server_matrix_valid"] is True
    profile_checks = [
        check
        for check in response["checks"]
        if check["check_key"].startswith(("runtime.transport.raw.", "runtime.transport.xhttp."))
    ]
    assert len(profile_checks) == 8
    assert {check["details"]["transport"] for check in profile_checks} == {"raw", "xhttp"}
    assert all(check["details"]["dns_ok"] for check in profile_checks)
    assert all(check["details"]["tcp_connect_ok"] for check in profile_checks)
    assert all(check["details"]["proxy_handshake_ok"] for check in profile_checks)
    assert all(check["details"]["http_probe_ok"] for check in profile_checks)
    assert {check["details"]["attempt_count"] for check in profile_checks} == {1}
    assert {check["details"]["exit_country"] for check in profile_checks} == {"DE"}
    assert len(processes) == 8
    assert all(process.terminated for process in processes)
    assert all(process.communicated for process in processes)


@pytest.mark.asyncio
async def test_shard_scope_accepts_complete_location_pair(monkeypatch: pytest.MonkeyPatch) -> None:
    processes = _install_success_boundaries(monkeypatch)
    shard_profiles = [_raw_profile(0), _xhttp_profile(0)]

    response = await agent.runtime_checks(
        _request(shard_profiles, request_scope="shard"), x_vpn_test_agent_secret="agent-secret"
    )

    assert response["status"] == "pass"
    matrix_check = next(
        check for check in response["checks"] if check["check_key"] == "runtime.transport_profile_matrix.required"
    )
    assert matrix_check["details"]["request_scope"] == "shard"
    assert matrix_check["details"]["actual_profile_count"] == 2
    assert matrix_check["details"]["actual_raw_count"] == 1
    assert matrix_check["details"]["actual_xhttp_count"] == 1
    assert matrix_check["details"]["complete_pair_count"] == 1
    profile_checks = [
        check
        for check in response["checks"]
        if check["check_key"].startswith(("runtime.transport.raw.", "runtime.transport.xhttp."))
    ]
    assert len(profile_checks) == 2
    assert len(processes) == 2


@pytest.mark.asyncio
async def test_shard_scope_accepts_multiple_complete_location_pairs(monkeypatch: pytest.MonkeyPatch) -> None:
    processes = _install_success_boundaries(monkeypatch)
    shard_profiles = [_raw_profile(0), _raw_profile(1), _xhttp_profile(0), _xhttp_profile(1)]

    response = await agent.runtime_checks(
        _request(shard_profiles, request_scope="shard"), x_vpn_test_agent_secret="agent-secret"
    )

    assert response["status"] == "pass"
    matrix_check = next(
        check for check in response["checks"] if check["check_key"] == "runtime.transport_profile_matrix.required"
    )
    assert matrix_check["details"]["request_scope"] == "shard"
    assert matrix_check["details"]["actual_profile_count"] == 4
    assert matrix_check["details"]["actual_raw_count"] == 2
    assert matrix_check["details"]["actual_xhttp_count"] == 2
    assert matrix_check["details"]["complete_pair_count"] == 2
    assert len(processes) == 4


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("profiles", "expected_error"),
    [
        pytest.param([], "profile_matrix_empty", id="empty"),
        pytest.param([_raw_profile(0)], "profile_matrix_one_sided_location_pair", id="one-sided"),
        pytest.param(
            [_raw_profile(0), _xhttp_profile(0), _raw_profile(0)],
            "profile_matrix_duplicate_location_pair",
            id="duplicate",
        ),
        pytest.param(_profiles() + [_raw_profile(0), _xhttp_profile(0)], "profile_matrix_too_large", id="too-large"),
    ],
)
async def test_shard_scope_rejects_invalid_location_pairs(
    profiles: list[dict[str, Any]],
    expected_error: str,
) -> None:
    response = await agent.runtime_checks(
        _request(profiles, request_scope="shard"), x_vpn_test_agent_secret="agent-secret"
    )

    assert response["status"] == "fail"
    assert response["reason"] == "profile_matrix_invalid"
    check = response["checks"][0]
    assert check["status"] == "fail"
    assert check["severity"] == "error"
    assert check["details"]["request_scope"] == "shard"
    assert check["details"]["actual_profile_count"] == len(profiles)
    assert check["details"]["safe_error_class"] == expected_error


@pytest.mark.asyncio
async def test_full_scope_rejects_duplicate_servers_hidden_by_location_labels() -> None:
    profiles = _profiles()
    profiles[1]["server"] = profiles[0]["server"]
    profiles[5]["server"] = profiles[4]["server"]

    response = await agent.runtime_checks(_request(profiles), x_vpn_test_agent_secret="agent-secret")

    assert response["status"] == "fail"
    check = response["checks"][0]
    assert check["details"]["safe_error_class"] == "profile_matrix_server_mismatch"
    assert check["details"]["server_matrix_valid"] is False


@pytest.mark.asyncio
async def test_raw_transport_tcp_failure_is_mandatory_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_success_boundaries(monkeypatch)

    async def tcp_boundary(_server: str, port: int, _timeout_seconds: float) -> bool:
        return port != 443

    monkeypatch.setattr(agent, "_tcp_connect", tcp_boundary)

    response = await agent.runtime_checks(_request(_profiles()), x_vpn_test_agent_secret="agent-secret")

    raw_checks = [check for check in response["checks"] if check["check_key"].startswith("runtime.transport.raw.")]
    xhttp_checks = [check for check in response["checks"] if check["check_key"].startswith("runtime.transport.xhttp.")]
    assert response["status"] == "fail"
    assert {check["status"] for check in raw_checks} == {"fail"}
    assert {check["details"]["safe_error_class"] for check in raw_checks} == {"tcp_connect_failed"}
    assert {check["status"] for check in xhttp_checks} == {"pass"}


@pytest.mark.asyncio
async def test_xhttp_transport_tcp_failure_is_mandatory_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_success_boundaries(monkeypatch)

    async def tcp_boundary(_server: str, port: int, _timeout_seconds: float) -> bool:
        return port != 8443

    monkeypatch.setattr(agent, "_tcp_connect", tcp_boundary)

    response = await agent.runtime_checks(_request(_profiles()), x_vpn_test_agent_secret="agent-secret")

    raw_checks = [check for check in response["checks"] if check["check_key"].startswith("runtime.transport.raw.")]
    xhttp_checks = [check for check in response["checks"] if check["check_key"].startswith("runtime.transport.xhttp.")]
    assert response["status"] == "fail"
    assert {check["status"] for check in raw_checks} == {"pass"}
    assert {check["status"] for check in xhttp_checks} == {"fail"}
    assert {check["details"]["safe_error_class"] for check in xhttp_checks} == {"tcp_connect_failed"}


@pytest.mark.asyncio
async def test_profile_timeout_still_cleans_up_xray_process(monkeypatch: pytest.MonkeyPatch) -> None:
    processes = _install_success_boundaries(monkeypatch)
    monkeypatch.setattr(agent, "_profile_timeout_seconds", lambda: 0.05)

    async def slow_probe(_socks_port: int, _timeout_seconds: float) -> tuple[bool, bool, str | None]:
        await agent.asyncio.sleep(1)
        return True, True, None

    monkeypatch.setattr(agent, "_probe_https_generate_204", slow_probe)

    result = await agent._run_profile(agent.RuntimeTransportProfile.model_validate(_raw_profile(0)))

    assert result.safe_error_class == "timeout"
    assert result.http_probe_ok is False
    assert processes[0].terminated is True
    assert processes[0].communicated is True


@pytest.mark.asyncio
async def test_http_timeout_does_not_claim_proxy_handshake(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_success_boundaries(monkeypatch)

    async def probe_timeout(_socks_port: int, _timeout_seconds: float) -> tuple[bool, bool, str | None]:
        return False, False, "http_probe_timeout"

    monkeypatch.setattr(agent, "_probe_https_generate_204", probe_timeout)

    result = await agent._run_profile(agent.RuntimeTransportProfile.model_validate(_raw_profile(0)))

    assert result.proxy_handshake_ok is False
    assert result.http_probe_ok is False
    assert result.safe_error_class == "http_probe_timeout"


@pytest.mark.asyncio
async def test_profile_retry_passes_when_second_attempt_fully_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts: dict[str, int] = {}

    async def flaky_run(profile: agent.RuntimeTransportProfile) -> agent.ProfileProbeResult:
        attempts[profile.node] = attempts.get(profile.node, 0) + 1
        if attempts[profile.node] == 1:
            return agent.ProfileProbeResult(
                dns_ok=True,
                tcp_connect_ok=True,
                proxy_handshake_ok=False,
                http_probe_ok=False,
                safe_error_class="http_probe_timeout",
            )
        return agent.ProfileProbeResult(
            dns_ok=True,
            tcp_connect_ok=True,
            proxy_handshake_ok=True,
            http_probe_ok=True,
            exit_country="DE",
        )

    monkeypatch.setattr(agent, "_run_profile", flaky_run)

    response = await agent.runtime_checks(
        _request([_raw_profile(0), _xhttp_profile(0)], request_scope="shard"),
        x_vpn_test_agent_secret="agent-secret",
    )

    assert response["status"] == "pass"
    profile_checks = [
        check
        for check in response["checks"]
        if check["check_key"].startswith(("runtime.transport.raw.", "runtime.transport.xhttp."))
    ]
    assert len(profile_checks) == 2
    assert {check["details"]["attempt_count"] for check in profile_checks} == {2}
    assert {check["details"]["safe_error_class"] for check in profile_checks} == {None}


@pytest.mark.asyncio
async def test_profile_retry_does_not_mask_persistent_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts = 0

    async def failing_run(_profile: agent.RuntimeTransportProfile) -> agent.ProfileProbeResult:
        nonlocal attempts
        attempts += 1
        return agent.ProfileProbeResult(
            dns_ok=True,
            tcp_connect_ok=True,
            proxy_handshake_ok=False,
            http_probe_ok=False,
            safe_error_class="http_probe_timeout",
        )

    monkeypatch.setattr(agent, "_run_profile", failing_run)

    response = await agent.runtime_checks(
        _request([_raw_profile(0), _xhttp_profile(0)], request_scope="shard"),
        x_vpn_test_agent_secret="agent-secret",
    )

    assert response["status"] == "fail"
    profile_checks = [
        check
        for check in response["checks"]
        if check["check_key"].startswith(("runtime.transport.raw.", "runtime.transport.xhttp."))
    ]
    assert len(profile_checks) == 2
    assert attempts == 6
    assert {check["details"]["attempt_count"] for check in profile_checks} == {3}
    assert {check["details"]["safe_error_class"] for check in profile_checks} == {"http_probe_timeout"}


@pytest.mark.asyncio
async def test_response_redacts_profile_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_success_boundaries(monkeypatch)
    profiles = _profiles()

    response = await agent.runtime_checks(_request(profiles), x_vpn_test_agent_secret="agent-secret")
    serialized = json.dumps(response, ensure_ascii=False)

    for profile in profiles:
        assert profile["uuid"] not in serialized
        assert profile["public_key"] not in serialized
        assert profile["short_id"] not in serialized
        assert profile["sni"] not in serialized
        if profile.get("xhttp_path"):
            assert profile["xhttp_path"] not in serialized


@pytest.mark.asyncio
async def test_proxy_only_disabled_behavior_is_preserved(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(agent.settings, "vpn_test_agent_proxy_only_enabled", False)

    response = await agent.runtime_checks(_request(_profiles()), x_vpn_test_agent_secret="agent-secret")

    assert response["status"] == "degraded"
    assert response["reason"] == "proxy_only_disabled"
    assert response["checks"][0]["severity"] == "warning"


def test_profile_validation_blocks_injection_hosts_paths_and_hard_max() -> None:
    bad_host = _raw_profile(0)
    bad_host["server"] = "de-3.cyber-vpn.org;touch"
    with pytest.raises(ValidationError):
        agent.RuntimeTransportProfile.model_validate(bad_host)

    bad_path = _xhttp_profile(0)
    bad_path["xhttp_path"] = "not/absolute"
    with pytest.raises(ValidationError):
        agent.RuntimeTransportProfile.model_validate(bad_path)

    too_many = _profiles() + [_raw_profile(0) for _ in range(agent.HARD_MAX_PROFILE_COUNT)]
    with pytest.raises(ValidationError):
        _request(too_many)

    with pytest.raises(ValidationError):
        _request(_profiles(), request_scope="partial")

    invalid_extra = {
        "run_id": "run-1",
        "suite_key": "premium_smart_ru_v1",
        "mode": "runtime",
        "runtime_mode": "proxy-only",
        "request_scope": "full",
        "transport_profiles": _profiles(),
        "raw_subscription_url": "vless://secret",
    }
    with pytest.raises(ValidationError):
        agent.RuntimeCheckRequest.model_validate(invalid_extra)
