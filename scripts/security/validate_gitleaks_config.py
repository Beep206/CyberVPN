#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import tomllib
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPOSITORY_ROOT / ".gitleaks.toml"
GENERIC_API_KEY_RULE_ID = "generic-api-key"
TASK2_ALLOWLIST_DESCRIPTION = "Task2 contract field names and synthetic test values are not credentials"
TASK2_ALLOWLIST_REGEXES = {
    r"(?i)\b(private_key|suite_key|registry_key|bgp_secret)\b",
}
TASK2_ALLOWED_PATHS = {
    "backend/src/application/vpn_testing/route_registry/premium_spb_de_exceptions_v1.yaml",
    "backend/src/application/vpn_testing/service.py",
    "backend/src/application/vpn_testing/suites/premium_spb_de_exceptions_v1.yaml",
    "backend/tests/helpers/spb_de_readiness.py",
    "backend/tests/unit/application/vpn_testing/test_task2_runtime_fault_evidence.py",
    "backend/tests/unit/application/vpn_testing/test_task2_runtime_fault_service.py",
    "backend/tests/unit/application/vpn_testing/test_vpn_tester_service.py",
    "backend/tests/unit/infrastructure/test_vpn_tester_repository.py",
    "backend/tests/unit/presentation/api/v1/admin/test_vpn_tester_task2_runtime_fault_evidence.py",
    "infra/tests/test_antifilter_bgp_collector.py",
}
REVIEWED_GLOBAL_GENERIC_ALLOWLIST_DESCRIPTION = "Synthetic test/evidence identifiers that are not credentials"
REVIEWED_GLOBAL_GENERIC_ALLOWLIST_PATHS = {
    r"^backend/tests/e2e/test_phase4_(finance|settlement)_foundations\.py$",
    r"^docs/evidence/partner-platform/stage3-outbox.*$",
}
REVIEWED_GLOBAL_GENERIC_ALLOWLIST_REGEXES = {
    (
        r"(?i)(idempotency[-_ -]?key|period_key|event_key|dead_letter_event_key|"
        r"""backlog_event_key|partition_key)["'\s:=]+[A-Za-z0-9_.:-]{8,}"""
    ),
}


def _iter_allowlists(
    config: Mapping[str, Any],
) -> Iterator[tuple[str | None, Mapping[str, Any]]]:
    for allowlist in config.get("allowlists", []):
        yield None, allowlist
    for rule in config.get("rules", []):
        rule_id = str(rule.get("id") or "")
        for allowlist in rule.get("allowlists", []):
            yield rule_id, allowlist


def _require_exact_allowlist_shape(
    allowlist: Mapping[str, Any],
    *,
    keys: set[str],
    condition: str,
    regex_target: str,
    paths: set[str],
    regexes: set[str],
) -> None:
    if set(allowlist) != keys:
        raise ValueError("Reviewed Gitleaks allowlist keys changed")
    if allowlist.get("condition") != condition:
        raise ValueError("Reviewed Gitleaks allowlist condition changed")
    if allowlist.get("regexTarget") != regex_target:
        raise ValueError("Reviewed Gitleaks allowlist regex target changed")
    if set(allowlist.get("paths", [])) != paths:
        raise ValueError("Reviewed Gitleaks allowlist paths changed")
    if set(allowlist.get("regexes", [])) != regexes:
        raise ValueError("Reviewed Gitleaks allowlist regexes changed")


