from __future__ import annotations

import ipaddress
import json
import os
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

from .models import (
    COMMUNITY_CATEGORY,
    CanonicalSource,
    CompilePolicy,
    Ipv6Policy,
    PolicyValidationError,
    SourceFile,
    SourceValidationError,
    parse_utc_timestamp,
    reject_non_finite_json,
    sha256_bytes,
)

Network = ipaddress.IPv4Network | ipaddress.IPv6Network


def _exact_keys(value: dict[str, Any], expected: set[str], context: str) -> None:
    actual = set(value)
    if actual != expected:
        raise SourceValidationError(
            f"{context} keys mismatch; missing={sorted(expected - actual)}, unexpected={sorted(actual - expected)}"
        )


def _safe_relative_file(root: Path, relative: object) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise SourceValidationError(
            "route file path must be a non-empty POSIX relative path"
        )
    pure = PurePosixPath(relative)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        raise SourceValidationError(f"unsafe route file path: {relative!r}")
    candidate = root.joinpath(*pure.parts)
    try:
        root_resolved = root.resolve(strict=True)
        candidate_resolved = candidate.resolve(strict=True)
        candidate_resolved.relative_to(root_resolved)
    except (OSError, ValueError) as exc:
        raise SourceValidationError(
            f"route file escapes or is missing from source root: {relative!r}"
        ) from exc
    current = candidate
    while current != root.parent:
        if current.is_symlink():
            raise SourceValidationError(
                f"symlinks are forbidden in source paths: {relative!r}"
            )
        if current == root:
            break
        current = current.parent
    if not candidate_resolved.is_file():
        raise SourceValidationError(f"route source is not a regular file: {relative!r}")
    return candidate_resolved


def load_source(
    manifest_path: Path, policy: CompilePolicy, now: datetime
) -> CanonicalSource:
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    now = now.astimezone(UTC)
    try:
        if manifest_path.is_symlink():
            raise SourceValidationError("source manifest must not be a symlink")
        with manifest_path.open("rb") as handle:
            raw = handle.read(policy.limits.max_manifest_bytes + 1)
        if len(raw) > policy.limits.max_manifest_bytes:
            raise SourceValidationError(
                f"source manifest exceeds {policy.limits.max_manifest_bytes} bytes"
            )
        value = json.loads(raw.decode("utf-8"), parse_constant=reject_non_finite_json)
    except SourceValidationError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise SourceValidationError(
            f"cannot read canonical source manifest: {exc}"
        ) from exc
    if not isinstance(value, dict):
        raise SourceValidationError("source manifest must be a JSON object")
    _exact_keys(
        value, {"schemaVersion", "source", "files", "ipv6Policy"}, "source manifest"
    )
    if value["schemaVersion"] != 1:
        raise SourceValidationError("unsupported source schemaVersion")

    source = value["source"]
    if not isinstance(source, dict):
        raise SourceValidationError("source must be an object")
    _exact_keys(
        source,
        {"type", "provider", "collector", "generatedAt", "sourceVersion"},
        "source",
    )
    source_type = source["type"]
    if source_type not in {"external-canonical-cidr", "bgp-canonical-cidr"}:
        raise SourceValidationError(
            "source.type must be an approved canonical CIDR interface"
        )
    for field in ("provider", "collector", "sourceVersion"):
        if (
            not isinstance(source[field], str)
            or not source[field].strip()
            or len(source[field]) > 200
        ):
            raise SourceValidationError(f"source.{field} must contain 1-200 characters")
    generated_at = parse_utc_timestamp(source["generatedAt"], "source.generatedAt")
    age = (now - generated_at).total_seconds()
    if age > policy.max_age_seconds:
        raise SourceValidationError(
            f"source is stale by {int(age)} seconds; maximum age is {policy.max_age_seconds} seconds"
        )
    if age < -policy.max_future_skew_seconds:
        raise SourceValidationError("source.generatedAt is too far in the future")

    try:
        ipv6 = _parse_source_ipv6(value["ipv6Policy"])
    except PolicyValidationError as exc:
        raise SourceValidationError(str(exc)) from exc
    if ipv6 != policy.ipv6:
        raise SourceValidationError(
            "source ipv6Policy must exactly match the reviewed compiler policy"
        )

    files = value["files"]
    if not isinstance(files, list) or not files:
        raise SourceValidationError("source files must be a non-empty array")
    if len(files) > policy.limits.max_files:
        raise SourceValidationError(
            f"source declares more than {policy.limits.max_files} files"
        )
    parsed: list[SourceFile] = []
    seen_paths: set[str] = set()
    seen_community_families: set[tuple[str, int]] = set()
    for index, item in enumerate(files):
        if not isinstance(item, dict):
            raise SourceValidationError(f"files[{index}] must be an object")
        _exact_keys(item, {"community", "family", "path", "sha256"}, f"files[{index}]")
        community = item["community"]
        family = item["family"]
        path = item["path"]
        checksum = item["sha256"]
        if not isinstance(community, str):
            raise SourceValidationError(f"files[{index}].community must be a string")
        if community not in COMMUNITY_CATEGORY:
            raise SourceValidationError(
                f"unknown or unsupported community: {community!r}"
            )
        if (
            isinstance(family, bool)
            or not isinstance(family, int)
            or family not in {4, 6}
        ):
            raise SourceValidationError(f"files[{index}].family must be 4 or 6")
        if not isinstance(path, str) or not path:
            raise SourceValidationError(
                f"files[{index}].path must be a non-empty string"
            )
        if (
            not isinstance(checksum, str)
            or len(checksum) != 64
            or any(c not in "0123456789abcdef" for c in checksum)
        ):
            raise SourceValidationError(
                f"files[{index}].sha256 must be lowercase SHA-256"
            )
        if path in seen_paths or (community, family) in seen_community_families:
            raise SourceValidationError(
                "source paths and community/family entries must be unique"
            )
        seen_paths.add(path)
        seen_community_families.add((community, family))
        parsed.append(
            SourceFile(community=community, family=family, path=path, sha256=checksum)
        )

    missing = sorted(set(COMMUNITY_CATEGORY) - {item.community for item in parsed})
    if missing:
        raise SourceValidationError(f"required communities are missing: {missing}")
    return CanonicalSource(
        generated_at=generated_at,
        source_version=source["sourceVersion"].strip(),
        source_type=source_type,
        provider=source["provider"].strip(),
        collector=source["collector"].strip(),
        files=tuple(
            sorted(parsed, key=lambda item: (item.community, item.family, item.path))
        ),
        ipv6=ipv6,
        manifest_path=manifest_path.resolve(),
        manifest_sha256=sha256_bytes(raw),
    )


