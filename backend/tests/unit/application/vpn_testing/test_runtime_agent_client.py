from __future__ import annotations

import hashlib
import hmac
import json
from collections.abc import Callable
from itertools import count
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
_FIXED_TIME = 1_800_000_000
_FIXED_MONOTONIC = 10_000.0


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


def _canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _sha256_hex(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _protocol_signature(
    *,
    secret: str,
    protocol_version: str,
    timestamp: str,
    nonce: str,
    audience: str,
    body_sha256: str,
    status_code: int | None = None,
) -> str:
    status_component = "" if status_code is None else str(status_code)
    material = (
        f"{protocol_version}\n{client.RUNTIME_AGENT_METHOD}\n{client.RUNTIME_AGENT_ENDPOINT}\n{status_component}\n"
        f"{client.RUNTIME_AGENT_CONTENT_TYPE}\n{timestamp}\n{nonce}\n{audience}\n{body_sha256}"
    ).encode("ascii")
    return hmac.new(secret.encode("utf-8"), material, hashlib.sha256).hexdigest()


def _request_secret(request: dict[str, Any]) -> str:
    return {
        "https://primary-agent.internal": "primary-agent-secret",
        "https://moscow-target-agent.internal": "moscow-target-secret",
        "https://spb-target-agent.internal": "spb-target-secret",
    }[request["base_url"]]


def _signed_response(
    request: dict[str, Any],
    data: Any,
    *,
    body: bytes | None = None,
    timestamp: str | None = None,
    nonce: str | None = None,
    header_overrides: dict[str, str] | None = None,
    drop_headers: tuple[str, ...] = (),
    status_code: int = 200,
) -> FakeResponse:
    response_body = body if body is not None else _canonical_json_bytes(data)
    response_timestamp = timestamp or request["headers"][client.RUNTIME_AGENT_TIMESTAMP_HEADER]
    response_nonce = nonce or request["headers"][client.RUNTIME_AGENT_NONCE_HEADER]
    response_audience = request["headers"][client.RUNTIME_AGENT_AUDIENCE_HEADER]
    body_sha256 = _sha256_hex(response_body)
    secret = _request_secret(request)
    headers = {
        client.RUNTIME_AGENT_RESPONSE_TIMESTAMP_HEADER: response_timestamp,
        client.RUNTIME_AGENT_RESPONSE_NONCE_HEADER: response_nonce,
        client.RUNTIME_AGENT_RESPONSE_AUDIENCE_HEADER: response_audience,
        "Content-Type": client.RUNTIME_AGENT_CONTENT_TYPE,
        client.RUNTIME_AGENT_RESPONSE_BODY_SHA256_HEADER: body_sha256,
        client.RUNTIME_AGENT_RESPONSE_SIGNATURE_HEADER: _protocol_signature(
            secret=secret,
            protocol_version=client.RUNTIME_AGENT_RESPONSE_PROTOCOL_VERSION,
            timestamp=response_timestamp,
            nonce=response_nonce,
            audience=response_audience,
            body_sha256=body_sha256,
            status_code=status_code,
        ),
    }
    for header in drop_headers:
        headers.pop(header, None)
    if header_overrides:
        headers.update(header_overrides)
    return FakeResponse(content=response_body, headers=headers, status_code=status_code)


def _response_with_tampered_status(request: dict[str, Any]) -> FakeResponse:
    response = _signed_response(request, {"status": "pass", "checks": []})
    response.status_code = 503
    return response


def _response_with_duplicate_signature_header(request: dict[str, Any]) -> FakeResponse:
    response = _signed_response(request, {"status": "pass", "checks": []})
    response.headers = httpx.Headers(
        [*response.headers.multi_items(), (client.RUNTIME_AGENT_RESPONSE_SIGNATURE_HEADER, "0" * 64)]
    )
    return response


def _assert_lower_hex(value: str, expected_length: int) -> None:
    assert len(value) == expected_length
    assert all(char in "0123456789abcdef" for char in value)


def _assert_valid_request_signature(
    request: dict[str, Any], secret: str, expected_audience: client.RuntimeAgentRole = "primary"
) -> None:
    headers = request["headers"]
    body = request["content"]
    body_sha256 = _sha256_hex(body)
    assert body == _canonical_json_bytes(request["json"])
    assert "X-VPN-Test-Agent-Secret" not in headers
    assert headers["Content-Type"] == client.RUNTIME_AGENT_CONTENT_TYPE
    assert headers[client.RUNTIME_AGENT_TIMESTAMP_HEADER] == str(_FIXED_TIME)
    _assert_lower_hex(headers[client.RUNTIME_AGENT_NONCE_HEADER], 32)
    assert headers[client.RUNTIME_AGENT_AUDIENCE_HEADER] == expected_audience
    assert headers[client.RUNTIME_AGENT_BODY_SHA256_HEADER] == body_sha256
    _assert_lower_hex(headers[client.RUNTIME_AGENT_BODY_SHA256_HEADER], 64)
    _assert_lower_hex(headers[client.RUNTIME_AGENT_SIGNATURE_HEADER], 64)
    assert hmac.compare_digest(
        headers[client.RUNTIME_AGENT_SIGNATURE_HEADER],
        _protocol_signature(
            secret=secret,
            protocol_version=client.RUNTIME_AGENT_PROTOCOL_VERSION,
            timestamp=headers[client.RUNTIME_AGENT_TIMESTAMP_HEADER],
            nonce=headers[client.RUNTIME_AGENT_NONCE_HEADER],
            audience=expected_audience,
            body_sha256=body_sha256,
        ),
    )


class FakeResponse:
    def __init__(self, *, content: bytes, headers: dict[str, str] | None = None, status_code: int = 200) -> None:
        self.content = content
        self.headers = httpx.Headers(headers or {})
        self.status_code = status_code
        self.json_called = False

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("POST", "https://runtime-agent.invalid/internal/v2/runtime-checks")
            response = httpx.Response(self.status_code, request=request, content=self.content)
            raise httpx.HTTPStatusError("runtime agent returned error", request=request, response=response)
        return None

    def json(self) -> Any:
        self.json_called = True
        return json.loads(self.content)

    async def aiter_bytes(self) -> Any:
        yield self.content


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

    async def post(self, path: str, *, content: bytes, headers: dict[str, str]) -> FakeResponse:
        payload = json.loads(content)
        request = {
            "base_url": self.base_url,
            "path": path,
            "content": content,
            "json": payload,
            "headers": headers,
            "trust_env": self.trust_env,
        }
        self.__class__.requests.append(request)
        failure = self.__class__.failures_by_base_url.get(self.base_url)
        if failure is not None:
            raise failure
        response = self.__class__.responses_by_base_url.get(self.base_url)
        if callable(response):
            produced_response = response(request)
            if isinstance(produced_response, FakeResponse):
                return produced_response
            return _signed_response(request, produced_response)
        if response is not None:
            if isinstance(response, FakeResponse):
                return response
            return _signed_response(request, response)
        return _signed_response(request, _default_response(request))

    def stream(self, method: str, path: str, *, content: bytes, headers: dict[str, str]) -> Any:
        client = self

        class FakeStreamContext:
            async def __aenter__(self) -> FakeResponse:
                assert method == "POST"
                self.response = await client.post(path, content=content, headers=headers)
                return self.response

            async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
                return None

        return FakeStreamContext()

    @classmethod
    def reset(cls) -> None:
        cls.requests = []
        cls.responses_by_base_url = {}
        cls.failures_by_base_url = {}


def _default_response(request: dict[str, Any]) -> dict[str, Any]:
    payload = request["json"]
    secret = _request_secret(request)
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
    monkeypatch.setattr(settings, "vpn_test_agent_signature_max_skew_seconds", 60)
    monkeypatch.setattr(client.time, "time", lambda: _FIXED_TIME)
    monkeypatch.setattr(client.time, "monotonic", lambda: _FIXED_MONOTONIC)
    nonces = count(1)
    monkeypatch.setattr(client.secrets, "token_hex", lambda size: f"{next(nonces):0{size * 2}x}")
    monkeypatch.setattr(client.httpx, "AsyncClient", FakeAsyncClient)
    with client._runtime_agent_nonce_cache_lock:
        client._runtime_agent_nonce_cache.clear()
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


def _response_evidence_error(result: dict[str, Any]) -> str:
    details = result["checks"][0]["details"]
    assert isinstance(details, dict)
    return str(details["evidence_error"])


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
    assert configured.vpn_test_agent_signature_max_skew_seconds == 60


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://regional-agent.example:18080", "https://regional-agent.example:18080"),
        ("http://cybervpn-vpn-test-agent:8080", "http://cybervpn-vpn-test-agent:8080"),
        ("http://regional-agent.example:18080", ""),
        ("https://user:password@regional-agent.example:18080", ""),
        ("https://regional-agent.example:18080/runtime", ""),
    ],
)
def test_agent_url_allows_only_https_or_local_compose_http(url: str, expected: str) -> None:
    assert client._agent_url(url) == expected


