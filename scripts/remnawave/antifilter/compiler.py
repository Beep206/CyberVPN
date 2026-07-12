from __future__ import annotations

import ipaddress
import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from .importer import Network, load_source, read_route_files
from .models import (
    CATEGORY_COMMUNITIES,
    DEFAULT_FORBIDDEN_NETWORKS,
    PRODUCT,
    CompilePolicy,
    SafetyGateError,
    SourceValidationError,
    canonical_json_bytes,
    format_utc_timestamp,
    reject_non_finite_json,
    sha256_bytes,
)


def _network_key(network: Network) -> tuple[int, int, int]:
    return network.version, int(network.network_address), network.prefixlen


def _collapse(networks: Iterable[Network]) -> list[Network]:
    materialized = list(networks)
    ipv4 = [network for network in materialized if network.version == 4]
    ipv6 = [network for network in materialized if network.version == 6]
    return sorted(
        [*ipaddress.collapse_addresses(ipv4), *ipaddress.collapse_addresses(ipv6)],
        key=_network_key,
    )


def _subnet_of(contained: Network, container: Network) -> bool:
    if isinstance(contained, ipaddress.IPv4Network) and isinstance(
        container, ipaddress.IPv4Network
    ):
        return contained.subnet_of(container)
    if isinstance(contained, ipaddress.IPv6Network) and isinstance(
        container, ipaddress.IPv6Network
    ):
        return contained.subnet_of(container)
    return False


def _address_exclude(container: Network, excluded: Network) -> list[Network]:
    if isinstance(container, ipaddress.IPv4Network) and isinstance(
        excluded, ipaddress.IPv4Network
    ):
        return list(container.address_exclude(excluded))
    if isinstance(container, ipaddress.IPv6Network) and isinstance(
        excluded, ipaddress.IPv6Network
    ):
        return list(container.address_exclude(excluded))
    raise AssertionError("address exclusion requires matching families")


def _subtract_networks(
    networks: Iterable[Network], exclusions: Iterable[Network]
) -> tuple[list[Network], int, int]:
    remaining = _collapse(networks)
    removed_addresses = 0
    matched_prefixes = 0
    for exclusion in sorted(exclusions, key=_network_key):
        next_remaining: list[Network] = []
        for network in remaining:
            if network.version != exclusion.version or not network.overlaps(exclusion):
                next_remaining.append(network)
                continue
            matched_prefixes += 1
            if _subnet_of(network, exclusion):
                removed_addresses += network.num_addresses
                continue
            if _subnet_of(exclusion, network):
                removed_addresses += exclusion.num_addresses
                next_remaining.extend(_address_exclude(network, exclusion))
                continue
            raise AssertionError("CIDR overlap must imply containment")
        remaining = _collapse(next_remaining)
    return remaining, matched_prefixes, removed_addresses


def _network_difference(
    left: Iterable[Network], right: Iterable[Network]
) -> list[Network]:
    result = _collapse(left)
    for excluded in _collapse(right):
        result, _, _ = _subtract_networks(result, [excluded])
    return _collapse(result)


def _cidr_bytes(networks: Iterable[Network]) -> bytes:
    values = [str(network) for network in sorted(networks, key=_network_key)]
    return (("\n".join(values) + "\n") if values else "").encode("ascii")


