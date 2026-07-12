from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import re
import shutil
import tempfile
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path, PurePosixPath
from collections.abc import Iterator
from typing import Any

from .compiler import (
    _canonical_categories,
    _canonical_union,
    _collapse,
    _network_difference,
    _safe_percent,
)
from .models import (
    CATEGORY_COMMUNITIES,
    DEFAULT_FORBIDDEN_NETWORKS,
    PRODUCT,
    CompilePolicy,
    PublishError,
    SourceValidationError,
    canonical_json_bytes,
    format_utc_timestamp,
    parse_utc_timestamp,
    reject_non_finite_json,
    sha256_bytes,
)

VERSION_RE = re.compile(r"^[0-9a-f]{64}$")
MAX_MANIFEST_BYTES = 4 * 1024 * 1024
MAX_APPROVAL_BYTES = 64 * 1024
MAX_POINTER_BYTES = 4096
MAX_ARTIFACT_BYTES = 256 * 1024 * 1024
MAX_CANDIDATE_BYTES = 1024 * 1024 * 1024
MAX_ARTIFACT_FILES = 128
REQUIRED_ARTIFACTS = {
    "canonical.json",
    "union/ipv4.cidr",
    "union/ipv6.cidr",
    "deltas/added.ipv4.cidr",
    "deltas/added.ipv6.cidr",
    "deltas/removed.ipv4.cidr",
    "deltas/removed.ipv6.cidr",
    "xray/de-exceptions.json",
    *{
        f"categories/{category}.ipv{family}.cidr"
        for category in CATEGORY_COMMUNITIES
        for family in (4, 6)
    },
}


def _read_limited(path: Path, limit: int, context: str) -> bytes:
    try:
        with path.open("rb") as handle:
            value = handle.read(limit + 1)
    except OSError as exc:
        raise PublishError(f"cannot read {context}: {exc}") from exc
    if len(value) > limit:
        raise PublishError(f"{context} exceeds {limit} bytes")
    return value


def _sha256_file(path: Path, limit: int, context: str) -> tuple[str, int]:
    digest = hashlib.sha256()
    total = 0
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                total += len(chunk)
                if total > limit:
                    raise PublishError(f"{context} exceeds {limit} bytes")
                digest.update(chunk)
    except PublishError:
        raise
    except OSError as exc:
        raise PublishError(f"cannot read {context}: {exc}") from exc
    return digest.hexdigest(), total


def _safe_artifact_path(root: Path, relative: object) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise PublishError("artifact path must be a non-empty POSIX relative path")
    pure = PurePosixPath(relative)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        raise PublishError(f"unsafe artifact path: {relative!r}")
    target = root.joinpath(*pure.parts)
    try:
        target.resolve(strict=True).relative_to(root.resolve(strict=True))
    except (OSError, ValueError) as exc:
        raise PublishError(
            f"artifact escapes or is missing from candidate: {relative!r}"
        ) from exc
    current = target
    while current != root.parent:
        if current.is_symlink():
            raise PublishError(f"artifact path contains a symlink: {relative!r}")
        if current == root:
            break
        current = current.parent
    if not target.is_file():
        raise PublishError(f"artifact must be a regular non-symlink file: {relative!r}")
    return target


