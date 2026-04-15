# Rust Workspace Overview

This file is the compile-oriented scaffold guide for the main Verta integrator.
It is derived from these normative sources:

- `docs/spec/verta_implementation_spec_rust_workspace_plan_v0_1.md`
- `docs/spec/verta_blueprint_v0.md`
- `docs/spec/verta_wire_format_freeze_candidate_v0_1.md`

If this document conflicts with those sources, the spec files win.

## Naming Mismatch To Resolve Up Front

The user prompt used example crate names such as `verta-proto`, `verta-transport`, `verta-bridge-contract`, `verta-bridge-remnawave`, `verta-client`, and `verta-gateway`.

The normative workspace spec does not use that naming.
The repository should keep the spec-defined `ns-*` layout:

- `verta-proto` is split into `ns-core` and `ns-wire`.
- `verta-transport` is not a standalone crate in the spec; transport-neutral traits belong in `ns-session`.
- `verta-transport-quic` and `verta-transport-h3` collapse into the first concrete carrier crate `ns-carrier-h3`.
- `verta-bridge-contract` is split into `ns-bridge-api` and `ns-bridge-domain`.
- `verta-bridge-remnawave` maps to `ns-remnawave-adapter`.
- `verta-client` maps to `apps/ns-clientd` plus `apps/nsctl`.
- `verta-gateway` maps to `apps/ns-gatewayd`.

Do not rename the workspace back to the prompt examples unless the implementation spec changes.

## Recommended Root Workspace Layout

The root should stay close to the implementation spec:

```text
Cargo.toml
Cargo.lock
rust-toolchain.toml
.cargo/config.toml
.editorconfig
rustfmt.toml
clippy.toml
.config/nextest.toml          # add next
deny.toml                     # add next
apps/
  ns-clientd/
  nsctl/
  ns-gatewayd/
  ns-bridge/
crates/
  ns-core/
  ns-wire/
  ns-session/
  ns-auth/
  ns-manifest/
  ns-policy/
  ns-observability/
  ns-storage/
  ns-carrier-h3/
  ns-client-inbound/
  ns-client-runtime/
  ns-gateway-runtime/
  ns-bridge-api/
  ns-bridge-domain/
  ns-remnawave-adapter/
  ns-testkit/
fixtures/
  wire/
  manifest/
  token/
  bridge/
  remnawave/
fuzz/
  cargo-fuzz/
integration/
  e2e/
  net-chaos/
  remnawave-sandbox/
xtask/                        # add when fixture and release automation starts
```

## Root File Targets

These root targets should exist and remain narrow in responsibility:

| File target | Status | Responsibility |
|---|---|---|
| `Cargo.toml` | present | workspace membership, shared dependencies, lint policy, default members |
| `rust-toolchain.toml` | present | stable toolchain pin and supported targets |
| `.cargo/config.toml` | present | safe aliases and build-wide rustflags |
| `.editorconfig` | present | cross-editor defaults |
| `rustfmt.toml` | present | formatting rules |
| `clippy.toml` | present | lint tuning only, no policy drift |
| `.config/nextest.toml` | recommended next | repeatable workspace test execution policy |
| `deny.toml` | recommended next | supply-chain, advisory, and license policy |
| `xtask/Cargo.toml` | recommended later | fixture verification, local CI helpers, sample config generation |

### Root `Cargo.toml` Rules

The root workspace should continue to enforce:

- explicit `members`, not implicit globs
- `resolver = "2"`
- `default-members` limited to app crates
- shared versions for Tokio, tracing, rustls, Quinn, h3, serde, time, and auth dependencies
- `publish = false` at workspace scope unless an explicit publishing plan appears later
- `unsafe_code = "forbid"` at workspace lint scope

### Root Toolchain And Config Baseline

Keep the current stable-first posture:

- `rust-toolchain.toml`: stable channel, minimal profile, `clippy` and `rustfmt`, Windows and Linux targets
- `.cargo/config.toml`: only transparent aliases such as `lint` and `test-all`
- `rustfmt.toml`: formatting only, no style experiments
- `clippy.toml`: practical thresholds and valid idents only

Do not add nightly-only defaults to the root toolchain.
Fuzzing or sanitizer jobs can use isolated Linux workflows later.

## Crate List And Boundaries

The crate graph should remain directional and match the implementation spec.

### Protocol Foundation

- `crates/ns-core`
  - Owns runtime-neutral identifiers, registries, limits, shared enums, and value objects.
  - Must not depend on Tokio, axum, Quinn, H3, or Remnawave-specific code.
- `crates/ns-wire`
  - Owns varint helpers, frame structs, codec logic, TLV handling, parse limits, and malformed-input errors.
  - Must not perform I/O or session orchestration.
- `crates/ns-session`
  - Owns state machines, sequencing rules, relay and UDP bookkeeping, and transport-neutral carrier traits.
  - Must not expose Quinn or H3 types in its public interfaces.