@pytest.mark.parametrize("skew_seconds", [0, -1, 301])
def test_settings_reject_invalid_runtime_agent_signature_skew(skew_seconds: int) -> None:
    with pytest.raises(ValueError, match="VPN_TEST_AGENT_SIGNATURE_MAX_SKEW_SECONDS"):
        Settings(
            environment="development",
            jwt_secret=SecretStr("xVanw-qakEZA0v_T5mJ9GSCJkTzoWYpHMJDX02lFg-B8"),
            remnawave_token=SecretStr("valid_token_for_testing_purposes_32characters"),
            cryptobot_token=SecretStr("valid_token_for_testing_purposes_32characters"),
            vpn_test_agent_signature_max_skew_seconds=skew_seconds,
        )


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
    _assert_valid_request_signature(request, "primary-agent-secret")
    with client._runtime_agent_nonce_cache_lock:
        assert (
            client._runtime_agent_nonce_cache[request["headers"][client.RUNTIME_AGENT_NONCE_HEADER]]
            == _FIXED_MONOTONIC + settings.vpn_test_agent_signature_max_skew_seconds * 2
        )
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
@pytest.mark.parametrize(
    ("response_factory", "expected_error"),
    [
        pytest.param(
            lambda request: _signed_response(
                request,
                {"status": "pass", "checks": []},
                drop_headers=(client.RUNTIME_AGENT_RESPONSE_TIMESTAMP_HEADER,),
            ),
            "response_timestamp_missing",
            id="missing-timestamp",
        ),
        pytest.param(
            lambda request: _signed_response(
                request,
                {"status": "pass", "checks": []},
                timestamp=str(_FIXED_TIME - 61),
            ),
            "response_timestamp_stale",
            id="stale-timestamp",
        ),
        pytest.param(
            lambda request: _signed_response(
                request,
                {"status": "pass", "checks": []},
                timestamp=str(_FIXED_TIME + 61),
            ),
            "response_timestamp_future",
            id="future-timestamp",
        ),
        pytest.param(
            lambda request: _signed_response(
                request,
                {"status": "pass", "checks": []},
                nonce="f" * 32,
            ),
            "response_nonce_mismatch",
            id="nonce-mismatch",
        ),
        pytest.param(
            lambda request: _signed_response(
                request,
                {"status": "pass", "checks": []},
                drop_headers=(client.RUNTIME_AGENT_RESPONSE_AUDIENCE_HEADER,),
            ),
            "response_audience_missing",
            id="missing-audience",
        ),
        pytest.param(
            lambda request: _signed_response(
                request,
                {"status": "pass", "checks": []},
                header_overrides={client.RUNTIME_AGENT_RESPONSE_AUDIENCE_HEADER: "spb"},
            ),
            "response_audience_mismatch",
            id="audience-mismatch",
        ),
        pytest.param(
            lambda request: _signed_response(
                request,
                {"status": "pass", "checks": []},
                header_overrides={"Content-Type": "text/plain"},
            ),
            "response_content_type_mismatch",
            id="content-type-mismatch",
        ),
        pytest.param(
            lambda request: _signed_response(
                request,
                None,
                body=b"x" * (client.RUNTIME_AGENT_MAX_RESPONSE_BODY_BYTES + 1),
            ),
            "response_body_too_large",
            id="oversized-body",
        ),
        pytest.param(
            _response_with_tampered_status,
            "response_signature_mismatch",
            id="status-tamper",
        ),
        pytest.param(
            _response_with_duplicate_signature_header,
            "response_signature_noncanonical",
            id="duplicate-signature-header",
        ),
        pytest.param(
            lambda request: _signed_response(
                request,
                {"status": "pass", "checks": []},
                header_overrides={client.RUNTIME_AGENT_RESPONSE_BODY_SHA256_HEADER: "0" * 64},
            ),
            "response_body_sha256_mismatch",
            id="body-hash-mismatch",
        ),
        pytest.param(
            lambda request: _signed_response(
                request,
                {"status": "pass", "checks": []},
                header_overrides={client.RUNTIME_AGENT_RESPONSE_SIGNATURE_HEADER: "0" * 64},
            ),
            "response_signature_mismatch",
            id="signature-mismatch",
        ),
    ],
)
async def test_call_runtime_agent_rejects_invalid_response_evidence(
    monkeypatch: pytest.MonkeyPatch,
    response_factory: ResponseFactory,
    expected_error: str,
) -> None:
    _configure_primary(monkeypatch)
    FakeAsyncClient.responses_by_base_url["https://primary-agent.internal"] = response_factory

    result = await client.call_runtime_agent(
        run_id="run-invalid-evidence",
        suite_key="premium_smart_ru_v1",
        mode="runtime",
        route_entries=[],
        generated_mihomo_artifact=_generated_mihomo(),
    )

    assert result["status"] == "fail"
    assert result["reason"] == "agent_invalid_response_evidence"
    assert _response_evidence_error(result) == expected_error
    _assert_no_sensitive_values(result, FakeAsyncClient.requests)


