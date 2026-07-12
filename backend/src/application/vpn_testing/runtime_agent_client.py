"""Internal client for the VPN test runtime agent."""

from __future__ import annotations

import asyncio
import json
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal
from uuid import UUID

import httpx
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator

from src.config.settings import settings

try:  # PyYAML is an optional parser fallback in slim tooling environments.
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

EXPECTED_RUNTIME_PROFILE_COUNT = 8
EXPECTED_RUNTIME_RAW_PROFILE_COUNT = 4
EXPECTED_RUNTIME_XHTTP_PROFILE_COUNT = 4
EXPECTED_REGIONAL_TARGET_PROFILE_COUNT = 2
HARD_MAX_RUNTIME_PROFILE_COUNT = 16
RUNTIME_AGENT_ENDPOINT = "/internal/v1/runtime-checks"
RUNTIME_AGENT_AUTH_HEADER = "X-VPN-Test-Agent-Secret"
PREMIUM_SMART_RU_RUNTIME_ENDPOINTS = {
    "de-relay.cyber-vpn.org": {"raw": 2053, "xhttp": 2083},
    "nl-4.cyber-vpn.org": {"raw": 443, "xhttp": 8443},
    "msk-relay.cyber-vpn.org": {"raw": 2053, "xhttp": 2083},
    "ru-spb-3.cyber-vpn.org": {"raw": 443, "xhttp": 8443},
}
PREMIUM_SMART_RU_RUNTIME_SERVERS = frozenset(PREMIUM_SMART_RU_RUNTIME_ENDPOINTS)
PREMIUM_SMART_RU_MOSCOW_SERVER = "msk-relay.cyber-vpn.org"
PREMIUM_SMART_RU_SPB_SERVER = "ru-spb-3.cyber-vpn.org"
PREMIUM_SMART_RU_LOCATION_BY_SERVER = {
    "de-relay.cyber-vpn.org": "DE",
    "nl-4.cyber-vpn.org": "NL",
    PREMIUM_SMART_RU_MOSCOW_SERVER: "RU Moscow",
    PREMIUM_SMART_RU_SPB_SERVER: "RU SPB",
}
PREMIUM_SMART_RU_RELEASE_LOCATION_KEY_BY_SERVER = {
    "de-relay.cyber-vpn.org": "de",
    "nl-4.cyber-vpn.org": "nl",
    PREMIUM_SMART_RU_MOSCOW_SERVER: "moscow",
    PREMIUM_SMART_RU_SPB_SERVER: "spb",
}
SENSITIVE_RESPONSE_KEYS = frozenset(
    {
        "uuid",
        "id",
        "public_key",
        "public-key",
        "publicKey",
        "short_id",
        "short-id",
        "shortId",
        "password",
        "token",
        "secret",
        "sni",
        "servername",
        "serverName",
        "xhttp_path",
        "xhttpPath",
        "path",
    }
)
RuntimeAgentRole = Literal["primary", "moscow", "spb"]


class RuntimeAgentTransportProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True, str_strip_whitespace=True)

    name: str = Field(..., min_length=1, max_length=160)
    location: str = Field(..., min_length=1, max_length=80)
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

    @field_validator("uuid")
    @classmethod
    def _validate_uuid(cls, value: str) -> str:
        normalized = value.strip()
        UUID(normalized)
        return normalized

    @field_validator("server")
    @classmethod
    def _validate_server(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in PREMIUM_SMART_RU_RUNTIME_SERVERS:
            raise ValueError("runtime_profile_server_not_allowed")
        return normalized

    @field_validator("network")
    @classmethod
    def _normalize_network(cls, value: str) -> str:
        return "raw" if value == "tcp" else value

    @model_validator(mode="after")
    def _validate_transport_contract(self) -> RuntimeAgentTransportProfile:
        expected_ports = PREMIUM_SMART_RU_RUNTIME_ENDPOINTS[self.server]
        if self.network == "raw":
            if self.port != expected_ports["raw"]:
                raise ValueError("raw_tcp_profile_port_mismatch")
            if self.flow != "xtls-rprx-vision":
                raise ValueError("raw_tcp_profiles_must_use_vision_flow")
            return self
        if self.port != expected_ports["xhttp"]:
            raise ValueError("xhttp_profile_port_mismatch")
        if not self.xhttp_path or not self.xhttp_path.startswith("/"):
            raise ValueError("xhttp_profiles_must_include_path")
        if not self.xhttp_mode:
            raise ValueError("xhttp_profiles_must_include_mode")
        return self

    @property
    def transport(self) -> str:
        return "xhttp" if self.network == "xhttp" else "raw"

    def credential_values(self) -> set[str]:
        values = {
            self.uuid,
            self.public_key,
            self.short_id,
            self.sni,
            self.xhttp_path or "",
            self.xhttp_mode or "",
        }
        return {value for value in values if value}


@dataclass(frozen=True)
class RuntimeAgentTarget:
    role: RuntimeAgentRole
    url: str
    secret: str
    profiles: tuple[RuntimeAgentTransportProfile, ...]


def _secret_value(secret: SecretStr | None) -> str:
    return secret.get_secret_value().strip() if secret is not None else ""


def _agent_secret() -> str:
    return _secret_value(settings.vpn_test_agent_secret)


def runtime_agent_configured() -> bool:
    return bool(_agent_url(settings.vpn_test_agent_url) and _agent_secret())


def _agent_url(value: Any) -> str:
    return str(value or "").strip().rstrip("/")


def _mapping_list(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _artifact_mapping(artifact: Any) -> Mapping[str, Any] | None:
    if isinstance(artifact, Mapping):
        if isinstance(artifact.get("proxies"), list):
            return artifact
        for key in (
            "generated_mihomo_yaml",
            "mihomo_yaml",
            "generated_subscription_yaml",
            "subscription_yaml",
            "yaml",
            "body",
            "text",
            "content",
        ):
            value = artifact.get(key)
            if isinstance(value, str) and value.strip():
                return _artifact_mapping(value)
        nested = artifact.get("mihomo") or artifact.get("generated_mihomo")
        if nested is not None:
            return _artifact_mapping(nested)
        return None
    if isinstance(artifact, str) and artifact.strip():
        try:
            parsed = yaml.safe_load(artifact) if yaml is not None else json.loads(artifact)
        except Exception:  # noqa: BLE001 - caller receives an empty profile matrix, not parser internals.
            return None
        return parsed if isinstance(parsed, Mapping) else None
    return None


def _reality_opts(proxy: Mapping[str, Any]) -> Mapping[str, Any]:
    reality = proxy.get("reality-opts")
    return reality if isinstance(reality, Mapping) else {}


def _xhttp_opts(proxy: Mapping[str, Any]) -> Mapping[str, Any]:
    options = proxy.get("xhttp-opts") or proxy.get("xhttp_opts")
    return options if isinstance(options, Mapping) else {}


def _location_from_name(name: str) -> str:
    lower = name.lower()
    if "moscow" in lower or "msk" in lower or "моск" in lower:
        return "RU Moscow"
    if "spb" in lower or "saint" in lower or "петер" in lower:
        return "RU SPB"
    if "nl" in lower or "amsterdam" in lower or "нидер" in lower:
        return "NL"
    if "de" in lower or "frankfurt" in lower or "герм" in lower:
        return "DE"
    return name[:80]


def runtime_profiles_from_generated_mihomo(artifact: Any) -> list[RuntimeAgentTransportProfile]:
    mapping = _artifact_mapping(artifact)
    if mapping is None:
        return []
    profiles: list[RuntimeAgentTransportProfile] = []
    for proxy in _mapping_list(mapping.get("proxies")):
        if str(proxy.get("type") or "").lower() != "vless":
            continue
        network = str(proxy.get("network") or "tcp").lower()
        if network not in {"", "tcp", "raw", "xhttp"}:
            continue
        reality = _reality_opts(proxy)
        xhttp = _xhttp_opts(proxy)
        name = str(proxy.get("name") or "").strip()
        server = str(proxy.get("server") or "").strip()
        if not name or not server:
            continue
        raw_profile = {
            "name": name,
            "location": PREMIUM_SMART_RU_LOCATION_BY_SERVER.get(server.lower(), _location_from_name(name)),
            "node": name,
            "server": server,
            "port": proxy.get("port"),
            "network": "xhttp" if network == "xhttp" else "raw",
            "uuid": proxy.get("uuid") or proxy.get("id") or proxy.get("password"),
            "flow": str(proxy.get("flow") or ""),
            "sni": proxy.get("servername") or proxy.get("sni"),
            "public_key": reality.get("public-key") or reality.get("publicKey") or reality.get("public_key"),
            "short_id": reality.get("short-id") or reality.get("shortId") or reality.get("short_id") or "",
            "xhttp_path": proxy.get("path") or xhttp.get("path"),
            "xhttp_mode": proxy.get("mode") or xhttp.get("mode"),
            "fingerprint": proxy.get("client-fingerprint") or proxy.get("fingerprint") or "chrome",
        }
        try:
            profiles.append(RuntimeAgentTransportProfile.model_validate(raw_profile))
        except ValueError:
            continue
        if len(profiles) >= HARD_MAX_RUNTIME_PROFILE_COUNT:
            break
    return profiles


def _profiles_from_route_entries(route_entries: Sequence[Any]) -> list[RuntimeAgentTransportProfile]:
    profiles: list[RuntimeAgentTransportProfile] = []
    for entry in route_entries:
        metadata = getattr(entry, "metadata_json", None)
        if not isinstance(metadata, Mapping):
            continue
        for key in ("runtime_transport_profiles", "transport_profiles", "profile_matrix"):
            for item in _mapping_list(metadata.get(key)):
                try:
                    profiles.append(RuntimeAgentTransportProfile.model_validate(item))
                except ValueError:
                    continue
        for key in ("generated_mihomo_yaml", "mihomo_yaml", "generated_subscription_yaml"):
            profiles.extend(runtime_profiles_from_generated_mihomo(metadata.get(key)))
        if len(profiles) >= HARD_MAX_RUNTIME_PROFILE_COUNT:
            return profiles[:HARD_MAX_RUNTIME_PROFILE_COUNT]
    return profiles


def _normalize_profiles(
    *,
    route_entries: Sequence[Any],
    transport_profiles: Sequence[Any] | None,
    generated_mihomo_artifact: Any,
) -> list[RuntimeAgentTransportProfile]:
    if transport_profiles is not None:
        profiles = [RuntimeAgentTransportProfile.model_validate(item) for item in transport_profiles]
    elif generated_mihomo_artifact is not None:
        profiles = runtime_profiles_from_generated_mihomo(generated_mihomo_artifact)
    else:
        profiles = _profiles_from_route_entries(route_entries)
    return profiles[:HARD_MAX_RUNTIME_PROFILE_COUNT]


def _failure_payload(
    reason: str,
    *,
    expected_count: int,
    actual_count: int,
    details: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    details_payload = {
        "expected_profile_count": expected_count,
        "actual_profile_count": actual_count,
        "hard_max_profile_count": HARD_MAX_RUNTIME_PROFILE_COUNT,
        "links_redacted": True,
    }
    if details is not None:
        details_payload.update(details)
    return {
        "status": "fail",
        "reason": reason,
        "agent_id": None,
        "checks": [
            {
                "check_key": "runtime.transport_profile_matrix.required",
                "check_name": "Runtime transport profile matrix",
                "category": "runtime",
                "status": "fail",
                "severity": "error",
                "target": "runtime-agent",
                "safe_summary": "Runtime profile matrix is outside the bounded internal request contract",
                "details": details_payload,
                "duration_ms": 0,
            }
        ],
    }


def _routes_payload(route_entries: Sequence[Any]) -> list[dict[str, Any]]:
    routes = []
    for entry in route_entries:
        metadata = getattr(entry, "metadata_json", None)
        routes.append(
            {
                "route_key": getattr(entry, "route_key", ""),
                "country_code": getattr(entry, "country_code", ""),
                "expected_modes": list(getattr(entry, "expected_modes", []) or []),
                "metadata": dict(metadata or {}) if isinstance(metadata, dict) else {},
            }
        )
    return routes


def _profile_payload(profiles: Sequence[RuntimeAgentTransportProfile]) -> list[dict[str, Any]]:
    return [profile.model_dump(exclude_none=True) for profile in profiles]


def _credential_values(profiles: Sequence[RuntimeAgentTransportProfile]) -> set[str]:
    values: set[str] = set()
    for profile in profiles:
        values.update(profile.credential_values())
    return values


def _redaction_values(profiles: Sequence[RuntimeAgentTransportProfile], secrets: Sequence[str]) -> set[str]:
    values = _credential_values(profiles)
    values.update(secret for secret in secrets if secret)
    return values


def _redact_response(value: Any, credential_values: set[str], *, key: str | None = None) -> Any:
    if isinstance(value, Mapping):
        redacted: dict[str, Any] = {}
        for child_key, child_value in value.items():
            child_key_str = str(child_key)
            redacted[child_key_str] = _redact_response(child_value, credential_values, key=child_key_str)
        return redacted
    if isinstance(value, list):
        return [_redact_response(item, credential_values, key=key) for item in value]
    if isinstance(value, str):
        if key in SENSITIVE_RESPONSE_KEYS:
            return "<redacted>"
        redacted_value = value
        for secret_value in credential_values:
            redacted_value = redacted_value.replace(secret_value, "<redacted>")
        return redacted_value
    if key in SENSITIVE_RESPONSE_KEYS and value is not None:
        return "<redacted>"
    return value


def _transport_counts(profiles: Sequence[RuntimeAgentTransportProfile]) -> dict[str, int]:
    return {
        "raw": sum(1 for profile in profiles if profile.transport == "raw"),
        "xhttp": sum(1 for profile in profiles if profile.transport == "xhttp"),
    }


def _validate_global_profile_matrix(profiles: Sequence[RuntimeAgentTransportProfile]) -> dict[str, Any] | None:
    counts = _transport_counts(profiles)
    if len(profiles) != EXPECTED_RUNTIME_PROFILE_COUNT:
        return _failure_payload(
            "profile_matrix_count_invalid",
            expected_count=EXPECTED_RUNTIME_PROFILE_COUNT,
            actual_count=len(profiles),
            details={
                "expected_raw_profile_count": EXPECTED_RUNTIME_RAW_PROFILE_COUNT,
                "actual_raw_profile_count": counts["raw"],
                "expected_xhttp_profile_count": EXPECTED_RUNTIME_XHTTP_PROFILE_COUNT,
                "actual_xhttp_profile_count": counts["xhttp"],
            },
        )
    if counts["raw"] != EXPECTED_RUNTIME_RAW_PROFILE_COUNT or counts["xhttp"] != EXPECTED_RUNTIME_XHTTP_PROFILE_COUNT:
        return _failure_payload(
            "profile_matrix_transport_count_invalid",
            expected_count=EXPECTED_RUNTIME_PROFILE_COUNT,
            actual_count=len(profiles),
            details={
                "expected_raw_profile_count": EXPECTED_RUNTIME_RAW_PROFILE_COUNT,
                "actual_raw_profile_count": counts["raw"],
                "expected_xhttp_profile_count": EXPECTED_RUNTIME_XHTTP_PROFILE_COUNT,
                "actual_xhttp_profile_count": counts["xhttp"],
            },
        )
    expected_server_counts = Counter({server: 1 for server in PREMIUM_SMART_RU_RUNTIME_SERVERS})
    raw_server_counts = Counter(profile.server for profile in profiles if profile.transport == "raw")
    xhttp_server_counts = Counter(profile.server for profile in profiles if profile.transport == "xhttp")
    if raw_server_counts != expected_server_counts or xhttp_server_counts != expected_server_counts:
        return _failure_payload(
            "profile_matrix_server_set_invalid",
            expected_count=EXPECTED_RUNTIME_PROFILE_COUNT,
            actual_count=len(profiles),
            details={
                "required_server_count": len(PREMIUM_SMART_RU_RUNTIME_SERVERS),
                "raw_server_matrix_valid": raw_server_counts == expected_server_counts,
                "xhttp_server_matrix_valid": xhttp_server_counts == expected_server_counts,
            },
        )
    return None


def _is_moscow_profile(profile: RuntimeAgentTransportProfile) -> bool:
    return profile.server == PREMIUM_SMART_RU_MOSCOW_SERVER


def _is_spb_profile(profile: RuntimeAgentTransportProfile) -> bool:
    return profile.server == PREMIUM_SMART_RU_SPB_SERVER


def _validate_regional_pair(
    profiles: Sequence[RuntimeAgentTransportProfile],
    *,
    role: RuntimeAgentRole,
) -> dict[str, Any] | None:
    counts = _transport_counts(profiles)
    if len(profiles) == EXPECTED_REGIONAL_TARGET_PROFILE_COUNT and counts["raw"] == 1 and counts["xhttp"] == 1:
        return None
    return _failure_payload(
        f"{role}_profile_split_invalid",
        expected_count=EXPECTED_RUNTIME_PROFILE_COUNT,
        actual_count=EXPECTED_RUNTIME_PROFILE_COUNT,
        details={
            "target_role": role,
            "expected_target_profile_count": EXPECTED_REGIONAL_TARGET_PROFILE_COUNT,
            "actual_target_profile_count": len(profiles),
            "expected_target_raw_profile_count": 1,
            "actual_target_raw_profile_count": counts["raw"],
            "expected_target_xhttp_profile_count": 1,
            "actual_target_xhttp_profile_count": counts["xhttp"],
        },
    )


def _configured_target(
    *,
    role: RuntimeAgentRole,
    url: str,
    secret: str,
    profiles: Sequence[RuntimeAgentTransportProfile],
) -> RuntimeAgentTarget | dict[str, Any] | None:
    if bool(url) != bool(secret):
        return _failure_payload(
            f"{role}_agent_partially_configured",
            expected_count=EXPECTED_RUNTIME_PROFILE_COUNT,
            actual_count=EXPECTED_RUNTIME_PROFILE_COUNT,
            details={"target_role": role, "agent_url_configured": bool(url), "agent_secret_configured": bool(secret)},
        )
    if not url:
        return None
    split_failure = _validate_regional_pair(profiles, role=role)
    if split_failure is not None:
        return split_failure
    return RuntimeAgentTarget(role=role, url=url, secret=secret, profiles=tuple(profiles))


def _runtime_agent_targets(
    *,
    primary_url: str,
    primary_secret: str,
    profiles: Sequence[RuntimeAgentTransportProfile],
) -> list[RuntimeAgentTarget] | dict[str, Any]:
    moscow_profiles = tuple(profile for profile in profiles if _is_moscow_profile(profile))
    spb_profiles = tuple(profile for profile in profiles if _is_spb_profile(profile))
    moscow_config = _configured_target(
        role="moscow",
        url=_agent_url(settings.vpn_test_agent_moscow_url),
        secret=_secret_value(settings.vpn_test_agent_moscow_secret),
        profiles=moscow_profiles,
    )
    if isinstance(moscow_config, dict):
        return moscow_config
    spb_config = _configured_target(
        role="spb",
        url=_agent_url(settings.vpn_test_agent_spb_url),
        secret=_secret_value(settings.vpn_test_agent_spb_secret),
        profiles=spb_profiles,
    )
    if isinstance(spb_config, dict):
        return spb_config

    regional_profiles: set[int] = set()
    targets: list[RuntimeAgentTarget] = []
    if isinstance(moscow_config, RuntimeAgentTarget):
        targets.append(moscow_config)
        regional_profiles.update(id(profile) for profile in moscow_config.profiles)
    if isinstance(spb_config, RuntimeAgentTarget):
        targets.append(spb_config)
        regional_profiles.update(id(profile) for profile in spb_config.profiles)

    primary_profiles = tuple(profile for profile in profiles if id(profile) not in regional_profiles)
    targets.insert(
        0,
        RuntimeAgentTarget(role="primary", url=primary_url, secret=primary_secret, profiles=primary_profiles),
    )
    return targets


def _agent_check_key(role: RuntimeAgentRole, check_key: Any) -> str:
    normalized = str(check_key or "runtime.agent.check").strip() or "runtime.agent.check"
    return f"runtime.agent.{role}.{normalized}"


def _runtime_transport_check_key(profile: RuntimeAgentTransportProfile) -> str:
    location = PREMIUM_SMART_RU_RELEASE_LOCATION_KEY_BY_SERVER[profile.server]
    return f"runtime.transport.{profile.transport}.{location}"


async def _post_runtime_agent(
    *,
    target: RuntimeAgentTarget,
    base_payload: Mapping[str, Any],
    redaction_values: set[str],
) -> tuple[RuntimeAgentRole, dict[str, Any]]:
    payload = dict(base_payload)
    payload["transport_profiles"] = _profile_payload(target.profiles)
    payload["request_scope"] = "full" if len(target.profiles) == EXPECTED_RUNTIME_PROFILE_COUNT else "shard"
    timeout = httpx.Timeout(
        connect=min(5.0, float(settings.vpn_test_agent_timeout_seconds)),
        read=float(settings.vpn_test_agent_timeout_seconds),
        write=10.0,
        pool=5.0,
    )
    async with httpx.AsyncClient(base_url=target.url, timeout=timeout, trust_env=False) as client:
        response = await client.post(
            RUNTIME_AGENT_ENDPOINT,
            json=payload,
            headers={RUNTIME_AGENT_AUTH_HEADER: target.secret},
        )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            data = {"status": "fail", "reason": "agent_invalid_response", "checks": []}
        return target.role, _redact_response(data, redaction_values)


def _combine_agent_payloads(
    responses: Sequence[tuple[RuntimeAgentRole, dict[str, Any]]],
    *,
    profile_counts_by_role: Mapping[RuntimeAgentRole, int],
    profiles_by_role: Mapping[RuntimeAgentRole, Sequence[RuntimeAgentTransportProfile]],
    profiles: Sequence[RuntimeAgentTransportProfile],
    redaction_values: set[str],
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    seen_check_keys: set[str] = set()
    agent_statuses: dict[str, str] = {}
    agent_ids: dict[str, Any] = {}
    for role, data in responses:
        status = str(data.get("status") or "degraded")
        agent_statuses[role] = status
        agent_ids[role] = data.get("agent_id")
        agent_checks = data.get("checks")
        if not isinstance(agent_checks, list) or not agent_checks:
            return _failure_payload(
                "agent_missing_checks",
                expected_count=EXPECTED_RUNTIME_PROFILE_COUNT,
                actual_count=len(profiles),
                details={"target_role": role, "agent_statuses": agent_statuses},
            )
        expected_transport_keys = {_runtime_transport_check_key(profile) for profile in profiles_by_role[role]}
        observed_transport_keys: set[str] = set()
        for item in agent_checks:
            if not isinstance(item, Mapping):
                return _failure_payload(
                    "agent_invalid_check",
                    expected_count=EXPECTED_RUNTIME_PROFILE_COUNT,
                    actual_count=len(profiles),
                    details={"target_role": role, "agent_statuses": agent_statuses},
                )
            check = dict(item)
            source_check_key = str(check.get("check_key") or "").strip()
            if status == "pass" and source_check_key.startswith(("runtime.transport.raw.", "runtime.transport.xhttp.")):
                if source_check_key not in expected_transport_keys:
                    return _failure_payload(
                        "agent_unexpected_transport_check",
                        expected_count=EXPECTED_RUNTIME_PROFILE_COUNT,
                        actual_count=len(profiles),
                        details={"target_role": role},
                    )
                check_key = source_check_key
                observed_transport_keys.add(check_key)
            else:
                check_key = _agent_check_key(role, source_check_key)
            if check_key in seen_check_keys:
                return _failure_payload(
                    "duplicate_agent_check_keys",
                    expected_count=EXPECTED_RUNTIME_PROFILE_COUNT,
                    actual_count=len(profiles),
                    details={"target_role": role, "duplicate_check_key": check_key},
                )
            seen_check_keys.add(check_key)
            check["check_key"] = check_key
            details = check.get("details")
            check["details"] = dict(details) if isinstance(details, Mapping) else {}
            check["details"]["agent_role"] = role
            check["details"]["agent_profile_count"] = profile_counts_by_role.get(role, 0)
            checks.append(check)
        if status == "pass" and observed_transport_keys != expected_transport_keys:
            return _failure_payload(
                "agent_transport_checks_incomplete",
                expected_count=EXPECTED_RUNTIME_PROFILE_COUNT,
                actual_count=len(profiles),
                details={
                    "target_role": role,
                    "expected_transport_check_count": len(expected_transport_keys),
                    "actual_transport_check_count": len(observed_transport_keys),
                },
            )

    checks.append(
        {
            "check_key": "runtime.transport_profile_matrix.required",
            "check_name": "Combined runtime transport profile matrix",
            "category": "runtime",
            "status": "pass",
            "severity": "error",
            "target": "global",
            "safe_summary": "All required runtime transport profiles were assigned to an agent shard",
            "details": {
                "actual_profile_count": len(profiles),
                "actual_raw_count": sum(profile.transport == "raw" for profile in profiles),
                "actual_xhttp_count": sum(profile.transport == "xhttp" for profile in profiles),
                "server_matrix_valid": True,
                "raw_server_matrix_valid": True,
                "xhttp_server_matrix_valid": True,
                "agent_profile_counts": dict(profile_counts_by_role),
            },
            "duration_ms": 0,
        }
    )

    combined_status = "pass" if all(status == "pass" for status in agent_statuses.values()) else "fail"
    payload: dict[str, Any] = {
        "status": combined_status,
        "agent_id": "multi-agent",
        "agent_ids": agent_ids,
        "checks": checks,
        "agent_statuses": agent_statuses,
    }
    if combined_status != "pass":
        payload["reason"] = "runtime_agent_partial_failure"
    return _redact_response(payload, redaction_values)


async def call_runtime_agent(
    *,
    run_id: str,
    suite_key: str,
    mode: str,
    route_entries: Sequence[Any],
    transport_profiles: Sequence[Any] | None = None,
    generated_mihomo_artifact: Any = None,
) -> dict[str, Any]:
    url = _agent_url(settings.vpn_test_agent_url)
    secret = _agent_secret()
    if not url or not secret:
        return {"status": "degraded", "reason": "agent_unavailable", "agent_id": None, "checks": []}
    if transport_profiles is not None and len(transport_profiles) > HARD_MAX_RUNTIME_PROFILE_COUNT:
        return _failure_payload(
            "profile_matrix_too_large",
            expected_count=EXPECTED_RUNTIME_PROFILE_COUNT,
            actual_count=len(transport_profiles),
        )

    profiles = _normalize_profiles(
        route_entries=route_entries,
        transport_profiles=transport_profiles,
        generated_mihomo_artifact=generated_mihomo_artifact,
    )
    if len(profiles) > HARD_MAX_RUNTIME_PROFILE_COUNT:
        return _failure_payload(
            "profile_matrix_too_large",
            expected_count=EXPECTED_RUNTIME_PROFILE_COUNT,
            actual_count=len(profiles),
        )
    matrix_failure = _validate_global_profile_matrix(profiles)
    if matrix_failure is not None:
        return matrix_failure

    payload = {
        "run_id": run_id,
        "suite_key": suite_key,
        "mode": mode,
        "runtime_mode": "proxy-only" if mode == "runtime" else mode,
        "tun_sandbox_requested": False,
        "routes": _routes_payload(route_entries),
        "transport_profiles": _profile_payload(profiles),
    }
    redaction_values = _redaction_values(
        profiles,
        (
            secret,
            _secret_value(settings.vpn_test_agent_moscow_secret),
            _secret_value(settings.vpn_test_agent_spb_secret),
        ),
    )
    targets_or_failure = _runtime_agent_targets(primary_url=url, primary_secret=secret, profiles=profiles)
    if isinstance(targets_or_failure, dict):
        return _redact_response(targets_or_failure, redaction_values)
    if len(targets_or_failure) == 1:
        _, data = await _post_runtime_agent(
            target=targets_or_failure[0],
            base_payload=payload,
            redaction_values=redaction_values,
        )
        return data
    try:
        responses = await asyncio.gather(
            *(
                _post_runtime_agent(target=target, base_payload=payload, redaction_values=redaction_values)
                for target in targets_or_failure
            )
        )
    except httpx.HTTPError as exc:
        return _redact_response(
            _failure_payload(
                "agent_request_failed",
                expected_count=EXPECTED_RUNTIME_PROFILE_COUNT,
                actual_count=len(profiles),
                details={"error_type": type(exc).__name__},
            ),
            redaction_values,
        )
    return _combine_agent_payloads(
        responses,
        profile_counts_by_role={target.role: len(target.profiles) for target in targets_or_failure},
        profiles_by_role={target.role: target.profiles for target in targets_or_failure},
        profiles=profiles,
        redaction_values=redaction_values,
    )
