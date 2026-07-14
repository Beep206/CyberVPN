from __future__ import annotations

import re
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

ALIAS_PAIRS = (
    ("activePluginUuid", "active_plugin_uuid"),
    ("pluginConfig", "plugin_config"),
    ("blockDuration", "block_duration"),
    ("ignoreLists", "ignore_lists"),
    ("userId", "user_id"),
)
MINIMUM_NODE_VERSION = (2, 7, 0)
MINIMUM_XRAY_VERSION = (26, 3, 27)
MINIMUM_KERNEL_VERSION = (5, 7, 0)
VERSION_PREFIX = re.compile(r"^v?(\d+)\.(\d+)(?:\.(\d+))?")


def _ensure_no_conflicting_aliases(value: Any, *, owner: str) -> None:
    if isinstance(value, dict):
        for primary_key, alternate_key in ALIAS_PAIRS:
            if (
                primary_key in value
                and alternate_key in value
                and value[primary_key] != value[alternate_key]
            ):
                raise RuntimeError(
                    f"{owner} has conflicting {primary_key}/{alternate_key} fields"
                )
        for item in value.values():
            _ensure_no_conflicting_aliases(item, owner=owner)
        return
    if isinstance(value, list):
        for item in value:
            _ensure_no_conflicting_aliases(item, owner=owner)


def _required_current_api_string(
    item: dict[str, Any],
    key: str,
    *,
    owner: str,
) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value or value != value.strip():
        raise RuntimeError(f"{owner} is missing valid {key}")
    return value


def _expected_address_set(expected_node_addresses: set[str]) -> set[str]:
    if not expected_node_addresses:
        raise RuntimeError("Expected node address set is required")
    normalized: set[str] = set()
    for address in expected_node_addresses:
        if not isinstance(address, str) or not address or address != address.strip():
            raise RuntimeError("Expected node address set contains an invalid address")
        normalized.add(address)
    if normalized != expected_node_addresses:
        raise RuntimeError(
            "Expected node address set contains duplicate/invalid values"
        )
    return normalized


def _nodes_by_expected_address(
    nodes: list[dict[str, Any]],
    *,
    expected_addresses: set[str],
) -> dict[str, dict[str, Any]]:
    nodes_by_address: dict[str, dict[str, Any]] = {}
    for node in nodes:
        if not isinstance(node, dict):
            raise RuntimeError("Node collection contains a non-object item")
        _ensure_no_conflicting_aliases(node, owner="Node response")
        address = node.get("address")
        if not isinstance(address, str) or address not in expected_addresses:
            continue
        if address in nodes_by_address:
            raise RuntimeError(
                f"Expected Remnawave node address {address} is ambiguous"
            )
        nodes_by_address[address] = node

    found_addresses = set(nodes_by_address)
    if found_addresses != expected_addresses:
        missing = sorted(expected_addresses - found_addresses)
        extra = sorted(found_addresses - expected_addresses)
        details = []
        if missing:
            details.append("missing: " + ", ".join(missing))
        if extra:
            details.append("extra: " + ", ".join(extra))
        raise RuntimeError(
            "Remnawave node address preflight did not match expected set"
            + (f" ({'; '.join(details)})" if details else "")
        )
    return nodes_by_address


def _find_expected_plugin(
    plugins: list[dict[str, Any]],
    *,
    expected_plugin_name: str,
) -> dict[str, Any]:
    matches: list[dict[str, Any]] = []
    for plugin in plugins:
        if not isinstance(plugin, dict):
            raise RuntimeError("Node plugin collection contains a non-object item")
        _ensure_no_conflicting_aliases(plugin, owner="Node plugin response")
        name = _required_current_api_string(
            plugin,
            "name",
            owner="Node plugin response",
        )
        if name == expected_plugin_name:
            matches.append(plugin)
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected exactly one {expected_plugin_name} node plugin, "
            f"found {len(matches)}"
        )
    return matches[0]


async def load_expected_node_plugin(
    request: Callable[[str, str], Awaitable[Any]],
    plugins: list[dict[str, Any]],
    *,
    expected_plugin_name: str,
) -> dict[str, Any]:
    """Load the full plugin when Remnawave's list response omits pluginConfig."""
    plugin = _find_expected_plugin(
        plugins,
        expected_plugin_name=expected_plugin_name,
    )
    if isinstance(plugin.get("pluginConfig"), dict):
        return plugin

    plugin_uuid = _required_current_api_string(
        plugin,
        "uuid",
        owner=f"Node plugin {expected_plugin_name}",
    )
    try:
        parsed_plugin_uuid = uuid.UUID(plugin_uuid)
    except ValueError as exc:
        raise RuntimeError(
            f"Node plugin {expected_plugin_name} has an invalid uuid"
        ) from exc

    canonical_uuid = str(parsed_plugin_uuid)
    detail = await request("GET", f"/node-plugins/{canonical_uuid}")
    if not isinstance(detail, dict):
        raise RuntimeError(
            f"Node plugin {expected_plugin_name} detail response must be an object"
        )
    _ensure_no_conflicting_aliases(detail, owner="Node plugin detail response")
    detail_name = _required_current_api_string(
        detail,
        "name",
        owner="Node plugin detail response",
    )
    detail_uuid = _required_current_api_string(
        detail,
        "uuid",
        owner="Node plugin detail response",
    )
    try:
        parsed_detail_uuid = uuid.UUID(detail_uuid)
    except ValueError as exc:
        raise RuntimeError("Node plugin detail response has an invalid uuid") from exc
    if detail_name != expected_plugin_name or parsed_detail_uuid != parsed_plugin_uuid:
        raise RuntimeError(
            f"Node plugin {expected_plugin_name} detail response does not match "
            "the selected plugin"
        )
    return detail


