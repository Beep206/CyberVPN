#!/usr/bin/env python3
"""Apply the Task2 SPB-default/DE-exceptions Remnawave foundation.

This operator creates a dedicated SPB customer server profile and a dedicated
DE bridge profile for the premium_spb_de_exceptions product. It consumes the
route artifact interface produced by the Antifilter compiler, but intentionally
does not create or edit scripts/remnawave/antifilter.

Dry-run is read-only. Apply and rollback require a rollback manifest outside
the repository. The manifest is written mode 0600 because it stores rollback
state byte-for-byte enough to restore pre-change shared profiles and Hosts.
"""

from __future__ import annotations

import argparse
import asyncio
import copy
import hashlib
import ipaddress
import json
import os
import re
import socket
import sys
import tempfile
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx

PRODUCT_CODE = "premium_spb_de_exceptions"
ARTIFACT_SCHEMA_VERSION = 1

SPB_BASE_PROFILE_NAME = "S1 SPB VLESS XHTTP"
DE_BASE_PROFILE_NAME = "S1 DE VLESS XHTTP"
SPB_PROFILE_NAME = "S1 SPB DE Exceptions"
DE_BRIDGE_PROFILE_NAME = "S1 DE SPB Bridge"

SPB_NODE_ADDRESS = "193.233.91.99"
DE_NODE_ADDRESS = "138.124.115.206"
SPB_PUBLIC_HOST = "spb-exceptions.cyber-vpn.org"
SPB_XHTTP_PATH = "/spb-de-exceptions-xhttp"
SPB_TASK2_RAW_PORT = 4443
SPB_TASK2_XHTTP_PORT = 8444
SPB_PRESERVED_PUBLIC_PORTS = {443, 8443}
SPB_BRIDGE_SOURCE_ADDRESS = "2a01:e5c0:1368::3"
DE_BRIDGE_LISTEN_ADDRESS = "2a0b:4140:ba84::2"
DE_BRIDGE_UPSTREAM_ADDRESS = DE_BRIDGE_LISTEN_ADDRESS

CUSTOMER_SQUAD_NAME = "CYBERVPN_SPB_DE_NODES"
EXTERNAL_SQUAD_NAME = "CYBERVPN_SPB_DE_EXCEPTIONS"
BRIDGE_SQUAD_NAME = "CYBERVPN_SPB_DE_BRIDGE"
BRIDGE_USERNAME = "CYBERVPN_SPB_DE_BRIDGE_USER"

BRIDGE_INBOUND_TAG = "DE_SPB_EXCEPTIONS_BRIDGE_9444"
BRIDGE_OUTBOUND_TAG = "DE_EXCEPTIONS_BRIDGE"
BRIDGE_PORT = 9444
BRIDGE_AEAD_METHOD = "chacha20-ietf-poly1305"
ALLOWED_AEAD_METHODS = {"chacha20-ietf-poly1305", "aes-128-gcm", "aes-256-gcm"}
IPV6_POLICY_MODES = {"enabled", "disabled", "fallback_block"}
IPV6_BLOCK_POLICY_MODES = {"disabled", "fallback_block"}
MAX_EXCEPTION_RULES = 50_000
MAX_EXCEPTION_PREFIXES = 500_000
REMNAWAVE_INBOUND_TAG_MAX_LENGTH = 36
PRESERVED_TAG_PREFIXES = {"spb": "T2S_", "de": "T2D_"}

OLD_TO_SPB_TAG = {
    "VLESS_REALITY_443": "SPB_EXCEPTIONS_REALITY_443",
    "VLESS_XHTTP_REALITY_8443": "SPB_EXCEPTIONS_XHTTP_REALITY_8443",
}
SPB_CUSTOMER_INBOUND_TAGS = list(OLD_TO_SPB_TAG.values())
SPB_CUSTOMER_INBOUND_TAG_SET = set(SPB_CUSTOMER_INBOUND_TAGS)
SPB_REQUIRED_INBOUND_PORTS = {
    "SPB_EXCEPTIONS_REALITY_443": SPB_TASK2_RAW_PORT,
    "SPB_EXCEPTIONS_XHTTP_REALITY_8443": SPB_TASK2_XHTTP_PORT,
}
SPB_PUBLIC_HOST_SPECS = [
    {
        "remark": "CyberVPN SPB DE Reality 4443",
        "legacy_remarks": ["CyberVPN SPB DE Reality 443"],
        "port": SPB_TASK2_RAW_PORT,
        "path": None,
        "inbound_tag": "SPB_EXCEPTIONS_REALITY_443",
        "server_description": "Premium SPB DE Exceptions",
        "host_tag": "SPB_DE_EXCEPTIONS_REALITY_443",
        "view_position": 242,
    },
    {
        "remark": "CyberVPN SPB DE XHTTP 8444",
        "legacy_remarks": ["CyberVPN SPB DE XHTTP 8443"],
        "port": SPB_TASK2_XHTTP_PORT,
        "path": SPB_XHTTP_PATH,
        "inbound_tag": "SPB_EXCEPTIONS_XHTTP_REALITY_8443",
        "server_description": "Premium SPB DE Exceptions",
        "host_tag": "SPB_DE_EXCEPTIONS_XHTTP_8443",
        "view_position": 243,
    },
]

MANAGEMENT_AND_SELF_IPS = [
    "geoip:private",
    "0.0.0.0/8",
    "10.0.0.0/8",
    "100.64.0.0/10",
    "127.0.0.0/8",
    "169.254.0.0/16",
    "172.16.0.0/12",
    "192.168.0.0/16",
    "224.0.0.0/4",
    "255.255.255.255/32",
    "::1/128",
    "fc00::/7",
    "fe80::/10",
    "ff00::/8",
    "45.87.41.146/32",
    f"{SPB_NODE_ADDRESS}/32",
    f"{DE_NODE_ADDRESS}/32",
    "2a01:e5c0:1368::2/128",
    f"{SPB_BRIDGE_SOURCE_ADDRESS}/128",
    f"{DE_BRIDGE_LISTEN_ADDRESS}/128",
]

BLOCKED_TORRENT_DOMAINS = [
    "1337x.to",
    "eztv.re",
    "limetorrents.lol",
    "nnmclub.to",
    "thepiratebay.org",
    "torrentdownload.info",
    "torrentgalaxy.to",
    "rutracker.org",
    "rutor.info",
    "kinozal.tv",
    "yts.mx",
]

INTERNAL_HTTP_REMNAWAVE_HOSTS = {"remnawave", "localhost", "127.0.0.1", "::1"}


def _find_repo_root() -> Path | None:
    script_path = Path(__file__).resolve()
    for candidate in (script_path.parent, *script_path.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


REPO_ROOT = _find_repo_root()


@dataclass(frozen=True)
class AntifilterArtifact:
    manifest_path: Path
    rules_path: Path
    manifest_sha256: str
    rules_sha256: str
    generated_at: datetime
    union_prefix_count: int
    union_ipv6_prefix_count: int
    ipv6_policy_mode: str
    raw_rules: list[dict[str, Any]]


class RemnawaveApi:
    def __init__(
        self, base_url: str, token: str, *, trusted_proxy_headers: bool = False
    ) -> None:
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
            timeout=30.0,
            trust_env=False,
        )

    async def request(self, method: str, path: str, **kwargs: Any) -> Any:
        normalized = path if path.startswith("/api/") else f"/api/{path.lstrip('/')}"
        response = await self._client.request(method, normalized, **kwargs)
        response.raise_for_status()
        if not response.content.strip():
            return {}
        payload = response.json()
        if isinstance(payload, dict) and set(payload) == {"response"}:
            return payload["response"]
        return payload

    async def close(self) -> None:
        await self._client.aclose()


def _collection(data: Any, key: str) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict) and isinstance(data.get(key), list):
        return [item for item in data[key] if isinstance(item, dict)]
    return []


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_limited_bytes(path: Path, *, max_bytes: int, label: str) -> bytes:
    if not path.is_file():
        raise RuntimeError(f"{label} does not exist")
    size = path.stat().st_size
    if size <= 0:
        raise RuntimeError(f"{label} is empty")
    if size > max_bytes:
        raise RuntimeError(f"{label} is too large")
    return path.read_bytes()


def _parse_utc_timestamp(value: Any) -> datetime:
    if not isinstance(value, str) or not value:
        raise RuntimeError("Antifilter manifest generatedAt is required")
    normalized = value.removesuffix("Z") + ("+00:00" if value.endswith("Z") else "")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise RuntimeError("Antifilter manifest generatedAt must be timezone-aware")
    return parsed.astimezone(UTC)


def _artifact_path_from_manifest(
    manifest_path: Path, manifest: dict[str, Any], override_path: Path | None
) -> Path:
    if override_path is not None:
        candidate = override_path.expanduser().resolve(strict=False)
    else:
        artifacts = manifest.get("artifacts")
        artifacts = artifacts if isinstance(artifacts, dict) else {}
        raw_path = (
            artifacts.get("xrayRulesPath")
            or artifacts.get("xray_rules_path")
            or (manifest.get("xray") or {}).get("rulesPath")
        )
        if not isinstance(raw_path, str) or not raw_path:
            raise RuntimeError(
                "Antifilter manifest must reference an Xray rules artifact"
            )
        candidate = (manifest_path.parent / raw_path).resolve(strict=False)

    root = manifest_path.parent.resolve(strict=False)
    if candidate != root and root not in candidate.parents:
        raise RuntimeError(
            "Antifilter artifact path must stay under the manifest directory"
        )
    return candidate


def _expected_rules_sha256(manifest: dict[str, Any]) -> str:
    artifacts = manifest.get("artifacts")
    artifacts = artifacts if isinstance(artifacts, dict) else {}
    value = (
        artifacts.get("xrayRulesSha256")
        or artifacts.get("xray_rules_sha256")
        or (manifest.get("xray") or {}).get("rulesSha256")
    )
    if not isinstance(value, str) or len(value) != 64:
        raise RuntimeError("Antifilter manifest must contain xrayRulesSha256")
    return value.lower()


def _ipv6_policy_mode(manifest: dict[str, Any]) -> str:
    policy = manifest.get("ipv6Policy")
    policy = policy if isinstance(policy, dict) else {}
    mode = policy.get("mode")
    if mode not in IPV6_POLICY_MODES:
        raise RuntimeError("Antifilter manifest ipv6Policy.mode is required")
    return str(mode)


def _union_family_count(manifest: dict[str, Any], family: str) -> int:
    union = manifest.get("union")
    union = union if isinstance(union, dict) else {}
    families = union.get("families")
    families = families if isinstance(families, dict) else {}
    value = families.get(family, 0)
    if not isinstance(value, int) or value < 0:
        raise RuntimeError(f"Antifilter manifest union.families.{family} is invalid")
    return value


