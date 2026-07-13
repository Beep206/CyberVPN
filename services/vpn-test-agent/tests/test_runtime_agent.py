from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
import stat
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from src import main as agent

ENDPOINTS = (
    ("de-relay.cyber-vpn.org", 2053, 2083),
    ("nl-4.cyber-vpn.org", 443, 8443),
    ("msk-relay.cyber-vpn.org", 2053, 2083),
    ("ru-spb-3.cyber-vpn.org", 443, 8443),
)
FIXED_NOW = 1_700_000_000
AGENT_AUTH_VALUE = "agent-secret"
LEGACY_AUTH_VALUE = "legacy-agent-secret"
VALID_V2_SECRET = "-".join(("alpha",) * 8)  # noqa: S105 - generated deterministic fixture.
VALID_LEGACY_SECRET = "-".join(("bravo",) * 8)  # noqa: S105 - generated deterministic fixture.


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
    server, raw_port, _ = ENDPOINTS[index]
    return {
        "name": f"raw-{index}",
        "location": ["DE", "NL", "RU Moscow", "RU SPB"][index],
        "node": f"node-raw-{index}",
        "server": server,
        "port": raw_port,
        "network": "raw",
        "uuid": f"00000000-0000-4000-8000-{index + 1:012x}",
        "flow": "xtls-rprx-vision",
        "sni": "www.google.com",
        "public_key": f"RawPublicKey{index}Abc",
        "short_id": f"{index + 1:08x}",
        "fingerprint": "chrome",
    }


