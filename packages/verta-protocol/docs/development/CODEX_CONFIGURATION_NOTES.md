# Codex Configuration Notes

## Repo-Scoped Settings

The repository-scoped Codex layer lives in:

- `.codex/config.toml` for shared agent defaults
- `.codex/agents/` for custom specialist agents
- `.agents/skills/` for repo-scoped reusable skills
- `AGENTS.md` for durable operating rules that every future run should follow

These files are safe to commit because they describe how Verta work should be performed inside this repository, not a single developer's personal environment.

## Why the Current Defaults Are Conservative

`.codex/config.toml` sets:

- `max_threads = 6` to allow useful parallel specialist work without encouraging uncontrolled fan-out
- `max_depth = 1` to keep delegation chains shallow and easier to review
- `job_max_runtime_seconds = 2700` so meaningful sub-tasks can run without becoming unattended background work

The config intentionally inherits the parent session model and reasoning defaults unless a task-specific agent file says otherwise.

## Optional User-Scoped Config Outside the Repo

Future user-scoped configuration belongs in the developer's home Codex config, not in this repository.
Examples that should stay user-scoped:

- preferred global model or reasoning settings
- personal trust and sandbox settings
- plugin enablement choices
- machine-specific timeout or network preferences
- approval defaults for the developer's own workstation

## Safely Adjusting Agent Concurrency Later

Only raise `max_threads` after the team confirms that:

- tasks are being split into genuinely independent workstreams
- each parallel task has clear file ownership or an isolated worktree
- review quality is staying high
- the local machine can handle the extra load without making feedback loops worse

If parallel work becomes noisy, lower `max_threads` before raising `max_depth`.
Keep `max_depth` conservative unless there is a proven need for subagents to spawn additional specialist layers.

## Worktrees and Approvals

Use separate worktrees for concurrent implementation tracks once the repository is initialized as a git repo.
Pair one worktree with one coherent task or Codex thread whenever practical.

Keep approvals conservative:

- prefer read-only review agents for compatibility and security passes
- avoid destructive or repository-wide actions without an explicit reason
- review diffs before merging outputs from multiple specialist threads

This repository currently stores the operating layer only.
When implementation begins, revisit the config only if the real workflow shows a clear need.
