# Verta Operating Guide

## Project Mission

Verta is an open-source adaptive proxy/VPN protocol suite written in Rust.
The project must stay on a non-fork integration path with Remnawave acting as the external control plane and subscription layer.
Implementation work must remain spec-driven, security-conscious, transport-agnostic at the session core, and friendly to future parallel Codex work.

Legacy naming note:

- `Verta` is the canonical public protocol name.
- Canonical spec filenames under `docs/spec/verta_*` and the canonical package path `packages/verta-protocol` are now active. Legacy artifact roots under `target/verta` and technical identifiers such as `ns-*` remain valid during the migration window.

## Authoritative Documents

Treat `docs/spec/` as the source of truth for protocol and integration behavior.
If code, notes, or assumptions disagree with those documents, the documents win until they are updated.

Authoritative inputs:

- `docs/spec/adaptive_proxy_vpn_protocol_master_plan.md`
- `docs/spec/verta_blueprint_v0.md` (`Verta` blueprint)
- `docs/spec/verta_wire_format_freeze_candidate_v0_1.md` (`Verta` wire format freeze candidate)
- `docs/spec/verta_remnawave_bridge_spec_v0_1.md` (`Verta` Remnawave bridge spec)
- `docs/spec/verta_threat_model_v0_1.md` (`Verta` threat model)
- `docs/spec/verta_security_test_and_interop_plan_v0_1.md` (`Verta` security and interop plan)
- `docs/spec/verta_implementation_spec_rust_workspace_plan_v0_1.md` (`Verta` implementation spec)
- `docs/spec/verta_protocol_rfc_draft_v0_1.md` (`Verta` RFC draft)

Use `docs/spec/INDEX.md` as the quick index.
If a required spec is absent in a future run, record that gap in `docs/spec/MISSING_INPUTS.md` instead of inventing replacement protocol behavior.

## Architecture Guardrails

- Keep the session core transport-agnostic.
- Keep transport personas and carrier implementations replaceable behind stable interfaces.
- Do not fork Remnawave or blur Verta logic into panel internals; use bridge and adapter boundaries.
- Treat wire-format, manifest, and bridge contract changes as compatibility-sensitive changes.
- Use Rust stable by default unless a spec-backed exception is approved.
- Prefer explicit versioning, registries, and capability negotiation over implicit behavior.
- Use `tracing` and structured logs for diagnostics; avoid ad-hoc print debugging in durable code.
- Keep changes small, reviewable, and scoped to one coherent concern.

## Work Style

- Start every implementation task by reading the governing spec files for that slice.
- State assumptions when the spec is silent, then stop and escalate if those assumptions would change behavior.
- Favor narrow specialist subagents and narrow repo-scoped skills over giant generic helpers.
- Keep plans execution-oriented: spec read, code change, verification, doc update, review.
- Prefer paired PowerShell and Bash commands in docs when shell examples are needed.
- Preserve useful existing files and unrelated user changes.

## Coding Rules

- Follow the authoritative specs; do not “improve” protocol behavior by intuition.
- Keep transport-independent logic out of transport-specific modules.
- Keep public APIs and crate boundaries aligned with the workspace plan and ADRs.
- Avoid custom cryptography and unsafe shortcuts.
- Fail safely on malformed or untrusted input; avoid panics in protocol-facing paths.
- Use explicit bounds, timeouts, and backpressure rather than unbounded buffers or retries.
- Prefer typed errors, clear invariants, and deterministic state transitions.
- Add focused comments only where an invariant, wire rule, or boundary is not obvious from the code.

## Testing Rules

- After meaningful code changes, run formatting, linting, and the relevant test suite before handing work off.
- Add or update tests whenever behavior changes.
- Add negative tests for malformed input, boundary conditions, and downgrade or replay handling when relevant.
- Add fuzz, interop, and performance coverage when touching parsers, state machines, transport boundaries, or hot paths.
- Do not mark work “done” if verification was skipped; explicitly note what was not run and why.

## Documentation Rules

