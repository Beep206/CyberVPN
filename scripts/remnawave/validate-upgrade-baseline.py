#!/usr/bin/env python3
"""Fail-closed validator for sanitized, read-only Remnawave baseline inventories."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, TypeGuard

_SCHEMA_VERSION = 2
_BASELINE_PANEL_VERSION = "2.8.0"
_BASELINE_NODE_VERSION = "2.8.0"
_BASELINE_SUBSCRIPTION_VERSION = "7.2.6"
_DEFAULT_MAX_AGE_MINUTES = 60
_MAX_ALLOWED_AGE_MINUTES = 360
_MAX_INVENTORY_BYTES = 1_000_000
_MAX_NODES_PER_ENVIRONMENT = 256
_MAX_FUTURE_SKEW = timedelta(minutes=5)
_MAX_PAIR_SKEW = timedelta(minutes=30)

_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")
_SAFE_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_SAFE_METADATA_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,255}$")
_REQUIRED_ENVIRONMENTS = frozenset({"staging", "production"})
_REQUIRED_PARITY_GROUPS = frozenset(
    {"users", "mappings", "nodes", "hosts", "profiles", "squads", "plugins", "hwids"}
)

_TOP_LEVEL_KEYS = frozenset(
    {
        "schema_version",
        "environment",
        "environment_binding_sha256",
        "collection_mode",
        "sanitized",
        "contains_secret_values",
        "collected_at",
        "panel",
        "nodes",
        "subscription_page",
        "migrations",
        "topology",
        "state_parity",
    }
)
_PANEL_KEYS = frozenset(
    {"version", "image_digest", "auth_secret_sha256", "source_metadata"}
)
_SOURCE_METADATA_KEYS = frozenset({"image_ref", "source_commit", "build_record_sha256"})
_NODE_KEYS = frozenset(
    {
        "name",
        "version",
        "image_digest",
        "runtime_secret_key_sha256",
        "panel_secret_key_sha256",
    }
)
_SUBSCRIPTION_KEYS = frozenset({"version", "image_digest"})
_MIGRATION_KEYS = frozenset(
    {
        "cybervpn_alembic_head",
        "remnawave_pending",
        "remnawave_failed",
        "remnawave_applied_count",
        "remnawave_expected_count",
        "remnawave_applied_set_sha256",
        "remnawave_expected_set_sha256",
        "parity",
    }
)
_TOPOLOGY_KEYS = frozenset(
    {
        "expected_node_count",
        "observed_node_count",
        "expected_node_names_sha256",
        "observed_node_names_sha256",
        "parity",
    }
)
_PARITY_KEYS = frozenset(
    {
        "authoritative_count",
        "observed_count",
        "authoritative_set_sha256",
        "observed_set_sha256",
        "count_parity",
        "identity_parity",
    }
)


def _object_without_duplicate_keys(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("inventory contains duplicate JSON object keys")
        value[key] = item
    return value


def _load(path: Path) -> dict[str, Any]:
    if path.stat().st_size > _MAX_INVENTORY_BYTES:
        raise ValueError(f"{path}: inventory exceeds the size limit")
    raw = path.read_text(encoding="utf-8")
    if len(raw.encode("utf-8")) > _MAX_INVENTORY_BYTES:
        raise ValueError(f"{path}: inventory exceeds the size limit")
    value = json.loads(raw, object_pairs_hook=_object_without_duplicate_keys)
    if not isinstance(value, dict):
        raise ValueError(f"{path}: inventory root must be an object")
    return value


def _check_exact_keys(
    value: dict[str, Any],
    expected: frozenset[str],
    *,
    label: str,
    errors: list[str],
) -> None:
    missing = expected - value.keys()
    unsupported = value.keys() - expected
    if missing:
        errors.append(f"{label}: required fields are missing")
    if unsupported:
        # Do not echo attacker-controlled field names into release logs.
        errors.append(f"{label}: unsupported fields are present")


def _as_object(value: object, *, label: str, errors: list[str]) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    errors.append(f"{label}: must be an object")
    return {}


def _parse_aware_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(timezone.utc)


def _is_non_negative_int(value: object) -> TypeGuard[int]:
    return type(value) is int and value >= 0


def _is_required_environment(value: object) -> TypeGuard[str]:
    return isinstance(value, str) and value in _REQUIRED_ENVIRONMENTS


def _set_sha256(values: set[str] | frozenset[str]) -> str:
    canonical = json.dumps(
        sorted(values), ensure_ascii=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _valid_fingerprint(value: object) -> TypeGuard[str]:
    return isinstance(value, str) and _SHA256_HEX_RE.fullmatch(value) is not None


def _same_fingerprint(left: object, right: object) -> bool:
    return (
        _valid_fingerprint(left)
        and _valid_fingerprint(right)
        and hmac.compare_digest(str(left), str(right))
    )


def _validate_source_metadata(value: object, *, prefix: str, errors: list[str]) -> None:
    metadata = _as_object(
        value, label=f"{prefix}: panel source metadata", errors=errors
    )
    _check_exact_keys(
        metadata,
        _SOURCE_METADATA_KEYS,
        label=f"{prefix}: panel source metadata",
        errors=errors,
    )
    image_ref = metadata.get("image_ref")
    source_commit = metadata.get("source_commit")
    if (
        not isinstance(image_ref, str)
        or _SAFE_METADATA_RE.fullmatch(image_ref) is None
        or "REPLACE" in image_ref.upper()
    ):
        errors.append(f"{prefix}: panel source image reference is missing or invalid")
    if (
        not isinstance(source_commit, str)
        or _SAFE_METADATA_RE.fullmatch(source_commit) is None
        or "REPLACE" in source_commit.upper()
    ):
        errors.append(
            f"{prefix}: panel source commit/build record is missing or invalid"
        )
    if not _valid_fingerprint(metadata.get("build_record_sha256")):
        errors.append(f"{prefix}: panel build record fingerprint is missing or invalid")


def _validate_migrations(
    value: object,
    *,
    prefix: str,
    expected_cybervpn_head: str,
    errors: list[str],
) -> None:
    migrations = _as_object(value, label=f"{prefix}: migrations", errors=errors)
    _check_exact_keys(
        migrations, _MIGRATION_KEYS, label=f"{prefix}: migrations", errors=errors
    )
    if migrations.get("cybervpn_alembic_head") != expected_cybervpn_head:
        errors.append(f"{prefix}: CyberVPN migration head mismatch")
    remnawave_pending = migrations.get("remnawave_pending")
    if type(remnawave_pending) is not int or remnawave_pending != 0:
        errors.append(f"{prefix}: Remnawave has pending migrations")
    if migrations.get("remnawave_failed") is not False:
        errors.append(f"{prefix}: Remnawave migration state is not clean")

    applied_count = migrations.get("remnawave_applied_count")
    expected_count = migrations.get("remnawave_expected_count")
    if not _is_non_negative_int(applied_count) or not _is_non_negative_int(
        expected_count
    ):
        errors.append(f"{prefix}: Remnawave migration counts are missing or invalid")
    elif applied_count != expected_count:
        errors.append(f"{prefix}: Remnawave migration count parity mismatch")

    applied_hash = migrations.get("remnawave_applied_set_sha256")
    expected_hash = migrations.get("remnawave_expected_set_sha256")
    if not _valid_fingerprint(applied_hash) or not _valid_fingerprint(expected_hash):
        errors.append(f"{prefix}: Remnawave migration set fingerprints are invalid")
    elif not _same_fingerprint(applied_hash, expected_hash):
        errors.append(f"{prefix}: Remnawave migration set parity mismatch")
    if migrations.get("parity") is not True:
        errors.append(f"{prefix}: Remnawave migration parity is not affirmed")


def _validate_state_parity(
    value: object, *, prefix: str, errors: list[str]
) -> dict[str, tuple[int, int, str, str]]:
    parity = _as_object(value, label=f"{prefix}: state_parity", errors=errors)
    _check_exact_keys(
        parity,
        _REQUIRED_PARITY_GROUPS,
        label=f"{prefix}: state_parity",
        errors=errors,
    )
    parsed: dict[str, tuple[int, int, str, str]] = {}
    for group in sorted(_REQUIRED_PARITY_GROUPS):
        record = _as_object(
            parity.get(group),
            label=f"{prefix}: state_parity.{group}",
            errors=errors,
        )
        _check_exact_keys(
            record,
            _PARITY_KEYS,
            label=f"{prefix}: state_parity.{group}",
            errors=errors,
        )
        authoritative_count = record.get("authoritative_count")
        observed_count = record.get("observed_count")
        authoritative_hash = record.get("authoritative_set_sha256")
        observed_hash = record.get("observed_set_sha256")
        counts_valid = _is_non_negative_int(
            authoritative_count
        ) and _is_non_negative_int(observed_count)
        hashes_valid = _valid_fingerprint(authoritative_hash) and _valid_fingerprint(
            observed_hash
        )
        if not counts_valid:
            errors.append(f"{prefix}: {group} parity counts are missing or invalid")
        elif authoritative_count != observed_count:
            errors.append(f"{prefix}: {group} count parity mismatch")
        if not hashes_valid:
            errors.append(f"{prefix}: {group} parity fingerprints are invalid")
        elif not _same_fingerprint(authoritative_hash, observed_hash):
            errors.append(f"{prefix}: {group} identity parity mismatch")
        if record.get("count_parity") is not True:
            errors.append(f"{prefix}: {group} count parity is not affirmed")
        if record.get("identity_parity") is not True:
            errors.append(f"{prefix}: {group} identity parity is not affirmed")
        if (
            _is_non_negative_int(authoritative_count)
            and _is_non_negative_int(observed_count)
            and _valid_fingerprint(authoritative_hash)
            and _valid_fingerprint(observed_hash)
        ):
            parsed[group] = (
                authoritative_count,
                observed_count,
                authoritative_hash,
                observed_hash,
            )
    return parsed


def _validate_topology(
    value: object,
    *,
    prefix: str,
    expected_node_names: frozenset[str],
    observed_node_names: set[str],
    state_parity: dict[str, tuple[int, int, str, str]],
    errors: list[str],
) -> None:
    topology = _as_object(value, label=f"{prefix}: topology", errors=errors)
    _check_exact_keys(
        topology, _TOPOLOGY_KEYS, label=f"{prefix}: topology", errors=errors
    )
    expected_count = topology.get("expected_node_count")
    observed_count = topology.get("observed_node_count")
    expected_hash = topology.get("expected_node_names_sha256")
    observed_hash = topology.get("observed_node_names_sha256")
    computed_expected_hash = _set_sha256(expected_node_names)
    computed_observed_hash = _set_sha256(observed_node_names)

    if expected_node_names != observed_node_names:
        errors.append(f"{prefix}: complete expected node topology mismatch")
    if not _is_non_negative_int(expected_count) or expected_count != len(
        expected_node_names
    ):
        errors.append(f"{prefix}: expected topology node count mismatch")
    if not _is_non_negative_int(observed_count) or observed_count != len(
        observed_node_names
    ):
        errors.append(f"{prefix}: observed topology node count mismatch")
    if not _valid_fingerprint(expected_hash) or not hmac.compare_digest(
        str(expected_hash), computed_expected_hash
    ):
        errors.append(f"{prefix}: expected topology fingerprint mismatch")
    if not _valid_fingerprint(observed_hash) or not hmac.compare_digest(
        str(observed_hash), computed_observed_hash
    ):
        errors.append(f"{prefix}: observed topology fingerprint mismatch")
    if topology.get("parity") is not True:
        errors.append(f"{prefix}: topology parity is not affirmed")

    node_parity = state_parity.get("nodes")
    if node_parity is not None:
        authoritative_count, parity_observed_count, authoritative_hash, parity_hash = (
            node_parity
        )
        if (
            authoritative_count != len(expected_node_names)
            or parity_observed_count != len(observed_node_names)
            or not hmac.compare_digest(authoritative_hash, computed_expected_hash)
            or not hmac.compare_digest(parity_hash, computed_observed_hash)
        ):
            errors.append(f"{prefix}: nodes state parity disagrees with topology")


def _validate_inventory(
    inventory: dict[str, Any],
    *,
    expected_panel_digest: str,
    expected_node_digest: str,
    expected_subscription_digest: str,
    expected_cybervpn_head: str,
    expected_binding_sha256: str | None,
    expected_node_names: frozenset[str],
    now: datetime,
    max_age: timedelta,
) -> tuple[list[str], datetime | None]:
    environment = inventory.get("environment")
    prefix = str(environment) if _is_required_environment(environment) else "unknown"
    errors: list[str] = []
    _check_exact_keys(inventory, _TOP_LEVEL_KEYS, label=prefix, errors=errors)
    schema_version = inventory.get("schema_version")
    if type(schema_version) is not int or schema_version != _SCHEMA_VERSION:
        errors.append(f"{prefix}: unsupported inventory schema_version")
    if not _is_required_environment(environment):
        errors.append(f"{prefix}: environment must be staging or production")
    if inventory.get("collection_mode") != "read_only":
        errors.append(f"{prefix}: collection_mode must be read_only")
    if (
        inventory.get("sanitized") is not True
        or inventory.get("contains_secret_values") is not False
    ):
        errors.append(
            f"{prefix}: inventory must be sanitized and contain no secret values"
        )

    binding = inventory.get("environment_binding_sha256")
    if not _valid_fingerprint(binding):
        errors.append(f"{prefix}: environment binding fingerprint is invalid")
    elif expected_binding_sha256 is None or not hmac.compare_digest(
        str(binding), expected_binding_sha256
    ):
        errors.append(f"{prefix}: environment binding mismatch")

    collected_at = _parse_aware_timestamp(inventory.get("collected_at"))
    if collected_at is None:
        errors.append(
            f"{prefix}: collected_at must be an ISO-8601 timestamp with timezone"
        )
    elif collected_at - now > _MAX_FUTURE_SKEW:
        errors.append(f"{prefix}: inventory timestamp is too far in the future")
    elif now - collected_at > max_age:
        errors.append(f"{prefix}: inventory is stale")

    panel = _as_object(inventory.get("panel"), label=f"{prefix}: panel", errors=errors)
    _check_exact_keys(panel, _PANEL_KEYS, label=f"{prefix}: panel", errors=errors)
    if panel.get("version") != _BASELINE_PANEL_VERSION:
        errors.append(f"{prefix}: panel version mismatch")
    if panel.get("image_digest") != expected_panel_digest:
        errors.append(f"{prefix}: panel digest mismatch")
    if not _valid_fingerprint(panel.get("auth_secret_sha256")):
        errors.append(
            f"{prefix}: panel auth secret continuity fingerprint is missing or invalid"
        )
    _validate_source_metadata(
        panel.get("source_metadata"), prefix=prefix, errors=errors
    )

    nodes = inventory.get("nodes")
    observed_node_names: set[str] = set()
    if not isinstance(nodes, list) or not nodes:
        errors.append(f"{prefix}: at least one node inventory item is required")
    elif len(nodes) > _MAX_NODES_PER_ENVIRONMENT:
        errors.append(f"{prefix}: node inventory exceeds the topology limit")
    else:
        node_secret_fingerprints: set[str] = set()
        for index, raw_node in enumerate(nodes):
            node = _as_object(raw_node, label=f"{prefix}: node[{index}]", errors=errors)
            _check_exact_keys(
                node, _NODE_KEYS, label=f"{prefix}: node[{index}]", errors=errors
            )
            node_name = node.get("name")
            if (
                not isinstance(node_name, str)
                or _SAFE_IDENTIFIER_RE.fullmatch(node_name) is None
                or node_name in observed_node_names
            ):
                errors.append(f"{prefix}: node[{index}] name is missing or duplicated")
            else:
                observed_node_names.add(node_name)
            if node.get("version") != _BASELINE_NODE_VERSION:
                errors.append(f"{prefix}: node[{index}] version mismatch")
            if node.get("image_digest") != expected_node_digest:
                errors.append(f"{prefix}: node[{index}] digest mismatch")
            runtime_fingerprint = node.get("runtime_secret_key_sha256")
            panel_fingerprint = node.get("panel_secret_key_sha256")
            if not _valid_fingerprint(runtime_fingerprint) or not _valid_fingerprint(
                panel_fingerprint
            ):
                errors.append(
                    f"{prefix}: node[{index}] SECRET_KEY fingerprints are missing or invalid"
                )
            elif not _same_fingerprint(runtime_fingerprint, panel_fingerprint):
                errors.append(
                    f"{prefix}: node[{index}] SECRET_KEY differs from the panel payload"
                )
            elif str(runtime_fingerprint) in node_secret_fingerprints:
                errors.append(
                    f"{prefix}: node[{index}] SECRET_KEY fingerprint is duplicated"
                )
            else:
                node_secret_fingerprints.add(str(runtime_fingerprint))

    subscription = _as_object(
        inventory.get("subscription_page"),
        label=f"{prefix}: subscription_page",
        errors=errors,
    )
    _check_exact_keys(
        subscription,
        _SUBSCRIPTION_KEYS,
        label=f"{prefix}: subscription_page",
        errors=errors,
    )
    if subscription.get("version") != _BASELINE_SUBSCRIPTION_VERSION:
        errors.append(f"{prefix}: subscription-page version mismatch")
    if subscription.get("image_digest") != expected_subscription_digest:
        errors.append(f"{prefix}: subscription-page digest mismatch")

    _validate_migrations(
        inventory.get("migrations"),
        prefix=prefix,
        expected_cybervpn_head=expected_cybervpn_head,
        errors=errors,
    )
    state_parity = _validate_state_parity(
        inventory.get("state_parity"), prefix=prefix, errors=errors
    )
    _validate_topology(
        inventory.get("topology"),
        prefix=prefix,
        expected_node_names=expected_node_names,
        observed_node_names=observed_node_names,
        state_parity=state_parity,
        errors=errors,
    )
    return errors, collected_at


def _expected_nodes(values: object, *, label: str) -> frozenset[str]:
    if not isinstance(values, list) or not values:
        raise ValueError(f"At least one expected {label} node is required")
    if len(values) > _MAX_NODES_PER_ENVIRONMENT:
        raise ValueError(f"Expected {label} topology exceeds the node limit")
    normalized: list[str] = []
    for value in values:
        if not isinstance(value, str) or _SAFE_IDENTIFIER_RE.fullmatch(value) is None:
            raise ValueError(f"Expected {label} node name is invalid")
        normalized.append(value)
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"Expected {label} node names must be unique")
    return frozenset(normalized)


def validate(
    args: argparse.Namespace, *, now: datetime | None = None
) -> dict[str, Any]:
    digests = {
        "panel": args.expected_panel_digest,
        "node": args.expected_node_digest,
        "subscription": args.expected_subscription_digest,
    }
    invalid_digest_names = [
        name
        for name, value in digests.items()
        if not isinstance(value, str) or _DIGEST_RE.fullmatch(value) is None
    ]
    if invalid_digest_names:
        raise ValueError(
            f"Expected digest is invalid for: {', '.join(sorted(invalid_digest_names))}"
        )
    if (
        not isinstance(args.expected_cybervpn_head, str)
        or _SAFE_IDENTIFIER_RE.fullmatch(args.expected_cybervpn_head) is None
    ):
        raise ValueError("Expected CyberVPN migration head is invalid")

    bindings = {
        "staging": args.expected_staging_binding_sha256,
        "production": args.expected_production_binding_sha256,
    }
    if any(not _valid_fingerprint(value) for value in bindings.values()):
        raise ValueError("Expected environment binding fingerprints are invalid")
    if hmac.compare_digest(bindings["staging"], bindings["production"]):
        raise ValueError("Staging and production environment bindings must differ")

    expected_nodes = {
        "staging": _expected_nodes(args.expected_staging_node, label="staging"),
        "production": _expected_nodes(
            args.expected_production_node, label="production"
        ),
    }
    max_age_minutes = args.max_age_minutes
    if (
        type(max_age_minutes) is not int
        or max_age_minutes < 1
        or max_age_minutes > _MAX_ALLOWED_AGE_MINUTES
    ):
        raise ValueError(
            f"max-age-minutes must be between 1 and {_MAX_ALLOWED_AGE_MINUTES}"
        )
    max_age = timedelta(minutes=max_age_minutes)
    validation_time = now or datetime.now(timezone.utc)
    if validation_time.tzinfo is None or validation_time.utcoffset() is None:
        raise ValueError("Validation time must include a timezone")
    validation_time = validation_time.astimezone(timezone.utc)

    if not isinstance(args.inventory, list) or len(args.inventory) != 2:
        return {
            "status": "blocked",
            "schema_version": _SCHEMA_VERSION,
            "environments": [],
            "error_count": 1,
            "errors": ["exactly one staging and one production inventory are required"],
        }
    inventories = [_load(path) for path in args.inventory]
    environments = [item.get("environment") for item in inventories]
    known_environments = sorted(
        value for value in environments if _is_required_environment(value)
    )
    errors: list[str] = []
    if (
        len(inventories) != 2
        or len(known_environments) != 2
        or set(known_environments) != _REQUIRED_ENVIRONMENTS
    ):
        errors.append("exactly one staging and one production inventory are required")

    collected_by_environment: dict[str, datetime] = {}
    for inventory in inventories:
        environment = inventory.get("environment")
        environment_key = environment if isinstance(environment, str) else ""
        expected_binding = bindings.get(environment_key)
        environment_nodes = expected_nodes.get(environment_key, frozenset())
        inventory_errors, collected_at = _validate_inventory(
            inventory,
            expected_panel_digest=digests["panel"],
            expected_node_digest=digests["node"],
            expected_subscription_digest=digests["subscription"],
            expected_cybervpn_head=args.expected_cybervpn_head,
            expected_binding_sha256=expected_binding,
            expected_node_names=environment_nodes,
            now=validation_time,
            max_age=max_age,
        )
        errors.extend(inventory_errors)
        if _is_required_environment(environment) and collected_at is not None:
            if environment in collected_by_environment:
                errors.append(f"{environment}: duplicate inventory")
            else:
                collected_by_environment[environment] = collected_at

    if set(collected_by_environment) == _REQUIRED_ENVIRONMENTS:
        pair_skew = abs(
            collected_by_environment["staging"] - collected_by_environment["production"]
        )
        if pair_skew > _MAX_PAIR_SKEW:
            errors.append(
                "staging and production inventory collection skew is too large"
            )

    return {
        "status": "pass" if not errors else "blocked",
        "schema_version": _SCHEMA_VERSION,
        "environments": known_environments,
        "error_count": len(errors),
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate fresh, environment-bound Remnawave 2.8 baselines"
    )
    parser.add_argument("--inventory", type=Path, action="append", required=True)
    parser.add_argument("--expected-panel-digest", required=True)
    parser.add_argument("--expected-node-digest", required=True)
    parser.add_argument("--expected-subscription-digest", required=True)
    parser.add_argument("--expected-staging-binding-sha256", required=True)
    parser.add_argument("--expected-production-binding-sha256", required=True)
    parser.add_argument("--expected-staging-node", action="append", required=True)
    parser.add_argument("--expected-production-node", action="append", required=True)
    parser.add_argument("--max-age-minutes", type=int, default=_DEFAULT_MAX_AGE_MINUTES)
    parser.add_argument("--expected-cybervpn-head", default="20260711_plan_code_len")
    args = parser.parse_args()
    try:
        result = validate(args)
    except (
        OSError,
        ValueError,
        TypeError,
        RecursionError,
        json.JSONDecodeError,
    ) as exc:
        result = {
            "status": "blocked",
            "schema_version": _SCHEMA_VERSION,
            "error_count": 1,
            "errors": [str(exc)],
        }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
