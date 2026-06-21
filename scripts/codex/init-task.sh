#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'USAGE'
Usage:
  scripts/codex/init-task.sh TASK_ID "Task title" ["Observable goal"]

Example:
  scripts/codex/init-task.sh CYBA-900 "Fix partner attribution replay" \
    "A transfer token can be consumed exactly once and duplicate claims do not create duplicate bindings"
USAGE
}

if [[ $# -lt 2 ]]; then
  usage >&2
  exit 2
fi

TASK_ID="$1"
TITLE="$2"
GOAL="${3:-$TITLE}"
ROOT="$(git rev-parse --show-toplevel)"
TARGET="${ROOT}/.codex/current-task.json"
TEMPLATE="${ROOT}/.codex/task-template.json"

mkdir -p "${ROOT}/.codex/tmp"
if [[ -f "${TARGET}" ]]; then
  cp -a "${TARGET}" "${ROOT}/.codex/tmp/current-task.$(date -u +%Y%m%dT%H%M%SZ).json"
fi

python3 - "${TEMPLATE}" "${TARGET}" "${TASK_ID}" "${TITLE}" "${GOAL}" <<'PY'
from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

template_path, target_path, task_id, title, goal = sys.argv[1:]
now = datetime.now(UTC).isoformat()

if Path(template_path).exists():
    payload = json.loads(Path(template_path).read_text(encoding="utf-8"))
else:
    payload = {
        "schema_version": 1,
        "acceptance_criteria": [],
        "negative_acceptance_criteria": [],
        "validations": [],
        "reviews": [],
        "unresolved": [],
    }

payload.update(
    {
        "task_id": task_id,
        "title": title,
        "goal": goal,
        "status": "in_progress",
        "assumptions": [],
        "in_scope": [],
        "out_of_scope": [],
        "affected_surfaces": [],
        "acceptance_criteria": [
            {
                "id": "AC-01",
                "text": "Replace this placeholder with one atomic observable outcome",
                "status": "pending",
                "implementation_evidence": [],
                "test_evidence": [],
            }
        ],
        "negative_acceptance_criteria": [],
        "validations": [],
        "reviews": [
            {
                "agent": "verifier",
                "status": "not_run",
                "findings": [],
                "evidence": "",
            },
            {
                "agent": "adversarial_reviewer",
                "status": "not_run",
                "findings": [],
                "evidence": "",
            },
        ],
        "unresolved": [],
        "created_at": now,
        "updated_at": now,
    }
)
Path(target_path).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY

printf 'Created %s\n' "${TARGET}"
printf 'Task: %s — %s\n' "${TASK_ID}" "${TITLE}"
printf 'Replace AC-01, add all criteria and exact validation commands before implementation.\n'
