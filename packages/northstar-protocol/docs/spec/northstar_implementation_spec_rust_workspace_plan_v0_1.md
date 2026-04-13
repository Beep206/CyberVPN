# Northstar Implementation Spec / Rust Workspace Plan v0.1

**Status:** Draft v0.1  
**Codename:** Northstar  
**Document type:** implementation specification, repository architecture, crate-boundary plan, runtime plan, build and delivery plan  
**Audience:** Rust engineers, protocol implementers, bridge/control-plane engineers, QA engineers, security reviewers, release engineers, AI coding agents  
**Companion documents:**
- `Adaptive Proxy/VPN Protocol Master Plan`
- `Blueprint v0 — Adaptive Proxy/VPN Protocol Suite (Northstar)`
- `Northstar Spec v0.1 — Wire Format Freeze Candidate`
- `Northstar Remnawave Bridge Spec v0.1`
- `Northstar Threat Model v0.1`
- `Northstar Security Test & Interop Plan v0.1`

---

## 1. Why this document exists

The Northstar document set now contains:

- a phased roadmap
- an architectural blueprint
- a frozen v0.1 wire contract
- a Bridge integration contract for the non-fork Remnawave path
- a threat model
- a validation and interop plan

What is still needed is a document that answers a more practical question:

**How should the Rust repository be structured so the protocol can actually be implemented without architectural drift, dependency chaos, or AI-agent-induced fragmentation?**

This document is the answer.

It defines:

- the repository layout
- crate boundaries and dependency rules
- runtime architecture for client, gateway, and Bridge
- code ownership rules
- configuration and storage conventions
- build, packaging, CI, and release expectations
- security and observability requirements at the codebase level
- task decomposition suitable for human developers and AI coding agents

This document is intentionally more operational than the Blueprint and more code-oriented than the Freeze Candidate.

---

## 2. Relationship to the other Northstar documents

This document does not replace any previous document.

Each document has a different role:

| Document | Primary question it answers |
|---|---|
| Master Plan | What should be built over time? |
| Blueprint v0 | What is the architecture? |
| Wire Format Freeze Candidate | What is frozen enough to implement on the wire? |
| Bridge Spec | How does Northstar integrate with Remnawave without forking it? |
| Threat Model | What can go wrong and what controls are required? |
| Security Test & Interop Plan | How do we prove correctness, safety, and compatibility? |
| **This document** | **How do we organize the Rust codebase and implementation work so the above can be delivered sanely?** |

The implementation spec MUST remain consistent with the Freeze Candidate and Bridge Spec. If any contradiction appears, the protocol contract documents win.

---

## 3. Version and implementation baseline

This implementation plan is scoped to the first serious implementation baseline:

- **Session core version:** `1`
- **Manifest schema version:** `1`
- **Bridge public API version prefix:** `/v0`
- **Primary carrier:** `h3`
- **Traffic modes in scope:**
  - TCP relay
  - UDP relay via datagram when available
  - UDP relay via stream fallback
- **Integration path:** Remnawave as external control plane, Northstar Bridge as adapter/manifest/token layer, Northstar Gateway as Rust data plane, Northstar Client as custom client

Explicitly not in the first implementation baseline:

- full IP tunnel mode
- alternate carriers as production-ready choices
- GUI-first desktop application
- mobile apps
- kernel-mode components
- multi-path transport
- FEC / erasure coding
- post-quantum migration work
- HSM/KMS-heavy production key infrastructure beyond clear abstraction points

These deferred items still appear later so they are not forgotten.

---

## 4. Implementation goals and non-goals

### 4.1 Primary implementation goals

The Rust repository and workspace design MUST make the following possible:

1. Implement the frozen wire contract without ambiguity.
2. Keep the protocol core independent from any single carrier implementation.
3. Allow the client, gateway, and Bridge to evolve in parallel.
4. Make testing and fuzzing natural, not bolted on later.
5. Keep performance-sensitive logic in narrow, reviewable areas.
6. Allow Windows-first client delivery without infecting the whole codebase with platform-specific branches.
7. Keep Remnawave integration isolated behind a narrow adapter boundary.
8. Make it hard for contributors to accidentally break compatibility.
9. Make it safe to use multiple AI coding agents in parallel.
10. Make future carriers possible without rewriting the session core.

### 4.2 Explicit non-goals of the workspace plan

This workspace is **not** trying to:

- maximize crate count for ideological purity
- hide complexity behind macros everywhere
- allow every crate to depend on every other crate
- treat `anyhow` as a substitute for domain errors
- mix frozen protocol logic with operator dashboard code
- optimize for every operating system equally in v0.1
- make GUI concerns drive the core architecture

The design goal is disciplined implementation, not aesthetic micro-crate perfection.

---

## 5. Engineering philosophy for the codebase

Northstar should be implemented as a **layered system with explicit boundaries**.

### 5.1 Layering model

```text
Apps / Binaries
    ↓
Runtime Crates (client, gateway, bridge)
    ↓
Service / Domain Crates
    ↓
Protocol / Manifest / Auth / Policy Crates
    ↓
Pure Core Types and Wire Codec Crates
```

### 5.2 Design posture

- Keep the **protocol and wire logic small, deterministic, and test-heavy**.
- Keep the **carrier implementation isolated**.
- Keep the **Remnawave adapter isolated**.
- Keep **platform-specific code isolated**.
- Prefer **pure crates** at the bottom and **effectful crates** near the edges.
- Prefer **trait boundaries** for components that are likely to vary in tests or future deployments.
- Prefer **bounded channels and explicit cancellation** over implicit global task sprawl.
- Prefer **domain-specific errors** inside libraries and `anyhow` only at binary boundaries.

### 5.3 Security posture

- First-party crates SHOULD use `#![forbid(unsafe_code)]` by default.
- Any exception for `unsafe` MUST be documented by an ADR and justified by profiling or unavoidable FFI.
- Untrusted inputs MUST be parsed with bounded allocations and explicit size limits.
- Secrets MUST NOT be logged.
- Debug output for secret-bearing types MUST be redacted.
- Pre-auth code paths MUST have strict CPU and memory discipline.

---

## 6. Workspace architecture

### 6.1 Repository layout

The repository SHOULD start with the following structure:

```text
northstar/
  .cargo/
    config.toml
  .config/
    nextest.toml
  .github/
    workflows/
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
  benches/
  deployments/
    dev/
    staging/
    prod-examples/
  docs/
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
  scripts/
  xtask/
  Cargo.toml
  Cargo.lock
  rust-toolchain.toml
  deny.toml
  README.md
  CHANGELOG.md
  LICENSE
```

### 6.2 Why this layout

This layout separates four classes of concerns:

1. **Reusable code** in `crates/`
2. **Deployable binaries** in `apps/`
3. **Cross-cutting build/test automation** in `xtask/`, `scripts/`, and CI config
4. **Artifacts and fixtures** in `fixtures/`, `fuzz/`, `integration/`, and `deployments/`

This makes it easier to:

- run focused tests
- hand tasks to AI agents without full-repo ambiguity
- preserve frozen fixtures outside source modules
- support both developer builds and deployment artifacts

