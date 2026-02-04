---
name: run-beads-orchestrator
description: Start autonomous Beads task execution until all work is complete
user_invocable: true
arguments:
  - name: flags
    description: "Optional flags: --epic <ID> to focus on epic, --task <ID> for single task"
    required: false
---

# Run Beads Orchestrator (Autonomous)

Start autonomous task execution that runs until all work is complete.

## Usage

```bash
# Execute ALL ready tasks until done
/run-beads-orchestrator

# Focus on specific epic until complete
/run-beads-orchestrator --epic VPNBussiness-epic-001

# Execute single task
/run-beads-orchestrator --task VPNBussiness-042
```

## What Happens

The orchestrator runs an **autonomous loop**:

```
┌─────────────────────────────────────────┐
│           AUTONOMOUS LOOP               │
│                                         │
│  1. Find ready tasks (bd ready)         │
│  2. Dispatch up to 4 in parallel        │
│  3. Wait for completions                │
│  4. Run code reviews                    │
│  5. Close completed beads               │
│  6. Repeat until no work left           │
│  7. Output: <promise>COMPLETE</promise> │
│                                         │
└─────────────────────────────────────────┘
```

## Instructions

<instructions>
**IMMEDIATELY** launch the beads-orchestrator agent with the autonomous run protocol.

Parse the flags:
- No flags → Execute all ready tasks
- `--epic <ID>` → Focus only on that epic's children
- `--task <ID>` → Execute single specific task

```python
Task(
    subagent_type="beads-orchestrator",
    model="opus",  # Use Opus 4.5 for best results
    prompt=f"""
    ## AUTONOMOUS EXECUTION MODE

    **Command:** beads-orchestrator run {FLAGS}

    Execute the autonomous loop protocol:

    1. Run `bd ready --json` to get available tasks
    2. {EPIC_FILTER if --epic else "Process all ready tasks"}
    3. Dispatch up to 4 supervisors in PARALLEL (single message, multiple Task calls)
    4. Wait for completions using TaskOutput
    5. Run code review for each completion
    6. Close beads with `bd close`
    7. Check for newly unblocked tasks
    8. REPEAT until no ready tasks AND no in_progress tasks
    9. Output `<promise>COMPLETE</promise>` when done

    **DO NOT STOP** until all work is complete or you hit an unrecoverable error.
    **DO NOT ASK** for user input - run autonomously.
    """
)
```

**Model:** This MUST run on Opus 4.5 for complex orchestration.

After the orchestrator outputs `<promise>COMPLETE</promise>`, show the user:
- Number of tasks completed
- Any errors encountered
- Final project status (`bd stats`)
</instructions>
