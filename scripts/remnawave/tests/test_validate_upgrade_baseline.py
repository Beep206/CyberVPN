from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "validate-upgrade-baseline.py"
SPEC = importlib.util.spec_from_file_location("validate_upgrade_baseline", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

NOW = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)
PANEL_DIGEST = "sha256:" + "1" * 64
NODE_DIGEST = "sha256:" + "2" * 64
SUBSCRIPTION_DIGEST = "sha256:" + "3" * 64
BINDINGS = {"staging": "4" * 64, "production": "5" * 64}
NODES = {
    "staging": ["staging-node-a", "staging-node-b"],
    "production": ["production-node-a", "production-node-b"],
}
PARITY_GROUPS = {
    "users",
    "mappings",
    "nodes",
    "hosts",
    "profiles",
    "squads",
    "plugins",
    "hwids",
}


def _set_sha256(values: list[str]) -> str:
    canonical = json.dumps(
        sorted(values), ensure_ascii=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _parity_record(count: int, fingerprint: str) -> dict[str, object]:
    return {
        "authoritative_count": count,
        "observed_count": count,
        "authoritative_set_sha256": fingerprint,
        "observed_set_sha256": fingerprint,
        "count_parity": True,
        "identity_parity": True,
    }


def _inventory(environment: str) -> dict[str, Any]:
    node_names = NODES[environment]
    node_fingerprint = _set_sha256(node_names)
    state_parity = {
        group: _parity_record(2, _fingerprint(f"{environment}:{group}"))
        for group in PARITY_GROUPS
    }
    state_parity["nodes"] = _parity_record(len(node_names), node_fingerprint)
    migration_fingerprint = _fingerprint(f"{environment}:migrations")
    collected_at = NOW - (
        timedelta(minutes=10) if environment == "staging" else timedelta(minutes=8)
    )
    return {
        "schema_version": 2,
        "environment": environment,
        "environment_binding_sha256": BINDINGS[environment],
        "collection_mode": "read_only",
        "sanitized": True,
        "contains_secret_values": False,
        "collected_at": collected_at.isoformat(),
        "panel": {
            "version": "2.8.0",
            "image_digest": PANEL_DIGEST,
            "auth_secret_sha256": "6" * 64,
            "source_metadata": {
                "image_ref": "cybervpn/remnawave-backend:2.8.0-raw-vision-flow.2",
                "source_commit": "7" * 40,
                "build_record_sha256": "8" * 64,
            },
        },
        "nodes": [
            {
                "name": name,
                "version": "2.8.0",
                "image_digest": NODE_DIGEST,
                "runtime_secret_key_sha256": str(index + 1) * 64,
                "panel_secret_key_sha256": str(index + 1) * 64,
            }
            for index, name in enumerate(node_names)
        ],
        "subscription_page": {
            "version": "7.2.6",
            "image_digest": SUBSCRIPTION_DIGEST,
        },
        "migrations": {
            "cybervpn_alembic_head": "20260711_plan_code_len",
            "remnawave_pending": 0,
            "remnawave_failed": False,
            "remnawave_applied_count": 42,
            "remnawave_expected_count": 42,
            "remnawave_applied_set_sha256": migration_fingerprint,
            "remnawave_expected_set_sha256": migration_fingerprint,
            "parity": True,
        },
        "topology": {
            "expected_node_count": len(node_names),
            "observed_node_count": len(node_names),
            "expected_node_names_sha256": node_fingerprint,
            "observed_node_names_sha256": node_fingerprint,
            "parity": True,
        },
        "state_parity": state_parity,
    }


def _write_inventories(tmp_path: Path, inventories: list[dict[str, Any]]) -> list[Path]:
    paths: list[Path] = []
    for index, inventory in enumerate(inventories):
        path = tmp_path / f"{index}-{inventory.get('environment', 'unknown')}.json"
        path.write_text(json.dumps(inventory), encoding="utf-8")
        paths.append(path)
    return paths


def _args(paths: list[Path], **overrides: object) -> argparse.Namespace:
    values: dict[str, object] = {
        "inventory": paths,
        "expected_panel_digest": PANEL_DIGEST,
        "expected_node_digest": NODE_DIGEST,
        "expected_subscription_digest": SUBSCRIPTION_DIGEST,
        "expected_staging_binding_sha256": BINDINGS["staging"],
        "expected_production_binding_sha256": BINDINGS["production"],
        "expected_staging_node": NODES["staging"],
        "expected_production_node": NODES["production"],
        "max_age_minutes": 60,
        "expected_cybervpn_head": "20260711_plan_code_len",
    }
    values.update(overrides)
    return argparse.Namespace(**values)


def _set_path(
    target: dict[str, Any], path: tuple[str | int, ...], value: object
) -> None:
    cursor: Any = target
    for key in path[:-1]:
        cursor = cursor[key]
    cursor[path[-1]] = value


def _validate_pair(
    tmp_path: Path, inventories: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    selected = inventories or [_inventory("staging"), _inventory("production")]
    return MODULE.validate(_args(_write_inventories(tmp_path, selected)), now=NOW)


def test_two_fresh_environment_bound_complete_inventories_pass(tmp_path: Path) -> None:
    result = _validate_pair(tmp_path)

    assert result == {
        "status": "pass",
        "schema_version": 2,
        "environments": ["production", "staging"],
        "error_count": 0,
        "errors": [],
    }


@pytest.mark.parametrize(
    ("field_path", "value", "expected_error"),
    [
        (("schema_version",), 1, "unsupported inventory schema_version"),
        (("schema_version",), 2.0, "unsupported inventory schema_version"),
        (("panel", "version"), "3.4.2", "panel version mismatch"),
        (
            ("panel", "image_digest"),
            "sha256:" + "9" * 64,
            "panel digest mismatch",
        ),
        (
            ("panel", "auth_secret_sha256"),
            "not-a-fingerprint",
            "auth secret continuity fingerprint",
        ),
        (
            ("panel", "source_metadata", "build_record_sha256"),
            "invalid",
            "build record fingerprint",
        ),
        (
            ("nodes", 0, "runtime_secret_key_sha256"),
            "invalid",
            "SECRET_KEY fingerprints",
        ),
        (
            ("nodes", 0, "panel_secret_key_sha256"),
            "9" * 64,
            "SECRET_KEY differs",
        ),
        (("migrations", "remnawave_pending"), 1, "pending migrations"),
        (("migrations", "remnawave_pending"), False, "pending migrations"),
        (
            ("migrations", "remnawave_expected_count"),
            43,
            "migration count parity mismatch",
        ),
        (
            ("migrations", "remnawave_expected_set_sha256"),
            "9" * 64,
            "migration set parity mismatch",
        ),
        (
            ("state_parity", "users", "observed_count"),
            3,
            "users count parity mismatch",
        ),
        (
            ("state_parity", "users", "observed_set_sha256"),
            "9" * 64,
            "users identity parity mismatch",
        ),
        (
            ("state_parity", "users", "identity_parity"),
            False,
            "users identity parity is not affirmed",
        ),
        (
            ("topology", "observed_node_names_sha256"),
            "9" * 64,
            "observed topology fingerprint mismatch",
        ),
        (
            ("topology", "expected_node_count"),
            2.0,
            "expected topology node count mismatch",
        ),
        (
            ("environment_binding_sha256",),
            "9" * 64,
            "environment binding mismatch",
        ),
    ],
)
def test_any_baseline_mismatch_blocks(
    tmp_path: Path,
    field_path: tuple[str | int, ...],
    value: object,
    expected_error: str,
) -> None:
    inventories = [_inventory("staging"), _inventory("production")]
    _set_path(inventories[0], field_path, value)

    result = _validate_pair(tmp_path, inventories)

    assert result["status"] == "blocked"
    assert any(expected_error in error for error in result["errors"])


@pytest.mark.parametrize("field", ["topology", "state_parity"])
def test_required_contract_sections_cannot_be_omitted(
    tmp_path: Path, field: str
) -> None:
    inventories = [_inventory("staging"), _inventory("production")]
    del inventories[0][field]

    result = _validate_pair(tmp_path, inventories)

    assert result["status"] == "blocked"
    assert any("required fields are missing" in error for error in result["errors"])


def test_unknown_fields_are_rejected_without_echoing_sensitive_values(
    tmp_path: Path,
) -> None:
    inventories = [_inventory("staging"), _inventory("production")]
    inventories[0]["unexpected_secret"] = "must-not-appear-in-output"

    result = _validate_pair(tmp_path, inventories)

    serialized = json.dumps(result)
    assert result["status"] == "blocked"
    assert "unsupported fields are present" in serialized
    assert "must-not-appear-in-output" not in serialized
    assert "unexpected_secret" not in serialized


def test_duplicate_json_object_keys_are_rejected(tmp_path: Path) -> None:
    path = tmp_path / "duplicate.json"
    path.write_text(
        '{"environment":"staging","environment":"production"}',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate JSON object keys"):
        MODULE._load(path)


def test_non_string_environment_fails_closed(tmp_path: Path) -> None:
    inventories = [_inventory("staging"), _inventory("production")]
    inventories[0]["environment"] = []

    result = _validate_pair(tmp_path, inventories)

    assert result["status"] == "blocked"
    assert any(
        "environment must be staging or production" in error
        for error in result["errors"]
    )


def test_missing_or_extra_expected_node_blocks_complete_topology(
    tmp_path: Path,
) -> None:
    paths = _write_inventories(
        tmp_path, [_inventory("staging"), _inventory("production")]
    )
    args = _args(
        paths,
        expected_staging_node=[*NODES["staging"], "staging-node-c"],
    )

    result = MODULE.validate(args, now=NOW)

    assert result["status"] == "blocked"
    assert any(
        "complete expected node topology mismatch" in error
        for error in result["errors"]
    )


def test_node_parity_must_agree_with_recomputed_topology(tmp_path: Path) -> None:
    inventories = [_inventory("staging"), _inventory("production")]
    inventories[0]["state_parity"]["nodes"] = _parity_record(2, "9" * 64)

    result = _validate_pair(tmp_path, inventories)

    assert result["status"] == "blocked"
    assert any(
        "nodes state parity disagrees with topology" in error
        for error in result["errors"]
    )


def test_stale_inventory_blocks(tmp_path: Path) -> None:
    inventories = [_inventory("staging"), _inventory("production")]
    inventories[0]["collected_at"] = (NOW - timedelta(minutes=61)).isoformat()

    result = _validate_pair(tmp_path, inventories)

    assert result["status"] == "blocked"
    assert any("inventory is stale" in error for error in result["errors"])


def test_timestamp_too_far_in_future_blocks(tmp_path: Path) -> None:
    inventories = [_inventory("staging"), _inventory("production")]
    inventories[0]["collected_at"] = (NOW + timedelta(minutes=6)).isoformat()

    result = _validate_pair(tmp_path, inventories)

    assert result["status"] == "blocked"
    assert any("too far in the future" in error for error in result["errors"])


def test_cross_environment_collection_skew_blocks(tmp_path: Path) -> None:
    inventories = [_inventory("staging"), _inventory("production")]
    inventories[0]["collected_at"] = (NOW - timedelta(minutes=50)).isoformat()
    inventories[1]["collected_at"] = (NOW - timedelta(minutes=5)).isoformat()

    result = _validate_pair(tmp_path, inventories)

    assert result["status"] == "blocked"
    assert any("collection skew is too large" in error for error in result["errors"])


def test_configured_freshness_window_remains_bounded(tmp_path: Path) -> None:
    paths = _write_inventories(
        tmp_path, [_inventory("staging"), _inventory("production")]
    )

    with pytest.raises(ValueError, match="max-age-minutes must be between"):
        MODULE.validate(_args(paths, max_age_minutes=361), now=NOW)


def test_environment_bindings_must_be_distinct(tmp_path: Path) -> None:
    paths = _write_inventories(
        tmp_path, [_inventory("staging"), _inventory("production")]
    )

    with pytest.raises(ValueError, match="environment bindings must differ"):
        MODULE.validate(
            _args(
                paths,
                expected_production_binding_sha256=BINDINGS["staging"],
            ),
            now=NOW,
        )


def test_cli_returns_blocking_exit_code_for_unfilled_example(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    example = SCRIPT.parent / "baseline-inventory.example.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(SCRIPT),
            "--inventory",
            str(example),
            "--inventory",
            str(example),
            "--expected-panel-digest",
            PANEL_DIGEST,
            "--expected-node-digest",
            NODE_DIGEST,
            "--expected-subscription-digest",
            SUBSCRIPTION_DIGEST,
            "--expected-staging-binding-sha256",
            BINDINGS["staging"],
            "--expected-production-binding-sha256",
            BINDINGS["production"],
            "--expected-staging-node",
            NODES["staging"][0],
            "--expected-production-node",
            NODES["production"][0],
        ],
    )

    exit_code = MODULE.main()
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 2
    assert output["status"] == "blocked"
    assert output["error_count"] > 0
