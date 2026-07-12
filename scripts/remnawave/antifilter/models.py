from __future__ import annotations

import hashlib
import ipaddress
import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

SCHEMA_VERSION = 1
PRODUCT = "premium_spb_de_exceptions"

CATEGORY_COMMUNITIES: dict[str, tuple[str, ...]] = {
    "rkn": ("65444:100",),
    "meta": ("65444:700",),
    "twitter_x": ("65444:710",),
    "netflix": ("65444:720",),
    "amazon_cloudfront": ("65444:730",),
    "microsoft": ("65444:740",),
    "amazon": ("65444:750",),
    "openai": ("65444:760",),
    "youtube": ("65444:770",),
    "google": ("65444:780",),
    "telegram": ("65444:790",),
    "discord": ("65444:800",),
    "custom_networks": ("65444:65444",),
}
COMMUNITY_CATEGORY = {
    community: category
    for category, communities in CATEGORY_COMMUNITIES.items()
    for community in communities
}

DEFAULT_FORBIDDEN_NETWORKS = tuple(
    ipaddress.ip_network(value)
    for value in (
        "0.0.0.0/8",
        "10.0.0.0/8",
        "100.64.0.0/10",
        "127.0.0.0/8",
        "169.254.0.0/16",
        "172.16.0.0/12",
        "192.0.0.0/24",
        "192.0.2.0/24",
        "192.88.99.0/24",
        "192.168.0.0/16",
        "198.18.0.0/15",
        "198.51.100.0/24",
        "203.0.113.0/24",
        "224.0.0.0/3",
        "::/127",
        "2001:db8::/32",
        "fc00::/7",
        "fe80::/10",
        "ff00::/8",
    )
)


class RouteCompilerError(ValueError):
    """A safe, operator-facing rejection of untrusted route data or state."""


class SourceValidationError(RouteCompilerError):
    pass


class PolicyValidationError(RouteCompilerError):
    pass


class SafetyGateError(RouteCompilerError):
    pass


class PublishError(RouteCompilerError):
    pass


@dataclass(frozen=True)
class ResourceLimits:
    max_manifest_bytes: int = 262_144
    max_file_bytes: int = 16_777_216
    max_total_bytes: int = 134_217_728
    max_files: int = 64
    max_lines_per_file: int = 1_000_000
    max_line_bytes: int = 128
    max_compiled_prefixes: int = 2_000_000


@dataclass(frozen=True)
class CategoryThreshold:
    min_prefixes: int
    max_prefixes: int


@dataclass(frozen=True)
class Ipv6Policy:
    mode: Literal["enabled", "disabled", "fallback_block"]
    reason: str


@dataclass(frozen=True)
class CompilePolicy:
    management_networks: tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...]
    self_endpoints: tuple[ipaddress.IPv4Address | ipaddress.IPv6Address, ...]
    category_thresholds: dict[str, CategoryThreshold]
    max_added_percent: float
    max_removed_percent: float
    max_ipv4_union_percent: float
    max_ipv6_union_percent: float
    max_exclusion_delta: int
    max_age_seconds: int
    max_future_skew_seconds: int
    ipv6: Ipv6Policy
    limits: ResourceLimits
    canonical_bytes: bytes


@dataclass(frozen=True)
class SourceFile:
    community: str
    family: int
    path: str
    sha256: str


