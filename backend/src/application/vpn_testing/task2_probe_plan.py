"""Build bounded Task2 route probes from the promoted Antifilter snapshot."""

from __future__ import annotations

import hashlib
import ipaddress
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.application.services.vpn_product_readiness import (
    TASK2_READINESS_STATE_INVALID_REASON,
    VpnProductReadinessError,
    load_spb_de_exceptions_promoted_manifest_snapshot,
)

TASK2_ANTIFILTER_CATEGORIES = (
    "rkn",
    "meta",
    "twitter_x",
    "netflix",
    "cloudfront",
    "microsoft",
    "amazon",
    "openai",
    "youtube",
    "google",
    "telegram",
    "discord",
    "custom_networks",
)
TASK2_ARTIFACT_CATEGORY_NAMES = {"cloudfront": "amazon_cloudfront"}
TASK2_UNMATCHED_PROBE_IPV4 = ipaddress.IPv4Address("1.1.1.1")
MAX_ROUTE_ARTIFACT_BYTES = 8 * 1024 * 1024
MAX_ROUTE_PREFIXES = 500_000


class Task2RouteProbeSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    route_key: str = Field(..., min_length=1, max_length=160)
    traffic_class: Literal["matched_exception", "unmatched_default"]
    category: str | None = Field(default=None, max_length=80)
    transport: Literal["raw", "xhttp"]
    probe_network: Literal["tcp", "udp"]
    target_ip: str
    target_port: int = Field(..., ge=1, le=65535)
    membership: Literal["member", "non_member"]
    expected_outbound: Literal["DE_EXCEPTIONS_BRIDGE", "DIRECT"]
    manifest_sha256: str = Field(..., pattern=r"^[0-9a-f]{64}$")
    route_feed_version: str = Field(..., min_length=1, max_length=128)

    @field_validator("target_ip")
    @classmethod
    def validate_public_ipv4(cls, value: str) -> str:
        address = ipaddress.ip_address(value)
        if not isinstance(address, ipaddress.IPv4Address) or _unsafe_probe_address(address):
            raise ValueError("task2_probe_target_must_be_public_ipv4")
        return str(address)


def _invalid(message: str) -> VpnProductReadinessError:
    return VpnProductReadinessError(TASK2_READINESS_STATE_INVALID_REASON, message)


def _unsafe_probe_address(address: ipaddress.IPv4Address) -> bool:
    return any(
        (
            not address.is_global,
            address.is_private,
            address.is_loopback,
            address.is_link_local,
            address.is_multicast,
            address.is_unspecified,
            address.is_reserved,
        )
    )


def _read_verified_artifact(
    version_dir: Path,
    manifest: Mapping[str, Any],
    relative_path: str,
) -> bytes:
    artifacts = manifest.get("artifacts")
    expected_sha256 = artifacts.get(relative_path) if isinstance(artifacts, Mapping) else None
    if not isinstance(expected_sha256, str) or len(expected_sha256) != 64:
        raise _invalid("Premium SPB/DE promoted manifest omits a required route artifact")
    path = version_dir / relative_path
    try:
        if path.is_symlink():
            raise _invalid("Premium SPB/DE route artifact path is not trusted")
        resolved = path.resolve(strict=True)
        resolved.relative_to(version_dir.resolve(strict=True))
        size = resolved.stat().st_size
        if size <= 0 or size > MAX_ROUTE_ARTIFACT_BYTES:
            raise _invalid("Premium SPB/DE route artifact size is invalid")
        raw = resolved.read_bytes()
    except VpnProductReadinessError:
        raise
    except (FileNotFoundError, OSError, ValueError) as exc:
        raise _invalid("Premium SPB/DE route artifact cannot be loaded safely") from exc
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise _invalid("Premium SPB/DE route artifact checksum is invalid")
    return raw