def _load_previous(
    previous_dir: Path | None,
    policy: CompilePolicy,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, str | None]:
    if previous_dir is None:
        return None, None, None
    manifest_path = previous_dir / "manifest.json"
    canonical_path = previous_dir / "canonical.json"
    try:
        if (
            previous_dir.is_symlink()
            or manifest_path.is_symlink()
            or canonical_path.is_symlink()
        ):
            raise SourceValidationError("previous artifact paths must not be symlinks")
        with manifest_path.open("rb") as handle:
            manifest_raw = handle.read(4 * 1024 * 1024 + 1)
        with canonical_path.open("rb") as handle:
            canonical_raw_input = handle.read(256 * 1024 * 1024 + 1)
        if (
            len(manifest_raw) > 4 * 1024 * 1024
            or len(canonical_raw_input) > 256 * 1024 * 1024
        ):
            raise SourceValidationError(
                "previous compiled artifact exceeds resource limits"
            )
        manifest = json.loads(
            manifest_raw.decode("utf-8"), parse_constant=reject_non_finite_json
        )
        canonical = json.loads(
            canonical_raw_input.decode("utf-8"), parse_constant=reject_non_finite_json
        )
    except SourceValidationError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise SourceValidationError(
            f"cannot load previous compiled artifact: {exc}"
        ) from exc
    if not isinstance(manifest, dict) or not isinstance(canonical, dict):
        raise SourceValidationError(
            "previous manifest and canonical artifact must be JSON objects"
        )
    if manifest.get("schemaVersion") != 1 or canonical.get("schemaVersion") != 1:
        raise SourceValidationError("unsupported previous artifact schemaVersion")
    policy_sha256 = sha256_bytes(policy.canonical_bytes)
    if (
        manifest.get("product") != PRODUCT
        or canonical.get("product") != PRODUCT
        or manifest.get("policySha256") != policy_sha256
    ):
        raise SourceValidationError("previous artifact product or policy mismatch")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict):
        raise SourceValidationError("previous manifest artifacts must be an object")
    expected = artifacts.get("canonical.json")
    canonical_raw = canonical_json_bytes(canonical)
    if expected != sha256_bytes(canonical_raw):
        raise SourceValidationError("previous canonical artifact checksum mismatch")
    source = manifest.get("source")
    prior = manifest.get("previousManifestSha256")
    if (
        not isinstance(source, dict)
        or not isinstance(source.get("manifestSha256"), str)
        or len(source["manifestSha256"]) != 64
        or (prior is not None and (not isinstance(prior, str) or len(prior) != 64))
    ):
        raise SourceValidationError("previous artifact provenance is invalid")
    expected_version = sha256_bytes(
        canonical_raw
        + policy_sha256.encode("ascii")
        + source["manifestSha256"].encode("ascii")
        + (prior or "").encode("ascii")
    )
    if manifest.get("version") != expected_version:
        raise SourceValidationError("previous artifact version checksum mismatch")
    return manifest, canonical, sha256_bytes(manifest_raw)


def _canonical_union(canonical: dict[str, Any] | None) -> dict[int, list[Network]]:
    if canonical is None:
        return {4: [], 6: []}
    union = canonical.get("union")
    if not isinstance(union, dict):
        raise SourceValidationError("previous canonical union is missing")
    result: dict[int, list[Network]] = {4: [], 6: []}
    for family, key in ((4, "ipv4"), (6, "ipv6")):
        values = union.get(key)
        if not isinstance(values, list) or any(
            not isinstance(item, str) for item in values
        ):
            raise SourceValidationError(f"previous canonical {key} union is invalid")
        try:
            parsed = [ipaddress.ip_network(item, strict=True) for item in values]
        except ValueError as exc:
            raise SourceValidationError(
                f"previous canonical {key} union contains invalid CIDR"
            ) from exc
        if any(network.version != family for network in parsed) or parsed != _collapse(
            parsed
        ):
            raise SourceValidationError(
                f"previous canonical {key} union is not canonical"
            )
        result[family] = parsed
    return result


def _canonical_categories(
    canonical: dict[str, Any] | None,
) -> dict[str, dict[int, list[Network]]]:
    result: dict[str, dict[int, list[Network]]] = {
        category: {4: [], 6: []} for category in CATEGORY_COMMUNITIES
    }
    if canonical is None:
        return result
    categories = canonical.get("categories")
    if not isinstance(categories, dict) or set(categories) != set(CATEGORY_COMMUNITIES):
        raise SourceValidationError("previous canonical categories are invalid")
    for category in CATEGORY_COMMUNITIES:
        entry = categories[category]
        if not isinstance(entry, dict):
            raise SourceValidationError(
                f"previous canonical category {category} is invalid"
            )
        for family, key in ((4, "ipv4"), (6, "ipv6")):
            values = entry.get(key)
            if not isinstance(values, list) or any(
                not isinstance(item, str) for item in values
            ):
                raise SourceValidationError(
                    f"previous canonical category {category}.{key} is invalid"
                )
            try:
                parsed = [ipaddress.ip_network(item, strict=True) for item in values]
            except ValueError as exc:
                raise SourceValidationError(
                    f"previous canonical category {category}.{key} contains invalid CIDR"
                ) from exc
            if any(
                network.version != family for network in parsed
            ) or parsed != _collapse(parsed):
                raise SourceValidationError(
                    f"previous canonical category {category}.{key} is not canonical"
                )
            result[category][family] = parsed
    return result