### 6.3 What should not exist in v0.1

The following repository patterns SHOULD be avoided early:

- a giant `common` crate with vague responsibilities
- direct app-to-app dependencies
- duplicated model types between client, gateway, and bridge code
- separate protocol definitions in both Rust and ad hoc JSON docs without generation discipline
- business logic hidden in shell scripts

---

## 7. Toolchain and workspace policy

### 7.1 Rust toolchain policy

The repository MUST:

- pin a stable Rust toolchain in `rust-toolchain.toml`
- document an explicit MSRV policy
- upgrade the pinned toolchain intentionally, not accidentally
- keep CI, local development, and release builds aligned

Recommended policy:

- **Stable channel only** for normal builds and releases
- **Nightly allowed only** for isolated jobs such as certain fuzzing or experimental profiling workflows
- **MSRV bumps require changelog entry and CI update**

### 7.2 Cargo workspace policy

The root `Cargo.toml` SHOULD use workspace inheritance for:

- edition
- version (if desired)
- license
- repository metadata
- common lint configuration where supported
- common dependency versions when it improves consistency

The workspace MUST define default members carefully so that routine developer commands do not accidentally build expensive optional targets.

### 7.3 Dependency policy

The workspace MUST maintain these dependency rules:

- exactly one async runtime family in first-party code: **Tokio**
- exactly one tracing API family in first-party code: **tracing**
- avoid duplicate HTTP stacks without justification
- avoid direct dependency leakage from binaries into low-level crates
- avoid enabling giant default feature sets unless needed
- prefer explicit feature flags over implicit dependency bloat

### 7.4 Supply-chain hygiene

The repository SHOULD include automated checks for:

- dependency advisories
- license policy
- banned/duplicated dependencies
- accidental git/path dependency drift in release builds

---

## 8. Recommended foundation stack

Northstar v0.1 should use a conservative, well-understood Rust networking stack.

### 8.1 Recommended primary stack

- **Tokio** for async runtime, I/O, timers, and task orchestration
- **rustls** for TLS
- **Quinn** for QUIC transport
- **h3** for HTTP/3 binding on top of QUIC
- **axum + tower + hyper-compatible ecosystem** for Bridge HTTP APIs
- **tracing** for instrumentation
- **serde / serde_json / toml** for config and data models
- **bytes** for efficient byte handling

### 8.2 Why these choices fit Northstar

This stack aligns with the architecture already chosen in the Blueprint:

- Tokio provides the runtime and async systems building blocks.
- rustls provides modern TLS defaults and a strong security posture.
- Quinn provides a portable user-space QUIC implementation and keeps low-level protocol logic in a dedicated layer.
- `h3` provides HTTP/3 client/server primitives over QUIC transport traits.
- axum fits the Bridge well because the Bridge is an HTTP service with typed request/response boundaries rather than a custom transport endpoint.
- tracing fits the observability requirements and integrates well with the Tokio ecosystem.

### 8.3 Deliberately deferred stack alternatives

These may be explored later, but are **not** the first implementation baseline:

- replacing Quinn with another QUIC stack
- introducing a second async runtime
- introducing a second web framework for Bridge APIs
- using a custom TLS stack outside rustls for first-party code
- adopting io_uring-specific runtime design as the default architecture

### 8.4 Operational note about fuzzing

`cargo-fuzz` / libFuzzer integration should be treated as a **Linux CI and Linux developer-lab concern**, not a Windows-first workflow, because sanitizer-backed fuzzing support is not the normal Windows path.

---

## 9. Crate graph and dependency boundaries

### 9.1 Crate dependency philosophy

The crate graph MUST be intentionally directional.

A useful mental model:

- lower crates know nothing about applications
- protocol crates know nothing about HTTP servers or QUIC runtime details
- carrier crates know about session traits and QUIC/H3 mechanics, not Bridge business logic
- Bridge crates know about Remnawave adaptation and HTTP APIs, not transport internals
- app crates primarily compose runtime crates and wire configuration together

### 9.2 High-level crate graph

```text
apps/ns-clientd ─────┐
apps/nsctl ──────────┼──> ns-client-runtime
                     │        ├──> ns-client-inbound
                     │        ├──> ns-carrier-h3
                     │        ├──> ns-session
                     │        ├──> ns-auth
                     │        ├──> ns-manifest
                     │        ├──> ns-policy
                     │        ├──> ns-observability
                     │        └──> ns-storage
                     │
apps/ns-gatewayd ────┼──> ns-gateway-runtime
                     │        ├──> ns-carrier-h3
                     │        ├──> ns-session
                     │        ├──> ns-auth
                     │        ├──> ns-policy
                     │        ├──> ns-observability
                     │        └──> ns-storage
                     │
apps/ns-bridge ──────┘──> ns-bridge-api
                              ├──> ns-bridge-domain
                              │      ├──> ns-remnawave-adapter
                              │      ├──> ns-auth
                              │      ├──> ns-manifest
                              │      ├──> ns-policy
                              │      ├──> ns-storage
                              │      └──> ns-observability
                              └──> ns-core / shared types as needed

ns-session ──> ns-core + ns-wire + ns-policy
ns-auth ─────> ns-core
ns-manifest ─> ns-core
ns-carrier-h3 -> ns-session + ns-core + ns-observability
ns-testkit -> almost everything by design, but never the other direction
```

### 9.3 Absolute dependency rules

The following MUST hold:

1. `ns-core` MUST NOT depend on Tokio, axum, Quinn, or Remnawave-specific crates.
2. `ns-wire` MUST NOT depend on network runtimes or Bridge code.
3. `ns-session` MUST NOT directly depend on Quinn, H3, axum, or database clients.
4. `ns-remnawave-adapter` MUST NOT depend on session or carrier crates.
5. `ns-bridge-api` MUST NOT contain Remnawave polling logic.
6. `ns-client-runtime` MUST NOT know Remnawave internals; it only knows Bridge contracts.
7. `ns-gateway-runtime` MUST NOT compile in Bridge HTTP server code.
8. `ns-testkit` MAY depend broadly, but production crates MUST NOT depend on `ns-testkit`.
9. App crates MUST be composition roots, not logic dumpsters.

These rules are not aesthetic. They directly reduce protocol drift and implementation confusion.

---

## 10. Detailed crate responsibilities

### 10.1 `ns-core`

**Role:** Pure domain model crate for protocol and runtime-neutral types.

**Owns:**
- version identifiers
- capability identifiers
- carrier kind identifiers
- error codes
- target/stream/flow identifiers
- shared value objects
- stable enums used across client, gateway, and Bridge where appropriate
- common trait-level types that are runtime-neutral

**Must not own:**
- encoders/decoders
- network sockets
- async runtime logic
- JWT parsing
- manifest download

**Notes:**
- Keep this crate boring.
- Minimize optional features.
- Prefer no heap allocation unless the type genuinely requires it.

### 10.2 `ns-wire`

**Role:** Canonical wire encoder/decoder implementation for the frozen protocol contract.

**Owns:**
- frame codecs
- varint helpers
- bounded readers/writers
- TLV helpers
- malformed-frame classification
- canonical binary fixtures loader helpers

