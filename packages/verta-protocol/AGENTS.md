# Verta Protocol Engineering Contract

Apply the repository root contract and `packages/AGENTS.md`. This file is
authoritative for `packages/verta-protocol/`.

Verta is an adaptive proxy/VPN protocol suite in Rust. It must remain
spec-driven, security-conscious, transport-agnostic at the session core, and
integrated with Remnawave through explicit bridge/adapter boundaries rather
than a panel fork.

`Verta` is the canonical public name. Existing internal crate/package
identifiers such as `ns-*` and documented artifact paths may remain until an
approved compatibility migration changes them.

## Normative sources

Read `docs/spec/INDEX.md` first, then every governing spec section for the
changed slice. Normative documents include:

- `docs/spec/adaptive_proxy_vpn_protocol_master_plan.md`
- `docs/spec/verta_blueprint_v0.md`
- `docs/spec/verta_wire_format_freeze_candidate_v0_1.md`
- `docs/spec/verta_remnawave_bridge_spec_v0_1.md`
- `docs/spec/verta_threat_model_v0_1.md`
- `docs/spec/verta_security_test_and_interop_plan_v0_1.md`
- `docs/spec/verta_implementation_spec_rust_workspace_plan_v0_1.md`
- `docs/spec/verta_protocol_rfc_draft_v0_1.md`

The relevant spec is authoritative for protocol behavior. The task may
explicitly request a spec change; in that case update/approve the specification
or ADR before making implementation behavior diverge.

If a required semantic rule is missing or contradictory, record the exact gap
in `docs/spec/MISSING_INPUTS.md` or an ADR. Do not invent wire, crypto,
downgrade, negotiation, authentication, replay, or bridge semantics.

Record the governing spec sections in `.codex/current-task.json` and the PR
description.

## Architecture invariants

- Keep session, policy, authentication, manifest, storage, observability,
  carrier, client runtime, gateway runtime, and bridge responsibilities in
  their documented crates.
- The session core remains transport-agnostic.
- Carrier/persona implementations remain replaceable behind stable interfaces.
- Remnawave remains an external control plane/subscription source integrated
  through bridge/adapter contracts.
- Keep platform-specific behavior behind explicit features/adapters.
- Prefer explicit versions, registries, capability negotiation, and typed state
  machines over implicit behavior.
- Treat public API, wire format, manifest, persisted state, CLI output, and
  bridge contracts as compatibility boundaries.
- Keep changes narrow and traceable to requirements. Do not combine unrelated
  protocol, refactor, tooling, and documentation work.

Before adding a crate, feature, abstraction, or dependency, inspect the
workspace plan and existing crates. Avoid cyclic dependencies and duplicate
types.

## Protocol and parser safety

- Parse untrusted input with explicit length/count/depth limits before
  allocation or decompression.
- Reject trailing, ambiguous, non-canonical, truncated, oversized, duplicate,
  and version-incompatible representations according to the spec.
- Avoid panics, `unwrap`, `expect`, unchecked indexing, integer truncation,
  overflow, and allocation based directly on attacker-controlled values.
- Use typed errors that preserve failure category without exposing secrets.
- Bound handshake work, session state, replay windows, queues, streams,
  reassembly, retry, timers, concurrent peers, and per-peer resources.
- Make timeout, cancellation, cleanup, backpressure, and shutdown behavior
  explicit.
- Test cross-protocol confusion, downgrade, replay, reflection/amplification,
  resource exhaustion, state desynchronization, and fingerprinting risks where
  relevant.
- Do not weaken validation or accept malformed legacy input merely to make an
  interop test pass.

## Cryptography and authentication

- Do not invent cryptographic primitives, constructions, key derivation, nonce
  formats, signature formats, or random generators.
- Use established audited libraries through documented APIs and the algorithms
  selected by the normative specs.
- Keep key, nonce, sequence, epoch, transcript, and replay invariants explicit.
- Use constant-time comparisons for secret authentication material through
  established APIs.
- Never log plaintext keys, secrets, tokens, credentials, transcripts,
  decrypted payloads, or stable identifiers that violate the threat model.
- Zeroize or minimize secret lifetime where the current design requires it.
- Crypto-sensitive changes require `security_reviewer`, negative tests, vectors,
  and a spec/ADR trace.

## Compatibility and versioning

A wire, manifest, persisted-state, public API, CLI, or bridge change requires:

1. Identify old and new versions and every consumer.
2. Decide whether the change is additive, negotiated, migrated, or breaking.
3. Update the normative spec/ADR and compatibility matrix.
4. Add golden vectors and decode/encode round trips.
5. Add old/new interop and downgrade-rejection tests.
6. Update client, gateway, bridge, testkit, tools, examples, and operator docs.
7. Preserve a safe rollback or explicitly document why rollback is impossible.
8. Run a second generation/vector check to prove reproducibility.

Do not silently change serialization order, defaults, enum discriminants, field
meaning, capability negotiation, command output consumed by automation, or
storage schema.

## Rust quality

- Use stable Rust unless a spec-backed and CI-supported exception is approved.
- Prefer ownership and safe abstractions. Any `unsafe` must be unavoidable,
  narrowly scoped, documented with safety invariants, reviewed, and covered by
  tests/Miri or equivalent evidence where applicable.
- Use typed errors and deterministic state transitions.
- Avoid blocking calls in async tasks.
- Bound channels, buffers, spawned tasks, retries, and parallelism.
- Propagate cancellation and join/clean up spawned tasks.
- Keep observability structured with `tracing`; avoid durable `println!`
  diagnostics.
- Do not add broad lint allowances. A narrow allowance must explain why and be
  located at the smallest scope.
- Review dependency default features, target support, license, security,
  maintenance, and binary footprint.

## Testing and evidence

For changed behavior add the relevant:

- unit tests for invariants/state transitions;
- malformed/boundary/property tests;
- golden vectors and canonical round trips;
- old/new and client/gateway/bridge interop tests;
- replay/downgrade/authentication negative tests;
- fuzz targets and regression corpus entries for parsers/state machines;
- concurrency, cancellation, timeout, and resource-bound tests;
- deterministic network impairment tests;
- target/platform tests;
- benchmarks for hot paths or changes with performance requirements;
- operator/CLI smoke tests.

A parser or protocol change without negative and boundary coverage is
incomplete. A benchmark must compare a meaningful baseline and must not replace
correctness tests.

Use `ns-testkit` and existing deterministic harnesses. Do not depend on the
public internet, arbitrary sleeps, production credentials, or uncontrolled
wall-clock timing.

## Documentation and ADRs

Update specs, examples, diagrams, CLI help, configuration templates, operator
guides, and release notes when behavior or expectations change.

Create an ADR under `docs/adr/` using the project template for:

- compatibility-sensitive decisions;
- transport/session boundary changes;
- Remnawave bridge contract choices;
- security tradeoffs;
- new cryptographic or authentication choices selected by the spec;
- intentional deviation from a governing document.

Documentation is synchronized after implementation and tests; it does not prove
implementation by itself.

## Subagents and worktrees

Use narrow specialist agents for spec mapping, implementation, fuzzing,
performance, interop, and security review. Give writing agents explicit crate
ownership and use separate worktrees for parallel tracks. The parent agent owns
spec interpretation, integration, and final verification.

No subagent may invent missing protocol semantics.

## WSL Ubuntu 24.04 local development

Use WSL Ubuntu 24.04 and Bash as the primary local execution environment for
this repository owner. Keep code and operator-facing scripts portable across
supported targets.

- Use Linux paths and manifest-scoped Cargo commands.
- Do not assume PowerShell is installed.
- Preserve or add paired `.ps1`/`.sh` wrappers when cross-platform operator
  workflows require both.
- Do not use symlink, case-sensitivity, GNU-tool, or filesystem assumptions
  without considering supported targets.
- Run target-specific CI/smoke for Windows/macOS behavior that WSL cannot prove.

## Required validation

From the repository root:

```bash
cargo fmt --manifest-path packages/verta-protocol/Cargo.toml --all -- --check
cargo clippy --manifest-path packages/verta-protocol/Cargo.toml --workspace --all-targets --all-features -- -D warnings
cargo test --manifest-path packages/verta-protocol/Cargo.toml --workspace
```

Add the relevant feature/target matrix, fuzz, interop, vector, benchmark,
Miri/sanitizer, CLI help, bridge, and release smoke commands for the changed
slice.

Before `TASK_STATUS: VERIFIED`:

- governing spec sections are recorded;
- code and specs/ADR agree;
- compatibility/security implications are covered;
- all affected tests were rerun after the final change;
- generated vectors/artifacts are reproducible;
- verifier, adversarial reviewer, and security reviewer (when relevant) have no
  unresolved finding.
