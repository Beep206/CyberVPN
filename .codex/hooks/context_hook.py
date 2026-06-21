from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False))


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


def task_summary(path: Path) -> str:
    if not path.exists():
        return "No current task contract exists yet. Create .codex/current-task.json before non-trivial edits."

    try:
        task = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return f"The current task contract is invalid and must be repaired: {error}."

    criteria = task.get("acceptance_criteria", [])
    counts: dict[str, int] = {}
    if isinstance(criteria, list):
        for criterion in criteria:
            if isinstance(criterion, dict):
                status = str(criterion.get("status", "pending"))
                counts[status] = counts.get(status, 0) + 1

    count_text = ", ".join(f"{key}={value}" for key, value in sorted(counts.items())) or "no criteria"
    return (
        f"Current task: {task.get('task_id', 'unknown')} — {task.get('title', 'untitled')}; "
        f"contract status={task.get('status', 'in_progress')}; {count_text}."
    )


def main() -> None:
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, TypeError):
        emit({"continue": True})
        return

    event = str(hook_input.get("hook_event_name") or "")
    root = git_root(str(hook_input.get("cwd") or "") or None)
    summary = task_summary(root / ".codex" / "current-task.json") if root else "Repository root was not resolved."

    common = (
        "CyberVPN autonomous mode is active: approval_policy=never, sandbox=danger-full-access. "
        "Do not ask for routine confirmation. Install missing project/system dependencies with sudo -n, "
        "start required local services, edit all needed surfaces, regenerate artifacts, run tests, and repair "
        "failures autonomously. For non-trivial edits, maintain .codex/current-task.json with atomic acceptance "
        "criteria and evidence. Do not stop after presenting a plan. Use specialist agents for broad work and "
        "independent verifier plus adversarial_reviewer before TASK_STATUS: VERIFIED. "
        "A build, mock, screenshot, report, or child-agent claim is not proof of production behavior. "
        + summary
    )

    if event == "SubagentStart":
        common += (
            " As a subagent, obey the assigned role and file ownership. Read applicable AGENTS.md files, "
            "return exact paths/symbols and evidence, and do not claim completion outside your assigned scope."
        )

    emit(
        {
            "continue": True,
            "hookSpecificOutput": {
                "hookEventName": event,
                "additionalContext": common,
            },
        }
    )


if __name__ == "__main__":
    main()