**Must not own:**
- session orchestration
- QUIC stream handling
- token verification
- Bridge API types

**Implementation rules:**
- every parse function has explicit size limits
- unknown-but-preservable values are preserved when required by the spec
- no panics on hostile input
- no I/O in this crate

### 10.3 `ns-session`

**Role:** Session state machine and protocol logic above the wire codec.

**Owns:**
- client and gateway session state machines
- control-stream sequencing rules
- stream and UDP flow bookkeeping
- capability negotiation application
- policy application hooks
- abstract carrier traits
- abstract verifier and clock hooks if needed

**Must not own:**
- direct Quinn types in public interfaces
- Bridge HTTP APIs
- Remnawave-specific types
- database access

**Key architectural rule:**
The session crate is where the frozen Northstar behavior lives. It should be possible to test it almost entirely with mocks or deterministic fake carriers.

### 10.4 `ns-auth`

**Role:** Authentication, token verification, signing abstraction, key-set caching hooks, device binding logic.

**Owns:**
- session token verification
- refresh/credential verification helpers where needed
- issuer/audience checks
- clock-skew and expiration validation helpers
- key rotation hooks and JWKS cache integration points
- replay-detection integration hooks
- device binding policy checks

**Must not own:**
- HTTP server endpoints
- manifest compilation logic
- carrier transport details

**Notes:**
- Keep signing and verification separated internally.
- The public interface should encourage verification by policy, not ad hoc claim peeking.

### 10.5 `ns-manifest`

**Role:** Manifest schema models, validation, compatibility checks, selection helpers, caching behavior.

**Owns:**
- manifest schema types
- signature verification hooks
- compatibility checks against client/gateway versions
- endpoint selection helpers
- profile resolution helpers
- manifest cache metadata

**Must not own:**
- HTTP fetching code tied to a specific client
- token refresh logic
- session data-plane state

### 10.6 `ns-policy`

**Role:** Policy types and decision logic that are transport-neutral.

**Owns:**
- effective session policy model
- target authorization model
- feature-flag application rules at runtime level
- rollout and compatibility policy structures where shared
- policy merge rules from manifest + token + local overrides

**Must not own:**
- Remnawave ingestion
- raw HTTP handlers
- QUIC handling

### 10.7 `ns-observability`

**Role:** Shared tracing, metrics, field naming, redaction, correlation helpers.

**Owns:**
- tracing field constants or helper macros
- metrics naming conventions
- redaction wrappers
- request/session correlation helpers
- standard span creation helpers
- structured event helper utilities

**Must not own:**
- actual business logic
- environment-specific exporters that force all users to link heavy stacks unless feature-gated

### 10.8 `ns-storage`

**Role:** Storage abstraction and concrete implementations used by Bridge and optionally by client/gateway caches.

**Owns:**
- storage traits
- DB model mappings where needed
- migrations for Bridge-owned data
- local cache implementations for file- or embedded-store use
- repository patterns kept intentionally narrow

**Must not own:**
- HTTP endpoints
- Remnawave fetch logic
- session state machine

**Suggested v0.1 posture:**
- Bridge: persistent relational store
- Gateway: mostly stateless, optional local durable caches only where justified
- Client: local file cache plus OS-appropriate secret storage hooks for refresh credentials or similar sensitive material

### 10.9 `ns-carrier-h3`

**Role:** Primary carrier implementation using QUIC + HTTP/3.

**Owns:**
- QUIC endpoint/session establishment
- HTTP/3 tunnel or request/channel orchestration according to Northstar carrier binding
- control stream binding
- relay stream binding
- datagram mapping
- transport-level error translation into session-friendly errors
- transport timers and configuration specific to the `h3` carrier

**Must not own:**
- session policy semantics
- Remnawave logic
- manifest compilation

**Critical rule:**
The carrier crate should be replaceable. It may be difficult, but it should not be architecturally impossible.

### 10.10 `ns-client-inbound`

**Role:** Local client-facing proxy listener layer.

**Owns:**
- SOCKS5 listener
- HTTP CONNECT listener
- local request normalization into runtime target objects
- inbound access controls for local use
- local buffering and backpressure at inbound edge

**Must not own:**
- session token refresh logic
- carrier establishment
- GUI concerns

**Reason to isolate it:**
Local proxy protocol parsing is a separate risk surface from the Northstar wire protocol and should not be mixed into runtime orchestration code.

### 10.11 `ns-client-runtime`

**Role:** Client session orchestrator.

**Owns:**
- bootstrap and import flow from Bridge
- manifest fetch and refresh
- endpoint/profile selection
- token acquisition/refresh orchestration
- carrier session lifecycle
- mapping local inbound requests to Northstar streams/flows
- network-change handling
- graceful reconnects and backoff
- local cache use

**Must not own:**
- Remnawave adapter details
- Bridge server internals
- raw wire codec implementation details beyond calling them through session/carrier layers

### 10.12 `ns-gateway-runtime`

**Role:** Gateway data-plane server runtime.

**Owns:**
- listener bootstrap
- accept loop
- pre-auth defenses
- token validation invocation
- session creation
- policy enforcement
- outbound dialers
- resource-budget enforcement
- drain/shutdown behavior
- telemetry emission at gateway edge

**Must not own:**
- Bridge public API server
- Remnawave ingestion
- manifest signing

### 10.13 `ns-bridge-api`

**Role:** Public Bridge HTTP API surface.

**Owns:**
- request/response models aligned to `/v0/*`
- route handlers
- auth context extraction for Bridge endpoints
- rate limiting at HTTP boundary
- response shaping and status-code discipline
- OpenAPI generation or alignment hooks if used

**Must not own:**
- Remnawave sync loops
- manifest compilation policy logic
- database migrations directly embedded in handlers

### 10.14 `ns-bridge-domain`

**Role:** Bridge business logic and orchestration.

**Owns:**
- user/device/runtime policy projection for Northstar
- manifest compilation
- token issuance orchestration
- lifecycle transitions triggered by Remnawave events or polling
- rollout cohort logic
- gateway inventory resolution
- consistency rules between canonical Bridge state and Remnawave-derived state

**Must not own:**
- HTTP framework code
- raw QUIC/H3 handling

### 10.15 `ns-remnawave-adapter`

**Role:** Remnawave-facing integration crate.

**Owns:**
- adapter client(s)
- webhook verification and normalization
- polling client(s)
- Remnawave model translation into Bridge domain events
- compatibility shim logic across supported Remnawave versions

**Must not own:**
- Northstar session logic
- carrier transport logic
- Bridge HTTP handlers

### 10.16 `ns-testkit`

**Role:** Test-only utilities across the workspace.

**Owns:**
- fake carrier implementations
- fake token issuers/verifiers
- deterministic clock
- deterministic randomness helpers where appropriate
- fixture loading helpers
- fake Remnawave server helpers
- net-chaos harness helpers

**Must not own:**
- production code paths used in release binaries

---

## 11. Application binaries and their roles

### 11.1 `apps/ns-clientd`

Primary client daemon/service.

