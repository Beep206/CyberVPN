#!/usr/bin/env python3
"""Safely prove the Remnawave Torrent Blocker plumbing path without live torrent traffic.

The script is intentionally dry-run by default. In apply mode it temporarily
sets Torrent Blocker includeRuleTags to one caller-supplied harmless synthetic
Task2 rule tag, invokes a caller-supplied safe runtime probe, waits for one new
Torrent Blocker report, then unblocks the observed source IP and restores the
exact original plugin config.

When the selected profile does not already contain the harmless synthetic route
rule, operators may opt into a temporary profile rule mode. That mode snapshots
the exact profile config, inserts one DIRECT rule scoped to the expected
synthetic Xray user/tId and selected inbound tags, then restores the exact
profile config in cleanup.

This proves only the webhook -> nftables -> report enforcement plumbing for the
selected synthetic route tag. It does not prove BitTorrent protocol recognition
or full per-node protocol behavior.
"""

from __future__ import annotations

import argparse
import asyncio
import copy
import hashlib
import hmac
import ipaddress
import json
import math
import os
import re
import secrets
import stat
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx

if __name__ == "__main__" and not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.remnawave.node_plugin_preflight import load_expected_node_plugin  # noqa: E402


DEFAULT_PLUGIN_NAME = "CYBERVPN_PREMIUM_SMART_RU_ABUSE_PROTECTION"
DEFAULT_INTERNAL_HOSTS = ("remnawave", "localhost", "127.0.0.1", "::1")
INTERNAL_HTTP_REMNAWAVE_HOSTS = set(DEFAULT_INTERNAL_HOSTS)
APPLY_CONFIRMATION = "APPLY_SAFE_TORRENT_BLOCKER_SELF_TEST"
NO_LIVE_TRAFFIC_CONFIRMATION = "NO_LIVE_TORRENT_SWARM_TOR_TRAFFIC"
RESTORE_CONFIRMATION = "RESTORE_PLUGIN_CONFIG_AND_UNBLOCK"
REDACTED = "[REDACTED]"
MAX_SYNC_TIMEOUT_SECONDS = 300.0
MAX_REPORT_TIMEOUT_SECONDS = 300.0
MAX_TRIGGER_TIMEOUT_SECONDS = 60.0
MAX_POLL_INTERVAL_SECONDS = 30.0
MAX_REPORT_PAGE_SIZE = 500
MAX_PROBE_EXECUTABLE_BYTES = 64 * 1024 * 1024
MAX_PROBE_MANIFEST_BYTES = 64 * 1024
SAFE_SYNTHETIC_DOMAIN = "task2-synthetic.invalid"
SAFE_SYNTHETIC_DOMAIN_MATCHERS = {
    f"domain:{SAFE_SYNTHETIC_DOMAIN}",
    f"full:{SAFE_SYNTHETIC_DOMAIN}",
}
SAFE_SYNTHETIC_OUTBOUNDS = {"direct"}
ALLOWED_SYNTHETIC_RULE_KEYS = {
    "domain",
    "inboundTag",
    "network",
    "outboundTag",
    "ruleTag",
    "type",
    "user",
}
PRODUCTION_DENIED_HOSTS = {"prod-app-1", "45.87.41.146"}
PRODUCTION_DENIED_DOMAIN_SUFFIXES = ("cyber-vpn.net",)
PRODUCTION_DENIED_NETWORKS = (ipaddress.ip_network("2a0d:2787:1b:12f5::/64"),)
SAFE_APPLY_ENV_VAR = "CYBERVPN_SAFE_TORRENT_BLOCKER_ENV"
PRODUCTION_SYNTHETIC_ENV_VALUE = "production-synthetic"
PRODUCTION_SYNTHETIC_MODE = "production_synthetic"
CONTROL_PLANE_SOURCE_DENIED_IPS = {ipaddress.ip_address("45.87.41.146")}
CONTROL_PLANE_SOURCE_DENIED_NETWORKS = (
    *PRODUCTION_DENIED_NETWORKS,
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
)
SAFE_SYNTHETIC_DESTINATION_NETWORKS = tuple(
    ipaddress.ip_network(value)
    for value in (
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16",
        "127.0.0.0/8",
        "fc00::/7",
        "fe80::/10",
        "::1/128",
    )
)
SAFE_PROBE_EXECUTABLES = {
    "cybervpn-safe-absence",
    "cybervpn-safe-probe",
    "safe-absence",
    "safe-probe",
}
FORBIDDEN_PROBE_EXECUTABLES = {
    "aria2c",
    "deluge",
    "qbittorrent",
    "qbittorrent-nox",
    "tor",
    "torsocks",
    "transmission-cli",
    "transmission-daemon",
    "transmission-remote",
    "webtorrent",
}
SAFE_TAG_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,160}$")
SAFE_SCOPE_VALUE_RE = re.compile(r"^[A-Za-z0-9_.:@-]{1,160}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
DOMAIN_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9-])(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,63}(?![A-Za-z0-9-])",
    re.IGNORECASE,
)
SENSITIVE_KEY_RE = re.compile(
    r"(token|secret|password|authorization|cookie|url|email|source|ip|address)",
    re.IGNORECASE,
)
TORRENT_CATALOG_DOMAINS = {
    "1337x.to",
    "eztv.re",
    "kinozal.tv",
    "limetorrents.lol",
    "nnmclub.to",
    "rutracker.org",
    "rutor.info",
    "thepiratebay.org",
    "torrentdownload.info",
    "torrentgalaxy.to",
    "yts.mx",
}
TORRENT_PORT_MARKERS = {"6881", "6889", "51413", "21413", "17417", "37305"}
TOR_BLOCK_MARKERS = {
    ".onion",
    "bittorrent",
    "magnet:",
    "torproject.org",
    "tor-exit",
    "tor-relay",
    "geoip:tor",
    "geosite:tor",
}
PROBE_ENV_ALLOWLIST = {
    "comspec",
    "lang",
    "lc_all",
    "pathext",
    "systemroot",
    "temp",
    "tmp",
    "tmpdir",
    "tz",
    "windir",
}
PROBE_MANIFEST_SCHEMA = "cybervpn.safe_probe_manifest.v1"
REPORT_RULE_TAG_FIELDS = ("ruleTag", "routingRuleTag", "matchedRuleTag")
APPROVED_PROBE_ROOTS = (Path("/opt/cybervpn/safe-probes"),)
APPROVED_PROBE_MANIFEST_PATH = Path("/etc/cybervpn/safe-torrent-blocker-probes.json")
REDACTION_KEY = secrets.token_bytes(32)


class SelfTestError(RuntimeError):
    def __init__(
        self,
        code: str,
        *,
        phase: str,
        cause_class: str | None = None,
        recovery_source_ip: str | None = None,
    ) -> None:
        super().__init__(code)
        self.code = code
        self.phase = phase
        self.cause_class = cause_class
        self.recovery_source_ip = recovery_source_ip


class SelfTestFailed(RuntimeError):
    def __init__(self, evidence: dict[str, Any]) -> None:
        super().__init__(
            str(evidence.get("failure", {}).get("code", "self_test_failed"))
        )
        self.evidence = evidence


class RemnawaveApi:
    def __init__(
        self,
        base_url: str,
        token: str,
        *,
        allowed_hosts: Sequence[str],
        trusted_proxy_headers: bool = False,
    ) -> None:
        _validate_remnawave_url(base_url, allowed_hosts)
        _validate_trusted_proxy_headers(base_url, trusted_proxy_headers, allowed_hosts)
        normalized = base_url.rstrip("/").removesuffix("/api")
        headers = {"Authorization": f"Bearer {token}"}
        if trusted_proxy_headers:
            headers.update(
                {
                    "X-Forwarded-Proto": "https",
                    "X-Forwarded-For": "127.0.0.1",
                }
            )
        self._client = httpx.AsyncClient(
            base_url=normalized,
            headers=headers,
            timeout=httpx.Timeout(20.0, connect=5.0, read=15.0, write=10.0, pool=5.0),
            trust_env=False,
        )

    async def request(self, method: str, path: str, **kwargs: Any) -> Any:
        normalized = path if path.startswith("/api/") else f"/api/{path.lstrip('/')}"
        response = await self._client.request(method, normalized, **kwargs)
        response.raise_for_status()
        if not response.content.strip():
            return {}
        data = response.json()
        if isinstance(data, dict) and set(data) == {"response"}:
            return data["response"]
        return data

    async def close(self) -> None:
        await self._client.aclose()


