from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import httpx
import pytest
from pydantic import SecretStr

from src.application.vpn_testing import runtime_agent_client as client
from src.application.vpn_testing import service as service_module
from src.config.settings import Settings, settings

_LOCATIONS = (
    ("DE Frankfurt", "de-relay.cyber-vpn.org", 2053, 2083),
    ("NL Amsterdam", "nl-4.cyber-vpn.org", 443, 8443),
    ("RU Moscow", "msk-relay.cyber-vpn.org", 2053, 2083),
    ("RU SPB", "ru-spb-3.cyber-vpn.org", 443, 8443),
)


def _raw_proxy(index: int) -> dict[str, Any]:
    location, server, raw_port, _ = _LOCATIONS[index]
    return {
        "name": f"{location} RAW {index + 1}",
        "type": "vless",
        "server": server,
        "port": raw_port,
        "network": "tcp",
        "uuid": f"00000000-0000-4000-8000-{index + 1:012x}",
        "flow": "xtls-rprx-vision",
        "servername": "www.microsoft.com",
        "client-fingerprint": "chrome",
        "reality-opts": {
            "public-key": f"RawPublicKey{index}Abc",
            "short-id": f"{index + 1:08x}",
        },
    }


def _xhttp_proxy(index: int) -> dict[str, Any]:
    location, server, _, xhttp_port = _LOCATIONS[index]
    return {
        "name": f"{location} XHTTP {index + 1}",
        "type": "vless",
        "server": server,
        "port": xhttp_port,
        "network": "xhttp",
        "uuid": f"00000000-0000-4000-8000-{index + 11:012x}",
        "servername": "www.microsoft.com",
        "client-fingerprint": "chrome",
        "reality-opts": {
            "public-key": f"XhttpPublicKey{index}Abc",
            "short-id": f"{index + 11:08x}",
        },
        "xhttp-opts": {"path": f"/xhttp/{index}", "mode": "auto"},
    }


def _generated_mihomo() -> dict[str, Any]:
    return {"proxies": [_raw_proxy(index) for index in range(4)] + [_xhttp_proxy(index) for index in range(4)]}


def _profiles_from_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    profiles = payload["transport_profiles"]
    assert isinstance(profiles, list)
    return profiles


def _transport_counts(profiles: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "raw": sum(1 for profile in profiles if profile["network"] == "raw"),
        "xhttp": sum(1 for profile in profiles if profile["network"] == "xhttp"),
    }


class FakeResponse:
    def __init__(self, data: Any) -> None:
        self._data = data

    def raise_for_status(self) -> None:
        return None

    def json(self) -> Any:
        return self._data


ResponseFactory = Callable[[dict[str, Any]], Any]


class FakeAsyncClient:
    requests: list[dict[str, Any]] = []
    responses_by_base_url: dict[str, Any | ResponseFactory] = {}
    failures_by_base_url: dict[str, Exception] = {}

    def __init__(self, *, base_url: str, timeout: Any, trust_env: bool) -> None:
        self.base_url = base_url
        self.timeout = timeout
        self.trust_env = trust_env

    async def __aenter__(self) -> FakeAsyncClient:
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    async def post(self, path: str, *, json: dict[str, Any], headers: dict[str, str]) -> FakeResponse:
        request = {
            "base_url": self.base_url,
            "path": path,
            "json": json,
            "headers": headers,
            "trust_env": self.trust_env,
        }
        self.__class__.requests.append(request)
        failure = self.__class__.failures_by_base_url.get(self.base_url)
        if failure is not None:
            raise failure
        response = self.__class__.responses_by_base_url.get(self.base_url)
        if callable(response):
            return FakeResponse(response(request))
        if response is not None:
            return FakeResponse(response)
        return FakeResponse(_default_response(request))

    @classmethod
    def reset(cls) -> None:
        cls.requests = []
        cls.responses_by_base_url = {}
        cls.failures_by_base_url = {}