def _load_candidate(candidate_dir: Path) -> tuple[dict[str, Any], bytes]:
    if candidate_dir.is_symlink() or not candidate_dir.is_dir():
        raise PublishError("candidate must be a regular directory")
    manifest_path = candidate_dir / "manifest.json"
    try:
        manifest_raw = _read_limited(
            manifest_path, MAX_MANIFEST_BYTES, "candidate manifest"
        )
        manifest = json.loads(
            manifest_raw.decode("utf-8"), parse_constant=reject_non_finite_json
        )
    except PublishError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise PublishError(f"cannot read candidate manifest: {exc}") from exc
    if not isinstance(manifest, dict) or manifest.get("schemaVersion") != 1:
        raise PublishError("candidate manifest schema is invalid")
    version = manifest.get("version")
    if not isinstance(version, str) or not VERSION_RE.fullmatch(version):
        raise PublishError("candidate version must be a lowercase SHA-256")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict) or not artifacts:
        raise PublishError("candidate artifact checksum map is missing")
    if len(artifacts) > MAX_ARTIFACT_FILES:
        raise PublishError(
            f"candidate declares more than {MAX_ARTIFACT_FILES} artifacts"
        )
    if set(artifacts) != REQUIRED_ARTIFACTS:
        raise PublishError(
            f"candidate artifact contract mismatch: {sorted(set(artifacts) ^ REQUIRED_ARTIFACTS)}"
        )
    total_bytes = len(manifest_raw)
    for relative, expected in sorted(artifacts.items()):
        if not isinstance(expected, str) or not VERSION_RE.fullmatch(expected):
            raise PublishError(f"invalid artifact checksum for {relative!r}")
        path = _safe_artifact_path(candidate_dir, relative)
        actual, size = _sha256_file(
            path, MAX_ARTIFACT_BYTES, f"candidate artifact {relative!r}"
        )
        total_bytes += size
        if total_bytes > MAX_CANDIDATE_BYTES:
            raise PublishError(f"candidate exceeds {MAX_CANDIDATE_BYTES} total bytes")
        if actual != expected:
            raise PublishError(f"candidate artifact checksum mismatch: {relative}")
    expected_files = {"manifest.json", *artifacts}
    actual_files = {
        path.relative_to(candidate_dir).as_posix()
        for path in candidate_dir.rglob("*")
        if path.is_file() or path.is_symlink()
    }
    if actual_files != expected_files:
        raise PublishError(
            f"candidate contains unexpected or missing files: {sorted(actual_files ^ expected_files)}"
        )
    expected_directories = {"categories", "union", "deltas", "xray"}
    actual_directories = {
        path.relative_to(candidate_dir).as_posix()
        for path in candidate_dir.rglob("*")
        if path.is_dir() and not path.is_symlink()
    }
    if actual_directories != expected_directories:
        raise PublishError(
            f"candidate directory contract mismatch: {sorted(actual_directories ^ expected_directories)}"
        )
    return manifest, manifest_raw