@pytest.mark.asyncio
async def test_call_runtime_agent_rejects_signed_non_json_response(monkeypatch: pytest.MonkeyPatch) -> None:
    _configure_primary(monkeypatch)
    FakeAsyncClient.responses_by_base_url["https://primary-agent.internal"] = lambda request: _signed_response(
        request,
        None,
        body=b"not-json",
    )

    result = await client.call_runtime_agent(
        run_id="run-invalid-json",
        suite_key="premium_smart_ru_v1",
        mode="runtime",
        route_entries=[],
        generated_mihomo_artifact=_generated_mihomo(),
    )

    assert result["status"] == "fail"
    assert result["reason"] == "agent_invalid_json_response"
    assert _response_evidence_error(result) == "response_json_invalid"


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
    _assert_valid_request_signature(by_url["https://primary-agent.internal"], "primary-agent-secret")
    _assert_valid_request_signature(
        by_url["https://moscow-target-agent.internal"], "moscow-target-secret", expected_audience="moscow"
    )
    _assert_valid_request_signature(
        by_url["https://spb-target-agent.internal"], "spb-target-secret", expected_audience="spb"
    )
    assert len({request["headers"][client.RUNTIME_AGENT_NONCE_HEADER] for request in by_url.values()}) == 3
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
@pytest.mark.parametrize(
    ("duplicate_kind", "expected_reason"),
    [("url", "duplicate_agent_target_url"), ("secret", "duplicate_agent_target_secret")],
)
async def test_call_runtime_agent_rejects_duplicate_regional_target_configuration(
    monkeypatch: pytest.MonkeyPatch,
    duplicate_kind: str,
    expected_reason: str,
) -> None:
    _configure_primary(monkeypatch)
    _configure_moscow_target(monkeypatch)
    if duplicate_kind == "url":
        monkeypatch.setattr(settings, "vpn_test_agent_moscow_url", settings.vpn_test_agent_url)
    else:
        monkeypatch.setattr(settings, "vpn_test_agent_moscow_secret", settings.vpn_test_agent_secret)

    result = await client.call_runtime_agent(
        run_id="run-duplicate-target",
        suite_key="premium_smart_ru_v1",
        mode="runtime",
        route_entries=[],
        generated_mihomo_artifact=_generated_mihomo(),
    )

    assert result["status"] == "fail"
    assert result["reason"] == expected_reason
    assert FakeAsyncClient.requests == []


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
async def test_call_runtime_agent_preserves_regional_protocol_failure_diagnostic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_primary(monkeypatch)
    _configure_moscow_target(monkeypatch)
    FakeAsyncClient.responses_by_base_url["https://moscow-target-agent.internal"] = FakeResponse(
        content=b"{}",
        headers={"Content-Type": client.RUNTIME_AGENT_CONTENT_TYPE},
    )

    result = await client.call_runtime_agent(
        run_id="run-regional-protocol-failure",
        suite_key="premium_smart_ru_v1",
        mode="runtime",
        route_entries=[],
        generated_mihomo_artifact=_generated_mihomo(),
    )

    assert result["status"] == "fail"
    assert result["reason"] == "runtime_agent_partial_failure"
    assert result["agent_failures"]["moscow"] == {
        "reason": "agent_invalid_response_evidence",
        "evidence_error": "response_timestamp_missing",
    }