def _default_response(request: dict[str, Any]) -> dict[str, Any]:
    payload = request["json"]
    secret = request["headers"][client.RUNTIME_AGENT_AUTH_HEADER]
    checks = [
        {
            "check_key": "runtime.transport_profile_matrix.required",
            "check_name": "Runtime transport profile matrix",
            "category": "runtime",
            "status": "pass",
            "severity": "error",
            "target": "global",
            "safe_summary": "Shard matrix passed",
            "details": {"request_scope": payload["request_scope"]},
            "duration_ms": 0,
        }
    ]
    for profile in _profiles_from_payload(payload):
        location_key = client.PREMIUM_SMART_RU_RELEASE_LOCATION_KEY_BY_SERVER[profile["server"]]
        checks.append(
            {
                "check_key": f"runtime.transport.{profile['network']}.{location_key}",
                "check_name": "Runtime concrete transport profile",
                "category": "runtime",
                "status": "pass",
                "severity": "error",
                "target": profile["server"],
                "safe_summary": f"must redact {secret} {profile['uuid']} {profile['public_key']}",
                "details": {
                    "uuid": profile["uuid"],
                    "public_key": profile["public_key"],
                    "short_id": profile["short_id"],
                    "secret": secret,
                    "safe_error_class": None,
                },
                "duration_ms": 1,
            }
        )
    return {
        "status": "pass",
        "agent_id": f"{request['base_url'].removeprefix('https://')}-agent",
        "checks": checks,
    }


def _configure_primary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "vpn_test_agent_url", "https://primary-agent.internal")
    monkeypatch.setattr(settings, "vpn_test_agent_secret", SecretStr("primary-agent-secret"))
    monkeypatch.setattr(settings, "vpn_test_agent_moscow_url", "")
    monkeypatch.setattr(settings, "vpn_test_agent_moscow_secret", None)
    monkeypatch.setattr(settings, "vpn_test_agent_spb_url", "")
    monkeypatch.setattr(settings, "vpn_test_agent_spb_secret", None)
    monkeypatch.setattr(settings, "vpn_test_agent_timeout_seconds", 20)
    monkeypatch.setattr(client.httpx, "AsyncClient", FakeAsyncClient)
    FakeAsyncClient.reset()


def _configure_moscow_target(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "vpn_test_agent_moscow_url", "https://moscow-target-agent.internal")
    monkeypatch.setattr(settings, "vpn_test_agent_moscow_secret", SecretStr("moscow-target-secret"))


def _configure_spb_target(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "vpn_test_agent_spb_url", "https://spb-target-agent.internal")
    monkeypatch.setattr(settings, "vpn_test_agent_spb_secret", SecretStr("spb-target-secret"))


def _request_by_url() -> dict[str, dict[str, Any]]:
    return {request["base_url"]: request for request in FakeAsyncClient.requests}


def _assert_no_sensitive_values(result: dict[str, Any], requests: list[dict[str, Any]]) -> None:
    serialized = json.dumps(result)
    for secret in ("primary-agent-secret", "moscow-target-secret", "spb-target-secret"):
        assert secret not in serialized
    for request in requests:
        for profile in _profiles_from_payload(request["json"]):
            assert profile["uuid"] not in serialized
            assert profile["public_key"] not in serialized
            assert profile["short_id"] not in serialized


def test_settings_accept_optional_regional_agent_targets() -> None:
    configured = Settings(
        environment="development",
        jwt_secret=SecretStr("xVanw-qakEZA0v_T5mJ9GSCJkTzoWYpHMJDX02lFg-B8"),
        remnawave_token=SecretStr("valid_token_for_testing_purposes_32characters"),
        cryptobot_token=SecretStr("valid_token_for_testing_purposes_32characters"),
        vpn_test_agent_moscow_url="https://moscow-target-agent.internal",
        vpn_test_agent_moscow_secret=SecretStr("moscow-target-secret"),
        vpn_test_agent_spb_url="https://spb-target-agent.internal",
        vpn_test_agent_spb_secret=SecretStr("spb-target-secret"),
    )

    assert configured.vpn_test_agent_moscow_url == "https://moscow-target-agent.internal"
    assert configured.vpn_test_agent_moscow_secret is not None
    assert configured.vpn_test_agent_moscow_secret.get_secret_value() == "moscow-target-secret"
    assert configured.vpn_test_agent_spb_url == "https://spb-target-agent.internal"
    assert configured.vpn_test_agent_spb_secret is not None
    assert configured.vpn_test_agent_spb_secret.get_secret_value() == "spb-target-secret"