def _verify_candidate_semantics(
    candidate_dir: Path, manifest: dict[str, Any], policy: CompilePolicy
) -> dict[str, Any]:
    policy_sha256 = sha256_bytes(policy.canonical_bytes)
    if (
        manifest.get("product") != PRODUCT
        or manifest.get("policySha256") != policy_sha256
    ):
        raise PublishError("candidate product or reviewed policy checksum mismatch")
    try:
        canonical_raw = _read_limited(
            candidate_dir / "canonical.json", MAX_ARTIFACT_BYTES, "canonical artifact"
        )
        canonical = json.loads(
            canonical_raw.decode("utf-8"), parse_constant=reject_non_finite_json
        )
    except PublishError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise PublishError(f"canonical artifact is invalid: {exc}") from exc
    if not isinstance(canonical, dict) or canonical.get("product") != PRODUCT:
        raise PublishError("canonical artifact product/schema is invalid")
    try:
        categories = _canonical_categories(canonical)
        union = _canonical_union(canonical)
    except SourceValidationError as exc:
        raise PublishError(str(exc)) from exc
    for category, communities in CATEGORY_COMMUNITIES.items():
        entry = canonical["categories"][category]
        if entry.get("communities") != list(communities):
            raise PublishError(f"canonical community mapping mismatch for {category}")
        count = sum(len(categories[category][family]) for family in (4, 6))
        if count == 0:
            raise PublishError(f"canonical category {category} is empty")
    manifest_categories = manifest.get("categories")
    if not isinstance(manifest_categories, dict):
        raise PublishError("candidate category manifest must be an object")
    for category in CATEGORY_COMMUNITIES:
        raw_count = manifest_categories.get(category, {}).get("prefixCountRaw")
        if (
            isinstance(raw_count, bool)
            or not isinstance(raw_count, int)
            or raw_count <= 0
        ):
            raise PublishError(
                f"candidate raw category count is invalid for {category}"
            )
    expected_categories = {
        category: {
            "communities": list(CATEGORY_COMMUNITIES[category]),
            "prefixCountRaw": manifest_categories[category]["prefixCountRaw"],
            "prefixCountCompiled": sum(
                len(categories[category][family]) for family in (4, 6)
            ),
            "addressCount": str(
                sum(
                    network.num_addresses
                    for family in (4, 6)
                    for network in categories[category][family]
                )
            ),
            "families": {
                "ipv4": len(categories[category][4]),
                "ipv6": len(categories[category][6]),
            },
            "sha256": sha256_bytes(
                canonical_json_bytes(
                    {
                        "ipv4": [str(network) for network in categories[category][4]],
                        "ipv6": [str(network) for network in categories[category][6]],
                    }
                )
            ),
        }
        for category in CATEGORY_COMMUNITIES
    }
    if manifest_categories != expected_categories:
        raise PublishError(
            "candidate category manifest does not match canonical routes"
        )
    derived_union = {
        family: _collapse(
            network
            for category in CATEGORY_COMMUNITIES
            for network in categories[category][family]
        )
        for family in (4, 6)
    }
    if derived_union != union:
        raise PublishError("canonical union does not equal the category union")
    expected_ipv6 = {"mode": policy.ipv6.mode, "reason": policy.ipv6.reason}
    if (
        canonical.get("ipv6Policy") != expected_ipv6
        or manifest.get("ipv6Policy") != expected_ipv6
    ):
        raise PublishError("candidate IPv6 policy does not match the reviewed policy")
    if policy.ipv6.mode == "enabled" and any(
        not categories[category][6] for category in CATEGORY_COMMUNITIES
    ):
        raise PublishError("enabled IPv6 candidate is missing category routes")
    if policy.ipv6.mode != "enabled" and union[6]:
        raise PublishError("disabled/fallback-block candidate contains IPv6 routes")
    forbidden = (*DEFAULT_FORBIDDEN_NETWORKS, *policy.management_networks)
    for family in (4, 6):
        for network in union[family]:
            if any(
                network.version == excluded.version and network.overlaps(excluded)
                for excluded in forbidden
            ):
                raise PublishError(
                    "canonical union contains forbidden or management space"
                )
            if any(
                endpoint.version == family and endpoint in network
                for endpoint in policy.self_endpoints
            ):
                raise PublishError("canonical union contains a self endpoint")
    family_sizes = {4: 2**32, 6: 2**128}
    limits = {4: policy.max_ipv4_union_percent, 6: policy.max_ipv6_union_percent}
    for family in (4, 6):
        addresses = sum(network.num_addresses for network in union[family])
        if addresses * 100.0 / family_sizes[family] > limits[family]:
            raise PublishError(
                f"IPv{family} canonical union exceeds reviewed address coverage"
            )
    union_manifest = manifest.get("union")
    if not isinstance(union_manifest, dict):
        raise PublishError("candidate union manifest is invalid")
    union_payload = {
        "ipv4": [str(network) for network in union[4]],
        "ipv6": [str(network) for network in union[6]],
    }
    if (
        union_manifest.get("prefixCount")
        != sum(len(union[family]) for family in (4, 6))
        or union_manifest.get("addressCount")
        != str(
            sum(network.num_addresses for family in (4, 6) for network in union[family])
        )
        or union_manifest.get("sha256")
        != sha256_bytes(canonical_json_bytes(union_payload))
    ):
        raise PublishError("candidate union manifest does not match canonical routes")
    xray_manifest = manifest.get("xray")
    if not isinstance(xray_manifest, dict) or xray_manifest != {
        "rulesPath": "xray/de-exceptions.json",
        "rulesSha256": manifest["artifacts"]["xray/de-exceptions.json"],
    }:
        raise PublishError("candidate Xray manifest contract is invalid")
    try:
        xray = json.loads(
            _read_limited(
                candidate_dir / "xray/de-exceptions.json",
                MAX_ARTIFACT_BYTES,
                "Xray artifact",
            ).decode("utf-8"),
            parse_constant=reject_non_finite_json,
        )
    except PublishError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise PublishError(f"Xray artifact is invalid: {exc}") from exc
    if (
        not isinstance(xray, dict)
        or xray.get("matchedFailurePolicy") != "fail_closed"
        or xray.get("outboundTag") != "DE_EXCEPTIONS_BRIDGE"
        or not isinstance(xray.get("rules"), list)
    ):
        raise PublishError("Xray artifact safety contract is invalid")
    rendered: dict[int, list[ipaddress.IPv4Network | ipaddress.IPv6Network]] = {
        4: [],
        6: [],
    }
    try:
        for rule in xray["rules"]:
            if not isinstance(rule, dict) or rule.get("family") not in {4, 6}:
                raise PublishError("Xray artifact contains an invalid rule")
            family = rule["family"]
            ips = rule.get("ip")
            if not isinstance(ips, list) or not ips:
                raise PublishError("Xray artifact contains an empty matcher")
            parsed = [ipaddress.ip_network(value, strict=True) for value in ips]
            if any(network.version != family for network in parsed):
                raise PublishError("Xray artifact family mismatch")
            rendered[family].extend(parsed)
    except (TypeError, ValueError) as exc:
        raise PublishError("Xray artifact contains invalid CIDR") from exc
    if {family: _collapse(rendered[family]) for family in (4, 6)} != union:
        raise PublishError("Xray artifact routes do not match the canonical union")
    source = manifest.get("source")
    previous = manifest.get("previousManifestSha256")
    if (
        not isinstance(source, dict)
        or not VERSION_RE.fullmatch(str(source.get("manifestSha256")))
        or (previous is not None and not VERSION_RE.fullmatch(str(previous)))
    ):
        raise PublishError("candidate provenance checksums are invalid")
    expected_version = sha256_bytes(
        canonical_raw
        + policy_sha256.encode("ascii")
        + source["manifestSha256"].encode("ascii")
        + (previous or "").encode("ascii")
    )
    if manifest.get("version") != expected_version:
        raise PublishError("candidate version does not match canonical provenance")
    return canonical


