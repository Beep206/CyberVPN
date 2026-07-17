"""Internal VPN Tester runtime agent."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import ipaddress
import json
import os
import re
import socket
import ssl
import tempfile
from collections import Counter, OrderedDict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter, time
from typing import Any, Literal
from uuid import UUID

import httpx
import structlog
from fastapi import FastAPI, HTTPException, Request, Response, status
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from starlette.datastructures import Headers

logger = structlog.get_logger(__name__)

EXPECTED_PROFILE_COUNT = 8
HARD_MAX_PROFILE_COUNT = 16
EXPECTED_RAW_COUNT = 4
EXPECTED_XHTTP_COUNT = 4
MAX_REQUEST_PROFILE_COUNT = EXPECTED_PROFILE_COUNT
MAX_PROFILE_PROBE_ATTEMPTS = 4
MAX_TASK2_ROUTE_EXPECTATIONS = 64
MAX_REPLAY_NONCES = 4096
MAX_REQUEST_BODY_BYTES = 256 * 1024
MAX_CONCURRENT_RUNTIME_CHECKS = 2
DEFAULT_PROTOCOL_MAX_SKEW_SECONDS = 60
SIGNED_RUNTIME_METHOD = "POST"
SIGNED_RUNTIME_PATH = "/internal/v2/runtime-checks"
SIGNED_RUNTIME_CONTENT_TYPE = "application/json"
GENERATE_204_URL = "https://example.com/"
EXIT_COUNTRY_URL = "https://ipwho.is/"
REQUEST_SECRET_HEADER = "X-VPN-Test-Agent-Secret"  # noqa: S105 - public protocol header name, not a secret.
REQUEST_TIMESTAMP_HEADER = "X-VPN-Test-Timestamp"
REQUEST_NONCE_HEADER = "X-VPN-Test-Nonce"
REQUEST_AUDIENCE_HEADER = "X-VPN-Test-Agent-Audience"
REQUEST_BODY_SHA256_HEADER = "X-VPN-Test-Body-SHA256"
REQUEST_SIGNATURE_HEADER = "X-VPN-Test-Signature"
RESPONSE_TIMESTAMP_HEADER = "X-VPN-Test-Response-Timestamp"
RESPONSE_NONCE_HEADER = "X-VPN-Test-Response-Nonce"
RESPONSE_AUDIENCE_HEADER = "X-VPN-Test-Response-Audience"
RESPONSE_BODY_SHA256_HEADER = "X-VPN-Test-Response-Body-SHA256"
RESPONSE_SIGNATURE_HEADER = "X-VPN-Test-Response-Signature"
PREMIUM_SMART_RU_ENDPOINT_PORTS = {
    "de-relay.cyber-vpn.org": {"raw": 2053, "xhttp": 2083},
    "nl-4.cyber-vpn.org": {"raw": 443, "xhttp": 8443},
    "msk-relay.cyber-vpn.org": {"raw": 2053, "xhttp": 2083},
    "ru-spb-3.cyber-vpn.org": {"raw": 443, "xhttp": 8443},
}
PREMIUM_SMART_RU_ALLOWED_SERVERS = frozenset(PREMIUM_SMART_RU_ENDPOINT_PORTS)
PREMIUM_SMART_RU_LOCATION_KEYS_BY_SERVER = {
    "de-relay.cyber-vpn.org": "de",
    "nl-4.cyber-vpn.org": "nl",
    "msk-relay.cyber-vpn.org": "moscow",
    "ru-spb-3.cyber-vpn.org": "spb",
}
TASK2_SUITE_ID = "premium_spb_de_exceptions_v1"
TASK2_ENDPOINT_SERVER = "spb-exceptions.cyber-vpn.org"
TASK2_ENDPOINT_SERVER_IPV4 = "193.233.91.99"
TASK2_ALLOWED_ENDPOINT_SERVERS = frozenset({TASK2_ENDPOINT_SERVER, TASK2_ENDPOINT_SERVER_IPV4})
TASK2_ENDPOINT_PORTS = {"raw": 4443, "xhttp": 8444}
MAX_TASK2_TCP_PROBE_PAYLOAD_BYTES = 4096
TASK2_TCP_HANDOFF_ATTEMPTS = 5
TASK2_TCP_RESPONSE_WINDOW_SECONDS = 1.5
TASK2_ROUTE_PROBE_CONCURRENCY = 2
TASK2_UDP_PROBE_PAYLOAD = b"\x00"
TASK2_UDP_HANDOFF_ATTEMPTS = 5
TASK2_UDP_RESPONSE_WINDOW_SECONDS = 0.25
TASK2_REQUIRED_ROUTE_PROBE_PAIRS = frozenset(
    {
        ("raw", "tcp"),
        ("raw", "udp"),
        ("xhttp", "tcp"),
        ("xhttp", "udp"),
    }
)
TASK2_BLOCKED_TARGET_NETWORKS = (
    ipaddress.ip_network("45.87.41.146/32"),
    ipaddress.ip_network("2a0d:2787:1b:12f5::/64"),
    ipaddress.ip_network("178.159.94.225/32"),
    ipaddress.ip_network("193.233.91.99/32"),
    ipaddress.ip_network("138.124.115.206/32"),
    ipaddress.ip_network("138.16.140.44/32"),
)
HOST_RE = re.compile(r"^(?=.{1,253}$)(?!-)[A-Za-z0-9.-]+(?<!-)$")
DECIMAL_UNIX_SECONDS_RE = re.compile(r"^(0|[1-9][0-9]{0,15})$")
LOWER_HEX_32_RE = re.compile(r"^[0-9a-f]{32}$")
LOWER_HEX_64_RE = re.compile(r"^[0-9a-f]{64}$")
PUBLIC_KEY_RE = re.compile(r"^[A-Za-z0-9_-]{10,120}$")
SHORT_ID_RE = re.compile(r"^[0-9A-Fa-f]{0,32}$")
SAFE_TOKEN_RE = re.compile(r"^[A-Za-z0-9_.-]{1,120}$")
XHTTP_MODE_RE = re.compile(r"^[a-z0-9_-]{1,32}$")
SAFE_PATH_RE = re.compile(r"^/[A-Za-z0-9._~!$&'()*+,;=:@%/-]{0,127}$")
SECRET_DETAIL_KEYS = frozenset(
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
        "target_ip",
        "targetIp",
        "target_port",
        "targetPort",
    }
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    vpn_test_agent_secret: str = ""
    vpn_test_agent_id: str = "stage1-vpn-test-agent"
    vpn_test_agent_role: Literal["primary", "moscow", "spb"] = "primary"
    vpn_test_agent_legacy_v1_enabled: bool = False
    vpn_test_agent_legacy_v1_secret: str = ""
    vpn_test_agent_tun_enabled: bool = False
    vpn_test_agent_proxy_only_enabled: bool = True
    vpn_test_agent_xray_binary: str = "xray"
    vpn_test_agent_profile_timeout_seconds: float = 20.0
    vpn_test_agent_profile_max_attempts: int = 3
    vpn_test_agent_profile_retry_backoff_seconds: float = 0.75
    vpn_test_agent_xray_start_timeout_seconds: float = 5.0
    vpn_test_agent_http_probe_url: str = GENERATE_204_URL
    vpn_test_agent_exit_country_url: str = EXIT_COUNTRY_URL
    vpn_test_agent_signature_max_skew_seconds: int = DEFAULT_PROTOCOL_MAX_SKEW_SECONDS

    @field_validator("vpn_test_agent_secret", "vpn_test_agent_legacy_v1_secret")
    @classmethod
    def _validate_agent_secret(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            return normalized
        placeholder_markers = (
            "replace",
            "example",
            "test",
            "placeholder",
            "changeme",
            "dummy",
            "local",
            "development",
            "dev-",
            "redacted",
            "your_",
        )
        if len(normalized) < 16 or any(marker in normalized.lower() for marker in placeholder_markers):
            raise ValueError("vpn_test_agent_secret_must_be_non_placeholder")
        return normalized

    @model_validator(mode="after")
    def _validate_legacy_v1_rollout_secret(self) -> Settings:
        if not self.vpn_test_agent_legacy_v1_enabled:
            return self
        if not self.vpn_test_agent_secret:
            raise ValueError("vpn_test_agent_v2_secret_required_during_legacy_rollout")
        if not self.vpn_test_agent_legacy_v1_secret:
            raise ValueError("vpn_test_agent_legacy_v1_secret_required_when_enabled")
        if hmac.compare_digest(self.vpn_test_agent_secret, self.vpn_test_agent_legacy_v1_secret):
            raise ValueError("vpn_test_agent_legacy_v1_secret_must_differ_from_v2_secret")
        return self

    @field_validator("vpn_test_agent_signature_max_skew_seconds")
    @classmethod
    def _validate_signature_max_skew_seconds(cls, value: int) -> int:
        if value < 1 or value > 300:
            raise ValueError("vpn_test_agent_signature_max_skew_seconds_out_of_range")
        return value


settings = Settings()
app = FastAPI(title="CyberVPN VPN Test Agent", docs_url=None, redoc_url=None, openapi_url=None)


@dataclass(frozen=True)
class SignedRequestContext:
    secret: str
    nonce: str
    audience: str


class ReplayNonceCache:
    def __init__(self, *, capacity: int = MAX_REPLAY_NONCES) -> None:
        self._capacity = capacity
        self._entries: OrderedDict[str, float] = OrderedDict()
        self._lock = asyncio.Lock()

    async def mark_seen(self, nonce: str, *, now_seconds: float, ttl_seconds: int) -> bool:
        async with self._lock:
            self._prune_expired_locked(now_seconds)
            if nonce in self._entries:
                return False
            if len(self._entries) >= self._capacity:
                return False
            self._entries[nonce] = now_seconds + ttl_seconds
            return True

    def clear(self) -> None:
        self._entries.clear()

    def _prune_expired_locked(self, now_seconds: float) -> None:
        while self._entries:
            _, expires_at = next(iter(self._entries.items()))
            if expires_at > now_seconds:
                return
            self._entries.popitem(last=False)


# Restart-window replay can only repeat read-only probes; it cannot forge backend evidence because
# responses are bound to the backend's pending nonce. The capacity guard below bounds that residual cost.
_request_replay_cache = ReplayNonceCache()


class RuntimeCheckCapacity:
    def __init__(self, *, capacity: int) -> None:
        self._capacity = capacity
        self._active = 0
        self._lock = asyncio.Lock()

    async def try_acquire(self) -> bool:
        async with self._lock:
            if self._active >= self._capacity:
                return False
            self._active += 1
            return True

    async def release(self) -> None:
        async with self._lock:
            if self._active <= 0:
                raise RuntimeError("runtime_check_capacity_release_without_acquire")
            self._active -= 1

    def clear(self) -> None:
        self._active = 0


_runtime_check_capacity = RuntimeCheckCapacity(capacity=MAX_CONCURRENT_RUNTIME_CHECKS)


class RuntimeRoute(BaseModel):
    model_config = ConfigDict(extra="forbid")

    route_key: str = Field(..., min_length=1, max_length=160)
    country_code: str = Field(default="", max_length=16)
    expected_modes: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RuntimeTransportProfile(BaseModel):
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

    @field_validator("name", "location", "node")
    @classmethod
    def _validate_safe_label(cls, value: str) -> str:
        normalized = value.strip()
        if any(char in normalized for char in ("\r", "\n", "\t")):
            raise ValueError("unsafe_label")
        return normalized

    @field_validator("server", "sni")
    @classmethod
    def _validate_hostname(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not HOST_RE.fullmatch(normalized) or ".." in normalized or "/" in normalized or ":" in normalized:
            raise ValueError("invalid_host")
        return normalized

    @field_validator("server")
    @classmethod
    def _validate_vpn_target(cls, value: str) -> str:
        if value not in PREMIUM_SMART_RU_ALLOWED_SERVERS:
            raise ValueError("vpn_target_not_allowed")
        return value

    @field_validator("uuid")
    @classmethod
    def _validate_uuid(cls, value: str) -> str:
        normalized = value.strip()
        try:
            UUID(normalized)
        except ValueError as exc:
            raise ValueError("invalid_vless_uuid") from exc
        return normalized

    @field_validator("flow")
    @classmethod
    def _validate_flow(cls, value: str) -> str:
        normalized = value.strip()
        if normalized and not SAFE_TOKEN_RE.fullmatch(normalized):
            raise ValueError("invalid_flow")
        return normalized

    @field_validator("public_key")
    @classmethod
    def _validate_public_key(cls, value: str) -> str:
        normalized = value.strip()
        if not PUBLIC_KEY_RE.fullmatch(normalized):
            raise ValueError("invalid_reality_public_key")
        return normalized

    @field_validator("short_id")
    @classmethod
    def _validate_short_id(cls, value: str) -> str:
        normalized = value.strip()
        if not SHORT_ID_RE.fullmatch(normalized):
            raise ValueError("invalid_reality_short_id")
        return normalized

    @field_validator("fingerprint")
    @classmethod
    def _validate_fingerprint(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not SAFE_TOKEN_RE.fullmatch(normalized):
            raise ValueError("invalid_fingerprint")
        return normalized

    @model_validator(mode="after")
    def _validate_transport_specific_fields(self) -> RuntimeTransportProfile:
        expected_ports = PREMIUM_SMART_RU_ENDPOINT_PORTS[self.server]
        if self.network in {"raw", "tcp"}:
            if self.port != expected_ports["raw"]:
                raise ValueError("raw_tcp_profile_port_mismatch")
            if self.flow != "xtls-rprx-vision":
                raise ValueError("raw_tcp_profiles_must_use_vision_flow")
            return self

        if self.port != expected_ports["xhttp"]:
            raise ValueError("xhttp_profile_port_mismatch")
        if not self.xhttp_path or not SAFE_PATH_RE.fullmatch(self.xhttp_path):
            raise ValueError("invalid_xhttp_path")
        if not self.xhttp_mode or not XHTTP_MODE_RE.fullmatch(self.xhttp_mode):
            raise ValueError("invalid_xhttp_mode")
        return self

    @property
    def transport(self) -> str:
        return "xhttp" if self.network == "xhttp" else "raw"


class Task2TransportProfile(BaseModel):
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

    @field_validator("name", "location", "node")
    @classmethod
    def _validate_safe_label(cls, value: str) -> str:
        normalized = value.strip()
        if any(char in normalized for char in ("\r", "\n", "\t")):
            raise ValueError("unsafe_label")
        return normalized

    @field_validator("server", "sni")
    @classmethod
    def _validate_hostname(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not HOST_RE.fullmatch(normalized) or ".." in normalized or "/" in normalized or ":" in normalized:
            raise ValueError("invalid_host")
        return normalized

    @field_validator("server")
    @classmethod
    def _validate_task2_target(cls, value: str) -> str:
        if value not in TASK2_ALLOWED_ENDPOINT_SERVERS:
            raise ValueError("task2_vpn_target_not_allowed")
        return value

    @field_validator("uuid")
    @classmethod
    def _validate_uuid(cls, value: str) -> str:
        normalized = value.strip()
        try:
            UUID(normalized)
        except ValueError as exc:
            raise ValueError("invalid_vless_uuid") from exc
        return normalized

    @field_validator("flow")
    @classmethod
    def _validate_flow(cls, value: str) -> str:
        normalized = value.strip()
        if normalized and not SAFE_TOKEN_RE.fullmatch(normalized):
            raise ValueError("invalid_flow")
        return normalized

    @field_validator("public_key")
    @classmethod
    def _validate_public_key(cls, value: str) -> str:
        normalized = value.strip()
        if not PUBLIC_KEY_RE.fullmatch(normalized):
            raise ValueError("invalid_reality_public_key")
        return normalized

    @field_validator("short_id")
    @classmethod
    def _validate_short_id(cls, value: str) -> str:
        normalized = value.strip()
        if not SHORT_ID_RE.fullmatch(normalized):
            raise ValueError("invalid_reality_short_id")
        return normalized

    @field_validator("fingerprint")
    @classmethod
    def _validate_fingerprint(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not SAFE_TOKEN_RE.fullmatch(normalized):
            raise ValueError("invalid_fingerprint")
        return normalized

    @model_validator(mode="after")
    def _validate_transport_specific_fields(self) -> Task2TransportProfile:
        if self.transport == "raw":
            if self.port != TASK2_ENDPOINT_PORTS["raw"]:
                raise ValueError("task2_raw_profile_port_mismatch")
            if self.flow != "xtls-rprx-vision":
                raise ValueError("task2_raw_profiles_must_use_vision_flow")
            return self

        if self.port != TASK2_ENDPOINT_PORTS["xhttp"]:
            raise ValueError("task2_xhttp_profile_port_mismatch")
        if not self.xhttp_path or not SAFE_PATH_RE.fullmatch(self.xhttp_path):
            raise ValueError("invalid_xhttp_path")
        if not self.xhttp_mode or not XHTTP_MODE_RE.fullmatch(self.xhttp_mode):
            raise ValueError("invalid_xhttp_mode")
        return self

    @property
    def transport(self) -> Literal["raw", "xhttp"]:
        return "xhttp" if self.network == "xhttp" else "raw"


class Task2RouteExpectation(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    expectation_id: str = Field(..., min_length=1, max_length=120)
    route_key: str = Field(..., min_length=1, max_length=160)
    transport: Literal["raw", "xhttp"]
    probe_network: Literal["tcp", "udp"]
    target_ip: str = Field(..., min_length=1, max_length=64)
    target_port: int = Field(..., ge=1, le=65535)
    expected_outbound: Literal["DE_EXCEPTIONS_BRIDGE", "DIRECT", "BLOCK"]
    membership: Literal["member", "non_member"]
    manifest_sha256: str = Field(..., min_length=64, max_length=64)
    route_feed_version: str = Field(..., min_length=1, max_length=120)

    @field_validator("expectation_id", "route_key", "route_feed_version")
    @classmethod
    def _validate_safe_token(cls, value: str) -> str:
        normalized = value.strip()
        if not SAFE_TOKEN_RE.fullmatch(normalized):
            raise ValueError("unsafe_task2_route_token")
        return normalized

    @field_validator("manifest_sha256")
    @classmethod
    def _validate_manifest_sha256(cls, value: str) -> str:
        normalized = value.strip()
        if not LOWER_HEX_64_RE.fullmatch(normalized):
            raise ValueError("invalid_manifest_sha256")
        return normalized

    @field_validator("target_ip")
    @classmethod
    def _validate_target_ip(cls, value: str) -> str:
        normalized = value.strip()
        try:
            parsed = ipaddress.ip_address(normalized)
        except ValueError as exc:
            raise ValueError("task2_target_ip_must_be_literal") from exc
        if (
            not parsed.is_global
            or parsed.is_private
            or parsed.is_loopback
            or parsed.is_link_local
            or parsed.is_multicast
            or parsed.is_unspecified
            or parsed.is_reserved
        ):
            raise ValueError("task2_target_ip_must_be_public")
        if any(parsed in network for network in TASK2_BLOCKED_TARGET_NETWORKS):
            raise ValueError("task2_target_ip_is_management_or_node")
        return parsed.compressed


class RuntimeCheckRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    run_id: str = Field(..., min_length=1, max_length=80)
    suite_key: str = Field(..., min_length=1, max_length=120)
    mode: str = Field(default="runtime", max_length=40)
    runtime_mode: str = Field(default="proxy-only", pattern="^(static|proxy-only|tun-sandbox)$")
    request_scope: Literal["full", "shard"] = Field(
        default="full",
        validation_alias=AliasChoices(
            "request_scope",
            "requestScope",
            "profile_scope",
            "profileScope",
            "runtime_scope",
            "runtimeScope",
            "scope",
        ),
    )
    tun_sandbox_requested: bool = False
    routes: list[RuntimeRoute | Task2RouteExpectation] = Field(default_factory=list, max_length=200)
    transport_profiles: list[RuntimeTransportProfile | Task2TransportProfile] = Field(
        default_factory=list,
        max_length=HARD_MAX_PROFILE_COUNT,
        validation_alias=AliasChoices("transport_profiles", "profiles", "profile_matrix"),
    )

    @model_validator(mode="after")
    def _validate_suite_contract(self) -> RuntimeCheckRequest:
        if self.suite_key == TASK2_SUITE_ID:
            if self.request_scope != "full":
                raise ValueError("task2_requires_full_scope")
            task2_profiles = [
                profile for profile in self.transport_profiles if isinstance(profile, Task2TransportProfile)
            ]
            if len(task2_profiles) != len(self.transport_profiles):
                raise ValueError("task2_requires_task2_profiles")
            if Counter(profile.transport for profile in task2_profiles) != Counter({"raw": 1, "xhttp": 1}):
                raise ValueError("task2_requires_exactly_one_raw_and_one_xhttp_profile")

            task2_routes = [route for route in self.routes if isinstance(route, Task2RouteExpectation)]
            if len(task2_routes) != len(self.routes):
                raise ValueError("task2_requires_route_expectations")
            if not task2_routes:
                raise ValueError("task2_route_expectations_required")
            if len(task2_routes) > MAX_TASK2_ROUTE_EXPECTATIONS:
                raise ValueError("task2_route_expectations_too_large")
            if len({route.expectation_id for route in task2_routes}) != len(task2_routes):
                raise ValueError("task2_duplicate_expectation_id")
            if len({route.route_key for route in task2_routes}) != len(task2_routes):
                raise ValueError("task2_duplicate_route_key")
            route_probe_pairs = {(route.transport, route.probe_network) for route in task2_routes}
            if not TASK2_REQUIRED_ROUTE_PROBE_PAIRS.issubset(route_probe_pairs):
                raise ValueError("task2_route_probe_matrix_incomplete")
            return self

        if any(isinstance(profile, Task2TransportProfile) for profile in self.transport_profiles):
            raise ValueError("task2_profiles_require_task2_suite")
        if any(isinstance(route, Task2RouteExpectation) for route in self.routes):
            raise ValueError("task2_routes_require_task2_suite")
        return self


class RuntimeProbeError(Exception):
    def __init__(self, safe_error_class: str) -> None:
        super().__init__(safe_error_class)
        self.safe_error_class = safe_error_class


@dataclass
class ProfileProbeResult:
    dns_ok: bool = False
    tcp_connect_ok: bool = False
    proxy_handshake_ok: bool = False
    http_probe_ok: bool = False
    exit_country: str | None = None
    latency_ms: int = 0
    attempt_count: int = 1
    safe_error_class: str | None = None

    @property
    def passed(self) -> bool:
        return self.dns_ok and self.tcp_connect_ok and self.proxy_handshake_ok and self.http_probe_ok


@dataclass(frozen=True)
class Task2RouteAttempt:
    expectation_id: str
    route_key: str
    transport: Literal["raw", "xhttp"]
    probe_network: Literal["tcp", "udp"]
    terminal_class: str

    def as_response(self) -> dict[str, str]:
        return {
            "expectation_id": self.expectation_id,
            "route_key": self.route_key,
            "transport": self.transport,
            "probe_network": self.probe_network,
            "terminal_class": self.terminal_class,
        }


def _profile_timeout_seconds() -> float:
    return max(2.0, min(float(settings.vpn_test_agent_profile_timeout_seconds), 60.0))


def _proxy_connect_timeout_seconds(profile_timeout_seconds: float) -> float:
    return min(10.0, profile_timeout_seconds)


def _profile_max_attempts() -> int:
    return max(1, min(int(settings.vpn_test_agent_profile_max_attempts), MAX_PROFILE_PROBE_ATTEMPTS))


def _profile_retry_backoff_seconds() -> float:
    return max(0.0, min(float(settings.vpn_test_agent_profile_retry_backoff_seconds), 5.0))


def _xray_start_timeout_seconds() -> float:
    return max(1.0, min(float(settings.vpn_test_agent_xray_start_timeout_seconds), 15.0))


def _protocol_max_skew_seconds() -> int:
    return int(settings.vpn_test_agent_signature_max_skew_seconds)


def _current_unix_seconds() -> int:
    return int(time())


def _elapsed_ms(started: float) -> int:
    return max(0, int((perf_counter() - started) * 1000))


def _auth_failed() -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated.")


def _require_legacy_secret(secret: str | None) -> None:
    configured = settings.vpn_test_agent_legacy_v1_secret.strip()
    supplied = secret.strip() if secret is not None else ""
    if configured and supplied and hmac.compare_digest(configured, supplied):
        return
    raise _auth_failed()


def _single_header(headers: Headers, name: str) -> str:
    values = headers.getlist(name)
    if len(values) != 1:
        raise _auth_failed()
    value = values[0]
    if value != value.strip():
        raise _auth_failed()
    return value


def _parse_timestamp_header(value: str, *, now_seconds: int, max_skew_seconds: int) -> None:
    if not DECIMAL_UNIX_SECONDS_RE.fullmatch(value):
        raise _auth_failed()
    timestamp = int(value)
    if timestamp < now_seconds - max_skew_seconds or timestamp > now_seconds + max_skew_seconds:
        raise _auth_failed()


def _request_signature(secret: str, timestamp: str, nonce: str, audience: str, body_sha256: str) -> str:
    message = (
        f"v2\n{SIGNED_RUNTIME_METHOD}\n{SIGNED_RUNTIME_PATH}\n\n{SIGNED_RUNTIME_CONTENT_TYPE}\n"
        f"{timestamp}\n{nonce}\n{audience}\n{body_sha256}"
    ).encode("ascii")
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


def _response_signature(
    secret: str,
    status_code: int,
    timestamp: str,
    nonce: str,
    audience: str,
    body_sha256: str,
) -> str:
    message = (
        f"v2-response\n{SIGNED_RUNTIME_METHOD}\n{SIGNED_RUNTIME_PATH}\n{status_code}\n"
        f"{SIGNED_RUNTIME_CONTENT_TYPE}\n{timestamp}\n{nonce}\n{audience}\n{body_sha256}"
    ).encode("ascii")
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


async def _verify_signed_request(request: Request, body: bytes) -> SignedRequestContext:
    headers = request.headers
    secret = settings.vpn_test_agent_secret
    if not secret:
        raise _auth_failed()
    if request.method != SIGNED_RUNTIME_METHOD or request.url.path != SIGNED_RUNTIME_PATH:
        raise _auth_failed()
    if _single_header(headers, "Content-Type") != SIGNED_RUNTIME_CONTENT_TYPE:
        raise _auth_failed()
    now_seconds = _current_unix_seconds()
    max_skew_seconds = _protocol_max_skew_seconds()

    timestamp = _single_header(headers, REQUEST_TIMESTAMP_HEADER)
    _parse_timestamp_header(timestamp, now_seconds=now_seconds, max_skew_seconds=max_skew_seconds)

    nonce = _single_header(headers, REQUEST_NONCE_HEADER)
    if not LOWER_HEX_32_RE.fullmatch(nonce):
        raise _auth_failed()

    audience = _single_header(headers, REQUEST_AUDIENCE_HEADER)
    if audience != settings.vpn_test_agent_role:
        raise _auth_failed()

    body_sha256 = _single_header(headers, REQUEST_BODY_SHA256_HEADER)
    if not LOWER_HEX_64_RE.fullmatch(body_sha256):
        raise _auth_failed()
    expected_body_sha256 = hashlib.sha256(body).hexdigest()
    if not hmac.compare_digest(expected_body_sha256, body_sha256):
        raise _auth_failed()

    signature = _single_header(headers, REQUEST_SIGNATURE_HEADER)
    if not LOWER_HEX_64_RE.fullmatch(signature):
        raise _auth_failed()
    expected_signature = _request_signature(secret, timestamp, nonce, audience, body_sha256)
    if not hmac.compare_digest(expected_signature, signature):
        raise _auth_failed()

    replay_accepted = await _request_replay_cache.mark_seen(
        nonce,
        now_seconds=float(now_seconds),
        ttl_seconds=max_skew_seconds * 2,
    )
    if not replay_accepted:
        raise _auth_failed()

    return SignedRequestContext(secret=secret, nonce=nonce, audience=audience)


def _response_json_bytes(content: dict[str, Any]) -> bytes:
    return json.dumps(content, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


async def _read_bounded_request_body(request: Request) -> bytes:
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > MAX_REQUEST_BODY_BYTES:
            raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="Request too large.")
        body.extend(chunk)
    return bytes(body)


def _signed_json_response(
    content: dict[str, Any],
    context: SignedRequestContext,
    *,
    status_code: int = status.HTTP_200_OK,
) -> Response:
    body = _response_json_bytes(content)
    timestamp = str(_current_unix_seconds())
    body_sha256 = hashlib.sha256(body).hexdigest()
    headers = {
        RESPONSE_TIMESTAMP_HEADER: timestamp,
        RESPONSE_NONCE_HEADER: context.nonce,
        RESPONSE_AUDIENCE_HEADER: context.audience,
        RESPONSE_BODY_SHA256_HEADER: body_sha256,
        RESPONSE_SIGNATURE_HEADER: _response_signature(
            context.secret,
            status_code,
            timestamp,
            context.nonce,
            context.audience,
            body_sha256,
        ),
    }
    return Response(content=body, media_type="application/json", headers=headers, status_code=status_code)


def _check(
    *,
    check_key: str,
    check_name: str,
    status_value: str,
    safe_summary: str,
    details: dict[str, Any] | None = None,
    target: str = "runtime-agent",
    severity: str = "error",
) -> dict[str, Any]:
    return {
        "check_key": check_key,
        "check_name": check_name,
        "category": "runtime",
        "status": status_value,
        "severity": severity,
        "target": target,
        "safe_summary": safe_summary,
        "details": _redact_details(dict(details or {})),
        "duration_ms": 0,
    }


def _redact_details(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            key_str = str(key)
            if key_str in SECRET_DETAIL_KEYS:
                redacted[key_str] = "<redacted>"
            else:
                redacted[key_str] = _redact_details(item)
        return redacted
    if isinstance(value, list):
        return [_redact_details(item) for item in value]
    return value


def _safe_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip().lower()).strip("-")
    return slug[:80] or "profile"


def _location_key(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _profile_matrix_details(
    profiles: list[RuntimeTransportProfile],
    request_scope: Literal["full", "shard"],
) -> dict[str, Any]:
    raw_count = sum(1 for profile in profiles if profile.transport == "raw")
    xhttp_count = sum(1 for profile in profiles if profile.transport == "xhttp")
    profile_count = len(profiles)
    raw_servers = Counter(profile.server for profile in profiles if profile.transport == "raw")
    xhttp_servers = Counter(profile.server for profile in profiles if profile.transport == "xhttp")
    expected_servers = Counter({server: 1 for server in PREMIUM_SMART_RU_ALLOWED_SERVERS})
    if request_scope == "full":
        raw_server_matrix_valid = raw_servers == expected_servers
        xhttp_server_matrix_valid = xhttp_servers == expected_servers
    else:
        raw_server_matrix_valid = all(count == 1 for count in raw_servers.values())
        xhttp_server_matrix_valid = all(count == 1 for count in xhttp_servers.values())
    server_matrix_valid = (
        raw_server_matrix_valid
        and xhttp_server_matrix_valid
        and raw_servers == xhttp_servers
        and set(raw_servers).issubset(PREMIUM_SMART_RU_ALLOWED_SERVERS)
    )
    location_counts: dict[str, dict[str, int]] = {}
    for profile in profiles:
        key = _location_key(profile.location)
        counts = location_counts.setdefault(key, {"raw": 0, "xhttp": 0})
        counts[profile.transport] += 1

    duplicate_location_count = sum(1 for counts in location_counts.values() if counts["raw"] > 1 or counts["xhttp"] > 1)
    one_sided_location_count = sum(
        1
        for counts in location_counts.values()
        if (counts["raw"] == 0 and counts["xhttp"] > 0) or (counts["xhttp"] == 0 and counts["raw"] > 0)
    )
    complete_pair_count = sum(1 for counts in location_counts.values() if counts["raw"] == 1 and counts["xhttp"] == 1)

    details: dict[str, Any] = {
        "request_scope": request_scope,
        "expected_profile_count": EXPECTED_PROFILE_COUNT if request_scope == "full" else None,
        "actual_profile_count": profile_count,
        "expected_raw_count": EXPECTED_RAW_COUNT if request_scope == "full" else None,
        "actual_raw_count": raw_count,
        "expected_xhttp_count": EXPECTED_XHTTP_COUNT if request_scope == "full" else None,
        "actual_xhttp_count": xhttp_count,
        "expected_location_count": EXPECTED_RAW_COUNT if request_scope == "full" else None,
        "actual_location_count": len(location_counts),
        "complete_pair_count": complete_pair_count,
        "duplicate_location_count": duplicate_location_count,
        "one_sided_location_count": one_sided_location_count,
        "server_matrix_valid": server_matrix_valid,
        "raw_server_matrix_valid": raw_server_matrix_valid,
        "xhttp_server_matrix_valid": xhttp_server_matrix_valid,
        "raw_servers": sorted(raw_servers),
        "xhttp_servers": sorted(xhttp_servers),
        "required_servers": sorted(PREMIUM_SMART_RU_ALLOWED_SERVERS) if request_scope == "full" else None,
        "min_profile_count": 2 if request_scope == "shard" else EXPECTED_PROFILE_COUNT,
        "max_profile_count": MAX_REQUEST_PROFILE_COUNT,
        "hard_max_profile_count": HARD_MAX_PROFILE_COUNT,
        "links_redacted": True,
    }
    if request_scope == "shard":
        details["expected_pair_shape"] = "raw+xhttp_per_location"
    return details


def _matrix_error_class(details: dict[str, Any], request_scope: Literal["full", "shard"]) -> str | None:
    actual_profile_count = int(details["actual_profile_count"])
    if actual_profile_count == 0:
        return "profile_matrix_empty"
    if actual_profile_count > MAX_REQUEST_PROFILE_COUNT:
        return "profile_matrix_too_large"
    if int(details["duplicate_location_count"]) > 0:
        return "profile_matrix_duplicate_location_pair"
    if int(details["one_sided_location_count"]) > 0:
        return "profile_matrix_one_sided_location_pair"
    if details["server_matrix_valid"] is not True:
        return "profile_matrix_server_mismatch"
    if request_scope == "shard":
        if actual_profile_count % 2 != 0 or int(details["complete_pair_count"]) * 2 != actual_profile_count:
            return "profile_matrix_incomplete_location_pair"
        return None
    if (
        actual_profile_count != EXPECTED_PROFILE_COUNT
        or int(details["actual_raw_count"]) != EXPECTED_RAW_COUNT
        or int(details["actual_xhttp_count"]) != EXPECTED_XHTTP_COUNT
        or int(details["complete_pair_count"]) != EXPECTED_RAW_COUNT
    ):
        return "profile_matrix_full_count_mismatch"
    return None


def _matrix_check(
    profiles: list[RuntimeTransportProfile],
    request_scope: Literal["full", "shard"],
) -> dict[str, Any] | None:
    details = _profile_matrix_details(profiles, request_scope)
    error_class = _matrix_error_class(details, request_scope)
    if error_class is None:
        return None
    details["safe_error_class"] = error_class
    if request_scope == "shard":
        summary = "Shard runtime profile matrix must contain one or more complete RAW/TCP and XHTTP location pairs"
    else:
        summary = "Full runtime profile matrix must contain exactly four RAW/TCP 443 and four XHTTP 8443 profiles"
    return _check(
        check_key="runtime.transport_profile_matrix.required",
        check_name="Runtime transport profile matrix",
        status_value="fail",
        safe_summary=summary,
        details=details,
    )


def _profile_check(profile: RuntimeTransportProfile, result: ProfileProbeResult) -> dict[str, Any]:
    target = f"{profile.node}:{profile.transport}"
    return {
        "check_key": (
            f"runtime.transport.{profile.transport}.{PREMIUM_SMART_RU_LOCATION_KEYS_BY_SERVER[profile.server]}"
        ),
        "check_name": "Runtime concrete transport profile",
        "category": "runtime",
        "status": "pass" if result.passed else "fail",
        "severity": "error",
        "target": target,
        "safe_summary": "Concrete VLESS Reality profile passed DNS, TCP, proxy handshake, and HTTPS probe"
        if result.passed
        else "Concrete VLESS Reality profile failed a mandatory runtime probe",
        "details": {
            "node": profile.node,
            "location": profile.location,
            "transport": profile.transport,
            "dns_ok": result.dns_ok,
            "tcp_connect_ok": result.tcp_connect_ok,
            "proxy_handshake_ok": result.proxy_handshake_ok,
            "http_probe_ok": result.http_probe_ok,
            "exit_country": result.exit_country,
            "latency_ms": result.latency_ms,
            "attempt_count": result.attempt_count,
            "safe_error_class": result.safe_error_class,
            "credentials_redacted": True,
        },
        "duration_ms": result.latency_ms,
    }


async def _resolve_dns(server: str, port: int, timeout_seconds: float) -> bool:
    loop = asyncio.get_running_loop()
    try:
        await asyncio.wait_for(loop.getaddrinfo(server, port, type=socket.SOCK_STREAM), timeout=timeout_seconds)
    except (OSError, TimeoutError):
        return False
    return True


async def _tcp_connect(server: str, port: int, timeout_seconds: float) -> bool:
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(server, port), timeout=timeout_seconds)
    except (OSError, TimeoutError):
        return False
    writer.close()
    try:
        await writer.wait_closed()
    except OSError:
        pass
    _ = reader
    return True


def _socks_target_bytes(target_ip: str, target_port: int) -> bytes:
    parsed = ipaddress.ip_address(target_ip)
    atyp = b"\x01" if parsed.version == 4 else b"\x04"
    return atyp + parsed.packed + target_port.to_bytes(2, "big")


async def _read_socks_exactly(reader: asyncio.StreamReader, count: int, timeout_seconds: float) -> bytes:
    return await asyncio.wait_for(reader.readexactly(count), timeout=timeout_seconds)


async def _socks5_no_auth(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    timeout_seconds: float,
) -> str | None:
    writer.write(b"\x05\x01\x00")
    await asyncio.wait_for(writer.drain(), timeout=timeout_seconds)
    response = await _read_socks_exactly(reader, 2, timeout_seconds)
    if response != b"\x05\x00":
        return "socks_auth_rejected"
    return None


async def _socks5_reply(
    reader: asyncio.StreamReader,
    timeout_seconds: float,
) -> tuple[str, tuple[str, int] | None]:
    header = await _read_socks_exactly(reader, 4, timeout_seconds)
    if header[0] != 5:
        return "socks_invalid_reply", None
    reply_code = header[1]
    atyp = header[3]
    if atyp == 1:
        raw_address = await _read_socks_exactly(reader, 4, timeout_seconds)
        host = str(ipaddress.IPv4Address(raw_address))
    elif atyp == 4:
        raw_address = await _read_socks_exactly(reader, 16, timeout_seconds)
        host = str(ipaddress.IPv6Address(raw_address))
    elif atyp == 3:
        raw_length = await _read_socks_exactly(reader, 1, timeout_seconds)
        raw_address = await _read_socks_exactly(reader, raw_length[0], timeout_seconds)
        host = raw_address.decode("ascii", errors="ignore")
    else:
        return "socks_invalid_reply", None
    raw_port = await _read_socks_exactly(reader, 2, timeout_seconds)
    endpoint = (host, int.from_bytes(raw_port, "big"))
    if reply_code != 0:
        return "socks_request_rejected", endpoint
    return "socks_request_ok", endpoint


async def _socks5_request(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    *,
    command: int,
    target_ip: str,
    target_port: int,
    timeout_seconds: float,
) -> tuple[str, tuple[str, int] | None]:
    writer.write(b"\x05" + bytes([command]) + b"\x00" + _socks_target_bytes(target_ip, target_port))
    await asyncio.wait_for(writer.drain(), timeout=timeout_seconds)
    return await _socks5_reply(reader, timeout_seconds)


def _task2_tls_client_hello() -> bytes:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    incoming = ssl.MemoryBIO()
    outgoing = ssl.MemoryBIO()
    tls = context.wrap_bio(incoming, outgoing, server_side=False, server_hostname=None)
    try:
        tls.do_handshake()
    except ssl.SSLWantReadError:
        pass

    payload = outgoing.read()
    if not payload or payload[0] != 0x16 or len(payload) > MAX_TASK2_TCP_PROBE_PAYLOAD_BYTES:
        raise RuntimeProbeError("tls_client_hello_generation_failed")
    return payload


async def _socks5_tcp_connect(socks_port: int, target_ip: str, target_port: int, timeout_seconds: float) -> str:
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection("127.0.0.1", socks_port),
            timeout=timeout_seconds,
        )
    except (OSError, TimeoutError):
        return "socks_unavailable"
    try:
        auth_error = await _socks5_no_auth(reader, writer, timeout_seconds)
        if auth_error is not None:
            return auth_error
        terminal_class, _ = await _socks5_request(
            reader,
            writer,
            command=1,
            target_ip=target_ip,
            target_port=target_port,
            timeout_seconds=timeout_seconds,
        )
        if terminal_class == "socks_request_ok":
            writer.write(_task2_tls_client_hello())
            await asyncio.wait_for(writer.drain(), timeout=timeout_seconds)
            try:
                await asyncio.wait_for(
                    reader.read(1),
                    timeout=min(TASK2_TCP_RESPONSE_WINDOW_SECONDS, timeout_seconds),
                )
            except (OSError, TimeoutError):
                pass
            return "tcp_connect_established"
        return terminal_class
    except TimeoutError:
        return "probe_timeout"
    except (OSError, RuntimeError, RuntimeProbeError, asyncio.IncompleteReadError):
        return "probe_io_error"
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except OSError:
            pass


class _UdpProbeProtocol(asyncio.DatagramProtocol):
    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self.response: asyncio.Future[Exception | None] = loop.create_future()
        self.closed: asyncio.Future[Exception | None] = loop.create_future()

    def datagram_received(self, _data: bytes, _address: tuple[Any, ...]) -> None:
        if not self.response.done():
            self.response.set_result(None)

    def error_received(self, exc: Exception) -> None:
        if not self.response.done():
            self.response.set_result(exc)

    def connection_lost(self, exc: Exception | None) -> None:
        if not self.closed.done():
            self.closed.set_result(exc)


async def _send_socks_udp_packet(
    *,
    relay_host: str,
    relay_port: int,
    target_ip: str,
    target_port: int,
    timeout_seconds: float,
) -> str:
    loop = asyncio.get_running_loop()
    packet = b"\x00\x00\x00" + _socks_target_bytes(target_ip, target_port) + TASK2_UDP_PROBE_PAYLOAD
    try:
        relay_address = ipaddress.ip_address(relay_host)
        family = socket.AF_INET6 if relay_address.version == 6 else socket.AF_INET
        endpoint: tuple[Any, ...] = (
            (relay_address.compressed, relay_port, 0, 0)
            if relay_address.version == 6
            else (relay_address.compressed, relay_port)
        )
    except ValueError:
        try:
            resolved = await asyncio.wait_for(
                loop.getaddrinfo(relay_host, relay_port, type=socket.SOCK_DGRAM),
                timeout=timeout_seconds,
            )
        except (OSError, TimeoutError):
            return "probe_io_error"
        if not resolved:
            return "probe_io_error"
        family, _, _, _, endpoint = resolved[0]

    deadline = loop.time() + timeout_seconds
    protocol = _UdpProbeProtocol(loop)
    transport: asyncio.DatagramTransport | None = None
    terminal_class = "udp_datagram_sent"

    def remaining() -> float:
        return max(0.001, deadline - loop.time())

    try:
        created_transport, _ = await asyncio.wait_for(
            loop.create_datagram_endpoint(
                lambda: protocol,
                remote_addr=endpoint,
                family=family,
            ),
            timeout=remaining(),
        )
        transport = created_transport
        transport.sendto(packet)
        try:
            response_error = await asyncio.wait_for(
                protocol.response,
                timeout=min(TASK2_UDP_RESPONSE_WINDOW_SECONDS, remaining()),
            )
            if response_error is not None:
                terminal_class = "probe_io_error"
        except TimeoutError:
            # SOCKS5 UDP relays do not owe the sender an acknowledgement.
            # Backend webhook correlation proves the selected outbound.
            pass
    except (OSError, RuntimeError, TimeoutError):
        terminal_class = "probe_io_error"
    finally:
        if transport is not None:
            transport.close()
            try:
                close_error = await asyncio.wait_for(protocol.closed, timeout=remaining())
            except TimeoutError:
                close_error = TimeoutError()
            if close_error is not None:
                terminal_class = "probe_io_error"
    return terminal_class


async def _socks5_udp_associate(socks_port: int, target_ip: str, target_port: int, timeout_seconds: float) -> str:
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection("127.0.0.1", socks_port),
            timeout=timeout_seconds,
        )
    except (OSError, TimeoutError):
        return "socks_unavailable"
    try:
        auth_error = await _socks5_no_auth(reader, writer, timeout_seconds)
        if auth_error is not None:
            return auth_error
        terminal_class, relay_endpoint = await _socks5_request(
            reader,
            writer,
            command=3,
            target_ip="0.0.0.0",
            target_port=0,
            timeout_seconds=timeout_seconds,
        )
        if terminal_class != "socks_request_ok" or relay_endpoint is None:
            return terminal_class
        relay_host, relay_port = relay_endpoint
        if relay_host in {"0.0.0.0", "::", ""}:
            relay_host = "127.0.0.1"
        return await _send_socks_udp_packet(
            relay_host=relay_host,
            relay_port=relay_port,
            target_ip=target_ip,
            target_port=target_port,
            timeout_seconds=timeout_seconds,
        )
    except TimeoutError:
        return "probe_timeout"
    except (OSError, RuntimeError, UnicodeDecodeError, asyncio.IncompleteReadError):
        return "probe_io_error"
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except OSError:
            pass


def _allocate_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _xray_config(
    profile: RuntimeTransportProfile | Task2TransportProfile,
    socks_port: int,
    *,
    udp_enabled: bool = False,
) -> dict[str, Any]:
    user: dict[str, Any] = {"id": profile.uuid, "encryption": "none"}
    if profile.flow:
        user["flow"] = profile.flow
    stream_settings: dict[str, Any] = {
        "network": profile.network,
        "security": "reality",
        "realitySettings": {
            "serverName": profile.sni,
            "fingerprint": profile.fingerprint,
            "publicKey": profile.public_key,
            "shortId": profile.short_id,
            "spiderX": "/",
        },
    }
    if profile.network == "xhttp":
        stream_settings["xhttpSettings"] = {
            "path": profile.xhttp_path,
            "mode": profile.xhttp_mode,
        }
    return {
        "log": {"loglevel": "warning"},
        "inbounds": [
            {
                "tag": "loopback-socks",
                "listen": "127.0.0.1",
                "port": socks_port,
                "protocol": "socks",
                "settings": {"auth": "noauth", "udp": udp_enabled},
            }
        ],
        "outbounds": [
            {
                "tag": "profile-out",
                "protocol": "vless",
                "settings": {
                    "vnext": [
                        {
                            "address": profile.server,
                            "port": profile.port,
                            "users": [user],
                        }
                    ]
                },
                "streamSettings": stream_settings,
            }
        ],
        "routing": {
            "domainStrategy": "AsIs",
            "rules": [{"type": "field", "inboundTag": ["loopback-socks"], "outboundTag": "profile-out"}],
        },
    }


def _write_xray_config(
    profile: RuntimeTransportProfile | Task2TransportProfile,
    socks_port: int,
    temp_dir: Path,
    *,
    udp_enabled: bool = False,
) -> Path:
    config_path = temp_dir / "xray-config.json"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    with os.fdopen(os.open(config_path, flags, 0o600), "w", encoding="utf-8") as handle:
        json.dump(_xray_config(profile, socks_port, udp_enabled=udp_enabled), handle, separators=(",", ":"))
    os.chmod(config_path, 0o600)
    return config_path


async def _start_xray(config_path: Path) -> asyncio.subprocess.Process:
    return await asyncio.create_subprocess_exec(
        settings.vpn_test_agent_xray_binary,
        "run",
        "-config",
        str(config_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )


async def _wait_for_local_port(port: int, timeout_seconds: float) -> bool:
    deadline = perf_counter() + timeout_seconds
    while perf_counter() < deadline:
        try:
            reader, writer = await asyncio.open_connection("127.0.0.1", port)
        except OSError:
            await asyncio.sleep(0.05)
            continue
        writer.close()
        try:
            await writer.wait_closed()
        except OSError:
            pass
        _ = reader
        return True
    return False


async def _probe_https_generate_204(socks_port: int, timeout_seconds: float) -> tuple[bool, bool, str | None]:
    proxy_url = f"socks5://127.0.0.1:{socks_port}"
    timeout = httpx.Timeout(
        connect=_proxy_connect_timeout_seconds(timeout_seconds),
        read=timeout_seconds,
        write=5.0,
        pool=2.0,
    )
    try:
        async with httpx.AsyncClient(
            proxy=proxy_url, timeout=timeout, follow_redirects=False, trust_env=False
        ) as client:
            response = await client.get(
                str(settings.vpn_test_agent_http_probe_url or GENERATE_204_URL),
                headers={"User-Agent": "CyberVPN-VPN-Test-Agent/1.0"},
            )
    except httpx.ProxyError:
        return False, False, "proxy_handshake_failed"
    except httpx.TimeoutException:
        return False, False, "http_probe_timeout"
    except httpx.HTTPError:
        return False, False, "http_probe_failed"
    status_ok = 200 <= response.status_code < 400
    return True, status_ok, None if status_ok else "http_probe_status"


async def _probe_exit_country(socks_port: int, timeout_seconds: float) -> str | None:
    proxy_url = f"socks5://127.0.0.1:{socks_port}"
    timeout = httpx.Timeout(connect=min(5.0, timeout_seconds), read=min(8.0, timeout_seconds), write=5.0, pool=2.0)
    try:
        async with httpx.AsyncClient(
            proxy=proxy_url, timeout=timeout, follow_redirects=False, trust_env=False
        ) as client:
            response = await client.get(
                str(settings.vpn_test_agent_exit_country_url or EXIT_COUNTRY_URL),
                headers={"User-Agent": "CyberVPN-VPN-Test-Agent/1.0"},
            )
            response.raise_for_status()
    except httpx.HTTPError:
        return None
    try:
        country_code = str(response.json().get("country_code") or "").upper()
    except (AttributeError, ValueError):
        return None
    return country_code if re.fullmatch(r"[A-Z]{2}", country_code) else None


async def _bounded_process_output(process: asyncio.subprocess.Process) -> None:
    try:
        await asyncio.wait_for(process.communicate(), timeout=1.0)
    except (TimeoutError, RuntimeError):
        return


async def _cleanup_process(process: asyncio.subprocess.Process) -> None:
    if process.returncode is None:
        process.terminate()
        try:
            await asyncio.wait_for(process.wait(), timeout=2.0)
        except TimeoutError:
            process.kill()
            await process.wait()
    await _bounded_process_output(process)


async def _run_profile(profile: RuntimeTransportProfile) -> ProfileProbeResult:
    started = perf_counter()
    result = ProfileProbeResult()
    timeout_seconds = _profile_timeout_seconds()
    process: asyncio.subprocess.Process | None = None
    temp_dir: tempfile.TemporaryDirectory[str] | None = None
    try:
        async with asyncio.timeout(timeout_seconds):
            result.dns_ok = await _resolve_dns(profile.server, profile.port, min(3.0, timeout_seconds))
            if not result.dns_ok:
                result.safe_error_class = "dns_failed"
                return result

            result.tcp_connect_ok = await _tcp_connect(profile.server, profile.port, min(5.0, timeout_seconds))
            if not result.tcp_connect_ok:
                result.safe_error_class = "tcp_connect_failed"
                return result

            socks_port = _allocate_loopback_port()
            temp_dir = tempfile.TemporaryDirectory(prefix="cybervpn-vpn-test-agent-")
            config_path = _write_xray_config(profile, socks_port, Path(temp_dir.name))
            process = await _start_xray(config_path)
            if not await _wait_for_local_port(socks_port, _xray_start_timeout_seconds()):
                result.safe_error_class = "xray_start_failed"
                return result

            handshake_ok, http_ok, error_class = await _probe_https_generate_204(socks_port, timeout_seconds)
            result.proxy_handshake_ok = handshake_ok
            result.http_probe_ok = http_ok
            result.safe_error_class = error_class
            if http_ok:
                result.exit_country = await _probe_exit_country(socks_port, timeout_seconds)
            return result
    except TimeoutError:
        result.safe_error_class = "timeout"
        return result
    except (OSError, RuntimeError, RuntimeProbeError) as exc:
        result.safe_error_class = getattr(exc, "safe_error_class", type(exc).__name__)
        return result
    finally:
        result.latency_ms = _elapsed_ms(started)
        if process is not None:
            await _cleanup_process(process)
        if temp_dir is not None:
            temp_dir.cleanup()


async def _run_profile_with_retry(profile: RuntimeTransportProfile) -> ProfileProbeResult:
    final_result = ProfileProbeResult()
    max_attempts = _profile_max_attempts()
    for attempt in range(1, max_attempts + 1):
        final_result = await _run_profile(profile)
        final_result.attempt_count = attempt
        if final_result.passed:
            return final_result
        if attempt < max_attempts:
            await asyncio.sleep(_profile_retry_backoff_seconds() * attempt)
    return final_result


def _task2_profiles(payload: RuntimeCheckRequest) -> list[Task2TransportProfile]:
    profiles = [profile for profile in payload.transport_profiles if isinstance(profile, Task2TransportProfile)]
    return sorted(profiles, key=lambda profile: 0 if profile.transport == "raw" else 1)


def _smart_ru_profiles(payload: RuntimeCheckRequest) -> list[RuntimeTransportProfile]:
    profiles = [profile for profile in payload.transport_profiles if isinstance(profile, RuntimeTransportProfile)]
    if len(profiles) != len(payload.transport_profiles):
        raise RuntimeProbeError("profile_matrix_invalid")
    return profiles


def _task2_route_expectations(payload: RuntimeCheckRequest) -> list[Task2RouteExpectation]:
    return [route for route in payload.routes if isinstance(route, Task2RouteExpectation)]


def _task2_route_attempts_for_terminal(
    expectations: list[Task2RouteExpectation],
    terminal_class: str,
) -> list[Task2RouteAttempt]:
    return _task2_route_attempts_for_terminals(expectations, {}, fallback_terminal=terminal_class)


def _task2_route_attempts_for_terminals(
    expectations: list[Task2RouteExpectation],
    terminal_classes: dict[str, str],
    *,
    fallback_terminal: str,
) -> list[Task2RouteAttempt]:
    return [
        Task2RouteAttempt(
            expectation_id=expectation.expectation_id,
            route_key=expectation.route_key,
            transport=expectation.transport,
            probe_network=expectation.probe_network,
            terminal_class=terminal_classes.get(expectation.expectation_id, fallback_terminal),
        )
        for expectation in expectations
    ]


async def _run_task2_profile_attempts(
    profile: Task2TransportProfile,
    expectations: list[Task2RouteExpectation],
) -> list[Task2RouteAttempt]:
    terminal_classes: dict[str, str] = {}
    base_timeout_seconds = _profile_timeout_seconds()
    tcp_expectations = [expectation for expectation in expectations if expectation.probe_network == "tcp"]
    udp_expectations = [expectation for expectation in expectations if expectation.probe_network == "udp"]
    tcp_batches = (
        (len(tcp_expectations) + TASK2_ROUTE_PROBE_CONCURRENCY - 1) // TASK2_ROUTE_PROBE_CONCURRENCY
    ) * TASK2_TCP_HANDOFF_ATTEMPTS
    udp_batches = (
        (len(udp_expectations) + TASK2_ROUTE_PROBE_CONCURRENCY - 1) // TASK2_ROUTE_PROBE_CONCURRENCY
    ) * TASK2_UDP_HANDOFF_ATTEMPTS
    response_window_budget = (
        tcp_batches * TASK2_TCP_RESPONSE_WINDOW_SECONDS + udp_batches * TASK2_UDP_RESPONSE_WINDOW_SECONDS
    )
    timeout_seconds = min(95.0, max(base_timeout_seconds, 20.0 + response_window_budget))
    process: asyncio.subprocess.Process | None = None
    temp_dir: tempfile.TemporaryDirectory[str] | None = None
    try:
        async with asyncio.timeout(timeout_seconds):
            dns_ok = await _resolve_dns(profile.server, profile.port, min(3.0, timeout_seconds))
            if not dns_ok:
                return _task2_route_attempts_for_terminal(expectations, "dns_failed")

            tcp_ok = await _tcp_connect(profile.server, profile.port, min(5.0, timeout_seconds))
            if not tcp_ok:
                return _task2_route_attempts_for_terminal(expectations, "profile_tcp_connect_failed")

            socks_port = _allocate_loopback_port()
            temp_dir = tempfile.TemporaryDirectory(prefix="cybervpn-vpn-test-agent-")
            config_path = _write_xray_config(profile, socks_port, Path(temp_dir.name), udp_enabled=True)
            process = await _start_xray(config_path)
            if not await _wait_for_local_port(socks_port, _xray_start_timeout_seconds()):
                return _task2_route_attempts_for_terminal(expectations, "xray_start_failed")

            probe_timeout = _proxy_connect_timeout_seconds(timeout_seconds)
            probe_capacity = asyncio.Semaphore(TASK2_ROUTE_PROBE_CONCURRENCY)

            async def probe(expectation: Task2RouteExpectation) -> str:
                async with probe_capacity:
                    if expectation.probe_network == "tcp":
                        return await _socks5_tcp_connect(
                            socks_port,
                            expectation.target_ip,
                            expectation.target_port,
                            probe_timeout,
                        )
                    return await _socks5_udp_associate(
                        socks_port,
                        expectation.target_ip,
                        expectation.target_port,
                        probe_timeout,
                    )

            for _ in range(TASK2_TCP_HANDOFF_ATTEMPTS):
                round_terminals = await asyncio.gather(*(probe(expectation) for expectation in tcp_expectations))
                for expectation, terminal_class in zip(tcp_expectations, round_terminals, strict=True):
                    previous = terminal_classes.get(expectation.expectation_id)
                    if previous != "tcp_connect_established":
                        terminal_classes[expectation.expectation_id] = terminal_class

            for _ in range(TASK2_UDP_HANDOFF_ATTEMPTS):
                round_terminals = await asyncio.gather(*(probe(expectation) for expectation in udp_expectations))
                for expectation, terminal_class in zip(udp_expectations, round_terminals, strict=True):
                    previous = terminal_classes.get(expectation.expectation_id)
                    if previous != "udp_datagram_sent":
                        terminal_classes[expectation.expectation_id] = terminal_class
            return _task2_route_attempts_for_terminals(
                expectations,
                terminal_classes,
                fallback_terminal="probe_io_error",
            )
    except TimeoutError:
        return _task2_route_attempts_for_terminals(
            expectations,
            terminal_classes,
            fallback_terminal="timeout",
        )
    except (OSError, RuntimeError, RuntimeProbeError):
        return _task2_route_attempts_for_terminals(
            expectations,
            terminal_classes,
            fallback_terminal="probe_io_error",
        )
    finally:
        if process is not None:
            await _cleanup_process(process)
        if temp_dir is not None:
            temp_dir.cleanup()


def _task2_contract_check(
    profiles: list[Task2TransportProfile],
    expectations: list[Task2RouteExpectation],
) -> dict[str, Any]:
    return _check(
        check_key="runtime.task2.contract.accepted",
        check_name="Task2 runtime request contract",
        status_value="pass",
        safe_summary="Task2 runtime request contract accepted exactly one RAW and one XHTTP profile",
        details={
            "suite_key": TASK2_SUITE_ID,
            "profile_count": len(profiles),
            "route_expectation_count": len(expectations),
            "max_route_expectations": MAX_TASK2_ROUTE_EXPECTATIONS,
            "raw_profile_count": sum(1 for profile in profiles if profile.transport == "raw"),
            "xhttp_profile_count": sum(1 for profile in profiles if profile.transport == "xhttp"),
            "tcp_route_attempt_count": sum(1 for route in expectations if route.probe_network == "tcp"),
            "udp_route_attempt_count": sum(1 for route in expectations if route.probe_network == "udp"),
            "credentials_redacted": True,
            "target_details_redacted": True,
        },
        severity="info",
    )


def _task2_route_attempt_check(attempts: list[Task2RouteAttempt]) -> dict[str, Any]:
    terminal_counts = Counter(attempt.terminal_class for attempt in attempts)
    return _check(
        check_key="runtime.task2.route_attempts",
        check_name="Task2 route probe attempts",
        status_value="partial",
        safe_summary="Task2 route probes were attempted; backend webhook correlation owns route-selection proof",
        details={
            "route_attempt_count": len(attempts),
            "terminal_classes": sorted(terminal_counts),
            "terminal_class_counts": dict(sorted(terminal_counts.items())),
            "backend_correlation_required": True,
            "credentials_redacted": True,
            "target_details_redacted": True,
        },
        severity="warning",
    )


def _task2_bridge_down_unsupported_check() -> dict[str, Any]:
    return _check(
        check_key="runtime.task2.bridge_down_injection.unsupported",
        check_name="Task2 bridge-down injection",
        status_value="unsupported",
        safe_summary="Bridge-down injection is unsupported by this agent slice and fails closed",
        details={"bridge_down_injection_supported": False, "fail_closed": True},
        severity="warning",
    )


async def _run_task2_runtime_checks(payload: RuntimeCheckRequest) -> dict[str, Any]:
    profiles = _task2_profiles(payload)
    expectations = _task2_route_expectations(payload)
    if payload.runtime_mode == "tun-sandbox" or payload.tun_sandbox_requested:
        checks = [
            _task2_contract_check(profiles, expectations),
            _task2_bridge_down_unsupported_check(),
        ]
        logger.info(
            "vpn_test_agent_task2_bridge_down_unsupported",
            suite_key=payload.suite_key,
            runtime_mode=payload.runtime_mode,
            route_expectation_count=len(expectations),
            status="fail",
        )
        return {
            "status": "fail",
            "agent_id": settings.vpn_test_agent_id,
            "runtime_mode": payload.runtime_mode,
            "tun_sandbox": False,
            "reason": "task2_bridge_down_unsupported",
            "checks": checks,
            "route_attempts": [],
        }

    attempts: list[Task2RouteAttempt] = []
    for profile in profiles:
        profile_expectations = [
            expectation for expectation in expectations if expectation.transport == profile.transport
        ]
        attempts.extend(await _run_task2_profile_attempts(profile, profile_expectations))

    checks = [
        _check(
            check_key="runtime.agent.available",
            check_name="Runtime agent availability",
            status_value="pass",
            safe_summary="Runtime agent accepted the internal proxy-only Task2 request",
            details={"agent_id": settings.vpn_test_agent_id, "process_id": os.getpid()},
            severity="info",
        ),
        _task2_contract_check(profiles, expectations),
        _task2_route_attempt_check(attempts),
        _task2_bridge_down_unsupported_check(),
    ]
    logger.info(
        "vpn_test_agent_task2_runtime_attempts_completed",
        suite_key=payload.suite_key,
        runtime_mode=payload.runtime_mode,
        profile_count=len(profiles),
        route_expectation_count=len(expectations),
        terminal_classes=sorted({attempt.terminal_class for attempt in attempts}),
        status="partial",
    )
    return {
        "status": "partial",
        "agent_id": settings.vpn_test_agent_id,
        "runtime_mode": payload.runtime_mode,
        "tun_sandbox": False,
        "reason": "backend_correlation_required",
        "checks": checks,
        "route_attempts": [attempt.as_response() for attempt in attempts],
    }


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "agent_id": settings.vpn_test_agent_id,
        "agent_role": settings.vpn_test_agent_role,
        "legacy_v1_enabled": settings.vpn_test_agent_legacy_v1_enabled,
        "proxy_only_enabled": settings.vpn_test_agent_proxy_only_enabled,
        "tun_enabled": settings.vpn_test_agent_tun_enabled,
        "xray_configured": bool(settings.vpn_test_agent_xray_binary.strip()),
        "checked_at": datetime.now(UTC).isoformat(),
    }


@app.post("/internal/v1/runtime-checks")
async def legacy_runtime_checks(request: Request) -> dict[str, Any]:
    if not settings.vpn_test_agent_legacy_v1_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")
    secret_values = request.headers.getlist(REQUEST_SECRET_HEADER)
    _require_legacy_secret(secret_values[0] if len(secret_values) == 1 else None)
    body = await _read_bounded_request_body(request)
    try:
        payload = RuntimeCheckRequest.model_validate_json(body)
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid request.") from exc
    if payload.suite_key == TASK2_SUITE_ID:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid request.")
    if not await _runtime_check_capacity.try_acquire():
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Runtime capacity exhausted.")
    try:
        return await _run_runtime_checks(payload)
    finally:
        await _runtime_check_capacity.release()


@app.post(SIGNED_RUNTIME_PATH)
async def runtime_checks(request: Request) -> Response:
    body = await _read_bounded_request_body(request)
    signed_context = await _verify_signed_request(request, body)
    try:
        payload = RuntimeCheckRequest.model_validate_json(body)
    except ValidationError:
        return _signed_json_response(
            {"detail": "Invalid request."},
            signed_context,
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    if not await _runtime_check_capacity.try_acquire():
        return _signed_json_response(
            {"detail": "Runtime capacity exhausted."},
            signed_context,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )
    try:
        return _signed_json_response(await _run_runtime_checks(payload), signed_context)
    finally:
        await _runtime_check_capacity.release()


async def _run_runtime_checks(payload: RuntimeCheckRequest) -> dict[str, Any]:
    if payload.suite_key == TASK2_SUITE_ID:
        if payload.runtime_mode == "proxy-only" and not settings.vpn_test_agent_proxy_only_enabled:
            return {
                "status": "fail",
                "agent_id": settings.vpn_test_agent_id,
                "runtime_mode": payload.runtime_mode,
                "tun_sandbox": False,
                "reason": "proxy_only_disabled",
                "checks": [
                    _check(
                        check_key="runtime.proxy_only.enabled",
                        check_name="Proxy-only runtime enabled",
                        status_value="fail",
                        safe_summary="Task2 proxy-only runtime checks are disabled by environment",
                        severity="error",
                    )
                ],
                "route_attempts": [],
            }
        return await _run_task2_runtime_checks(payload)

    if payload.runtime_mode == "tun-sandbox" and not settings.vpn_test_agent_tun_enabled:
        return {
            "status": "skipped",
            "agent_id": settings.vpn_test_agent_id,
            "runtime_mode": payload.runtime_mode,
            "tun_sandbox": False,
            "reason": "tun_sandbox_disabled",
            "checks": [
                _check(
                    check_key="runtime.tun_sandbox.enabled",
                    check_name="TUN sandbox enabled",
                    status_value="skipped",
                    safe_summary="TUN sandbox runtime checks are disabled by environment",
                    details={"tun_sandbox_requested": payload.tun_sandbox_requested},
                    severity="warning",
                )
            ],
        }
    if payload.runtime_mode == "proxy-only" and not settings.vpn_test_agent_proxy_only_enabled:
        return {
            "status": "degraded",
            "agent_id": settings.vpn_test_agent_id,
            "runtime_mode": payload.runtime_mode,
            "tun_sandbox": False,
            "reason": "proxy_only_disabled",
            "checks": [
                _check(
                    check_key="runtime.proxy_only.enabled",
                    check_name="Proxy-only runtime enabled",
                    status_value="degraded",
                    safe_summary="Proxy-only runtime checks are disabled by environment",
                    severity="warning",
                )
            ],
        }
    smart_ru_profiles = _smart_ru_profiles(payload)
    matrix_failure = _matrix_check(smart_ru_profiles, payload.request_scope)
    if matrix_failure is not None:
        logger.info(
            "vpn_test_agent_runtime_profile_matrix_failed",
            suite_key=payload.suite_key,
            runtime_mode=payload.runtime_mode,
            request_scope=payload.request_scope,
            profile_count=len(smart_ru_profiles),
        )
        return {
            "status": "fail",
            "agent_id": settings.vpn_test_agent_id,
            "runtime_mode": payload.runtime_mode,
            "tun_sandbox": False,
            "reason": "profile_matrix_invalid",
            "checks": [matrix_failure],
        }

    profile_checks = []
    for profile in smart_ru_profiles:
        profile_checks.append(_profile_check(profile, await _run_profile_with_retry(profile)))

    matrix_details = _profile_matrix_details(smart_ru_profiles, payload.request_scope)

    checks = [
        _check(
            check_key="runtime.agent.available",
            check_name="Runtime agent availability",
            status_value="pass",
            safe_summary="Runtime agent accepted the internal proxy-only request",
            details={"agent_id": settings.vpn_test_agent_id, "process_id": os.getpid()},
            severity="info",
        ),
        _check(
            check_key="runtime.transport_profile_matrix.required",
            check_name="Runtime transport profile matrix",
            status_value="pass",
            safe_summary="Runtime profile matrix contains the requested full transport set"
            if payload.request_scope == "full"
            else "Runtime profile matrix contains the requested complete shard transport pairs",
            details=matrix_details,
            severity="info",
        ),
        *profile_checks,
    ]
    response_status = "pass" if all(check["status"] == "pass" for check in checks) else "fail"
    logger.info(
        "vpn_test_agent_runtime_checks_completed",
        suite_key=payload.suite_key,
        runtime_mode=payload.runtime_mode,
        request_scope=payload.request_scope,
        profile_count=len(smart_ru_profiles),
        status=response_status,
    )
    return {
        "status": response_status,
        "agent_id": settings.vpn_test_agent_id,
        "runtime_mode": payload.runtime_mode,
        "tun_sandbox": False,
        "checks": checks,
    }