- Create or update docs whenever behavior, interfaces, or operator expectations change.
- Keep docs concise, structured, and spec-referenced.
- Use ADRs for intentional deviations, major design choices, compatibility-sensitive changes, or boundary decisions.
- Keep examples, verification commands, and release-facing docs synchronized with actual behavior.

## Security Rules

- Use the threat model as a routine review input, not a one-time artifact.
- Preserve secure defaults; do not weaken them for convenience.
- Never log secrets, raw tokens, long-lived identifiers, or plaintext sensitive payloads.
- Treat downgrade, replay, resource exhaustion, cross-protocol confusion, and fingerprinting risks as first-class review topics.
- Call out any use of `unsafe`, crypto-sensitive changes, parser complexity growth, or unauthenticated amplification paths.

## Review Expectations

- Reviews must check spec conformance, compatibility risk, security impact, tests, and doc updates.
- Wire-format and bridge-contract changes require especially skeptical review.
- Prefer concrete findings with file references, required follow-ups, and missing tests called out explicitly.
- If a task changes behavior without updating docs or ADRs, the review is incomplete.

## Done Means

Implementation work is only done when:

- the governing spec sections were read and cited in the task notes or PR;
- the code matches the spec or an approved ADR;
- formatting, linting, and relevant tests were run after the change;
- diagnostics or observability were updated when needed;
- docs, templates, and examples were updated for behavior changes;
- the resulting diff is small enough for a focused review.

## Specs vs Implementation

- Specs are normative; implementation follows them.
- If implementation reveals a real gap, ambiguity, or conflict in the spec, stop and record it instead of silently deciding protocol behavior in code.
- Use ADRs for controlled deviations or architecture choices, and update the relevant spec documents when the normative behavior changes.
- Do not make ad-hoc protocol, wire-format, manifest, or bridge changes without an ADR or spec update.

## ADR Process

- Record ADRs under `docs/adr/NNNN-short-title.md`.
- Use `docs/templates/adr-template.md`.
- Write ADRs for compatibility-sensitive choices, transport abstraction boundaries, control-plane contract decisions, security tradeoffs, and any intentional deviation from a governing spec.
- Link the ADR to the affected specs and implementation changes.

## Windows-First Local Development

- Treat Windows and PowerShell as the first-class local path.
- Do not require WSL-only, Linux-only, or shell-fragile workflows when a clean cross-platform option exists.
- Keep script pairs in `scripts/*.ps1` and `scripts/*.sh` where that improves team reliability.
- Use portable paths and avoid hidden assumptions about symlinks, case sensitivity, or GNU-only tooling.

## Branch and Diff Hygiene

- Use one coherent task per branch.
- Prefer branch names with a `codex/` prefix when creating new branches.
- Keep diffs tight; avoid mixing setup, refactor, and behavior changes without a strong reason.
- Review the diff before finishing and call out any intentionally deferred work.
- Never overwrite or revert unrelated user changes without explicit permission.

## Worktrees for Parallel Tasks

- Use a separate git worktree for each parallel implementation track once this repository is initialized as a git repo.
- Keep one Codex thread mapped to one worktree whenever practical.
- Use worktrees for concurrent transport, bridge, fuzz, perf, or docs tasks that should not share build artifacts or partial edits.
- Keep shared design decisions in ADRs or spec updates so parallel threads do not drift.

## Subagent Usage

- Delegate narrow, specialist tasks to the smallest agent that can do the job well.
- Keep the parent agent responsible for scope control, spec selection, integration, and final verification.
- Give subagents explicit file ownership or output boundaries when they will write.
- Use read-only review agents for compatibility or security checks before merge-ready handoff.
- Do not ask subagents to invent missing protocol semantics.

## Do Not

- Do not fork Remnawave.
- Do not make the session core transport-specific.
- Do not make transport personas non-replaceable.
- Do not invent custom cryptography.
- Do not slip ad-hoc wire or bridge changes into implementation code without ADRs or spec updates.
- Do not introduce giant generic agents or giant generic skills.
- Do not rely on Linux-only or WSL-only workflows.
- Do not weaken security defaults to make tests or demos easier.
- Do not mark implementation complete without verification and doc updates.