### Auth, Manifest, Policy, And Shared Runtime Support

- `crates/ns-auth`
  - Owns JWT/JWKS verification policy, verifier traits, clock injection, replay hooks, and device-binding checks.
- `crates/ns-manifest`
  - Owns schema v1 types, validation, compatibility checks, signature verification hooks, and selection helpers.
- `crates/ns-policy`
  - Owns effective policy types, merge rules, authorization helpers, and runtime-neutral limits.
- `crates/ns-observability`
  - Owns tracing field names, redaction wrappers, span helpers, and metrics naming conventions.
- `crates/ns-storage`
  - Owns narrow storage traits and simple reference implementations used by Bridge-side code.
- `crates/ns-testkit`
  - Owns fakes, deterministic clocks, fixture helpers, and cross-crate test support.
  - Production crates must not depend on this crate.

### Carrier, Runtime, And Bridge Edge Crates

- `crates/ns-carrier-h3`
  - Owns the first QUIC plus HTTP/3 carrier binding.
  - Depends on `ns-session` traits instead of defining session behavior.
- `crates/ns-client-inbound`
  - Owns local inbound protocol normalization for SOCKS5 and HTTP CONNECT later.
- `crates/ns-client-runtime`
  - Owns manifest fetch, token exchange, endpoint selection, session supervision, and reconnect control.
- `crates/ns-gateway-runtime`
  - Owns admission flow, session accept loop, upstream dial orchestration, and drain handling.
- `crates/ns-bridge-api`
  - Owns the public `/v0/*` HTTP boundary and OpenAPI-aligned models.
- `crates/ns-bridge-domain`
  - Owns manifest compilation, token issuance orchestration, device registry logic, and bridge-side policy application.
- `crates/ns-remnawave-adapter`
  - Owns the non-fork Remnawave adapter boundary, normalization, webhook verification, and test fakes.

### App Composition Roots

- `apps/ns-clientd`
  - Client daemon binary. Config load, tracing bootstrap, runtime start, validation mode.
- `apps/nsctl`
  - Operator and developer CLI. Config validation, manifest inspection, diagnostics, local helper commands.
- `apps/ns-gatewayd`
  - Gateway daemon binary. Config load, tracing, listener startup, shutdown handling.
- `apps/ns-bridge`
  - Bridge service binary. Config load, tracing, HTTP server bootstrap, health endpoints.

Apps are composition roots only.
Do not move protocol logic into app crates.

## Starter Module Responsibilities

These are the recommended initial module targets for compile-oriented scaffolding.
They define ownership, not protocol behavior beyond what is already frozen in the specs.

### `crates/ns-core/src/`

- `lib.rs`: crate docs and public re-exports
- `ids.rs`: `SessionId`, `RelayId`, `FlowId`, and other stable identifiers
- `registry.rs`: capability ids, carrier kinds, error codes, target kinds
- `limits.rs`: shared hard ceilings pulled from the freeze candidate
- `types.rs`: shared value objects that are runtime-neutral
- `error.rs`: core-domain errors that are not transport-specific

### `crates/ns-wire/src/`

- `lib.rs`: public codec surface
- `frame.rs`: frozen frame structs and enums
- `varint.rs`: canonical QUIC-style varint encoder and decoder
- `tlv.rs`: metadata TLV parse and encode helpers
- `codec.rs`: envelope and payload encode or decode entry points
- `limits.rs`: wire-level parse ceilings
- `error.rs`: malformed-input and compatibility-safe parser errors
- `fixtures.rs`: test-only fixture loading helpers

### `crates/ns-session/src/`

- `lib.rs`: session-facing API surface
- `traits.rs`: carrier-facing and verifier-facing abstract traits
- `state.rs`: client and gateway session states
- `handshake.rs`: hello sequencing and negotiated session values
- `streams.rs`: relay stream bookkeeping
- `udp.rs`: UDP flow bookkeeping and fallback-mode coordination
- `policy.rs`: hooks that apply already-derived policy to session behavior
- `error.rs`: state-machine and sequencing errors

### `crates/ns-auth/src/`

- `lib.rs`: verification-oriented public API
- `claims.rs`: typed claims and JOSE header models
- `jwks.rs`: JWKS fetch, parse, cache, and key selection helpers
- `verifier.rs`: token verification flow and policy checks
- `clock.rs`: injectable clock trait or helper types
- `replay.rs`: replay-detection hook interfaces
- `error.rs`: auth and trust-validation errors

### `crates/ns-manifest/src/`

- `lib.rs`: manifest API surface
- `schema.rs`: schema v1 structs and serde rules
- `validate.rs`: structure and compatibility validation
- `signature.rs`: signature verification hooks
- `select.rs`: endpoint and carrier-profile selection helpers
- `cache.rs`: cache metadata and conditional-fetch helper types
- `error.rs`: manifest validation and compatibility errors