@pytest.mark.asyncio
async def test_call_runtime_agent_preserves_signed_regional_capacity_diagnostic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_primary(monkeypatch)
    _configure_moscow_target(monkeypatch)
    FakeAsyncClient.responses_by_base_url["https://moscow-target-agent.internal"] = lambda request: _signed_response(
        request,
        {"detail": "Runtime capacity exhausted."},
        status_code=429,
    )

    result = await client.call_runtime_agent(
        run_id="run-regional-capacity-failure",
        suite_key="premium_smart_ru_v1",
        mode="runtime",
        route_entries=[],
        generated_mihomo_artifact=_generated_mihomo(),
    )

    assert result["status"] == "fail"
    assert result["reason"] == "runtime_agent_partial_failure"
    assert result["agent_failures"]["moscow"] == {
        "reason": "agent_capacity_exhausted",
        "evidence_error": "response_http_status_429",
    }


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
async def test_call_runtime_agent_fails_closed_when_agent_identity_is_reused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_primary(monkeypatch)
    _configure_moscow_target(monkeypatch)
    for url in ("https://primary-agent.internal", "https://moscow-target-agent.internal"):
        FakeAsyncClient.responses_by_base_url[url] = lambda request: {
            **_default_response(request),
            "agent_id": "duplicate-agent-id",
        }

    result = await client.call_runtime_agent(
        run_id="run-duplicate-agent-id",
        suite_key="premium_smart_ru_v1",
        mode="runtime",
        route_entries=[],
        generated_mihomo_artifact=_generated_mihomo(),
    )

    assert result["status"] == "fail"
    assert result["reason"] == "duplicate_agent_identity"


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
