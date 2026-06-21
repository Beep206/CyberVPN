from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, NoReturn

STATUS_MARKER = re.compile(
    r"\A\s*TASK_STATUS:\s*(VERIFIED|PARTIAL|BLOCKED)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
REQUIRED_SECTIONS = (
    "Acceptance criteria",
    "Validation",
    "Review",
    "Unresolved",
    "Changed files",
)
SETUP_ALLOWED_PREFIXES = (
    ".agents/skills/",
    ".agents/plugins/",
    "plugins/cybervpn-autonomous-team/",
    ".codex/",
    "docs/codex/",
    "scripts/codex/",
)
SETUP_ALLOWED_FILES = {
    ".gitignore",
    "AGENTS.md",
    "backend/AGENTS.md",
    "frontend/AGENTS.md",
    "admin/AGENTS.md",
    "partner/AGENTS.md",
    "cybervpn_mobile/AGENTS.md",
    "apps/desktop-client/AGENTS.md",
    "services/AGENTS.md",
    "packages/AGENTS.md",
    "infra/AGENTS.md",
}


def emit(payload: dict[str, Any]) -> NoReturn:
    print(json.dumps(payload, ensure_ascii=False))
    raise SystemExit(0)


def stop_or_continue(issues: list[str], already_continued: bool) -> NoReturn:
    reason = (
        "CyberVPN completion gate failed:\n- "
        + "\n- ".join(issues)
        + "\nContinue implementation and validation. If completion is impossible, set the contract and "
        "final marker to PARTIAL or BLOCKED and list exact unresolved criteria."
    )
    if already_continued:
        emit(
            {
                "continue": False,
                "stopReason": reason,
                "systemMessage": reason,
            }
        )
    emit({"decision": "block", "reason": reason})


def git_root(cwd: str | None) -> Path | None:
    try:
        return Path(
            subprocess.check_output(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=cwd or None,
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def changed_paths(root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    paths: list[str] = []
    for raw_line in result.stdout.splitlines():
        if len(raw_line) < 4:
            continue
        value = raw_line[3:].strip()
        if " -> " in value:
            value = value.split(" -> ", 1)[1]
        paths.append(value.strip('"'))
    return paths


def is_setup_path(path: str) -> bool:
    return path in SETUP_ALLOWED_FILES or any(path.startswith(prefix) for prefix in SETUP_ALLOWED_PREFIXES)


def preexisting_dirty_paths(contract: dict[str, Any]) -> set[str]:
    raw_paths = contract.get("preexisting_dirty_paths", [])
    if not isinstance(raw_paths, list):
        return set()
    return {str(path) for path in raw_paths if isinstance(path, str) and path}


def evidence_present(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return bool(value)
    if isinstance(value, dict):
        return bool(value)
    return False


def main() -> None:
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, TypeError):
        emit({"continue": True})

    root = git_root(str(hook_input.get("cwd") or "") or None)
    if root is None:
        emit({"continue": True})

    dirty = changed_paths(root)
    if not dirty:
        emit({"continue": True})

    already_continued = bool(hook_input.get("stop_hook_active"))
    last_message = str(hook_input.get("last_assistant_message") or "")
    contract_path = root / ".codex" / "current-task.json"
    issues: list[str] = []

    if not contract_path.exists():
        stop_or_continue(
            [
                "The working tree is dirty but .codex/current-task.json is missing.",
                "Create a task contract with scripts/codex/init-task.sh and record acceptance criteria/validation.",
            ],
            already_continued,
        )

    try:
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        stop_or_continue([f"Invalid .codex/current-task.json: {error}"], already_continued)

    task_id = str(contract.get("task_id") or "")
    contract_status = str(contract.get("status") or "in_progress").lower()

    if task_id == "SETUP-BOOTSTRAP":
        baseline_dirty = preexisting_dirty_paths(contract)
        non_setup = [
            path
            for path in dirty
            if not is_setup_path(path) and path not in baseline_dirty
        ]
        if non_setup:
            issues.append(
                "SETUP-BOOTSTRAP contract is stale because non-setup files changed: "
                + ", ".join(non_setup[:10])
            )

    marker = STATUS_MARKER.match(last_message)
    if marker is None:
        issues.append("Final response must begin with TASK_STATUS: VERIFIED, PARTIAL, or BLOCKED on its own line.")
        response_status = None
    else:
        response_status = marker.group(1).lower()

    if contract_status not in {"verified", "partial", "blocked"}:
        issues.append(
            f"Task contract status is {contract_status!r}; it must be verified, partial, or blocked before stopping."
        )
    elif response_status != contract_status:
        issues.append(
            f"Response status {response_status!r} does not match contract status {contract_status!r}."
        )

    criteria = contract.get("acceptance_criteria")
    validations = contract.get("validations")
    reviews = contract.get("reviews")
    unresolved = contract.get("unresolved")

    if not isinstance(criteria, list) or not criteria:
        issues.append("Task contract has no acceptance criteria.")
        criteria = []
    if not isinstance(validations, list):
        issues.append("Task contract validations must be an array.")
        validations = []
    if not isinstance(reviews, list):
        reviews = []
    if not isinstance(unresolved, list):
        issues.append("Task contract unresolved must be an array.")
        unresolved = []

    if contract_status == "verified":
        for criterion in criteria:
            if not isinstance(criterion, dict):
                issues.append("Acceptance criterion entry is not an object.")
                continue
            criterion_id = str(criterion.get("id") or "unknown")
            if str(criterion.get("status") or "pending").lower() != "pass":
                issues.append(f"{criterion_id} is not PASS.")
            if not evidence_present(criterion.get("implementation_evidence")):
                issues.append(f"{criterion_id} has no implementation evidence.")
            if not evidence_present(criterion.get("test_evidence")):
                issues.append(f"{criterion_id} has no test/runtime evidence.")

        for validation in validations:
            if not isinstance(validation, dict):
                issues.append("Validation entry is not an object.")
                continue
            if not validation.get("required", True):
                continue
            command = str(validation.get("command") or "unknown command")
            if str(validation.get("status") or "not_run").lower() != "pass":
                issues.append(f"Required validation did not pass: {command}.")
            if validation.get("exit_code") != 0:
                issues.append(f"Validation marked PASS without exit code 0: {command}.")
            if not evidence_present(validation.get("evidence")):
                issues.append(f"Validation has no evidence: {command}.")

        required_reviewers = {"verifier", "adversarial_reviewer"}
        passed_reviewers = {
            str(review.get("agent") or "")
            for review in reviews
            if isinstance(review, dict) and str(review.get("status") or "").lower() == "pass"
        }
        missing_reviews = sorted(required_reviewers - passed_reviewers)
        if missing_reviews and task_id != "SETUP-BOOTSTRAP":
            issues.append("Missing passing independent reviews: " + ", ".join(missing_reviews) + ".")

        if unresolved:
            issues.append("VERIFIED task still contains unresolved items.")

    if contract_status in {"partial", "blocked"} and not unresolved:
        issues.append(f"{contract_status.upper()} task must list exact unresolved items.")

    for section in REQUIRED_SECTIONS:
        if section.lower() not in last_message.lower():
            issues.append(f"Final response is missing section: {section}.")

    if issues:
        stop_or_continue(issues, already_continued)

    emit({"continue": True})


if __name__ == "__main__":
    main()