@dataclass(frozen=True)
class CanonicalSource:
    generated_at: datetime
    source_version: str
    source_type: str
    provider: str
    collector: str
    files: tuple[SourceFile, ...]
    ipv6: Ipv6Policy
    manifest_path: Path
    manifest_sha256: str


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def parse_utc_timestamp(value: object, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise SourceValidationError(
            f"{field} must be a non-empty RFC3339 UTC timestamp"
        )
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise SourceValidationError(
            f"{field} is not a valid RFC3339 timestamp"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        raise SourceValidationError(f"{field} must use UTC")
    return parsed.astimezone(UTC)


def format_utc_timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _require_exact_keys(
    value: dict[str, Any], expected: set[str], context: str
) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        unexpected = sorted(actual - expected)
        raise PolicyValidationError(
            f"{context} keys mismatch; missing={missing}, unexpected={unexpected}"
        )


def _positive_int(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise PolicyValidationError(f"{field} must be a positive integer")
    return value


def _non_negative_number(value: object, field: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
    ):
        raise PolicyValidationError(f"{field} must be a non-negative number")
    return float(value)


def reject_non_finite_json(value: str) -> None:
    raise ValueError(f"non-finite JSON number is forbidden: {value}")


def _load_json_object(
    path: Path, max_bytes: int, context: str
) -> tuple[dict[str, Any], bytes]:
    try:
        with path.open("rb") as handle:
            raw = handle.read(max_bytes + 1)
        if len(raw) > max_bytes:
            raise PolicyValidationError(f"{context} exceeds {max_bytes} bytes")
        value = json.loads(raw.decode("utf-8"), parse_constant=reject_non_finite_json)
    except PolicyValidationError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise PolicyValidationError(f"cannot read canonical {context}: {exc}") from exc
    if not isinstance(value, dict):
        raise PolicyValidationError(f"{context} must be a JSON object")
    return value, raw


def _parse_ipv6_policy(value: object, context: str) -> Ipv6Policy:
    if not isinstance(value, dict):
        raise PolicyValidationError(f"{context} must be an object")
    _require_exact_keys(value, {"mode", "reason"}, context)
    mode = value["mode"]
    reason = value["reason"]
    if mode not in {"enabled", "disabled", "fallback_block"}:
        raise PolicyValidationError(
            f"{context}.mode must be enabled, disabled, or fallback_block"
        )
    if not isinstance(reason, str) or not reason.strip() or len(reason) > 500:
        raise PolicyValidationError(f"{context}.reason must contain 1-500 characters")
    return Ipv6Policy(mode=mode, reason=reason.strip())


def load_policy(path: Path) -> CompilePolicy:
    value, raw = _load_json_object(path, 262_144, "policy")
    _require_exact_keys(
        value,
        {
            "schemaVersion",
            "managementNetworks",
            "selfEndpoints",
            "thresholds",
            "freshness",
            "ipv6Policy",
            "resourceLimits",
        },
        "policy",
    )
    if value["schemaVersion"] != SCHEMA_VERSION:
        raise PolicyValidationError("unsupported policy schemaVersion")

    management_raw = value["managementNetworks"]
    endpoints_raw = value["selfEndpoints"]
    if not isinstance(management_raw, list) or not isinstance(endpoints_raw, list):
        raise PolicyValidationError(
            "managementNetworks and selfEndpoints must be arrays"
        )
    try:
        management = tuple(
            ipaddress.ip_network(item, strict=True) for item in management_raw
        )
        endpoints = tuple(ipaddress.ip_address(item) for item in endpoints_raw)
    except (TypeError, ValueError) as exc:
        raise PolicyValidationError(
            f"policy contains an invalid canonical network/address: {exc}"
        ) from exc
    if len(set(management)) != len(management) or len(set(endpoints)) != len(endpoints):
        raise PolicyValidationError(
            "managementNetworks and selfEndpoints must not contain duplicates"
        )

    thresholds = value["thresholds"]
    if not isinstance(thresholds, dict):
        raise PolicyValidationError("thresholds must be an object")
    _require_exact_keys(
        thresholds,
        {
            "default",
            "categories",
            "maxAddedPercent",
            "maxRemovedPercent",
            "maxIpv4UnionPercent",
            "maxIpv6UnionPercent",
            "maxExclusionDelta",
        },
        "thresholds",
    )
    default = thresholds["default"]
    overrides = thresholds["categories"]
    if not isinstance(default, dict) or not isinstance(overrides, dict):
        raise PolicyValidationError("threshold defaults and categories must be objects")
    _require_exact_keys(default, {"minPrefixes", "maxPrefixes"}, "thresholds.default")
    unknown_categories = set(overrides) - set(CATEGORY_COMMUNITIES)
    if unknown_categories:
        raise PolicyValidationError(
            f"unknown threshold categories: {sorted(unknown_categories)}"
        )
    category_thresholds: dict[str, CategoryThreshold] = {}
    for category in CATEGORY_COMMUNITIES:
        selected = overrides.get(category, default)
        if not isinstance(selected, dict):
            raise PolicyValidationError(
                f"thresholds.categories.{category} must be an object"
            )
        _require_exact_keys(
            selected,
            {"minPrefixes", "maxPrefixes"},
            f"thresholds.categories.{category}",
        )
        minimum = _positive_int(selected["minPrefixes"], f"{category}.minPrefixes")
        maximum = _positive_int(selected["maxPrefixes"], f"{category}.maxPrefixes")
        if minimum > maximum:
            raise PolicyValidationError(f"{category} minPrefixes exceeds maxPrefixes")
        category_thresholds[category] = CategoryThreshold(minimum, maximum)

    freshness = value["freshness"]
    limits = value["resourceLimits"]
    if not isinstance(freshness, dict) or not isinstance(limits, dict):
        raise PolicyValidationError("freshness and resourceLimits must be objects")
    _require_exact_keys(
        freshness, {"maxAgeSeconds", "maxFutureSkewSeconds"}, "freshness"
    )
    limit_fields = {
        "maxManifestBytes",
        "maxFileBytes",
        "maxTotalBytes",
        "maxFiles",
        "maxLinesPerFile",
        "maxLineBytes",
        "maxCompiledPrefixes",
    }
    _require_exact_keys(limits, limit_fields, "resourceLimits")
    resource_limits = ResourceLimits(
        max_manifest_bytes=_positive_int(
            limits["maxManifestBytes"], "maxManifestBytes"
        ),
        max_file_bytes=_positive_int(limits["maxFileBytes"], "maxFileBytes"),
        max_total_bytes=_positive_int(limits["maxTotalBytes"], "maxTotalBytes"),
        max_files=_positive_int(limits["maxFiles"], "maxFiles"),
        max_lines_per_file=_positive_int(limits["maxLinesPerFile"], "maxLinesPerFile"),
        max_line_bytes=_positive_int(limits["maxLineBytes"], "maxLineBytes"),
        max_compiled_prefixes=_positive_int(
            limits["maxCompiledPrefixes"], "maxCompiledPrefixes"
        ),
    )
    if resource_limits.max_file_bytes > resource_limits.max_total_bytes:
        raise PolicyValidationError("maxFileBytes cannot exceed maxTotalBytes")

    return CompilePolicy(
        management_networks=management,
        self_endpoints=endpoints,
        category_thresholds=category_thresholds,
        max_added_percent=_non_negative_number(
            thresholds["maxAddedPercent"], "maxAddedPercent"
        ),
        max_removed_percent=_non_negative_number(
            thresholds["maxRemovedPercent"], "maxRemovedPercent"
        ),
        max_ipv4_union_percent=_non_negative_number(
            thresholds["maxIpv4UnionPercent"], "maxIpv4UnionPercent"
        ),
        max_ipv6_union_percent=_non_negative_number(
            thresholds["maxIpv6UnionPercent"], "maxIpv6UnionPercent"
        ),
        max_exclusion_delta=_positive_int(
            thresholds["maxExclusionDelta"], "maxExclusionDelta"
        ),
        max_age_seconds=_positive_int(freshness["maxAgeSeconds"], "maxAgeSeconds"),
        max_future_skew_seconds=_positive_int(
            freshness["maxFutureSkewSeconds"], "maxFutureSkewSeconds"
        ),
        ipv6=_parse_ipv6_policy(value["ipv6Policy"], "ipv6Policy"),
        limits=resource_limits,
        canonical_bytes=canonical_json_bytes(value),
    )