def _validate_torrent_blocker_config(
    plugin: dict[str, Any],
    *,
    expected_plugin_name: str,
    block_duration: int,
) -> None:
    plugin_config = plugin.get("pluginConfig")
    if not isinstance(plugin_config, dict):
        raise RuntimeError(
            f"Node plugin {expected_plugin_name} is missing pluginConfig"
        )
    torrent_blocker = plugin_config.get("torrentBlocker")
    if not isinstance(torrent_blocker, dict):
        raise RuntimeError(
            f"Node plugin {expected_plugin_name} is missing torrentBlocker"
        )
    expected_torrent_blocker = {
        "enabled": True,
        "ignoreLists": {"ip": [], "userId": []},
        "blockDuration": block_duration,
    }
    if torrent_blocker != expected_torrent_blocker:
        raise RuntimeError(
            f"Node plugin {expected_plugin_name} torrentBlocker does not match "
            "the expected fail-closed contract"
        )


def _version_tuple(value: Any, *, owner: str) -> tuple[int, int, int]:
    if not isinstance(value, str) or not value or value != value.strip():
        raise RuntimeError(f"{owner} is missing a valid version")
    match = VERSION_PREFIX.match(value)
    if match is None:
        raise RuntimeError(f"{owner} has an unsupported version format")
    major, minor, patch = match.groups()
    return int(major), int(minor), int(patch or 0)


def _validate_node_runtime(node: dict[str, Any], *, address: str) -> None:
    owner = f"Expected Remnawave node address {address}"
    if node.get("isConnected") is not True:
        raise RuntimeError(f"{owner} must be connected")
    if node.get("isDisabled") is not False:
        raise RuntimeError(f"{owner} must not be disabled")
    if node.get("isConnecting") is not False:
        raise RuntimeError(f"{owner} must not be connecting")

    versions = node.get("versions")
    if not isinstance(versions, dict):
        raise RuntimeError(f"{owner} is missing runtime versions")
    node_version = _version_tuple(
        versions.get("node"),
        owner=f"{owner} Remnawave Node",
    )
    xray_version = _version_tuple(
        versions.get("xray"),
        owner=f"{owner} Xray Core",
    )
    if node_version < MINIMUM_NODE_VERSION:
        raise RuntimeError(f"{owner} Remnawave Node version is too old")
    if xray_version < MINIMUM_XRAY_VERSION:
        raise RuntimeError(f"{owner} Xray Core version is too old")

    system = node.get("system")
    info = system.get("info") if isinstance(system, dict) else None
    if not isinstance(info, dict):
        raise RuntimeError(f"{owner} is missing runtime system information")
    if str(info.get("platform") or "").casefold() != "linux":
        raise RuntimeError(f"{owner} must run Linux")
    kernel_version = _version_tuple(
        info.get("release"),
        owner=f"{owner} Linux kernel",
    )
    if kernel_version < MINIMUM_KERNEL_VERSION:
        raise RuntimeError(f"{owner} Linux kernel version is too old")


def validate_torrent_blocker_preflight(
    nodes: list[dict[str, Any]],
    plugins: list[dict[str, Any]],
    *,
    expected_node_addresses: set[str],
    expected_plugin_name: str,
    block_duration: int = 86400,
) -> dict[str, Any]:
    if not isinstance(nodes, list):
        raise RuntimeError("Node collection must be a list")
    if not isinstance(plugins, list):
        raise RuntimeError("Node plugin collection must be a list")
    if not isinstance(expected_plugin_name, str) or not expected_plugin_name:
        raise RuntimeError("Expected plugin name is required")
    if not isinstance(block_duration, int) or isinstance(block_duration, bool):
        raise RuntimeError("Torrent blocker block duration must be an integer")

    expected_addresses = _expected_address_set(expected_node_addresses)
    nodes_by_address = _nodes_by_expected_address(
        nodes,
        expected_addresses=expected_addresses,
    )
    expected_plugin = _find_expected_plugin(
        plugins,
        expected_plugin_name=expected_plugin_name,
    )
    expected_plugin_uuid = _required_current_api_string(
        expected_plugin,
        "uuid",
        owner=f"Node plugin {expected_plugin_name}",
    )
    _validate_torrent_blocker_config(
        expected_plugin,
        expected_plugin_name=expected_plugin_name,
        block_duration=block_duration,
    )

    for address, node in nodes_by_address.items():
        _validate_node_runtime(node, address=address)
        active_plugin_uuid = _required_current_api_string(
            node,
            "activePluginUuid",
            owner=f"Expected Remnawave node address {address}",
        )
        if active_plugin_uuid != expected_plugin_uuid:
            raise RuntimeError(
                f"Expected Remnawave node address {address} must have active plugin "
                f"{expected_plugin_name}"
            )

    return {
        "pluginName": expected_plugin_name,
        "nodeCount": len(nodes_by_address),
        "blockDuration": block_duration,
    }
