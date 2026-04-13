# Codex Runbook

## Purpose

Use this repository in Codex App as a spec-driven, multi-agent workspace.
The goal is to keep context clean, tasks isolated, and outputs reviewable.

## Basic Flow

1. Read `AGENTS.md`.
2. Open the governing files in `docs/spec/`.
3. Decide whether the task is exploration, implementation, review, or documentation.
4. Keep one coherent goal per thread.
5. Review the diff and verification results before finishing.

## Breaking Work Into Threads

- Use one thread per coherent task.
- Split threads by subsystem, not by whim.
- Good thread boundaries include session core, QUIC carrier work, bridge contract work, fuzz coverage, perf work, and docs sync.
- Start a fresh thread when the problem statement changes meaningfully or the active context becomes noisy.

## When To Use Worktrees

- Use a separate git worktree for parallel implementation tracks once the repository is initialized as a git repo.
- Pair one thread with one worktree whenever possible.
- Use worktrees when two tasks will both write code, or when review needs a clean isolated checkout.
- Skip worktrees for pure exploration or read-only review.

## When To Stay In Local Mode

- Stay in the current thread and worktree for small, contiguous follow-ups on the same files.
- Stay local when the task is mostly reading, planning, or reviewing outputs from another specialist.
- Escalate to additional threads only when the extra isolation genuinely reduces risk or context load.

## When To Review Diffs

- Review diffs before every major handoff.
- Review diffs again after merging outputs from specialist agents.
- Treat doc and script changes as first-class review surfaces, not just code changes.
- If the diff mixes setup, behavior, and cleanup, split it unless the coupling is unavoidable.

## Keeping Context Clean

- Load only the relevant spec sections for the task.
- Use repo-scoped skills when a task matches them.
- Summarize findings into checklists instead of carrying large prose blocks forward.
- Do not keep stale assumptions alive after the specs or ADRs say otherwise.

## Recovering From Drift

- Re-open `docs/spec/INDEX.md` and the governing documents.
- Re-run `scripts/spec-drift-check.ps1` or `scripts/spec-drift-check.sh`.
- Compare active assumptions against ADRs and current docs.
- If drift is real, stop and resolve it with a doc update, ADR, or explicit follow-up issue before implementing more behavior.

## Recommended Sequence

1. Exploration: read specs, inspect current files, choose the narrowest relevant agent or skill.
2. Implementation: make the smallest patch that moves the task forward.
3. Verification: run the relevant checks and note any skipped items honestly.
4. Review: inspect the diff for spec alignment, security, docs, and test coverage.
5. Sync: update docs, templates, or ADRs if the behavior or workflow changed.
