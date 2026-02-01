"""Bridge to Task Master for reading project tasks."""

from __future__ import annotations

import json
from pathlib import Path

from crewai.tools import tool

TASKS_JSON = Path("/home/beep/projects/VPNBussiness/.taskmaster/tasks/tasks.json")


@tool("get_task_master_tasks")
def get_task_master_tasks() -> str:
    """Get all tasks from Task Master tasks.json with their status."""
    if not TASKS_JSON.exists():
        return "No tasks.json found at .taskmaster/tasks/tasks.json"
    try:
        data = json.loads(TASKS_JSON.read_text(encoding="utf-8"))
        summary = []
        for task in data.get("tasks", []):
            deps = ", ".join(str(d) for d in task.get("dependencies", []))
            dep_str = f" [depends: {deps}]" if deps else ""
            summary.append(f"[{task['id']}] {task['title']} ({task['status']}){dep_str}")
        return "\n".join(summary) if summary else "No tasks found"
    except Exception as e:
        return f"Error reading tasks: {e}"


@tool("get_task_master_task_detail")
def get_task_master_task_detail(task_id: str) -> str:
    """Get detailed information about a specific Task Master task by ID.

    Args:
        task_id: The task ID (e.g., "1", "1.2", "1.2.1").
    """
    if not TASKS_JSON.exists():
        return "No tasks.json found"
    try:
        data = json.loads(TASKS_JSON.read_text(encoding="utf-8"))
        for task in data.get("tasks", []):
            if str(task["id"]) == task_id:
                return json.dumps(task, indent=2, ensure_ascii=False)[:5000]
        return f"Task {task_id} not found"
    except Exception as e:
        return f"Error: {e}"