def _parse_ipv4_networks(raw: bytes) -> list[ipaddress.IPv4Network]:
    try:
        lines = raw.decode("ascii").splitlines()
    except UnicodeDecodeError as exc:
        raise _invalid("Premium SPB/DE route artifact is not ASCII") from exc
    if not lines or len(lines) > MAX_ROUTE_PREFIXES:
        raise _invalid("Premium SPB/DE route artifact prefix count is invalid")
    networks: list[ipaddress.IPv4Network] = []
    for line in lines:
        if not line or line != line.strip():
            raise _invalid("Premium SPB/DE route artifact contains a non-canonical prefix")
        try:
            network = ipaddress.ip_network(line, strict=True)
        except ValueError as exc:
            raise _invalid("Premium SPB/DE route artifact contains an invalid prefix") from exc
        if not isinstance(network, ipaddress.IPv4Network) or network.prefixlen == 0:
            raise _invalid("Premium SPB/DE route artifact contains an unsupported prefix")
        networks.append(network)
    return networks


def _first_safe_address(networks: Sequence[ipaddress.IPv4Network]) -> ipaddress.IPv4Address:
    for network in networks:
        first = int(network.network_address)
        last = int(network.broadcast_address)
        offsets = (0,) if network.num_addresses == 1 else (1, 0, 2, 3)
        for offset in offsets:
            candidate = ipaddress.IPv4Address(first + offset)
            if int(candidate) <= last and not _unsafe_probe_address(candidate):
                return candidate
    raise _invalid("Premium SPB/DE route artifact has no safe probe address")


def _route_metadata(route: Any) -> Mapping[str, Any]:
    metadata = getattr(route, "metadata_json", None)
    return metadata if isinstance(metadata, Mapping) else {}


def _find_route(
    route_entries: Sequence[Any],
    *,
    traffic_class: str,
    transport: str | None = None,
    probe_network: str,
    category: str | None = None,
) -> Any:
    matches = []
    for route in route_entries:
        metadata = _route_metadata(route)
        if metadata.get("traffic_class") != traffic_class:
            continue
        if metadata.get("probe_network") != probe_network:
            continue
        if transport is not None and metadata.get("transport") != transport:
            continue
        if category is not None and metadata.get("category") != category:
            continue
        if category is not None and metadata.get("transport") is not None:
            continue
        matches.append(route)
    if len(matches) != 1:
        raise _invalid("Task2 route registry does not resolve one deterministic probe")
    return matches[0]


def _spec(
    route: Any,
    *,
    category: str | None,
    transport: Literal["raw", "xhttp"],
    probe_network: Literal["tcp", "udp"],
    target_ip: ipaddress.IPv4Address,
    target_port: int,
    manifest_sha256: str,
    route_feed_version: str,
) -> Task2RouteProbeSpec:
    metadata = _route_metadata(route)
    traffic_class = str(metadata.get("traffic_class") or "")
    expected_outbound = str(metadata.get("expected_outbound") or "")
    membership = str(metadata.get("membership") or "")
    normalized_membership = {
        "must_be_in_compiled_union": "member",
        "must_not_be_in_compiled_union": "non_member",
    }.get(membership)
    return Task2RouteProbeSpec.model_validate(
        {
            "route_key": str(getattr(route, "route_key", "")),
            "traffic_class": traffic_class,
            "category": category,
            "transport": transport,
            "probe_network": probe_network,
            "target_ip": str(target_ip),
            "target_port": target_port,
            "membership": normalized_membership,
            "expected_outbound": expected_outbound,
            "manifest_sha256": manifest_sha256,
            "route_feed_version": route_feed_version,
        }
    )


