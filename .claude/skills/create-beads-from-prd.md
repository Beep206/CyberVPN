---
name: create-beads-from-prd
description: Convert a PRD into Beads tasks (epic + children with dependencies) for autonomous execution
user_invocable: true
arguments:
  - name: prd_path
    description: Path to PRD file (optional - will prompt if not provided)
    required: false
---

# Create Beads from PRD

Convert a PRD document into Beads tasks for autonomous ralph-tui execution.

## Usage

```
/create-beads-from-prd [path/to/prd.md]
```

## What This Does

1. Reads the specified PRD (or prompts for one)
2. Extracts Quality Gates (commands that must pass)
3. Creates an epic bead for the feature
4. Creates child beads for each user story
5. Sets up dependencies (schema → backend → UI)
6. Outputs tasks ready for `ralph-tui run --tracker beads`

## Instructions

<instructions>
Launch the `prd-to-beads` agent to convert the PRD into Beads tasks.

If a PRD path was provided as argument, pass it to the agent.
If no path was provided, first ask the user which PRD to convert or let them paste the content.

The agent will:
1. Read and analyze the PRD
2. Extract quality gates
3. Split large stories if needed
4. Create epic + child beads with proper dependencies
5. Sync to beads database

After completion, show:
- Epic ID created
- Number of child tasks
- Dependency graph summary
- Command to start execution: `ralph-tui run --tracker beads --epic [EPIC_ID]`
</instructions>