Responsibilities:
- run as console process in dev mode
- run as Windows service in production-oriented Windows deployments
- optionally support foreground mode for diagnosis
- host local proxy listeners
- maintain active Bridge session bootstrap state
- maintain active Northstar carrier session(s)

Not in scope for v0.1:
- polished GUI
- embedded updater
- TUN mode

### 11.2 `apps/nsctl`

CLI administration and diagnostic tool.

Responsibilities:
- import/bootstrap from Bridge URL or import code
- inspect manifest cache
- rotate or clear local state
- print health/status
- trigger connectivity diagnostics
- dump sanitized diagnostic bundles

This tool is especially important for developer workflows and supportability.

### 11.3 `apps/ns-gatewayd`

Gateway service.

Responsibilities:
- bind QUIC/H3 listener(s)
- enforce token and policy gates
- forward allowed traffic
- expose health and metrics endpoints as configured
- support graceful drain and rolling restart behavior

### 11.4 `apps/ns-bridge`

Bridge service binary.

Responsibilities:
- expose `/v0/*` public APIs
- run Remnawave ingestion workers
- compile and sign manifests
- issue session tokens
- manage device and rollout state
- expose operator and health surfaces as separately protected endpoints

---

## 12. Runtime architecture by component

## 12.1 Client runtime architecture

Recommended internal subsystems:

1. **Bootstrap Manager**
   - handles first import
   - validates bootstrap payloads
   - stores initial trust anchors and Bridge endpoint metadata

2. **Manifest Manager**
   - fetches full manifest
   - performs conditional revalidation
   - applies compatibility checks
   - stages manifest updates before activation

3. **Credential Manager**
   - stores refresh credential or equivalent long-lived client credential
   - requests short-lived session token
   - handles expiry/refresh jitter
   - supports revocation handling

4. **Endpoint/Profile Selector**
   - chooses gateway endpoint
   - chooses carrier profile
   - applies backoff and failover
   - records health observations

5. **Carrier Session Manager**
   - creates and owns active carrier connection
   - opens control stream
   - manages relay streams and datagrams
   - handles reconnect logic

6. **Inbound Manager**
   - accepts SOCKS5/HTTP CONNECT requests
   - maps them into session actions
   - enforces local resource bounds

7. **State Cache**
   - caches manifest and other safe local state
   - tracks last known endpoint health
   - stores minimal diagnostics state

8. **Supervisor / Shutdown Coordinator**
   - coordinates task lifecycle
   - ensures no orphan background tasks on shutdown
   - drains local listeners and active streams cleanly

### 12.2 Gateway runtime architecture

Recommended internal subsystems:

1. **Listener Supervisor**
   - owns network listeners
   - handles rolling configuration changes where possible

2. **Pre-auth Guard**
   - rate-limits unauthenticated attempts
   - bounds handshake work
   - applies cheap rejection early

3. **Session Admission**
   - validates session token
   - checks audience/issuer/expiry/device policy
   - initializes session policy and quotas

4. **Session Engine**
   - runs control-stream state machine
   - manages relay stream and UDP flow tables
   - mediates between session layer and outbound connectors

5. **Outbound Connectors**
   - handles TCP dialers
   - handles UDP socket setup
   - applies target authorization
   - enforces per-policy restrictions

6. **Budget Enforcer**
   - enforces stream count, flow count, bytes-in-flight, handshake deadlines, idle timeouts

7. **Drain Manager**
   - supports graceful restart and maintenance windows

8. **Telemetry Layer**
   - emits metrics, spans, structured events
   - supports high-cardinality guardrails

### 12.3 Bridge runtime architecture

Recommended internal subsystems:

1. **Public API Service**
   - serves client-facing `/v0/*`
   - isolated from admin/operator API surface

2. **Remnawave Ingestion Workers**
   - polling pipeline
   - webhook validation pipeline
   - normalization into domain events

3. **Domain Projection Engine**
   - projects Remnawave state into Northstar device/user/runtime state
   - computes effective policy

4. **Manifest Compiler**
   - resolves gateway inventory
   - attaches profile references
   - signs manifest payloads

5. **Token Issuer**
   - issues short-lived session tokens
   - tracks signing material versions
   - records issuance metadata required for debugging and abuse handling

6. **Device Registry**
   - binds client install/device state
   - tracks local Bridge-side device metadata
   - reconciles with Remnawave lifecycle state

7. **Rollout Controller**
   - applies profile rollouts and kill switches
   - supports staged deployment by cohort, geography, or operator tags

8. **State Store**
   - stores Bridge canonical state and operational metadata

---

## 13. Concurrency model and task management rules

Northstar is a networked async system. Concurrency decisions must be explicit.

### 13.1 Runtime posture

- Tokio multi-thread runtime SHOULD be the default for Bridge and Gateway.
- Client runtime MAY use multi-thread or current-thread in some modes, but the default v0.1 client daemon should use Tokio in a conventional configuration.
- Long-lived background tasks MUST be tracked by a supervisor.
- Detached tasks without ownership are prohibited.

### 13.2 Task lifecycle rules

Every significant task SHOULD have:

- a parent owner
- cancellation path
- shutdown deadline behavior
- tracing context
- error propagation strategy

### 13.3 Channels and backpressure

- Prefer bounded `mpsc` channels over unbounded channels.
- Use explicit queue sizes tied to resource budgets.
- Dropping behavior MUST be deliberate and documented.
- High-volume telemetry channels MUST have sampling or bounded buffering.

### 13.4 Blocking work

- CPU-heavy or blocking operations MUST NOT run accidentally on async executor threads.
- Certificate/key loading, compression, filesystem scanning, and certain database tasks MUST be isolated appropriately.
- `spawn_blocking` is allowed only when justified and measured.

### 13.5 Cancellation and drain discipline

- Session tasks MUST stop promptly when the carrier closes or a terminal protocol error occurs.
- Gateway shutdown MUST reject new admissions before killing in-flight work.
- Client shutdown MUST stop local listeners before tearing down active session state.

---

## 14. Error model and result-handling policy

### 14.1 Library crates

Library crates SHOULD:

- expose typed errors
- classify errors into actionable categories
- avoid leaking transport-specific internals across boundaries
- preserve enough context for tracing and diagnosis

### 14.2 Binary crates

Binary crates MAY use `anyhow`-style top-level error aggregation, but only at the final composition boundary.

### 14.3 Error taxonomy

Northstar code SHOULD distinguish between at least these classes:

- protocol violation
- auth failure
- policy rejection
- transport failure
- timeout
- upstream connect failure
- resource budget exceeded
- stale or invalid manifest
- Bridge dependency failure
- operator misconfiguration
- internal invariant failure

### 14.4 Panic policy

- Panic on untrusted input is forbidden.
- Panics SHOULD be reserved for impossible internal invariant corruption only.
- Recoverable domain failure must remain a normal error path.

---

## 15. Configuration policy

### 15.1 Configuration layering

Each application SHOULD support configuration layering in this order:

1. compiled defaults
2. config file
3. environment variables
4. CLI flags

CLI flags win over environment, environment wins over file, file wins over defaults.