def _parse_source_ipv6(value: object) -> Ipv6Policy:
    if not isinstance(value, dict):
        raise PolicyValidationError("ipv6Policy must be an object")
    if set(value) != {"mode", "reason"}:
        raise PolicyValidationError("ipv6Policy must contain exactly mode and reason")
    mode = value["mode"]
    reason = value["reason"]
    if mode not in {"enabled", "disabled", "fallback_block"}:
        raise PolicyValidationError("invalid ipv6Policy.mode")
    if not isinstance(reason, str) or not reason.strip() or len(reason) > 500:
        raise PolicyValidationError("invalid ipv6Policy.reason")
    return Ipv6Policy(mode=mode, reason=reason.strip())


def read_route_files(
    source: CanonicalSource, policy: CompilePolicy
) -> dict[str, dict[int, list[Network]]]:
    result: dict[str, dict[int, list[Network]]] = {
        category: {4: [], 6: []} for category in set(COMMUNITY_CATEGORY.values())
    }
    total_bytes = 0
    root = source.manifest_path.parent
    for source_file in source.files:
        path = _safe_relative_file(root, source_file.path)
        try:
            if not os.path.isfile(path):
                raise SourceValidationError(
                    f"route source is not a regular file: {source_file.path!r}"
                )
            with path.open("rb") as handle:
                raw = handle.read(policy.limits.max_file_bytes + 1)
        except SourceValidationError:
            raise
        except OSError as exc:
            raise SourceValidationError(
                f"cannot read route file {source_file.path!r}: {exc}"
            ) from exc
        if len(raw) > policy.limits.max_file_bytes:
            raise SourceValidationError(
                f"route file {source_file.path!r} exceeds {policy.limits.max_file_bytes} bytes"
            )
        total_bytes += len(raw)
        if total_bytes > policy.limits.max_total_bytes:
            raise SourceValidationError(
                f"route files exceed {policy.limits.max_total_bytes} total bytes"
            )
        if sha256_bytes(raw) != source_file.sha256:
            raise SourceValidationError(
                f"checksum mismatch for route file {source_file.path!r}"
            )
        try:
            text = raw.decode("ascii")
        except UnicodeDecodeError as exc:
            raise SourceValidationError(
                f"route file {source_file.path!r} must be ASCII"
            ) from exc
        lines = text.splitlines()
        if not lines:
            raise SourceValidationError(f"route file {source_file.path!r} is empty")
        if len(lines) > policy.limits.max_lines_per_file:
            raise SourceValidationError(
                f"route file {source_file.path!r} exceeds {policy.limits.max_lines_per_file} lines"
            )
        networks: list[Network] = []
        for line_number, line in enumerate(lines, start=1):
            if (
                not line
                or line != line.strip()
                or len(line.encode("ascii")) > policy.limits.max_line_bytes
            ):
                raise SourceValidationError(
                    f"invalid formatting at {source_file.path}:{line_number}"
                )
            if any(marker in line for marker in ("#", ";", ",")) or any(
                character.isspace() for character in line
            ):
                raise SourceValidationError(
                    f"CIDR-only line required at {source_file.path}:{line_number}"
                )
            try:
                network = ipaddress.ip_network(line, strict=False)
            except ValueError as exc:
                raise SourceValidationError(
                    f"invalid CIDR at {source_file.path}:{line_number}"
                ) from exc
            if network.version != source_file.family:
                raise SourceValidationError(
                    f"address family mismatch at {source_file.path}:{line_number}"
                )
            networks.append(network)
        result[COMMUNITY_CATEGORY[source_file.community]][source_file.family].extend(
            networks
        )
    return result
