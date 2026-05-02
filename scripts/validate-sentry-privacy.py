#!/usr/bin/env python3
"""Validate the repo-local Sentry privacy baseline."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ALLOWED_ATTACHMENTS_POLICY = {"disabled_unless_explicitly_approved"}
ALLOWED_REPLAY_NETWORK_POLICY = {"opt_in_only"}
ALLOWED_SAFE_IDENTITY_POLICY = {"internal_user_id_or_hashed_telegram_id_only"}


def append_summary(summary_file: str, expectation_count: int, errors: list[str]) -> None:
    if not summary_file:
        return

    path = Path(summary_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write("### Sentry Privacy Baseline Validation\n\n")
        if errors:
            handle.write("- result: `failed`\n")
            for error in errors:
                handle.write(f"- error: `{error}`\n")
            handle.write("\n")
            return

        handle.write("- result: `passed`\n")
        handle.write(f"- code_expectations: `{expectation_count}`\n")
        handle.write("- repo_baseline: `validated`\n\n")


def main() -> int:
    baseline_path = Path("docs/observability/sentry/privacy-baseline.json")
    summary_file = os.environ.get("GITHUB_STEP_SUMMARY", "")

    payload = json.loads(baseline_path.read_text(encoding="utf-8"))
    errors: list[str] = []

    if payload.get("schema_version") != 1:
        errors.append("schema_version must equal 1")

    org_defaults = payload.get("org_defaults", {})
    if org_defaults.get("sdk_default_pii") is not False:
        errors.append("org_defaults.sdk_default_pii must be false")
    if org_defaults.get("prevent_storing_ip_addresses") is not True:
        errors.append("org_defaults.prevent_storing_ip_addresses must be true")
    if org_defaults.get("require_default_scrubbers") is not True:
        errors.append("org_defaults.require_default_scrubbers must be true")
    if org_defaults.get("attachments_policy") not in ALLOWED_ATTACHMENTS_POLICY:
        errors.append("org_defaults.attachments_policy must use the approved value")
    if org_defaults.get("replay_network_detail_policy") not in ALLOWED_REPLAY_NETWORK_POLICY:
        errors.append("org_defaults.replay_network_detail_policy must use the approved value")
    if org_defaults.get("safe_identity_policy") not in ALLOWED_SAFE_IDENTITY_POLICY:
        errors.append("org_defaults.safe_identity_policy must use the approved value")

    for key in ("scrub_headers", "scrub_field_markers", "strict_endpoint_classes", "approval_checkpoints"):
        values = payload.get(key, [])
        if not isinstance(values, list) or not values:
            errors.append(f"{key} must be a non-empty list")

    expectations = payload.get("code_expectations", [])
    if not isinstance(expectations, list) or not expectations:
        errors.append("code_expectations must be a non-empty list")

    for expectation in expectations:
        path_value = expectation.get("path", "").strip()
        required_snippets = expectation.get("must_contain", [])

        if not path_value:
            errors.append("code_expectations entry is missing `path`")
            continue
        if not isinstance(required_snippets, list) or not required_snippets:
            errors.append(f"code_expectations entry `{path_value}` has no must_contain values")
            continue

        path = Path(path_value)
        if not path.exists():
            errors.append(f"missing path `{path_value}`")
            continue

        contents = path.read_text(encoding="utf-8")
        for snippet in required_snippets:
            if snippet not in contents:
                errors.append(f"`{path_value}` is missing required snippet `{snippet}`")

    append_summary(summary_file, len(expectations), errors)

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"[sentry-privacy] expectations={len(expectations)} baseline=validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