@pytest.mark.asyncio
async def test_call_runtime_agent_derives_payload_from_generated_mihomo_and_redacts_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_primary(monkeypatch)
    monkeypatch.setenv("HTTPS_PROXY", "http://untrusted-proxy.invalid:8080")
    monkeypatch.setenv("ALL_PROXY", "socks5://untrusted-proxy.invalid:1080")

    result = await client.call_runtime_agent(
        run_id="run-1",
        suite_key="premium_smart_ru_v1",
        mode="runtime",
        route_entries=[],
        generated_mihomo_artifact=_generated_mihomo(),
    )

    assert len(FakeAsyncClient.requests) == 1
    request = FakeAsyncClient.requests[0]
    payload = request["json"]
    profiles = _profiles_from_payload(payload)
    assert request["base_url"] == "https://primary-agent.internal"
    assert request["path"] == client.RUNTIME_AGENT_ENDPOINT
    assert request["trust_env"] is False
    assert request["headers"] == {client.RUNTIME_AGENT_AUTH_HEADER: "primary-agent-secret"}
    assert payload["runtime_mode"] == "proxy-only"
    assert payload["request_scope"] == "full"
    assert len(profiles) == client.EXPECTED_RUNTIME_PROFILE_COUNT
    assert _transport_counts(profiles) == {"raw": 4, "xhttp": 4}
    assert {"uuid", "public_key", "short_id", "sni"}.issubset(profiles[0])
    assert profiles[4]["xhttp_path"] == "/xhttp/0"
    assert profiles[4]["xhttp_mode"] == "auto"
    assert all(not item["check_key"].startswith("runtime.agent.primary.") for item in result["checks"])
    profile_check = next(
        check
        for check in result["checks"]
        if check["check_key"].startswith(("runtime.transport.raw.", "runtime.transport.xhttp."))
    )
    assert profile_check["details"]["uuid"] == "<redacted>"
    assert "<redacted>" in profile_check["safe_summary"]
    _assert_no_sensitive_values(result, FakeAsyncClient.requests)


@pytest.mark.asyncio
async def test_call_runtime_agent_splits_moscow_and_spb_targets_and_combines_unique_checks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_primary(monkeypatch)
    _configure_moscow_target(monkeypatch)
    _configure_spb_target(monkeypatch)

    result = await client.call_runtime_agent(
        run_id="run-1",
        suite_key="premium_smart_ru_v1",
        mode="runtime",
        route_entries=[],
        generated_mihomo_artifact=_generated_mihomo(),
    )

    by_url = _request_by_url()
    assert set(by_url) == {
        "https://primary-agent.internal",
        "https://moscow-target-agent.internal",
        "https://spb-target-agent.internal",
    }
    primary_profiles = _profiles_from_payload(by_url["https://primary-agent.internal"]["json"])
    moscow_profiles = _profiles_from_payload(by_url["https://moscow-target-agent.internal"]["json"])
    spb_profiles = _profiles_from_payload(by_url["https://spb-target-agent.internal"]["json"])
    assert {profile["location"] for profile in primary_profiles} == {"DE", "NL"}
    assert {profile["location"] for profile in moscow_profiles} == {"RU Moscow"}
    assert {profile["location"] for profile in spb_profiles} == {"RU SPB"}
    assert len(primary_profiles) == 4
    assert len(moscow_profiles) == client.EXPECTED_REGIONAL_TARGET_PROFILE_COUNT
    assert len(spb_profiles) == client.EXPECTED_REGIONAL_TARGET_PROFILE_COUNT
    assert by_url["https://primary-agent.internal"]["json"]["request_scope"] == "shard"
    assert by_url["https://moscow-target-agent.internal"]["json"]["request_scope"] == "shard"
    assert by_url["https://spb-target-agent.internal"]["json"]["request_scope"] == "shard"
    assert _transport_counts(moscow_profiles) == {"raw": 1, "xhttp": 1}
    assert _transport_counts(spb_profiles) == {"raw": 1, "xhttp": 1}
    assert by_url["https://primary-agent.internal"]["headers"] == {
        client.RUNTIME_AGENT_AUTH_HEADER: "primary-agent-secret"
    }
    assert by_url["https://moscow-target-agent.internal"]["headers"] == {
        client.RUNTIME_AGENT_AUTH_HEADER: "moscow-target-secret"
    }
    assert by_url["https://spb-target-agent.internal"]["headers"] == {
        client.RUNTIME_AGENT_AUTH_HEADER: "spb-target-secret"
    }
    check_keys = [item["check_key"] for item in result["checks"]]
    assert len(check_keys) == len(set(check_keys))
    assert {key for key in check_keys if key.startswith(("runtime.transport.raw.", "runtime.transport.xhttp."))} == {
        f"runtime.transport.{transport}.{location}"
        for transport in ("raw", "xhttp")
        for location in ("de", "nl", "moscow", "spb")
    }
    assert "runtime.transport_profile_matrix.required" in check_keys
    assert (
        service_module.PREMIUM_SMART_RU_RELEASE_GATE_RUNTIME_RAW_CHECKS
        | service_module.PREMIUM_SMART_RU_RELEASE_GATE_RUNTIME_XHTTP_CHECKS
    ).issubset(check_keys)
    assert check_keys.count(service_module.PREMIUM_SMART_RU_RELEASE_GATE_RUNTIME_MATRIX_CHECK) == 1
    assert any(key.startswith("runtime.agent.primary.runtime.transport_profile_matrix") for key in check_keys)
    assert any(key.startswith("runtime.agent.moscow.runtime.transport_profile_matrix") for key in check_keys)
    assert any(key.startswith("runtime.agent.spb.runtime.transport_profile_matrix") for key in check_keys)
    assert result["status"] == "pass"
    _assert_no_sensitive_values(result, FakeAsyncClient.requests)