### 15.2 Configuration formats

Recommended:

- local app config: **TOML**
- manifest and wire/public API documents: frozen by spec and typically JSON-shaped
- deployment templates: may use YAML or Helm-style templates later, but this is outside the Rust crate contracts

### 15.3 Configuration validation

- Validate at startup before binding listeners when possible.
- Unknown fields in static local config SHOULD default to rejection rather than silent ignore.
- Feature-gated config blocks SHOULD fail clearly if used without required build/runtime support.

### 15.4 Configuration separation

Separate:

- public Bridge config
- operator/admin Bridge config
- client runtime config
- gateway runtime config
- test-only config

Do not use one mega-struct for the whole repository.

---

## 16. Storage and persistence model

### 16.1 General policy

Persist only what must be persisted.

Northstar should bias toward:

- stateless gateway runtime where practical
- Bridge as canonical policy/device store
- thin client cache with careful handling of secrets

### 16.2 Client-side persistence

Client SHOULD persist:

- Bridge bootstrap metadata
- manifest cache and validation metadata
- last-known endpoint/profile health summaries
- minimal diagnostics bundle metadata

Client SHOULD NOT persist:

- long-term verbose traffic history
- raw session payloads
- sensitive tokens in plaintext on disk

On Windows, secret-bearing client material SHOULD be stored using OS-appropriate secret storage mechanisms when feasible rather than raw flat files.

### 16.3 Gateway-side persistence

Gateway SHOULD remain mostly stateless in v0.1.

Acceptable persistent data:

- local config
- optional trust/key material cache
- bounded operational snapshots if needed for restart support

Gateway SHOULD NOT become the canonical source for user/device entitlement state.

### 16.4 Bridge-side persistence

Bridge SHOULD persist:

- device records
- refresh or client credential metadata
- manifest issuance metadata
- signing key metadata and rotation state
- rollout cohort assignments
- normalized Remnawave lifecycle snapshots or event offsets where necessary
- audit-relevant but privacy-scoped operator events

For multi-instance Bridge deployments, a real database is the baseline expectation. SQLite is fine for dev and maybe small single-node experiments, but not the architectural default.

---

## 17. Observability implementation rules

### 17.1 Observability goals

Northstar observability should help answer:

- why a client cannot connect
- why a gateway rejected a session
- whether a carrier profile is degrading
- whether Remnawave ingestion is stale
- whether a rollout caused regressions
- whether a parser or auth path is under attack

### 17.2 Tracing policy

Use structured tracing throughout the workspace.

Standard field families SHOULD include:

- `session.id`
- `device.id`
- `user.ref` (privacy-safe reference, not raw PII)
- `gateway.id`
- `bridge.req_id`
- `carrier.kind`
- `profile.id`
- `stream.id`
- `flow.id`
- `error.code`
- `policy.epoch`

### 17.3 Logging policy

- No secrets in logs.
- No full tokens in logs.
- No raw manifest bodies in normal logs.
- Use structured fields over stringly-typed mega-messages.
- Separate operator diagnostics from default user-level logs.

### 17.4 Metrics policy

Metrics SHOULD cover:

- handshake success/failure counts
- session admission latency
- manifest fetch result counts
- token issuance/verification result counts
- stream/flow counts
- gateway outbound dial outcomes
- datagram vs stream-fallback usage
- Bridge ingestion freshness
- Remnawave webhook verification outcomes
- rate-limit hits
- memory and queue pressure signals

### 17.5 Privacy posture

- Per-user and per-device labels MUST be tightly controlled.
- High-cardinality labels MUST be reviewed explicitly.
- Diagnostic bundles MUST support redaction.

---

## 18. Security implementation rules at code level

### 18.1 Secret handling

- Treat refresh credentials, signing keys, session tokens, and private key material as secrets.
- Use explicit secret-bearing wrapper types or redaction-aware newtypes.
- Secrets MUST NOT implement naive `Debug` that dumps values.

### 18.2 Verification discipline

- Token verification MUST happen before expensive admission work when possible.
- Manifest signature verification MUST happen before activation.
- Webhook signature verification MUST happen before event acceptance.
- Clock handling in auth code MUST be injectable for tests.

### 18.3 Resource budget discipline

- Pre-auth paths MUST enforce strict deadlines and bounded buffers.
- Per-session and per-connection budgets MUST be represented in code, not just docs.
- Any “temporary” unlimited queue or buffer is a bug unless explicitly justified.

### 18.4 Unsafe/FFI posture

- Avoid FFI in the first implementation unless essential.
- If a platform integration later needs FFI, isolate it behind a tiny crate or module with its own review requirements.

### 18.5 Protocol drift prevention

- The wire contract MUST be represented centrally, not re-encoded differently in multiple crates.
- Fixture-based conformance tests MUST guard parser/serializer behavior.

---

## 19. Carrier abstraction strategy

### 19.1 Why abstraction matters

Northstar is supposed to remain adaptable. That only works if the session core does not become secretly coupled to the first carrier.

### 19.2 Carrier trait boundary

The carrier layer SHOULD expose a narrow interface sufficient for:

- control stream open/bind
- relay stream open/bind
- datagram send/receive
- close/error reporting
- carrier capability reporting

The exact trait surface may evolve, but the principle must hold: **session logic talks to a carrier abstraction, not directly to Quinn/H3 types in most of the codebase**.

### 19.3 `h3` carrier implementation guidance

The `ns-carrier-h3` crate SHOULD isolate:

- QUIC endpoint creation
- TLS/ALPN setup for the carrier profile
- HTTP/3 session/channel creation
- datagram capability detection
- transport-specific error normalization
- qlog/transport telemetry hooks when implemented

### 19.4 Future carrier readiness without premature complexity

The first codebase does not need a polished plugin system for carriers.
It does need:

- one stable carrier abstraction
- one well-implemented carrier
- enough modularity to add another carrier later without rewriting `ns-session`

---

## 20. Remnawave integration implementation strategy

### 20.1 Non-fork baseline

Northstar uses Remnawave as an external control plane and entitlement source. The Rust workspace must reflect that separation.

### 20.2 Adapter boundary

All Remnawave-specific logic MUST remain inside `ns-remnawave-adapter` plus Bridge domain orchestration.

That includes:

- webhook signature processing
- polling API clients
- raw subscription material retrieval and translation
- version compatibility shims for supported Remnawave panel ranges
- normalization of lifecycle events into Bridge domain events

### 20.3 What the rest of the codebase should see

The rest of the codebase should see normalized concepts such as:

- user enabled / disabled
- device allowed / revoked
- subscription plan state
- gateway inventory view
- metadata relevant to rollout or client support

The session, carrier, and client runtime layers should never need to know how Remnawave itself represented those things.

### 20.4 Why this matters

This keeps the non-fork integration realistic:

- Remnawave changes affect the adapter and Bridge domain layer
- the data plane remains stable
- the client remains Bridge-centric, not Remnawave-centric

---

## 21. Windows-first client considerations

The user environment for this project is Windows-centric, so the workspace should not treat Windows as an afterthought.

### 21.1 Client delivery posture

The client side should support these modes:

1. **Developer mode:** foreground console process
2. **Service mode:** background daemon/service
3. **Diagnostics mode:** verbose, support-friendly execution with sanitized bundle export

### 21.2 Path conventions

A sensible Windows posture is:

- machine-wide config under a machine-scoped application data directory
- per-user cache under a user-local application data directory
- logs under a predictable machine- or user-scoped log directory depending on mode

Do not scatter ad hoc files all over the working directory.

### 21.3 Secret storage posture

For sensitive long-lived client-side credentials, prefer OS-supported secret storage mechanisms where practical instead of plaintext flat-file storage.

### 21.4 Service integration posture

The service wrapper should be thin. Core runtime logic must stay testable without the Windows service host.

This means:

- service-specific entrypoint code in app crate only
- runtime logic lives in `ns-client-runtime`
- no direct service manager calls from protocol or carrier crates

### 21.5 Deferred Windows work

These are useful later, but not first milestones:

- GUI / system tray UX
- Wintun/TUN mode
- installer/updater polish
- deep OS policy integration

---

## 22. Gateway deployment posture

### 22.1 v0.1 deployment expectation

Gateway is primarily a server-side component. The first serious deployments will usually be Linux-oriented even if client development is Windows-first.

### 22.2 Service model

Gateway should be implemented as a standard long-running service with:

- static config file
- health endpoint
- metrics endpoint
- graceful drain support
- clear shutdown behavior

### 22.3 Statelessness preference

The gateway should avoid accumulating operator state. It should derive entitlement from tokens and local config/policy sources defined by the spec, not from becoming its own control plane.

### 22.4 Deferred gateway work

Useful later but not first-line implementation work:

- advanced eBPF/eXpress Data Path instrumentation
- custom allocators as default policy
- kernel bypass experiments
- multi-region smart control built into the gateway itself

---

## 23. Bridge service design details

### 23.1 Public vs operator surfaces

The Bridge MUST separate:

- public client APIs (`/v0/*`)
- internal operator/admin surfaces
- health/readiness/metrics surfaces

These surfaces may share process space in v0.1, but the code must still keep them logically separate.

### 23.2 Bridge process model

A practical Bridge service can start as one binary with separate modules and route groups, provided the domain boundaries remain clean.

### 23.3 Manifest compiler design

The manifest compiler should be a distinct domain component, not code embedded inside HTTP handlers.

Inputs:
- normalized user/device state
- rollout cohort state
- gateway inventory
- supported carrier profiles
- compatibility rules

Outputs:
- signed manifest
- metadata needed for caching and diagnostics

### 23.4 Token issuer design

Token issuance should likewise be a distinct domain service with:

- signer abstraction
- policy input model
- TTL strategy
- key-version tagging
- audit-safe issuance record

---

## 24. Coding conventions and style rules

### 24.1 Formatting and linting

The repository SHOULD enforce:

- rustfmt
- clippy on strict-but-practical settings
- no unchecked warnings in CI for main workspace targets

### 24.2 Module structure

Keep modules shallow enough to navigate, but deep enough to preserve boundaries.

Good pattern:

```text
crate/
  src/
    lib.rs
    error.rs
    types.rs
    codec/
    state/
    tests/
```

Bad pattern:
- a single 4,000-line `mod.rs`
- ten nested folders with one tiny file each and no cohesion

### 24.3 Trait usage policy

Use traits where they buy one of these things:

- test substitution
- carrier abstraction
- storage abstraction
- signing/verifier abstraction
- clock/randomness abstraction where necessary

Do not create traits just to avoid calling a concrete type directly once.

### 24.4 Macro policy

- Avoid macros for ordinary control flow.
- Small helper macros for tracing fields or fixture definitions are acceptable.
- Wire protocol behavior must remain readable in normal Rust code.

### 24.5 Serialization policy

- Keep spec-shaped structs separate from persistence models when their lifecycles differ.
- Prefer explicit serde attributes over magical hidden defaults.
- Use `deny_unknown_fields` thoughtfully for local config and Bridge API models where appropriate.

---

## 25. Testing architecture inside the workspace

### 25.1 Test pyramid

Each crate should participate in the following pyramid where relevant:

1. unit tests
2. property tests
3. fixture/conformance tests
4. integration tests
5. fuzz tests
6. benchmark/regression tests

### 25.2 Per-crate expectations

- `ns-wire`: heavy fixture, parser, and malformed-input coverage
- `ns-session`: state-machine and sequencing tests
- `ns-auth`: token validation matrix tests and clock skew tests
- `ns-manifest`: schema and compatibility tests
- `ns-carrier-h3`: transport-integration and datagram/fallback tests
- `ns-client-runtime`: reconnect, refresh, and inbound-to-session mapping tests
- `ns-gateway-runtime`: admission, policy, and resource-budget tests
- `ns-bridge-domain`: lifecycle and projection tests
- `ns-remnawave-adapter`: sandbox contract tests and reorder/idempotency tests

### 25.3 Test execution tooling

A pragmatic testing toolchain includes:

- standard `cargo test` for local fast iteration
- `cargo nextest` for faster and more isolated workspace test execution in CI and serious local runs
- `proptest` for property testing
- `cargo-fuzz` for fuzzing on supported Linux workflows
- `criterion` for microbenchmarks where appropriate

### 25.4 Fixture policy

Frozen fixtures MUST live outside ad hoc inline strings wherever practical.

Suggested fixture domains:

- wire
- manifest
- token
- webhook
- Remnawave adapter inputs
- malformed corpus
- interop transcripts

---

## 26. Benchmarking and performance engineering plan

### 26.1 What to benchmark first

The first benchmark targets should not be vanity throughput charts. They should answer practical questions:

- wire codec throughput and allocation behavior
- session engine overhead per stream/flow
- token verification cost
- manifest verification and parse cost
- gateway admission latency under load
- datagram vs stream-fallback overhead
- bounded-memory behavior under many concurrent sessions

### 26.2 Benchmark placement

- microbenchmarks in `benches/` or crate-local `benches/`
- scenario benchmarks in `integration/` or dedicated lab tools
- release-gating perf checks only after baseline stabilization

### 26.3 Performance anti-patterns to avoid

- benchmarking only localhost happy path
- tuning before wire correctness is stable
- introducing `unsafe` for micro-gains without proof
- chasing synthetic max throughput while handshake failure behavior is still weak

---

## 27. Build, packaging, and release engineering

### 27.1 Build outputs

Minimum release artifacts for v0.1 should include:

- `ns-clientd` binaries
- `nsctl` binaries
- `ns-gatewayd` binaries
- `ns-bridge` binaries
- checksums
- version metadata
- changelog snippets or release notes

### 27.2 Recommended target matrix

At minimum, plan for:

- client: `x86_64-pc-windows-msvc`
- gateway: `x86_64-unknown-linux-gnu`
- bridge: `x86_64-unknown-linux-gnu`

Good follow-up targets:

- `aarch64-unknown-linux-gnu`
- Windows ARM64 if there is operator demand

### 27.3 Packaging posture

Start simple:

- zipped/tarred release artifacts
- service install scripts for dev/staging
- example config templates