### `crates/ns-policy/src/`

- `lib.rs`: policy-facing exports
- `model.rs`: effective policy and session-limit types
- `merge.rs`: manifest plus token plus local override merge rules
- `decision.rs`: authorization helpers for targets and runtime actions
- `limits.rs`: typed policy limits
- `error.rs`: policy denial or invalid-policy errors

### `crates/ns-observability/src/`

- `lib.rs`: tracing bootstrap and shared helpers
- `fields.rs`: stable tracing field keys
- `redaction.rs`: redacted wrappers for secrets and identifiers
- `tracing.rs`: common span and event helpers
- `metrics.rs`: metric name constants and label helpers
- `error.rs`: observability bootstrap errors if needed

### `crates/ns-storage/src/`

- `lib.rs`: storage trait exports
- `traits.rs`: narrow repository traits
- `memory.rs`: in-memory reference implementation for early tests
- `models.rs`: storage-facing persistence models only where shared
- `error.rs`: storage and repository errors

### `crates/ns-carrier-h3/src/`

- `lib.rs`: carrier implementation surface
- `config.rs`: H3 carrier config mapping from manifest profile
- `client.rs`: client-side carrier session bootstrap
- `server.rs`: gateway-side carrier accept path
- `binding.rs`: mapping between H3 primitives and `ns-session` traits
- `datagram.rs`: datagram support and fallback-mode coordination
- `error.rs`: carrier-specific error mapping

### `crates/ns-client-inbound/src/`

- `lib.rs`: normalized inbound request API
- `socks5.rs`: SOCKS5 parser and handshake boundary
- `http_connect.rs`: HTTP CONNECT parser and normalization
- `normalize.rs`: conversion into session-neutral target requests
- `error.rs`: local inbound parse and policy errors

### `crates/ns-client-runtime/src/`

- `lib.rs`: runtime entry points
- `config.rs`: client config model
- `bootstrap.rs`: manifest bootstrap and startup validation
- `manifest.rs`: manifest fetch and refresh orchestration
- `token.rs`: token exchange orchestration
- `selector.rs`: endpoint and profile selection orchestration
- `supervisor.rs`: session lifecycle, reconnect, and shutdown control
- `error.rs`: runtime-level errors

### `crates/ns-gateway-runtime/src/`

- `lib.rs`: gateway runtime entry points
- `config.rs`: gateway config model
- `accept.rs`: carrier accept loop
- `admission.rs`: pre-auth limits and admission checks
- `session.rs`: gateway session orchestration
- `upstream.rs`: outbound TCP and UDP connection orchestration
- `shutdown.rs`: graceful drain and stop behavior
- `error.rs`: gateway runtime errors

### `crates/ns-bridge-api/src/`

- `lib.rs`: router construction entry points
- `models.rs`: request and response models for `/v0/*`
- `routes.rs`: public route registration only
- `extract.rs`: request extraction and auth context helpers
- `response.rs`: HTTP error mapping and response helpers
- `error.rs`: bridge HTTP boundary errors

### `crates/ns-bridge-domain/src/`

- `lib.rs`: bridge domain services
- `bootstrap.rs`: device registration and bootstrap orchestration
- `manifest_compiler.rs`: manifest assembly and signing orchestration
- `token_issuer.rs`: token issuance orchestration
- `devices.rs`: device registry flows
- `policy.rs`: bridge-side policy shaping inputs
- `error.rs`: domain-level bridge errors

### `crates/ns-remnawave-adapter/src/`

- `lib.rs`: adapter traits and entry points
- `client.rs`: Remnawave fetch or poll client
- `normalize.rs`: conversion into bridge-domain inputs
- `webhook.rs`: webhook verification and ingestion boundary
- `fake.rs`: fake adapter for local integration tests
- `error.rs`: adapter errors

### `crates/ns-testkit/src/`

- `lib.rs`: testkit exports
- `clock.rs`: deterministic clock helpers
- `carrier.rs`: fake carrier and session harness pieces
- `auth.rs`: fake signer and verifier helpers
- `bridge.rs`: fake bridge responses and adapter fixtures
- `fixtures.rs`: workspace fixture path helpers

## Immediate Integrator Notes

- Keep the existing `ns-*` member list in the root `Cargo.toml`; it matches the normative workspace plan.
- Add `.config/nextest.toml` and `deny.toml` before the first serious CI gate, not after.
- Keep `ns-session` as the transport-neutral boundary. Do not introduce a generic `verta-transport` crate that duplicates this role.
- Keep bridge logic split across `ns-bridge-api`, `ns-bridge-domain`, and `ns-remnawave-adapter`. Do not collapse them into one bridge crate.
- If a public package naming strategy is needed later, solve that through package metadata and release docs, not by renaming the internal workspace away from the spec.
