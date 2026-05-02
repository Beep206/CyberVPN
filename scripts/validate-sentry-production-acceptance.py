#!/usr/bin/env python3
"""Validate the repo-local Sentry production acceptance registry."""

from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ACCEPTANCE_PATH = ROOT / "docs/observability/sentry/production-acceptance-registry.json"
GOVERNANCE_PATH = ROOT / "docs/observability/sentry/governance-registry.json"
RELEASE_PROOF_PATH = ROOT / "docs/observability/sentry/release-proof-registry.json"

ALLOWED_ACCEPTANCE_STATUSES = {
    "pending_live_sentry",
    "pending_external_deployer",
    "pending_deploy_strategy",
    "production_accepted",
}
ALLOWED_DEPLOY_MARKER_STRATEGIES = {
    "repo_workflow",
    "external_deployer",
    "not_yet_defined",
}
ALLOWED_OPEN_GATES = {
    "live_project_provisioned",
    "privacy_rules_applied_in_sentry",
    "alert_routing_applied_in_sentry",
    "deploy_marker_strategy_assigned",
    "production_smoke_verified",
    "symbolication_proved_in_live_sentry",
    "deploy_marker_verified_in_live_sentry",
    "external_deployer_confirmed",
}


def append_summary(
    summary_file: str,
    status_counts: Counter[str],
    deploy_strategy_counts: Counter[str],
    errors: list[str],
) -> None:
    if not summary_file:
        return

    path = Path(summary_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write("### Sentry Production Acceptance Validation\n\n")
        if errors:
            handle.write("- result: `failed`\n")
            for error in errors:
                handle.write(f"- error: `{error}`\n")
            handle.write("\n")
            return

        handle.write("- result: `passed`\n")
        handle.write(f"- projects: `{sum(status_counts.values())}`\n")
        for status, count in sorted(status_counts.items()):
            handle.write(f"- status `{status}`: `{count}`\n")
        for strategy, count in sorted(deploy_strategy_counts.items()):
            handle.write(f"- deploy strategy `{strategy}`: `{count}`\n")
        handle.write("\n")


def main() -> int:
    summary_file = os.environ.get("GITHUB_STEP_SUMMARY", "")

    acceptance = json.loads(ACCEPTANCE_PATH.read_text(encoding="utf-8"))
    governance = json.loads(GOVERNANCE_PATH.read_text(encoding="utf-8"))
    release_proof = json.loads(RELEASE_PROOF_PATH.read_text(encoding="utf-8"))

    errors: list[str] = []
    status_counts: Counter[str] = Counter()
    deploy_strategy_counts: Counter[str] = Counter()

    if acceptance.get("schema_version") != 1:
        errors.append("schema_version must equal 1")

    projects = acceptance.get("projects", [])
    governance_projects = {entry["project"]: entry for entry in governance.get("projects", [])}
    release_proof_by_project: dict[str, str] = {}
    for surface in release_proof.get("surfaces", []):
        for project in surface.get("release_projects", []):
            release_proof_by_project[project] = surface.get("deploy_marker_mode", "")

    seen_projects: set[str] = set()
    for entry in projects:
        project = entry.get("project", "").strip()
        surface = entry.get("surface", "").strip()
        owner_team = entry.get("owner_team", "").strip()
        acceptance_status = entry.get("acceptance_status", "").strip()
        deploy_marker_strategy = entry.get("deploy_marker_strategy", "").strip()
        open_gates = entry.get("open_gates", [])

        if not project:
            errors.append("project entry is missing `project`")
            continue
        if project in seen_projects:
            errors.append(f"duplicate project `{project}`")
            continue
        seen_projects.add(project)

        governance_entry = governance_projects.get(project)
        if governance_entry is None:
            errors.append(f"project `{project}` missing from governance-registry.json")
            continue

        if owner_team != governance_entry.get("owner_team"):
            errors.append(f"project `{project}` owner_team does not match governance registry")
        if surface != governance_entry.get("surface"):
            errors.append(f"project `{project}` surface does not match governance registry")
        if acceptance_status not in ALLOWED_ACCEPTANCE_STATUSES:
            errors.append(f"project `{project}` has invalid acceptance_status `{acceptance_status}`")
        if deploy_marker_strategy not in ALLOWED_DEPLOY_MARKER_STRATEGIES:
            errors.append(
                f"project `{project}` has invalid deploy_marker_strategy `{deploy_marker_strategy}`"
            )
        if not isinstance(open_gates, list) or any(gate not in ALLOWED_OPEN_GATES for gate in open_gates):
            errors.append(f"project `{project}` has invalid open_gates")

        if acceptance_status == "production_accepted" and open_gates:
            errors.append(f"project `{project}` cannot be production_accepted while open_gates remain")
        if acceptance_status == "pending_external_deployer" and deploy_marker_strategy != "external_deployer":
            errors.append(f"project `{project}` pending_external_deployer must use external_deployer strategy")
        if acceptance_status == "pending_deploy_strategy" and deploy_marker_strategy != "not_yet_defined":
            errors.append(f"project `{project}` pending_deploy_strategy must use not_yet_defined strategy")
        if acceptance_status == "pending_live_sentry" and deploy_marker_strategy == "not_yet_defined":
            errors.append(f"project `{project}` pending_live_sentry must have a defined deploy marker strategy")

        proof_strategy = release_proof_by_project.get(project)
        if proof_strategy and proof_strategy == "external_deployer" and deploy_marker_strategy != "external_deployer":
            errors.append(f"project `{project}` must use external_deployer strategy to match release-proof registry")
        if proof_strategy and proof_strategy == "release_workflow" and deploy_marker_strategy != "repo_workflow":
            errors.append(f"project `{project}` must use repo_workflow strategy to match release-proof registry")
        if proof_strategy and "symbolication_proved_in_live_sentry" not in open_gates and acceptance_status != "production_accepted":
            errors.append(f"project `{project}` with release-proof baseline must keep symbolication_proved_in_live_sentry as an open gate until accepted")
        if deploy_marker_strategy == "repo_workflow" and "deploy_marker_verified_in_live_sentry" not in open_gates and acceptance_status != "production_accepted":
            errors.append(f"project `{project}` with repo_workflow strategy must keep deploy_marker_verified_in_live_sentry as an open gate until accepted")
        if deploy_marker_strategy == "external_deployer" and "external_deployer_confirmed" not in open_gates and acceptance_status != "production_accepted":
            errors.append(f"project `{project}` with external_deployer strategy must keep external_deployer_confirmed as an open gate until accepted")

        status_counts[acceptance_status] += 1
        deploy_strategy_counts[deploy_marker_strategy] += 1

    missing_projects = set(governance_projects) - seen_projects
    extra_projects = seen_projects - set(governance_projects)
    if missing_projects:
        errors.append("missing projects: " + ", ".join(sorted(missing_projects)))
    if extra_projects:
        errors.append("unexpected projects: " + ", ".join(sorted(extra_projects)))

    append_summary(summary_file, status_counts, deploy_strategy_counts, errors)

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(
        "[sentry-production-acceptance] "
        f"projects={sum(status_counts.values())} "
        f"pending_live_sentry={status_counts['pending_live_sentry']} "
        f"pending_external_deployer={status_counts['pending_external_deployer']} "
        f"pending_deploy_strategy={status_counts['pending_deploy_strategy']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
