---
name: run-beads-orchestrator
description: Start the Beads orchestrator to execute tasks in parallel with dependency management
user_invocable: true
arguments:
  - name: mode
    description: "Execution mode: 'auto' (dispatch all ready), 'epic' (focus on epic), 'task' (single task)"
    required: false
  - name: target
    description: "Epic ID or Task ID to focus on (optional)"
    required: false
---

# Run Beads Orchestrator

Start parallel task execution with the Beads orchestrator.

## Usage

```bash
# Auto mode - dispatch all ready tasks
/run-beads-orchestrator

# Focus on specific epic
/run-beads-orchestrator epic VPNBussiness-epic-001

# Execute single task
/run-beads-orchestrator task VPNBussiness-042
```

## Modes

| Mode | Description |
|------|-------------|
| `auto` | Find all ready tasks, dispatch in parallel batches |
| `epic` | Focus on one epic, execute children in dependency order |
| `task` | Execute a single specific task |

## Instructions

<instructions>
Launch the `beads-orchestrator` agent based on the requested mode.

### Auto Mode (default)
```python
Task(
    subagent_type="beads-orchestrator",
    prompt="""
    Execute all ready Beads tasks in parallel.
    
    1. Run `bd ready --json` to find unblocked tasks
    2. Group by domain (backend, frontend, mobile)
    3. Dispatch up to 4 supervisors in parallel
    4. Monitor completion
    5. Request code reviews
    6. Close completed tasks
    7. Repeat until no ready tasks
    """
)
```

### Epic Mode
```python
Task(
    subagent_type="beads-orchestrator",
    prompt="""
    Execute epic {TARGET_ID} with its children.
    
    1. Run `bd show {TARGET_ID}` to see epic structure
    2. Check for design doc, create if missing
    3. Execute children in dependency order
    4. Dispatch parallel where possible
    5. Close epic when all children done
    """
)
```

### Task Mode
```python
Task(
    subagent_type="beads-orchestrator",
    prompt="""
    Execute single task {TARGET_ID}.
    
    1. Run `bd show {TARGET_ID}` for details
    2. Create worktree
    3. Dispatch appropriate supervisor
    4. Request code review
    5. Close task
    """
)
```

After completion, show summary:
- Tasks completed
- Tasks remaining
- Any errors encountered
</instructions>
