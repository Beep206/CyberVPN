# ADR Guide

## When ADRs Are Required

Write an ADR when a change affects:

- session-core invariants or transport-agnostic boundaries
- transport persona or carrier abstractions
- Remnawave bridge contract shape or non-fork integration strategy
- wire-format or manifest compatibility assumptions
- security posture, trust boundaries, or verification strategy
- a deliberate deviation from a governing spec

Do not create ADRs for trivial refactors, typo fixes, or changes that have no durable design consequence.

## Naming Convention

- Store ADRs under `docs/adr/`.
- Use `NNNN-short-title.md`.
- Start numbering at `0001`.
- Keep one ADR focused on one decision.

## Recommended Template

Use `docs/templates/adr-template.md`.
Every ADR should include:

- title and status
- context
- decision
- alternatives considered
- consequences
- links to governing specs and related implementation work
- follow-up actions

## Relation To Spec Changes

- If the ADR clarifies how to implement an existing spec rule, cite the relevant spec sections explicitly.
- If the ADR records an intentional deviation or new normative rule, update the affected spec documents in the same workstream or create an explicit follow-up item.
- Do not let ADRs and specs silently diverge.

## Relation To Implementation Changes

- Link the ADR from the implementation task or PR.
- Update tests, verification docs, and release-facing docs when the ADR affects observable behavior.
- If implementation reveals a gap in the docs, capture the gap in the ADR or related issue instead of coding around it silently.

## Helper Script

Use `scripts/new-adr.ps1` or `scripts/new-adr.sh` to create a numbered ADR from the shared template.