@pytest.mark.asyncio
async def test_call_runtime_agent_leaves_unconfigured_regional_target_on_primary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_primary(monkeypatch)
    _configure_moscow_target(monkeypatch)

    result = await client.call_runtime_agent(
        run_id="run-1",
        suite_key="premium_smart_ru_v1",
        mode="runtime",
        route_entries=[],
        generated_mihomo_artifact=_generated_mihomo(),
    )

    by_url = _request_by_url()
    assert set(by_url) == {"https://primary-agent.internal", "https://moscow-target-agent.internal"}
    primary_profiles = _profiles_from_payload(by_url["https://primary-agent.internal"]["json"])
    moscow_profiles = _profiles_from_payload(by_url["https://moscow-target-agent.internal"]["json"])
    assert {profile["location"] for profile in moscow_profiles} == {"RU Moscow"}
    assert {profile["location"] for profile in primary_profiles} == {"DE", "NL", "RU SPB"}
    assert len(primary_profiles) == 6
    assert by_url["https://primary-agent.internal"]["json"]["request_scope"] == "shard"
    assert by_url["https://moscow-target-agent.internal"]["json"]["request_scope"] == "shard"
    assert result["status"] == "pass"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("url_attr", "secret_attr", "reason"),
    [
        ("vpn_test_agent_moscow_url", "vpn_test_agent_moscow_secret", "moscow_agent_partially_configured"),
        ("vpn_test_agent_spb_url", "vpn_test_agent_spb_secret", "spb_agent_partially_configured"),
    ],
)
async def test_call_runtime_agent_fails_closed_for_partial_regional_target_config(
    monkeypatch: pytest.MonkeyPatch,
    url_attr: str,
    secret_attr: str,
    reason: str,
) -> None:
    _configure_primary(monkeypatch)
    monkeypatch.setattr(settings, url_attr, "https://regional-agent.internal")
    monkeypatch.setattr(settings, secret_attr, None)

    result = await client.call_runtime_agent(
        run_id="run-1",
        suite_key="premium_smart_ru_v1",
        mode="runtime",
        route_entries=[],
        generated_mihomo_artifact=_generated_mihomo(),
    )

    assert result["status"] == "fail"
    assert result["reason"] == reason
    assert FakeAsyncClient.requests == []
    assert "regional-agent.internal" not in json.dumps(result)


@pytest.mark.asyncio
async def test_call_runtime_agent_rejects_matrix_without_four_per_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    _configure_primary(monkeypatch)
    raw_profiles = [
        profile
        for profile in client.runtime_profiles_from_generated_mihomo(_generated_mihomo())
        if profile.transport == "raw"
    ]

    result = await client.call_runtime_agent(
        run_id="run-1",
        suite_key="premium_smart_ru_v1",
        mode="runtime",
        route_entries=[],
        transport_profiles=raw_profiles * 2,
    )

    assert result["status"] == "fail"
    assert result["reason"] == "profile_matrix_transport_count_invalid"
    assert result["checks"][0]["details"]["actual_raw_profile_count"] == 8
    assert result["checks"][0]["details"]["actual_xhttp_profile_count"] == 0
    assert FakeAsyncClient.requests == []


