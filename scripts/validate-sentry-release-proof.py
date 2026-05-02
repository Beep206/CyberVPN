#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = ROOT / "docs/observability/sentry/release-proof-registry.json"

ALLOWED_DEPLOY_MARKER_MODES = {"release_workflow", "external_deployer"}


def fail(message: str) -> None:
    print(f"[sentry-release-proof] ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def ensure(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def load_registry() -> dict:
    try:
        return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        fail(f"registry not found: {exc}")
    except json.JSONDecodeError as exc:
        fail(f"invalid JSON: {exc}")


def validate_registry(data: dict) -> list[dict]:
    ensure(data.get("schema_version") == 1, "schema_version must be 1")
    ensure(isinstance(data.get("last_updated"), str) and data["last_updated"], "last_updated must be a non-empty string")
    surfaces = data.get("surfaces")
    ensure(isinstance(surfaces, list) and surfaces, "surfaces must be a non-empty array")

    seen_names: set[str] = set()
    for index, surface in enumerate(surfaces, start=1):
        prefix = f"surfaces[{index}]"
        name = surface.get("surface")
        ensure(isinstance(name, str) and name, f"{prefix}.surface must be a non-empty string")
        ensure(name not in seen_names, f"duplicate surface entry: {name}")
        seen_names.add(name)

        workflow = surface.get("workflow")
        ensure(isinstance(workflow, str) and workflow, f"{prefix}.workflow must be a non-empty string")
        ensure((ROOT / workflow).exists(), f"{prefix}.workflow does not exist: {workflow}")

        release_projects = surface.get("release_projects")
        ensure(
            isinstance(release_projects, list)
            and release_projects
            and all(isinstance(project, str) and project for project in release_projects),
            f"{prefix}.release_projects must be a non-empty string array",
        )

        deploy_marker_mode = surface.get("deploy_marker_mode")
        ensure(
            deploy_marker_mode in ALLOWED_DEPLOY_MARKER_MODES,
            f"{prefix}.deploy_marker_mode must be one of {sorted(ALLOWED_DEPLOY_MARKER_MODES)}",
        )

        required_evidence_labels = surface.get("required_evidence_labels")
        ensure(
            isinstance(required_evidence_labels, list)
            and required_evidence_labels
            and all(isinstance(label, str) and label for label in required_evidence_labels),
            f"{prefix}.required_evidence_labels must be a non-empty string array",
        )

        code_expectations = surface.get("code_expectations")
        ensure(isinstance(code_expectations, list) and code_expectations, f"{prefix}.code_expectations must be a non-empty array")
        for exp_index, expectation in enumerate(code_expectations, start=1):
            exp_prefix = f"{prefix}.code_expectations[{exp_index}]"
            path = expectation.get("path")
            ensure(isinstance(path, str) and path, f"{exp_prefix}.path must be a non-empty string")
            file_path = ROOT / path
            ensure(file_path.exists(), f"{exp_prefix}.path does not exist: {path}")
            must_contain = expectation.get("must_contain")
            ensure(
                isinstance(must_contain, list)
                and must_contain
                and all(isinstance(snippet, str) and snippet for snippet in must_contain),
                f"{exp_prefix}.must_contain must be a non-empty string array",
            )

    return surfaces


def validate_expectations(surfaces: list[dict]) -> int:
    checked = 0
    for surface in surfaces:
        for expectation in surface["code_expectations"]:
            file_path = ROOT / expectation["path"]
            content = file_path.read_text(encoding="utf-8")
            for snippet in expectation["must_contain"]:
                ensure(snippet in content, f"missing snippet in {expectation['path']}: {snippet}")
                checked += 1
    return checked


def write_summary(surface_count: int, snippet_count: int) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return

    with open(summary_path, "a", encoding="utf-8") as summary:
        summary.write("### Sentry release proof validation\n")
        summary.write(f"- Registry: `{REGISTRY_PATH.relative_to(ROOT)}`\n")
        summary.write(f"- Surfaces: `{surface_count}`\n")
        summary.write(f"- Snippet checks: `{snippet_count}`\n")


def main() -> None:
    registry = load_registry()
    surfaces = validate_registry(registry)
    snippet_count = validate_expectations(surfaces)
    write_summary(len(surfaces), snippet_count)
    print(f"[sentry-release-proof] surfaces={len(surfaces)} snippet_checks={snippet_count} validated")


if __name__ == "__main__":
    main()