def _load_json(data: bytes, *, label: str) -> Any:
    try:
        return json.loads(data.decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - public CLI boundary normalizes the error.
        raise RuntimeError(f"{label} is not valid JSON") from exc


def _actual_raw_rule_ipv6_prefix_count(raw_rules: list[dict[str, Any]]) -> int:
    count = 0
    for raw_rule in raw_rules:
        ips = raw_rule.get("ip")
        if not isinstance(ips, list) or not ips:
            raise RuntimeError(
                "Antifilter exception rules must contain non-empty ip matchers"
            )
        for item in ips:
            if not isinstance(item, str) or not item:
                raise RuntimeError(
                    "Antifilter exception rules must contain non-empty ip matchers"
                )
            try:
                network = ipaddress.ip_network(item, strict=False)
            except ValueError as exc:
                raise RuntimeError(
                    f"Antifilter exception matcher is not a CIDR: {item}"
                ) from exc
            if network.version == 6:
                count += 1
    return count


def _load_antifilter_artifact(
    manifest_path: Path,
    *,
    rules_path: Path | None = None,
    max_age_hours: int = 72,
) -> AntifilterArtifact:
    resolved_manifest = manifest_path.expanduser().resolve(strict=False)
    manifest_bytes = _read_limited_bytes(
        resolved_manifest, max_bytes=2 * 1024 * 1024, label="Antifilter manifest"
    )
    manifest = _load_json(manifest_bytes, label="Antifilter manifest")
    if not isinstance(manifest, dict):
        raise RuntimeError("Antifilter manifest must be a JSON object")
    if manifest.get("schemaVersion") != ARTIFACT_SCHEMA_VERSION:
        raise RuntimeError("Antifilter manifest schemaVersion is not supported")
    if manifest.get("product") != PRODUCT_CODE:
        raise RuntimeError("Antifilter manifest product does not match Task2")

    generated_at = _parse_utc_timestamp(manifest.get("generatedAt"))
    if max_age_hours > 0:
        max_age = timedelta(hours=max_age_hours)
        if datetime.now(UTC) - generated_at > max_age:
            raise RuntimeError("Antifilter manifest is stale")

    union = manifest.get("union")
    union = union if isinstance(union, dict) else {}
    prefix_count = union.get("prefixCount")
    if not isinstance(prefix_count, int) or prefix_count <= 0:
        raise RuntimeError("Antifilter manifest union.prefixCount must be positive")
    union_sha = union.get("sha256")
    if not isinstance(union_sha, str) or len(union_sha) != 64:
        raise RuntimeError("Antifilter manifest union.sha256 is required")
    ipv6_policy_mode = _ipv6_policy_mode(manifest)
    union_ipv6_prefix_count = _union_family_count(manifest, "ipv6")
    if ipv6_policy_mode == "enabled" and union_ipv6_prefix_count <= 0:
        raise RuntimeError(
            "Antifilter IPv6 policy is enabled but the IPv6 artifact is empty"
        )

    resolved_rules = _artifact_path_from_manifest(
        resolved_manifest, manifest, rules_path
    )
    rules_bytes = _read_limited_bytes(
        resolved_rules,
        max_bytes=16 * 1024 * 1024,
        label="Antifilter Xray rules artifact",
    )
    rules_sha = _sha256_bytes(rules_bytes)
    if rules_sha != _expected_rules_sha256(manifest):
        raise RuntimeError("Antifilter Xray rules artifact checksum mismatch")
    rules_payload = _load_json(rules_bytes, label="Antifilter Xray rules artifact")
    raw_rules = (
        rules_payload.get("rules") if isinstance(rules_payload, dict) else rules_payload
    )
    if not isinstance(raw_rules, list) or not raw_rules:
        raise RuntimeError(
            "Antifilter Xray rules artifact must contain non-empty rules"
        )
    if not all(isinstance(rule, dict) for rule in raw_rules):
        raise RuntimeError("Antifilter Xray rules must be JSON objects")
    actual_ipv6_prefix_count = _actual_raw_rule_ipv6_prefix_count(raw_rules)
    if actual_ipv6_prefix_count != union_ipv6_prefix_count:
        raise RuntimeError(
            "Antifilter manifest IPv6 prefix count does not match the Xray artifact"
        )
    if ipv6_policy_mode == "enabled" and actual_ipv6_prefix_count <= 0:
        raise RuntimeError(
            "Antifilter IPv6 policy is enabled but the IPv6 artifact is empty"
        )
    return AntifilterArtifact(
        manifest_path=resolved_manifest,
        rules_path=resolved_rules,
        manifest_sha256=_sha256_bytes(manifest_bytes),
        rules_sha256=rules_sha,
        generated_at=generated_at,
        union_prefix_count=prefix_count,
        union_ipv6_prefix_count=union_ipv6_prefix_count,
        ipv6_policy_mode=ipv6_policy_mode,
        raw_rules=raw_rules,
    )


def _management_networks() -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
    networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
    for item in MANAGEMENT_AND_SELF_IPS:
        if item.startswith("geoip:"):
            continue
        networks.append(ipaddress.ip_network(item, strict=False))
    return networks


MANAGEMENT_NETWORKS = _management_networks()


def _canonical_exception_ip_matchers(ips: list[Any]) -> list[str]:
    if len(ips) > MAX_EXCEPTION_PREFIXES:
        raise RuntimeError(
            "Antifilter exception rule exceeds the per-rule prefix limit"
        )
    canonical: list[str] = []
    for item in ips:
        if not isinstance(item, str) or not item:
            raise RuntimeError(
                "Antifilter exception rules must contain non-empty ip matchers"
            )
        try:
            network = ipaddress.ip_network(item, strict=False)
        except ValueError as exc:
            raise RuntimeError(
                f"Antifilter exception matcher is not a CIDR: {item}"
            ) from exc
        if network.prefixlen == 0:
            raise RuntimeError(
                "Antifilter exception rules must not contain wildcard routes"
            )
        if any(
            network.overlaps(management)
            for management in MANAGEMENT_NETWORKS
            if management.version == network.version
        ):
            raise RuntimeError(
                "Antifilter exception rules must not contain management or node networks"
            )
        canonical.append(str(network))
    return canonical


def _normalize_exception_rules(
    raw_rules: list[dict[str, Any]],
    *,
    customer_inbound_tags: list[str] | None = None,
) -> list[dict[str, Any]]:
    if len(raw_rules) > MAX_EXCEPTION_RULES:
        raise RuntimeError("Antifilter exception artifact contains too many rules")
    normalized: list[dict[str, Any]] = []
    total_prefixes = 0
    for index, raw_rule in enumerate(raw_rules, start=1):
        ips = raw_rule.get("ip")
        if not isinstance(ips, list) or not ips:
            raise RuntimeError(
                "Antifilter exception rules must contain non-empty ip matchers"
            )
        canonical_ips = _canonical_exception_ip_matchers(ips)
        total_prefixes += len(canonical_ips)
        if total_prefixes > MAX_EXCEPTION_PREFIXES:
            raise RuntimeError(
                "Antifilter exception artifact contains too many prefixes"
            )
        normalized.append(
            {
                "type": "field",
                "ruleTag": raw_rule.get("ruleTag")
                or f"de-exceptions-artifact-{index:04d}",
                "inboundTag": list(customer_inbound_tags or SPB_CUSTOMER_INBOUND_TAGS),
                "ip": canonical_ips,
                "network": "tcp,udp",
                "outboundTag": BRIDGE_OUTBOUND_TAG,
            }
        )
    return normalized


def _bridge_inbound() -> dict[str, Any]:
    return {
        "tag": BRIDGE_INBOUND_TAG,
        "port": BRIDGE_PORT,
        "listen": DE_BRIDGE_LISTEN_ADDRESS,
        "protocol": "shadowsocks",
        "settings": {
            "clients": [],
            "method": BRIDGE_AEAD_METHOD,
            "network": "tcp,udp",
        },
        "sniffing": {
            "enabled": True,
            "destOverride": ["http", "tls", "quic"],
            "routeOnly": True,
        },
    }


def _require_outbound(
    config: dict[str, Any], tag: str, protocol: str
) -> dict[str, Any]:
    outbound = next(
        (
            item
            for item in config.get("outbounds", [])
            if isinstance(item, dict) and item.get("tag") == tag
        ),
        None,
    )
    if outbound is None or outbound.get("protocol") != protocol:
        raise RuntimeError(f"Base profile must contain {tag} {protocol} outbound")
    return copy.deepcopy(outbound)


def _clone_spb_customer_inbounds(
    base_config: dict[str, Any],
    task2_listen_address: str | None,
    *,
    xhttp_path: str = SPB_XHTTP_PATH,
) -> list[dict[str, Any]]:
    inbounds_by_tag = {
        inbound.get("tag"): inbound
        for inbound in base_config.get("inbounds", [])
        if isinstance(inbound, dict) and inbound.get("tag")
    }
    cloned: list[dict[str, Any]] = []
    for source_tag, target_tag in OLD_TO_SPB_TAG.items():
        source = inbounds_by_tag.get(source_tag) or inbounds_by_tag.get(target_tag)
        if source is None:
            raise RuntimeError(f"SPB base profile is missing inbound {source_tag}")
        inbound = copy.deepcopy(source)
        inbound["tag"] = target_tag
        if task2_listen_address:
            inbound["listen"] = task2_listen_address
        expected_port = SPB_REQUIRED_INBOUND_PORTS[target_tag]
        inbound["port"] = expected_port
        if target_tag == "SPB_EXCEPTIONS_XHTTP_REALITY_8443":
            stream_settings = inbound.get("streamSettings")
            if not isinstance(stream_settings, dict):
                raise RuntimeError("Task2 XHTTP inbound has no streamSettings")
            if stream_settings.get("network") != "xhttp":
                raise RuntimeError("Task2 XHTTP inbound must use xhttp network")
            xhttp_settings = stream_settings.get("xhttpSettings")
            if not isinstance(xhttp_settings, dict):
                raise RuntimeError("Task2 XHTTP inbound has no xhttpSettings")
            xhttp_settings["path"] = xhttp_path
        cloned.append(inbound)
    return cloned


def _replace_tagged(items: Any, replacements: list[dict[str, Any]]) -> list[Any]:
    items = items if isinstance(items, list) else []
    replacement_tags = {item["tag"] for item in replacements}
    preserved = [
        copy.deepcopy(item)
        for item in items
        if not (isinstance(item, dict) and item.get("tag") in replacement_tags)
    ]
    return [*preserved, *copy.deepcopy(replacements)]


def _task2_preserved_tag(scope: str, source_tag: str) -> str:
    prefix = PRESERVED_TAG_PREFIXES.get(scope)
    if prefix is None:
        raise RuntimeError("Unsupported preserved inbound tag scope")
    if source_tag.startswith(prefix):
        if len(source_tag) > REMNAWAVE_INBOUND_TAG_MAX_LENGTH:
            raise RuntimeError("Existing Task2 preserved inbound tag is too long")
        return source_tag
    normalized = re.sub(r"[^A-Za-z0-9_]+", "_", source_tag).strip("_") or "INBOUND"
    digest = hashlib.sha256(source_tag.encode("utf-8")).hexdigest()[:8]
    max_base_length = REMNAWAVE_INBOUND_TAG_MAX_LENGTH - len(prefix) - len(digest) - 1
    return f"{prefix}{normalized[:max_base_length]}_{digest}"


def _preserved_inbound_tag_map(
    config: dict[str, Any], scope: str, *, exclude_tags: set[str]
) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for inbound in config.get("inbounds", []):
        if not isinstance(inbound, dict) or not inbound.get("tag"):
            continue
        source_tag = str(inbound["tag"])
        if source_tag in exclude_tags:
            continue
        target_tag = _task2_preserved_tag(scope, source_tag)
        if target_tag in mapping.values() and mapping.get(source_tag) != target_tag:
            raise RuntimeError("Preserved inbound tag mapping is not unique")
        mapping[source_tag] = target_tag
    return mapping


def _spb_shared_public_source_tags(
    config: dict[str, Any], active_tags: list[str]
) -> list[str]:
    active_tag_set = set(active_tags)
    selected: dict[int, str] = {}
    for inbound in config.get("inbounds", []):
        if not isinstance(inbound, dict):
            continue
        tag = str(inbound.get("tag") or "")
        port = int(inbound.get("port") or 0)
        if tag not in active_tag_set or inbound.get("protocol") != "vless":
            continue
        if port not in {443, 8443}:
            continue
        network = str((inbound.get("streamSettings") or {}).get("network") or "")
        if port == 443 and network not in {"raw", "tcp"}:
            continue
        if port == 8443 and network != "xhttp":
            continue
        if port in selected:
            raise RuntimeError(f"SPB shared IPv4 port {port} maps to multiple active inbounds")
        selected[port] = tag
    if set(selected) != {443, 8443}:
        raise RuntimeError("SPB shared IPv4 RAW 443 and XHTTP 8443 inbounds are required")
    return [selected[443], selected[8443]]


def _spb_shared_xhttp_path(
    config: dict[str, Any], shared_public_source_tags: list[str]
) -> str:
    shared_tags = set(shared_public_source_tags)
    candidates: list[str] = []
    for inbound in config.get("inbounds", []):
        if not isinstance(inbound, dict) or inbound.get("tag") not in shared_tags:
            continue
        if int(inbound.get("port") or 0) != 8443:
            continue
        stream_settings = inbound.get("streamSettings")
        xhttp_settings = (
            stream_settings.get("xhttpSettings")
            if isinstance(stream_settings, dict)
            else None
        )
        path = xhttp_settings.get("path") if isinstance(xhttp_settings, dict) else None
        if isinstance(path, str) and path.startswith("/") and len(path) <= 256:
            candidates.append(path)
    if len(set(candidates)) != 1:
        raise RuntimeError("SPB shared IPv4 XHTTP inbound must have one valid path")
    return candidates[0]


def _rewrite_inbound_tag_references(value: Any, mapping: dict[str, str]) -> Any:
    if isinstance(value, list):
        return [_rewrite_inbound_tag_references(item, mapping) for item in value]
    if not isinstance(value, dict):
        return copy.deepcopy(value)
    rewritten: dict[str, Any] = {}
    for key, item in value.items():
        if key == "inboundTag" and isinstance(item, str):
            rewritten[key] = mapping.get(item, item)
        elif key == "inboundTag" and isinstance(item, list):
            rewritten[key] = [mapping.get(str(tag), str(tag)) for tag in item]
        else:
            rewritten[key] = _rewrite_inbound_tag_references(item, mapping)
    return rewritten


def _rename_preserved_inbounds(
    config: dict[str, Any], mapping: dict[str, str]
) -> dict[str, Any]:
    renamed = _rewrite_inbound_tag_references(config, mapping)
    for inbound in renamed.get("inbounds", []):
        if isinstance(inbound, dict) and inbound.get("tag") in mapping:
            inbound["tag"] = mapping[str(inbound["tag"])]
    return renamed


def _routing_rules(config: dict[str, Any]) -> list[dict[str, Any]]:
    routing = config.get("routing")
    routing = routing if isinstance(routing, dict) else {}
    return [
        copy.deepcopy(rule)
        for rule in routing.get("rules", [])
        if isinstance(rule, dict)
    ]


def _rule_inbound_tags(rule: dict[str, Any]) -> set[str]:
    value = rule.get("inboundTag")
    if isinstance(value, list):
        return {str(item) for item in value}
    if isinstance(value, str):
        return {value}
    return set()


def _is_task2_de_rule(rule: dict[str, Any]) -> bool:
    return BRIDGE_INBOUND_TAG in _rule_inbound_tags(rule)


def _is_task2_spb_rule(rule: dict[str, Any]) -> bool:
    if str(rule.get("ruleTag") or "").startswith("task2-"):
        return True
    inbound_tags = _rule_inbound_tags(rule)
    if inbound_tags and rule.get("outboundTag") == BRIDGE_OUTBOUND_TAG:
        return True
    if inbound_tags and inbound_tags.issubset(SPB_CUSTOMER_INBOUND_TAG_SET):
        return True
    return inbound_tags == {BRIDGE_INBOUND_TAG} and str(
        rule.get("ruleTag") or ""
    ).startswith("task2-")


def _routing_with_prepended_rules(
    config: dict[str, Any],
    task2_rules: list[dict[str, Any]],
    *,
    drop_rule: Any,
) -> dict[str, Any]:
    routing = copy.deepcopy(
        config.get("routing") if isinstance(config.get("routing"), dict) else {}
    )
    existing_rules = [rule for rule in _routing_rules(config) if not drop_rule(rule)]
    routing["rules"] = [*copy.deepcopy(task2_rules), *existing_rules]
    return routing


def _build_de_bridge_config(
    base_config: dict[str, Any], preserved_tag_map: dict[str, str] | None = None
) -> dict[str, Any]:
    config = _rename_preserved_inbounds(base_config, preserved_tag_map or {})
    _require_outbound(config, "DIRECT", "freedom")
    _require_outbound(config, "BLOCK", "blackhole")
    config["inbounds"] = _replace_tagged(
        config.get("inbounds", []), [_bridge_inbound()]
    )
    bridge_rules = [
        {
            "type": "field",
            "ruleTag": "task2-de-bridge-management-block",
            "inboundTag": [BRIDGE_INBOUND_TAG],
            "ip": MANAGEMENT_AND_SELF_IPS,
            "outboundTag": "BLOCK",
        },
        {
            "type": "field",
            "ruleTag": "task2-de-bridge-direct",
            "inboundTag": [BRIDGE_INBOUND_TAG],
            "network": "tcp,udp",
            "outboundTag": "DIRECT",
        },
    ]
    config["routing"] = _routing_with_prepended_rules(
        config, bridge_rules, drop_rule=_is_task2_de_rule
    )
    _validate_no_empty_routing_rules(config)
    return config


def _bridge_outbound(bridge_password: str, de_upstream_address: str) -> dict[str, Any]:
    if BRIDGE_AEAD_METHOD not in ALLOWED_AEAD_METHODS:
        raise RuntimeError("Bridge Shadowsocks method must be AEAD")
    return {
        "tag": BRIDGE_OUTBOUND_TAG,
        "protocol": "shadowsocks",
        "settings": {
            "servers": [
                {
                    "address": de_upstream_address,
                    "port": BRIDGE_PORT,
                    "password": bridge_password,
                    "method": BRIDGE_AEAD_METHOD,
                    "level": 0,
                }
            ]
        },
    }


def _static_spb_rules(
    exception_rules: list[dict[str, Any]],
    ipv6_policy_mode: str,
    customer_inbound_tags: list[str] | None = None,
) -> list[dict[str, Any]]:
    resolved_customer_tags = list(customer_inbound_tags or SPB_CUSTOMER_INBOUND_TAGS)
    scoped = {"type": "field", "inboundTag": resolved_customer_tags}
    rules = [
        {
            **scoped,
            "ruleTag": "task2-management-private-self-block",
            "ip": MANAGEMENT_AND_SELF_IPS,
            "outboundTag": "BLOCK",
        },
        {
            "type": "field",
            "ruleTag": "task2-bridge-inbound-isolation-block",
            "inboundTag": [BRIDGE_INBOUND_TAG],
            "network": "tcp,udp",
            "outboundTag": "BLOCK",
        },
        {
            **scoped,
            "ruleTag": "task2-bittorrent-protocol-block",
            "protocol": ["bittorrent"],
            "outboundTag": "BLOCK",
        },
        {
            **scoped,
            "ruleTag": "task2-torrent-domain-block",
            "domain": [f"domain:{domain}" for domain in BLOCKED_TORRENT_DOMAINS],
            "outboundTag": "BLOCK",
        },
        {
            **scoped,
            "ruleTag": "task2-ads-trackers-block",
            "domain": ["geosite:category-ads-all"],
            "outboundTag": "BLOCK",
        },
        {
            **scoped,
            "ruleTag": "task2-tor-best-effort-block",
            "domain": [
                "domain:torproject.org",
                "domain:torproject.net",
                r"regexp:\.onion$",
            ],
            "outboundTag": "BLOCK",
        },
        {
            **scoped,
            "ruleTag": "task2-smtp-abuse-port-block",
            "network": "tcp",
            "port": "25,465,587",
            "outboundTag": "BLOCK",
        },
    ]
    if ipv6_policy_mode in IPV6_BLOCK_POLICY_MODES:
        rules.append(
            {
                **scoped,
                "ruleTag": "task2-ipv6-policy-block",
                "ip": ["::/0"],
                "outboundTag": "BLOCK",
            }
        )
    rules.extend(exception_rules)
    rules.append(
        {
            "type": "field",
            "ruleTag": "task2-final-spb-direct",
            "inboundTag": resolved_customer_tags,
            "network": "tcp,udp",
            "outboundTag": "DIRECT",
        },
    )
    return rules


def _build_spb_customer_config(
    base_config: dict[str, Any],
    bridge_password: str,
    de_upstream_address: str,
    artifact_rules: list[dict[str, Any]],
    *,
    ipv6_policy_mode: str,
    task2_listen_address: str | None,
    preserved_tag_map: dict[str, str] | None = None,
    customer_inbound_tags: list[str] | None = None,
    shared_xhttp_path: str = SPB_XHTTP_PATH,
) -> dict[str, Any]:
    if ipv6_policy_mode not in IPV6_POLICY_MODES:
        raise RuntimeError("Unsupported Antifilter IPv6 policy mode")
    _require_outbound(base_config, "DIRECT", "freedom")
    _require_outbound(base_config, "BLOCK", "blackhole")
    exception_rules = _normalize_exception_rules(
        artifact_rules,
        customer_inbound_tags=customer_inbound_tags,
    )
    config = copy.deepcopy(base_config)
    config["inbounds"] = _replace_tagged(
        config.get("inbounds", []),
        _clone_spb_customer_inbounds(
            base_config,
            task2_listen_address,
            xhttp_path=shared_xhttp_path,
        ),
    )
    config = _rename_preserved_inbounds(config, preserved_tag_map or {})
    config["outbounds"] = _replace_tagged(
        config.get("outbounds", []),
        [_bridge_outbound(bridge_password, de_upstream_address)],
    )
    config["routing"] = _routing_with_prepended_rules(
        config,
        _static_spb_rules(
            exception_rules,
            ipv6_policy_mode,
            customer_inbound_tags=customer_inbound_tags,
        ),
        drop_rule=_is_task2_spb_rule,
    )
    config["routing"]["domainStrategy"] = "IPOnDemand"
    if ipv6_policy_mode in IPV6_BLOCK_POLICY_MODES:
        dns = copy.deepcopy(
            config.get("dns") if isinstance(config.get("dns"), dict) else {}
        )
        dns["queryStrategy"] = "UseIPv4"
        if not isinstance(dns.get("servers"), list) or not dns["servers"]:
            dns["servers"] = ["localhost"]
        config["dns"] = dns
    _validate_no_empty_routing_rules(config)
    _validate_final_direct_rule(config, customer_inbound_tags=customer_inbound_tags)
    return config


def _validate_no_empty_routing_rules(config: dict[str, Any]) -> None:
    match_keys = {"inboundTag", "ip", "domain", "protocol", "network", "port"}
    for index, rule in enumerate(config.get("routing", {}).get("rules", []), start=1):
        if not isinstance(rule, dict):
            raise RuntimeError(f"Routing rule {index} is not an object")
        if not any(
            key in rule and rule[key] not in (None, [], "") for key in match_keys
        ):
            raise RuntimeError(f"Routing rule {index} has no matcher")
        if not rule.get("outboundTag"):
            raise RuntimeError(f"Routing rule {index} has no outboundTag")


def _validate_final_direct_rule(
    config: dict[str, Any], *, customer_inbound_tags: list[str] | None = None
) -> None:
    rules = config.get("routing", {}).get("rules", [])
    if not rules:
        raise RuntimeError("SPB profile routing rules are empty")
    task2_rules = [
        rule for rule in rules if isinstance(rule, dict) and _is_task2_spb_rule(rule)
    ]
    expected = {
        "type": "field",
        "ruleTag": "task2-final-spb-direct",
        "inboundTag": list(customer_inbound_tags or SPB_CUSTOMER_INBOUND_TAGS),
        "network": "tcp,udp",
        "outboundTag": "DIRECT",
    }
    if not task2_rules or task2_rules[-1] != expected:
        raise RuntimeError("SPB profile final DIRECT rule is not exactly scoped")


def _profile_inbound_uuid_by_tag(profile: dict[str, Any] | None) -> dict[str, str]:
    if not isinstance(profile, dict):
        return {}
    return {
        str(item["tag"]): str(item["uuid"])
        for item in profile.get("inbounds", [])
        if isinstance(item, dict) and item.get("tag") and item.get("uuid")
    }


def _profile_inbound_tag_by_uuid(profile: dict[str, Any] | None) -> dict[str, str]:
    return {
        inbound_uuid: tag
        for tag, inbound_uuid in _profile_inbound_uuid_by_tag(profile).items()
    }


def _active_inbound_tags(
    profile: dict[str, Any],
    node: dict[str, Any],
    *,
    exclude_tags: set[str],
) -> list[str]:
    tag_by_uuid = _profile_inbound_tag_by_uuid(profile)
    active_uuids = (
        _normalize_node_config_profile(node.get("configProfile")).get("activeInbounds")
        or []
    )
    tags: list[str] = []
    for inbound_uuid in active_uuids:
        tag = tag_by_uuid.get(str(inbound_uuid))
        if tag and tag not in exclude_tags and tag not in tags:
            tags.append(tag)
    if tags:
        return tags
    return [
        tag for tag in _profile_inbound_uuid_by_tag(profile) if tag not in exclude_tags
    ]


def _mapped_active_inbounds(
    tag_to_uuid: dict[str, str],
    preserved_tags: list[str],
    added_tags: list[str],
) -> list[str]:
    ordered_tags: list[str] = []
    for tag in [*preserved_tags, *added_tags]:
        if tag not in ordered_tags:
            ordered_tags.append(tag)
    return _ordered_inbound_uuids(tag_to_uuid, ordered_tags)


def _ordered_active_tags(preserved_tags: list[str], added_tags: list[str]) -> list[str]:
    ordered_tags: list[str] = []
    for tag in [*preserved_tags, *added_tags]:
        if tag not in ordered_tags:
            ordered_tags.append(tag)
    return ordered_tags


def _validate_dedicated_listen_address(address: str | None) -> str | None:
    if address is None or not str(address).strip():
        return None
    normalized = str(address).strip()
    try:
        parsed = ipaddress.ip_address(normalized)
    except ValueError as exc:
        raise RuntimeError("SPB Task2 listen address must be an IP address") from exc
    if parsed.is_unspecified:
        raise RuntimeError("SPB Task2 listen address must not be wildcard")
    return str(parsed)


ListenAddress = ipaddress.IPv4Address | ipaddress.IPv6Address


def _listen_address_for_conflict(value: object) -> ListenAddress | None:
    if value is None or not str(value).strip():
        return None
    normalized = str(value).strip()
    if normalized.startswith("[") and normalized.endswith("]"):
        normalized = normalized[1:-1]
    try:
        parsed = ipaddress.ip_address(normalized)
    except ValueError:
        return None
    if parsed.is_unspecified:
        return None
    return parsed


def _listen_addresses_conflict(
    left: ListenAddress | None,
    right: ListenAddress | None,
) -> bool:
    if left is None or right is None:
        return True
    return left == right


def _pin_preserved_spb_listeners(
    base_config: dict[str, Any],
    active_tags: list[str],
    listen_address: str | None,
) -> dict[str, Any]:
    config = copy.deepcopy(base_config)
    if listen_address is None:
        return config

    parsed_target = _listen_address_for_conflict(listen_address)
    if parsed_target is None:
        raise RuntimeError("SPB preserved listen address must be a concrete IP")

    active_tag_set = set(active_tags)
    required_ports = SPB_PRESERVED_PUBLIC_PORTS
    pinned = 0
    for inbound in config.get("inbounds", []):
        tag = str(inbound.get("tag") or "")
        if tag not in active_tag_set:
            continue
        try:
            port = int(inbound.get("port", 0))
        except (TypeError, ValueError) as exc:
            raise RuntimeError(f"SPB preserved inbound {tag} has invalid port") from exc
        if port not in required_ports:
            continue
        current = _listen_address_for_conflict(inbound.get("listen"))
        if current is not None and current != parsed_target:
            raise RuntimeError(
                f"SPB preserved inbound {tag} already uses a different concrete listen address"
            )
        inbound["listen"] = listen_address
        pinned += 1

    if pinned == 0:
        raise RuntimeError(
            "SPB preserved listen address did not match an active 443/8443 inbound"
        )
    return config


def _validate_no_active_listener_conflicts(
    config: dict[str, Any], active_tags: list[str], *, label: str
) -> None:
    active_tag_set = set(active_tags)
    listeners: list[tuple[str, int, ListenAddress | None]] = []
    for inbound in config.get("inbounds", []):
        if not isinstance(inbound, dict):
            continue
        tag = str(inbound.get("tag") or "")
        if tag not in active_tag_set:
            continue
        try:
            port = int(inbound.get("port", 0))
        except (TypeError, ValueError) as exc:
            raise RuntimeError(
                f"{label} active inbound {tag} has invalid port"
            ) from exc
        if port <= 0:
            continue
        listen = _listen_address_for_conflict(inbound.get("listen"))
        for existing_tag, existing_port, existing_listen in listeners:
            if existing_port == port and _listen_addresses_conflict(
                existing_listen, listen
            ):
                raise RuntimeError(
                    f"{label} would activate duplicate Xray listeners on port "
                    f"{port} for {existing_tag} and {tag}; set "
                    "--spb-task2-listen-address to a dedicated non-overlapping "
                    "bind IP or use a separate runtime/front-proxy design"
                )
        listeners.append((tag, port, listen))


def _bridge_inbound_uuids_from_profiles(*profiles: dict[str, Any] | None) -> set[str]:
    bridge_uuids: set[str] = set()
    for profile in profiles:
        for tag, inbound_uuid in _profile_inbound_uuid_by_tag(profile).items():
            if tag == BRIDGE_INBOUND_TAG:
                bridge_uuids.add(inbound_uuid)
    return bridge_uuids


def _host_inbound_uuid(host: dict[str, Any]) -> str:
    inbound = host.get("inbound") if isinstance(host, dict) else None
    inbound = inbound if isinstance(inbound, dict) else {}
    for value in (
        inbound.get("configProfileInboundUuid"),
        inbound.get("config_profile_inbound_uuid"),
        inbound.get("inboundUuid"),
        inbound.get("inbound_uuid"),
        inbound.get("uuid"),
        host.get("configProfileInboundUuid"),
        host.get("config_profile_inbound_uuid"),
        host.get("inboundUuid"),
        host.get("inbound_uuid"),
    ):
        if value:
            return str(value)
    return ""


def _validate_no_public_bridge_hosts(
    hosts: list[dict[str, Any]], *profiles: dict[str, Any] | None
) -> None:
    bridge_inbound_uuids = _bridge_inbound_uuids_from_profiles(*profiles)
    for host in hosts:
        if _host_inbound_uuid(host) in bridge_inbound_uuids:
            raise RuntimeError("Bridge inbound must not have a public Remnawave Host")


def _validate_bridge_port_available(profiles: list[dict[str, Any]]) -> None:
    for profile in profiles:
        for inbound in profile.get("inbounds", []):
            if not isinstance(inbound, dict):
                continue
            try:
                port = int(inbound.get("port", 0))
            except (TypeError, ValueError):
                continue
            tag = str(inbound.get("tag") or "")
            if port == BRIDGE_PORT and tag != BRIDGE_INBOUND_TAG:
                raise RuntimeError(
                    f"Bridge port {BRIDGE_PORT} is already used by inbound {tag}"
                )


def _validate_local_bridge_socket_available(port: int = BRIDGE_PORT) -> None:
    sockets: list[socket.socket] = []
    try:
        if port > 0:
            probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                probe.settimeout(0.2)
                if probe.connect_ex(("127.0.0.1", port)) == 0:
                    raise RuntimeError(
                        f"Bridge port {port} is already in use locally for TCP"
                    )
            finally:
                probe.close()
        for sock_type, label in (
            (socket.SOCK_STREAM, "TCP"),
            (socket.SOCK_DGRAM, "UDP"),
        ):
            sock = socket.socket(socket.AF_INET, sock_type)
            sockets.append(sock)
            sock.bind(("0.0.0.0", port))
        return
    except OSError as exc:
        raise RuntimeError(
            f"Bridge port {port} is already in use locally for TCP or UDP"
        ) from exc
    finally:
        for sock in sockets:
            sock.close()


def _inbound_uuids(squad: dict[str, Any]) -> list[str]:
    return [
        item["uuid"] if isinstance(item, dict) else str(item)
        for item in squad.get("inbounds", [])
    ]


def _squad_uuids(user: dict[str, Any]) -> list[str]:
    return [
        item["uuid"] if isinstance(item, dict) else str(item)
        for item in user.get("activeInternalSquads", [])
    ]


def _isolated_squad_inbounds(inbound_uuid: str) -> list[str]:
    return [inbound_uuid]


def _isolated_user_squads(squad_uuid: str) -> list[str]:
    return [squad_uuid]


def _validate_existing_bridge_user_isolation(
    user: dict[str, Any] | None,
    squad: dict[str, Any] | None,
) -> None:
    if user is None:
        return
    allowed = {str(squad["uuid"])} if squad is not None else set()
    assigned = set(_squad_uuids(user))
    if not assigned.issubset(allowed):
        raise RuntimeError(
            "Existing Task2 bridge user has non-bridge squad assignments"
        )
    if user.get("externalSquadUuid") or user.get("externalSquad"):
        raise RuntimeError("Existing Task2 bridge user must not have an external squad")


def _validate_bridge_squad_inbound_isolation(
    squad: dict[str, Any] | None,
    allowed_bridge_inbound_uuids: set[str],
) -> None:
    if squad is None:
        return
    assigned = set(_inbound_uuids(squad))
    if assigned and not assigned.issubset(allowed_bridge_inbound_uuids):
        raise RuntimeError(
            "Existing Task2 bridge squad has non-bridge inbound assignments"
        )


def _normalize_node_config_profile(
    config_profile: dict[str, Any] | None,
) -> dict[str, Any]:
    config_profile = config_profile or {}
    return {
        "activeConfigProfileUuid": config_profile.get("activeConfigProfileUuid"),
        "activeInbounds": [
            item["uuid"] if isinstance(item, dict) else str(item)
            for item in config_profile.get("activeInbounds", [])
        ],
    }


def _task2_host_remarks() -> set[str]:
    return {
        str(remark)
        for spec in SPB_PUBLIC_HOST_SPECS
        for remark in [spec["remark"], *spec.get("legacy_remarks", [])]
    }


def _safe_host_snapshot(host: dict[str, Any]) -> dict[str, Any]:
    return copy.deepcopy(host)


def _host_payload(
    spec: dict[str, Any], public_host: str, profile_uuid: str, inbound_uuid: str
) -> dict[str, Any]:
    return {
        "remark": spec["remark"],
        "address": public_host,
        "port": spec["port"],
        "path": spec["path"],
        "inbound": {
            "configProfileUuid": profile_uuid,
            "configProfileInboundUuid": inbound_uuid,
        },
        "isDisabled": False,
        "serverDescription": spec["server_description"],
        "tag": spec["host_tag"],
        "viewPosition": spec["view_position"],
    }


async def _upsert_spb_public_hosts(
    api: RemnawaveApi,
    hosts: list[dict[str, Any]],
    public_host: str,
    profile_uuid: str,
    tag_to_uuid: dict[str, str],
    *,
    xhttp_path: str = SPB_XHTTP_PATH,
) -> list[dict[str, Any]]:
    existing_by_remark = {
        host.get("remark"): host
        for host in hosts
        if host.get("remark") in _task2_host_remarks()
    }
    upserted: list[dict[str, Any]] = []
    for spec in SPB_PUBLIC_HOST_SPECS:
        spec = {
            **spec,
            "path": xhttp_path if spec["inbound_tag"] == "SPB_EXCEPTIONS_XHTTP_REALITY_8443" else spec["path"],
        }
        inbound_uuid = tag_to_uuid.get(str(spec["inbound_tag"]))
        if not inbound_uuid:
            raise RuntimeError(
                f"SPB profile is missing public Host inbound {spec['inbound_tag']}"
            )
        payload = _host_payload(spec, public_host, profile_uuid, inbound_uuid)
        existing = existing_by_remark.get(spec["remark"])
        if existing is None:
            existing = next(
                (
                    existing_by_remark.get(legacy_remark)
                    for legacy_remark in spec.get("legacy_remarks", [])
                    if existing_by_remark.get(legacy_remark) is not None
                ),
                None,
            )
        if existing:
            result = await api.request(
                "PATCH",
                "/hosts",
                json={**payload, "uuid": existing["uuid"]},
            )
        else:
            result = await api.request("POST", "/hosts", json=payload)
        upserted.append(result if isinstance(result, dict) else payload)
    return upserted


def _host_snapshots_for_profile(
    hosts: list[dict[str, Any]],
    profile: dict[str, Any],
    *,
    exclude_tags: set[str],
) -> list[dict[str, Any]]:
    tag_by_uuid = _profile_inbound_tag_by_uuid(profile)
    snapshots: list[dict[str, Any]] = []
    for host in hosts:
        tag = tag_by_uuid.get(_host_inbound_uuid(host))
        if tag and tag not in exclude_tags:
            snapshots.append(_safe_host_snapshot(host))
    return snapshots


def _host_remap_payload(
    host: dict[str, Any],
    profile_uuid: str,
    inbound_uuid: str,
    *,
    exclude_from_squad_uuid: str | None = None,
    remove_from_squad_uuid: str | None = None,
) -> dict[str, Any]:
    payload = {
        "uuid": host["uuid"],
        "inbound": {
            "configProfileUuid": profile_uuid,
            "configProfileInboundUuid": inbound_uuid,
        },
    }
    current_exclusions = {
        str(item) for item in host.get("excludedInternalSquads", []) if item
    }
    desired_exclusions = set(current_exclusions)
    if exclude_from_squad_uuid is not None:
        desired_exclusions.add(exclude_from_squad_uuid)
    if remove_from_squad_uuid is not None:
        desired_exclusions.discard(remove_from_squad_uuid)
    if desired_exclusions != current_exclusions:
        payload["excludedInternalSquads"] = sorted(desired_exclusions)
    return payload


async def _remap_profile_hosts(
    api: RemnawaveApi,
    hosts: list[dict[str, Any]],
    source_profile: dict[str, Any],
    target_profile: dict[str, Any],
    *,
    exclude_tags: set[str],
    tag_map: dict[str, str] | None = None,
    exclude_from_squad_uuid: str | None = None,
    remove_from_squad_uuid: str | None = None,
) -> None:
    source_tag_by_uuid = _profile_inbound_tag_by_uuid(source_profile)
    target_uuid_by_tag = _profile_inbound_uuid_by_tag(target_profile)
    for host in hosts:
        current_uuid = _host_inbound_uuid(host)
        source_tag = source_tag_by_uuid.get(current_uuid)
        if not source_tag or source_tag in exclude_tags:
            continue
        target_uuid = target_uuid_by_tag.get(
            (tag_map or {}).get(source_tag, source_tag)
        )
        if not target_uuid:
            raise RuntimeError(
                f"Superset profile is missing preserved inbound tag {source_tag}"
            )
        current_exclusions = {
            str(item) for item in host.get("excludedInternalSquads", []) if item
        }
        needs_exclusion = (
            exclude_from_squad_uuid is not None
            and exclude_from_squad_uuid not in current_exclusions
        )
        needs_exclusion_removal = (
            remove_from_squad_uuid is not None
            and remove_from_squad_uuid in current_exclusions
        )
        if target_uuid != current_uuid or needs_exclusion or needs_exclusion_removal:
            await api.request(
                "PATCH",
                "/hosts",
                json=_host_remap_payload(
                    host,
                    target_profile["uuid"],
                    target_uuid,
                    exclude_from_squad_uuid=exclude_from_squad_uuid,
                    remove_from_squad_uuid=remove_from_squad_uuid,
                ),
            )


async def _restore_host_snapshots(
    api: RemnawaveApi, snapshots: list[dict[str, Any]]
) -> None:
    for host in snapshots:
        if not isinstance(host, dict) or not host.get("uuid"):
            continue
        inbound = host.get("inbound")
        if not isinstance(inbound, dict) or not all(
            inbound.get(key)
            for key in ("configProfileUuid", "configProfileInboundUuid")
        ):
            raise RuntimeError("Host rollback snapshot is missing inbound identity")
        payload = {
            "uuid": host["uuid"],
            "inbound": {
                "configProfileUuid": inbound["configProfileUuid"],
                "configProfileInboundUuid": inbound["configProfileInboundUuid"],
            },
        }
        payload["excludedInternalSquads"] = host.get("excludedInternalSquads", [])
        await api.request(
            "PATCH",
            "/hosts",
            json=payload,
        )


async def _rollback_spb_public_hosts(
    api: RemnawaveApi, manifest: dict[str, Any]
) -> None:
    snapshots = manifest.get("spbHosts")
    snapshots = snapshots if isinstance(snapshots, list) else []
    snapshot_by_remark = {
        snapshot.get("remark"): snapshot
        for snapshot in snapshots
        if isinstance(snapshot, dict) and snapshot.get("remark")
    }
    hosts = _collection(await api.request("GET", "/hosts"), "hosts")
    current_by_remark = {
        host.get("remark"): host
        for host in hosts
        if host.get("remark") in _task2_host_remarks()
    }
    for remark, snapshot in snapshot_by_remark.items():
        current = current_by_remark.get(remark)
        if current and snapshot.get("uuid"):
            await api.request(
                "PATCH", "/hosts", json={**snapshot, "uuid": snapshot["uuid"]}
            )
    for remark, current in current_by_remark.items():
        if remark not in snapshot_by_remark and current.get("uuid"):
            await _delete_if_present(api, f"/hosts/{current['uuid']}")


def _validate_remnawave_url(base_url: str, allowed_hosts: list[str]) -> None:
    parsed = urlsplit(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise RuntimeError("Remnawave URL must use http or https with a hostname")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise RuntimeError(
            "Remnawave URL must not contain credentials, query, or fragment"
        )
    if parsed.path.rstrip("/") not in {"", "/api"}:
        raise RuntimeError("Remnawave URL path must be empty or /api")
    normalized_allowed = {host.casefold() for host in allowed_hosts}
    hostname = parsed.hostname.casefold()
    if hostname not in normalized_allowed:
        raise RuntimeError("Remnawave URL hostname is not in the operator allowlist")
    if parsed.scheme == "http" and hostname not in INTERNAL_HTTP_REMNAWAVE_HOSTS:
        raise RuntimeError("Remnawave URL must use https outside local/internal hosts")


def _validate_manifest_path(path: Path) -> Path:
    resolved = path.expanduser().resolve(strict=False)
    if any(part.casefold() == ".codex" for part in resolved.parts):
        raise RuntimeError("Rollback manifest must not be under a .codex directory")
    if REPO_ROOT is not None and (
        resolved == REPO_ROOT or REPO_ROOT in resolved.parents
    ):
        raise RuntimeError("Rollback manifest must be outside the repository")
    return resolved


def _write_manifest(path: Path, payload: dict[str, Any]) -> None:
    if path.exists() and path.is_symlink():
        raise RuntimeError("Rollback manifest path must not be a symlink")
    path.parent.mkdir(parents=True, exist_ok=True)
    if os.name != "nt" and path.parent.stat().st_mode & 0o002:
        raise RuntimeError(
            "Rollback manifest parent directory must not be world-writable"
        )

    disk_payload = copy.deepcopy(payload)
    if not isinstance(disk_payload, dict):
        raise RuntimeError("Rollback manifest payload must be an object")

    temp_name: str | None = None
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temp_path = Path(temp_name)
    try:
        os.chmod(temp_path, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(disk_payload, handle, ensure_ascii=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
        os.chmod(path, 0o600)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def _read_manifest(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError("Rollback manifest does not exist")
    if os.name != "nt" and path.stat().st_mode & 0o077:
        raise RuntimeError("Rollback manifest permissions must be 0600")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("version") != 1:
        raise RuntimeError("Rollback manifest version is not supported")
    return payload


def _checkpoint(path: Path, manifest: dict[str, Any], phase: str) -> None:
    manifest["phase"] = phase
    _write_manifest(path, manifest)


async def _get_user(api: RemnawaveApi, username: str) -> dict[str, Any] | None:
    try:
        data = await api.request("GET", f"/users/by-username/{username}")
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in {404, 409}:
            return None
        raise
    if isinstance(data, list):
        return data[0] if data else None
    return data if isinstance(data, dict) else None


async def _delete_if_present(api: RemnawaveApi, path: str) -> None:
    try:
        await api.request("DELETE", path)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code != 404:
            raise


async def _restore_profile_or_delete(
    api: RemnawaveApi,
    *,
    profile: dict[str, Any] | None,
    profile_name: str,
) -> None:
    if profile is not None:
        await api.request(
            "PATCH",
            "/config-profiles",
            json={
                "uuid": profile["uuid"],
                "name": profile["name"],
                "config": profile["config"],
            },
        )
        return
    profiles = _collection(
        await api.request("GET", "/config-profiles"), "configProfiles"
    )
    created = next(
        (item for item in profiles if item.get("name") == profile_name), None
    )
    if created:
        await _delete_if_present(api, f"/config-profiles/{created['uuid']}")


async def _rollback(
    api: RemnawaveApi, manifest: dict[str, Any], manifest_path: Path
) -> dict[str, Any]:
    if manifest.get("phase") == "rolled_back":
        return {"mode": "rollback", "status": "already_rolled_back"}
    spb_node = manifest.get("spbNode")
    if spb_node:
        await api.request(
            "PATCH",
            "/nodes",
            json={
                "uuid": spb_node["uuid"],
                "configProfile": _normalize_node_config_profile(
                    spb_node["configProfile"]
                ),
            },
        )
    customer_squad = manifest.get("customerSquad")
    if customer_squad:
        await api.request(
            "PATCH",
            "/internal-squads",
            json={
                "uuid": customer_squad["uuid"],
                "inbounds": customer_squad["inbounds"],
            },
        )
    external_squad = manifest.get("externalSquad")
    if external_squad:
        await api.request(
            "PATCH",
            "/external-squads",
            json={
                "uuid": external_squad["uuid"],
                "responseHeaders": external_squad["responseHeaders"],
            },
        )
    await _restore_host_snapshots(api, manifest.get("spbRemappedHosts") or [])
    await _rollback_spb_public_hosts(api, manifest)
    await _restore_profile_or_delete(
        api,
        profile=manifest.get("spbProfile"),
        profile_name=manifest["spbProfileName"],
    )
    if spb_node:
        await api.request(
            "POST",
            f"/nodes/{spb_node['uuid']}/actions/restart",
            json={"forceRestart": True},
        )

    bridge_user = manifest.get("bridgeUser")
    if bridge_user:
        await api.request(
            "PATCH",
            "/users",
            json={
                "uuid": bridge_user["uuid"],
                "activeInternalSquads": bridge_user["activeInternalSquads"],
                "externalSquadUuid": None,
            },
        )
    else:
        current_user = await _get_user(api, manifest["bridgeUsername"])
        if current_user:
            await _delete_if_present(api, f"/users/{current_user['uuid']}")

    bridge_squad = manifest.get("bridgeSquad")
    if bridge_squad:
        await api.request(
            "PATCH",
            "/internal-squads",
            json={"uuid": bridge_squad["uuid"], "inbounds": bridge_squad["inbounds"]},
        )
    else:
        squads = _collection(
            await api.request("GET", "/internal-squads"), "internalSquads"
        )
        created_squad = next(
            (
                item
                for item in squads
                if item.get("name") == manifest["bridgeSquadName"]
            ),
            None,
        )
        if created_squad:
            await _delete_if_present(api, f"/internal-squads/{created_squad['uuid']}")

    de_node = manifest.get("deNode")
    if de_node:
        await api.request(
            "PATCH",
            "/nodes",
            json={
                "uuid": de_node["uuid"],
                "configProfile": _normalize_node_config_profile(
                    de_node["configProfile"]
                ),
            },
        )
    await _restore_host_snapshots(api, manifest.get("deRemappedHosts") or [])
    await _restore_profile_or_delete(
        api,
        profile=manifest.get("deBridgeProfile"),
        profile_name=manifest["deBridgeProfileName"],
    )
    if de_node:
        await api.request(
            "POST",
            f"/nodes/{de_node['uuid']}/actions/restart",
            json={"forceRestart": True},
        )

    _checkpoint(manifest_path, manifest, "rolled_back")
    return {"mode": "rollback", "status": "rolled_back"}


def _find_by_name(items: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    return next((item for item in items if item.get("name") == name), None)


def _find_node(nodes: list[dict[str, Any]], address: str) -> dict[str, Any]:
    node = next((item for item in nodes if item.get("address") == address), None)
    if node is None:
        raise RuntimeError(f"Remnawave node {address} was not found")
    return node


async def _node_source_profile(
    api: RemnawaveApi,
    node: dict[str, Any],
    base_profile: dict[str, Any],
) -> dict[str, Any]:
    active_uuid = _normalize_node_config_profile(node.get("configProfile")).get(
        "activeConfigProfileUuid"
    )
    if active_uuid and active_uuid != base_profile.get("uuid"):
        return await api.request("GET", f"/config-profiles/{active_uuid}")
    return base_profile


def _ordered_inbound_uuids(tag_to_uuid: dict[str, str], tags: list[str]) -> list[str]:
    missing = [tag for tag in tags if tag not in tag_to_uuid]
    if missing:
        raise RuntimeError(
            f"Config profile is missing inbound tag(s): {', '.join(missing)}"
        )
    return [tag_to_uuid[tag] for tag in tags]


async def _run(args: argparse.Namespace) -> dict[str, Any]:
    token = os.environ.get("REMNAWAVE_TOKEN") or os.environ.get("REMNAWAVE_API_TOKEN")
    if not token:
        raise RuntimeError("REMNAWAVE_TOKEN or REMNAWAVE_API_TOKEN is required")

    _validate_remnawave_url(args.remnawave_url, args.allow_remnawave_host)
    remnawave_host = urlsplit(args.remnawave_url).hostname
    if (
        args.trusted_proxy_headers
        and (remnawave_host or "").casefold() not in INTERNAL_HTTP_REMNAWAVE_HOSTS
    ):
        raise RuntimeError(
            "Trusted proxy headers are allowed only for local/internal Remnawave API hosts"
        )
    manifest_path = _validate_manifest_path(args.rollback_manifest)

    if args.rollback:
        api = RemnawaveApi(
            args.remnawave_url,
            token,
            trusted_proxy_headers=args.trusted_proxy_headers,
        )
        try:
            return await _rollback(api, _read_manifest(manifest_path), manifest_path)
        finally:
            await api.close()

    artifact = _load_antifilter_artifact(
        args.artifact_manifest,
        rules_path=args.xray_rules_artifact,
        max_age_hours=args.max_artifact_age_hours,
    )
    spb_task2_listen_address = _validate_dedicated_listen_address(
        args.spb_task2_listen_address
    )
    spb_preserved_listen_address = _validate_dedicated_listen_address(
        args.spb_preserved_listen_address
    )

    api = RemnawaveApi(
        args.remnawave_url,
        token,
        trusted_proxy_headers=args.trusted_proxy_headers,
    )
    try:
        profiles = _collection(
            await api.request("GET", "/config-profiles"), "configProfiles"
        )
        spb_base_ref = _find_by_name(profiles, args.spb_base_profile)
        de_base_ref = _find_by_name(profiles, args.de_base_profile)
        if spb_base_ref is None or de_base_ref is None:
            raise RuntimeError("Required SPB or DE base profile was not found")
        spb_base_profile = await api.request(
            "GET", f"/config-profiles/{spb_base_ref['uuid']}"
        )
        de_base_profile = await api.request(
            "GET", f"/config-profiles/{de_base_ref['uuid']}"
        )
        existing_spb_ref = _find_by_name(profiles, args.spb_profile)
        existing_de_bridge_ref = _find_by_name(profiles, args.de_bridge_profile)
        existing_spb_profile = (
            await api.request("GET", f"/config-profiles/{existing_spb_ref['uuid']}")
            if existing_spb_ref
            else None
        )
        existing_de_bridge_profile = (
            await api.request(
                "GET", f"/config-profiles/{existing_de_bridge_ref['uuid']}"
            )
            if existing_de_bridge_ref
            else None
        )
        _validate_bridge_port_available(
            [
                spb_base_profile,
                de_base_profile,
                *(
                    profile
                    for profile in (existing_spb_profile, existing_de_bridge_profile)
                    if profile
                ),
            ]
        )
        if not args.skip_local_socket_preflight:
            _validate_local_bridge_socket_available(BRIDGE_PORT)

        nodes = _collection(await api.request("GET", "/nodes"), "nodes")
        spb_node = _find_node(nodes, args.spb_node_address)
        de_node = _find_node(nodes, args.de_node_address)
        spb_source_profile = await _node_source_profile(api, spb_node, spb_base_profile)
        de_source_profile = await _node_source_profile(api, de_node, de_base_profile)
        spb_preserved_active_tags = _active_inbound_tags(
            spb_source_profile,
            spb_node,
            exclude_tags=SPB_CUSTOMER_INBOUND_TAG_SET,
        )
        de_preserved_active_tags = _active_inbound_tags(
            de_source_profile,
            de_node,
            exclude_tags={BRIDGE_INBOUND_TAG},
        )
        _validate_bridge_port_available([spb_source_profile, de_source_profile])
        hosts = _collection(await api.request("GET", "/hosts"), "hosts")
        _validate_no_public_bridge_hosts(
            hosts,
            spb_base_profile,
            de_base_profile,
            spb_source_profile,
            de_source_profile,
            existing_spb_profile,
            existing_de_bridge_profile,
        )

        squads = _collection(
            await api.request("GET", "/internal-squads"), "internalSquads"
        )
        external_squads = _collection(
            await api.request("GET", "/external-squads"), "externalSquads"
        )
        customer_squad = _find_by_name(squads, args.customer_squad)
        external_squad = _find_by_name(external_squads, args.external_squad)
        bridge_squad = _find_by_name(squads, args.bridge_squad)
        bridge_user = await _get_user(api, args.bridge_username)
        _validate_existing_bridge_user_isolation(bridge_user, bridge_squad)
        _validate_bridge_squad_inbound_isolation(
            bridge_squad,
            _bridge_inbound_uuids_from_profiles(
                de_base_profile, de_source_profile, existing_de_bridge_profile
            ),
        )
        if customer_squad is None or external_squad is None:
            raise RuntimeError(
                "Task2 customer internal/external squads must be seeded first"
            )

        de_preserved_tag_map = _preserved_inbound_tag_map(
            de_source_profile["config"],
            "de",
            exclude_tags={BRIDGE_INBOUND_TAG},
        )
        spb_preserved_tag_map = _preserved_inbound_tag_map(
            spb_source_profile["config"],
            "spb",
            exclude_tags=SPB_CUSTOMER_INBOUND_TAG_SET | {BRIDGE_INBOUND_TAG},
        )
        de_preserved_target_tags = [
            de_preserved_tag_map.get(tag, tag) for tag in de_preserved_active_tags
        ]
        spb_preserved_target_tags = [
            spb_preserved_tag_map.get(tag, tag) for tag in spb_preserved_active_tags
        ]
        spb_shared_public_source_tags = _spb_shared_public_source_tags(
            spb_source_profile["config"], spb_preserved_active_tags
        )
        spb_customer_routing_tags = list(SPB_CUSTOMER_INBOUND_TAGS)
        spb_shared_xhttp_path = _spb_shared_xhttp_path(
            spb_source_profile["config"], spb_shared_public_source_tags
        )

        de_bridge_config = _build_de_bridge_config(
            de_source_profile["config"], de_preserved_tag_map
        )
        spb_source_config = _pin_preserved_spb_listeners(
            spb_source_profile["config"],
            spb_preserved_active_tags,
            spb_preserved_listen_address,
        )
        spb_config = _build_spb_customer_config(
            spb_source_config,
            bridge_user.get("ssPassword", "dry-run-placeholder")
            if bridge_user
            else "dry-run-placeholder",
            args.de_bridge_upstream_address,
            artifact.raw_rules,
            ipv6_policy_mode=artifact.ipv6_policy_mode,
            task2_listen_address=spb_task2_listen_address,
            preserved_tag_map=spb_preserved_tag_map,
            customer_inbound_tags=spb_customer_routing_tags,
            shared_xhttp_path=spb_shared_xhttp_path,
        )
        spb_next_active_tags = _ordered_active_tags(
            spb_preserved_target_tags, SPB_CUSTOMER_INBOUND_TAGS
        )
        _validate_no_active_listener_conflicts(
            spb_config,
            spb_next_active_tags,
            label="SPB shared Task2 profile",
        )
        plan = {
            "mode": "apply" if args.apply else "dry-run",
            "product": PRODUCT_CODE,
            "artifactManifestSha256": artifact.manifest_sha256,
            "artifactRulesSha256": artifact.rules_sha256,
            "artifactUnionPrefixCount": artifact.union_prefix_count,
            "artifactUnionIpv6PrefixCount": artifact.union_ipv6_prefix_count,
            "ipv6PolicyMode": artifact.ipv6_policy_mode,
            "bridgePort": BRIDGE_PORT,
            "bridgePortFree": True,
            "bridgeSocketPreflight": "skipped"
            if args.skip_local_socket_preflight
            else "passed-local",
            "bridgeProtocol": "shadowsocks",
            "bridgeAeadMethod": BRIDGE_AEAD_METHOD,
            "bridgeInboundTag": BRIDGE_INBOUND_TAG,
            "bridgeOutboundTag": BRIDGE_OUTBOUND_TAG,
            "bridgePublicHost": "none",
            "spbPublicHost": args.spb_public_host,
            "spbPublicHostCount": len(SPB_PUBLIC_HOST_SPECS),
            "bridgeUser": "reuse" if bridge_user else "create",
            "bridgeSquad": "update" if bridge_squad else "create",
            "spbProfile": "update" if existing_spb_profile else "create",
            "deBridgeProfile": "update" if existing_de_bridge_profile else "create",
            "spbProfileInboundTags": spb_customer_routing_tags,
            "spbTask2ListenAddress": spb_task2_listen_address,
            "spbPreservedListenAddress": spb_preserved_listen_address,
            "deBridgeInboundTag": BRIDGE_INBOUND_TAG,
            "spbPreservedActiveInboundTags": spb_preserved_active_tags,
            "dePreservedActiveInboundTags": de_preserved_active_tags,
            "spbPreservedTargetInboundTags": spb_preserved_target_tags,
            "dePreservedTargetInboundTags": de_preserved_target_tags,
            "spbRoutingRuleCount": len(spb_config["routing"]["rules"]),
            "deBridgeRoutingRuleCount": len(de_bridge_config["routing"]["rules"]),
            "restartOrder": ["de", "spb"],
        }
        if not args.apply:
            return plan

        manifest = {
            "version": 1,
            "phase": "planned",
            "product": PRODUCT_CODE,
            "artifactManifestSha256": artifact.manifest_sha256,
            "artifactRulesSha256": artifact.rules_sha256,
            "spbProfile": existing_spb_profile,
            "spbProfileName": args.spb_profile,
            "deBridgeProfile": existing_de_bridge_profile,
            "deBridgeProfileName": args.de_bridge_profile,
            "spbNode": {
                "uuid": spb_node["uuid"],
                "configProfile": _normalize_node_config_profile(
                    spb_node.get("configProfile")
                ),
            },
            "deNode": {
                "uuid": de_node["uuid"],
                "configProfile": _normalize_node_config_profile(
                    de_node.get("configProfile")
                ),
            },
            "customerSquad": {
                "uuid": customer_squad["uuid"],
                "inbounds": _inbound_uuids(customer_squad),
            },
            "externalSquad": {
                "uuid": external_squad["uuid"],
                "responseHeaders": external_squad.get("responseHeaders") or {},
            },
            "spbRemappedHosts": _host_snapshots_for_profile(
                hosts,
                spb_source_profile,
                exclude_tags=SPB_CUSTOMER_INBOUND_TAG_SET,
            ),
            "deRemappedHosts": _host_snapshots_for_profile(
                hosts,
                de_source_profile,
                exclude_tags={BRIDGE_INBOUND_TAG},
            ),
            "spbHosts": [
                _safe_host_snapshot(host)
                for host in hosts
                if host.get("remark") in _task2_host_remarks()
            ],
            "spbHostRemarks": sorted(_task2_host_remarks()),
            "bridgeSquad": (
                {"uuid": bridge_squad["uuid"], "inbounds": _inbound_uuids(bridge_squad)}
                if bridge_squad
                else None
            ),
            "bridgeSquadName": args.bridge_squad,
            "bridgeUser": (
                {
                    "uuid": bridge_user["uuid"],
                    "activeInternalSquads": _squad_uuids(bridge_user),
                    "externalSquadUuid": bridge_user.get("externalSquadUuid"),
                }
                if bridge_user
                else None
            ),
            "bridgeUsername": args.bridge_username,
        }
        _checkpoint(manifest_path, manifest, "planned")

        try:
            _checkpoint(manifest_path, manifest, "mutation_started")
            if existing_de_bridge_profile is None:
                de_bridge_profile = await api.request(
                    "POST",
                    "/config-profiles",
                    json={"name": args.de_bridge_profile, "config": de_bridge_config},
                )
            else:
                de_bridge_profile = await api.request(
                    "PATCH",
                    "/config-profiles",
                    json={
                        "uuid": existing_de_bridge_profile["uuid"],
                        "name": args.de_bridge_profile,
                        "config": de_bridge_config,
                    },
                )
            _checkpoint(manifest_path, manifest, "de_bridge_profile_ready")
            de_bridge_profile = await api.request(
                "GET", f"/config-profiles/{de_bridge_profile['uuid']}"
            )
            de_bridge_tags = _profile_inbound_uuid_by_tag(de_bridge_profile)
            bridge_inbound_uuid = de_bridge_tags.get(BRIDGE_INBOUND_TAG)
            if not bridge_inbound_uuid:
                raise RuntimeError(
                    "DE bridge profile did not expose the bridge inbound"
                )
            de_node_active_inbounds = _mapped_active_inbounds(
                de_bridge_tags, de_preserved_target_tags, [BRIDGE_INBOUND_TAG]
            )

            if bridge_squad is None:
                bridge_squad = await api.request(
                    "POST",
                    "/internal-squads",
                    json={
                        "name": args.bridge_squad,
                        "inbounds": _isolated_squad_inbounds(bridge_inbound_uuid),
                    },
                )
            else:
                bridge_squad = await api.request(
                    "PATCH",
                    "/internal-squads",
                    json={
                        "uuid": bridge_squad["uuid"],
                        "inbounds": _isolated_squad_inbounds(bridge_inbound_uuid),
                    },
                )
            _checkpoint(manifest_path, manifest, "bridge_squad_ready")

            if bridge_user is None:
                bridge_user = await api.request(
                    "POST",
                    "/users",
                    json={
                        "username": args.bridge_username,
                        "status": "ACTIVE",
                        "vlessUuid": str(uuid.uuid4()),
                        "trafficLimitBytes": 0,
                        "trafficLimitStrategy": "NO_RESET",
                        "expireAt": "2099-12-31T23:59:59.000Z",
                        "description": "CyberVPN internal SPB to DE exceptions bridge",
                        "tag": "BRIDGE",
                        "activeInternalSquads": _isolated_user_squads(
                            bridge_squad["uuid"]
                        ),
                        "externalSquadUuid": None,
                    },
                )
            else:
                patched_user = await api.request(
                    "PATCH",
                    "/users",
                    json={
                        "uuid": bridge_user["uuid"],
                        "activeInternalSquads": _isolated_user_squads(
                            bridge_squad["uuid"]
                        ),
                        "externalSquadUuid": None,
                    },
                )
                bridge_user = {**bridge_user, **patched_user}
            if not bridge_user.get("ssPassword"):
                raise RuntimeError(
                    "Task2 bridge service user has no Shadowsocks credential"
                )
            _checkpoint(manifest_path, manifest, "bridge_user_ready")

            spb_config = _build_spb_customer_config(
                spb_source_config,
                bridge_user["ssPassword"],
                args.de_bridge_upstream_address,
                artifact.raw_rules,
                ipv6_policy_mode=artifact.ipv6_policy_mode,
                task2_listen_address=spb_task2_listen_address,
                preserved_tag_map=spb_preserved_tag_map,
                customer_inbound_tags=spb_customer_routing_tags,
                shared_xhttp_path=spb_shared_xhttp_path,
            )
            if existing_spb_profile is None:
                spb_profile = await api.request(
                    "POST",
                    "/config-profiles",
                    json={"name": args.spb_profile, "config": spb_config},
                )
            else:
                spb_profile = await api.request(
                    "PATCH",
                    "/config-profiles",
                    json={
                        "uuid": existing_spb_profile["uuid"],
                        "name": args.spb_profile,
                        "config": spb_config,
                    },
                )
            _checkpoint(manifest_path, manifest, "spb_profile_ready")
            spb_profile = await api.request(
                "GET", f"/config-profiles/{spb_profile['uuid']}"
            )
            spb_tags = _profile_inbound_uuid_by_tag(spb_profile)
            spb_customer_inbounds = _ordered_inbound_uuids(
                spb_tags, spb_customer_routing_tags
            )
            spb_node_active_inbounds = _mapped_active_inbounds(
                spb_tags, spb_preserved_target_tags, SPB_CUSTOMER_INBOUND_TAGS
            )
            _validate_no_active_listener_conflicts(
                spb_profile.get("config", spb_config),
                spb_next_active_tags,
                label="SPB shared Task2 profile",
            )
            await _remap_profile_hosts(
                api,
                hosts,
                spb_source_profile,
                spb_profile,
                exclude_tags=SPB_CUSTOMER_INBOUND_TAG_SET,
                tag_map=spb_preserved_tag_map,
                remove_from_squad_uuid=str(customer_squad["uuid"]),
            )
            await _upsert_spb_public_hosts(
                api,
                hosts,
                args.spb_public_host,
                spb_profile["uuid"],
                spb_tags,
                xhttp_path=spb_shared_xhttp_path,
            )
            _checkpoint(manifest_path, manifest, "spb_public_hosts_ready")

            await api.request(
                "PATCH",
                "/internal-squads",
                json={
                    "uuid": customer_squad["uuid"],
                    "inbounds": spb_customer_inbounds,
                },
            )
            safe_headers = {
                **(external_squad.get("responseHeaders") or {}),
                "x-cybervpn-plan": PRODUCT_CODE,
                "x-cybervpn-routing": "spb-default-de-exceptions",
            }
            await api.request(
                "PATCH",
                "/external-squads",
                json={"uuid": external_squad["uuid"], "responseHeaders": safe_headers},
            )
            _checkpoint(manifest_path, manifest, "customer_squads_ready")

            await _remap_profile_hosts(
                api,
                hosts,
                de_source_profile,
                de_bridge_profile,
                exclude_tags={BRIDGE_INBOUND_TAG},
                tag_map=de_preserved_tag_map,
            )
            _checkpoint(manifest_path, manifest, "shared_hosts_remapped")

            hosts = _collection(await api.request("GET", "/hosts"), "hosts")
            _validate_no_public_bridge_hosts(hosts, de_bridge_profile, spb_profile)
            await api.request(
                "PATCH",
                "/nodes",
                json={
                    "uuid": de_node["uuid"],
                    "configProfile": {
                        "activeConfigProfileUuid": de_bridge_profile["uuid"],
                        "activeInbounds": de_node_active_inbounds,
                    },
                },
            )
            _checkpoint(manifest_path, manifest, "de_node_bridge_ready")
            await api.request(
                "POST",
                f"/nodes/{de_node['uuid']}/actions/restart",
                json={"forceRestart": True},
            )
            _checkpoint(manifest_path, manifest, "de_node_restarted")

            await api.request(
                "PATCH",
                "/nodes",
                json={
                    "uuid": spb_node["uuid"],
                    "configProfile": {
                        "activeConfigProfileUuid": spb_profile["uuid"],
                        "activeInbounds": spb_node_active_inbounds,
                    },
                },
            )
            _checkpoint(manifest_path, manifest, "spb_node_profile_ready")
            await api.request(
                "POST",
                f"/nodes/{spb_node['uuid']}/actions/restart",
                json={"forceRestart": True},
            )
            _checkpoint(manifest_path, manifest, "spb_node_restarted")
            _checkpoint(manifest_path, manifest, "applied")
            return {**plan, "status": "applied"}
        except Exception as apply_error:
            manifest["failurePhase"] = manifest.get("phase")
            manifest["failureClass"] = type(apply_error).__name__
            if isinstance(apply_error, RuntimeError):
                manifest["failureReason"] = str(apply_error)
            _checkpoint(manifest_path, manifest, "rollback_started")
            try:
                await _rollback(api, manifest, manifest_path)
            except Exception:
                _checkpoint(manifest_path, manifest, "rollback_failed")
                raise RuntimeError(
                    "Task2 apply and automatic rollback failed"
                ) from None
            raise RuntimeError(
                "Task2 apply failed and was rolled back"
            ) from apply_error
    finally:
        await api.close()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--apply", action="store_true", help="Apply changes; dry-run is the default"
    )
    mode.add_argument(
        "--rollback", action="store_true", help="Restore state from --rollback-manifest"
    )
    parser.add_argument(
        "--artifact-manifest",
        type=Path,
        default=Path("artifacts/antifilter/manifest.json"),
        help="Antifilter compiler manifest for premium_spb_de_exceptions",
    )
    parser.add_argument(
        "--xray-rules-artifact",
        type=Path,
        default=None,
        help="Optional explicit Xray rules artifact path under the manifest directory",
    )
    parser.add_argument("--max-artifact-age-hours", type=int, default=72)
    parser.add_argument(
        "--remnawave-url",
        default=os.environ.get("REMNAWAVE_URL", "http://remnawave:3000"),
    )
    parser.add_argument("--spb-base-profile", default=SPB_BASE_PROFILE_NAME)
    parser.add_argument("--de-base-profile", default=DE_BASE_PROFILE_NAME)
    parser.add_argument("--spb-profile", default=SPB_PROFILE_NAME)
    parser.add_argument("--de-bridge-profile", default=DE_BRIDGE_PROFILE_NAME)
    parser.add_argument("--spb-node-address", default=SPB_NODE_ADDRESS)
    parser.add_argument("--de-node-address", default=DE_NODE_ADDRESS)
    parser.add_argument("--spb-public-host", default=SPB_PUBLIC_HOST)
    parser.add_argument(
        "--spb-preserved-listen-address",
        default=os.environ.get("SPB_PRESERVED_LISTEN_ADDRESS"),
        help=(
            "Optional concrete bind IP for preserved SPB 443/8443 inbounds; "
            "required when the active shared profile currently uses wildcard listeners"
        ),
    )
    parser.add_argument(
        "--spb-task2-listen-address",
        default=os.environ.get("SPB_TASK2_LISTEN_ADDRESS"),
        help=(
            "Dedicated SPB bind IP for isolated Task2 RAW 4443/XHTTP 8444 inbounds"
        ),
    )
    parser.add_argument(
        "--de-bridge-upstream-address", default=DE_BRIDGE_UPSTREAM_ADDRESS
    )
    parser.add_argument(
        "--skip-local-socket-preflight",
        action="store_true",
        help="Skip the local TCP/UDP bind check when target-side preflight is performed separately",
    )
    parser.add_argument("--customer-squad", default=CUSTOMER_SQUAD_NAME)
    parser.add_argument("--external-squad", default=EXTERNAL_SQUAD_NAME)
    parser.add_argument("--bridge-squad", default=BRIDGE_SQUAD_NAME)
    parser.add_argument("--bridge-username", default=BRIDGE_USERNAME)
    parser.add_argument(
        "--allow-remnawave-host",
        action="append",
        default=["remnawave", "localhost", "127.0.0.1", "::1"],
        help="Allow an additional exact Remnawave API hostname",
    )
    parser.add_argument(
        "--trusted-proxy-headers",
        action="store_true",
        help="Send trusted proxy headers only to an allowlisted internal API host",
    )
    parser.add_argument(
        "--rollback-manifest",
        type=Path,
        default=Path("/var/lib/cybervpn/remnawave/spb-de-exceptions-rollback.json"),
    )
    return parser.parse_args()


def main() -> int:
    try:
        result = asyncio.run(_run(_parse_args()))
    except Exception as exc:  # noqa: BLE001 - CLI must emit a stable secret-safe failure.
        status = getattr(getattr(exc, "response", None), "status_code", None)
        payload: dict[str, Any] = {
            "status": "failed",
            "errorClass": type(exc).__name__,
            "httpStatus": status,
        }
        if isinstance(exc, RuntimeError):
            reason = str(exc)
            forbidden_reason_markers = (
                "token",
                "password",
                "secret",
                "credential",
                "subscription",
                "private key",
            )
            if (
                0 < len(reason) <= 500
                and "\n" not in reason
                and "\r" not in reason
                and not any(
                    marker in reason.casefold() for marker in forbidden_reason_markers
                )
            ):
                payload["reason"] = reason
        print(
            json.dumps(payload, sort_keys=True),
            file=sys.stderr,
        )
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