def _prefix_matches(exclusions: object, key: str) -> int:
    if not isinstance(exclusions, dict):
        raise PublishError("candidate exclusions must be an object")
    value = exclusions.get(key)
    if (
        not isinstance(value, dict)
        or isinstance(value.get("prefixMatches"), bool)
        or not isinstance(value.get("prefixMatches"), int)
    ):
        raise PublishError(f"candidate exclusions.{key} is invalid")
    return value["prefixMatches"]


def _verify_delta_decision(
    root: Path,
    manifest: dict[str, Any],
    canonical: dict[str, Any],
    policy: CompilePolicy,
) -> None:
    active = _read_pointer(root, "active")
    previous_sha = manifest.get("previousManifestSha256")
    previous_manifest: dict[str, Any] | None = None
    previous_canonical: dict[str, Any] | None = None
    if active is None:
        if previous_sha is not None:
            raise PublishError(
                "bootstrap candidate references an untrusted previous manifest"
            )
    elif active["version"] != manifest["version"]:
        if previous_sha != active["manifestSha256"]:
            raise PublishError(
                "candidate previous manifest is not the current active version"
            )
        previous_dir = root / "versions" / active["version"]
        previous_manifest, _ = _load_candidate(previous_dir)
        if previous_manifest.get("product") != PRODUCT or previous_manifest.get(
            "policySha256"
        ) != sha256_bytes(policy.canonical_bytes):
            raise PublishError("active previous version has incompatible provenance")
        if previous_manifest.get("version") != active["version"]:
            raise PublishError("active pointer/version manifest mismatch")
        _verify_candidate_semantics(previous_dir, previous_manifest, policy)
        try:
            previous_canonical_value = json.loads(
                _read_limited(
                    previous_dir / "canonical.json",
                    MAX_ARTIFACT_BYTES,
                    "active canonical artifact",
                ).decode("utf-8"),
                parse_constant=reject_non_finite_json,
            )
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise PublishError(f"active canonical artifact is invalid: {exc}") from exc
        if not isinstance(previous_canonical_value, dict):
            raise PublishError("active canonical artifact must be an object")
        previous_canonical = previous_canonical_value

    current_union = _canonical_union(canonical)
    previous_union = _canonical_union(previous_canonical)
    current_categories = _canonical_categories(canonical)
    previous_categories = _canonical_categories(previous_canonical)
    added = {
        family: _network_difference(current_union[family], previous_union[family])
        for family in (4, 6)
    }
    removed = {
        family: _network_difference(previous_union[family], current_union[family])
        for family in (4, 6)
    }
    previous_addresses = sum(
        network.num_addresses for family in (4, 6) for network in previous_union[family]
    )
    added_addresses = sum(
        network.num_addresses for family in (4, 6) for network in added[family]
    )
    removed_addresses = sum(
        network.num_addresses for family in (4, 6) for network in removed[family]
    )
    category_changes: dict[str, dict[str, Any]] = {}
    for category in CATEGORY_COMMUNITIES:
        category_added = {
            family: _network_difference(
                current_categories[category][family],
                previous_categories[category][family],
            )
            for family in (4, 6)
        }
        category_removed = {
            family: _network_difference(
                previous_categories[category][family],
                current_categories[category][family],
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
    added_percent = _safe_percent(added_addresses, previous_addresses)
    removed_percent = _safe_percent(removed_addresses, previous_addresses)
    expected_change = {
        "added": sum(len(added[family]) for family in (4, 6)),
        "removed": sum(len(removed[family]) for family in (4, 6)),
        "addedAddressCount": str(added_addresses),
        "removedAddressCount": str(removed_addresses),
        "addedPercent": added_percent,
        "removedPercent": removed_percent,
        "categories": category_changes,
    }
    if manifest.get("change") != expected_change:
        raise PublishError(
            "candidate change metadata does not match trusted delta state"
        )
    reasons: list[str] = []
    for category in CATEGORY_COMMUNITIES:
        count = sum(len(current_categories[category][family]) for family in (4, 6))
        threshold = policy.category_thresholds[category]
        if count < threshold.min_prefixes:
            reasons.append(
                f"{category} compiled prefix count {count} is below {threshold.min_prefixes}"
            )
        if count > threshold.max_prefixes:
            reasons.append(
                f"{category} compiled prefix count {count} exceeds {threshold.max_prefixes}"
            )
    if previous_manifest is not None:
        if added_percent > policy.max_added_percent:
            reasons.append(
                f"added address delta {added_percent}% exceeds {policy.max_added_percent}%"
            )
        if removed_percent > policy.max_removed_percent:
            reasons.append(
                f"removed address delta {removed_percent}% exceeds {policy.max_removed_percent}%"
            )
        for category, change in category_changes.items():
            if change["addedPercent"] > policy.max_added_percent:
                reasons.append(
                    f"{category} added address delta {change['addedPercent']}% exceeds {policy.max_added_percent}%"
                )
            if change["removedPercent"] > policy.max_removed_percent:
                reasons.append(
                    f"{category} removed address delta {change['removedPercent']}% exceeds {policy.max_removed_percent}%"
                )
        current_matches = sum(
            _prefix_matches(manifest.get("exclusions"), key)
            for key in ("private", "management")
        )
        previous_matches = sum(
            _prefix_matches(previous_manifest.get("exclusions"), key)
            for key in ("private", "management")
        )
        exclusion_delta = abs(current_matches - previous_matches)
        if exclusion_delta > policy.max_exclusion_delta:
            reasons.append(
                f"exclusion prefix-match delta {exclusion_delta} exceeds {policy.max_exclusion_delta}"
            )
    expected_safety = {
        "status": "approval_required" if reasons else "accepted",
        "reasons": sorted(reasons),
    }
    if manifest.get("safety") != expected_safety:
        raise PublishError(
            "candidate safety decision does not match trusted delta state"
        )


def _validate_store_root(store_root: Path) -> Path:
    root = store_root.absolute()
    if any(part.lower() in {".codex", ".git"} for part in root.parts):
        raise PublishError(
            "publish store must not be placed under repository control metadata"
        )
    root.mkdir(parents=True, exist_ok=True)
    if root.is_symlink():
        raise PublishError("publish store root must not be a symlink")
    return root


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(canonical_json_bytes(value))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _fsync_directory(path: Path) -> None:
    if os.name == "nt":
        return
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _fsync_tree(root: Path) -> None:
    for path in root.rglob("*"):
        if path.is_file():
            with path.open("r+b") as handle:
                handle.flush()
                os.fsync(handle.fileno())
    if os.name != "nt":
        for directory, _, _ in os.walk(root, topdown=False):
            _fsync_directory(Path(directory))


@contextmanager
def _state_lock(root: Path) -> Iterator[None]:
    lock_path = root / ".state.lock"
    try:
        descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise PublishError(
            "artifact state is locked by another publish/promote/rollback operation"
        ) from exc
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(b"locked\n")
            handle.flush()
            os.fsync(handle.fileno())
        _fsync_directory(root)
        yield
    finally:
        lock_path.unlink(missing_ok=True)
        _fsync_directory(root)


def _read_pointer(root: Path, name: str) -> dict[str, Any] | None:
    path = root / f"{name}.json"
    if not path.exists():
        return None
    try:
        value = json.loads(
            _read_limited(path, MAX_POINTER_BYTES, f"{name} pointer").decode("utf-8"),
            parse_constant=reject_non_finite_json,
        )
    except PublishError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise PublishError(f"cannot read {name} pointer: {exc}") from exc
    if not isinstance(value, dict) or set(value) != {"version", "manifestSha256"}:
        raise PublishError(f"{name} pointer is invalid")
    if not VERSION_RE.fullmatch(str(value["version"])) or not VERSION_RE.fullmatch(
        str(value["manifestSha256"])
    ):
        raise PublishError(f"{name} pointer checksums are invalid")
    version_dir = root / "versions" / value["version"]
    if not version_dir.is_dir():
        raise PublishError(f"{name} points to a missing version")
    manifest_path = version_dir / "manifest.json"
    manifest_sha256, _ = _sha256_file(
        manifest_path, MAX_MANIFEST_BYTES, f"{name} manifest"
    )
    if manifest_sha256 != value["manifestSha256"]:
        raise PublishError(f"{name} pointer manifest checksum mismatch")
    return value


def approve_candidate(
    candidate_dir: Path,
    approval_path: Path,
    *,
    approved_by: str,
    ticket: str,
    approved_at: datetime,
) -> dict[str, Any]:
    manifest, manifest_raw = _load_candidate(candidate_dir)
    if manifest.get("safety", {}).get("status") != "approval_required":
        raise PublishError(
            "manual approval is only valid for an approval-required candidate"
        )
    if (
        not approved_by.strip()
        or not ticket.strip()
        or len(approved_by) > 200
        or len(ticket) > 200
    ):
        raise PublishError("approved_by and ticket must contain 1-200 characters")
    record = {
        "schemaVersion": 1,
        "candidateVersion": manifest["version"],
        "manifestSha256": sha256_bytes(manifest_raw),
        "reasons": manifest["safety"]["reasons"],
        "approvedBy": approved_by.strip(),
        "approvedAt": format_utc_timestamp(approved_at),
        "ticket": ticket.strip(),
    }
    if approval_path.exists() or approval_path.is_symlink():
        raise PublishError("approval record path already exists")
    _atomic_json(approval_path, record)
    return record


def _verify_approval(
    manifest: dict[str, Any], manifest_raw: bytes, approval_path: Path | None
) -> None:
    status = manifest.get("safety", {}).get("status")
    if status == "accepted":
        if approval_path is not None:
            raise PublishError(
                "accepted candidate must not use a manual approval override"
            )
        return
    if status != "approval_required" or approval_path is None:
        raise PublishError("candidate is blocked pending a manual approval record")
    try:
        record = json.loads(
            _read_limited(
                approval_path, MAX_APPROVAL_BYTES, "manual approval record"
            ).decode("utf-8"),
            parse_constant=reject_non_finite_json,
        )
    except PublishError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise PublishError(f"cannot read manual approval record: {exc}") from exc
    expected_keys = {
        "schemaVersion",
        "candidateVersion",
        "manifestSha256",
        "reasons",
        "approvedBy",
        "approvedAt",
        "ticket",
    }
    if not isinstance(record, dict) or set(record) != expected_keys:
        raise PublishError("manual approval record schema is invalid")
    if (
        record["schemaVersion"] != 1
        or record["candidateVersion"] != manifest["version"]
        or record["manifestSha256"] != sha256_bytes(manifest_raw)
        or record["reasons"] != manifest["safety"]["reasons"]
        or not isinstance(record["approvedBy"], str)
        or not record["approvedBy"].strip()
        or not isinstance(record["ticket"], str)
        or not record["ticket"].strip()
        or len(record["approvedBy"]) > 200
        or len(record["ticket"]) > 200
    ):
        raise PublishError(
            "manual approval record does not authorize this exact candidate"
        )
    try:
        parse_utc_timestamp(record["approvedAt"], "approvedAt")
    except SourceValidationError as exc:
        raise PublishError("manual approval timestamp is invalid") from exc


def _publish_candidate_unlocked(
    candidate_dir: Path,
    store_root: Path,
    *,
    policy: CompilePolicy,
    approval_path: Path | None = None,
) -> dict[str, Any]:
    manifest, manifest_raw = _load_candidate(candidate_dir)
    canonical = _verify_candidate_semantics(candidate_dir, manifest, policy)
    root = _validate_store_root(store_root)
    active = _read_pointer(root, "active")
    if active is not None and active["version"] == manifest["version"]:
        existing, existing_raw = _load_candidate(root / "versions" / active["version"])
        _verify_candidate_semantics(
            root / "versions" / active["version"], existing, policy
        )
        if existing_raw != manifest_raw:
            raise PublishError("immutable version collision")
        return active
    _verify_delta_decision(root, manifest, canonical, policy)
    _verify_approval(manifest, manifest_raw, approval_path)
    versions = root / "versions"
    versions.mkdir(exist_ok=True)
    version_dir = versions / manifest["version"]
    if version_dir.exists():
        existing, existing_raw = _load_candidate(version_dir)
        _verify_candidate_semantics(version_dir, existing, policy)
        if existing_raw != manifest_raw:
            raise PublishError("immutable version collision")
    else:
        temporary = Path(
            tempfile.mkdtemp(prefix=f".{manifest['version']}.tmp-", dir=versions)
        )
        try:
            shutil.copytree(
                candidate_dir, temporary, dirs_exist_ok=True, symlinks=False
            )
            copied_manifest, copied_raw = _load_candidate(temporary)
            if (
                copied_manifest["version"] != manifest["version"]
                or copied_raw != manifest_raw
            ):
                raise PublishError("copied candidate verification failed")
            _fsync_tree(temporary)
            os.replace(temporary, version_dir)
            _fsync_directory(versions)
        except Exception:
            shutil.rmtree(temporary, ignore_errors=True)
            raise

    pointer = {
        "version": manifest["version"],
        "manifestSha256": sha256_bytes(manifest_raw),
    }
    _read_pointer(root, "active")
    lkg = _read_pointer(root, "last-known-good")
    if lkg is None:
        _atomic_json(root / "last-known-good.json", pointer)
    _atomic_json(root / "active.json", pointer)
    return pointer


def publish_candidate(
    candidate_dir: Path,
    store_root: Path,
    *,
    policy: CompilePolicy,
    approval_path: Path | None = None,
) -> dict[str, Any]:
    root = _validate_store_root(store_root)
    with _state_lock(root):
        return _publish_candidate_unlocked(
            candidate_dir, root, policy=policy, approval_path=approval_path
        )


def promote_active(store_root: Path) -> dict[str, Any]:
    root = _validate_store_root(store_root)
    with _state_lock(root):
        active = _read_pointer(root, "active")
        if active is None:
            raise PublishError("cannot promote without an active version")
        _atomic_json(root / "last-known-good.json", active)
        return active


def rollback_to_lkg(store_root: Path) -> dict[str, Any]:
    root = _validate_store_root(store_root)
    with _state_lock(root):
        lkg = _read_pointer(root, "last-known-good")
        if lkg is None:
            raise PublishError("cannot roll back without a last-known-good version")
        _atomic_json(root / "active.json", lkg)
        return lkg


def record_failure(
    store_root: Path, *, reason: str, source_sha256: str | None, failed_at: datetime
) -> Path:
    root = _validate_store_root(store_root)
    safe_reason = " ".join(reason.split())[:1000]
    record = {
        "schemaVersion": 1,
        "status": "degraded",
        "failedAt": format_utc_timestamp(failed_at),
        "reason": safe_reason,
        "sourceSha256": source_sha256,
    }
    digest = sha256_bytes(canonical_json_bytes(record))
    path = root / "failures" / f"{digest}.json"
    if not path.exists():
        _atomic_json(path, record)
    return path
