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
TASK2_ALLOWLIST_DESCRIPTION = (
    "Task2 contract field names and synthetic test values are not credentials"
)
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


def _iter_allowlists(config: Mapping[str, Any]) -> Iterator[Mapping[str, Any]]:
    yield from config.get("allowlists", [])
    for rule in config.get("rules", []):
        yield from rule.get("allowlists", [])


def validate_gitleaks_config(config_path: Path = CONFIG_PATH) -> None:
    with config_path.open("rb") as config_file:
        config = tomllib.load(config_file)

    allowlists = list(_iter_allowlists(config))
    for allowlist in allowlists:
        for pattern in allowlist.get("paths", []):
            if not pattern.startswith("^") or not pattern.endswith("$"):
                raise ValueError(f"Gitleaks allowlist path must be anchored: {pattern}")

    task2_allowlists = [
        allowlist
        for allowlist in allowlists
        if allowlist.get("description") == TASK2_ALLOWLIST_DESCRIPTION
    ]
    if len(task2_allowlists) != 1:
        raise ValueError("Exactly one Task2 Gitleaks allowlist is required")

    expected_patterns = {f"^{re.escape(path)}$" for path in TASK2_ALLOWED_PATHS}
    configured_patterns = set(task2_allowlists[0].get("paths", []))
    if configured_patterns != expected_patterns:
        raise ValueError(
            "Task2 Gitleaks allowlist paths differ from the reviewed exact set"
        )

    for path in TASK2_ALLOWED_PATHS:
        pattern = re.compile(f"^{re.escape(path)}$")
        if pattern.fullmatch(path) is None:
            raise ValueError(
                f"Task2 Gitleaks allowlist does not match its exact path: {path}"
            )
        if (
            pattern.fullmatch(f"{path}.bak") is not None
            or pattern.fullmatch(f"tmp/{path}") is not None
        ):
            raise ValueError(
                f"Task2 Gitleaks allowlist accepts a near-miss path: {path}"
            )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate the repository Gitleaks allowlist policy."
    )
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
