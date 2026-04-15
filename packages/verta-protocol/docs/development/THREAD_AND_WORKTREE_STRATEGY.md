# Thread And Worktree Strategy

## Core Rule

Keep one coherent task per thread.
If a thread is trying to do architecture, implementation, security review, and release docs all at once, it is too broad.

## When To Stay In The Same Thread

- The follow-up work touches the same files and the same governing specs.
- The new step is a direct continuation of the active task.
- The context still fits comfortably without hiding key assumptions.

## When To Fork A New Thread

- The workstream changes subsystem or objective.
- A specialist review should happen independently of the implementation thread.
- The current thread has accumulated too much stale context or mixed decisions.

## Worktree Guidance

- Use a separate git worktree for each concurrent writing task once the repository is initialized as a git repo.
- Keep one thread mapped to one worktree when practical.
- Use separate worktrees for transport work, bridge work, fuzz work, perf work, and doc-heavy sweeps when they would otherwise collide.
- Use a clean review worktree when you want to inspect diffs without half-finished local edits.

## Review Threads

- Spin up a separate review thread when you want an independent compatibility or security pass.
- Prefer read-only reviewer agents in those threads.
- Merge reviewer findings back into the implementation thread deliberately instead of letting two writing threads edit the same files casually.

## Current Repository Note

This repository is not yet initialized as a git repo.
Adopt the worktree pattern as soon as git setup begins so the multi-agent workflow stays clean from the start.
