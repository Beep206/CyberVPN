# ADR 0002: Verta Public Protocol Rename

- Status: Accepted
- Date: 2026-04-15

## Context

The protocol workspace, specs, release surfaces, and operator docs were originally published under the `Northstar` name.
That public identity has now been renamed to `Verta`.

The repository still has deep technical coupling to stable internal identifiers across:

- Rust crate and binary identifiers such as `ns-*`, `nsctl`, `ns-clientd`, `ns-gatewayd`, and `ns-bridge`
- environment variables under `VERTA_*`
- artifact roots under `target/verta`
- workflow filenames under `.github/workflows/verta-*`
- canonical spec filenames under `docs/spec/verta_*`

A one-shot rename of every internal identifier would create unnecessary risk for release evidence attribution, maintained verification lanes, operator runbooks, and downstream automation.

## Decision

`Verta` is the canonical public and repository-level protocol name.

The public and repository-level rename is complete:

1. Public docs, specs, release surfaces, and runbooks now use `Verta`.
2. The package path is now `packages/verta-protocol`.
3. Environment variables are standardized under `VERTA_*`.
4. Artifact roots are standardized under `target/verta`.
5. Workflow filenames are standardized under `.github/workflows/verta-*`.

Internal `ns-*` crate and binary identifiers remain unchanged by design until a separate internal-ID migration is explicitly approved.

## Alternatives Considered

- Option A:
  One-shot global rename of docs, paths, env vars, crates, binaries, workflows, and artifacts.
- Option B:
  Public-first rename with an explicit compatibility window and deferred internal-ID migration.

## Consequences

Positive:

- Public branding is now consistent at the repository, release, and operator layers.
- Verification and release evidence remain attributable under one canonical `Verta` identity.
- Operators and downstream automation continue to work without reintroducing `Northstar`.

Negative:

- The repository still contains stable internal technical identifiers such as `ns-*`.
- A future internal-ID migration would still require its own review and compatibility plan.

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
- Keep `VERTA_*` env vars and `target/verta/` artifact paths as the maintained canonical identifiers.
- Decide separately whether `ns-*` technical identifiers should remain stable or be renamed.
