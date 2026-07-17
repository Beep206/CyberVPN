#!/usr/bin/env python3
"""Apply the WELCOMERU SPB-direct/DE-BGP Remnawave routing layout.

The operator is intentionally narrow:

* customer ingress is the existing SPB VLESS Reality 443 and XHTTP 8443;
* accepted Antifilter BGP IPv4 prefixes use an internal DE bridge;
* every other destination exits directly from SPB;
* the internal bridge uses VLESS RAW + REALITY, not Shadowsocks or WireGuard;
* Moscow and Netherlands profiles, nodes, Hosts, and squads are not mutated.

Apply mode requires a mode-0600 rollback manifest outside the repository. Any
failed mutation triggers an automatic restore from that manifest. Output is a
secret-free structural summary; full profile snapshots remain only in the
rollback manifest.
"""

from __future__ import annotations

import argparse
import asyncio
import copy
import hashlib
import ipaddress
import json
import os
import secrets
import stat
import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx

PRODUCT_CODE = "premium_spb_de_exceptions"
SPB_NODE_ADDRESS = "193.233.91.99"
DE_NODE_ADDRESS = "138.124.115.206"
DE_BRIDGE_ADDRESS = "2a0b:4140:ba84::2"
# Moscow's public VPN address is 178.159.94.225, while Remnawave deliberately
# identifies the node through this control-plane address.
MOSCOW_NODE_ADDRESS = "172.30.3.1"
NL_NODE_ADDRESS = "138.16.140.44"

SPB_PROFILE_NAME = "S1 SPB DE Exceptions"
DE_PROFILE_NAME = "S1 DE SPB Bridge"
TARGET_SQUAD_NAME = "CYBERVPN_SPB_DE_NODES"
TARGET_EXTERNAL_SQUAD_NAME = "CYBERVPN_SPB_DE_EXCEPTIONS"
BRIDGE_SQUAD_NAME = "CYBERVPN_SPB_DE_BRIDGE"
BRIDGE_USERNAME = "CYBERVPN_SPB_DE_BRIDGE_USER"
TORRENT_PLUGIN_NAME = "CYBERVPN_PREMIUM_SMART_RU_ABUSE_PROTECTION"

BRIDGE_INBOUND_TAG = "DE_SPB_EXCEPTIONS_BRIDGE_9444"
BRIDGE_OUTBOUND_TAG = "DE_EXCEPTIONS_BRIDGE"
BRIDGE_PORT = 9444

TARGET_RAW_REMARK = "CyberVPN WELCOMERU SPB Reality"
TARGET_XHTTP_REMARK = "CyberVPN WELCOMERU SPB XHTTP"
TARGET_HOST_REMARKS = {TARGET_RAW_REMARK, TARGET_XHTTP_REMARK}

ROUTE_RULE_TAG = "welcomeru-bgp-to-de"
DIRECT_RULE_TAG = "welcomeru-spb-direct"
MANAGEMENT_RULE_TAG = "welcomeru-management-private-self-block"
DE_DIRECT_RULE_TAG = "welcomeru-de-bridge-direct"
SOURCE_MANAGEMENT_RULE_TAG = "task2-management-private-self-block"

MAX_ARTIFACT_BYTES = 64 * 1024 * 1024
MIN_PREFIXES = 1_000
MAX_PREFIXES = 50_000
MAX_ARTIFACT_AGE = timedelta(hours=72)
NODE_WAIT_ATTEMPTS = 18
NODE_WAIT_SECONDS = 5
SPB_IPV4_DNS_SERVERS = [
    "https+local://1.1.1.1/dns-query",
    "https+local://8.8.8.8/dns-query",
]


def _discover_repo_root() -> Path | None:
    starts = (Path(__file__).resolve().parent, Path.cwd().resolve())
    for start in starts:
        for candidate in (start, *start.parents):
            if (candidate / ".git").exists() and (candidate / "AGENTS.md").is_file():
                return candidate
    return None


REPO_ROOT = _discover_repo_root()

FORBIDDEN_IPV4 = tuple(
    ipaddress.ip_network(value)
    for value in (
        "0.0.0.0/8",
        "10.0.0.0/8",
        "100.64.0.0/10",
        "127.0.0.0/8",
        "169.254.0.0/16",
        "172.16.0.0/12",
        "192.168.0.0/16",
        "224.0.0.0/4",
        "240.0.0.0/4",
        "45.87.41.146/32",
        f"{SPB_NODE_ADDRESS}/32",
        f"{DE_NODE_ADDRESS}/32",
    )
)

HOST_MUTABLE_FIELDS = (
    "remark",
    "address",
    "port",
    "path",
    "sni",
    "host",
    "alpn",
    "fingerprint",
    "isDisabled",
    "securityLayer",
    "xhttpExtraParams",
    "muxParams",
    "sockoptParams",
    "finalMask",
    "serverDescription",
    "tags",
    "isHidden",
    "overrideSniFromAddress",
    "keepSniBlank",
    "vlessRouteId",
    "pinnedPeerCertSha256",
    "verifyPeerCertByName",
    "shuffleHost",
    "mihomoX25519",
    "mihomoIpVersion",
    "nodes",
    "xrayJsonTemplateUuid",
    "excludedInternalSquads",
    "excludeFromSubscriptionTypes",
)