@pytest.mark.asyncio
async def test_call_runtime_agent_rejects_duplicate_compensated_server_matrix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_primary(monkeypatch)
    artifact = _generated_mihomo()
    artifact["proxies"][3]["server"] = "de-relay.cyber-vpn.org"
    artifact["proxies"][3]["port"] = 2053

    result = await client.call_runtime_agent(
        run_id="run-1",
        suite_key="premium_smart_ru_v1",
        mode="runtime",
        route_entries=[],
        generated_mihomo_artifact=artifact,
    )

    assert result["status"] == "fail"
    assert result["reason"] == "profile_matrix_server_set_invalid"
    assert FakeAsyncClient.requests == []


def test_generated_runtime_profiles_reject_unapproved_destination() -> None:
    artifact = _generated_mihomo()
    artifact["proxies"][0]["server"] = "127.0.0.1"

    profiles = client.runtime_profiles_from_generated_mihomo(artifact)

    assert len(profiles) == 7
    assert all(profile.server in client.PREMIUM_SMART_RU_RUNTIME_SERVERS for profile in profiles)


@pytest.mark.asyncio
async def test_call_runtime_agent_fails_closed_when_regional_agent_returns_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_primary(monkeypatch)
    _configure_moscow_target(monkeypatch)
    FakeAsyncClient.responses_by_base_url["https://moscow-target-agent.internal"] = {
        "status": "fail",
        "agent_id": "moscow-target-agent",
        "checks": [
            {
                "check_key": "runtime.transport.moscow",
                "check_name": "Moscow runtime",
                "category": "runtime",
                "status": "fail",
                "severity": "error",
                "target": "moscow",
                "safe_summary": "Moscow target failed",
                "details": {"safe_error_class": "ProxyHandshakeFailed"},
                "duration_ms": 1,
            }
        ],
    }

    result = await client.call_runtime_agent(
        run_id="run-1",
        suite_key="premium_smart_ru_v1",
        mode="runtime",
        route_entries=[],
        generated_mihomo_artifact=_generated_mihomo(),
    )

    assert result["status"] == "fail"
    assert result["reason"] == "runtime_agent_partial_failure"
    assert result["agent_statuses"] == {"primary": "pass", "moscow": "fail"}


@pytest.mark.asyncio
async def test_call_runtime_agent_fails_closed_when_regional_request_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_primary(monkeypatch)
    _configure_moscow_target(monkeypatch)
    FakeAsyncClient.failures_by_base_url["https://moscow-target-agent.internal"] = httpx.ConnectError(
        "connection failed"
    )

    result = await client.call_runtime_agent(
        run_id="run-1",
        suite_key="premium_smart_ru_v1",
        mode="runtime",
        route_entries=[],
        generated_mihomo_artifact=_generated_mihomo(),
    )

    assert result["status"] == "fail"
    assert result["reason"] == "agent_request_failed"
    assert result["checks"][0]["details"]["error_type"] == "ConnectError"


@pytest.mark.asyncio
async def test_call_runtime_agent_fails_closed_when_combined_check_keys_duplicate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_primary(monkeypatch)
    _configure_moscow_target(monkeypatch)
    FakeAsyncClient.responses_by_base_url["https://primary-agent.internal"] = {
        "status": "pass",
        "agent_id": "primary-agent",
        "checks": [
            {"check_key": "runtime.duplicate", "status": "pass", "details": {}},
            {"check_key": "runtime.duplicate", "status": "pass", "details": {}},
        ],
    }

    result = await client.call_runtime_agent(
        run_id="run-1",
        suite_key="premium_smart_ru_v1",
        mode="runtime",
        route_entries=[],
        generated_mihomo_artifact=_generated_mihomo(),
    )

    assert result["status"] == "fail"
    assert result["reason"] == "duplicate_agent_check_keys"
    check_keys = [item["check_key"] for item in result["checks"]]
    assert len(check_keys) == len(set(check_keys))


@pytest.mark.asyncio
async def test_call_runtime_agent_rejects_explicit_matrix_above_hard_max(monkeypatch: pytest.MonkeyPatch) -> None:
    _configure_primary(monkeypatch)

    oversized = client.runtime_profiles_from_generated_mihomo(_generated_mihomo()) * 3

    result = await client.call_runtime_agent(
        run_id="run-1",
        suite_key="premium_smart_ru_v1",
        mode="runtime",
        route_entries=[],
        transport_profiles=oversized,
    )

    assert result["status"] == "fail"
    assert result["reason"] == "profile_matrix_too_large"
    assert result["checks"][0]["severity"] == "error"
    assert result["checks"][0]["details"]["actual_profile_count"] == 24
    assert FakeAsyncClient.requests == []
