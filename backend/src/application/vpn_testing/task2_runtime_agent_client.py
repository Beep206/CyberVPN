"""Task2-specific runtime-agent client and selected-outbound correlation."""

from __future__ import annotations

import asyncio
import json
import secrets
from collections.abc import Mapping, Sequence
from typing import Any, Literal
from urllib.parse import urlparse
from uuid import UUID

import httpx
import yaml
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator

from src.application.vpn_testing.runtime_agent_client import (
    RUNTIME_AGENT_ENDPOINT,
    RUNTIME_AGENT_METHOD,
    RuntimeAgentProtocolError,
    _read_bounded_runtime_agent_response,
    _redact_response,
    _signed_runtime_agent_request,
    _validate_runtime_agent_response_evidence,
)
from src.application.vpn_testing.task2_probe_plan import Task2RouteProbeSpec, build_task2_route_probe_specs
from src.application.vpn_testing.task2_route_evidence import (
    Task2RouteEvidenceExpectation,
    Task2RouteEvidenceRejected,
    Task2RouteEvidenceStore,
    Task2RouteEvidenceUnavailable,
    task2_route_evidence_result_digest,
    task2_route_evidence_target_digest,
)
from src.config.settings import settings

TASK2_SUITE_ID = "premium_spb_de_exceptions_v1"
TASK2_SERVER = "spb-exceptions.cyber-vpn.org"
TASK2_PORTS = {"raw": 4443, "xhttp": 8444}
TASK2_RESULT_POLL_SECONDS = 5.0
TASK2_RESULT_POLL_INTERVAL_SECONDS = 0.1
TASK2_MAX_ROUTE_EXPECTATIONS = 64
TASK2_CORRELATION_PORT_MIN = 1024
TASK2_CORRELATION_PORT_MAX = 65535
_SAFE_TERMINAL_CLASSES = frozenset(
    {
        "tcp_connect_established",
        "udp_datagram_sent",
        "socks_unavailable",
        "socks_auth_rejected",
        "socks_invalid_reply",
        "socks_request_rejected",
        "socks_request_ok",
        "probe_timeout",
        "timeout",
        "probe_io_error",
        "dns_failed",
        "profile_tcp_connect_failed",
        "xray_start_failed",
    }
)


class Task2RuntimeProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True, str_strip_whitespace=True)

    name: str = Field(..., min_length=1, max_length=160)
    location: str = Field(default="RU SPB", min_length=1, max_length=80)
    node: str = Field(..., min_length=1, max_length=160)
    server: str = Field(..., min_length=1, max_length=253)
    port: int = Field(..., ge=1, le=65535)
    network: Literal["raw", "tcp", "xhttp"]
    uuid: str = Field(..., min_length=1, max_length=80)
    flow: str = Field(default="", max_length=80)
    sni: str = Field(..., min_length=1, max_length=253, validation_alias=AliasChoices("sni", "servername"))
    public_key: str = Field(
        ...,
        min_length=1,
        max_length=120,
        validation_alias=AliasChoices("public_key", "publicKey", "public-key"),
    )
    short_id: str = Field(
        default="",
        max_length=32,
        validation_alias=AliasChoices("short_id", "shortId", "short-id"),
    )
    xhttp_path: str | None = Field(
        default=None,
        max_length=128,
        validation_alias=AliasChoices("xhttp_path", "xhttpPath", "path"),
    )
    xhttp_mode: str | None = Field(
        default=None,
        max_length=32,
        validation_alias=AliasChoices("xhttp_mode", "xhttpMode", "mode"),
    )
    fingerprint: str = Field(default="chrome", min_length=1, max_length=40)

    @field_validator("server")
    @classmethod
    def validate_server(cls, value: str) -> str:
        normalized = value.lower()
        if normalized != TASK2_SERVER:
            raise ValueError("task2_runtime_server_not_allowed")
        return normalized

    @field_validator("uuid")
    @classmethod
    def validate_uuid(cls, value: str) -> str:
        UUID(value)
        return value

    @property
    def transport(self) -> Literal["raw", "xhttp"]:
        return "xhttp" if self.network == "xhttp" else "raw"

    @model_validator(mode="after")
    def validate_transport(self) -> Task2RuntimeProfile:
        if self.port != TASK2_PORTS[self.transport]:
            raise ValueError("task2_runtime_profile_port_mismatch")
        if self.transport == "raw" and self.flow != "xtls-rprx-vision":
            raise ValueError("task2_runtime_raw_profile_requires_vision")
        if self.transport == "xhttp" and (not self.xhttp_path or not self.xhttp_path.startswith("/")):
            raise ValueError("task2_runtime_xhttp_path_required")
        if self.transport == "xhttp" and not self.xhttp_mode:
            raise ValueError("task2_runtime_xhttp_mode_required")
        return self

    def credential_values(self) -> set[str]:
        return {
            item
            for item in (self.uuid, self.sni, self.public_key, self.short_id, self.xhttp_path, self.xhttp_mode)
            if item
        }


