# Codex Automation Library

This file intentionally does not create app automations.
It collects candidate prompts that can be turned into automations later if the team wants recurring Codex runs.

## Daily Spec Drift Scan

- Suggested cadence: weekday morning
- Prompt: `Compare AGENTS.md, docs/spec/INDEX.md, ADRs, and the latest repository changes. Report any drift between implementation-facing docs and the authoritative Northstar specs. Open follow-up items only when drift or ambiguity is real.`

## Weekly Security Checklist

- Suggested cadence: weekly
- Prompt: `Review recent Northstar changes against the threat model. Summarize downgrade, replay, resource-exhaustion, logging, and trust-boundary risks. Call out missing tests or ADRs.`

## Release Doc Sync

- Suggested cadence: before milestones or tagged releases
- Prompt: `Sweep release-facing docs, examples, verification commands, ADR references, and spec-adjacent notes. Report any inconsistency that would confuse contributors or operators preparing a release.`

## Recent Diff Review

- Suggested cadence: daily on active branches
- Prompt: `Inspect the most recent Northstar diffs for scope creep, missing doc updates, missing verification, and violations of AGENTS.md. Summarize concrete findings only.`

## Conformance Regression Scan

- Suggested cadence: after parser, wire-format, or bridge changes
- Prompt: `Review the latest parser, manifest, bridge, and conformance-related changes. Recommend negative tests, fuzz targets, interop fixtures, or compatibility checks that should be added next.`