class RemnawaveApi:
    def __init__(self, base_url: str, token: str) -> None:
        parsed = urlsplit(base_url)
        if parsed.scheme not in {"http", "https"}:
            raise RuntimeError("Remnawave URL must use http or https")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise RuntimeError(
                "Remnawave URL must not contain credentials, query, or fragment"
            )
        if parsed.path.rstrip("/") not in {"", "/api"}:
            raise RuntimeError("Remnawave URL path must be empty or /api")
        normalized = base_url.rstrip("/").removesuffix("/api")
        host = (urlsplit(normalized).hostname or "").casefold()
        if host not in {"remnawave", "localhost", "127.0.0.1", "::1"}:
            raise RuntimeError("operator requires the internal Remnawave API")
        self._client = httpx.AsyncClient(
            base_url=normalized,
            headers={
                "Authorization": f"Bearer {token}",
                "X-Forwarded-Proto": "https",
                "X-Forwarded-For": "127.0.0.1",
            },
            timeout=90.0,
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


def _validate_user_ref(value: str) -> str:
    candidate = value.strip()
    if not candidate or len(candidate) > 64:
        raise RuntimeError("target WELCOMERU user reference is invalid")
    try:
        parsed = uuid.UUID(candidate)
    except ValueError as error:
        raise RuntimeError("target WELCOMERU user reference must be a UUID") from error
    return str(parsed)


def _stable_control_hash(
    node: dict[str, Any],
    profile: dict[str, Any],
    *,
    hosts: list[dict[str, Any]],
    squads: list[dict[str, Any]],
) -> str:
    config_profile = node.get("configProfile") or {}
    inbound_tags = _profile_tag_by_uuid(profile)
    regional_hosts = [
        host for host in hosts if _host_inbound_uuid(host) in inbound_tags
    ]
    regional_squad_memberships = []
    for squad in squads:
        tags = sorted(
            inbound_tags[inbound_uuid]
            for inbound_uuid in _squad_inbounds(squad)
            if inbound_uuid in inbound_tags
        )
        if tags:
            regional_squad_memberships.append(
                {
                    "uuid": squad.get("uuid"),
                    "name": squad.get("name"),
                    "inboundTags": tags,
                }
            )
    payload = {
        "node": {
            "uuid": node.get("uuid"),
            "address": node.get("address"),
            "activePluginUuid": node.get("activePluginUuid"),
            "activeConfigProfileUuid": config_profile.get("activeConfigProfileUuid"),
            "activeInbounds": config_profile.get("activeInbounds") or [],
        },
        "profile": {
            "uuid": profile.get("uuid"),
            "name": profile.get("name"),
            "config": profile.get("config") or {},
        },
        "hosts": sorted(
            regional_hosts,
            key=lambda host: (
                str(host.get("uuid") or ""),
                str(host.get("remark") or ""),
            ),
        ),
        "squadMemberships": sorted(
            regional_squad_memberships,
            key=lambda squad: (
                str(squad.get("uuid") or ""),
                str(squad.get("name") or ""),
            ),
        ),
    }
    canonical = json.dumps(
        payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode()
    return hashlib.sha256(canonical).hexdigest()


def _external_squad_uuid(user: dict[str, Any]) -> str | None:
    external_squad = user.get("externalSquad")
    if isinstance(external_squad, dict) and external_squad.get("uuid"):
        return str(external_squad["uuid"])
    value = user.get("externalSquadUuid")
    return str(value) if value else None


def _collection(value: Any, key: str) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict) and isinstance(value.get(key), list):
        return [item for item in value[key] if isinstance(item, dict)]
    return []


def _item_uuid(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("uuid") or "")
    return str(value or "")


def _find_one(
    items: list[dict[str, Any]], predicate: Any, label: str
) -> dict[str, Any]:
    matches = [item for item in items if predicate(item)]
    if len(matches) != 1:
        raise RuntimeError(f"expected exactly one {label}")
    return matches[0]


def _profile_uuid_by_tag(profile: dict[str, Any]) -> dict[str, str]:
    return {
        str(item["tag"]): str(item["uuid"])
        for item in profile.get("inbounds") or []
        if isinstance(item, dict) and item.get("tag") and item.get("uuid")
    }


def _profile_tag_by_uuid(profile: dict[str, Any]) -> dict[str, str]:
    return {uuid: tag for tag, uuid in _profile_uuid_by_tag(profile).items()}


def _squad_inbounds(squad: dict[str, Any]) -> list[str]:
    return [uuid for item in squad.get("inbounds") or [] if (uuid := _item_uuid(item))]


def _user_squads(user: dict[str, Any]) -> set[str]:
    return {
        uuid
        for item in user.get("activeInternalSquads") or []
        if (uuid := _item_uuid(item))
    }


def _host_inbound_uuid(host: dict[str, Any]) -> str:
    inbound = host.get("inbound") or {}
    return str(inbound.get("configProfileInboundUuid") or "")


def _host_profile_uuid(host: dict[str, Any]) -> str:
    inbound = host.get("inbound") or {}
    return str(inbound.get("configProfileUuid") or "")


def _host_exclusions(host: dict[str, Any]) -> set[str]:
    return {
        uuid
        for item in host.get("excludedInternalSquads") or []
        if (uuid := _item_uuid(item))
    }


def _active_tags(node: dict[str, Any], profile: dict[str, Any]) -> list[str]:
    tag_by_uuid = _profile_tag_by_uuid(profile)
    active = [
        tag_by_uuid.get(_item_uuid(item))
        for item in (node.get("configProfile") or {}).get("activeInbounds") or []
    ]
    if any(tag is None for tag in active):
        raise RuntimeError("node has an active inbound outside its profile")
    return [str(tag) for tag in active]


def _rule_inbound_tags(rule: dict[str, Any]) -> set[str]:
    value = rule.get("inboundTag")
    if isinstance(value, list):
        return {str(item) for item in value}
    return {str(value)} if value else set()


def _config_inbound_by_tag(config: dict[str, Any], tag: str) -> dict[str, Any]:
    return _find_one(
        [item for item in config.get("inbounds") or [] if isinstance(item, dict)],
        lambda item: item.get("tag") == tag,
        f"inbound {tag}",
    )


def _standard_spb_inbounds(
    config: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    inbounds = [item for item in config.get("inbounds") or [] if isinstance(item, dict)]

    def is_reality(item: dict[str, Any]) -> bool:
        stream = item.get("streamSettings") or {}
        return item.get("protocol") == "vless" and stream.get("security") == "reality"

    raw = _find_one(
        inbounds,
        lambda item: (
            is_reality(item)
            and int(item.get("port") or 0) == 443
            and (item.get("streamSettings") or {}).get("network") in {"tcp", "raw"}
        ),
        "SPB VLESS Reality 443 inbound",
    )
    xhttp = _find_one(
        inbounds,
        lambda item: (
            is_reality(item)
            and int(item.get("port") or 0) == 8443
            and (item.get("streamSettings") or {}).get("network") == "xhttp"
        ),
        "SPB XHTTP Reality 8443 inbound",
    )
    if str(raw.get("listen") or "") not in {SPB_NODE_ADDRESS, "0.0.0.0", "::"}:
        raise RuntimeError("SPB RAW inbound is not publicly reachable on the SPB node")
    if str(xhttp.get("listen") or "") not in {SPB_NODE_ADDRESS, "0.0.0.0", "::"}:
        raise RuntimeError(
            "SPB XHTTP inbound is not publicly reachable on the SPB node"
        )
    return raw, xhttp


def _read_json_artifact(
    path: Path, *, max_bytes: int, label: str
) -> tuple[bytes, dict[str, Any]]:
    if not path.is_file() or path.is_symlink():
        raise RuntimeError(f"{label} is missing or unsafe")
    size = path.stat().st_size
    if size <= 0 or size > max_bytes:
        raise RuntimeError(f"{label} size is invalid")
    raw = path.read_bytes()
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise RuntimeError(f"{label} must be a JSON object")
    return raw, payload


def _artifact(
    path: Path,
    manifest_path: Path,
    active_pointer_path: Path,
    last_known_good_pointer_path: Path,
) -> tuple[list[str], dict[str, Any]]:
    active_resolved = active_pointer_path.resolve(strict=True)
    lkg_resolved = last_known_good_pointer_path.resolve(strict=True)
    if active_resolved == lkg_resolved or os.path.samefile(
        active_resolved, lkg_resolved
    ):
        raise RuntimeError(
            "BGP active and last-known-good pointers must be distinct files"
        )
    raw, payload = _read_json_artifact(
        path, max_bytes=MAX_ARTIFACT_BYTES, label="canonical BGP artifact"
    )
    if not isinstance(payload, dict) or payload.get("product") != PRODUCT_CODE:
        raise RuntimeError("canonical BGP artifact product mismatch")
    union = payload.get("union") or {}
    values = union.get("ipv4")
    if not isinstance(values, list) or not MIN_PREFIXES <= len(values) <= MAX_PREFIXES:
        raise RuntimeError(
            "canonical BGP IPv4 prefix count is outside the reviewed range"
        )
    if union.get("ipv6") not in ([], None):
        raise RuntimeError("this WELCOMERU rollout accepts only BGP IPv4 prefixes")

    networks: list[ipaddress.IPv4Network] = []
    for value in values:
        if not isinstance(value, str):
            raise RuntimeError("canonical BGP artifact contains a non-string prefix")
        network = ipaddress.ip_network(value, strict=True)
        if not isinstance(network, ipaddress.IPv4Network):
            raise RuntimeError("canonical BGP artifact contains a non-IPv4 prefix")
        if (
            not network.is_global
            or not network.network_address.is_global
            or not network.broadcast_address.is_global
        ):
            raise RuntimeError("canonical BGP artifact contains a non-public prefix")
        if any(network.overlaps(forbidden) for forbidden in FORBIDDEN_IPV4):
            raise RuntimeError("canonical BGP artifact overlaps a forbidden network")
        networks.append(network)
    collapsed = list(ipaddress.collapse_addresses(networks))
    if len(collapsed) != len(networks) or len(set(networks)) != len(networks):
        raise RuntimeError("canonical BGP artifact is not deduplicated and collapsed")

    generated_raw = payload.get("generatedAt")
    if not isinstance(generated_raw, str):
        raise RuntimeError("canonical BGP artifact has no generation timestamp")
    generated = datetime.fromisoformat(
        generated_raw.removesuffix("Z")
        + ("+00:00" if generated_raw.endswith("Z") else "")
    )
    now = datetime.now(UTC)
    generated_utc = generated.astimezone(UTC) if generated.tzinfo else None
    if generated_utc is None or now - generated_utc > MAX_ARTIFACT_AGE:
        raise RuntimeError("canonical BGP artifact is stale")
    if generated_utc - now > timedelta(minutes=5):
        raise RuntimeError("canonical BGP artifact timestamp is in the future")

    canonical_sha256 = hashlib.sha256(raw).hexdigest()
    manifest_raw, manifest = _read_json_artifact(
        manifest_path, max_bytes=4 * 1024 * 1024, label="BGP artifact manifest"
    )
    active_raw, active_pointer = _read_json_artifact(
        active_pointer_path, max_bytes=16 * 1024, label="BGP active pointer"
    )
    lkg_raw, lkg_pointer = _read_json_artifact(
        last_known_good_pointer_path,
        max_bytes=16 * 1024,
        label="BGP last-known-good pointer",
    )
    safety = manifest.get("safety") or {}
    artifacts = manifest.get("artifacts") or {}
    manifest_union = manifest.get("union") or {}
    manifest_families = manifest_union.get("families") or {}
    manifest_source = manifest.get("source") or {}
    manifest_sha256 = hashlib.sha256(manifest_raw).hexdigest()
    if manifest.get("product") != PRODUCT_CODE:
        raise RuntimeError("BGP artifact manifest product mismatch")
    if safety != {"status": "accepted", "reasons": []}:
        raise RuntimeError("BGP artifact manifest is not safety-accepted")
    if artifacts.get("canonical.json") != canonical_sha256:
        raise RuntimeError("canonical BGP artifact checksum mismatch")
    if (
        manifest_families.get("ipv4") != len(values)
        or manifest_families.get("ipv6") != 0
    ):
        raise RuntimeError("BGP artifact manifest family counts mismatch")
    if manifest_source.get("sourceVersion") != payload.get("sourceVersion"):
        raise RuntimeError("BGP artifact source version mismatch")
    if (
        active_pointer.get("version") != manifest.get("version")
        or active_pointer.get("manifestSha256") != manifest_sha256
    ):
        raise RuntimeError("BGP artifact is not the published active version")
    if lkg_pointer != active_pointer:
        raise RuntimeError(
            "BGP active artifact has not been promoted to last-known-good"
        )

    active_raw_after, _ = _read_json_artifact(
        active_pointer_path, max_bytes=16 * 1024, label="BGP active pointer"
    )
    lkg_raw_after, _ = _read_json_artifact(
        last_known_good_pointer_path,
        max_bytes=16 * 1024,
        label="BGP last-known-good pointer",
    )
    if active_raw_after != active_raw or lkg_raw_after != lkg_raw:
        raise RuntimeError("BGP published pointers changed during validation")

    evidence = {
        "canonicalSha256": canonical_sha256,
        "manifestSha256": manifest_sha256,
        "version": manifest.get("version"),
        "generatedAt": generated_utc.isoformat(),
        "prefixCount": len(values),
        "sourceVersion": payload.get("sourceVersion"),
        "safetyStatus": "accepted",
    }
    return [str(network) for network in networks], evidence


def _validate_manifest_path(path: Path) -> Path:
    resolved = path.expanduser().resolve(strict=False)
    if any(part.casefold() in {".git", ".codex"} for part in resolved.parts):
        raise RuntimeError("rollback manifest must remain outside repository metadata")
    if REPO_ROOT is not None and (
        resolved == REPO_ROOT or REPO_ROOT in resolved.parents
    ):
        raise RuntimeError("rollback manifest must remain outside the repository")
    if not resolved.parent.is_dir() or resolved.parent.is_symlink():
        raise RuntimeError("rollback manifest parent is missing or unsafe")
    parent_info = resolved.parent.lstat()
    if not stat.S_ISDIR(parent_info.st_mode):
        raise RuntimeError("rollback manifest parent is not a directory")
    if os.name != "nt":
        if parent_info.st_uid != os.geteuid():
            raise RuntimeError("rollback manifest parent must be operator-owned")
        if stat.S_IMODE(parent_info.st_mode) & 0o077:
            raise RuntimeError("rollback manifest parent must be private mode 0700")
    if resolved.exists():
        info = resolved.lstat()
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
            raise RuntimeError("rollback manifest path is unsafe")
        if info.st_nlink != 1:
            raise RuntimeError("rollback manifest must not have hard links")
        if os.name != "nt":
            if info.st_uid != os.geteuid():
                raise RuntimeError("rollback manifest must be operator-owned")
            if stat.S_IMODE(info.st_mode) & 0o077:
                raise RuntimeError("rollback manifest must be private mode 0600")
    return resolved


def _fsync_directory(path: Path) -> None:
    if os.name == "nt":
        return
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_manifest(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.{secrets.token_hex(8)}.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(
                payload,
                handle,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            )
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600)
        _fsync_directory(path.parent)
    finally:
        if temporary.exists():
            temporary.unlink()


def _read_manifest(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise RuntimeError("rollback manifest is missing or unsafe")
    if path.stat().st_size > 64 * 1024 * 1024:
        raise RuntimeError("rollback manifest is too large")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("version") != 1:
        raise RuntimeError("rollback manifest version is invalid")
    if payload.get("product") != PRODUCT_CODE:
        raise RuntimeError("rollback manifest product mismatch")
    return payload


def _checkpoint(path: Path, manifest: dict[str, Any], phase: str) -> None:
    manifest["phase"] = phase
    _write_manifest(path, manifest)


def _snapshot_inbound_ref(
    uuid: str,
    spb_tags: dict[str, str],
    de_tags: dict[str, str],
) -> dict[str, str]:
    if uuid in spb_tags:
        return {"profile": "spb", "tag": spb_tags[uuid]}
    if uuid in de_tags:
        return {"profile": "de", "tag": de_tags[uuid]}
    return {"uuid": uuid}


def _resolve_inbound_ref(
    ref: dict[str, str],
    spb_uuids: dict[str, str],
    de_uuids: dict[str, str],
) -> str:
    profile = ref.get("profile")
    if profile == "spb":
        return spb_uuids[ref["tag"]]
    if profile == "de":
        return de_uuids[ref["tag"]]
    return ref["uuid"]


def _host_update_payload(
    host: dict[str, Any],
    *,
    profile_uuid: str | None = None,
    inbound_uuid: str | None = None,
) -> dict[str, Any]:
    payload = {"uuid": host["uuid"]}
    for field in HOST_MUTABLE_FIELDS:
        if field in host:
            payload[field] = copy.deepcopy(host[field])
    if "excludedInternalSquads" in payload:
        payload["excludedInternalSquads"] = sorted(_host_exclusions(host))
    if profile_uuid and inbound_uuid:
        payload["inbound"] = {
            "configProfileUuid": profile_uuid,
            "configProfileInboundUuid": inbound_uuid,
        }
    return payload


async def _profile_by_name(
    api: RemnawaveApi, refs: list[dict[str, Any]], name: str
) -> dict[str, Any]:
    ref = _find_one(refs, lambda item: item.get("name") == name, f"profile {name}")
    value = await api.request("GET", f"/config-profiles/{ref['uuid']}")
    if not isinstance(value, dict):
        raise RuntimeError("Remnawave returned an invalid profile")
    return value


async def _user_by_username(api: RemnawaveApi, username: str) -> dict[str, Any]:
    value = await api.request("GET", f"/users/by-username/{username}")
    if isinstance(value, list):
        value = value[0] if value else None
    if not isinstance(value, dict):
        raise RuntimeError("bridge service user is missing")
    return value


async def _wait_for_node(api: RemnawaveApi, node_uuid: str) -> None:
    for attempt in range(NODE_WAIT_ATTEMPTS):
        nodes = _collection(await api.request("GET", "/nodes"), "nodes")
        node = _find_one(nodes, lambda item: str(item.get("uuid")) == node_uuid, "node")
        if node.get("isConnected") is True and node.get("isDisabled") is False:
            return
        if attempt + 1 < NODE_WAIT_ATTEMPTS:
            await asyncio.sleep(NODE_WAIT_SECONDS)
    raise RuntimeError("Remnawave node did not reconnect")


def _target_host_payload(
    *,
    remark: str,
    inbound_uuid: str,
    profile_uuid: str,
    port: int,
    path: str | None,
    excluded_squads: list[str],
    tag: str,
) -> dict[str, Any]:
    return {
        "remark": remark,
        "address": SPB_NODE_ADDRESS,
        "port": port,
        "path": path,
        "inbound": {
            "configProfileUuid": profile_uuid,
            "configProfileInboundUuid": inbound_uuid,
        },
        "isDisabled": False,
        "serverDescription": "Premium SPB DE routing",
        "tags": [tag],
        "isHidden": False,
        "excludedInternalSquads": excluded_squads,
    }


async def _restore(
    api: RemnawaveApi, manifest: dict[str, Any], manifest_path: Path
) -> dict[str, Any]:
    _checkpoint(manifest_path, manifest, "rollback_started")

    spb_snapshot = manifest["profiles"]["spb"]
    de_snapshot = manifest["profiles"]["de"]
    await api.request(
        "PATCH",
        "/config-profiles",
        json={
            "uuid": de_snapshot["uuid"],
            "name": de_snapshot["name"],
            "config": de_snapshot["config"],
        },
    )
    await api.request(
        "PATCH",
        "/config-profiles",
        json={
            "uuid": spb_snapshot["uuid"],
            "name": spb_snapshot["name"],
            "config": spb_snapshot["config"],
        },
    )
    restored_de = await api.request("GET", f"/config-profiles/{de_snapshot['uuid']}")
    restored_spb = await api.request("GET", f"/config-profiles/{spb_snapshot['uuid']}")
    de_uuids = _profile_uuid_by_tag(restored_de)
    spb_uuids = _profile_uuid_by_tag(restored_spb)

    for host_uuid in manifest.get("createdHostUuids") or []:
        try:
            await api.request("DELETE", f"/hosts/{host_uuid}")
        except httpx.HTTPStatusError as error:
            if error.response.status_code != 404:
                raise

    host_creation_tag = manifest.get("hostCreationTag")
    if isinstance(host_creation_tag, str) and host_creation_tag:
        current_hosts = _collection(await api.request("GET", "/hosts"), "hosts")
        for host in current_hosts:
            host_uuid = str(host.get("uuid") or "")
            host_tags = host.get("tags") or []
            if (
                host_uuid
                and isinstance(host_tags, list)
                and host_creation_tag in host_tags
                and host.get("remark") in TARGET_HOST_REMARKS
                and _host_profile_uuid(host) == str(restored_spb["uuid"])
            ):
                try:
                    await api.request("DELETE", f"/hosts/{host_uuid}")
                except httpx.HTTPStatusError as error:
                    if error.response.status_code != 404:
                        raise

    for snapshot in manifest.get("hosts") or []:
        ref = snapshot["inboundRef"]
        profile_kind = ref.get("profile")
        profile_uuid = (
            restored_spb["uuid"] if profile_kind == "spb" else restored_de["uuid"]
        )
        inbound_uuid = _resolve_inbound_ref(ref, spb_uuids, de_uuids)
        await api.request(
            "PATCH",
            "/hosts",
            json=_host_update_payload(
                snapshot["host"],
                profile_uuid=profile_uuid,
                inbound_uuid=inbound_uuid,
            ),
        )

    for snapshot in manifest.get("squads") or []:
        inbounds = [
            _resolve_inbound_ref(ref, spb_uuids, de_uuids)
            for ref in snapshot["inboundRefs"]
        ]
        await api.request(
            "PATCH",
            "/internal-squads",
            json={
                "uuid": snapshot["uuid"],
                "name": snapshot["name"],
                "inbounds": inbounds,
            },
        )

    for kind, profile, uuids in (
        ("de", restored_de, de_uuids),
        ("spb", restored_spb, spb_uuids),
    ):
        node = manifest["nodes"][kind]
        await api.request(
            "PATCH",
            "/nodes",
            json={
                "uuid": node["uuid"],
                "configProfile": {
                    "activeConfigProfileUuid": profile["uuid"],
                    "activeInbounds": [uuids[tag] for tag in node["activeInboundTags"]],
                },
            },
        )
        await api.request(
            "POST",
            f"/nodes/{node['uuid']}/actions/restart",
            json={"forceRestart": True},
        )

    await _wait_for_node(api, manifest["nodes"]["de"]["uuid"])
    await _wait_for_node(api, manifest["nodes"]["spb"]["uuid"])
    _checkpoint(manifest_path, manifest, "rolled_back")
    return {"status": "rolled_back", "rollbackManifest": str(manifest_path)}


async def _run(args: argparse.Namespace) -> dict[str, Any]:
    token = ""
    if args.token_file:
        token_path = Path(args.token_file)
        if not token_path.is_file() or token_path.is_symlink():
            raise RuntimeError("Remnawave token file is missing or unsafe")
        token = token_path.read_text(encoding="utf-8").strip()
    token = token or os.environ.get("REMNAWAVE_TOKEN", "").strip()
    if not token:
        raise RuntimeError("REMNAWAVE_TOKEN or --token-file is required")
    target_user_ref = args.target_user_ref
    if args.target_user_ref_file:
        target_ref_path = Path(args.target_user_ref_file)
        if not target_ref_path.is_file() or target_ref_path.is_symlink():
            raise RuntimeError("target user reference file is missing or unsafe")
        target_user_ref = target_ref_path.read_text(encoding="utf-8").strip()
    if not args.rollback and not target_user_ref:
        raise RuntimeError("target WELCOMERU user reference is required")
    if not args.rollback:
        target_user_ref = _validate_user_ref(str(target_user_ref))

    manifest_path = _validate_manifest_path(args.rollback_manifest)
    if args.apply and manifest_path.exists():
        raise RuntimeError("apply requires a new rollback manifest path")
    api = RemnawaveApi(args.remnawave_url, token)
    try:
        if args.rollback:
            return await _restore(api, _read_manifest(manifest_path), manifest_path)

        prefixes, artifact_evidence = _artifact(
            args.canonical_artifact,
            args.artifact_manifest,
            args.active_pointer,
            args.last_known_good_pointer,
        )
        profile_refs = _collection(
            await api.request("GET", "/config-profiles"), "configProfiles"
        )
        spb_profile = await _profile_by_name(api, profile_refs, SPB_PROFILE_NAME)
        de_profile = await _profile_by_name(api, profile_refs, DE_PROFILE_NAME)
        nodes = _collection(await api.request("GET", "/nodes"), "nodes")
        hosts = _collection(await api.request("GET", "/hosts"), "hosts")
        squads = _collection(
            await api.request("GET", "/internal-squads"), "internalSquads"
        )
        external_squads = _collection(
            await api.request("GET", "/external-squads"), "externalSquads"
        )
        plugins = _collection(await api.request("GET", "/node-plugins"), "nodePlugins")

        spb_node = _find_one(
            nodes, lambda item: item.get("address") == SPB_NODE_ADDRESS, "SPB node"
        )
        de_node = _find_one(
            nodes, lambda item: item.get("address") == DE_NODE_ADDRESS, "DE node"
        )
        moscow_node = _find_one(
            nodes,
            lambda item: item.get("address") == MOSCOW_NODE_ADDRESS,
            "Moscow node",
        )
        nl_node = _find_one(
            nodes,
            lambda item: item.get("address") == NL_NODE_ADDRESS,
            "Netherlands node",
        )
        if any(
            node.get("isConnected") is not True or node.get("isDisabled") is not False
            for node in (spb_node, de_node)
        ):
            raise RuntimeError("SPB or DE Remnawave node is unavailable")
        if str(
            (spb_node.get("configProfile") or {}).get("activeConfigProfileUuid")
        ) != str(spb_profile["uuid"]):
            raise RuntimeError("SPB node is not on the expected profile")
        if str(
            (de_node.get("configProfile") or {}).get("activeConfigProfileUuid")
        ) != str(de_profile["uuid"]):
            raise RuntimeError("DE node is not on the expected profile")

        target_squad = _find_one(
            squads, lambda item: item.get("name") == TARGET_SQUAD_NAME, "target squad"
        )
        target_external_squad = _find_one(
            external_squads,
            lambda item: item.get("name") == TARGET_EXTERNAL_SQUAD_NAME,
            "target external squad",
        )
        bridge_squad = _find_one(
            squads, lambda item: item.get("name") == BRIDGE_SQUAD_NAME, "bridge squad"
        )
        target_user = await api.request("GET", f"/users/{target_user_ref}")
        bridge_user = await _user_by_username(api, BRIDGE_USERNAME)
        if not isinstance(target_user, dict) or target_user.get("status") != "ACTIVE":
            raise RuntimeError("target WELCOMERU user is missing or inactive")
        if _user_squads(target_user) != {str(target_squad["uuid"])}:
            raise RuntimeError("target WELCOMERU user is not isolated to its squad")
        if _external_squad_uuid(target_user) != str(target_external_squad["uuid"]):
            raise RuntimeError(
                "target WELCOMERU user is not assigned to the expected external squad"
            )
        if _user_squads(bridge_user) != {str(bridge_squad["uuid"])}:
            raise RuntimeError("bridge service user is not isolated to its squad")
        if bridge_user.get("externalSquadUuid") or bridge_user.get("externalSquad"):
            raise RuntimeError("bridge service user unexpectedly has an external squad")
        target_user_id = target_user.get("tId") or target_user.get("id")
        if (
            isinstance(target_user_id, bool)
            or not isinstance(target_user_id, int)
            or target_user_id <= 0
        ):
            raise RuntimeError("target Remnawave user ID is invalid")
        if not bridge_user.get("vlessUuid"):
            raise RuntimeError("bridge service user has no VLESS credential")

        spb_config = copy.deepcopy(spb_profile.get("config") or {})
        de_config = copy.deepcopy(de_profile.get("config") or {})
        raw_inbound, xhttp_inbound = _standard_spb_inbounds(spb_config)
        raw_tag = str(raw_inbound["tag"])
        xhttp_tag = str(xhttp_inbound["tag"])
        spb_active_tags = _active_tags(spb_node, spb_profile)
        de_active_tags = _active_tags(de_node, de_profile)
        if not {raw_tag, xhttp_tag}.issubset(spb_active_tags):
            raise RuntimeError("standard SPB customer inbounds are not active")
        if BRIDGE_INBOUND_TAG not in de_active_tags:
            raise RuntimeError("DE bridge inbound is not active")

        bridge_inbound = _config_inbound_by_tag(de_config, BRIDGE_INBOUND_TAG)
        bridge_outbound = _find_one(
            [
                item
                for item in spb_config.get("outbounds") or []
                if isinstance(item, dict)
            ],
            lambda item: item.get("tag") == BRIDGE_OUTBOUND_TAG,
            "SPB DE bridge outbound",
        )
        if any(
            _host_profile_uuid(host) == str(de_profile["uuid"])
            and _host_inbound_uuid(host)
            == _profile_uuid_by_tag(de_profile)[BRIDGE_INBOUND_TAG]
            for host in hosts
        ):
            raise RuntimeError("internal DE bridge is exposed through a public Host")

        plugin_uuid = str(spb_node.get("activePluginUuid") or "")
        if not plugin_uuid or plugin_uuid != str(de_node.get("activePluginUuid") or ""):
            raise RuntimeError("SPB and DE must share the reviewed node plugin")
        for label, node in (("Moscow", moscow_node), ("Netherlands", nl_node)):
            if str(node.get("activePluginUuid") or "") != plugin_uuid:
                raise RuntimeError(
                    f"{label} is not assigned to the reviewed node plugin"
                )
        plugin_ref = _find_one(
            plugins,
            lambda item: str(item.get("uuid") or "") == plugin_uuid,
            "active node plugin",
        )
        plugin = await api.request("GET", f"/node-plugins/{plugin_ref['uuid']}")
        if not isinstance(plugin, dict):
            raise RuntimeError("Remnawave returned an invalid node plugin")
        if plugin.get("name") != TORRENT_PLUGIN_NAME:
            raise RuntimeError("active node plugin identity is not the reviewed plugin")
        plugin_config = copy.deepcopy(plugin.get("pluginConfig") or {})
        torrent = plugin_config.get("torrentBlocker")
        expected_torrent = {
            "enabled": True,
            "ignoreLists": {"ip": [], "userId": []},
            "blockDuration": 86400,
        }
        if torrent != expected_torrent:
            raise RuntimeError(
                "reviewed torrent blocker does not match the fail-closed contract"
            )

        moscow_profile_uuid = str(
            (moscow_node.get("configProfile") or {}).get("activeConfigProfileUuid")
            or ""
        )
        nl_profile_uuid = str(
            (nl_node.get("configProfile") or {}).get("activeConfigProfileUuid") or ""
        )
        if not moscow_profile_uuid or not nl_profile_uuid:
            raise RuntimeError("Moscow or Netherlands active profile is missing")
        moscow_profile = await api.request(
            "GET", f"/config-profiles/{moscow_profile_uuid}"
        )
        nl_profile = await api.request("GET", f"/config-profiles/{nl_profile_uuid}")
        if not isinstance(moscow_profile, dict) or not isinstance(nl_profile, dict):
            raise RuntimeError("Moscow or Netherlands profile response is invalid")
        untouched_hashes = {
            "moscow": _stable_control_hash(
                moscow_node, moscow_profile, hosts=hosts, squads=squads
            ),
            "netherlands": _stable_control_hash(
                nl_node, nl_profile, hosts=hosts, squads=squads
            ),
        }

        spb_tag_by_uuid = _profile_tag_by_uuid(spb_profile)
        de_tag_by_uuid = _profile_tag_by_uuid(de_profile)
        spb_profile_uuid = str(spb_profile["uuid"])
        de_profile_uuid = str(de_profile["uuid"])
        affected_squads = [
            squad
            for squad in squads
            if str(squad.get("uuid") or "")
            in {str(target_squad["uuid"]), str(bridge_squad["uuid"])}
            or any(
                uuid in spb_tag_by_uuid or uuid in de_tag_by_uuid
                for uuid in _squad_inbounds(squad)
            )
        ]
        affected_hosts = [
            host
            for host in hosts
            if _host_profile_uuid(host) in {spb_profile_uuid, de_profile_uuid}
        ]

        plan = {
            "mode": "apply" if args.apply else "plan",
            "product": PRODUCT_CODE,
            "artifact": artifact_evidence,
            "untouchedControlHashes": untouched_hashes,
            "customerIngress": [
                {"transport": "vless-reality-raw", "port": 443},
                {"transport": "vless-reality-xhttp", "port": 8443},
            ],
            "bridgeCurrentProtocol": bridge_inbound.get("protocol"),
            "bridgeCurrentOutboundProtocol": bridge_outbound.get("protocol"),
            "bridgeTargetProtocol": "vless-raw-reality-without-vision",
            "matchedEgress": "de",
            "fallbackEgress": "spb-direct",
            "targetRuleUserScoped": True,
            "torrentPluginMode": "preserved-global-protocol-block",
            "targetTorrentPolicy": "blocked-by-remnawave-plugin",
            "torrentPluginMutation": False,
            "torrentPluginAttachedNodeCount": 4,
            "affectedSquadCount": len(affected_squads),
            "affectedHostCount": len(affected_hosts),
            "moscowNodeProfileMutations": 0,
            "netherlandsNodeProfileMutations": 0,
            "regionalHostAndSquadMembershipsVerifiedUnchanged": True,
        }
        if not args.apply:
            return plan

        host_creation_tag = f"WELCOMERU_APPLY_{secrets.token_hex(12)}"
        manifest = {
            "version": 1,
            "product": PRODUCT_CODE,
            "createdAt": datetime.now(UTC).isoformat(),
            "phase": "planned",
            "artifact": artifact_evidence,
            "untouchedControlHashes": untouched_hashes,
            "hostCreationTag": host_creation_tag,
            "profiles": {
                "spb": copy.deepcopy(spb_profile),
                "de": copy.deepcopy(de_profile),
            },
            "nodes": {
                "spb": {
                    "uuid": spb_node["uuid"],
                    "activeInboundTags": spb_active_tags,
                },
                "de": {
                    "uuid": de_node["uuid"],
                    "activeInboundTags": de_active_tags,
                },
            },
            "squads": [
                {
                    "uuid": squad["uuid"],
                    "name": squad["name"],
                    "inboundRefs": [
                        _snapshot_inbound_ref(uuid, spb_tag_by_uuid, de_tag_by_uuid)
                        for uuid in _squad_inbounds(squad)
                    ],
                }
                for squad in affected_squads
            ],
            "hosts": [
                {
                    "host": copy.deepcopy(host),
                    "inboundRef": _snapshot_inbound_ref(
                        _host_inbound_uuid(host), spb_tag_by_uuid, de_tag_by_uuid
                    ),
                }
                for host in affected_hosts
            ],
            "createdHostUuids": [],
        }
        _checkpoint(manifest_path, manifest, "planned")

        mutation_started = False
        try:
            reality_sources = [
                item
                for item in de_config.get("inbounds") or []
                if isinstance(item, dict)
                and item.get("tag") != BRIDGE_INBOUND_TAG
                and item.get("protocol") == "vless"
                and (item.get("streamSettings") or {}).get("security") == "reality"
                and (item.get("streamSettings") or {}).get("network") in {"tcp", "raw"}
                and item.get("tag") in de_active_tags
            ]
            reality_sources = [
                item
                for item in reality_sources
                if bool(
                    (
                        (item.get("streamSettings") or {}).get("realitySettings") or {}
                    ).get("target")
                )
            ]
            if not reality_sources:
                raise RuntimeError("active DE Reality camouflage source is missing")
            reality_source = sorted(
                reality_sources,
                key=lambda item: (
                    int(item.get("port") or 0) != 443,
                    str(item.get("tag") or ""),
                ),
            )[0]
            source_reality = copy.deepcopy(
                (reality_source.get("streamSettings") or {}).get("realitySettings")
                or {}
            )
            server_names = source_reality.get("serverNames")
            target = source_reality.get("target")
            if (
                not isinstance(server_names, list)
                or not server_names
                or not isinstance(target, str)
            ):
                raise RuntimeError("DE Reality camouflage settings are incomplete")

            generated = await api.request("GET", "/system/tools/x25519/generate")
            keypairs = (
                generated.get("keypairs") if isinstance(generated, dict) else None
            )
            if not isinstance(keypairs, list) or not keypairs:
                raise RuntimeError("Remnawave did not generate a Reality keypair")
            keypair = keypairs[0]
            private_key = (
                keypair.get("privateKey") if isinstance(keypair, dict) else None
            )
            public_key = keypair.get("publicKey") if isinstance(keypair, dict) else None
            if not isinstance(private_key, str) or not isinstance(public_key, str):
                raise RuntimeError("generated Reality keypair is invalid")
            short_id = secrets.token_hex(8)

            de_next = copy.deepcopy(de_config)
            de_inbounds = []
            for inbound in de_next.get("inbounds") or []:
                if (
                    not isinstance(inbound, dict)
                    or inbound.get("tag") != BRIDGE_INBOUND_TAG
                ):
                    de_inbounds.append(inbound)
                    continue
                de_inbounds.append(
                    {
                        "tag": BRIDGE_INBOUND_TAG,
                        "port": BRIDGE_PORT,
                        "listen": DE_BRIDGE_ADDRESS,
                        "protocol": "vless",
                        "settings": {
                            "clients": [],
                            "decryption": "none",
                            "flow": "",
                        },
                        "sniffing": {
                            "enabled": True,
                            "destOverride": ["http", "tls", "quic"],
                        },
                        "streamSettings": {
                            "network": "raw",
                            "security": "reality",
                            "realitySettings": {
                                "target": target,
                                "serverNames": server_names,
                                "privateKey": private_key,
                                "shortIds": [short_id],
                            },
                        },
                    }
                )
            de_next["inbounds"] = de_inbounds
            de_routing = copy.deepcopy(de_next.get("routing") or {})
            de_rules = [
                rule
                for rule in de_routing.get("rules") or []
                if isinstance(rule, dict)
                and BRIDGE_INBOUND_TAG not in _rule_inbound_tags(rule)
                and rule.get("ruleTag") != DE_DIRECT_RULE_TAG
            ]
            de_routing["rules"] = [
                {
                    "type": "field",
                    "ruleTag": DE_DIRECT_RULE_TAG,
                    "inboundTag": [BRIDGE_INBOUND_TAG],
                    "network": "tcp,udp",
                    "outboundTag": "DIRECT",
                },
                *de_rules,
            ]
            de_next["routing"] = de_routing
            mutation_started = True
            await api.request(
                "PATCH",
                "/config-profiles",
                json={
                    "uuid": de_profile["uuid"],
                    "name": de_profile["name"],
                    "config": de_next,
                },
            )
            de_updated = await api.request(
                "GET", f"/config-profiles/{de_profile['uuid']}"
            )
            de_updated_uuids = _profile_uuid_by_tag(de_updated)
            if BRIDGE_INBOUND_TAG not in de_updated_uuids:
                raise RuntimeError("updated DE profile has no bridge inbound")

            for snapshot in manifest["squads"]:
                if snapshot["uuid"] == bridge_squad["uuid"]:
                    desired = [de_updated_uuids[BRIDGE_INBOUND_TAG]]
                else:
                    desired = [
                        _resolve_inbound_ref(
                            ref, _profile_uuid_by_tag(spb_profile), de_updated_uuids
                        )
                        for ref in snapshot["inboundRefs"]
                    ]
                await api.request(
                    "PATCH",
                    "/internal-squads",
                    json={
                        "uuid": snapshot["uuid"],
                        "inbounds": list(dict.fromkeys(desired)),
                    },
                )
            for snapshot in manifest["hosts"]:
                ref = snapshot["inboundRef"]
                if ref.get("profile") != "de":
                    continue
                await api.request(
                    "PATCH",
                    "/hosts",
                    json={
                        "uuid": snapshot["host"]["uuid"],
                        "inbound": {
                            "configProfileUuid": de_updated["uuid"],
                            "configProfileInboundUuid": de_updated_uuids[ref["tag"]],
                        },
                    },
                )
            await api.request(
                "PATCH",
                "/nodes",
                json={
                    "uuid": de_node["uuid"],
                    "configProfile": {
                        "activeConfigProfileUuid": de_updated["uuid"],
                        "activeInbounds": [
                            de_updated_uuids[tag] for tag in de_active_tags
                        ],
                    },
                },
            )
            await api.request(
                "POST",
                f"/nodes/{de_node['uuid']}/actions/restart",
                json={"forceRestart": True},
            )
            await _wait_for_node(api, str(de_node["uuid"]))
            _checkpoint(manifest_path, manifest, "de_vless_reality_bridge_ready")

            spb_next = copy.deepcopy(spb_config)
            next_outbounds = []
            for outbound in spb_next.get("outbounds") or []:
                if (
                    not isinstance(outbound, dict)
                    or outbound.get("tag") != BRIDGE_OUTBOUND_TAG
                ):
                    next_outbounds.append(outbound)
                    continue
                next_outbounds.append(
                    {
                        "tag": BRIDGE_OUTBOUND_TAG,
                        "protocol": "vless",
                        "settings": {
                            "address": DE_BRIDGE_ADDRESS,
                            "port": BRIDGE_PORT,
                            "id": bridge_user["vlessUuid"],
                            "encryption": "none",
                        },
                        "streamSettings": {
                            "network": "raw",
                            "security": "reality",
                            "realitySettings": {
                                "serverName": str(server_names[0]),
                                "password": public_key,
                                "shortId": short_id,
                            },
                        },
                    }
                )
            spb_next["outbounds"] = next_outbounds
            spb_routing = copy.deepcopy(spb_next.get("routing") or {})
            management_source = _find_one(
                [
                    rule
                    for rule in spb_routing.get("rules") or []
                    if isinstance(rule, dict)
                ],
                lambda item: item.get("ruleTag") == SOURCE_MANAGEMENT_RULE_TAG,
                "reviewed management/private protection rule",
            )
            if management_source.get("outboundTag") != "BLOCK":
                raise RuntimeError("management/private protection does not fail closed")
            existing_rules = [
                rule
                for rule in spb_routing.get("rules") or []
                if isinstance(rule, dict)
                and rule.get("ruleTag")
                not in {MANAGEMENT_RULE_TAG, ROUTE_RULE_TAG, DIRECT_RULE_TAG}
            ]
            target_user_match = [str(target_user_id)]
            target_inbound_tags = [raw_tag, xhttp_tag]
            management_rule = copy.deepcopy(management_source)
            management_rule.pop("webhook", None)
            management_rule["type"] = "field"
            management_rule["ruleTag"] = MANAGEMENT_RULE_TAG
            management_rule["inboundTag"] = target_inbound_tags
            management_rule["user"] = target_user_match
            spb_routing["domainStrategy"] = "IPOnDemand"
            spb_routing["rules"] = [
                management_rule,
                {
                    "type": "field",
                    "ruleTag": ROUTE_RULE_TAG,
                    "inboundTag": target_inbound_tags,
                    "user": target_user_match,
                    "ip": prefixes,
                    "network": "tcp,udp",
                    "outboundTag": BRIDGE_OUTBOUND_TAG,
                },
                {
                    "type": "field",
                    "ruleTag": DIRECT_RULE_TAG,
                    "inboundTag": target_inbound_tags,
                    "user": target_user_match,
                    "network": "tcp,udp",
                    "outboundTag": "DIRECT",
                },
                *existing_rules,
            ]
            spb_next["routing"] = spb_routing
            spb_dns = copy.deepcopy(
                spb_next.get("dns") if isinstance(spb_next.get("dns"), dict) else {}
            )
            spb_dns["queryStrategy"] = "UseIPv4"
            spb_dns["servers"] = list(SPB_IPV4_DNS_SERVERS)
            spb_next["dns"] = spb_dns
            await api.request(
                "PATCH",
                "/config-profiles",
                json={
                    "uuid": spb_profile["uuid"],
                    "name": spb_profile["name"],
                    "config": spb_next,
                },
            )
            spb_updated = await api.request(
                "GET", f"/config-profiles/{spb_profile['uuid']}"
            )
            spb_updated_uuids = _profile_uuid_by_tag(spb_updated)
            if not {raw_tag, xhttp_tag}.issubset(spb_updated_uuids):
                raise RuntimeError(
                    "updated SPB profile lacks standard customer inbounds"
                )

            for snapshot in manifest["squads"]:
                if snapshot["uuid"] == target_squad["uuid"]:
                    desired = [spb_updated_uuids[raw_tag], spb_updated_uuids[xhttp_tag]]
                elif snapshot["uuid"] == bridge_squad["uuid"]:
                    desired = [de_updated_uuids[BRIDGE_INBOUND_TAG]]
                else:
                    desired = [
                        _resolve_inbound_ref(ref, spb_updated_uuids, de_updated_uuids)
                        for ref in snapshot["inboundRefs"]
                    ]
                await api.request(
                    "PATCH",
                    "/internal-squads",
                    json={
                        "uuid": snapshot["uuid"],
                        "inbounds": list(dict.fromkeys(desired)),
                    },
                )
            for snapshot in manifest["hosts"]:
                ref = snapshot["inboundRef"]
                if ref.get("profile") != "spb":
                    continue
                await api.request(
                    "PATCH",
                    "/hosts",
                    json={
                        "uuid": snapshot["host"]["uuid"],
                        "inbound": {
                            "configProfileUuid": spb_updated["uuid"],
                            "configProfileInboundUuid": spb_updated_uuids[ref["tag"]],
                        },
                    },
                )

            all_other_squad_uuids = sorted(
                str(squad["uuid"])
                for squad in squads
                if str(squad.get("uuid") or "") != str(target_squad["uuid"])
            )
            current_hosts = _collection(await api.request("GET", "/hosts"), "hosts")
            standard_uuids = {spb_updated_uuids[raw_tag], spb_updated_uuids[xhttp_tag]}
            target_hosts: dict[str, dict[str, Any]] = {}
            for host in current_hosts:
                if host.get("remark") in TARGET_HOST_REMARKS:
                    if _host_profile_uuid(host) != str(spb_updated["uuid"]):
                        raise RuntimeError(
                            "target Host remark belongs to another profile"
                        )
                    if str(host["remark"]) in target_hosts:
                        raise RuntimeError("duplicate target Host remark")
                    target_hosts[str(host["remark"])] = host
                elif _host_inbound_uuid(host) in standard_uuids:
                    await api.request(
                        "PATCH",
                        "/hosts",
                        json={
                            "uuid": host["uuid"],
                            "excludedInternalSquads": sorted(
                                _host_exclusions(host) | {str(target_squad["uuid"])}
                            ),
                        },
                    )

            xhttp_path = str(
                (
                    (xhttp_inbound.get("streamSettings") or {}).get("xhttpSettings")
                    or {}
                ).get("path")
                or ""
            )
            if not xhttp_path.startswith("/"):
                raise RuntimeError("SPB XHTTP inbound path is invalid")
            target_specs = (
                (
                    TARGET_RAW_REMARK,
                    spb_updated_uuids[raw_tag],
                    443,
                    None,
                    "WELCOMERU_SPB_REALITY",
                ),
                (
                    TARGET_XHTTP_REMARK,
                    spb_updated_uuids[xhttp_tag],
                    8443,
                    xhttp_path,
                    "WELCOMERU_SPB_XHTTP",
                ),
            )
            for remark, inbound_uuid, port, path, tag in target_specs:
                payload = _target_host_payload(
                    remark=remark,
                    inbound_uuid=inbound_uuid,
                    profile_uuid=str(spb_updated["uuid"]),
                    port=port,
                    path=path,
                    excluded_squads=all_other_squad_uuids,
                    tag=tag,
                )
                existing = target_hosts.get(remark)
                if existing:
                    payload["uuid"] = existing["uuid"]
                    await api.request("PATCH", "/hosts", json=payload)
                else:
                    creation_payload = copy.deepcopy(payload)
                    creation_payload["tags"] = [
                        *creation_payload.get("tags", []),
                        host_creation_tag,
                    ]
                    created = await api.request("POST", "/hosts", json=creation_payload)
                    if not isinstance(created, dict) or not created.get("uuid"):
                        raise RuntimeError("Remnawave did not return the created Host")
                    manifest["createdHostUuids"].append(created["uuid"])
                    _checkpoint(manifest_path, manifest, "spb_target_hosts_creating")
                    await api.request(
                        "PATCH", "/hosts", json={**payload, "uuid": created["uuid"]}
                    )

            await api.request(
                "PATCH",
                "/nodes",
                json={
                    "uuid": spb_node["uuid"],
                    "configProfile": {
                        "activeConfigProfileUuid": spb_updated["uuid"],
                        "activeInbounds": [
                            spb_updated_uuids[tag] for tag in spb_active_tags
                        ],
                    },
                },
            )
            await api.request(
                "POST",
                f"/nodes/{spb_node['uuid']}/actions/restart",
                json={"forceRestart": True},
            )
            await _wait_for_node(api, str(spb_node["uuid"]))
            _checkpoint(manifest_path, manifest, "spb_customer_routing_ready")

            verify_spb = await api.request(
                "GET", f"/config-profiles/{spb_profile['uuid']}"
            )
            verify_de = await api.request(
                "GET", f"/config-profiles/{de_profile['uuid']}"
            )
            verify_plugin = await api.request("GET", f"/node-plugins/{plugin['uuid']}")
            verify_ignored_users = (
                (
                    (verify_plugin.get("pluginConfig") or {}).get("torrentBlocker")
                    or {}
                ).get("ignoreLists")
                or {}
            ).get("userId") or []
            if verify_ignored_users != []:
                raise RuntimeError("torrent blocker unexpectedly exempts a user")
            if (verify_plugin.get("pluginConfig") or {}) != plugin_config:
                raise RuntimeError("node plugin changed during WELCOMERU apply")

            verify_nodes = _collection(await api.request("GET", "/nodes"), "nodes")
            verify_squads = _collection(
                await api.request("GET", "/internal-squads"), "internalSquads"
            )
            verify_hosts = _collection(await api.request("GET", "/hosts"), "hosts")
            for label, address, profile_uuid in (
                ("moscow", MOSCOW_NODE_ADDRESS, moscow_profile_uuid),
                ("netherlands", NL_NODE_ADDRESS, nl_profile_uuid),
            ):
                verify_node = _find_one(
                    verify_nodes,
                    lambda item, expected=address: item.get("address") == expected,
                    f"{label} node",
                )
                verify_profile = await api.request(
                    "GET", f"/config-profiles/{profile_uuid}"
                )
                if (
                    not isinstance(verify_profile, dict)
                    or _stable_control_hash(
                        verify_node,
                        verify_profile,
                        hosts=verify_hosts,
                        squads=verify_squads,
                    )
                    != untouched_hashes[label]
                ):
                    raise RuntimeError(f"{label} control plane changed unexpectedly")
            verify_rules = (verify_spb.get("config") or {}).get("routing", {}).get(
                "rules"
            ) or []
            verify_dns = (verify_spb.get("config") or {}).get("dns") or {}
            if (
                verify_dns.get("queryStrategy") != "UseIPv4"
                or verify_dns.get("servers") != SPB_IPV4_DNS_SERVERS
            ):
                raise RuntimeError("SPB IPv4-only DNS policy verification failed")
            route_rule = _find_one(
                verify_rules,
                lambda item: item.get("ruleTag") == ROUTE_RULE_TAG,
                "route rule",
            )
            management_rule = _find_one(
                verify_rules,
                lambda item: item.get("ruleTag") == MANAGEMENT_RULE_TAG,
                "management protection rule",
            )
            direct_rule = _find_one(
                verify_rules,
                lambda item: item.get("ruleTag") == DIRECT_RULE_TAG,
                "direct rule",
            )
            verify_bridge = _config_inbound_by_tag(
                verify_de.get("config") or {}, BRIDGE_INBOUND_TAG
            )
            verify_bridge_outbound = _find_one(
                [
                    outbound
                    for outbound in (verify_spb.get("config") or {}).get("outbounds")
                    or []
                    if isinstance(outbound, dict)
                ],
                lambda item: item.get("tag") == BRIDGE_OUTBOUND_TAG,
                "updated SPB bridge outbound",
            )
            if (
                verify_bridge.get("protocol") != "vless"
                or (verify_bridge.get("streamSettings") or {}).get("network") != "raw"
                or (verify_bridge.get("streamSettings") or {}).get("security")
                != "reality"
                or (verify_bridge.get("settings") or {}).get("flow") != ""
            ):
                raise RuntimeError("DE bridge control-plane verification failed")
            verify_bridge_outbound_settings = (
                verify_bridge_outbound.get("settings") or {}
            )
            verify_bridge_outbound_stream = (
                verify_bridge_outbound.get("streamSettings") or {}
            )
            verify_bridge_outbound_reality = (
                verify_bridge_outbound_stream.get("realitySettings") or {}
            )
            if (
                verify_bridge_outbound.get("protocol") != "vless"
                or verify_bridge_outbound_settings.get("address") != DE_BRIDGE_ADDRESS
                or verify_bridge_outbound_settings.get("port") != BRIDGE_PORT
                or verify_bridge_outbound_settings.get("id") != bridge_user["vlessUuid"]
                or verify_bridge_outbound_settings.get("encryption") != "none"
                or "flow" in verify_bridge_outbound_settings
                or verify_bridge_outbound_stream.get("network") != "raw"
                or verify_bridge_outbound_stream.get("security") != "reality"
                or not verify_bridge_outbound_reality.get("serverName")
                or not verify_bridge_outbound_reality.get("password")
                or not verify_bridge_outbound_reality.get("shortId")
            ):
                raise RuntimeError("SPB VLESS RAW Reality bridge outbound is invalid")
            if (
                route_rule.get("type") != "field"
                or route_rule.get("ip") != prefixes
                or route_rule.get("network") != "tcp,udp"
                or route_rule.get("inboundTag") != target_inbound_tags
                or route_rule.get("user") != target_user_match
                or route_rule.get("outboundTag") != BRIDGE_OUTBOUND_TAG
            ):
                raise RuntimeError("SPB BGP route control-plane verification failed")
            target_rule_order = [
                rule.get("ruleTag")
                for rule in verify_rules
                if rule.get("ruleTag")
                in {MANAGEMENT_RULE_TAG, ROUTE_RULE_TAG, DIRECT_RULE_TAG}
            ]
            if (
                management_rule.get("type") != "field"
                or management_rule.get("inboundTag") != target_inbound_tags
                or management_rule.get("user") != target_user_match
                or management_rule.get("outboundTag") != "BLOCK"
                or target_rule_order
                != [MANAGEMENT_RULE_TAG, ROUTE_RULE_TAG, DIRECT_RULE_TAG]
            ):
                raise RuntimeError(
                    "SPB target routing safety order verification failed"
                )
            if (
                direct_rule.get("type") != "field"
                or direct_rule.get("inboundTag") != target_inbound_tags
                or direct_rule.get("user") != target_user_match
                or direct_rule.get("outboundTag") != "DIRECT"
                or direct_rule.get("network") != "tcp,udp"
            ):
                raise RuntimeError(
                    "SPB direct fallback control-plane verification failed"
                )

            verify_target_squad = _find_one(
                verify_squads,
                lambda item: str(item.get("uuid")) == str(target_squad["uuid"]),
                "updated target squad",
            )
            verify_spb_uuids = _profile_uuid_by_tag(verify_spb)
            if set(_squad_inbounds(verify_target_squad)) != {
                verify_spb_uuids[raw_tag],
                verify_spb_uuids[xhttp_tag],
            }:
                raise RuntimeError(
                    "target squad does not contain exactly two SPB inbounds"
                )

            visible_target_hosts = [
                host
                for host in verify_hosts
                if _host_inbound_uuid(host) in set(_squad_inbounds(verify_target_squad))
                and str(target_squad["uuid"]) not in _host_exclusions(host)
                and host.get("isDisabled") is not True
            ]
            if {
                host.get("remark") for host in visible_target_hosts
            } != TARGET_HOST_REMARKS:
                raise RuntimeError(
                    "target subscription Host set is not exactly the SPB pair"
                )
            if any(
                host_creation_tag in (host.get("tags") or [])
                for host in visible_target_hosts
            ):
                raise RuntimeError("temporary Host creation marker was not removed")

            _checkpoint(manifest_path, manifest, "applied")
            return {
                **plan,
                "status": "applied",
                "bridgeProtocol": "vless-raw-reality-without-vision",
                "targetVisibleHostCount": len(visible_target_hosts),
                "nodeRestarts": ["de", "spb"],
                "rollbackManifest": str(manifest_path),
            }
        except Exception as apply_error:
            if mutation_started:
                try:
                    await _restore(api, manifest, manifest_path)
                except Exception:
                    _checkpoint(manifest_path, manifest, "rollback_failed")
                    raise RuntimeError("apply and automatic rollback failed") from None
            raise RuntimeError("apply failed and was rolled back") from apply_error
    finally:
        await api.close()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--rollback", action="store_true")
    parser.add_argument("--remnawave-url", default="http://remnawave:3000/api")
    parser.add_argument("--token-file")
    parser.add_argument("--target-user-ref", required=False)
    parser.add_argument("--target-user-ref-file")
    parser.add_argument("--canonical-artifact", type=Path)
    parser.add_argument("--artifact-manifest", type=Path)
    parser.add_argument("--active-pointer", type=Path)
    parser.add_argument("--last-known-good-pointer", type=Path)
    parser.add_argument("--rollback-manifest", type=Path, required=True)
    args = parser.parse_args()
    if not args.rollback:
        if not args.target_user_ref and not args.target_user_ref_file:
            parser.error("--target-user-ref or --target-user-ref-file is required")
        if args.canonical_artifact is None:
            parser.error("--canonical-artifact is required")
        if args.artifact_manifest is None:
            parser.error("--artifact-manifest is required")
        if args.active_pointer is None:
            parser.error("--active-pointer is required")
        if args.last_known_good_pointer is None:
            parser.error("--last-known-good-pointer is required")
    return args


def main() -> int:
    try:
        result = asyncio.run(_run(_parse_args()))
    except Exception as error:
        status = (
            error.response.status_code
            if isinstance(error, httpx.HTTPStatusError)
            else None
        )
        reason = str(error) if isinstance(error, RuntimeError) else None
        print(
            json.dumps(
                {
                    "status": "failed",
                    "errorClass": type(error).__name__,
                    "httpStatus": status,
                    "reason": reason,
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