def _validate_remnawave_url(base_url: str, allowed_hosts: Sequence[str]) -> None:
    parsed = urlsplit(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise SelfTestError("invalid_remnawave_url", phase="preflight")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise SelfTestError("unsafe_remnawave_url", phase="preflight")
    if parsed.path.rstrip("/") not in {"", "/api"}:
        raise SelfTestError("unsupported_remnawave_url_path", phase="preflight")
    hostname = parsed.hostname.casefold()
    if hostname in PRODUCTION_DENIED_HOSTS or _host_matches_denied_suffix(
        hostname, PRODUCTION_DENIED_DOMAIN_SUFFIXES
    ):
        raise SelfTestError("production_remnawave_host_denied", phase="preflight")
    try:
        host_ip = ipaddress.ip_address(hostname)
    except ValueError:
        host_ip = None
    if host_ip is not None and any(
        host_ip in network for network in PRODUCTION_DENIED_NETWORKS
    ):
        raise SelfTestError("production_remnawave_host_denied", phase="preflight")
    allowed = {host.casefold() for host in allowed_hosts}
    if hostname not in allowed:
        raise SelfTestError("remnawave_host_not_allowed", phase="preflight")
    if parsed.scheme == "http" and hostname not in DEFAULT_INTERNAL_HOSTS:
        raise SelfTestError("external_plaintext_remnawave_url", phase="preflight")


def _host_matches_denied_suffix(hostname: str, suffixes: Sequence[str]) -> bool:
    return any(
        hostname == suffix or hostname.endswith(f".{suffix}") for suffix in suffixes
    )


def _validate_trusted_proxy_headers(
    base_url: str, enabled: bool, allowed_hosts: Sequence[str]
) -> None:
    if not enabled:
        return
    parsed = urlsplit(base_url)
    hostname = (parsed.hostname or "").casefold()
    allowed = {host.casefold() for host in allowed_hosts}
    if hostname not in allowed:
        raise SelfTestError("remnawave_host_not_allowed", phase="preflight")
    if hostname not in INTERNAL_HTTP_REMNAWAVE_HOSTS:
        raise SelfTestError(
            "trusted_proxy_headers_require_internal_host", phase="preflight"
        )


def _require_internal_operator_remnawave_host(base_url: str) -> None:
    hostname = (urlsplit(base_url).hostname or "").casefold()
    if hostname not in INTERNAL_HTTP_REMNAWAVE_HOSTS:
        raise SelfTestError(
            "safe_operator_requires_internal_remnawave_host",
            phase="preflight",
        )


def _collection(data: Any, key: str) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        value = data.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        records = data.get("records")
        if key == "records" and isinstance(records, list):
            return [item for item in records if isinstance(item, dict)]
    return []


def _json_hash(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def _text_hash(value: str | bytes | None) -> str | None:
    if value is None:
        return None
    raw = value if isinstance(value, bytes) else value.encode("utf-8", "replace")
    return hashlib.sha256(raw).hexdigest()


def _sensitive_hash(value: str | bytes | None) -> str | None:
    if value is None:
        return None
    raw = value if isinstance(value, bytes) else value.encode("utf-8", "replace")
    return hmac.new(REDACTION_KEY, raw, hashlib.sha256).hexdigest()


def _sanitize_for_evidence(value: Any, key_name: str = "") -> Any:
    if isinstance(value, Mapping):
        sanitized: dict[str, Any] = {}
        for key, child in value.items():
            text_key = str(key)
            if text_key.casefold().endswith("sha256"):
                sanitized[text_key] = _sanitize_for_evidence(child, text_key)
            elif SENSITIVE_KEY_RE.search(text_key):
                sanitized[text_key] = _redacted_hash(child)
            else:
                sanitized[text_key] = _sanitize_for_evidence(child, text_key)
        return sanitized
    if isinstance(value, list):
        return [_sanitize_for_evidence(item, key_name) for item in value]
    if not key_name.casefold().endswith("sha256") and SENSITIVE_KEY_RE.search(key_name):
        return _redacted_hash(value)
    if isinstance(value, str) and _looks_sensitive_string(value):
        return _redacted_hash(value)
    return value


def _redacted_hash(value: Any) -> dict[str, str | bool | None]:
    normalized = "" if value is None else str(value)
    return {"redacted": True, "sha256": _sensitive_hash(normalized)}


def _looks_sensitive_string(value: str) -> bool:
    lowered = value.casefold()
    if "://" in value or "@" in value:
        return True
    if re.search(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", value):
        return True
    return "bearer " in lowered or "secret" in lowered or "token" in lowered


def _validate_rule_tag(tag: str) -> None:
    if not SAFE_TAG_RE.fullmatch(tag):
        raise SelfTestError("invalid_synthetic_rule_tag", phase="preflight")
    lowered = tag.casefold()
    if "task2" not in lowered or "synthetic" not in lowered:
        raise SelfTestError(
            "synthetic_rule_tag_must_be_task2_synthetic", phase="preflight"
        )


def _run_scoped_rule_tag(base_tag: str) -> str:
    suffix = secrets.token_hex(16)
    candidate = f"{base_tag}:{suffix}"
    if len(candidate) > 160:
        raise SelfTestError(
            "synthetic_rule_tag_too_long_for_run_nonce",
            phase="preflight",
        )
    _validate_rule_tag(candidate)
    return candidate


def _validate_temporary_profile_rule_args(args: argparse.Namespace) -> None:
    if not args.temporary_profile_rule:
        return
    if len(args.node_uuid or []) != 1:
        raise SelfTestError(
            "temporary_profile_rule_requires_exactly_one_node", phase="preflight"
        )
    if not args.profile_inbound_tag:
        raise SelfTestError("profile_inbound_tag_required", phase="preflight")
    if len(args.profile_inbound_tag) != len(set(args.profile_inbound_tag)):
        raise SelfTestError("duplicate_profile_inbound_tag", phase="preflight")
    if not args.expected_xray_user:
        raise SelfTestError("expected_xray_user_required", phase="preflight")
    if not args.expected_xray_tid:
        raise SelfTestError("expected_xray_tid_required", phase="preflight")
    if args.expected_xray_user != args.expected_xray_tid:
        raise SelfTestError("expected_xray_user_must_equal_tid", phase="preflight")
    for value in [
        *args.profile_inbound_tag,
        args.expected_xray_user,
        args.expected_xray_tid,
    ]:
        if not SAFE_SCOPE_VALUE_RE.fullmatch(value):
            raise SelfTestError(
                "unsafe_temporary_profile_rule_scope_value", phase="preflight"
            )


def _parse_json_object(
    raw: str | None, *, code: str, phase: str
) -> dict[str, Any] | None:
    if raw is None:
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SelfTestError(code, phase=phase, cause_class=type(exc).__name__) from exc
    if not isinstance(parsed, dict):
        raise SelfTestError(code, phase=phase)
    return parsed


def _parse_command_json(
    raw: str | None,
    *,
    required: bool,
    phase: str,
    require_synthetic_target: bool = False,
) -> list[str] | None:
    if raw is None:
        if required:
            raise SelfTestError("trigger_command_required", phase=phase)
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SelfTestError(
            "invalid_command_json", phase=phase, cause_class=type(exc).__name__
        ) from exc
    if (
        not isinstance(parsed, list)
        or not parsed
        or not all(isinstance(item, str) and item for item in parsed)
    ):
        raise SelfTestError("invalid_command_json", phase=phase)
    _validate_safe_probe_command(
        parsed,
        phase=phase,
        require_synthetic_target=require_synthetic_target,
    )
    return parsed


def _validate_safe_probe_command(
    command: Sequence[str],
    *,
    phase: str,
    require_synthetic_target: bool = False,
) -> None:
    executable = Path(command[0]).name.casefold().removesuffix(".exe")
    if executable in FORBIDDEN_PROBE_EXECUTABLES:
        raise SelfTestError("unsafe_probe_executable", phase=phase)
    if executable not in SAFE_PROBE_EXECUTABLES:
        raise SelfTestError("probe_executable_not_allowed", phase=phase)
    text = " ".join(command).casefold()
    if any(marker in text for marker in TOR_BLOCK_MARKERS):
        raise SelfTestError("unsafe_probe_mentions_forbidden_traffic", phase=phase)
    if ".torrent" in text or "peer_id=" in text or "announce" in text:
        raise SelfTestError("unsafe_probe_mentions_forbidden_traffic", phase=phase)
    if any(domain in text for domain in TORRENT_CATALOG_DOMAINS):
        raise SelfTestError("unsafe_probe_mentions_torrent_catalog", phase=phase)
    if any(
        re.search(rf"(?<!\d){re.escape(port_marker)}(?!\d)", text)
        for port_marker in TORRENT_PORT_MARKERS
    ):
        raise SelfTestError("unsafe_probe_mentions_torrent_port", phase=phase)
    if require_synthetic_target:
        _validate_synthetic_probe_target(command, phase=phase)


def _validate_synthetic_probe_target(command: Sequence[str], *, phase: str) -> None:
    exact_arguments = ["--target", f"http://{SAFE_SYNTHETIC_DOMAIN}"]
    if list(command[1:]) != exact_arguments:
        raise SelfTestError(
            "probe_target_must_be_exact_safe_synthetic_url",
            phase=phase,
        )
    argument_text = " ".join(command[1:]).casefold()
    domains = {
        match.group(0).strip(".").casefold()
        for match in DOMAIN_TOKEN_RE.finditer(argument_text)
    }
    if SAFE_SYNTHETIC_DOMAIN not in domains:
        raise SelfTestError("safe_synthetic_target_required", phase=phase)
    if domains != {SAFE_SYNTHETIC_DOMAIN}:
        raise SelfTestError("probe_target_must_be_safe_synthetic_domain", phase=phase)
    for value in re.findall(r"\b[a-z][a-z0-9+.-]*://[^\s]+", argument_text):
        parsed = urlsplit(value)
        if (
            parsed.scheme != "http"
            or (parsed.hostname or "").casefold() != SAFE_SYNTHETIC_DOMAIN
            or parsed.username
            or parsed.password
        ):
            raise SelfTestError(
                "probe_target_must_be_safe_synthetic_domain",
                phase=phase,
            )


def _validate_posix_approved_artifact(
    path: Path,
    stat_result: os.stat_result,
    *,
    executable: bool,
    phase: str,
) -> None:
    if os.name == "nt":
        return
    mode = stat.S_IMODE(stat_result.st_mode)
    current_uid = _effective_uid()
    if stat_result.st_uid not in {0, current_uid}:
        raise SelfTestError("probe_artifact_owner_not_approved", phase=phase)
    if mode & 0o222:
        raise SelfTestError("probe_artifact_must_be_read_only", phase=phase)
    if executable and not mode & 0o111:
        raise SelfTestError("probe_executable_not_executable", phase=phase)
    if path.parent.stat().st_mode & 0o022:
        raise SelfTestError("probe_artifact_parent_is_writable", phase=phase)


def _approved_probe_root(resolved: Path, *, phase: str) -> Path:
    for configured_root in APPROVED_PROBE_ROOTS:
        try:
            if configured_root.is_symlink():
                continue
            root = configured_root.resolve(strict=True)
        except OSError:
            continue
        if not root.is_dir() or not resolved.is_relative_to(root):
            continue
        root_stat = root.stat()
        if os.name != "nt":
            if root_stat.st_uid not in {0, _effective_uid()}:
                raise SelfTestError(
                    "approved_probe_root_owner_not_approved", phase=phase
                )
            if root_stat.st_mode & 0o022:
                raise SelfTestError("approved_probe_root_is_writable", phase=phase)
        return root
    raise SelfTestError("probe_executable_outside_approved_root", phase=phase)


def _effective_uid() -> int:
    getter = getattr(os, "geteuid", None)
    return int(getter()) if callable(getter) else -1


def _approved_probe_manifest_hash(resolved: Path, *, phase: str) -> str:
    manifest_path = APPROVED_PROBE_MANIFEST_PATH
    if not manifest_path.is_absolute() or manifest_path.is_symlink():
        raise SelfTestError("probe_manifest_path_invalid", phase=phase)
    try:
        manifest_stat = manifest_path.stat()
        if (
            not manifest_path.is_file()
            or manifest_stat.st_size <= 0
            or manifest_stat.st_size > MAX_PROBE_MANIFEST_BYTES
        ):
            raise SelfTestError("probe_manifest_invalid", phase=phase)
        _validate_posix_approved_artifact(
            manifest_path,
            manifest_stat,
            executable=False,
            phase=phase,
        )
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except SelfTestError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SelfTestError(
            "probe_manifest_unavailable",
            phase=phase,
            cause_class=type(exc).__name__,
        ) from exc
    if not isinstance(payload, dict) or set(payload) != {"schema", "helpers"}:
        raise SelfTestError("probe_manifest_invalid", phase=phase)
    if payload.get("schema") != PROBE_MANIFEST_SCHEMA:
        raise SelfTestError("probe_manifest_schema_mismatch", phase=phase)
    helpers = payload.get("helpers")
    if not isinstance(helpers, dict):
        raise SelfTestError("probe_manifest_invalid", phase=phase)
    approved_hash = helpers.get(str(resolved))
    if not isinstance(approved_hash, str) or not SHA256_RE.fullmatch(
        approved_hash.casefold()
    ):
        raise SelfTestError("probe_executable_not_in_approved_manifest", phase=phase)
    return approved_hash.casefold()


def _file_sha256(path: Path, *, phase: str) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as artifact_file:
            for chunk in iter(lambda: artifact_file.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise SelfTestError(
            "probe_executable_unavailable",
            phase=phase,
            cause_class=type(exc).__name__,
        ) from exc
    return digest.hexdigest()


def _validated_pinned_probe_command(
    command: Sequence[str],
    expected_sha256: str | None,
    *,
    phase: str,
    require_synthetic_target: bool = False,
) -> tuple[list[str], str]:
    _validate_safe_probe_command(
        command,
        phase=phase,
        require_synthetic_target=require_synthetic_target,
    )
    executable = Path(command[0])
    if not executable.is_absolute():
        raise SelfTestError(
            "probe_executable_absolute_path_required",
            phase=phase,
        )
    if executable.is_symlink():
        raise SelfTestError("probe_executable_symlink_denied", phase=phase)
    try:
        resolved = executable.resolve(strict=True)
        stat_result = resolved.stat()
    except OSError as exc:
        raise SelfTestError(
            "probe_executable_unavailable",
            phase=phase,
            cause_class=type(exc).__name__,
        ) from exc
    if (
        not resolved.is_file()
        or stat_result.st_size <= 0
        or stat_result.st_size > MAX_PROBE_EXECUTABLE_BYTES
    ):
        raise SelfTestError("probe_executable_invalid", phase=phase)
    _approved_probe_root(resolved, phase=phase)
    _validate_posix_approved_artifact(
        resolved,
        stat_result,
        executable=True,
        phase=phase,
    )
    normalized_expected = (expected_sha256 or "").strip().casefold()
    if not SHA256_RE.fullmatch(normalized_expected):
        raise SelfTestError("probe_executable_sha256_required", phase=phase)
    manifest_sha256 = _approved_probe_manifest_hash(resolved, phase=phase)
    if not hmac.compare_digest(manifest_sha256, normalized_expected):
        raise SelfTestError("probe_executable_manifest_sha256_mismatch", phase=phase)
    before_identity = (
        stat_result.st_dev,
        stat_result.st_ino,
        stat_result.st_size,
        stat_result.st_mtime_ns,
    )
    actual_sha256 = _file_sha256(resolved, phase=phase)
    after_stat = resolved.stat()
    after_identity = (
        after_stat.st_dev,
        after_stat.st_ino,
        after_stat.st_size,
        after_stat.st_mtime_ns,
    )
    if before_identity != after_identity:
        raise SelfTestError("probe_artifact_changed_during_validation", phase=phase)
    if not hmac.compare_digest(actual_sha256, normalized_expected):
        raise SelfTestError("probe_executable_sha256_mismatch", phase=phase)
    validated = [str(resolved), *command[1:]]
    _validate_safe_probe_command(
        validated,
        phase=phase,
        require_synthetic_target=require_synthetic_target,
    )
    return validated, actual_sha256


def _require_apply_confirmations(args: argparse.Namespace) -> str:
    if not args.apply:
        return "dry_run"
    safe_environment = os.environ.get(SAFE_APPLY_ENV_VAR, "").strip().casefold()
    if safe_environment != PRODUCTION_SYNTHETIC_ENV_VALUE:
        raise SelfTestError(
            "production_synthetic_environment_required", phase="preflight"
        )
    expected = {
        "confirm_apply": APPLY_CONFIRMATION,
        "confirm_no_live_traffic": NO_LIVE_TRAFFIC_CONFIRMATION,
        "confirm_restore": RESTORE_CONFIRMATION,
    }
    for attr, value in expected.items():
        if getattr(args, attr) != value:
            raise SelfTestError(f"missing_{attr}", phase="preflight")
    if not args.node_uuid:
        raise SelfTestError("node_uuid_required", phase="preflight")
    if not args.expected_source_ip:
        raise SelfTestError("expected_source_ip_required", phase="preflight")
    if not all(
        (args.expected_user_uuid, args.expected_username, args.expected_action_user_id)
    ):
        raise SelfTestError("complete_expected_identity_required", phase="preflight")
    trigger_command = _parse_command_json(
        args.trigger_command_json,
        required=True,
        phase="preflight",
        require_synthetic_target=True,
    )
    assert trigger_command is not None
    _validated_pinned_probe_command(
        trigger_command,
        args.trigger_executable_sha256,
        phase="preflight",
        require_synthetic_target=True,
    )
    absence_command = _parse_command_json(
        args.absence_check_command_json,
        required=False,
        phase="preflight",
    )
    if absence_command is not None:
        _validated_pinned_probe_command(
            absence_command,
            args.absence_check_executable_sha256,
            phase="preflight",
        )
    _require_production_synthetic_mode(args)
    return PRODUCTION_SYNTHETIC_MODE


def _require_production_synthetic_mode(args: argparse.Namespace) -> None:
    if not args.temporary_profile_rule:
        raise SelfTestError(
            "production_synthetic_requires_temporary_profile_rule",
            phase="preflight",
        )
    if len(args.node_uuid or []) != 1:
        raise SelfTestError(
            "production_synthetic_requires_exactly_one_node",
            phase="preflight",
        )
    if len(args.profile_inbound_tag or []) != 1:
        raise SelfTestError(
            "production_synthetic_requires_exactly_one_inbound",
            phase="preflight",
        )
    _require_internal_operator_remnawave_host(args.remnawave_url)
    _validate_non_control_plane_source_ip(args.expected_source_ip)
    if not args.expected_destination_ip:
        raise SelfTestError("expected_destination_ip_required", phase="preflight")
    _validate_safe_synthetic_destination_ip(args.expected_destination_ip)
    if not isinstance(args.expected_destination_port, int) or not (
        1 <= args.expected_destination_port <= 65535
    ):
        raise SelfTestError("invalid_expected_destination_port", phase="preflight")


def _validate_non_control_plane_source_ip(value: str | None) -> None:
    if not value:
        raise SelfTestError("expected_source_ip_required", phase="preflight")
    ip = ipaddress.ip_address(_normalize_ip(value))
    if ip in CONTROL_PLANE_SOURCE_DENIED_IPS or any(
        ip in network for network in CONTROL_PLANE_SOURCE_DENIED_NETWORKS
    ):
        raise SelfTestError(
            "production_synthetic_source_ip_must_not_be_control_plane",
            phase="preflight",
        )
    if ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_unspecified:
        raise SelfTestError(
            "production_synthetic_source_ip_must_not_be_control_plane",
            phase="preflight",
        )


def _validate_safe_synthetic_destination_ip(value: str) -> None:
    destination = ipaddress.ip_address(_normalize_ip(value))
    if not any(
        destination in network for network in SAFE_SYNTHETIC_DESTINATION_NETWORKS
    ):
        raise SelfTestError(
            "production_synthetic_destination_must_be_internal",
            phase="preflight",
        )


def _require_token() -> str:
    token = os.environ.get("REMNAWAVE_TOKEN") or os.environ.get("REMNAWAVE_API_TOKEN")
    if not token:
        raise SelfTestError("remnawave_token_required", phase="preflight")
    return token


def _validate_numeric_bounds(args: argparse.Namespace) -> None:
    _validate_float_range(
        args.sync_timeout_seconds,
        code="invalid_sync_timeout_seconds",
        minimum=0.0,
        maximum=MAX_SYNC_TIMEOUT_SECONDS,
        allow_zero=False,
    )
    _validate_float_range(
        args.report_timeout_seconds,
        code="invalid_report_timeout_seconds",
        minimum=0.0,
        maximum=MAX_REPORT_TIMEOUT_SECONDS,
        allow_zero=False,
    )
    _validate_float_range(
        args.trigger_timeout_seconds,
        code="invalid_trigger_timeout_seconds",
        minimum=0.0,
        maximum=MAX_TRIGGER_TIMEOUT_SECONDS,
        allow_zero=False,
    )
    _validate_float_range(
        args.sync_poll_interval_seconds,
        code="invalid_sync_poll_interval_seconds",
        minimum=0.0,
        maximum=MAX_POLL_INTERVAL_SECONDS,
        allow_zero=True,
    )
    _validate_float_range(
        args.report_poll_interval_seconds,
        code="invalid_report_poll_interval_seconds",
        minimum=0.0,
        maximum=MAX_POLL_INTERVAL_SECONDS,
        allow_zero=True,
    )
    if (
        not isinstance(args.report_page_size, int)
        or args.report_page_size < 1
        or args.report_page_size > MAX_REPORT_PAGE_SIZE
    ):
        raise SelfTestError("invalid_report_page_size", phase="preflight")


def _validate_float_range(
    value: float,
    *,
    code: str,
    minimum: float,
    maximum: float,
    allow_zero: bool,
) -> None:
    if not isinstance(value, int | float) or not math.isfinite(float(value)):
        raise SelfTestError(code, phase="preflight")
    numeric = float(value)
    if numeric < minimum or numeric > maximum or (numeric == 0 and not allow_zero):
        raise SelfTestError(code, phase="preflight")


def _plugin_config(plugin: Mapping[str, Any]) -> dict[str, Any]:
    config = plugin.get("pluginConfig")
    if not isinstance(config, dict):
        raise SelfTestError("plugin_config_missing", phase="preflight")
    torrent_blocker = config.get("torrentBlocker")
    if not isinstance(torrent_blocker, dict):
        raise SelfTestError("torrent_blocker_config_missing", phase="preflight")
    return config


def _plugin_uuid(plugin: Mapping[str, Any]) -> str:
    value = plugin.get("uuid")
    if not isinstance(value, str) or not value:
        raise SelfTestError("plugin_uuid_missing", phase="preflight")
    return value


def _profile_config(profile: Mapping[str, Any]) -> dict[str, Any]:
    config = profile.get("config")
    if not isinstance(config, dict):
        raise SelfTestError("profile_config_missing", phase="preflight")
    return config


def _profile_uuid(profile: Mapping[str, Any]) -> str:
    value = profile.get("uuid")
    if not isinstance(value, str) or not value:
        raise SelfTestError("profile_uuid_missing", phase="preflight")
    return value


def _plugin_config_with_include_rule_tags(
    original: Mapping[str, Any], tag: str
) -> dict[str, Any]:
    updated = copy.deepcopy(dict(original))
    torrent_blocker = updated.get("torrentBlocker")
    if not isinstance(torrent_blocker, dict):
        raise SelfTestError("torrent_blocker_config_missing", phase="preflight")
    torrent_blocker["includeRuleTags"] = [tag]
    return updated


def _assert_only_include_rule_tags_changed(
    original: Mapping[str, Any],
    updated: Mapping[str, Any],
) -> None:
    comparable_original = copy.deepcopy(dict(original))
    comparable_updated = copy.deepcopy(dict(updated))
    original_tb = comparable_original.get("torrentBlocker")
    updated_tb = comparable_updated.get("torrentBlocker")
    if not isinstance(original_tb, dict) or not isinstance(updated_tb, dict):
        raise SelfTestError("torrent_blocker_config_missing", phase="preflight")
    original_tb.pop("includeRuleTags", None)
    updated_tb.pop("includeRuleTags", None)
    if comparable_original != comparable_updated:
        raise SelfTestError("plugin_config_payload_not_preserved", phase="preflight")


async def _load_plugin(api: RemnawaveApi, plugin_name: str) -> dict[str, Any]:
    plugins = _collection(await api.request("GET", "/node-plugins"), "nodePlugins")
    plugin = await load_expected_node_plugin(
        api.request, plugins, expected_plugin_name=plugin_name
    )
    if not isinstance(plugin, dict):
        raise SelfTestError("plugin_not_found", phase="preflight")
    return plugin


def _selected_nodes(
    nodes: Sequence[dict[str, Any]], node_uuids: Sequence[str]
) -> list[dict[str, Any]]:
    expected = set(node_uuids)
    found = [node for node in nodes if str(node.get("uuid") or "") in expected]
    found_ids = {str(node.get("uuid") or "") for node in found}
    if found_ids != expected:
        raise SelfTestError("selected_node_missing", phase="preflight")
    return found


def _validate_selected_nodes(nodes: Sequence[dict[str, Any]], plugin_uuid: str) -> None:
    for node in nodes:
        if node.get("activePluginUuid") != plugin_uuid:
            raise SelfTestError("selected_node_plugin_mismatch", phase="preflight")
        if node.get("isConnected") is not True:
            raise SelfTestError("selected_node_not_connected", phase="preflight")
        if node.get("isDisabled") is True:
            raise SelfTestError("selected_node_disabled", phase="preflight")


def _active_config_profile_uuid(node: Mapping[str, Any]) -> str | None:
    config_profile = node.get("configProfile")
    if isinstance(config_profile, Mapping):
        value = config_profile.get("activeConfigProfileUuid")
        if isinstance(value, str) and value:
            return value
    value = node.get("activeConfigProfileUuid")
    return value if isinstance(value, str) and value else None


def _node_runtime_state(node: Mapping[str, Any], *, phase: str) -> dict[str, Any]:
    node_uuid = node.get("uuid")
    last_status_change = node.get("lastStatusChange")
    if not isinstance(node_uuid, str) or not node_uuid:
        raise SelfTestError("node_runtime_uuid_missing", phase=phase)
    if not isinstance(last_status_change, str) or not last_status_change:
        raise SelfTestError("node_runtime_marker_missing", phase=phase)
    return {
        "nodeUuid": node_uuid,
        "lastStatusChange": last_status_change,
        "isConnected": node.get("isConnected") is True,
        "isConnecting": node.get("isConnecting") is True,
        "isDisabled": node.get("isDisabled") is True,
        "activePluginUuid": node.get("activePluginUuid"),
        "activeProfileUuid": _active_config_profile_uuid(node),
    }


def _node_runtime_is_ready(state: Mapping[str, Any]) -> bool:
    return (
        state.get("isConnected") is True
        and state.get("isConnecting") is False
        and state.get("isDisabled") is False
    )


async def _fetch_node_runtime_state(
    api: RemnawaveApi,
    *,
    node_uuid: str,
    profile_uuid: str,
    plugin_uuid: str,
    phase: str,
) -> dict[str, Any]:
    nodes = _collection(await api.request("GET", "/nodes"), "nodes")
    matches = [node for node in nodes if node.get("uuid") == node_uuid]
    if len(matches) != 1:
        raise SelfTestError("node_runtime_lookup_mismatch", phase=phase)
    state = _node_runtime_state(matches[0], phase=phase)
    if state["activePluginUuid"] != plugin_uuid:
        raise SelfTestError("node_runtime_plugin_mismatch", phase=phase)
    if state["activeProfileUuid"] != profile_uuid:
        raise SelfTestError("node_runtime_profile_mismatch", phase=phase)
    return state


async def _capture_ready_node_runtime_state(
    api: RemnawaveApi,
    *,
    node_uuid: str,
    profile_uuid: str,
    plugin_uuid: str,
    phase: str,
) -> dict[str, Any]:
    state = await _fetch_node_runtime_state(
        api,
        node_uuid=node_uuid,
        profile_uuid=profile_uuid,
        plugin_uuid=plugin_uuid,
        phase=phase,
    )
    if not _node_runtime_is_ready(state):
        raise SelfTestError("node_runtime_not_ready", phase=phase)
    return state


async def _poll_node_runtime_transition(
    api: RemnawaveApi,
    *,
    before: Mapping[str, Any],
    profile_uuid: str,
    plugin_uuid: str,
    timeout_seconds: float,
    interval_seconds: float,
    timeout_code: str,
    phase: str,
) -> tuple[int, dict[str, Any], bool]:
    deadline = time.monotonic() + timeout_seconds
    attempts = 0
    saw_not_ready = False
    while True:
        attempts += 1
        current = await _fetch_node_runtime_state(
            api,
            node_uuid=str(before["nodeUuid"]),
            profile_uuid=profile_uuid,
            plugin_uuid=plugin_uuid,
            phase=phase,
        )
        ready = _node_runtime_is_ready(current)
        if not ready:
            saw_not_ready = True
        marker_changed = current["lastStatusChange"] != before["lastStatusChange"]
        if ready and (marker_changed or saw_not_ready):
            return attempts, current, saw_not_ready
        if time.monotonic() >= deadline:
            raise SelfTestError(timeout_code, phase=phase)
        await asyncio.sleep(interval_seconds)


def _node_runtime_transition_evidence(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    *,
    attempts: int,
    saw_not_ready: bool,
) -> dict[str, Any]:
    return {
        "status": "observed",
        "pollAttempts": attempts,
        "nodeUuidSha256": _text_hash(str(before["nodeUuid"])),
        "beforeMarkerSha256": _text_hash(str(before["lastStatusChange"])),
        "afterMarkerSha256": _text_hash(str(after["lastStatusChange"])),
        "markerChanged": before["lastStatusChange"] != after["lastStatusChange"],
        "transientNotReadyObserved": saw_not_ready,
        "finalConnected": after["isConnected"] is True,
        "finalConnecting": after["isConnecting"] is True,
    }


async def _prepare_temporary_profile_rule(
    api: RemnawaveApi,
    nodes: Sequence[dict[str, Any]],
    args: argparse.Namespace,
) -> dict[str, Any]:
    if len(nodes) != 1:
        raise SelfTestError(
            "temporary_profile_rule_requires_exactly_one_node", phase="preflight"
        )
    profile_uuid = _active_config_profile_uuid(nodes[0])
    if not profile_uuid:
        raise SelfTestError("selected_node_active_profile_missing", phase="preflight")
    profile = await api.request("GET", f"/config-profiles/{profile_uuid}")
    if not isinstance(profile, dict):
        raise SelfTestError("profile_detail_invalid", phase="preflight")
    if _profile_uuid(profile) != profile_uuid:
        raise SelfTestError("profile_uuid_mismatch", phase="preflight")
    original_config = copy.deepcopy(_profile_config(profile))
    planned_config = _profile_config_with_temporary_rule(original_config, args)
    return {
        "nodeUuid": str(nodes[0]["uuid"]),
        "profileUuid": profile_uuid,
        "profileName": profile.get("name")
        if isinstance(profile.get("name"), str)
        else None,
        "originalConfig": original_config,
        "plannedConfig": planned_config,
        "evidence": {
            "mode": "temporary_profile_rule",
            "selectedProfiles": 1,
            "selectedNodes": 1,
            "profileUuidSha256": _text_hash(profile_uuid),
            "originalConfigSha256": _json_hash(original_config),
            "plannedConfigSha256": _json_hash(planned_config),
            "preStateHashBackupCaptured": True,
            "temporaryRule": {
                "ruleTagSha256": _text_hash(args.synthetic_rule_tag),
                "domain": f"full:{SAFE_SYNTHETIC_DOMAIN}",
                "network": "tcp",
                "outboundTag": "DIRECT",
                "inboundTagCount": len(args.profile_inbound_tag),
                "expectedXrayUserSha256": _sensitive_hash(args.expected_xray_user),
                "expectedXrayTidSha256": _sensitive_hash(args.expected_xray_tid),
            },
        },
    }


def _profile_config_with_temporary_rule(
    original: Mapping[str, Any], args: argparse.Namespace
) -> dict[str, Any]:
    _require_profile_inbound_tags(original, args.profile_inbound_tag)
    if any(
        str(rule.get("ruleTag") or "") == args.synthetic_rule_tag
        for rule in _routing_rules(original)
    ):
        raise SelfTestError(
            "temporary_profile_rule_tag_already_exists", phase="preflight"
        )
    updated = copy.deepcopy(dict(original))
    rule = _temporary_profile_rule(args)
    _validate_harmless_synthetic_rule(rule)
    rules = _mutable_routing_rules(updated)
    insert_index = _temporary_rule_insert_index(rules)
    rules.insert(insert_index, rule)
    _assert_exactly_one_profile_rule_added(original, updated, rule, insert_index)
    _assert_temporary_rule_precedes_catch_all(updated, args.synthetic_rule_tag)
    return updated


def _require_profile_inbound_tags(
    config: Mapping[str, Any], selected_tags: Sequence[str]
) -> None:
    available = {
        str(inbound.get("tag") or "")
        for inbound in config.get("inbounds", [])
        if isinstance(inbound, Mapping) and inbound.get("tag")
    }
    if not available:
        raise SelfTestError("profile_inbounds_missing", phase="preflight")
    if not set(selected_tags).issubset(available):
        raise SelfTestError("selected_profile_inbound_tag_missing", phase="preflight")


def _temporary_profile_rule(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "type": "field",
        "ruleTag": args.synthetic_rule_tag,
        "inboundTag": list(args.profile_inbound_tag),
        "domain": [f"full:{SAFE_SYNTHETIC_DOMAIN}"],
        "network": "tcp",
        "user": [args.expected_xray_tid],
        "outboundTag": "DIRECT",
    }


def _mutable_routing_rules(config: dict[str, Any]) -> list[dict[str, Any]]:
    routing = config.get("routing")
    if routing is None:
        routing = {}
        config["routing"] = routing
    if not isinstance(routing, dict):
        raise SelfTestError("profile_routing_invalid", phase="preflight")
    rules = routing.get("rules")
    if rules is None:
        rules = []
        routing["rules"] = rules
    if not isinstance(rules, list):
        raise SelfTestError("profile_routing_rules_invalid", phase="preflight")
    return rules


def _assert_exactly_one_profile_rule_added(
    original: Mapping[str, Any],
    updated: Mapping[str, Any],
    rule: Mapping[str, Any],
    insert_index: int,
) -> None:
    expected = copy.deepcopy(dict(original))
    _mutable_routing_rules(expected).insert(insert_index, copy.deepcopy(dict(rule)))
    if updated != expected:
        raise SelfTestError("profile_config_payload_not_preserved", phase="preflight")


def _temporary_rule_insert_index(rules: Sequence[Mapping[str, Any]]) -> int:
    index = 0
    while index < len(rules) and _is_block_guard_rule(rules[index]):
        index += 1
    return index


def _is_block_guard_rule(rule: Mapping[str, Any]) -> bool:
    return str(rule.get("outboundTag") or "").casefold() == "block"


def _assert_temporary_rule_precedes_catch_all(
    config: Mapping[str, Any], tag: str
) -> None:
    rules = _routing_rules(config)
    temp_index = next(
        (index for index, rule in enumerate(rules) if rule.get("ruleTag") == tag),
        None,
    )
    if temp_index is None:
        raise SelfTestError("temporary_profile_rule_missing", phase="preflight")
    if any(not _is_block_guard_rule(rule) for rule in rules[:temp_index]):
        raise SelfTestError(
            "temporary_profile_rule_inserted_after_non_guard", phase="preflight"
        )
    for index, rule in enumerate(rules):
        if index <= temp_index:
            continue
        if _is_catch_all_rule(rule):
            return
    if any(_is_catch_all_rule(rule) for rule in rules[:temp_index]):
        raise SelfTestError("temporary_profile_rule_after_catch_all", phase="preflight")


def _is_catch_all_rule(rule: Mapping[str, Any]) -> bool:
    if rule.get("domain") or rule.get("ip") or rule.get("protocol"):
        return False
    if rule.get("port") or rule.get("sourcePort") or rule.get("network"):
        return False
    if rule.get("user") or rule.get("inboundTag"):
        return False
    return bool(rule.get("outboundTag"))


async def _validate_synthetic_rule_exists(
    api: RemnawaveApi,
    nodes: Sequence[dict[str, Any]],
    tag: str,
) -> dict[str, int]:
    checked_profiles: set[str] = set()
    matching_rules = 0
    for node in nodes:
        profile_uuid = _active_config_profile_uuid(node)
        if not profile_uuid or profile_uuid in checked_profiles:
            continue
        checked_profiles.add(profile_uuid)
        profile = await api.request("GET", f"/config-profiles/{profile_uuid}")
        config = profile.get("config") if isinstance(profile, dict) else None
        rules = _routing_rules(config)
        for rule in rules:
            if str(rule.get("ruleTag") or "") == tag:
                _validate_harmless_synthetic_rule(rule)
                matching_rules += 1
    if matching_rules == 0:
        raise SelfTestError("synthetic_rule_tag_not_found", phase="preflight")
    return {"profilesChecked": len(checked_profiles), "matchingRules": matching_rules}


def _routing_rules(config: Any) -> list[dict[str, Any]]:
    if not isinstance(config, Mapping):
        return []
    routing = config.get("routing")
    if not isinstance(routing, Mapping):
        return []
    rules = routing.get("rules")
    if not isinstance(rules, list):
        return []
    return [rule for rule in rules if isinstance(rule, dict)]


def _as_sequence(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _validate_harmless_synthetic_rule(rule: Mapping[str, Any]) -> None:
    protocols = {str(item).casefold() for item in _as_sequence(rule.get("protocol"))}
    processes = {str(item).casefold() for item in _as_sequence(rule.get("process"))}
    domains = {str(item).casefold() for item in _as_sequence(rule.get("domain"))}
    networks = {str(item).casefold() for item in _as_sequence(rule.get("network"))}
    ports = {str(item).casefold() for item in _as_sequence(rule.get("port"))}
    outbound = str(rule.get("outboundTag") or "").casefold()
    text = json.dumps(rule, sort_keys=True, default=str).casefold()
    if set(rule) - ALLOWED_SYNTHETIC_RULE_KEYS:
        raise SelfTestError("synthetic_rule_has_unsupported_fields", phase="preflight")
    if not domains or not domains.issubset(SAFE_SYNTHETIC_DOMAIN_MATCHERS):
        raise SelfTestError("synthetic_rule_must_use_safe_target", phase="preflight")
    if outbound not in SAFE_SYNTHETIC_OUTBOUNDS:
        raise SelfTestError("synthetic_rule_must_use_safe_outbound", phase="preflight")
    if networks and networks != {"tcp"}:
        raise SelfTestError("synthetic_rule_must_use_tcp_only", phase="preflight")
    if "bittorrent" in protocols:
        raise SelfTestError(
            "synthetic_rule_uses_bittorrent_protocol", phase="preflight"
        )
    if any("torrent" in item for item in processes):
        raise SelfTestError("synthetic_rule_uses_torrent_process", phase="preflight")
    if any(marker in text for marker in TOR_BLOCK_MARKERS):
        raise SelfTestError(
            "synthetic_rule_mentions_forbidden_traffic", phase="preflight"
        )
    if any(
        port_marker in port for port in ports for port_marker in TORRENT_PORT_MARKERS
    ):
        raise SelfTestError("synthetic_rule_uses_torrent_port", phase="preflight")
    if any(_domain_matches_catalog(domain) for domain in domains):
        raise SelfTestError("synthetic_rule_matches_torrent_catalog", phase="preflight")


def _domain_matches_catalog(value: str) -> bool:
    normalized = value.strip().casefold()
    for prefix in ("domain:", "full:"):
        normalized = normalized.removeprefix(prefix)
    if normalized.startswith("keyword:"):
        keyword = normalized.removeprefix("keyword:").strip()
        return not keyword or any(
            keyword in domain for domain in TORRENT_CATALOG_DOMAINS
        )
    if normalized.startswith("regexp:"):
        pattern = normalized.removeprefix("regexp:").strip()
        if not pattern or len(pattern) > 512:
            return True
        try:
            return any(
                re.search(pattern, domain, flags=re.IGNORECASE)
                for domain in TORRENT_CATALOG_DOMAINS
            )
        except re.error:
            return True
    return normalized in TORRENT_CATALOG_DOMAINS


async def _patch_plugin_config(
    api: RemnawaveApi, plugin_uuid: str, config: Mapping[str, Any]
) -> None:
    await api.request(
        "PATCH",
        "/node-plugins",
        json={"uuid": plugin_uuid, "pluginConfig": copy.deepcopy(dict(config))},
    )


async def _patch_profile_config(
    api: RemnawaveApi,
    profile_uuid: str,
    profile_name: str | None,
    config: Mapping[str, Any],
) -> None:
    payload: dict[str, Any] = {
        "uuid": profile_uuid,
        "config": copy.deepcopy(dict(config)),
    }
    if profile_name:
        payload["name"] = profile_name
    await api.request("PATCH", "/config-profiles", json=payload)


async def _fetch_plugin_config(api: RemnawaveApi, plugin_uuid: str) -> dict[str, Any]:
    detail = await api.request("GET", f"/node-plugins/{plugin_uuid}")
    if not isinstance(detail, dict):
        raise SelfTestError("plugin_detail_invalid", phase="restore")
    return _plugin_config(detail)


async def _fetch_profile_config(api: RemnawaveApi, profile_uuid: str) -> dict[str, Any]:
    detail = await api.request("GET", f"/config-profiles/{profile_uuid}")
    if not isinstance(detail, dict):
        raise SelfTestError("profile_detail_invalid", phase="restore")
    return _profile_config(detail)


async def _poll_plugin_config(
    api: RemnawaveApi,
    plugin_uuid: str,
    expected_config: Mapping[str, Any],
    *,
    timeout_seconds: float,
    interval_seconds: float,
) -> int:
    deadline = time.monotonic() + timeout_seconds
    attempts = 0
    while True:
        attempts += 1
        current = await _fetch_plugin_config(api, plugin_uuid)
        if current == expected_config:
            return attempts
        if time.monotonic() >= deadline:
            raise SelfTestError("node_config_sync_timeout", phase="sync")
        await asyncio.sleep(interval_seconds)


async def _poll_profile_config(
    api: RemnawaveApi,
    profile_uuid: str,
    expected_config: Mapping[str, Any],
    *,
    timeout_seconds: float,
    interval_seconds: float,
) -> int:
    deadline = time.monotonic() + timeout_seconds
    attempts = 0
    while True:
        attempts += 1
        current = await _fetch_profile_config(api, profile_uuid)
        if current == expected_config:
            return attempts
        if time.monotonic() >= deadline:
            raise SelfTestError("profile_config_sync_timeout", phase="sync")
        await asyncio.sleep(interval_seconds)


def _run_probe_command(
    command: Sequence[str], timeout_seconds: float
) -> subprocess.CompletedProcess[bytes]:
    environment = {
        key: value
        for key, value in os.environ.items()
        if key.casefold() in PROBE_ENV_ALLOWLIST
    }
    return subprocess.run(
        list(command),
        capture_output=True,
        check=False,
        close_fds=True,
        cwd=str(Path(command[0]).parent),
        env=environment,
        shell=False,
        stdin=subprocess.DEVNULL,
        timeout=timeout_seconds,
    )


def _execute_probe(
    command: Sequence[str],
    timeout_seconds: float,
    expected_sha256: str | None,
    *,
    phase: str,
) -> dict[str, Any]:
    validated_command, executable_sha256 = _validated_pinned_probe_command(
        command,
        expected_sha256,
        phase=phase,
        require_synthetic_target=phase == "trigger",
    )
    try:
        result = _run_probe_command(validated_command, timeout_seconds)
    except subprocess.TimeoutExpired as exc:
        raise SelfTestError(
            "trigger_timeout" if phase == "trigger" else "absence_check_timeout",
            phase=phase,
            cause_class=type(exc).__name__,
        ) from exc
    try:
        post_command, post_sha256 = _validated_pinned_probe_command(
            validated_command,
            executable_sha256,
            phase=phase,
            require_synthetic_target=phase == "trigger",
        )
    except SelfTestError as exc:
        raise SelfTestError(
            "probe_artifact_changed_during_execution",
            phase=phase,
            cause_class=exc.code,
        ) from exc
    if post_command != validated_command or not hmac.compare_digest(
        post_sha256, executable_sha256
    ):
        raise SelfTestError(
            "probe_artifact_changed_during_execution",
            phase=phase,
        )
    evidence = {
        "kind": "command",
        "oneShot": True,
        "argvCount": len(validated_command),
        "executableSha256": executable_sha256,
        "environmentScrubbed": True,
        "artifactRevalidatedAfterExecution": True,
        "exitCode": result.returncode,
        "stdoutSha256": _sensitive_hash(result.stdout),
        "stderrSha256": _sensitive_hash(result.stderr),
        "outputDigest": "hmac_sha256_process_secret",
        "outputRedacted": True,
    }
    if result.returncode != 0:
        raise SelfTestError(
            "trigger_failed" if phase == "trigger" else "absence_check_failed",
            phase=phase,
            cause_class="CalledProcess",
        )
    return evidence


async def _fetch_report_records(
    api: RemnawaveApi, page_size: int
) -> list[dict[str, Any]]:
    payload = await api.request(
        "GET",
        "/node-plugins/torrent-blocker",
        params={
            "start": 0,
            "size": page_size,
            "sorting": '[{"id":"createdAt","desc":true}]',
        },
    )
    return _collection(payload, "records")


def _record_id(record: Mapping[str, Any]) -> str:
    return str(record.get("id") or "")


async def _poll_for_single_new_report(
    api: RemnawaveApi,
    baseline_ids: set[str],
    args: argparse.Namespace,
    not_before: datetime,
) -> tuple[dict[str, Any], int]:
    deadline = time.monotonic() + args.report_timeout_seconds
    attempts = 0
    while True:
        attempts += 1
        records = await _fetch_report_records(api, args.report_page_size)
        new_records = [
            record
            for record in records
            if _record_id(record) and _record_id(record) not in baseline_ids
        ]
        bound_records = [
            record
            for record in new_records
            if _report_matches_expected_identity(record, args, not_before)
        ]
        if bound_records:
            recovery_source_ip = _normalize_ip(args.expected_source_ip)
            for record in bound_records:
                try:
                    _validate_report(record, args, not_before)
                except SelfTestError as exc:
                    exc.recovery_source_ip = recovery_source_ip
                    raise
            if len(bound_records) != 1:
                raise SelfTestError(
                    "multiple_probe_bound_reports",
                    phase="report",
                    recovery_source_ip=recovery_source_ip,
                )
            return bound_records[0], attempts
        if time.monotonic() >= deadline:
            raise SelfTestError("report_timeout", phase="report")
        await asyncio.sleep(args.report_poll_interval_seconds)


def _report_matches_expected_identity(
    record: Mapping[str, Any],
    args: argparse.Namespace,
    not_before: datetime,
) -> bool:
    report = record.get("report")
    action = report.get("actionReport") if isinstance(report, Mapping) else None
    user = record.get("user")
    node = record.get("node")
    if not all(isinstance(value, Mapping) for value in (action, user, node)):
        return False
    if str(node.get("uuid") or "") not in set(args.node_uuid or []):
        return False
    if args.expected_user_uuid and user.get("uuid") != args.expected_user_uuid:
        return False
    if args.expected_username and user.get("username") != args.expected_username:
        return False
    if (
        args.expected_action_user_id
        and str(action.get("userId") or "") != args.expected_action_user_id
    ):
        return False
    try:
        if _normalize_ip(str(action.get("ip") or "")) != _normalize_ip(
            args.expected_source_ip
        ):
            return False
    except SelfTestError:
        return False
    return _report_is_after_probe(record, action, not_before)


def _validate_report(
    record: Mapping[str, Any], args: argparse.Namespace, not_before: datetime
) -> None:
    report = record.get("report")
    if not isinstance(report, Mapping):
        raise SelfTestError("report_payload_missing", phase="report")
    action = report.get("actionReport")
    xray = report.get("xrayReport")
    user = record.get("user")
    node = record.get("node")
    if not isinstance(action, Mapping) or not isinstance(xray, Mapping):
        raise SelfTestError("report_payload_missing", phase="report")
    if not isinstance(user, Mapping) or not isinstance(node, Mapping):
        raise SelfTestError("report_identity_missing", phase="report")
    if str(node.get("uuid") or "") not in set(args.node_uuid or []):
        raise SelfTestError("report_node_uuid_mismatch", phase="report")
    if action.get("blocked") is not True:
        raise SelfTestError("report_not_blocked", phase="report")
    if args.expected_user_uuid and user.get("uuid") != args.expected_user_uuid:
        raise SelfTestError("report_user_uuid_mismatch", phase="report")
    if args.expected_username and user.get("username") != args.expected_username:
        raise SelfTestError("report_username_mismatch", phase="report")
    if (
        args.expected_action_user_id
        and str(action.get("userId") or "") != args.expected_action_user_id
    ):
        raise SelfTestError("report_action_user_id_mismatch", phase="report")
    expected_ip = _normalize_ip(args.expected_source_ip)
    action_ip = _normalize_ip(str(action.get("ip") or ""))
    if action_ip != expected_ip:
        raise SelfTestError("report_source_ip_mismatch", phase="report")
    xray_source = xray.get("source")
    if not isinstance(xray_source, str) or not xray_source:
        raise SelfTestError("report_xray_source_missing", phase="report")
    source_host = _host_from_endpoint(xray_source)
    if source_host is None:
        raise SelfTestError("report_xray_source_invalid", phase="report")
    try:
        normalized_xray_source = str(ipaddress.ip_address(source_host))
    except ValueError as exc:
        raise SelfTestError(
            "report_xray_source_invalid",
            phase="report",
            cause_class=type(exc).__name__,
        ) from exc
    if normalized_xray_source != expected_ip:
        raise SelfTestError("report_xray_source_mismatch", phase="report")
    if args.expected_action_user_id and str(xray.get("email") or "") != str(
        args.expected_action_user_id
    ):
        raise SelfTestError("report_xray_email_mismatch", phase="report")
    if str(xray.get("inboundTag") or "") not in set(args.profile_inbound_tag or []):
        raise SelfTestError("report_xray_inbound_tag_mismatch", phase="report")
    if str(xray.get("network") or "").casefold() != "tcp":
        raise SelfTestError("report_xray_network_mismatch", phase="report")
    if str(xray.get("outboundTag") or "").casefold() != "direct":
        raise SelfTestError("report_xray_outbound_mismatch", phase="report")
    if _report_has_rule_tag_field(xray) and not _report_rule_tag_fields_match(
        xray,
        args.synthetic_rule_tag,
    ):
        raise SelfTestError("report_xray_rule_tag_mismatch", phase="report")
    expected_destination = (
        _normalize_ip(args.expected_destination_ip),
        args.expected_destination_port,
    )
    if _endpoint_ip_port(xray.get("destination")) != expected_destination:
        raise SelfTestError("report_xray_destination_mismatch", phase="report")
    if (
        _endpoint_ip_port(xray.get("originalTarget"), allow_transport_prefix=True)
        != expected_destination
    ):
        raise SelfTestError("report_xray_original_target_mismatch", phase="report")
    route_target = xray.get("routeTarget")
    if (
        route_target not in (None, "")
        and _endpoint_ip_port(
            route_target,
            allow_transport_prefix=True,
        )
        != expected_destination
    ):
        raise SelfTestError("report_xray_route_target_mismatch", phase="report")
    if str(xray.get("protocol") or "").casefold() == "bittorrent":
        raise SelfTestError("report_used_live_bittorrent_protocol", phase="report")
    xray_text = json.dumps(xray, sort_keys=True, default=str).casefold()
    if not _report_is_after_probe(record, action, not_before):
        raise SelfTestError("report_not_after_probe", phase="report")
    if "task2" not in xray_text or "synthetic" not in xray_text:
        raise SelfTestError("report_missing_synthetic_marker", phase="report")
    if any(marker in xray_text for marker in TOR_BLOCK_MARKERS):
        raise SelfTestError("report_mentions_forbidden_traffic", phase="report")
    if any(domain in xray_text for domain in TORRENT_CATALOG_DOMAINS):
        raise SelfTestError("report_mentions_torrent_catalog", phase="report")


def _normalize_ip(value: str) -> str:
    try:
        return str(ipaddress.ip_address(value.strip()))
    except ValueError as exc:
        raise SelfTestError(
            "invalid_source_ip", phase="preflight", cause_class=type(exc).__name__
        ) from exc


def _host_from_endpoint(value: str) -> str | None:
    text = value.strip()
    if not text:
        return None
    if text.startswith("[") and "]" in text:
        return text[1 : text.index("]")]
    if text.count(":") == 1:
        return text.split(":", 1)[0]
    try:
        ipaddress.ip_address(text)
    except ValueError:
        return None
    return text


def _endpoint_ip_port(
    value: Any, *, allow_transport_prefix: bool = False
) -> tuple[str, int] | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if allow_transport_prefix and text.casefold().startswith("tcp:"):
        text = text[4:]
    if text.startswith("["):
        closing = text.find("]")
        if closing < 0 or closing + 2 > len(text) or text[closing + 1] != ":":
            return None
        host = text[1:closing]
        port_text = text[closing + 2 :]
    elif text.count(":") == 1:
        host, port_text = text.rsplit(":", 1)
    else:
        return None
    try:
        normalized_host = str(ipaddress.ip_address(host))
        port = int(port_text)
    except (ValueError, TypeError):
        return None
    if not 1 <= port <= 65535:
        return None
    return normalized_host, port


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _report_is_after_probe(
    record: Mapping[str, Any],
    action: Mapping[str, Any],
    not_before: datetime,
) -> bool:
    candidates = [record.get("createdAt"), action.get("processedAt")]
    for candidate in candidates:
        if not isinstance(candidate, str) or not candidate:
            continue
        parsed = _parse_report_datetime(candidate)
        if parsed is not None and parsed >= not_before:
            return True
    return False


def _parse_report_datetime(value: str) -> datetime | None:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _report_evidence(record: Mapping[str, Any]) -> dict[str, Any]:
    report = record.get("report") if isinstance(record.get("report"), Mapping) else {}
    action = report.get("actionReport") if isinstance(report, Mapping) else {}
    xray = report.get("xrayReport") if isinstance(report, Mapping) else {}
    user = record.get("user") if isinstance(record.get("user"), Mapping) else {}
    node = record.get("node") if isinstance(record.get("node"), Mapping) else {}
    return {
        "id": record.get("id"),
        "blocked": action.get("blocked") if isinstance(action, Mapping) else None,
        "userUuidSha256": _sensitive_hash(str(user.get("uuid")))
        if isinstance(user, Mapping) and user.get("uuid")
        else None,
        "usernameSha256": _sensitive_hash(str(user.get("username")))
        if isinstance(user, Mapping) and user.get("username")
        else None,
        "nodeUuidSha256": _sensitive_hash(str(node.get("uuid")))
        if isinstance(node, Mapping) and node.get("uuid")
        else None,
        "sourceIpSha256": _sensitive_hash(str(action.get("ip")))
        if isinstance(action, Mapping) and action.get("ip")
        else None,
        "xrayProtocol": xray.get("protocol") if isinstance(xray, Mapping) else None,
        "xrayOutboundTag": xray.get("outboundTag")
        if isinstance(xray, Mapping)
        else None,
        "runRuleTagBinding": "exact_report_field"
        if isinstance(xray, Mapping) and _report_has_rule_tag_field(xray)
        else "inferred_from_unique_active_plugin_and_profile_config",
        "sensitiveFieldsRedacted": True,
    }


def _report_has_rule_tag_field(xray: Mapping[str, Any]) -> bool:
    return any(field in xray for field in REPORT_RULE_TAG_FIELDS)


def _report_rule_tag_fields_match(
    xray: Mapping[str, Any],
    expected_rule_tag: str,
) -> bool:
    for field in REPORT_RULE_TAG_FIELDS:
        if field not in xray:
            continue
        raw_value = xray[field]
        values = [raw_value] if isinstance(raw_value, str) else raw_value
        if (
            not isinstance(values, list)
            or len(values) != 1
            or values[0] != expected_rule_tag
        ):
            return False
    return True


def _report_action_ip(record: Mapping[str, Any]) -> str:
    report = record.get("report")
    action = report.get("actionReport") if isinstance(report, Mapping) else None
    if not isinstance(action, Mapping):
        raise SelfTestError("report_payload_missing", phase="report")
    return _normalize_ip(str(action.get("ip") or ""))


async def _assert_plugin_config_matches(
    api: RemnawaveApi,
    plugin_uuid: str,
    expected_config: Mapping[str, Any],
    *,
    code: str,
    phase: str,
) -> None:
    current = await _fetch_plugin_config(api, plugin_uuid)
    if current != expected_config:
        raise SelfTestError(code, phase=phase)


async def _assert_profile_config_matches(
    api: RemnawaveApi,
    profile_uuid: str,
    expected_config: Mapping[str, Any],
    *,
    code: str,
    phase: str,
) -> None:
    current = await _fetch_profile_config(api, profile_uuid)
    if current != expected_config:
        raise SelfTestError(code, phase=phase)


def _replace_template_ip(value: Any, source_ip: str) -> Any:
    if isinstance(value, str):
        return value.replace("{{source_ip}}", source_ip)
    if isinstance(value, list):
        return [_replace_template_ip(item, source_ip) for item in value]
    if isinstance(value, dict):
        return {
            str(key): _replace_template_ip(child, source_ip)
            for key, child in value.items()
        }
    return value


def _build_unblock_payload(args: argparse.Namespace, source_ip: str) -> dict[str, Any]:
    command_template = _parse_json_object(
        args.unblock_command_json,
        code="invalid_unblock_command_json",
        phase="unblock",
    )
    command = (
        _replace_template_ip(command_template, source_ip)
        if command_template is not None
        else {"command": "unblockIps", "ips": [source_ip]}
    )
    if command != {"command": "unblockIps", "ips": [source_ip]}:
        raise SelfTestError(
            "unblock_command_must_match_official_schema", phase="unblock"
        )
    target_nodes = _parse_json_object(
        args.target_nodes_json,
        code="invalid_target_nodes_json",
        phase="unblock",
    ) or {"target": "specificNodes", "nodeUuids": list(args.node_uuid or [])}
    _validate_executor_target_nodes(target_nodes, args.node_uuid or [])
    return {"command": command, "targetNodes": target_nodes}


def _validate_executor_target_nodes(
    target_nodes: Mapping[str, Any], selected_node_uuids: Sequence[str]
) -> None:
    if set(target_nodes) != {"target", "nodeUuids"}:
        raise SelfTestError(
            "target_nodes_must_use_exact_specific_nodes_schema", phase="unblock"
        )
    if target_nodes.get("target") != "specificNodes":
        raise SelfTestError("target_nodes_must_target_specific_nodes", phase="unblock")
    value = target_nodes.get("nodeUuids")
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item for item in value
    ):
        raise SelfTestError("target_nodes_must_use_node_uuids", phase="unblock")
    if len(value) != len(set(value)):
        raise SelfTestError("target_nodes_duplicate_node_uuid", phase="unblock")
    if set(value) != set(selected_node_uuids):
        raise SelfTestError("target_nodes_must_match_selected_nodes", phase="unblock")


async def _unblock_source(
    api: RemnawaveApi, args: argparse.Namespace, source_ip: str
) -> dict[str, Any]:
    payload = _build_unblock_payload(args, source_ip)
    response = await api.request("POST", "/node-plugins/executor", json=payload)
    if not isinstance(response, Mapping) or response.get("eventSent") is not True:
        raise SelfTestError("unblock_event_not_sent", phase="unblock")
    return {
        "status": "sent",
        "sourceIpSha256": _sensitive_hash(source_ip),
        "targetNodesSha256": _json_hash(payload["targetNodes"]),
        "command": "unblockIps",
        "sensitiveDigest": "hmac_sha256_process_secret",
    }


def _run_absence_check(args: argparse.Namespace) -> dict[str, Any]:
    command = _parse_command_json(
        args.absence_check_command_json,
        required=False,
        phase="absence_check",
    )
    if command is None:
        return {"status": "not_supported", "reason": "no_absence_check_command"}
    evidence = _execute_probe(
        command,
        args.trigger_timeout_seconds,
        args.absence_check_executable_sha256,
        phase="absence_check",
    )
    return {"status": "passed", **evidence}


def _failure_from_exception(
    exc: BaseException, *, fallback_phase: str
) -> dict[str, Any]:
    if isinstance(exc, SelfTestError):
        return {
            "code": exc.code,
            "phase": exc.phase,
            "class": exc.cause_class or type(exc).__name__,
        }
    return {
        "code": "unexpected_failure",
        "phase": fallback_phase,
        "class": type(exc).__name__,
    }


async def _run(args: argparse.Namespace) -> dict[str, Any]:
    _validate_rule_tag(args.synthetic_rule_tag)
    _validate_temporary_profile_rule_args(args)
    apply_mode = _require_apply_confirmations(args)
    _validate_numeric_bounds(args)
    if args.expected_source_ip:
        _normalize_ip(args.expected_source_ip)
    if args.temporary_profile_rule:
        args = copy.copy(args)
        args.synthetic_rule_tag = _run_scoped_rule_tag(args.synthetic_rule_tag)

    evidence: dict[str, Any] = {
        "schema": "cybervpn.remnawave.safe_torrent_blocker_self_test.v1",
        "status": "running",
        "mode": PRODUCTION_SYNTHETIC_MODE
        if apply_mode == PRODUCTION_SYNTHETIC_MODE
        else ("apply" if args.apply else "dry-run"),
        "applyEnvironment": apply_mode,
        "dryRun": not args.apply,
        "proofScope": {
            "plumbing": "webhook_to_nftables_to_report",
            "bitTorrentRecognition": False,
            "perNodeProtocolRecognition": False,
        },
        "trafficSafety": {
            "liveTorrentTraffic": False,
            "swarmTraffic": False,
            "torTraffic": False,
            "torrentCatalogWebsiteProbe": False,
            "safeSyntheticRuleOnly": True,
            "runScopedRuleTag": bool(args.temporary_profile_rule),
        },
        "transport": {"trustedProxyHeaders": bool(args.trusted_proxy_headers)},
        "plugin": {},
        "profileRule": {},
        "sync": {},
        "trigger": {},
        "report": {},
        "cleanup": {
            "unblock": {"status": "not_started"},
            "restore": {"status": "not_started"},
            "profileRestore": {"status": "not_started"},
        },
    }
    _require_internal_operator_remnawave_host(args.remnawave_url)
    token = _require_token()
    api = RemnawaveApi(
        args.remnawave_url,
        token,
        allowed_hosts=args.allow_remnawave_host,
        trusted_proxy_headers=args.trusted_proxy_headers,
    )
    original_config: dict[str, Any] | None = None
    planned_config: dict[str, Any] | None = None
    plugin_uuid: str | None = None
    profile_rule_state: dict[str, Any] | None = None
    profile_mutation_attempted = False
    mutation_attempted = False
    probe_attempted = False
    observed_report_source_ip: str | None = None
    primary_exc: BaseException | None = None

    try:
        plugin = await _load_plugin(api, args.plugin_name)
        plugin_uuid = _plugin_uuid(plugin)
        original_config = copy.deepcopy(_plugin_config(plugin))
        planned_config = _plugin_config_with_include_rule_tags(
            original_config, args.synthetic_rule_tag
        )
        _assert_only_include_rule_tags_changed(original_config, planned_config)
        evidence["plugin"] = {
            "nameSha256": _text_hash(args.plugin_name),
            "uuidSha256": _text_hash(plugin_uuid),
            "originalConfigSha256": _json_hash(original_config),
            "plannedConfigSha256": _json_hash(planned_config),
            "runRuleTagSha256": _sensitive_hash(args.synthetic_rule_tag),
            "preStateHashBackupCaptured": True,
            "onlyIncludeRuleTagsChanges": True,
            "proofScope": "webhook_to_nftables_to_report_plumbing_only",
            "bitTorrentRecognitionProven": False,
            "perNodeProtocolRecognitionProven": False,
            "temporaryIncludeRuleTagsReplacement": True,
            "originalIncludeRuleTagsSha256": _json_hash(
                original_config.get("torrentBlocker", {}).get("includeRuleTags")
                if isinstance(original_config.get("torrentBlocker"), Mapping)
                else None
            ),
        }
        nodes_payload = await api.request("GET", "/nodes")
        selected_nodes = _selected_nodes(
            _collection(nodes_payload, "nodes"), args.node_uuid or []
        )
        if selected_nodes:
            _validate_selected_nodes(selected_nodes, plugin_uuid)
            evidence["nodes"] = {
                "selectedCount": len(selected_nodes),
                "nodeUuidSha256": [
                    _text_hash(str(node.get("uuid"))) for node in selected_nodes
                ],
            }
            if args.temporary_profile_rule:
                profile_rule_state = await _prepare_temporary_profile_rule(
                    api, selected_nodes, args
                )
                evidence["profileRule"] = profile_rule_state["evidence"]
            else:
                evidence["syntheticRule"] = await _validate_synthetic_rule_exists(
                    api,
                    selected_nodes,
                    args.synthetic_rule_tag,
                )
        else:
            evidence["nodes"] = {"selectedCount": 0}

        if not args.apply:
            evidence["status"] = "dry_run"
            evidence["plannedMutation"] = {
                "pluginConfigPatch": "pluginConfig.torrentBlocker.includeRuleTags",
                "includeRuleTagsCount": 1,
                "temporaryIncludeRuleTagsReplacement": True,
                "selectedRuleWebhookScopeOnlyWhileEnabled": True,
                "temporaryProfileRule": bool(args.temporary_profile_rule),
            }
            evidence["cleanup"] = {
                "unblock": {"status": "not_required_in_dry_run"},
                "restore": {"status": "not_required_in_dry_run"},
                "profileRestore": {"status": "not_required_in_dry_run"},
            }
            return evidence

        baseline_records = await _fetch_report_records(api, args.report_page_size)
        baseline_ids = {
            _record_id(record) for record in baseline_records if _record_id(record)
        }
        evidence["report"]["baselineRecordCount"] = len(baseline_ids)

        profile_runtime_before: dict[str, Any] | None = None
        if profile_rule_state is not None:
            profile_uuid = str(profile_rule_state["profileUuid"])
            original_profile_config = profile_rule_state["originalConfig"]
            await _assert_profile_config_matches(
                api,
                profile_uuid,
                original_profile_config,
                code="profile_config_concurrent_drift_before_patch",
                phase="preflight",
            )

        await _assert_plugin_config_matches(
            api,
            plugin_uuid,
            original_config,
            code="plugin_config_concurrent_drift_before_patch",
            phase="preflight",
        )
        mutation_attempted = True
        await _patch_plugin_config(api, plugin_uuid, planned_config)
        evidence["plugin"]["patched"] = True
        sync_attempts = await _poll_plugin_config(
            api,
            plugin_uuid,
            planned_config,
            timeout_seconds=args.sync_timeout_seconds,
            interval_seconds=args.sync_poll_interval_seconds,
        )
        evidence["sync"] = {"status": "observed", "pollAttempts": sync_attempts}

        if profile_rule_state is not None:
            node_uuid = str(profile_rule_state["nodeUuid"])
            profile_uuid = str(profile_rule_state["profileUuid"])
            profile_name = profile_rule_state["profileName"]
            planned_profile_config = profile_rule_state["plannedConfig"]
            profile_runtime_before = await _capture_ready_node_runtime_state(
                api,
                node_uuid=node_uuid,
                profile_uuid=profile_uuid,
                plugin_uuid=plugin_uuid,
                phase="preflight",
            )
            await _assert_profile_config_matches(
                api,
                profile_uuid,
                original_profile_config,
                code="profile_config_concurrent_drift_before_profile_patch",
                phase="preflight",
            )
            profile_mutation_attempted = True
            await _patch_profile_config(
                api,
                profile_uuid,
                profile_name,
                planned_profile_config,
            )
            evidence["profileRule"]["patched"] = True
            profile_sync_attempts = await _poll_profile_config(
                api,
                profile_uuid,
                planned_profile_config,
                timeout_seconds=args.sync_timeout_seconds,
                interval_seconds=args.sync_poll_interval_seconds,
            )
            evidence["profileRule"]["sync"] = {
                "status": "observed",
                "pollAttempts": profile_sync_attempts,
            }
            (
                runtime_attempts,
                runtime_after,
                saw_not_ready,
            ) = await _poll_node_runtime_transition(
                api,
                before=profile_runtime_before,
                profile_uuid=profile_uuid,
                plugin_uuid=plugin_uuid,
                timeout_seconds=args.sync_timeout_seconds,
                interval_seconds=args.sync_poll_interval_seconds,
                timeout_code="node_runtime_transition_timeout",
                phase="sync",
            )
            evidence["profileRule"]["runtimeTransition"] = (
                _node_runtime_transition_evidence(
                    profile_runtime_before,
                    runtime_after,
                    attempts=runtime_attempts,
                    saw_not_ready=saw_not_ready,
                )
            )
            evidence["syntheticRule"] = await _validate_synthetic_rule_exists(
                api,
                selected_nodes,
                args.synthetic_rule_tag,
            )

        trigger_command = _parse_command_json(
            args.trigger_command_json,
            required=True,
            phase="trigger",
            require_synthetic_target=True,
        )
        assert trigger_command is not None
        trigger_started_at = _utc_now()
        probe_attempted = True
        trigger_exc: Exception | None = None
        try:
            evidence["trigger"] = _execute_probe(
                trigger_command,
                args.trigger_timeout_seconds,
                args.trigger_executable_sha256,
                phase="trigger",
            )
        except Exception as exc:
            trigger_exc = exc
            evidence["trigger"] = {
                "status": "failed",
                "failure": _failure_from_exception(exc, fallback_phase="trigger"),
                "outputRedacted": True,
            }
        try:
            report_record, report_attempts = await _poll_for_single_new_report(
                api, baseline_ids, args, trigger_started_at
            )
        except SelfTestError as report_exc:
            if report_exc.recovery_source_ip is not None:
                observed_report_source_ip = report_exc.recovery_source_ip
                evidence["report"].update(
                    {
                        "status": "rejected_probe_bound_report",
                        "failure": _failure_from_exception(
                            report_exc,
                            fallback_phase="report",
                        ),
                    }
                )
            if trigger_exc is not None and report_exc.code == "report_timeout":
                evidence["report"].update(
                    {
                        "status": "not_observed_after_failed_trigger",
                        "failure": _failure_from_exception(
                            report_exc,
                            fallback_phase="report",
                        ),
                    }
                )
                raise trigger_exc
            raise
        observed_report_source_ip = _report_action_ip(report_record)
        evidence["report"].update(
            {
                "status": "observed",
                "pollAttempts": report_attempts,
                "newReportCount": 1,
                "record": _report_evidence(report_record),
            }
        )
        if trigger_exc is not None:
            raise trigger_exc
        evidence["status"] = "passed"
    except asyncio.CancelledError as exc:
        primary_exc = SelfTestError(
            "cancelled", phase="cancel", cause_class=type(exc).__name__
        )
    except KeyboardInterrupt as exc:
        primary_exc = SelfTestError(
            "interrupted", phase="interrupt", cause_class=type(exc).__name__
        )
    except Exception as exc:
        primary_exc = exc
    finally:
        cleanup_errors: list[SelfTestError] = []
        if (
            args.apply
            and probe_attempted
            and observed_report_source_ip is not None
            and plugin_uuid is not None
        ):
            try:
                evidence["cleanup"]["unblock"] = await _unblock_source(
                    api, args, observed_report_source_ip
                )
                evidence["cleanup"]["absenceCheck"] = _run_absence_check(args)
            except BaseException as exc:
                cleanup_error = (
                    exc
                    if isinstance(exc, SelfTestError)
                    else SelfTestError(
                        "unblock_failed",
                        phase="unblock",
                        cause_class=type(exc).__name__,
                    )
                )
                cleanup_errors.append(cleanup_error)
                evidence["cleanup"]["unblock"] = {
                    "status": "failed",
                    "code": cleanup_error.code,
                    "class": cleanup_error.cause_class or type(exc).__name__,
                }
        elif args.apply:
            evidence["cleanup"]["unblock"] = {
                "status": "not_required",
                "reason": "no_valid_report_observed",
            }
        if (
            mutation_attempted
            and original_config is not None
            and plugin_uuid is not None
        ):
            try:
                plugin_restore_precheck_error: SelfTestError | None = None
                if planned_config is not None:
                    try:
                        current_before_restore = await _fetch_plugin_config(
                            api, plugin_uuid
                        )
                        if current_before_restore not in (
                            planned_config,
                            original_config,
                        ):
                            plugin_restore_precheck_error = SelfTestError(
                                "plugin_config_concurrent_drift_before_restore",
                                phase="restore",
                            )
                    except BaseException as exc:
                        plugin_restore_precheck_error = (
                            exc
                            if isinstance(exc, SelfTestError)
                            else SelfTestError(
                                "restore_precheck_failed",
                                phase="restore",
                                cause_class=type(exc).__name__,
                            )
                        )
                if plugin_restore_precheck_error is not None:
                    raise plugin_restore_precheck_error
                await _patch_plugin_config(api, plugin_uuid, original_config)
                restored_config = await _fetch_plugin_config(api, plugin_uuid)
                if restored_config != original_config:
                    raise SelfTestError("restore_verification_failed", phase="restore")
                evidence["cleanup"]["restore"] = {
                    "status": "verified",
                    "restoredConfigSha256": _json_hash(restored_config),
                }
            except BaseException as exc:
                cleanup_error = (
                    exc
                    if isinstance(exc, SelfTestError)
                    else SelfTestError(
                        "restore_failed",
                        phase="restore",
                        cause_class=type(exc).__name__,
                    )
                )
                cleanup_errors.append(cleanup_error)
                evidence["cleanup"]["restore"] = {
                    "status": "failed",
                    "code": cleanup_error.code,
                    "class": cleanup_error.cause_class or type(exc).__name__,
                }
        elif args.apply:
            evidence["cleanup"]["restore"] = {"status": "not_required"}
        if (
            profile_mutation_attempted
            and profile_rule_state is not None
            and plugin_uuid is not None
        ):
            try:
                profile_uuid = str(profile_rule_state["profileUuid"])
                profile_name = profile_rule_state["profileName"]
                original_profile_config = profile_rule_state["originalConfig"]
                planned_profile_config = profile_rule_state["plannedConfig"]
                profile_restore_precheck_error: SelfTestError | None = None
                try:
                    current_before_restore = await _fetch_profile_config(
                        api, profile_uuid
                    )
                    if current_before_restore not in (
                        planned_profile_config,
                        original_profile_config,
                    ):
                        profile_restore_precheck_error = SelfTestError(
                            "profile_config_concurrent_drift_before_restore",
                            phase="restore",
                        )
                except BaseException as exc:
                    profile_restore_precheck_error = (
                        exc
                        if isinstance(exc, SelfTestError)
                        else SelfTestError(
                            "profile_restore_precheck_failed",
                            phase="restore",
                            cause_class=type(exc).__name__,
                        )
                    )
                if profile_restore_precheck_error is not None:
                    raise profile_restore_precheck_error
                node_uuid = str(profile_rule_state["nodeUuid"])
                runtime_before_restore: dict[str, Any] | None = None
                runtime_baseline_error: SelfTestError | None = None
                try:
                    runtime_before_restore = await _fetch_node_runtime_state(
                        api,
                        node_uuid=node_uuid,
                        profile_uuid=profile_uuid,
                        plugin_uuid=plugin_uuid,
                        phase="restore",
                    )
                except BaseException as exc:
                    runtime_baseline_error = (
                        exc
                        if isinstance(exc, SelfTestError)
                        else SelfTestError(
                            "node_runtime_restore_baseline_failed",
                            phase="restore",
                            cause_class=type(exc).__name__,
                        )
                    )
                await _patch_profile_config(
                    api,
                    profile_uuid,
                    profile_name,
                    original_profile_config,
                )
                restored_profile_config = await _fetch_profile_config(api, profile_uuid)
                if restored_profile_config != original_profile_config:
                    raise SelfTestError(
                        "profile_restore_verification_failed", phase="restore"
                    )
                if runtime_baseline_error is not None or runtime_before_restore is None:
                    raise runtime_baseline_error or SelfTestError(
                        "node_runtime_restore_baseline_failed", phase="restore"
                    )
                (
                    runtime_attempts,
                    runtime_after,
                    saw_not_ready,
                ) = await _poll_node_runtime_transition(
                    api,
                    before=runtime_before_restore,
                    profile_uuid=profile_uuid,
                    plugin_uuid=plugin_uuid,
                    timeout_seconds=args.sync_timeout_seconds,
                    interval_seconds=args.sync_poll_interval_seconds,
                    timeout_code="node_runtime_restore_transition_timeout",
                    phase="restore",
                )
                evidence["cleanup"]["profileRestore"] = {
                    "status": "verified",
                    "restoredConfigSha256": _json_hash(restored_profile_config),
                    "hashEqualsPreState": True,
                    "runtimeTransition": _node_runtime_transition_evidence(
                        runtime_before_restore,
                        runtime_after,
                        attempts=runtime_attempts,
                        saw_not_ready=saw_not_ready,
                    ),
                }
            except BaseException as exc:
                cleanup_error = (
                    exc
                    if isinstance(exc, SelfTestError)
                    else SelfTestError(
                        "profile_restore_failed",
                        phase="restore",
                        cause_class=type(exc).__name__,
                    )
                )
                cleanup_errors.append(cleanup_error)
                evidence["cleanup"]["profileRestore"] = {
                    "status": "failed",
                    "code": cleanup_error.code,
                    "class": cleanup_error.cause_class or type(exc).__name__,
                }
        elif args.apply:
            evidence["cleanup"]["profileRestore"] = {"status": "not_required"}
        try:
            await api.close()
        except BaseException as exc:
            cleanup_error = (
                exc
                if isinstance(exc, SelfTestError)
                else SelfTestError(
                    "api_close_failed",
                    phase="close",
                    cause_class=type(exc).__name__,
                )
            )
            cleanup_errors.append(cleanup_error)
            evidence["cleanup"]["close"] = {
                "status": "failed",
                "code": cleanup_error.code,
                "class": cleanup_error.cause_class or type(exc).__name__,
            }

    if cleanup_errors:
        first = cleanup_errors[0]
        evidence["status"] = "failed"
        evidence["failure"] = {
            "code": first.code,
            "phase": first.phase,
            "class": first.cause_class or type(first).__name__,
            "primaryFailure": _failure_from_exception(primary_exc, fallback_phase="run")
            if primary_exc
            else None,
        }
        raise SelfTestFailed(evidence)
    if primary_exc is not None:
        evidence["status"] = "failed"
        evidence["failure"] = _failure_from_exception(primary_exc, fallback_phase="run")
        raise SelfTestFailed(evidence)
    return evidence


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply the temporary self-test; default is dry-run",
    )
    parser.add_argument(
        "--remnawave-url",
        default=os.environ.get("REMNAWAVE_URL", "http://remnawave:3000"),
    )
    parser.add_argument(
        "--allow-remnawave-host",
        action="append",
        default=list(DEFAULT_INTERNAL_HOSTS),
        help="Additional API allowlist entry; this operator still requires a fixed internal host.",
    )
    parser.add_argument(
        "--trusted-proxy-headers",
        action="store_true",
        help=(
            "Send X-Forwarded-Proto=https and X-Forwarded-For=127.0.0.1. "
            "Allowed only for explicitly allowlisted loopback/internal Remnawave hosts."
        ),
    )
    parser.add_argument("--plugin-name", default=DEFAULT_PLUGIN_NAME)
    parser.add_argument("--synthetic-rule-tag", required=True)
    parser.add_argument("--node-uuid", action="append", default=[])
    parser.add_argument(
        "--temporary-profile-rule",
        action="store_true",
        help=(
            "Temporarily insert one harmless DIRECT profile rule for the selected "
            "synthetic user/tId and inbound tags before running the plugin proof."
        ),
    )
    parser.add_argument(
        "--profile-inbound-tag",
        action="append",
        default=[],
        help="Inbound tag to scope the temporary profile rule; repeat as needed.",
    )
    parser.add_argument(
        "--target-nodes-json",
        help=(
            "Official executor targetNodes JSON. Defaults to "
            '{"target":"specificNodes","nodeUuids":[...]} for selected nodes.'
        ),
    )
    parser.add_argument(
        "--trigger-command-json",
        help=(
            "Approved absolute helper argv; the target must be exactly "
            "http://task2-synthetic.invalid."
        ),
    )
    parser.add_argument(
        "--trigger-executable-sha256",
        help=(
            "Required SHA-256 pin; it must also match the fixed read-only approved "
            "helper manifest."
        ),
    )
    parser.add_argument(
        "--absence-check-command-json",
        help="Optional safe command that verifies the selected source is no longer blocked.",
    )
    parser.add_argument(
        "--absence-check-executable-sha256",
        help="Required SHA-256 pin when an absence-check executable is configured.",
    )
    parser.add_argument(
        "--unblock-command-json",
        help=(
            "Optional command JSON template; must render exactly to "
            '{"command":"unblockIps","ips":["{{source_ip}}"]}.'
        ),
    )
    parser.add_argument("--expected-user-uuid")
    parser.add_argument("--expected-username")
    parser.add_argument("--expected-action-user-id")
    parser.add_argument("--expected-xray-user")
    parser.add_argument("--expected-xray-tid")
    parser.add_argument("--expected-source-ip")
    parser.add_argument(
        "--expected-destination-ip",
        help="Exact resolved synthetic listener IP expected in the Xray report.",
    )
    parser.add_argument(
        "--expected-destination-port",
        type=int,
        help="Exact synthetic listener port expected in the Xray report.",
    )
    parser.add_argument("--sync-timeout-seconds", type=float, default=90.0)
    parser.add_argument("--sync-poll-interval-seconds", type=float, default=2.0)
    parser.add_argument("--report-timeout-seconds", type=float, default=90.0)
    parser.add_argument("--report-poll-interval-seconds", type=float, default=2.0)
    parser.add_argument("--report-page-size", type=int, default=50)
    parser.add_argument("--trigger-timeout-seconds", type=float, default=20.0)
    parser.add_argument("--confirm-apply")
    parser.add_argument("--confirm-no-live-traffic")
    parser.add_argument("--confirm-restore")
    return parser


def _safe_failure_output(exc: BaseException) -> dict[str, Any]:
    if isinstance(exc, SelfTestFailed):
        return exc.evidence
    return {
        "schema": "cybervpn.remnawave.safe_torrent_blocker_self_test.v1",
        "status": "failed",
        "failure": _failure_from_exception(exc, fallback_phase="main"),
    }


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = asyncio.run(_run(args))
    except Exception as exc:
        print(
            json.dumps(
                _sanitize_for_evidence(_safe_failure_output(exc)),
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 1
    print(
        json.dumps(
            _sanitize_for_evidence(result), sort_keys=True, separators=(",", ":")
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