def validate_gitleaks_config(config_path: Path = CONFIG_PATH) -> None:
    with config_path.open("rb") as config_file:
        config = tomllib.load(config_file)

    if set(config) != {"title", "extend", "allowlists", "rules"}:
        raise ValueError("Gitleaks top-level configuration shape changed")
    if config.get("extend") != {"useDefault": True}:
        raise ValueError("Gitleaks default-rule extension shape changed")

    generic_rules = [rule for rule in config.get("rules", []) if rule.get("id") == GENERIC_API_KEY_RULE_ID]
    if len(generic_rules) != 1:
        raise ValueError("Exactly one generic-api-key rule extension is required")
    generic_rule = generic_rules[0]
    if set(generic_rule) != {"id", "allowlists"}:
        raise ValueError("generic-api-key rule extension shape changed")
    if len(generic_rule.get("allowlists", [])) != 1:
        raise ValueError("generic-api-key rule must contain one reviewed allowlist")

    allowlists = list(_iter_allowlists(config))
    for _, allowlist in allowlists:
        for pattern in allowlist.get("paths", []):
            if not pattern.startswith("^") or not pattern.endswith("$"):
                raise ValueError(f"Gitleaks allowlist path must be anchored: {pattern}")

    task2_allowlists = [
        (owner_rule_id, allowlist)
        for owner_rule_id, allowlist in allowlists
        if allowlist.get("description") == TASK2_ALLOWLIST_DESCRIPTION
    ]
    if len(task2_allowlists) != 1:
        raise ValueError("Exactly one Task2 Gitleaks allowlist is required")

    task2_owner_rule_id, task2_allowlist = task2_allowlists[0]
    if task2_owner_rule_id != GENERIC_API_KEY_RULE_ID:
        raise ValueError("Task2 Gitleaks allowlist must belong to generic-api-key")

    expected_patterns = {f"^{re.escape(path)}$" for path in TASK2_ALLOWED_PATHS}
    try:
        _require_exact_allowlist_shape(
            task2_allowlist,
            keys={"description", "condition", "regexTarget", "paths", "regexes"},
            condition="AND",
            regex_target="line",
            paths=expected_patterns,
            regexes=TASK2_ALLOWLIST_REGEXES,
        )
    except ValueError as exc:
        raise ValueError("Task2 Gitleaks allowlist differs from the reviewed exact shape") from exc

    reviewed_global_allowlists = [
        allowlist
        for owner_rule_id, allowlist in allowlists
        if owner_rule_id is None and allowlist.get("description") == REVIEWED_GLOBAL_GENERIC_ALLOWLIST_DESCRIPTION
    ]
    if len(reviewed_global_allowlists) != 1:
        raise ValueError("Exactly one reviewed global generic-api-key allowlist is required")
    reviewed_global_allowlist = reviewed_global_allowlists[0]
    if set(reviewed_global_allowlist.get("targetRules", [])) != {GENERIC_API_KEY_RULE_ID}:
        raise ValueError("Reviewed global allowlist target rules changed")
    _require_exact_allowlist_shape(
        reviewed_global_allowlist,
        keys={
            "description",
            "targetRules",
            "condition",
            "regexTarget",
            "paths",
            "regexes",
        },
        condition="AND",
        regex_target="match",
        paths=REVIEWED_GLOBAL_GENERIC_ALLOWLIST_PATHS,
        regexes=REVIEWED_GLOBAL_GENERIC_ALLOWLIST_REGEXES,
    )

    for owner_rule_id, allowlist in allowlists:
        target_rules = set(allowlist.get("targetRules", []))
        affects_generic_api_key = owner_rule_id == GENERIC_API_KEY_RULE_ID or (
            owner_rule_id is None and (not target_rules or GENERIC_API_KEY_RULE_ID in target_rules)
        )
        if not affects_generic_api_key:
            continue
        if allowlist is task2_allowlist or allowlist is reviewed_global_allowlist:
            continue
        raise ValueError("Unreviewed generic-api-key allowlist is forbidden")

    for path in TASK2_ALLOWED_PATHS:
        pattern = re.compile(f"^{re.escape(path)}$")
        if pattern.fullmatch(path) is None:
            raise ValueError(f"Task2 Gitleaks allowlist does not match its exact path: {path}")
        if pattern.fullmatch(f"{path}.bak") is not None or pattern.fullmatch(f"tmp/{path}") is not None:
            raise ValueError(f"Task2 Gitleaks allowlist accepts a near-miss path: {path}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the repository Gitleaks allowlist policy.")
    parser.add_argument(
        "--config",
        type=Path,
        default=CONFIG_PATH,
        help="Path to the Gitleaks TOML file.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    validate_gitleaks_config(_parse_args().config)
    print("Gitleaks config policy OK")