def _atomic_write_directory(output_dir: Path, files: dict[str, bytes]) -> None:
    output = output_dir.absolute()
    if any(part.lower() in {".codex", ".git"} for part in output.parts):
        raise SourceValidationError(
            "refusing to write compiler artifacts under repository control metadata"
        )
    if output.exists() or output.is_symlink():
        raise SourceValidationError(
            f"immutable candidate path already exists: {output}"
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{output.name}.tmp-", dir=output.parent))
    try:
        for relative, content in sorted(files.items()):
            target = temporary / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
        _fsync_directory_tree(temporary)
        os.replace(temporary, output)
        _fsync_directory(output.parent)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def _fsync_directory(path: Path) -> None:
    if os.name == "nt":
        return
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _fsync_directory_tree(root: Path) -> None:
    for directory, _, _ in os.walk(root, topdown=False):
        _fsync_directory(Path(directory))


def _safe_percent(numerator: int, denominator: int) -> float:
    if numerator == 0:
        return 0.0
    if denominator == 0:
        return 100.0
    return round((numerator * 100.0) / denominator, 6)


def compile_routes(
    source_manifest: Path,
    policy: CompilePolicy,
    output_dir: Path,
    *,
    now: datetime,
    previous_dir: Path | None = None,
) -> dict[str, Any]:
    """Compile an immutable candidate without changing active or LKG state."""

    source = load_source(source_manifest, policy, now)
    routes = read_route_files(source, policy)
    previous_manifest, previous_canonical, previous_manifest_sha256 = _load_previous(
        previous_dir, policy
    )
    previous_union = _canonical_union(previous_canonical)
    previous_categories = _canonical_categories(previous_canonical)

    compiled: dict[str, dict[int, list[Network]]] = {}
    category_stats: dict[str, dict[str, Any]] = {}
    private_matches = private_addresses = 0
    management_matches = management_addresses = 0
    self_matches: list[str] = []

    for category in CATEGORY_COMMUNITIES:
        compiled[category] = {4: [], 6: []}
        raw_networks = routes[category]
        raw_count = sum(len(raw_networks[family]) for family in (4, 6))
        for family in (4, 6):
            normalized = _collapse(raw_networks[family])
            for endpoint in policy.self_endpoints:
                if endpoint.version == family and any(
                    endpoint in network for network in normalized
                ):
                    self_matches.append(f"{category}:{endpoint}")
            after_private, matched, removed_count = _subtract_networks(
                normalized, DEFAULT_FORBIDDEN_NETWORKS
            )
            private_matches += matched
            private_addresses += removed_count
            after_management, matched, removed_count = _subtract_networks(
                after_private, policy.management_networks
            )
            management_matches += matched
            management_addresses += removed_count
            compiled[category][family] = after_management
        total_compiled = sum(len(compiled[category][family]) for family in (4, 6))
        if total_compiled == 0:
            raise SafetyGateError(
                f"required category {category} is empty after exclusions"
            )
        category_stats[category] = {
            "raw": raw_count,
            "compiled": total_compiled,
            "addresses": sum(
                network.num_addresses
                for family in (4, 6)
                for network in compiled[category][family]
            ),
        }

    if self_matches:
        raise SafetyGateError(
            f"self endpoint present in source union: {sorted(set(self_matches))}"
        )

    union = {
        family: _collapse(
            network
            for category in CATEGORY_COMMUNITIES
            for network in compiled[category][family]
        )
        for family in (4, 6)
    }
    total_compiled_prefixes = sum(
        len(compiled[category][family]) for category in compiled for family in (4, 6)
    )
    if total_compiled_prefixes > policy.limits.max_compiled_prefixes:
        raise SafetyGateError(
            f"compiled output exceeds {policy.limits.max_compiled_prefixes} category prefixes"
        )
    if policy.ipv6.mode == "enabled" and not union[6]:
        raise SafetyGateError(
            "IPv6 policy is enabled but the compiled IPv6 union is empty"
        )
    if policy.ipv6.mode == "enabled":
        missing_ipv6_communities = sorted(
            set(
                community
                for communities in CATEGORY_COMMUNITIES.values()
                for community in communities
            )
            - {
                source_file.community
                for source_file in source.files
                if source_file.family == 6
            }
        )
        if missing_ipv6_communities:
            raise SafetyGateError(
                "IPv6 policy is enabled but communities are missing IPv6 files: "
                f"{missing_ipv6_communities}"
            )
        missing_ipv6 = sorted(
            category for category in CATEGORY_COMMUNITIES if not compiled[category][6]
        )
        if missing_ipv6:
            raise SafetyGateError(
                f"IPv6 policy is enabled but categories are missing IPv6 routes: {missing_ipv6}"
            )
    if policy.ipv6.mode != "enabled" and union[6]:
        raise SafetyGateError(
            "IPv6 routes were supplied while reviewed policy requires disabled/fallback-block state"
        )

    family_address_counts = {
        family: sum(network.num_addresses for network in union[family])
        for family in (4, 6)
    }
    coverage_limits = {
        4: policy.max_ipv4_union_percent,
        6: policy.max_ipv6_union_percent,
    }
    family_sizes = {4: 2**32, 6: 2**128}
    for family in (4, 6):
        coverage_percent_exact = (
            family_address_counts[family] * 100.0 / family_sizes[family]
        )
        if coverage_percent_exact > coverage_limits[family]:
            raise SafetyGateError(
                f"IPv{family} union address coverage {round(coverage_percent_exact, 6)}% "
                f"exceeds {coverage_limits[family]}%"
            )

    added = {
        family: _network_difference(union[family], previous_union[family])
        for family in (4, 6)
    }
    removed_delta = {
        family: _network_difference(previous_union[family], union[family])
        for family in (4, 6)
    }
    category_changes: dict[str, dict[str, Any]] = {}
    for category in CATEGORY_COMMUNITIES:
        category_added = {
            family: _network_difference(
                compiled[category][family], previous_categories[category][family]
            )
            for family in (4, 6)
        }
        category_removed = {
            family: _network_difference(
                previous_categories[category][family], compiled[category][family]
            )
            for family in (4, 6)
        }
        previous_category_addresses = sum(
            network.num_addresses
            for family in (4, 6)
            for network in previous_categories[category][family]
        )
        category_added_addresses = sum(
            network.num_addresses
            for family in (4, 6)
            for network in category_added[family]
        )
        category_removed_addresses = sum(
            network.num_addresses
            for family in (4, 6)
            for network in category_removed[family]
        )
        category_changes[category] = {
            "added": sum(len(category_added[family]) for family in (4, 6)),
            "removed": sum(len(category_removed[family]) for family in (4, 6)),
            "addedAddressCount": str(category_added_addresses),
            "removedAddressCount": str(category_removed_addresses),
            "addedPercent": _safe_percent(
                category_added_addresses, previous_category_addresses
            ),
            "removedPercent": _safe_percent(
                category_removed_addresses, previous_category_addresses
            ),
        }
    current_addresses = sum(
        network.num_addresses for family in (4, 6) for network in union[family]
    )
    previous_addresses = sum(
        network.num_addresses for family in (4, 6) for network in previous_union[family]
    )
    added_addresses = sum(
        network.num_addresses for family in (4, 6) for network in added[family]
    )
    removed_addresses = sum(
        network.num_addresses for family in (4, 6) for network in removed_delta[family]
    )
    added_percent = _safe_percent(added_addresses, previous_addresses)
    removed_percent = _safe_percent(removed_addresses, previous_addresses)

    suspicious: list[str] = []
    for category, stats in category_stats.items():
        threshold = policy.category_thresholds[category]
        if stats["compiled"] < threshold.min_prefixes:
            suspicious.append(
                f"{category} compiled prefix count {stats['compiled']} is below {threshold.min_prefixes}"
            )
        if stats["compiled"] > threshold.max_prefixes:
            suspicious.append(
                f"{category} compiled prefix count {stats['compiled']} exceeds {threshold.max_prefixes}"
            )
    if previous_manifest is not None:
        if added_percent > policy.max_added_percent:
            suspicious.append(
                f"added address delta {added_percent}% exceeds {policy.max_added_percent}%"
            )
        if removed_percent > policy.max_removed_percent:
            suspicious.append(
                f"removed address delta {removed_percent}% exceeds {policy.max_removed_percent}%"
            )
        for category, change in category_changes.items():
            if change["addedPercent"] > policy.max_added_percent:
                suspicious.append(
                    f"{category} added address delta {change['addedPercent']}% exceeds {policy.max_added_percent}%"
                )
            if change["removedPercent"] > policy.max_removed_percent:
                suspicious.append(
                    f"{category} removed address delta {change['removedPercent']}% exceeds {policy.max_removed_percent}%"
                )
        previous_exclusions = previous_manifest.get("exclusions", {})
        if not isinstance(previous_exclusions, dict):
            raise SourceValidationError(
                "previous manifest exclusions must be an object"
            )
        previous_exclusion_matches = 0
        for key in ("private", "management"):
            exclusion = previous_exclusions.get(key, {})
            if not isinstance(exclusion, dict) or not isinstance(
                exclusion.get("prefixMatches", 0), int
            ):
                raise SourceValidationError(
                    f"previous manifest exclusions.{key} is invalid"
                )
            previous_exclusion_matches += exclusion.get("prefixMatches", 0)
        exclusion_delta = abs(
            (private_matches + management_matches) - previous_exclusion_matches
        )
        if exclusion_delta > policy.max_exclusion_delta:
            suspicious.append(
                f"exclusion prefix-match delta {exclusion_delta} exceeds {policy.max_exclusion_delta}"
            )

    canonical = {
        "schemaVersion": 1,
        "product": "premium_spb_de_exceptions",
        "sourceVersion": source.source_version,
        "generatedAt": format_utc_timestamp(source.generated_at),
        "ipv6Policy": {"mode": policy.ipv6.mode, "reason": policy.ipv6.reason},
        "categories": {
            category: {
                "communities": list(CATEGORY_COMMUNITIES[category]),
                "ipv4": [str(network) for network in compiled[category][4]],
                "ipv6": [str(network) for network in compiled[category][6]],
            }
            for category in CATEGORY_COMMUNITIES
        },
        "union": {
            "ipv4": [str(network) for network in union[4]],
            "ipv6": [str(network) for network in union[6]],
        },
    }
    canonical_raw = canonical_json_bytes(canonical)
    policy_sha256 = sha256_bytes(policy.canonical_bytes)
    version = sha256_bytes(
        canonical_raw
        + policy_sha256.encode("ascii")
        + source.manifest_sha256.encode("ascii")
        + (previous_manifest_sha256 or "").encode("ascii")
    )

    files: dict[str, bytes] = {"canonical.json": canonical_raw}
    for category in CATEGORY_COMMUNITIES:
        files[f"categories/{category}.ipv4.cidr"] = _cidr_bytes(compiled[category][4])
        files[f"categories/{category}.ipv6.cidr"] = _cidr_bytes(compiled[category][6])
    files["union/ipv4.cidr"] = _cidr_bytes(union[4])
    files["union/ipv6.cidr"] = _cidr_bytes(union[6])
    files["deltas/added.ipv4.cidr"] = _cidr_bytes(added[4])
    files["deltas/added.ipv6.cidr"] = _cidr_bytes(added[6])
    files["deltas/removed.ipv4.cidr"] = _cidr_bytes(removed_delta[4])
    files["deltas/removed.ipv6.cidr"] = _cidr_bytes(removed_delta[6])
    xray = {
        "schemaVersion": 1,
        "outboundTag": "DE_EXCEPTIONS_BRIDGE",
        "matchedFailurePolicy": "fail_closed",
        "ipv6Policy": {
            "mode": policy.ipv6.mode,
            "unmatched": "profile_disabled"
            if policy.ipv6.mode == "disabled"
            else (
                "block"
                if policy.ipv6.mode == "fallback_block"
                else "normal_profile_policy"
            ),
        },
        "rules": [
            {
                "family": family,
                "ip": [str(network) for network in union[family]],
                "outboundTag": "DE_EXCEPTIONS_BRIDGE",
            }
            for family in (4, 6)
            if union[family]
        ],
    }
    files["xray/de-exceptions.json"] = canonical_json_bytes(xray)

    manifest = {
        "schemaVersion": 1,
        "product": "premium_spb_de_exceptions",
        "version": version,
        "generatedAt": format_utc_timestamp(source.generated_at),
        "source": {
            "type": source.source_type,
            "provider": source.provider,
            "collector": source.collector,
            "sourceVersion": source.source_version,
            "manifestSha256": source.manifest_sha256,
        },
        "policySha256": policy_sha256,
        "freshness": {
            "status": "fresh",
            "maxAgeSeconds": policy.max_age_seconds,
            "maxFutureSkewSeconds": policy.max_future_skew_seconds,
        },
        "ipv6Policy": {"mode": policy.ipv6.mode, "reason": policy.ipv6.reason},
        "xray": {
            "rulesPath": "xray/de-exceptions.json",
            "rulesSha256": sha256_bytes(files["xray/de-exceptions.json"]),
        },
        "categories": {
            category: {
                "communities": list(CATEGORY_COMMUNITIES[category]),
                "prefixCountRaw": category_stats[category]["raw"],
                "prefixCountCompiled": category_stats[category]["compiled"],
                "addressCount": str(category_stats[category]["addresses"]),
                "families": {
                    "ipv4": len(compiled[category][4]),
                    "ipv6": len(compiled[category][6]),
                },
                "sha256": sha256_bytes(
                    canonical_json_bytes(
                        {
                            "ipv4": [str(network) for network in compiled[category][4]],
                            "ipv6": [str(network) for network in compiled[category][6]],
                        }
                    )
                ),
            }
            for category in CATEGORY_COMMUNITIES
        },
        "union": {
            "prefixCount": sum(len(union[family]) for family in (4, 6)),
            "addressCount": str(current_addresses),
            "families": {"ipv4": len(union[4]), "ipv6": len(union[6])},
            "sha256": sha256_bytes(
                canonical_json_bytes(
                    {
                        "ipv4": [str(network) for network in union[4]],
                        "ipv6": [str(network) for network in union[6]],
                    }
                )
            ),
        },
        "exclusions": {
            "private": {
                "prefixMatches": private_matches,
                "addressCount": str(private_addresses),
            },
            "management": {
                "prefixMatches": management_matches,
                "addressCount": str(management_addresses),
            },
            "selfEndpoints": {"prefixMatches": 0, "addressCount": "0"},
            "invalid": {"prefixMatches": 0, "addressCount": "0"},
        },
        "previousManifestSha256": previous_manifest_sha256,
        "change": {
            "added": sum(len(added[family]) for family in (4, 6)),
            "removed": sum(len(removed_delta[family]) for family in (4, 6)),
            "addedAddressCount": str(added_addresses),
            "removedAddressCount": str(removed_addresses),
            "addedPercent": added_percent,
            "removedPercent": removed_percent,
            "categories": category_changes,
        },
        "safety": {
            "status": "approval_required" if suspicious else "accepted",
            "reasons": sorted(suspicious),
        },
        "artifacts": {
            relative: sha256_bytes(content)
            for relative, content in sorted(files.items())
        },
    }
    files["manifest.json"] = canonical_json_bytes(manifest)
    _atomic_write_directory(output_dir, files)
    return manifest