def _secret_value(secret: SecretStr | None) -> str:
    return secret.get_secret_value().strip() if secret is not None else ""


def task2_runtime_agent_configured() -> bool:
    return bool(_agent_url(settings.vpn_test_agent_spb_url) and _secret_value(settings.vpn_test_agent_spb_secret))


def _agent_url(value: Any) -> str:
    normalized = str(value or "").strip().rstrip("/")
    if not normalized:
        return ""
    parsed = urlparse(normalized)
    if (
        parsed.scheme != "https"
        or parsed.hostname is None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        return ""
    return normalized


def _artifact_mapping(artifact: Any) -> Mapping[str, Any] | None:
    if isinstance(artifact, Mapping):
        if isinstance(artifact.get("proxies"), list):
            return artifact
        for key in ("generated_mihomo_yaml", "mihomo_yaml", "generated_subscription_yaml", "yaml", "body"):
            value = artifact.get(key)
            if value is not None:
                resolved = _artifact_mapping(value)
                if resolved is not None:
                    return resolved
        return None
    if isinstance(artifact, str) and artifact.strip():
        try:
            value = yaml.safe_load(artifact)
        except yaml.YAMLError:
            return None
        return value if isinstance(value, Mapping) else None
    return None


def task2_runtime_profiles_from_generated_mihomo(artifact: Any) -> list[Task2RuntimeProfile]:
    mapping = _artifact_mapping(artifact)
    if mapping is None:
        return []
    profiles: list[Task2RuntimeProfile] = []
    for proxy in mapping.get("proxies", []):
        if not isinstance(proxy, Mapping) or str(proxy.get("type") or "").lower() != "vless":
            continue
        server = str(proxy.get("server") or "").lower()
        if server != TASK2_SERVER:
            continue
        network = str(proxy.get("network") or "tcp").lower()
        if network not in {"raw", "tcp", "xhttp"}:
            continue
        reality = proxy.get("reality-opts")
        reality = reality if isinstance(reality, Mapping) else {}
        xhttp = proxy.get("xhttp-opts")
        xhttp = xhttp if isinstance(xhttp, Mapping) else {}
        raw_profile = {
            "name": proxy.get("name"),
            "location": "RU SPB",
            "node": proxy.get("name"),
            "server": server,
            "port": proxy.get("port"),
            "network": network,
            "uuid": proxy.get("uuid") or proxy.get("id") or proxy.get("password"),
            "flow": proxy.get("flow") or "",
            "sni": proxy.get("servername") or proxy.get("sni"),
            "public_key": reality.get("public-key") or reality.get("publicKey") or reality.get("public_key"),
            "short_id": reality.get("short-id") or reality.get("shortId") or reality.get("short_id") or "",
            "xhttp_path": proxy.get("path") or xhttp.get("path"),
            "xhttp_mode": proxy.get("mode") or xhttp.get("mode"),
            "fingerprint": proxy.get("client-fingerprint") or proxy.get("fingerprint") or "chrome",
        }
        try:
            profiles.append(Task2RuntimeProfile.model_validate(raw_profile))
        except ValueError:
            continue
    if len(profiles) != 2 or {profile.transport for profile in profiles} != {"raw", "xhttp"}:
        return []
    return sorted(profiles, key=lambda profile: profile.transport)


def _contains_forbidden_selected_outbound(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(
            key == "selected_outbound" or _contains_forbidden_selected_outbound(item) for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_forbidden_selected_outbound(item) for item in value)
    return False


def _failure(reason: str, *, details: Mapping[str, Any] | None = None) -> dict[str, Any]:
    return {
        "status": "fail",
        "reason": reason,
        "checks": [
            {
                "check_key": "premium_spb_de_exceptions.runtime.dispatch",
                "check_name": "Task2 runtime agent dispatch",
                "category": "runtime",
                "status": "fail",
                "severity": "error",
                "target": "spb-runtime-agent",
                "safe_summary": "Task2 runtime selected-outbound proof failed closed",
                "details": dict(details or {}),
                "duration_ms": 0,
            }
        ],
    }


async def _post_signed_payload(
    *,
    url: str,
    secret: str,
    payload: Mapping[str, Any],
    redaction_values: set[str],
) -> dict[str, Any]:
    try:
        body, headers, request_nonce, max_skew_seconds = _signed_runtime_agent_request(
            payload=payload,
            secret=secret,
            audience="spb",
        )
    except RuntimeAgentProtocolError as exc:
        return _failure("agent_request_signature_failed", details={"evidence_error": exc.reason})
    timeout_seconds = min(180.0, max(30.0, float(settings.vpn_test_agent_timeout_seconds) * 6))
    timeout = httpx.Timeout(connect=min(5.0, timeout_seconds), read=timeout_seconds, write=15.0, pool=5.0)
    try:
        async with httpx.AsyncClient(base_url=url, timeout=timeout, trust_env=False) as client:
            async with client.stream(
                RUNTIME_AGENT_METHOD,
                RUNTIME_AGENT_ENDPOINT,
                content=body,
                headers=headers,
            ) as response:
                response_body = await _read_bounded_runtime_agent_response(response)
                response_body = _validate_runtime_agent_response_evidence(
                    response=response,
                    response_body=response_body,
                    secret=secret,
                    request_nonce=request_nonce,
                    expected_audience="spb",
                    max_skew_seconds=max_skew_seconds,
                )
                if not 200 <= response.status_code < 300:
                    return _failure(
                        "agent_signed_http_error",
                        details={"response_status": response.status_code},
                    )
    except RuntimeAgentProtocolError as exc:
        return _failure("agent_invalid_response_evidence", details={"evidence_error": exc.reason})
    except httpx.HTTPError as exc:
        return _failure("agent_request_failed", details={"error_type": type(exc).__name__})
    try:
        decoded = json.loads(response_body)
    except json.JSONDecodeError:
        return _failure("agent_invalid_json_response")
    if not isinstance(decoded, dict):
        return _failure("agent_invalid_response")
    return _redact_response(decoded, redaction_values)


def _target(spec: Task2RouteProbeSpec) -> str:
    return f"{spec.probe_network}:{spec.target_ip}:{spec.target_port}"


def _run_scoped_probe_specs(specs: Sequence[Task2RouteProbeSpec]) -> list[Task2RouteProbeSpec]:
    """Make the callback target tuple unpredictable and unique for this run."""

    if not specs or len(specs) > TASK2_MAX_ROUTE_EXPECTATIONS:
        raise ValueError("task2_probe_matrix_invalid")
    port_span = TASK2_CORRELATION_PORT_MAX - TASK2_CORRELATION_PORT_MIN + 1
    ports: set[int] = set()
    while len(ports) < len(specs):
        ports.add(TASK2_CORRELATION_PORT_MIN + secrets.randbelow(port_span))
    return [spec.model_copy(update={"target_port": port}) for spec, port in zip(specs, sorted(ports), strict=True)]


def _expectation_payload(spec: Task2RouteProbeSpec, expectation_id: str) -> dict[str, Any]:
    return {
        "expectation_id": expectation_id,
        "route_key": spec.route_key,
        "transport": spec.transport,
        "probe_network": spec.probe_network,
        "target_ip": spec.target_ip,
        "target_port": spec.target_port,
        "expected_outbound": spec.expected_outbound,
        "membership": spec.membership,
        "manifest_sha256": spec.manifest_sha256,
        "route_feed_version": spec.route_feed_version,
    }


def _validate_agent_attempts(
    agent_payload: Mapping[str, Any],
    expectation_ids: Mapping[str, str],
) -> dict[str, str] | None:
    if _contains_forbidden_selected_outbound(agent_payload):
        return None
    attempts = agent_payload.get("route_attempts")
    if not isinstance(attempts, list) or len(attempts) != len(expectation_ids):
        return None
    terminals: dict[str, str] = {}
    for item in attempts:
        if not isinstance(item, Mapping) or set(item) != {
            "expectation_id",
            "route_key",
            "transport",
            "probe_network",
            "terminal_class",
        }:
            return None
        route_key = str(item["route_key"])
        if expectation_ids.get(route_key) != item["expectation_id"] or route_key in terminals:
            return None
        terminal_class = str(item["terminal_class"])
        if terminal_class not in _SAFE_TERMINAL_CLASSES:
            return None
        terminals[route_key] = terminal_class
    return terminals if set(terminals) == set(expectation_ids) else None


async def _collect_results(
    store: Task2RouteEvidenceStore,
    target_digests: Mapping[str, str],
    specs_by_route: Mapping[str, Task2RouteProbeSpec],
    *,
    run_id: str,
    webhook_secret: str,
) -> dict[str, Any]:
    deadline = asyncio.get_running_loop().time() + TASK2_RESULT_POLL_SECONDS
    results: dict[str, Any] = {}
    while True:
        for route_key, target_digest in target_digests.items():
            if route_key in results:
                continue
            result = await store.get_result_for_target_digest(run_id, target_digest)
            if result is not None:
                spec = specs_by_route[route_key]
                expected_verdict = "pass" if result.selected_outbound == spec.expected_outbound else "fail"
                expected_digest = task2_route_evidence_result_digest(
                    webhook_secret,
                    run_id=result.run_id,
                    route_key=result.route_key,
                    selected_outbound=result.selected_outbound,
                    verdict=result.verdict,
                    target_digest=target_digest,
                )
                if (
                    result.run_id != run_id
                    or result.route_key != route_key
                    or result.verdict != expected_verdict
                    or not secrets.compare_digest(result.digest, expected_digest)
                ):
                    raise Task2RouteEvidenceRejected("result_binding_mismatch")
                results[route_key] = result
        if len(results) == len(target_digests) or asyncio.get_running_loop().time() >= deadline:
            return results
        await asyncio.sleep(TASK2_RESULT_POLL_INTERVAL_SECONDS)


async def call_task2_runtime_agent(
    *,
    run_id: str,
    route_entries: Sequence[Any],
    generated_mihomo_artifact: Any,
    evidence_store: Task2RouteEvidenceStore,
) -> dict[str, Any]:
    """Dispatch Task2 probes and correlate only server-produced selected-outbound events."""

    url = _agent_url(settings.vpn_test_agent_spb_url)
    secret = _secret_value(settings.vpn_test_agent_spb_secret)
    if not url or not secret:
        return _failure("task2_agent_unavailable")
    profiles = task2_runtime_profiles_from_generated_mihomo(generated_mihomo_artifact)
    if len(profiles) != 2:
        return _failure("task2_profile_matrix_invalid")
    try:
        feed_specs = build_task2_route_probe_specs(route_entries)
    except (ValueError, OSError):
        return _failure("task2_promoted_feed_invalid")
    if not feed_specs or len(feed_specs) > TASK2_MAX_ROUTE_EXPECTATIONS:
        return _failure("task2_probe_matrix_invalid")
    try:
        specs = _run_scoped_probe_specs(feed_specs)
    except ValueError:
        return _failure("task2_probe_matrix_invalid")

    webhook_secret = settings.vpn_tester_task2_xray_webhook_secret.get_secret_value().strip()
    expectation_ids: dict[str, str] = {}
    target_digests: dict[str, str] = {}
    created_digests: list[str] = []
    try:
        for spec in specs:
            expectation_id = secrets.token_hex(16)
            target_digest = task2_route_evidence_target_digest(webhook_secret, _target(spec))
            await evidence_store.create_expectation(
                Task2RouteEvidenceExpectation(
                    run_id=run_id,
                    route_key=spec.route_key,
                    target_digest=target_digest,
                    expected_outbound=spec.expected_outbound,
                    expected_inbound_tag=(
                        "SPB_EXCEPTIONS_REALITY_443" if spec.transport == "raw" else "SPB_EXCEPTIONS_XHTTP_REALITY_8443"
                    ),
                    expected_network=spec.probe_network,
                )
            )
            expectation_ids[spec.route_key] = expectation_id
            target_digests[spec.route_key] = target_digest
            created_digests.append(target_digest)
    except (Task2RouteEvidenceRejected, Task2RouteEvidenceUnavailable):
        try:
            await evidence_store.delete_expectations(created_digests)
        except Task2RouteEvidenceUnavailable:
            pass
        return _failure("task2_expectation_store_unavailable")

    payload = {
        "run_id": run_id,
        "suite_key": TASK2_SUITE_ID,
        "mode": "runtime",
        "runtime_mode": "proxy-only",
        "request_scope": "full",
        "tun_sandbox_requested": False,
        "routes": [_expectation_payload(spec, expectation_ids[spec.route_key]) for spec in specs],
        "transport_profiles": [profile.model_dump(exclude_none=True) for profile in profiles],
    }
    redaction_values = {secret, webhook_secret}
    for profile in profiles:
        redaction_values.update(profile.credential_values())
    agent_payload = await _post_signed_payload(
        url=url,
        secret=secret,
        payload=payload,
        redaction_values=redaction_values,
    )
    terminals = _validate_agent_attempts(agent_payload, expectation_ids)
    if terminals is None:
        try:
            await evidence_store.delete_expectations(created_digests)
        except Task2RouteEvidenceUnavailable:
            pass
        return _failure("task2_agent_attempt_evidence_invalid")

    try:
        results = await _collect_results(
            evidence_store,
            target_digests,
            {spec.route_key: spec for spec in specs},
            run_id=run_id,
            webhook_secret=webhook_secret,
        )
    except (Task2RouteEvidenceRejected, Task2RouteEvidenceUnavailable):
        results = {}
    finally:
        try:
            await evidence_store.delete_expectations(created_digests)
        except Task2RouteEvidenceUnavailable:
            pass
    try:
        confirmed_specs = build_task2_route_probe_specs(route_entries)
    except (ValueError, OSError):
        return _failure("task2_promoted_feed_changed")
    if [item.model_dump() for item in confirmed_specs] != [item.model_dump() for item in feed_specs]:
        return _failure("task2_promoted_feed_changed")

    checks: list[dict[str, Any]] = []
    for spec in specs:
        result = results.get(spec.route_key)
        status_value = "pass" if result is not None and result.verdict == "pass" else "fail"
        checks.append(
            {
                "check_key": f"premium_spb_de_exceptions.selected_outbound.{spec.route_key}",
                "check_name": "Task2 server selected outbound",
                "category": "runtime",
                "status": status_value,
                "severity": "error",
                "target": spec.route_key,
                "safe_summary": "Server-selected outbound matched the promoted feed expectation"
                if status_value == "pass"
                else "Server-selected outbound evidence was missing or mismatched",
                "details": {
                    "route_key": spec.route_key,
                    "traffic_class": spec.traffic_class,
                    "category": spec.category,
                    "transport": spec.transport,
                    "probe_network": spec.probe_network,
                    "membership": spec.membership,
                    "expected_outbound": spec.expected_outbound,
                    "selected_outbound": result.selected_outbound if result is not None else None,
                    "verdict": result.verdict if result is not None else "missing",
                    "digest": result.digest if result is not None else None,
                    "terminal_class": terminals[spec.route_key],
                    "manifest_sha256": spec.manifest_sha256,
                    "route_feed_version": spec.route_feed_version,
                    "credentials_redacted": True,
                },
                "duration_ms": 0,
            }
        )
    selected_outbound_pass = len(results) == len(specs) and all(check["status"] == "pass" for check in checks)
    checks.append(
        {
            "check_key": "premium_spb_de_exceptions.selected_outbound.matrix",
            "check_name": "Task2 selected-outbound matrix",
            "category": "runtime",
            "status": "degraded" if selected_outbound_pass else "fail",
            "severity": "warning" if selected_outbound_pass else "error",
            "target": "spb-xray",
            "safe_summary": "Selected-outbound matrix matched; bridge-down evidence is still required"
            if selected_outbound_pass
            else "Task2 selected-outbound matrix is incomplete",
            "details": {
                "expected_count": len(specs),
                "actual_count": len(results),
                "all_13_categories_declared": sum(spec.category is not None for spec in specs) >= 13,
                "raw_xhttp_tcp_udp_declared": True,
                "bridge_down_evidence_claimed": False,
            },
            "duration_ms": 0,
        }
    )
    return {
        "status": "partial" if selected_outbound_pass else "fail",
        "reason": "bridge_down_evidence_not_claimed" if selected_outbound_pass else "selected_outbound_matrix_failed",
        "agent_id": agent_payload.get("agent_id"),
        "checks": checks,
    }