Later:

- Windows installer packaging
- signed packages
- automated updater design

### 27.4 Reproducibility posture

The release process SHOULD aim for:

- pinned toolchain
- deterministic build inputs where practical
- version stamping from CI or tagged source only
- artifact signing as the project matures

---

## 28. CI/CD plan

### 28.1 Required CI lanes

A practical initial CI matrix SHOULD include:

1. format + lint
2. workspace tests
3. nextest run
4. dependency/supply-chain checks
5. docs/build sanity
6. Linux fuzz or fuzz-regression lane
7. integration lane for Bridge + fake Remnawave + gateway + client
8. optional benchmark regression lane

### 28.2 Platform coverage

At minimum:

- Linux CI for most heavy checks
- Windows CI for client build/test sanity

### 28.3 Gating policy

Main branch SHOULD reject merges when:

- frozen fixture tests fail
- public API/schema diff checks fail
- supply-chain policy checks fail
- required integration tests fail
- known fuzz regressions reappear

---

## 29. `xtask` and developer automation strategy

### 29.1 Why `xtask`

Northstar will need repeatable developer workflows beyond plain Cargo commands. The `xtask` pattern is appropriate for:

- fixture generation and validation
- schema/OpenAPI export tasks
- local dev environment setup helpers
- version stamping
- release prep checks
- deterministic test corpus management

### 29.2 Good `xtask` candidates

- `cargo xtask verify-fixtures`
- `cargo xtask export-openapi`
- `cargo xtask dev-cert`
- `cargo xtask gen-sample-config`
- `cargo xtask ci-local`
- `cargo xtask bundle-diagnostics`

### 29.3 What should not go into `xtask`

- production runtime logic
- hidden protocol transformations
- critical security logic only available through build scripts

---

## 30. AI-agent implementation workflow

Northstar is a good candidate for AI-assisted development, but only if the repository structure and rules prevent drift.

### 30.1 AI-agent guardrails

AI coding agents MUST NOT:

- change the frozen wire format without explicit approval
- add ad hoc fields to protocol frames
- mix Remnawave-specific code into session/carrier crates
- introduce unbounded queues casually
- add silent fallback behavior that weakens verification or policy checks
- replace typed errors with opaque string errors in library crates

### 30.2 Good AI task packets

The repository should make it easy to assign narrow task packets like:

- implement `CLIENT_HELLO` codec + fixture tests in `ns-wire`
- implement session state transitions for `OPEN_STREAM` in `ns-session`
- implement Bridge manifest conditional-fetch handler in `ns-bridge-api`
- implement Remnawave webhook normalization in `ns-remnawave-adapter`
- implement SOCKS5 inbound parser in `ns-client-inbound`
- add gateway admission rate-limit metrics in `ns-gateway-runtime`

### 30.3 Mandatory review pattern for AI contributions

Every AI-generated change SHOULD be reviewed for:

- crate-boundary compliance
- spec compliance
- allocation and timeout behavior
- logging/redaction correctness
- test coverage against the relevant fixture or state matrix

### 30.4 Why the workspace plan matters for AI

A messy repository makes AI output worse.
A well-layered repository makes AI output narrower, more testable, and easier to review.

---

## 31. Phase-by-phase implementation order inside the workspace

### Phase A — Repository bootstrap

Deliver:
- workspace skeleton
- pinned toolchain
- lint/test/CI skeleton
- empty crates with README/module docs
- root policy docs
- fixture directories

Exit criteria:
- builds cleanly
- CI runs on Linux and Windows
- no crate-boundary violations in initial graph

### Phase B — Core contract implementation

Deliver:
- `ns-core`
- `ns-wire`
- fixture loader helpers
- initial conformance tests

Exit criteria:
- frozen v0.1 frame fixtures pass
- malformed input tests exist for every frame family

### Phase C — Session engine

Deliver:
- `ns-session`
- fake carrier test harness in `ns-testkit`
- session sequencing tests

Exit criteria:
- major happy-path and protocol-violation paths covered
- state machine works without real QUIC stack

### Phase D — Auth + manifest + policy

Deliver:
- `ns-auth`
- `ns-manifest`
- `ns-policy`

Exit criteria:
- signed manifest acceptance path works in tests
- token verification and policy derivation tests pass

### Phase E — H3 carrier

Deliver:
- `ns-carrier-h3`
- carrier integration tests
- datagram and stream-fallback coverage

Exit criteria:
- client/gateway can establish real carrier session in lab
- transport errors map correctly into session outcomes

### Phase F — Gateway runtime

Deliver:
- `ns-gateway-runtime`
- `apps/ns-gatewayd`

Exit criteria:
- policy and quota enforcement functional
- graceful drain implemented

### Phase G — Client runtime and local inbound

Deliver:
- `ns-client-inbound`
- `ns-client-runtime`
- `apps/ns-clientd`
- `apps/nsctl`

Exit criteria:
- local SOCKS5 / HTTP CONNECT to Northstar path works
- manifest refresh and reconnect logic present
- Windows build and service-mode entrypoint exist

### Phase H — Bridge runtime and Remnawave adapter

Deliver:
- `ns-bridge-domain`
- `ns-bridge-api`
- `ns-remnawave-adapter`
- `apps/ns-bridge`

Exit criteria:
- Bridge can bootstrap client, issue tokens, and compile manifests from normalized Remnawave state
- sandbox integration tests pass

### Phase I — Hardening and release gates

Deliver:
- fuzz harnesses
- nextest config
- benchmark baseline
- abuse and chaos tests
- packaging scripts

Exit criteria:
- release gates from the Security Test & Interop Plan are met for the intended milestone

---

## 32. Suggested workspace conventions in practice

### 32.1 Root `Cargo.toml` pattern

A practical root workspace configuration should:

- declare members explicitly
- use resolver `2` or current recommended resolver for the pinned toolchain
- centralize common dependency versions where it reduces drift
- avoid exposing internal crates as publishable by default unless needed

### 32.2 Root `.cargo/config.toml`

Useful defaults may include:

- target-specific runner helpers for tests when needed
- common rustflags for local dev or selected CI jobs
- aliases for repeated commands

These settings must remain understandable. Avoid a magic config file that surprises contributors.

### 32.3 Feature flag policy

Suggested feature categories:

- `metrics`
- `otlp`
- `dangerous-test-helpers`
- `dev-tools`
- `windows-service`
- `datagram`

Feature flags SHOULD represent meaningful optional capabilities, not patch over architecture confusion.

---

## 33. Minimal file and path conventions

### 33.1 Documentation files

At minimum, each crate SHOULD have:

- `README.md`
- crate-level docs in `lib.rs`
- a short “owns / does not own” section

### 33.2 Fixture naming

Examples:

```text
fixtures/wire/hello/client_hello_v1_ok.bin
fixtures/wire/hello/client_hello_v1_truncated.bin
fixtures/manifest/v1/minimal_ok.json
fixtures/token/jws/session_token_valid_01.txt
fixtures/bridge/bootstrap/bootstrap_ok_01.json
fixtures/remnawave/webhook/user_revoked_01.json
```