def _xhttp_profile(index: int) -> dict[str, Any]:
    server, _, xhttp_port = ENDPOINTS[index]
    return {
        "name": f"xhttp-{index}",
        "location": ["DE", "NL", "RU Moscow", "RU SPB"][index],
        "node": f"node-xhttp-{index}",
        "server": server,
        "port": xhttp_port,
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
    monkeypatch.setattr(agent.settings, "vpn_test_agent_secret", AGENT_AUTH_VALUE)
    monkeypatch.setattr(agent.settings, "vpn_test_agent_role", "primary")
    monkeypatch.setattr(agent.settings, "vpn_test_agent_legacy_v1_enabled", False)
    monkeypatch.setattr(agent.settings, "vpn_test_agent_legacy_v1_secret", LEGACY_AUTH_VALUE)
    monkeypatch.setattr(agent.settings, "vpn_test_agent_proxy_only_enabled", True)
    monkeypatch.setattr(agent.settings, "vpn_test_agent_tun_enabled", False)
    monkeypatch.setattr(agent.settings, "vpn_test_agent_profile_timeout_seconds", 5.0)
    monkeypatch.setattr(agent.settings, "vpn_test_agent_profile_max_attempts", 3)
    monkeypatch.setattr(agent.settings, "vpn_test_agent_profile_retry_backoff_seconds", 0.0)
    monkeypatch.setattr(agent.settings, "vpn_test_agent_signature_max_skew_seconds", 60)
    monkeypatch.setattr(agent, "_current_unix_seconds", lambda: FIXED_NOW)
    agent._request_replay_cache.clear()
    agent._runtime_check_capacity.clear()


def _request_body(payload: dict[str, Any] | None = None) -> bytes:
    raw_payload = payload or _request([]).model_dump(by_alias=True)
    return json.dumps(raw_payload, separators=(",", ":")).encode("utf-8")


def _signing_headers(
    body: bytes,
    *,
    secret: str = AGENT_AUTH_VALUE,
    timestamp: int = FIXED_NOW,
    nonce: str = "0123456789abcdef0123456789abcdef",
    audience: str = "primary",
) -> dict[str, str]:
    body_sha256 = hashlib.sha256(body).hexdigest()
    signature = hmac.new(
        secret.encode("utf-8"),
        (
            f"v2\n{agent.SIGNED_RUNTIME_METHOD}\n{agent.SIGNED_RUNTIME_PATH}\n\n"
            f"{agent.SIGNED_RUNTIME_CONTENT_TYPE}\n{timestamp}\n{nonce}\n{audience}\n{body_sha256}"
        ).encode("ascii"),
        hashlib.sha256,
    ).hexdigest()
    return {
        "Content-Type": agent.SIGNED_RUNTIME_CONTENT_TYPE,
        agent.REQUEST_TIMESTAMP_HEADER: str(timestamp),
        agent.REQUEST_NONCE_HEADER: nonce,
        agent.REQUEST_AUDIENCE_HEADER: audience,
        agent.REQUEST_BODY_SHA256_HEADER: body_sha256,
        agent.REQUEST_SIGNATURE_HEADER: signature,
    }


def _response_signature(
    secret: str, status_code: int, timestamp: str, nonce: str, audience: str, body_sha256: str
) -> str:
    return hmac.new(
        secret.encode("utf-8"),
        (
            f"v2-response\n{agent.SIGNED_RUNTIME_METHOD}\n{agent.SIGNED_RUNTIME_PATH}\n{status_code}\n"
            f"{agent.SIGNED_RUNTIME_CONTENT_TYPE}\n{timestamp}\n{nonce}\n{audience}\n{body_sha256}"
        ).encode("ascii"),
        hashlib.sha256,
    ).hexdigest()


async def _post_runtime_check(body: bytes, headers: dict[str, str] | list[tuple[str, str]]) -> httpx.Response:
    transport = httpx.ASGITransport(app=agent.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        return await client.post(agent.SIGNED_RUNTIME_PATH, content=body, headers=headers)


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
async def test_legacy_runtime_checks_auth_rejects_missing_secret() -> None:
    with pytest.raises(HTTPException) as exc:
        agent._require_legacy_secret(None)

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_health_exposes_role_and_legacy_rollout_state_without_secrets() -> None:
    response = await agent.health()

    assert response["agent_role"] == "primary"
    assert response["legacy_v1_enabled"] is False
    assert AGENT_AUTH_VALUE not in json.dumps(response)
    assert LEGACY_AUTH_VALUE not in json.dumps(response)


@pytest.mark.parametrize(
    ("v2_secret", "legacy_secret"),
    [
        ("", VALID_LEGACY_SECRET),
        (VALID_V2_SECRET, ""),
        (VALID_V2_SECRET, VALID_V2_SECRET),
    ],
)
def test_legacy_runtime_settings_require_distinct_rollout_secrets(v2_secret: str, legacy_secret: str) -> None:
    with pytest.raises(ValidationError):
        agent.Settings(
            vpn_test_agent_secret=v2_secret,
            vpn_test_agent_legacy_v1_enabled=True,
            vpn_test_agent_legacy_v1_secret=legacy_secret,
        )


@pytest.mark.asyncio
async def test_legacy_runtime_checks_remains_compatible_during_agent_first_rollout() -> None:
    agent.settings.vpn_test_agent_legacy_v1_enabled = True
    transport = httpx.ASGITransport(app=agent.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/internal/v1/runtime-checks",
            json=_request([]).model_dump(by_alias=True),
            headers={agent.REQUEST_SECRET_HEADER: f" {LEGACY_AUTH_VALUE} "},
        )

    assert response.status_code == 200
    assert response.json()["reason"] == "profile_matrix_invalid"
    assert agent.RESPONSE_SIGNATURE_HEADER not in response.headers


@pytest.mark.asyncio
async def test_legacy_runtime_checks_is_disabled_by_default() -> None:
    transport = httpx.ASGITransport(app=agent.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/internal/v1/runtime-checks", content=b"{")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_legacy_runtime_checks_uses_body_and_concurrency_bounds(monkeypatch: pytest.MonkeyPatch) -> None:
    agent.settings.vpn_test_agent_legacy_v1_enabled = True
    both_started = asyncio.Event()
    release = asyncio.Event()
    active = 0
    peak_active = 0

    async def blocking_runtime_checks(_payload: agent.RuntimeCheckRequest) -> dict[str, Any]:
        nonlocal active, peak_active
        active += 1
        peak_active = max(peak_active, active)
        if active == agent.MAX_CONCURRENT_RUNTIME_CHECKS:
            both_started.set()
        try:
            await release.wait()
            return {"status": "pass", "agent_id": agent.settings.vpn_test_agent_id, "checks": [{"status": "pass"}]}
        finally:
            active -= 1

    monkeypatch.setattr(agent, "_run_runtime_checks", blocking_runtime_checks)
    body = _request_body()
    headers = {agent.REQUEST_SECRET_HEADER: LEGACY_AUTH_VALUE, "Content-Type": "application/json"}
    transport = httpx.ASGITransport(app=agent.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        first = asyncio.create_task(client.post("/internal/v1/runtime-checks", content=body, headers=headers))
        second = asyncio.create_task(client.post("/internal/v1/runtime-checks", content=body, headers=headers))
        await asyncio.wait_for(both_started.wait(), timeout=1)
        saturated = await client.post("/internal/v1/runtime-checks", content=body, headers=headers)
        oversized = await client.post(
            "/internal/v1/runtime-checks",
            content=b"x" * (agent.MAX_REQUEST_BODY_BYTES + 1),
            headers=headers,
        )
        release.set()
        completed = await asyncio.gather(first, second)

    assert [response.status_code for response in completed] == [200, 200]
    assert saturated.status_code == 429
    assert oversized.status_code == 413
    assert peak_active == agent.MAX_CONCURRENT_RUNTIME_CHECKS


@pytest.mark.asyncio
async def test_signed_protocol_accepts_valid_request_and_signs_exact_response() -> None:
    body = _request_body()
    nonce = "11111111111111111111111111111111"
    headers = _signing_headers(body, nonce=nonce)

    response = await _post_runtime_check(body, headers)

    assert response.status_code == 200
    assert agent.REQUEST_SECRET_HEADER not in headers
    assert response.headers[agent.RESPONSE_TIMESTAMP_HEADER] == str(FIXED_NOW)
    assert response.headers[agent.RESPONSE_NONCE_HEADER] == nonce
    assert response.headers[agent.RESPONSE_AUDIENCE_HEADER] == "primary"
    response_body_hash = hashlib.sha256(response.content).hexdigest()
    assert response.headers[agent.RESPONSE_BODY_SHA256_HEADER] == response_body_hash
    assert response.headers[agent.RESPONSE_SIGNATURE_HEADER] == _response_signature(
        AGENT_AUTH_VALUE,
        response.status_code,
        str(FIXED_NOW),
        nonce,
        "primary",
        response_body_hash,
    )
    assert response.json()["status"] == "fail"
    assert response.json()["reason"] == "profile_matrix_invalid"


@pytest.mark.asyncio
async def test_signed_protocol_rejects_replayed_nonce() -> None:
    body = _request_body()
    headers = _signing_headers(body, nonce="22222222222222222222222222222222")

    first_response = await _post_runtime_check(body, headers)
    second_response = await _post_runtime_check(body, headers)

    assert first_response.status_code == 200
    assert second_response.status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize("timestamp", [FIXED_NOW - 61, FIXED_NOW + 61])
async def test_signed_protocol_rejects_stale_and_future_timestamps(timestamp: int) -> None:
    body = _request_body()

    response = await _post_runtime_check(body, _signing_headers(body, timestamp=timestamp))

    assert response.status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mutate_headers",
    [
        pytest.param(
            lambda headers: {key: value for key, value in headers.items() if key != agent.REQUEST_AUDIENCE_HEADER},
            id="missing-audience",
        ),
        pytest.param(
            lambda headers: {**headers, agent.REQUEST_TIMESTAMP_HEADER: "01700000000"}, id="noncanonical-timestamp"
        ),
        pytest.param(
            lambda headers: {**headers, agent.REQUEST_NONCE_HEADER: "ABCDEFabcdef0123456789abcdef0123"},
            id="noncanonical-nonce",
        ),
        pytest.param(
            lambda headers: {**headers, agent.REQUEST_AUDIENCE_HEADER: "spb"},
            id="wrong-audience",
        ),
        pytest.param(
            lambda headers: {**headers, "Content-Type": "text/plain"},
            id="wrong-content-type",
        ),
        pytest.param(
            lambda headers: {
                **headers,
                agent.REQUEST_BODY_SHA256_HEADER: headers[agent.REQUEST_BODY_SHA256_HEADER].upper(),
            },
            id="noncanonical-body-hash",
        ),
        pytest.param(
            lambda headers: {
                **headers,
                agent.REQUEST_SIGNATURE_HEADER: headers[agent.REQUEST_SIGNATURE_HEADER].upper(),
            },
            id="noncanonical-signature",
        ),
    ],
)
async def test_signed_protocol_rejects_malformed_or_noncanonical_headers(mutate_headers: Any) -> None:
    body = _request_body()
    headers = mutate_headers(_signing_headers(body, nonce="33333333333333333333333333333333"))

    response = await _post_runtime_check(body, headers)

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_signed_protocol_rejects_duplicate_headers() -> None:
    body = _request_body()
    headers = list(_signing_headers(body, nonce="44444444444444444444444444444444").items())
    headers.append((agent.REQUEST_NONCE_HEADER, "55555555555555555555555555555555"))

    response = await _post_runtime_check(body, headers)

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_signed_protocol_rejects_tampered_body_before_pydantic_processing() -> None:
    body = _request_body()
    tampered_body = b'{"raw_subscription_url":"vless://secret"}'

    response = await _post_runtime_check(
        tampered_body, _signing_headers(body, nonce="66666666666666666666666666666666")
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_signed_protocol_rejects_wrong_signature() -> None:
    body = _request_body()
    headers = _signing_headers(body, nonce="77777777777777777777777777777777")
    headers[agent.REQUEST_SIGNATURE_HEADER] = "0" * 64

    response = await _post_runtime_check(body, headers)

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_signed_protocol_rejects_oversized_body_before_authentication() -> None:
    body = b"x" * (agent.MAX_REQUEST_BODY_BYTES + 1)

    response = await _post_runtime_check(body, _signing_headers(body, nonce="88888888888888888888888888888888"))

    assert response.status_code == 413


@pytest.mark.asyncio
async def test_signed_protocol_bounds_concurrent_runtime_checks(monkeypatch: pytest.MonkeyPatch) -> None:
    both_started = asyncio.Event()
    release = asyncio.Event()
    active = 0
    peak_active = 0

    async def blocking_runtime_checks(_payload: agent.RuntimeCheckRequest) -> dict[str, Any]:
        nonlocal active, peak_active
        active += 1
        peak_active = max(peak_active, active)
        if active == agent.MAX_CONCURRENT_RUNTIME_CHECKS:
            both_started.set()
        try:
            await release.wait()
            return {"status": "pass", "agent_id": agent.settings.vpn_test_agent_id, "checks": [{"status": "pass"}]}
        finally:
            active -= 1

    monkeypatch.setattr(agent, "_run_runtime_checks", blocking_runtime_checks)
    body = _request_body()
    first = asyncio.create_task(
        _post_runtime_check(body, _signing_headers(body, nonce="90000000000000000000000000000001"))
    )
    second = asyncio.create_task(
        _post_runtime_check(body, _signing_headers(body, nonce="90000000000000000000000000000002"))
    )
    await asyncio.wait_for(both_started.wait(), timeout=1)

    saturated = await _post_runtime_check(body, _signing_headers(body, nonce="90000000000000000000000000000003"))
    release.set()
    completed = await asyncio.gather(first, second)

    assert [response.status_code for response in completed] == [200, 200]
    assert saturated.status_code == 429
    saturated_body_hash = hashlib.sha256(saturated.content).hexdigest()
    assert saturated.headers[agent.RESPONSE_SIGNATURE_HEADER] == _response_signature(
        AGENT_AUTH_VALUE,
        429,
        str(FIXED_NOW),
        "90000000000000000000000000000003",
        "primary",
        saturated_body_hash,
    )
    assert peak_active == agent.MAX_CONCURRENT_RUNTIME_CHECKS


@pytest.mark.asyncio
async def test_missing_profile_matrix_fails_as_error_not_degraded() -> None:
    response = await agent._run_runtime_checks(_request([]))

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

    response = await agent._run_runtime_checks(_request(_profiles()))

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
    assert {check["check_key"] for check in profile_checks} == {
        f"runtime.transport.{transport}.{location}"
        for transport in ("raw", "xhttp")
        for location in ("de", "nl", "moscow", "spb")
    }
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

    response = await agent._run_runtime_checks(_request(shard_profiles, request_scope="shard"))

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

    response = await agent._run_runtime_checks(_request(shard_profiles, request_scope="shard"))

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
    response = await agent._run_runtime_checks(_request(profiles, request_scope="shard"))

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
    profiles[1]["port"] = profiles[0]["port"]
    profiles[5]["server"] = profiles[4]["server"]
    profiles[5]["port"] = profiles[4]["port"]

    response = await agent._run_runtime_checks(_request(profiles))

    assert response["status"] == "fail"
    check = response["checks"][0]
    assert check["details"]["safe_error_class"] == "profile_matrix_server_mismatch"
    assert check["details"]["server_matrix_valid"] is False


@pytest.mark.asyncio
async def test_raw_transport_tcp_failure_is_mandatory_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_success_boundaries(monkeypatch)

    async def tcp_boundary(_server: str, port: int, _timeout_seconds: float) -> bool:
        return port not in {443, 2053}

    monkeypatch.setattr(agent, "_tcp_connect", tcp_boundary)

    response = await agent._run_runtime_checks(_request(_profiles()))

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
        return port not in {8443, 2083}

    monkeypatch.setattr(agent, "_tcp_connect", tcp_boundary)

    response = await agent._run_runtime_checks(_request(_profiles()))

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

    response = await agent._run_runtime_checks(_request([_raw_profile(0), _xhttp_profile(0)], request_scope="shard"))

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

    response = await agent._run_runtime_checks(_request([_raw_profile(0), _xhttp_profile(0)], request_scope="shard"))

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

    response = await agent._run_runtime_checks(_request(profiles))
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

    response = await agent._run_runtime_checks(_request(_profiles()))

    assert response["status"] == "degraded"
    assert response["reason"] == "proxy_only_disabled"
    assert response["checks"][0]["severity"] == "warning"


def test_profile_validation_blocks_injection_hosts_paths_and_hard_max() -> None:
    bad_host = _raw_profile(0)
    bad_host["server"] = "de-relay.cyber-vpn.org;touch"
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
