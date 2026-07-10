"""Internal VPN Tester runtime agent."""

from __future__ import annotations

import asyncio
import hmac
import json
import os
import re
import socket
import tempfile
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any, Literal
from uuid import UUID

import httpx
import structlog
from fastapi import FastAPI, Header, HTTPException, status
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = structlog.get_logger(__name__)

EXPECTED_PROFILE_COUNT = 8
HARD_MAX_PROFILE_COUNT = 16
EXPECTED_RAW_COUNT = 4
EXPECTED_XHTTP_COUNT = 4
MAX_REQUEST_PROFILE_COUNT = EXPECTED_PROFILE_COUNT
MAX_PROFILE_PROBE_ATTEMPTS = 4
GENERATE_204_URL = "https://example.com/"
EXIT_COUNTRY_URL = "https://ipwho.is/"
PREMIUM_SMART_RU_ALLOWED_SERVERS = frozenset(
    {
        "de-3.cyber-vpn.org",
        "nl-4.cyber-vpn.org",
        "ru-msk-3.cyber-vpn.org",
        "ru-spb-3.cyber-vpn.org",
    }
)
HOST_RE = re.compile(r"^(?=.{1,253}$)(?!-)[A-Za-z0-9.-]+(?<!-)$")
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
    }
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    vpn_test_agent_secret: str = ""
    vpn_test_agent_id: str = "stage1-vpn-test-agent"
    vpn_test_agent_tun_enabled: bool = False
    vpn_test_agent_proxy_only_enabled: bool = True
    vpn_test_agent_xray_binary: str = "xray"
    vpn_test_agent_profile_timeout_seconds: float = 20.0
    vpn_test_agent_profile_max_attempts: int = 3
    vpn_test_agent_profile_retry_backoff_seconds: float = 0.75
    vpn_test_agent_xray_start_timeout_seconds: float = 5.0
    vpn_test_agent_http_probe_url: str = GENERATE_204_URL
    vpn_test_agent_exit_country_url: str = EXIT_COUNTRY_URL

    @field_validator("vpn_test_agent_secret")
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


settings = Settings()
app = FastAPI(title="CyberVPN VPN Test Agent", docs_url=None, redoc_url=None, openapi_url=None)


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
        if self.network in {"raw", "tcp"}:
            if self.port != 443:
                raise ValueError("raw_tcp_profiles_must_use_443")
            if self.flow != "xtls-rprx-vision":
                raise ValueError("raw_tcp_profiles_must_use_vision_flow")
            return self

        if self.port != 8443:
            raise ValueError("xhttp_profiles_must_use_8443")
        if not self.xhttp_path or not SAFE_PATH_RE.fullmatch(self.xhttp_path):
            raise ValueError("invalid_xhttp_path")
        if not self.xhttp_mode or not XHTTP_MODE_RE.fullmatch(self.xhttp_mode):
            raise ValueError("invalid_xhttp_mode")
        return self

    @property
    def transport(self) -> str:
        return "xhttp" if self.network == "xhttp" else "raw"


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
    routes: list[RuntimeRoute] = Field(default_factory=list, max_length=200)
    transport_profiles: list[RuntimeTransportProfile] = Field(
        default_factory=list,
        max_length=HARD_MAX_PROFILE_COUNT,
        validation_alias=AliasChoices("transport_profiles", "profiles", "profile_matrix"),
    )


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


def _elapsed_ms(started: float) -> int:
    return max(0, int((perf_counter() - started) * 1000))


def _require_secret(secret: str | None) -> None:
    configured = settings.vpn_test_agent_secret.strip()
    if configured and secret and hmac.compare_digest(configured, secret.strip()):
        return
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated.")


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
        "check_key": f"runtime.transport.{profile.transport}.{_safe_slug(profile.node)}",
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


def _allocate_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _xray_config(profile: RuntimeTransportProfile, socks_port: int) -> dict[str, Any]:
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
                "settings": {"auth": "noauth", "udp": False},
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


def _write_xray_config(profile: RuntimeTransportProfile, socks_port: int, temp_dir: Path) -> Path:
    config_path = temp_dir / "xray-config.json"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    with os.fdopen(os.open(config_path, flags, 0o600), "w", encoding="utf-8") as handle:
        json.dump(_xray_config(profile, socks_port), handle, separators=(",", ":"))
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


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "agent_id": settings.vpn_test_agent_id,
        "proxy_only_enabled": settings.vpn_test_agent_proxy_only_enabled,
        "tun_enabled": settings.vpn_test_agent_tun_enabled,
        "xray_configured": bool(settings.vpn_test_agent_xray_binary.strip()),
        "checked_at": datetime.now(UTC).isoformat(),
    }


@app.post("/internal/v1/runtime-checks")
async def runtime_checks(
    payload: RuntimeCheckRequest,
    x_vpn_test_agent_secret: str | None = Header(default=None, alias="X-VPN-Test-Agent-Secret"),
) -> dict[str, Any]:
    _require_secret(x_vpn_test_agent_secret)
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

    matrix_failure = _matrix_check(payload.transport_profiles, payload.request_scope)
    if matrix_failure is not None:
        logger.info(
            "vpn_test_agent_runtime_profile_matrix_failed",
            suite_key=payload.suite_key,
            runtime_mode=payload.runtime_mode,
            request_scope=payload.request_scope,
            profile_count=len(payload.transport_profiles),
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
    for profile in payload.transport_profiles:
        profile_checks.append(_profile_check(profile, await _run_profile_with_retry(profile)))

    matrix_details = _profile_matrix_details(payload.transport_profiles, payload.request_scope)

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
        profile_count=len(payload.transport_profiles),
        status=response_status,
    )
    return {
        "status": response_status,
        "agent_id": settings.vpn_test_agent_id,
        "runtime_mode": payload.runtime_mode,
        "tun_sandbox": False,
        "checks": checks,
    }
