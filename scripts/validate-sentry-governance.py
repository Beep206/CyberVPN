#!/usr/bin/env python3
"""Validate the repo-local Sentry governance registry."""

from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path

EXPECTED_PROJECTS = {
    "web-frontend",
    "web-admin",
    "web-partner",
    "backend-api",
    "task-worker",
    "cybervpn-mobile",
    "telegram-bot",
    "desktop-renderer",
    "desktop-native",
    "android-tv",
    "node-fleet-controller",
    "helix-adapter",
    "helix-node",
}
ALLOWED_TEAMS = {"web", "core", "client-apps", "platform"}
ALLOWED_CHANNELS = {"github", "email", "production-ops"}
ALLOWED_PRODUCTION_TIERS = {"prod_critical", "prod_standard"}
ALLOWED_STAGING_TIERS = {"staging_release_blocker", "staging_minimal"}
ALLOWED_APPLY_STATUS = {"planned_in_sentry", "implemented_in_sentry"}


def append_summary(
    summary_file: str,
    team_counts: Counter[str],
    critical_count: int,
    pending_apply_count: int,
    errors: list[str],
) -> None:
    if not summary_file:
        return

    path = Path(summary_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write("### Sentry Governance Registry Validation\n\n")
        if errors:
            handle.write("- result: `failed`\n")
            for error in errors:
                handle.write(f"- error: `{error}`\n")
            handle.write("\n")
            return

        handle.write("- result: `passed`\n")
        handle.write(f"- projects: `{sum(team_counts.values())}`\n")
        handle.write(f"- prod_critical_projects: `{critical_count}`\n")
        handle.write(f"- planned_in_sentry: `{pending_apply_count}`\n")
        for team, count in sorted(team_counts.items()):
            handle.write(f"- team `{team}`: `{count}`\n")
        handle.write("\n")


def main() -> int:
    registry_path = Path("docs/observability/sentry/governance-registry.json")
    summary_file = os.environ.get("GITHUB_STEP_SUMMARY", "")

    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    projects = payload.get("projects", [])

    errors: list[str] = []
    seen_projects: set[str] = set()
    team_counts: Counter[str] = Counter()
    critical_count = 0
    pending_apply_count = 0

    if payload.get("schema_version") != 1:
        errors.append("schema_version must equal 1")

    if set(payload.get("logical_teams", [])) != ALLOWED_TEAMS:
        errors.append("logical_teams must exactly match the allowed logical team set")

    declared_channels = set(payload.get("allowed_channels", []))
    if declared_channels != ALLOWED_CHANNELS:
        errors.append("allowed_channels must exactly match the allowed channel set")

    for entry in projects:
        project = entry.get("project", "").strip()
        team = entry.get("owner_team", "").strip()
        prod_tier = entry.get("production_alert_tier", "").strip()
        staging_tier = entry.get("staging_alert_tier", "").strip()
        apply_status = entry.get("apply_status", "").strip()
        prod_channels = set(entry.get("production_channels", []))
        staging_channels = set(entry.get("staging_channels", []))

        if not project:
            errors.append("project entry is missing `project`")
            continue
        if project in seen_projects:
            errors.append(f"duplicate project `{project}`")
            continue
        seen_projects.add(project)

        if team not in ALLOWED_TEAMS:
            errors.append(f"project `{project}` has invalid owner_team `{team}`")
        if prod_tier not in ALLOWED_PRODUCTION_TIERS:
            errors.append(
                f"project `{project}` has invalid production_alert_tier `{prod_tier}`"
            )
        if staging_tier not in ALLOWED_STAGING_TIERS:
            errors.append(
                f"project `{project}` has invalid staging_alert_tier `{staging_tier}`"
            )
        if apply_status not in ALLOWED_APPLY_STATUS:
            errors.append(f"project `{project}` has invalid apply_status `{apply_status}`")
        if not prod_channels or not prod_channels.issubset(ALLOWED_CHANNELS):
            errors.append(f"project `{project}` has invalid production_channels")
        if not staging_channels or not staging_channels.issubset(ALLOWED_CHANNELS):
            errors.append(f"project `{project}` has invalid staging_channels")
        if entry.get("routing_basis") != "project-first":
            errors.append(f"project `{project}` must use routing_basis `project-first`")

        team_counts[team] += 1
        if prod_tier == "prod_critical":
            critical_count += 1
        if apply_status == "planned_in_sentry":
            pending_apply_count += 1

    missing_projects = EXPECTED_PROJECTS - seen_projects
    extra_projects = seen_projects - EXPECTED_PROJECTS
    if missing_projects:
        errors.append(
            "missing projects: " + ", ".join(sorted(missing_projects))
        )
    if extra_projects:
        errors.append(
            "unexpected projects: " + ", ".join(sorted(extra_projects))
        )

    append_summary(summary_file, team_counts, critical_count, pending_apply_count, errors)

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(
        "[sentry-governance] "
        f"projects={sum(team_counts.values())} "
        f"prod_critical={critical_count} "
        f"planned_in_sentry={pending_apply_count}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