### 33.3 Integration test naming

Prefer explicit test names like:

- `e2e_client_gateway_tcp_relay.rs`
- `e2e_bridge_manifest_rotation.rs`
- `e2e_remnawave_user_disable_revokes_access.rs`

---

## 34. What is intentionally deferred but should stay visible

These items are too much for the first implementation wave, but they should remain in the project memory:

### 34.1 Protocol/data-plane backlog

- full IP tunnel mode
- secondary carriers (`raw_quic`, `h2_tls`, others)
- multipath support
- FEC / erasure coding
- session resumption / 0-RTT policy work
- transport profile hot-swap without reconnect where feasible
- advanced active-probing response strategies

### 34.2 Client backlog

- GUI app / tray app
- TUN mode on Windows and other platforms
- installer / updater
- richer diagnostics UX
- mobile clients

### 34.3 Gateway backlog

- advanced autoscaling hooks
- eBPF-heavy observability
- NUMA-aware tuning
- custom congestion experiments if carrier layer later supports them

### 34.4 Bridge backlog

- HSM/KMS-backed signing path
- multi-region Bridge topology
- operator dashboard or admin API expansion
- richer rollout targeting and analytics
- advanced inventory control plane for gateways

### 34.5 Process/governance backlog

- ADR repository for major architecture decisions
- formal compatibility policy document
- contributor certification matrix for security-sensitive areas
- independent implementation program beyond the Rust reference stack

---

## 35. Risks this workspace plan is specifically trying to reduce

This plan is intentionally defensive against several common failure modes.

### 35.1 Protocol drift risk

Reduced by:
- central wire crate
- frozen fixtures
- session crate boundaries

### 35.2 Dependency spaghetti risk

Reduced by:
- directional crate graph
- strict “must not own” rules
- isolated Remnawave adapter

### 35.3 AI-agent chaos risk

Reduced by:
- narrow task packets
- explicit crate ownership
- review guardrails

### 35.4 Platform sprawl risk

Reduced by:
- isolating Windows-specific integration in app/runtime edges
- not making every crate platform-aware

### 35.5 Premature-optimization risk

Reduced by:
- performance work focused on measured hotspots
- avoiding `unsafe` and allocator tricks by default
- deferring exotic runtime and network stack experiments

---

## 36. Recommended initial TODO map by crate

### `ns-core`
- define core ids and enums
- define shared value objects
- define session-neutral error codes and capability types

### `ns-wire`
- implement frame envelope encode/decode
- implement per-frame codecs
- add binary fixture tests
- add malformed corpus regression tests

### `ns-session`
- define session traits
- implement client and gateway state machines
- implement stream/flow registry logic
- implement protocol violation handling paths

### `ns-auth`
- define verifier trait and claims model
- implement JWT/JWKS verification profile
- implement clock injection for tests
- add device binding validation hooks

### `ns-manifest`
- model schema v1
- implement validation and compatibility checks
- implement selection helpers
- implement signature verification hooks

### `ns-policy`
- define effective policy model
- implement target authorization helpers
- implement quota merge logic

### `ns-carrier-h3`
- define transport config mapping from carrier profile
- implement QUIC/H3 connect path
- map control streams and relay streams
- map datagram and fallback paths

### `ns-client-inbound`
- implement SOCKS5 parser and handshake
- implement HTTP CONNECT parser and handshake
- expose normalized target requests

### `ns-client-runtime`
- bootstrap flow
- manifest refresh loop
- token refresh flow
- endpoint/profile selection
- reconnect and shutdown behavior

### `ns-gateway-runtime`
- listener setup
- pre-auth rate limits
- token verification integration
- outbound dial/connect and flow lifecycle
- graceful drain

### `ns-bridge-domain`
- normalized lifecycle state model
- manifest compiler
- token issuer orchestration
- device registry logic
- rollout controller

### `ns-bridge-api`
- `/v0/*` routes
- request/response models
- auth/rate-limit middleware
- error-to-HTTP mapping

### `ns-remnawave-adapter`
- polling client
- webhook verification
- event normalization
- compatibility shims

### `ns-testkit`
- fake carrier
- fake verifier
- deterministic clock
- fake Remnawave server
- fixture helper library

---

## 37. Definition of done for workspace-level maturity

Northstar v0.1 implementation workspace should be considered structurally mature when:

1. all main crates exist with stable boundaries
2. frozen wire fixtures are enforced in CI
3. the session engine can be tested without real network transport
4. Remnawave logic is isolated to adapter + Bridge domain crates
5. client, gateway, and Bridge binaries all compose from reusable runtime crates
6. Windows client builds and Linux server builds both work in CI
7. supply-chain and lint gates exist
8. fuzzing and regression corpora exist for hostile-input surfaces
9. observability fields and redaction rules are standardized
10. AI-generated patches can be scoped to one or two crates without destabilizing the whole codebase

That is the point where the codebase stops being “an experiment” and becomes a maintainable protocol implementation.

---

## 38. Final guidance

Do not try to make the first Rust workspace “perfect forever.”

Do make it:

- layered
- explicit
- hostile-input-safe
- test-first where the wire contract matters
- Windows-conscious on the client side
- Linux-practical on the server side
- disciplined enough that future carriers, TUN mode, and deeper hardening work remain possible

The first implementation should optimize for **clarity, correctness, and replaceable boundaries**.
That is what gives Northstar the best chance of becoming a serious long-lived open-source protocol project instead of another clever but fragile prototype.

---

## Appendix A — Recommended official references for the chosen stack

These are useful primary references for the implementation team:

- Tokio: https://tokio.rs/  
- Tokio runtime docs: https://docs.rs/tokio/latest/tokio/runtime/  
- rustls: https://docs.rs/rustls/latest/rustls/  
- rustls manual: https://docs.rs/rustls/latest/rustls/manual/  
- Quinn: https://docs.rs/quinn/latest/quinn/  
- quinn-proto: https://docs.rs/quinn-proto/latest/quinn_proto/  
- h3 crate: https://docs.rs/h3/latest/h3/  
- axum: https://docs.rs/axum/latest/axum/  
- tracing: https://docs.rs/tracing/latest/tracing/  
- cargo-nextest: https://nexte.st/  
- Rust Fuzz Book / cargo-fuzz: https://rust-fuzz.github.io/book/cargo-fuzz.html  
- cargo-deny: https://embarkstudios.github.io/cargo-deny/  
- RustSec / cargo-audit: https://rustsec.org/  
- Criterion.rs: https://bheisler.github.io/criterion.rs/book/  
- proptest: https://docs.rs/proptest/latest/proptest/  

---

## Appendix B — Suggested ADR topics to create soon after repository bootstrap

1. Why Tokio/rustls/Quinn/h3 is the v0.1 baseline
2. Why Remnawave integration is isolated behind the Bridge
3. Why the session crate is transport-neutral
4. Why Windows client and Linux gateway have different first-class priorities
5. Why first-party crates default to `forbid(unsafe_code)`
6. Why the gateway is mostly stateless
7. Why Bridge persistence is required for serious deployments
8. Why TUN mode is deferred from v0.1

