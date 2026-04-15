# ADR 0002: Verta Public Protocol Rename

- Status: Accepted
- Date: 2026-04-15

## Context

The protocol workspace, specs, release surfaces, and operator docs were originally published under the `verta` name.
That identity is now being renamed to `Verta`.

The repository already has deep technical coupling to the legacy name across:

- the package path `packages/verta-protocol`
- Rust crate and binary identifiers such as `ns-*`, `nsctl`, `ns-clientd`, `ns-gatewayd`, and `ns-bridge`
- environment variables under `VERTA_*`
- artifact roots under `target/verta`
- workflow filenames under `.github/workflows/verta-*`
- canonical spec filenames under `docs/spec/verta_*`

A one-shot rename would create unnecessary risk for release evidence attribution, maintained verification lanes, operator runbooks, and downstream automation.

## Decision

`Verta` becomes the canonical public protocol name.

The rename will proceed in staged waves:

1. Wave 0 freezes the rename policy in ADRs and canonical docs.
2. Wave 1 renames public docs, specs, release surfaces, and runbooks to `Verta`.
3. Wave 2 adds compatibility aliases for `VERTA_*` and future `target/verta` usage while preserving `VERTA_*` and `target/verta`.
4. Wave 3 may rename the package path to `packages/verta-protocol` after compatibility is proven.
5. Wave 4 will separately decide whether internal `ns-*` identifiers should remain stable or be renamed.

During Wave 0 and Wave 1:

- `verta` remains the legacy technical identity where filenames, env names, artifact roots, and existing verification lanes still depend on it.
- `ns-*` crate and binary names remain unchanged.
- `VERTA_*` env vars remain unchanged.
- `target/verta` remains unchanged.

## Alternatives Considered

- Option A:
  One-shot global rename of docs, paths, env vars, crates, binaries, workflows, and artifacts.
- Option B:
  Public-first rename with an explicit compatibility window and deferred internal-ID migration.

## Consequences

Positive:

- Public branding becomes consistent immediately.
- Verification and release evidence stay attributable during the rename.
- Operators and downstream automation keep working during the migration window.

Negative:

- The repository will temporarily contain mixed public and technical naming.
- Some legacy filenames and machine-readable values will continue to contain `verta` until later waves land.

## Spec Links

- `docs/spec/INDEX.md`
- `docs/spec/verta_blueprint_v0.md`
- `docs/spec/verta_wire_format_freeze_candidate_v0_1.md`
- `docs/spec/verta_remnawave_bridge_spec_v0_1.md`
- `docs/spec/verta_threat_model_v0_1.md`
- `docs/spec/verta_security_test_and_interop_plan_v0_1.md`
- `docs/spec/verta_implementation_spec_rust_workspace_plan_v0_1.md`
- `docs/spec/verta_protocol_rfc_draft_v0_1.md`

## Follow-Up

- Make `Verta` canonical across README, AGENTS, spec index, phased plan, implementation status, release docs, and runbook indexes.
- Add `VERTA_*` compatibility aliases without removing `VERTA_*`.
- Decide separately whether `packages/verta-protocol` and `ns-*` technical identifiers should remain stable or be renamed.