def build_task2_route_probe_specs(route_entries: Sequence[Any]) -> list[Task2RouteProbeSpec]:
    """Build the complete synthetic selected-outbound declaration from active/LKG state."""

    pointer, manifest, version_dir = load_spb_de_exceptions_promoted_manifest_snapshot()
    if manifest.get("product") != "premium_spb_de_exceptions" or manifest.get("version") != pointer.version:
        raise _invalid("Premium SPB/DE promoted manifest identity is invalid")

    union_networks = _parse_ipv4_networks(_read_verified_artifact(version_dir, manifest, "union/ipv4.cidr"))
    if any(TASK2_UNMATCHED_PROBE_IPV4 in network for network in union_networks):
        raise _invalid("Task2 unmatched control address is present in the promoted union")

    category_targets: dict[str, ipaddress.IPv4Address] = {}
    for category in TASK2_ANTIFILTER_CATEGORIES:
        artifact_category = TASK2_ARTIFACT_CATEGORY_NAMES.get(category, category)
        networks = _parse_ipv4_networks(
            _read_verified_artifact(version_dir, manifest, f"categories/{artifact_category}.ipv4.cidr")
        )
        target = _first_safe_address(networks)
        if not any(target in network for network in union_networks):
            raise _invalid("Task2 category probe address is absent from the promoted union")
        category_targets[category] = target

    specs: list[Task2RouteProbeSpec] = []
    for category_index, category in enumerate(TASK2_ANTIFILTER_CATEGORIES):
        route = _find_route(
            route_entries,
            traffic_class="matched_exception",
            probe_network="tcp",
            category=category,
        )
        specs.append(
            _spec(
                route,
                category=category,
                transport="raw",
                probe_network="tcp",
                target_ip=category_targets[category],
                # The same IP can legitimately occur in multiple Antifilter
                # categories. A per-category port keeps webhook correlation
                # unique without changing the IP-only Xray routing decision.
                target_port=31000 + category_index,
                manifest_sha256=pointer.manifest_sha256,
                route_feed_version=pointer.version,
            )
        )

    matched_ports = {
        ("raw", "tcp"): 24443,
        ("xhttp", "tcp"): 24444,
        ("raw", "udp"): 25353,
        ("xhttp", "udp"): 25354,
    }
    custom_target = category_targets["custom_networks"]
    transports: tuple[Literal["raw", "xhttp"], ...] = ("raw", "xhttp")
    probe_networks: tuple[Literal["tcp", "udp"], ...] = ("tcp", "udp")
    for transport in transports:
        for probe_network in probe_networks:
            route = _find_route(
                route_entries,
                traffic_class="matched_exception",
                transport=transport,
                probe_network=probe_network,
            )
            specs.append(
                _spec(
                    route,
                    category="custom_networks",
                    transport=transport,
                    probe_network=probe_network,
                    target_ip=custom_target,
                    target_port=matched_ports[(transport, probe_network)],
                    manifest_sha256=pointer.manifest_sha256,
                    route_feed_version=pointer.version,
                )
            )

    default_ports = {
        ("raw", "tcp"): 443,
        ("xhttp", "tcp"): 8443,
        ("raw", "udp"): 53,
        ("xhttp", "udp"): 5353,
    }
    for transport in transports:
        for probe_network in probe_networks:
            route = _find_route(
                route_entries,
                traffic_class="unmatched_default",
                transport=transport,
                probe_network=probe_network,
            )
            specs.append(
                _spec(
                    route,
                    category=None,
                    transport=transport,
                    probe_network=probe_network,
                    target_ip=TASK2_UNMATCHED_PROBE_IPV4,
                    target_port=default_ports[(transport, probe_network)],
                    manifest_sha256=pointer.manifest_sha256,
                    route_feed_version=pointer.version,
                )
            )

    route_keys = [spec.route_key for spec in specs]
    correlation_targets = {(spec.probe_network, spec.target_ip, spec.target_port) for spec in specs}
    if len(specs) != 21 or len(route_keys) != len(set(route_keys)) or len(correlation_targets) != len(specs):
        raise _invalid("Task2 selected-outbound probe matrix is incomplete or ambiguous")
    return specs
