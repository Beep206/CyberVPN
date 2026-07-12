#!/usr/bin/env python3
"""Apply the INCY-compatible Premium Smart RU policy to the Frankfurt node.

The regular XRAY_BASE64 subscription contains individual VLESS links and cannot
carry Mihomo routing rules. This operator tool creates a Frankfurt-only Xray
Config Profile that keeps global traffic in Germany and forwards Russian
destinations to Moscow through a dedicated Remnawave service user.

The Remnawave token is a secret and must be supplied only through an environment
variable. The rollback manifest contains private Config Profile material and
must remain mode 0600 outside the repository.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import copy
import hashlib
import json
import os
import stat
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx

BASE_PROFILE_NAME = "S1 DE VLESS XHTTP"
DE_PROFILE_NAME = "S1 DE Smart RU Server"
MOSCOW_PROFILE_NAME = "S1 Moscow Smart Global Server"
DE_NODE_ADDRESS = "138.124.115.206"
DE_PUBLIC_HOST = "de-relay.cyber-vpn.org"
MOSCOW_PUBLIC_HOST = "msk-relay.cyber-vpn.org"
MOSCOW_NODE_ADDRESS = "178.159.94.225"
MOSCOW_NODE_NAME = "🇷🇺 RU Moscow 01 25G"
MOSCOW_UPSTREAM_ADDRESS = "2a12:5940:e38b::2"
FRANKFURT_UPSTREAM_ADDRESS = "2a0b:4140:ba84::2"
SMART_SQUAD_NAME = "CYBERVPN_PREMIUM_SMART_RU_NODES"
EXTERNAL_SQUAD_NAME = "CYBERVPN_PREMIUM_SMART_RU"
BRIDGE_SQUAD_NAME = "CYBERVPN_SMART_RU_BRIDGE"
BRIDGE_USERNAME = "cybervpn_de_ru_bridge"
BRIDGE_INBOUND_TAG = "MSK_SMART_RU_BRIDGE_9443"
GLOBAL_BRIDGE_SQUAD_NAME = "CYBERVPN_SMART_GLOBAL_BRIDGE"
GLOBAL_BRIDGE_USERNAME = "cybervpn_ru_de_bridge"
GLOBAL_BRIDGE_INBOUND_TAG = "DE_SMART_GLOBAL_BRIDGE_9443"
GLOBAL_BRIDGE_OUTBOUND_TAG = "DE_GLOBAL_BRIDGE"
BRIDGE_PORT = 9443
POLICY_ARTIFACT_DIR = Path(__file__).resolve().parent / "generated" / "premium_smart_ru"
POLICY_PATH = Path(__file__).resolve().parent / "policies" / "premium_smart_ru.yaml"
XRAY_SERVER_ARTIFACT = "xray-server.json"
LEGACY_HEADER_ARTIFACT = "legacy-routing-header.json"
DE_INCY_AUXILIARY_TAGS = frozenset(
    {
        "PREMIUM_SMART_RU_INCY_DE_RAW",
        "PREMIUM_SMART_RU_INCY_DE_XHTTP",
        "PREMIUM_SMART_RU_INCY_VIRTUAL",
    }
)
MOSCOW_INCY_AUXILIARY_TAGS = frozenset(
    {
        "PREMIUM_SMART_RU_INCY_MSK_RAW",
        "PREMIUM_SMART_RU_INCY_MSK_XHTTP",
    }
)


def _find_repo_root() -> Path | None:
    script_path = Path(__file__).resolve()
    for candidate in (script_path.parent, *script_path.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def _has_expected_auxiliary_tag(
    host: dict[str, Any], allowed_tags: frozenset[str]
) -> bool:
    tags = host.get("tags")
    return isinstance(tags, list) and any(tag in allowed_tags for tag in tags)


REPO_ROOT = _find_repo_root()
OLD_TO_NEW_TAG = {
    "VLESS_REALITY_443": "DE_SMART_REALITY_443",
    "VLESS_XHTTP_REALITY_8443": "DE_SMART_XHTTP_REALITY_8443",
}
CUSTOMER_INBOUND_TAGS = list(OLD_TO_NEW_TAG)
DE_CUSTOMER_INBOUND_TAGS = list(OLD_TO_NEW_TAG.values())
MOSCOW_OLD_TO_NEW_TAG = {
    "VLESS_REALITY_443": "MSK_SMART_REALITY_443",
    "VLESS_XHTTP_REALITY_8443": "MSK_SMART_XHTTP_REALITY_8443",
    BRIDGE_INBOUND_TAG: "MSK_SMART_RU_BRIDGE_V2_9443",
}
MOSCOW_CUSTOMER_INBOUND_TAGS = [
    MOSCOW_OLD_TO_NEW_TAG[tag] for tag in CUSTOMER_INBOUND_TAGS
]
MOSCOW_BRIDGE_INBOUND_TAG = MOSCOW_OLD_TO_NEW_TAG[BRIDGE_INBOUND_TAG]
BRIDGE_INBOUND_TAGS = {
    BRIDGE_INBOUND_TAG,
    MOSCOW_BRIDGE_INBOUND_TAG,
    GLOBAL_BRIDGE_INBOUND_TAG,
}
RELAY_PUBLIC_HOST_PORT_BY_TAG = {
    "VLESS_REALITY_443": 2053,
    "VLESS_XHTTP_REALITY_8443": 2083,
    "DE_SMART_REALITY_443": 2053,
    "DE_SMART_XHTTP_REALITY_8443": 2083,
    "MSK_SMART_REALITY_443": 2053,
    "MSK_SMART_XHTTP_REALITY_8443": 2083,
}


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _load_policy_artifact(artifact_dir: Path, name: str) -> dict[str, Any]:
    manifest_path = artifact_dir / "manifest.json"
    artifact_path = artifact_dir / name
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        content = artifact_path.read_bytes()
        artifact = json.loads(content)
        policy_content = POLICY_PATH.read_bytes()
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            f"Cannot load compiled policy artifact {name}: {exc}"
        ) from exc

    metadata = manifest.get("artifacts", {}).get(name)
    if not isinstance(metadata, dict):
        raise RuntimeError(f"Compiler manifest does not declare {name}")
    if metadata.get("bytes") != len(content) or metadata.get("sha256") != _sha256(
        content
    ):
        raise RuntimeError(f"Compiled policy artifact {name} checksum or size mismatch")
    if manifest.get("source", {}).get("sha256") != _sha256(policy_content):
        raise RuntimeError(
            f"Compiled policy artifact {name} is stale for canonical policy"
        )
    coverage_name = {
        XRAY_SERVER_ARTIFACT: "xrayServer",
        LEGACY_HEADER_ARTIFACT: "legacyHeader",
    }[name]
    coverage = manifest.get("rendererCoverage", {}).get(coverage_name)
    if not isinstance(coverage, dict) or coverage.get("status") != "rendered":
        raise RuntimeError(
            f"Compiler manifest does not mark {coverage_name} as rendered"
        )
    if coverage.get("artifact") != name:
        raise RuntimeError(
            f"Compiler manifest points {coverage_name} to another artifact"
        )
    if (
        artifact.get("schemaVersion") != 1
        or artifact.get("product") != "premium_smart_ru"
    ):
        raise RuntimeError(
            f"Compiled policy artifact {name} has an unsupported contract"
        )
    return artifact


def _load_policy_artifacts(
    artifact_dir: Path = POLICY_ARTIFACT_DIR,
) -> tuple[dict[str, Any], str]:
    server = _load_policy_artifact(artifact_dir, XRAY_SERVER_ARTIFACT)
    legacy = _load_policy_artifact(artifact_dir, LEGACY_HEADER_ARTIFACT)
    if server.get("consumer") != "remnawave-xray-server":
        raise RuntimeError("Compiled server routing artifact has an invalid consumer")
    if legacy.get("consumer") != "remnawave-legacy-routing-header":
        raise RuntimeError("Compiled legacy routing artifact has an invalid consumer")
    value = legacy.get("value")
    decoded = legacy.get("decoded")
    if not isinstance(value, str) or not isinstance(decoded, dict):
        raise RuntimeError("Compiled legacy routing artifact is incomplete")
    try:
        encoded_decoded = json.loads(base64.b64decode(value, validate=True))
    except (ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            "Compiled legacy routing header is not valid base64 JSON"
        ) from exc
    if encoded_decoded != decoded:
        raise RuntimeError("Compiled legacy routing header payload mismatch")
    return server, value


def _policy_routing_rules(
    artifact: dict[str, Any],
    *,
    inbound_tags: list[str],
    action_tags: dict[str, str],
) -> list[dict[str, Any]]:
    typed_rules = artifact.get("rules")
    if not isinstance(typed_rules, list) or not typed_rules:
        raise RuntimeError("Compiled server routing artifact contains no rules")
    rendered: list[dict[str, Any]] = []
    for typed_rule in typed_rules:
        if not isinstance(typed_rule, dict):
            raise RuntimeError(
                "Compiled server routing artifact contains an invalid rule"
            )
        action = typed_rule.get("action")
        if action not in action_tags:
            raise RuntimeError(
                "Compiled server routing artifact contains an invalid action"
            )
        matches = typed_rule.get("matches")
        if not isinstance(matches, list) or not matches:
            raise RuntimeError(
                f"Compiled server routing rule {typed_rule.get('id')} has no matcher"
            )
        for match in matches:
            if not isinstance(match, dict) or not match:
                raise RuntimeError(
                    "Compiled server routing artifact contains an empty matcher"
                )
            # Client process matchers have no meaningful identity on a remote Xray server.
            if set(match) == {"process"}:
                continue
            rendered.append(
                {
                    **match,
                    "ruleTag": str(typed_rule["id"]),
                    "inboundTag": list(inbound_tags),
                    "outboundTag": action_tags[action],
                }
            )
    if not rendered:
        raise RuntimeError("Compiled server routing artifact rendered no server rules")
    return rendered


def _policy_domain_count(artifact: dict[str, Any], action: str) -> int:
    return sum(
        len(match.get("domain", []))
        for rule in artifact["rules"]
        if rule.get("action") == action
        for match in rule.get("matches", [])
        if isinstance(match, dict)
    )


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
        data = response.json()
        if isinstance(data, dict) and set(data) == {"response"}:
            return data["response"]
        return data

    async def close(self) -> None:
        await self._client.aclose()


def _collection(data: Any, key: str) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict) and isinstance(data.get(key), list):
        return [item for item in data[key] if isinstance(item, dict)]
    return []


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


def _node_inbound_uuids(node: dict[str, Any]) -> list[str]:
    config_profile = node.get("configProfile") or {}
    return [
        item["uuid"] if isinstance(item, dict) else str(item)
        for item in config_profile.get("activeInbounds", [])
    ]


def _bridge_inbound(tag: str) -> dict[str, Any]:
    return {
        "tag": tag,
        "port": BRIDGE_PORT,
        "listen": "0.0.0.0",  # noqa: S104 - bridge access is service-user/squad scoped.
        "protocol": "shadowsocks",
        "settings": {"clients": [], "network": "tcp,udp"},
        "sniffing": {
            "enabled": True,
            "destOverride": ["http", "tls", "quic"],
            "routeOnly": True,
        },
    }


def _isolated_squad_inbounds(inbound_uuid: str) -> list[str]:
    return [inbound_uuid]


def _isolated_user_squads(squad_uuid: str) -> list[str]:
    return [squad_uuid]


def _validate_existing_bridge_user_isolation(
    user: dict[str, Any] | None,
    squad: dict[str, Any] | None,
    *,
    label: str,
) -> None:
    if user is None:
        return
    allowed = {str(squad["uuid"])} if squad is not None else set()
    assigned = set(_squad_uuids(user))
    if not assigned.issubset(allowed):
        raise RuntimeError(f"Existing {label} user has non-bridge squad assignments")


def _profile_inbound_uuid_by_tag(profile: dict[str, Any]) -> dict[str, str]:
    return {
        str(item["tag"]): str(item["uuid"])
        for item in profile.get("inbounds", [])
        if isinstance(item, dict) and item.get("tag") and item.get("uuid")
    }


def _bridge_inbound_uuids_from_profiles(*profiles: dict[str, Any] | None) -> set[str]:
    bridge_uuids: set[str] = set()
    for profile in profiles:
        if not isinstance(profile, dict):
            continue
        for tag, inbound_uuid in _profile_inbound_uuid_by_tag(profile).items():
            if tag in BRIDGE_INBOUND_TAGS:
                bridge_uuids.add(inbound_uuid)
    return bridge_uuids


def _desired_customer_squad_inbounds(
    current_inbounds: list[str],
    managed_customer_inbounds: list[str],
    bridge_inbound_uuids: set[str],
) -> list[str]:
    return list(
        dict.fromkeys(
            [
                inbound_uuid
                for inbound_uuid in current_inbounds
                if inbound_uuid not in bridge_inbound_uuids
            ]
            + managed_customer_inbounds
        )
    )


def _ordered_inbound_uuids(tag_to_uuid: dict[str, str], tags: list[str]) -> list[str]:
    missing = [tag for tag in tags if tag not in tag_to_uuid]
    if missing:
        raise RuntimeError(
            f"Config profile is missing expected inbound tag(s): {', '.join(missing)}"
        )
    return [tag_to_uuid[tag] for tag in tags]


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
    if parsed.hostname.casefold() not in normalized_allowed:
        raise RuntimeError("Remnawave URL hostname is not in the operator allowlist")


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


def _build_base_config(base_config: dict[str, Any]) -> dict[str, Any]:
    config = copy.deepcopy(base_config)
    direct_outbound = next(
        (
            outbound
            for outbound in config.get("outbounds", [])
            if outbound.get("tag") == "DIRECT"
        ),
        None,
    )
    if direct_outbound is None or direct_outbound.get("protocol") != "freedom":
        raise RuntimeError("Base profile must contain the DIRECT freedom outbound")
    direct_settings = direct_outbound.get("settings")
    if not isinstance(direct_settings, dict):
        direct_settings = {}
        direct_outbound["settings"] = direct_settings
    direct_settings["domainStrategy"] = "UseIPv4"

    config["inbounds"] = [
        inbound
        for inbound in config.get("inbounds", [])
        if inbound.get("tag") != BRIDGE_INBOUND_TAG
    ]
    config["inbounds"].append(_bridge_inbound(BRIDGE_INBOUND_TAG))
    return config


def _validate_public_host_shape(
    hosts: list[dict[str, Any]],
    *,
    inbound_tag_by_uuid: dict[str, str],
    label: str,
) -> None:
    if len(hosts) != 2:
        raise RuntimeError(f"Expected exactly two {label} hosts, found {len(hosts)}")

    tags = []
    for host in hosts:
        inbound = host.get("inbound")
        inbound = inbound if isinstance(inbound, dict) else {}
        inbound_uuid = str(inbound.get("configProfileInboundUuid") or "")
        tag = inbound_tag_by_uuid.get(inbound_uuid, "")
        if not tag:
            raise RuntimeError(
                f"{label} host references an unknown config-profile inbound"
            )
        if bool(
            host.get("isDisabled")
            if "isDisabled" in host
            else host.get("is_disabled", False)
        ):
            raise RuntimeError(f"{label} host must be enabled")
        exclusions = host.get("excludeFromSubscriptionTypes")
        if exclusions is None:
            exclusions = host.get("exclude_from_subscription_types") or []
        if any(str(item).casefold() == "xray_base64" for item in exclusions):
            raise RuntimeError(f"{label} host must not be excluded from XRAY_BASE64")
        if "port" in host:
            expected_port = RELAY_PUBLIC_HOST_PORT_BY_TAG.get(tag)
            if expected_port is not None and int(host["port"]) != expected_port:
                raise RuntimeError(f"{label} host port does not match its inbound tag")
        tags.append(tag)

    raw_count = sum(
        tag in {"VLESS_REALITY_443", "DE_SMART_REALITY_443", "MSK_SMART_REALITY_443"}
        for tag in tags
    )
    xhttp_count = sum(
        tag
        in {
            "VLESS_XHTTP_REALITY_8443",
            "DE_SMART_XHTTP_REALITY_8443",
            "MSK_SMART_XHTTP_REALITY_8443",
        }
        for tag in tags
    )
    if raw_count != 1 or xhttp_count != 1:
        raise RuntimeError(
            f"{label} hosts must contain exactly one RAW and one XHTTP inbound"
        )


def _validate_frankfurt_host_shape(
    hosts: list[dict[str, Any]],
    *,
    inbound_tag_by_uuid: dict[str, str],
) -> None:
    _validate_public_host_shape(
        hosts,
        inbound_tag_by_uuid=inbound_tag_by_uuid,
        label="Frankfurt",
    )


def _validate_moscow_host_shape(
    hosts: list[dict[str, Any]],
    *,
    inbound_tag_by_uuid: dict[str, str],
) -> None:
    _validate_public_host_shape(
        hosts,
        inbound_tag_by_uuid=inbound_tag_by_uuid,
        label="Moscow",
    )


def _validate_no_public_bridge_hosts(
    hosts: list[dict[str, Any]],
    *profiles: dict[str, Any] | None,
) -> None:
    bridge_inbound_uuids = _bridge_inbound_uuids_from_profiles(*profiles)
    for host in hosts:
        inbound = host.get("inbound")
        inbound = inbound if isinstance(inbound, dict) else {}
        inbound_uuid = str(inbound.get("configProfileInboundUuid") or "")
        if inbound_uuid in bridge_inbound_uuids:
            raise RuntimeError("Bridge inbounds must not have public Remnawave hosts")


def _build_config(
    base_config: dict[str, Any],
    bridge_ss_password: str,
    moscow_upstream: str,
    policy_artifact: dict[str, Any],
) -> dict[str, Any]:
    config = copy.deepcopy(base_config)
    config["inbounds"] = [
        copy.deepcopy(inbound)
        for inbound in config.get("inbounds", [])
        if inbound.get("tag") in OLD_TO_NEW_TAG
    ]
    for inbound in config["inbounds"]:
        inbound["tag"] = OLD_TO_NEW_TAG[inbound["tag"]]
    config["inbounds"].append(_bridge_inbound(GLOBAL_BRIDGE_INBOUND_TAG))

    config["outbounds"] = [
        outbound
        for outbound in config.get("outbounds", [])
        if outbound.get("tag") != "RU_MSK_BRIDGE"
    ]
    config["outbounds"].append(
        {
            "tag": "RU_MSK_BRIDGE",
            "protocol": "shadowsocks",
            "settings": {
                "servers": [
                    {
                        "address": moscow_upstream,
                        "port": BRIDGE_PORT,
                        "password": bridge_ss_password,
                        "method": "chacha20-ietf-poly1305",
                        "level": 0,
                    }
                ]
            },
        }
    )

    inbound_tags = list(OLD_TO_NEW_TAG.values())
    config["routing"] = {
        "domainStrategy": "IPIfNonMatch",
        "rules": _policy_routing_rules(
            policy_artifact,
            inbound_tags=inbound_tags,
            action_tags={
                "direct": "DIRECT",
                "block": "BLOCK",
                "eu": "DIRECT",
                "ru": "RU_MSK_BRIDGE",
            },
        ),
    }
    return config


def _build_moscow_global_config(
    base_config: dict[str, Any],
    bridge_ss_password: str,
    frankfurt_upstream: str,
    policy_artifact: dict[str, Any],
) -> dict[str, Any]:
    config = copy.deepcopy(base_config)
    inbound_by_tag = {
        inbound.get("tag"): inbound
        for inbound in config.get("inbounds", [])
        if isinstance(inbound, dict) and inbound.get("tag")
    }
    expected_inbounds = CUSTOMER_INBOUND_TAGS + [BRIDGE_INBOUND_TAG]
    missing_inbounds = [tag for tag in expected_inbounds if tag not in inbound_by_tag]
    if missing_inbounds:
        raise RuntimeError(
            f"Moscow profile base config is missing inbound tag(s): {', '.join(missing_inbounds)}"
        )
    config["inbounds"] = [
        copy.deepcopy(inbound_by_tag[tag]) for tag in expected_inbounds
    ]
    for inbound in config["inbounds"]:
        inbound["tag"] = MOSCOW_OLD_TO_NEW_TAG[inbound["tag"]]

    outbounds = [
        outbound
        for outbound in config.get("outbounds", [])
        if isinstance(outbound, dict)
        and outbound.get("tag") != GLOBAL_BRIDGE_OUTBOUND_TAG
    ]
    direct_outbound = next(
        (outbound for outbound in outbounds if outbound.get("tag") == "DIRECT"), None
    )
    if direct_outbound is None or direct_outbound.get("protocol") != "freedom":
        raise RuntimeError("Moscow profile must contain the DIRECT freedom outbound")
    outbounds = [direct_outbound] + [
        outbound for outbound in outbounds if outbound is not direct_outbound
    ]
    outbounds.append(
        {
            "tag": GLOBAL_BRIDGE_OUTBOUND_TAG,
            "protocol": "shadowsocks",
            "settings": {
                "servers": [
                    {
                        "address": frankfurt_upstream,
                        "port": BRIDGE_PORT,
                        "password": bridge_ss_password,
                        "method": "chacha20-ietf-poly1305",
                        "level": 0,
                    }
                ]
            },
        }
    )
    config["outbounds"] = outbounds

    inbound_tags = list(MOSCOW_CUSTOMER_INBOUND_TAGS)

    config["routing"] = {
        "domainStrategy": "IPIfNonMatch",
        "rules": _policy_routing_rules(
            policy_artifact,
            inbound_tags=inbound_tags,
            action_tags={
                "direct": "DIRECT",
                "block": "BLOCK",
                "eu": GLOBAL_BRIDGE_OUTBOUND_TAG,
                "ru": "DIRECT",
            },
        ),
    }
    return config


def _validate_manifest_target_stat(target_stat: os.stat_result) -> None:
    if not stat.S_ISREG(target_stat.st_mode):
        raise RuntimeError("Rollback manifest target must be a regular file")
    if target_stat.st_nlink != 1:
        raise RuntimeError("Rollback manifest target must not have hard links")
    if os.name != "nt":
        if target_stat.st_uid != os.geteuid():
            raise RuntimeError("Rollback manifest target must be owned by the operator")
        if target_stat.st_mode & 0o077:
            raise RuntimeError("Rollback manifest target permissions must be 0600")


def _validate_existing_manifest_target(path: Path) -> os.stat_result | None:
    try:
        target_stat = path.lstat()
    except FileNotFoundError:
        return None
    _validate_manifest_target_stat(target_stat)
    return target_stat


def _validate_manifest_parent(path: Path) -> None:
    parent_stat = path.parent.lstat()
    if not stat.S_ISDIR(parent_stat.st_mode):
        raise RuntimeError("Rollback manifest parent must be a directory")
    if os.name != "nt":
        if parent_stat.st_uid != os.geteuid():
            raise RuntimeError("Rollback manifest parent must be owned by the operator")
        if parent_stat.st_mode & 0o002:
            raise RuntimeError(
                "Rollback manifest parent directory must not be world-writable"
            )


def _fsync_directory(path: Path) -> None:
    if os.name == "nt":
        return
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_manifest(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    _validate_manifest_parent(path)
    _validate_existing_manifest_target(path)

    disk_payload = copy.deepcopy(payload)
    if not isinstance(disk_payload, dict):
        raise RuntimeError("Rollback manifest payload must be an object")

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
        _fsync_directory(path.parent)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def _validate_manifest_path(path: Path) -> Path:
    resolved = path.expanduser().resolve(strict=False)
    if any(part.casefold() == ".codex" for part in resolved.parts):
        raise RuntimeError("Rollback manifest must not be under a .codex directory")
    if REPO_ROOT is not None and (
        resolved == REPO_ROOT or REPO_ROOT in resolved.parents
    ):
        raise RuntimeError("Rollback manifest must be outside the repository")
    return resolved


def _read_manifest(path: Path) -> dict[str, Any]:
    _validate_manifest_parent(path)
    expected_stat = _validate_existing_manifest_target(path)
    if expected_stat is None:
        raise RuntimeError("Rollback manifest does not exist")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise RuntimeError(f"Cannot safely open rollback manifest: {exc}") from exc
    with os.fdopen(descriptor, "r", encoding="utf-8") as handle:
        opened_stat = os.fstat(handle.fileno())
        _validate_manifest_target_stat(opened_stat)
        if (opened_stat.st_dev, opened_stat.st_ino) != (
            expected_stat.st_dev,
            expected_stat.st_ino,
        ):
            raise RuntimeError("Rollback manifest changed while it was being opened")
        payload = json.load(handle)
        current_stat = path.lstat()
        if (opened_stat.st_dev, opened_stat.st_ino) != (
            current_stat.st_dev,
            current_stat.st_ino,
        ):
            raise RuntimeError("Rollback manifest changed while it was being read")
    if not isinstance(payload, dict) or payload.get("version") not in {2, 3}:
        raise RuntimeError("Rollback manifest version is not supported")
    return payload


def _checkpoint(path: Path, manifest: dict[str, Any], phase: str) -> None:
    manifest["phase"] = phase
    _write_manifest(path, manifest)


async def _delete_if_present(api: RemnawaveApi, path: str) -> None:
    try:
        await api.request("DELETE", path)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code != 404:
            raise


async def _rollback(
    api: RemnawaveApi, manifest: dict[str, Any], manifest_path: Path
) -> dict[str, Any]:
    bridge_user = manifest.get("bridgeUser")
    if bridge_user:
        await api.request(
            "PATCH",
            "/users",
            json={
                "uuid": bridge_user["uuid"],
                "activeInternalSquads": bridge_user["activeInternalSquads"],
            },
        )
    elif manifest.get("bridgeUsername"):
        current_user = await _get_user(api, manifest["bridgeUsername"])
        if current_user:
            await _delete_if_present(api, f"/users/{current_user['uuid']}")

    global_bridge_user = manifest.get("globalBridgeUser")
    if global_bridge_user:
        await api.request(
            "PATCH",
            "/users",
            json={
                "uuid": global_bridge_user["uuid"],
                "activeInternalSquads": global_bridge_user["activeInternalSquads"],
            },
        )
    elif manifest.get("globalBridgeUsername"):
        current_global_user = await _get_user(api, manifest["globalBridgeUsername"])
        if current_global_user:
            await _delete_if_present(api, f"/users/{current_global_user['uuid']}")

    smart_squad = manifest["smartSquad"]
    await api.request(
        "PATCH",
        "/internal-squads",
        json={"uuid": smart_squad["uuid"], "inbounds": smart_squad["inbounds"]},
    )
    external_squad = manifest["externalSquad"]
    await api.request(
        "PATCH",
        "/external-squads",
        json={
            "uuid": external_squad["uuid"],
            "responseHeaders": external_squad["responseHeaders"],
        },
    )
    bridge_squad = manifest.get("bridgeSquad")
    if bridge_squad:
        await api.request(
            "PATCH",
            "/internal-squads",
            json={
                "uuid": bridge_squad["uuid"],
                "inbounds": bridge_squad["inbounds"],
            },
        )
    elif manifest.get("bridgeSquadName"):
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

    global_bridge_squad = manifest.get("globalBridgeSquad")
    if global_bridge_squad:
        await api.request(
            "PATCH",
            "/internal-squads",
            json={
                "uuid": global_bridge_squad["uuid"],
                "inbounds": global_bridge_squad["inbounds"],
            },
        )
    elif manifest.get("globalBridgeSquadName"):
        squads = _collection(
            await api.request("GET", "/internal-squads"), "internalSquads"
        )
        created_global_squad = next(
            (
                item
                for item in squads
                if item.get("name") == manifest["globalBridgeSquadName"]
            ),
            None,
        )
        if created_global_squad:
            await _delete_if_present(
                api, f"/internal-squads/{created_global_squad['uuid']}"
            )

    for host in manifest.get("deHosts", []):
        await api.request(
            "PATCH",
            "/hosts",
            json={"uuid": host["uuid"], "inbound": host["inbound"]},
        )
    for host in manifest.get("moscowHosts", []):
        await api.request(
            "PATCH",
            "/hosts",
            json={"uuid": host["uuid"], "inbound": host["inbound"]},
        )
    for node_key in ("deNode", "moscowNode"):
        node = manifest.get(node_key)
        if not node:
            continue
        await api.request(
            "PATCH",
            "/nodes",
            json={
                "uuid": node["uuid"],
                "configProfile": _normalize_node_config_profile(node["configProfile"]),
            },
        )

    base_profile = manifest["baseProfile"]
    await api.request(
        "PATCH",
        "/config-profiles",
        json={
            "uuid": base_profile["uuid"],
            "name": base_profile["name"],
            "config": base_profile["config"],
        },
    )
    de_profile = manifest.get("deProfile")
    if de_profile:
        await api.request(
            "PATCH",
            "/config-profiles",
            json={
                "uuid": de_profile["uuid"],
                "name": de_profile["name"],
                "config": de_profile["config"],
            },
        )
    moscow_profile = manifest.get("moscowProfile")
    if moscow_profile:
        await api.request(
            "PATCH",
            "/config-profiles",
            json={
                "uuid": moscow_profile["uuid"],
                "name": moscow_profile["name"],
                "config": moscow_profile["config"],
            },
        )

    profiles = _collection(
        await api.request("GET", "/config-profiles"), "configProfiles"
    )
    if de_profile is None:
        created = next(
            (
                item
                for item in profiles
                if item.get("name") == manifest["deProfileName"]
            ),
            None,
        )
        if created:
            await _delete_if_present(api, f"/config-profiles/{created['uuid']}")
    if moscow_profile is None and manifest.get("moscowProfileName"):
        created_moscow_profile = next(
            (
                item
                for item in profiles
                if item.get("name") == manifest["moscowProfileName"]
            ),
            None,
        )
        if created_moscow_profile:
            await _delete_if_present(
                api, f"/config-profiles/{created_moscow_profile['uuid']}"
            )

    restored_node_uuids = [
        node["uuid"]
        for node_key in ("deNode", "moscowNode")
        if (node := manifest.get(node_key))
    ]
    for node_uuid in restored_node_uuids:
        await api.request(
            "POST",
            f"/nodes/{node_uuid}/actions/restart",
            json={"forceRestart": True},
        )

    _checkpoint(manifest_path, manifest, "rolled_back")
    return {"mode": "rollback", "status": "rolled_back"}


async def _run(args: argparse.Namespace) -> dict[str, Any]:
    token = os.environ.get("REMNAWAVE_TOKEN") or os.environ.get("REMNAWAVE_API_TOKEN")
    if not token:
        raise RuntimeError("REMNAWAVE_TOKEN or REMNAWAVE_API_TOKEN is required")

    _validate_remnawave_url(args.remnawave_url, args.allow_remnawave_host)
    manifest_path = _validate_manifest_path(args.rollback_manifest)

    api = RemnawaveApi(
        args.remnawave_url,
        token,
        trusted_proxy_headers=args.trusted_proxy_headers,
    )
    try:
        if args.rollback:
            return await _rollback(api, _read_manifest(manifest_path), manifest_path)

        policy_artifact, legacy_routing_header = _load_policy_artifacts()

        profiles = _collection(
            await api.request("GET", "/config-profiles"), "configProfiles"
        )
        base_ref = next(
            item for item in profiles if item.get("name") == args.base_profile
        )
        base_profile = await api.request("GET", f"/config-profiles/{base_ref['uuid']}")
        existing_profile_ref = next(
            (item for item in profiles if item.get("name") == args.de_profile),
            None,
        )
        existing_profile = (
            await api.request("GET", f"/config-profiles/{existing_profile_ref['uuid']}")
            if existing_profile_ref
            else None
        )
        existing_moscow_profile_ref = next(
            (item for item in profiles if item.get("name") == args.moscow_profile),
            None,
        )
        existing_moscow_profile = (
            await api.request(
                "GET", f"/config-profiles/{existing_moscow_profile_ref['uuid']}"
            )
            if existing_moscow_profile_ref
            else None
        )

        nodes = _collection(await api.request("GET", "/nodes"), "nodes")
        de_node = next(
            item for item in nodes if item.get("address") == args.de_node_address
        )
        moscow_node = next(
            item
            for item in nodes
            if item.get("address") == args.moscow_node_address
            or item.get("name") == MOSCOW_NODE_NAME
        )
        hosts = _collection(await api.request("GET", "/hosts"), "hosts")
        de_address_hosts = [
            item for item in hosts if item.get("address") == args.de_public_host
        ]
        de_hosts = [
            item
            for item in de_address_hosts
            if "DE Frankfurt" in str(item.get("remark"))
            and not _has_expected_auxiliary_tag(item, DE_INCY_AUXILIARY_TAGS)
        ]
        unexpected_de_hosts = [
            item
            for item in de_address_hosts
            if item not in de_hosts
            and not _has_expected_auxiliary_tag(item, DE_INCY_AUXILIARY_TAGS)
        ]
        if unexpected_de_hosts:
            raise RuntimeError(
                "Unexpected Frankfurt public host row has a non-Frankfurt remark"
            )
        moscow_address_hosts = [
            item for item in hosts if item.get("address") == args.moscow_public_host
        ]
        moscow_hosts = [
            item
            for item in moscow_address_hosts
            if "Moscow" in str(item.get("remark"))
            and not _has_expected_auxiliary_tag(item, MOSCOW_INCY_AUXILIARY_TAGS)
        ]
        unexpected_moscow_hosts = [
            item
            for item in moscow_address_hosts
            if item not in moscow_hosts
            and not _has_expected_auxiliary_tag(item, MOSCOW_INCY_AUXILIARY_TAGS)
        ]
        if unexpected_moscow_hosts:
            raise RuntimeError(
                "Unexpected Moscow public host row has a non-Moscow remark"
            )
        inbound_tag_by_uuid = {
            str(item.get("uuid")): str(item.get("tag") or "")
            for profile in (base_profile, existing_profile, existing_moscow_profile)
            if isinstance(profile, dict)
            for item in profile.get("inbounds", [])
            if isinstance(item, dict) and item.get("uuid")
        }
        _validate_frankfurt_host_shape(
            de_hosts,
            inbound_tag_by_uuid=inbound_tag_by_uuid,
        )
        _validate_moscow_host_shape(
            moscow_hosts,
            inbound_tag_by_uuid=inbound_tag_by_uuid,
        )
        _validate_no_public_bridge_hosts(
            hosts,
            base_profile,
            existing_profile,
            existing_moscow_profile,
        )

        squads = _collection(
            await api.request("GET", "/internal-squads"), "internalSquads"
        )
        smart_squad = next(
            item for item in squads if item.get("name") == args.smart_squad
        )
        external_squads = _collection(
            await api.request("GET", "/external-squads"), "externalSquads"
        )
        external_squad = next(
            item for item in external_squads if item.get("name") == args.external_squad
        )
        bridge_squad = next(
            (item for item in squads if item.get("name") == args.bridge_squad),
            None,
        )
        global_bridge_squad = next(
            (item for item in squads if item.get("name") == args.global_bridge_squad),
            None,
        )
        bridge_user = await _get_user(api, args.bridge_username)
        global_bridge_user = await _get_user(api, args.global_bridge_username)
        _validate_existing_bridge_user_isolation(
            bridge_user,
            bridge_squad,
            label="Frankfurt-to-Moscow bridge",
        )
        _validate_existing_bridge_user_isolation(
            global_bridge_user,
            global_bridge_squad,
            label="Moscow-to-Frankfurt bridge",
        )
        planned_base_config = _build_base_config(base_profile["config"])
        planned_config = _build_config(
            planned_base_config,
            bridge_user.get("ssPassword", "dry-run-placeholder")
            if bridge_user
            else "dry-run-placeholder",
            args.moscow_upstream_address,
            policy_artifact,
        )
        planned_moscow_config = _build_moscow_global_config(
            planned_base_config,
            global_bridge_user.get("ssPassword", "dry-run-placeholder")
            if global_bridge_user
            else "dry-run-placeholder",
            args.frankfurt_upstream_address,
            policy_artifact,
        )

        plan = {
            "mode": "apply" if args.apply else "dry-run",
            "bridgeUser": "reuse" if bridge_user else "create",
            "bridgeSquad": "update" if bridge_squad else "create",
            "reverseBridgeUser": "reuse" if global_bridge_user else "create",
            "reverseBridgeSquad": "update" if global_bridge_squad else "create",
            "baseProfile": "noop"
            if planned_base_config == base_profile["config"]
            else "update",
            "deProfile": "update" if existing_profile else "create",
            "moscowProfile": "update" if existing_moscow_profile else "create",
            "bridgeProtocol": "shadowsocks",
            "bridgePort": BRIDGE_PORT,
            "reverseBridgeInboundTag": GLOBAL_BRIDGE_INBOUND_TAG,
            "reverseBridgeOutboundTag": GLOBAL_BRIDGE_OUTBOUND_TAG,
            "reverseBridgeEndpointAddress": args.frankfurt_upstream_address,
            "reverseBridgeEndpointPort": BRIDGE_PORT,
            "reverseBridgePublicHost": "none",
            "incyRoutingHeader": "noop"
            if (external_squad.get("responseHeaders") or {}).get("routing")
            == legacy_routing_header
            else "update",
            "frankfurtHostCount": len(de_hosts),
            "moscowHostCount": len(moscow_hosts),
            "deProfileInboundCount": len(planned_config["inbounds"]),
            "moscowProfileInboundCount": len(planned_moscow_config["inbounds"]),
            "directDomainCount": _policy_domain_count(policy_artifact, "eu"),
            "ruDomainCount": _policy_domain_count(policy_artifact, "ru"),
            "routingRuleCount": len(planned_config["routing"]["rules"]),
            "moscowRoutingRuleCount": len(planned_moscow_config["routing"]["rules"]),
        }
        if not args.apply:
            return plan

        manifest = {
            "version": 3,
            "phase": "planned",
            "baseProfile": base_profile,
            "deProfile": existing_profile,
            "deProfileName": args.de_profile,
            "moscowProfile": existing_moscow_profile,
            "moscowProfileName": args.moscow_profile,
            "deNode": {
                "uuid": de_node["uuid"],
                "configProfile": _normalize_node_config_profile(
                    de_node.get("configProfile")
                ),
            },
            "moscowNode": {
                "uuid": moscow_node["uuid"],
                "configProfile": _normalize_node_config_profile(
                    moscow_node.get("configProfile")
                ),
            },
            "deHosts": [
                {"uuid": item["uuid"], "inbound": item.get("inbound")}
                for item in de_hosts
            ],
            "moscowHosts": [
                {"uuid": item["uuid"], "inbound": item.get("inbound")}
                for item in moscow_hosts
            ],
            "smartSquad": {
                "uuid": smart_squad["uuid"],
                "inbounds": _inbound_uuids(smart_squad),
            },
            "externalSquad": {
                "uuid": external_squad["uuid"],
                "responseHeaders": external_squad.get("responseHeaders") or {},
            },
            "bridgeSquad": (
                {
                    "uuid": bridge_squad["uuid"],
                    "inbounds": _inbound_uuids(bridge_squad),
                }
                if bridge_squad
                else None
            ),
            "bridgeSquadName": args.bridge_squad,
            "globalBridgeSquad": (
                {
                    "uuid": global_bridge_squad["uuid"],
                    "inbounds": _inbound_uuids(global_bridge_squad),
                }
                if global_bridge_squad
                else None
            ),
            "globalBridgeSquadName": args.global_bridge_squad,
            "bridgeUser": (
                {
                    "uuid": bridge_user["uuid"],
                    "activeInternalSquads": _squad_uuids(bridge_user),
                }
                if bridge_user
                else None
            ),
            "bridgeUsername": args.bridge_username,
            "globalBridgeUser": (
                {
                    "uuid": global_bridge_user["uuid"],
                    "activeInternalSquads": _squad_uuids(global_bridge_user),
                }
                if global_bridge_user
                else None
            ),
            "globalBridgeUsername": args.global_bridge_username,
        }
        _checkpoint(manifest_path, manifest, "planned")

        try:
            old_base_tags = {
                tag: inbound_uuid
                for tag, inbound_uuid in _profile_inbound_uuid_by_tag(
                    base_profile
                ).items()
                if tag in CUSTOMER_INBOUND_TAGS
            }
            await api.request(
                "PATCH",
                "/config-profiles",
                json={
                    "uuid": base_profile["uuid"],
                    "name": base_profile["name"],
                    "config": planned_base_config,
                },
            )
            _checkpoint(manifest_path, manifest, "base_profile_updated")
            base_profile = await api.request(
                "GET", f"/config-profiles/{base_profile['uuid']}"
            )
            base_tags = _profile_inbound_uuid_by_tag(base_profile)
            if any(
                base_tags.get(tag) != inbound_uuid
                for tag, inbound_uuid in old_base_tags.items()
            ):
                raise RuntimeError(
                    "Base public inbound UUIDs changed during bridge update"
                )
            _ordered_inbound_uuids(
                base_tags, CUSTOMER_INBOUND_TAGS + [BRIDGE_INBOUND_TAG]
            )

            if bridge_squad is None:
                bridge_squad = await api.request(
                    "POST",
                    "/internal-squads",
                    json={
                        "name": args.bridge_squad,
                        "inbounds": _isolated_squad_inbounds(
                            base_tags[BRIDGE_INBOUND_TAG]
                        ),
                    },
                )
            else:
                bridge_squad = await api.request(
                    "PATCH",
                    "/internal-squads",
                    json={
                        "uuid": bridge_squad["uuid"],
                        "inbounds": _isolated_squad_inbounds(
                            base_tags[BRIDGE_INBOUND_TAG]
                        ),
                    },
                )
            _checkpoint(manifest_path, manifest, "forward_bridge_squad_ready")

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
                        "description": "CyberVPN internal Frankfurt to Moscow Smart RU bridge",
                        "tag": "BRIDGE",
                        "activeInternalSquads": _isolated_user_squads(
                            bridge_squad["uuid"]
                        ),
                        "externalSquadUuid": None,
                    },
                )
            else:
                patched_bridge_user = await api.request(
                    "PATCH",
                    "/users",
                    json={
                        "uuid": bridge_user["uuid"],
                        "activeInternalSquads": _isolated_user_squads(
                            bridge_squad["uuid"]
                        ),
                    },
                )
                bridge_user = {**bridge_user, **patched_bridge_user}
            if not bridge_user.get("ssPassword"):
                raise RuntimeError("Bridge service user has no Shadowsocks credential")
            _checkpoint(manifest_path, manifest, "forward_bridge_user_ready")

            config = _build_config(
                base_profile["config"],
                bridge_user["ssPassword"],
                args.moscow_upstream_address,
                policy_artifact,
            )
            if existing_profile is None:
                de_profile = await api.request(
                    "POST",
                    "/config-profiles",
                    json={"name": args.de_profile, "config": config},
                )
            else:
                de_profile = await api.request(
                    "PATCH",
                    "/config-profiles",
                    json={
                        "uuid": existing_profile["uuid"],
                        "name": args.de_profile,
                        "config": config,
                    },
                )
            _checkpoint(manifest_path, manifest, "de_profile_updated")
            de_profile = await api.request(
                "GET", f"/config-profiles/{de_profile['uuid']}"
            )

            tag_to_clone = _profile_inbound_uuid_by_tag(de_profile)
            expected_de_tags = DE_CUSTOMER_INBOUND_TAGS + [GLOBAL_BRIDGE_INBOUND_TAG]
            if set(tag_to_clone) != set(expected_de_tags):
                raise RuntimeError(
                    "Frankfurt profile inbound tags do not match the expected contract"
                )
            de_customer_inbounds = _ordered_inbound_uuids(
                tag_to_clone, DE_CUSTOMER_INBOUND_TAGS
            )
            de_active_inbounds = de_customer_inbounds + [
                tag_to_clone[GLOBAL_BRIDGE_INBOUND_TAG]
            ]

            if global_bridge_squad is None:
                global_bridge_squad = await api.request(
                    "POST",
                    "/internal-squads",
                    json={
                        "name": args.global_bridge_squad,
                        "inbounds": _isolated_squad_inbounds(
                            tag_to_clone[GLOBAL_BRIDGE_INBOUND_TAG]
                        ),
                    },
                )
            else:
                global_bridge_squad = await api.request(
                    "PATCH",
                    "/internal-squads",
                    json={
                        "uuid": global_bridge_squad["uuid"],
                        "inbounds": _isolated_squad_inbounds(
                            tag_to_clone[GLOBAL_BRIDGE_INBOUND_TAG]
                        ),
                    },
                )
            _checkpoint(manifest_path, manifest, "reverse_bridge_squad_ready")

            if global_bridge_user is None:
                global_bridge_user = await api.request(
                    "POST",
                    "/users",
                    json={
                        "username": args.global_bridge_username,
                        "status": "ACTIVE",
                        "vlessUuid": str(uuid.uuid4()),
                        "trafficLimitBytes": 0,
                        "trafficLimitStrategy": "NO_RESET",
                        "expireAt": "2099-12-31T23:59:59.000Z",
                        "description": "CyberVPN internal Moscow to Frankfurt Smart Global bridge",
                        "tag": "BRIDGE",
                        "activeInternalSquads": _isolated_user_squads(
                            global_bridge_squad["uuid"]
                        ),
                        "externalSquadUuid": None,
                    },
                )
            else:
                patched_global_bridge_user = await api.request(
                    "PATCH",
                    "/users",
                    json={
                        "uuid": global_bridge_user["uuid"],
                        "activeInternalSquads": _isolated_user_squads(
                            global_bridge_squad["uuid"]
                        ),
                    },
                )
                global_bridge_user = {
                    **global_bridge_user,
                    **patched_global_bridge_user,
                }
            if not global_bridge_user.get("ssPassword"):
                raise RuntimeError(
                    "Reverse bridge service user has no Shadowsocks credential"
                )
            _checkpoint(manifest_path, manifest, "reverse_bridge_user_ready")

            moscow_config = _build_moscow_global_config(
                base_profile["config"],
                global_bridge_user["ssPassword"],
                args.frankfurt_upstream_address,
                policy_artifact,
            )
            if existing_moscow_profile is None:
                moscow_profile = await api.request(
                    "POST",
                    "/config-profiles",
                    json={"name": args.moscow_profile, "config": moscow_config},
                )
            else:
                moscow_profile = await api.request(
                    "PATCH",
                    "/config-profiles",
                    json={
                        "uuid": existing_moscow_profile["uuid"],
                        "name": args.moscow_profile,
                        "config": moscow_config,
                    },
                )
            _checkpoint(manifest_path, manifest, "moscow_profile_updated")
            moscow_profile = await api.request(
                "GET", f"/config-profiles/{moscow_profile['uuid']}"
            )
            moscow_tags = _profile_inbound_uuid_by_tag(moscow_profile)
            expected_moscow_tags = MOSCOW_CUSTOMER_INBOUND_TAGS + [
                MOSCOW_BRIDGE_INBOUND_TAG
            ]
            if set(moscow_tags) != set(expected_moscow_tags):
                raise RuntimeError(
                    "Moscow profile inbound tags do not match the expected contract"
                )
            moscow_customer_inbounds = _ordered_inbound_uuids(
                moscow_tags,
                MOSCOW_CUSTOMER_INBOUND_TAGS,
            )
            moscow_active_inbounds = moscow_customer_inbounds + [
                moscow_tags[MOSCOW_BRIDGE_INBOUND_TAG]
            ]
            _validate_no_public_bridge_hosts(
                hosts,
                base_profile,
                existing_profile,
                de_profile,
                existing_moscow_profile,
                moscow_profile,
            )

            bridge_squad = await api.request(
                "PATCH",
                "/internal-squads",
                json={
                    "uuid": bridge_squad["uuid"],
                    "inbounds": _isolated_squad_inbounds(
                        moscow_tags[MOSCOW_BRIDGE_INBOUND_TAG]
                    ),
                },
            )
            global_bridge_squad = await api.request(
                "PATCH",
                "/internal-squads",
                json={
                    "uuid": global_bridge_squad["uuid"],
                    "inbounds": _isolated_squad_inbounds(
                        tag_to_clone[GLOBAL_BRIDGE_INBOUND_TAG]
                    ),
                },
            )
            _checkpoint(manifest_path, manifest, "bridge_squads_isolated")

            bridge_user = await api.request(
                "PATCH",
                "/users",
                json={
                    "uuid": bridge_user["uuid"],
                    "activeInternalSquads": _isolated_user_squads(bridge_squad["uuid"]),
                },
            )
            global_bridge_user = await api.request(
                "PATCH",
                "/users",
                json={
                    "uuid": global_bridge_user["uuid"],
                    "activeInternalSquads": _isolated_user_squads(
                        global_bridge_squad["uuid"]
                    ),
                },
            )
            _checkpoint(manifest_path, manifest, "bridge_users_isolated")

            bridge_inbound_uuids = _bridge_inbound_uuids_from_profiles(
                base_profile,
                existing_profile,
                de_profile,
                existing_moscow_profile,
                moscow_profile,
            )
            desired_squad_inbounds = _desired_customer_squad_inbounds(
                _inbound_uuids(smart_squad),
                moscow_customer_inbounds + de_customer_inbounds,
                bridge_inbound_uuids,
            )
            await api.request(
                "PATCH",
                "/internal-squads",
                json={
                    "uuid": smart_squad["uuid"],
                    "inbounds": desired_squad_inbounds,
                },
            )
            desired_response_headers = {
                **(external_squad.get("responseHeaders") or {}),
                "routing": legacy_routing_header,
            }
            await api.request(
                "PATCH",
                "/external-squads",
                json={
                    "uuid": external_squad["uuid"],
                    "responseHeaders": desired_response_headers,
                },
            )
            _checkpoint(manifest_path, manifest, "squads_and_headers_updated")

            uuid_to_tag = {
                inbound_uuid: tag
                for profile in (
                    manifest["baseProfile"],
                    base_profile,
                    existing_profile,
                    de_profile,
                )
                if isinstance(profile, dict)
                for tag, inbound_uuid in _profile_inbound_uuid_by_tag(profile).items()
            }
            for host in de_hosts:
                current_uuid = host["inbound"]["configProfileInboundUuid"]
                current_tag = uuid_to_tag[current_uuid]
                new_tag = OLD_TO_NEW_TAG.get(current_tag, current_tag)
                if new_tag not in DE_CUSTOMER_INBOUND_TAGS:
                    raise RuntimeError(
                        "Frankfurt public host must remain attached to a customer inbound"
                    )
                await api.request(
                    "PATCH",
                    "/hosts",
                    json={
                        "uuid": host["uuid"],
                        "inbound": {
                            "configProfileUuid": de_profile["uuid"],
                            "configProfileInboundUuid": tag_to_clone[new_tag],
                        },
                    },
                )
            _checkpoint(manifest_path, manifest, "frankfurt_hosts_updated")

            moscow_uuid_to_tag = {
                inbound_uuid: tag
                for profile in (
                    manifest["baseProfile"],
                    base_profile,
                    existing_moscow_profile,
                    moscow_profile,
                )
                if isinstance(profile, dict)
                for tag, inbound_uuid in _profile_inbound_uuid_by_tag(profile).items()
            }
            for host in moscow_hosts:
                current_uuid = host["inbound"]["configProfileInboundUuid"]
                current_tag = moscow_uuid_to_tag[current_uuid]
                target_tag = MOSCOW_OLD_TO_NEW_TAG.get(current_tag, current_tag)
                if target_tag not in MOSCOW_CUSTOMER_INBOUND_TAGS:
                    raise RuntimeError(
                        "Moscow public host must remain attached to a customer inbound"
                    )
                await api.request(
                    "PATCH",
                    "/hosts",
                    json={
                        "uuid": host["uuid"],
                        "inbound": {
                            "configProfileUuid": moscow_profile["uuid"],
                            "configProfileInboundUuid": moscow_tags[target_tag],
                        },
                    },
                )
            _checkpoint(manifest_path, manifest, "moscow_hosts_updated")

            await api.request(
                "PATCH",
                "/nodes",
                json={
                    "uuid": moscow_node["uuid"],
                    "configProfile": {
                        "activeConfigProfileUuid": moscow_profile["uuid"],
                        "activeInbounds": moscow_active_inbounds,
                    },
                },
            )
            _checkpoint(manifest_path, manifest, "moscow_node_updated")

            await api.request(
                "PATCH",
                "/nodes",
                json={
                    "uuid": de_node["uuid"],
                    "configProfile": {
                        "activeConfigProfileUuid": de_profile["uuid"],
                        "activeInbounds": de_active_inbounds,
                    },
                },
            )
            _checkpoint(manifest_path, manifest, "customer_paths_updated")
            for node in (de_node, moscow_node):
                await api.request(
                    "POST",
                    f"/nodes/{node['uuid']}/actions/restart",
                    json={"forceRestart": True},
                )
            _checkpoint(manifest_path, manifest, "nodes_restarted")
            _checkpoint(manifest_path, manifest, "applied")
            return {
                **plan,
                "profileInboundCount": len(tag_to_clone),
                "moscowProfileInboundCountApplied": len(moscow_tags),
                "smartSquadInboundCount": len(desired_squad_inbounds),
                "bridgeSquadInboundCount": 1,
                "reverseBridgeSquadInboundCount": 1,
                "bridgeUserIsolated": True,
                "reverseBridgeUserIsolated": True,
                "incyRoutingHeaderApplied": True,
                "frankfurtNodeSwitched": True,
                "frankfurtNodeActiveInboundCount": len(de_active_inbounds),
                "moscowNodeActiveInboundCount": len(moscow_active_inbounds),
                "moscowSmartGlobalActivated": True,
                "nodesRestarted": True,
            }
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
                    "Smart RU apply and automatic rollback failed"
                ) from None
            raise RuntimeError(
                "Smart RU apply failed and was rolled back"
            ) from apply_error
    finally:
        await api.close()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes; otherwise perform a read-only dry-run",
    )
    mode.add_argument(
        "--rollback",
        action="store_true",
        help="Restore the state recorded in --rollback-manifest",
    )
    parser.add_argument(
        "--remnawave-url",
        default=os.environ.get("REMNAWAVE_URL", "http://remnawave:3000"),
    )
    parser.add_argument("--base-profile", default=BASE_PROFILE_NAME)
    parser.add_argument("--de-profile", default=DE_PROFILE_NAME)
    parser.add_argument("--moscow-profile", default=MOSCOW_PROFILE_NAME)
    parser.add_argument("--de-node-address", default=DE_NODE_ADDRESS)
    parser.add_argument("--de-public-host", default=DE_PUBLIC_HOST)
    parser.add_argument("--moscow-public-host", default=MOSCOW_PUBLIC_HOST)
    parser.add_argument("--moscow-node-address", default=MOSCOW_NODE_ADDRESS)
    parser.add_argument("--smart-squad", default=SMART_SQUAD_NAME)
    parser.add_argument("--external-squad", default=EXTERNAL_SQUAD_NAME)
    parser.add_argument("--bridge-squad", default=BRIDGE_SQUAD_NAME)
    parser.add_argument("--bridge-username", default=BRIDGE_USERNAME)
    parser.add_argument("--global-bridge-squad", default=GLOBAL_BRIDGE_SQUAD_NAME)
    parser.add_argument("--global-bridge-username", default=GLOBAL_BRIDGE_USERNAME)
    parser.add_argument("--moscow-upstream-address", default=MOSCOW_UPSTREAM_ADDRESS)
    parser.add_argument(
        "--frankfurt-upstream-address", default=FRANKFURT_UPSTREAM_ADDRESS
    )
    parser.add_argument(
        "--allow-remnawave-host",
        action="append",
        default=["remnawave", "localhost", "127.0.0.1", "::1"],
        help="Allow an additional exact Remnawave API hostname",
    )
    parser.add_argument(
        "--trusted-proxy-headers",
        action="store_true",
        help="Send required proxy headers only to an allowlisted internal API host",
    )
    parser.add_argument(
        "--rollback-manifest",
        type=Path,
        default=Path(
            "/var/lib/cybervpn/remnawave/premium-smart-ru-routing-rollback.json"
        ),
    )
    return parser.parse_args()


def main() -> int:
    try:
        result = asyncio.run(_run(_parse_args()))
    except Exception as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        print(
            json.dumps(
                {
                    "status": "failed",
                    "errorClass": type(exc).__name__,
                    "httpStatus": status,
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
