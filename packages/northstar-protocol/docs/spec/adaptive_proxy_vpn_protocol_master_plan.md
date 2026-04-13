
# Development Plan — Open-Source Adaptive Proxy/VPN Protocol Suite in Rust

> This roadmap is intentionally **over-scoped**. It is designed to help the team build the right thing first, keep the long-term vision visible, and avoid forgetting “too much for now” items that may become important later.

## 1. Executive Summary

This document describes a development plan for an open-source Rust project that aims to deliver a **modern, adaptive, high-performance proxy/VPN protocol suite** with:

- an **own Rust server implementation**,
- an **own cross-platform client/agent**,
- **Remnawave used as control plane and subscription delivery layer**,
- no fork of Remnawave,
- a clean separation between:
  - a **stable session core**,
  - **replaceable transport/carrier layers**,
  - **remotely switchable deployment profiles**,
  - and a **custom client experience** distributed through subscription mechanisms.

The core strategic choice is:

- **Do not try to force a brand-new wire protocol into native Xray/Remnawave node execution from day one.**
- Instead, build:
  1. a **Rust edge/server**,
  2. a **Rust client/agent**,
  3. a **Remnawave bridge/integration layer**,
  4. and a **subscription/app bootstrap flow** that makes the custom client easy to distribute and operate.

The project should be treated not as “one perfect protocol”, but as a **protocol suite**:

- **Control plane** for users, devices, quotas, subscription delivery, rollout, and policy.
- **Session core** for authentication, channel establishment, stream/datagram handling, and capability negotiation.
- **Carrier layer** for standards-based transports (for example QUIC + HTTP/3 first, with fallback families later).
- **Profile layer** for remotely changeable deployment behavior, operational tuning, and compatibility policy.

The long-term objective is not only throughput or latency. The actual target is a protocol family that is:

- easier to operate than current ad-hoc stacks,
- easier to evolve safely,
- easier to audit,
- less brittle under changing network conditions,
- and easier to integrate into a modern open-source ecosystem.

---

## 2. Planning Basis and Ecosystem Assumptions

This plan assumes the following integration reality:

1. **Remnawave remains the external control plane**, not the packet-processing engine for the new protocol.
2. **Remnawave already supports multiple subscription families and client-aware delivery**, which makes it useful as a bootstrap and distribution layer for a custom client.
3. **Remnawave Node is centered on Xray-core**, so a truly new protocol is not going to become “native” inside existing Remnawave Node execution without deeper upstream/core work.
4. **Remnawave’s newer subscription and subscription-page capabilities are strong enough to support the “own client + own protocol + no panel fork” strategy**.
5. **The project should use standards-based transports first**, especially where proxying and tunneling over QUIC/HTTP/3 already have IETF foundations.

This implies a practical operating model:

- Remnawave stores and manages **users, quotas, policies, squads, templates, subscription UX, and lifecycle events**.
- A new **custom bridge service** synchronizes the relevant state into the Rust edge/control system.
- The custom client identifies itself to Remnawave subscription infrastructure and receives either:
  - a custom bootstrap manifest,
  - or app-config instructions,
  - while still fitting into the broader subscription-based user workflow.

---

## 3. Product Vision

### 3.1 Primary Goal

Build an open-source Rust-based protocol suite that can provide:

- secure remote access,
- proxy mode,
- future VPN/tunnel mode,
- strong operability,
- fast iteration,
- high observability,
- and controlled transport/profile agility.

### 3.2 Product Definition

The product is **not just a wire protocol**. It is a complete system:

- protocol specification,
- server implementation,
- client implementation,
- subscription/bootstrap format,
- control-plane bridge,
- operator tooling,
- observability stack,
- interoperability and test corpus,
- release and governance model.

### 3.3 Success Criteria

The project succeeds when it has all of the following:

- a published protocol specification,
- a reproducible Rust reference implementation,
- a production-grade client on at least desktop and one mobile platform,
- a Remnawave integration path that does not require forking the panel,
- a stable rollout model,
- comprehensive testing and operational runbooks,
- and a community process that can sustain long-term evolution.

---

## 4. Strategic Constraints

### 4.1 What We Will Optimize For

- **Correctness before cleverness**
- **Operational clarity before hidden magic**
- **Interoperability before novelty**
- **Replaceable outer layers before a giant monolithic protocol**
- **Simple, auditable authentication and policy plumbing**
- **Strong telemetry and debugging from the first prototype**
- **Fast rollback and profile switching**
- **Cross-platform viability**
- **Open-source maintainability**

### 4.2 What We Will Avoid

- custom cryptography,
- protocol complexity for its own sake,
- tight coupling to one ecosystem runtime,
- premature kernel-bypass optimization,
- undocumented “magic” heuristics,
- brittle special cases hidden in code instead of explicit profiles,
- and feature growth without versioning discipline.

### 4.3 Explicit Non-Goals for Early Phases

Do **not** try to ship all of these in the first production-capable milestone:

- multipath transport,
- post-quantum experiments,
- custom congestion-control research,
- kernel-space dataplane,
- enterprise SSO and multi-tenant billing,
- in-protocol plugin VM,
- mesh routing,
- full site-to-site networking,
- or custom silicon/offload work.

These are valid later ideas, but they must not compromise the first stable architecture.

---

## 5. Design Principles

### 5.1 Stable Core, Replaceable Exterior

The session core must remain compact and stable. Transport/carrier choices must be pluggable.

### 5.2 Standards First

When a standard already solves a lower-layer problem, use it rather than inventing a new mechanism.

### 5.3 Version Everything

Version the wire format, the manifest, the control API, the profile bundle, and the test vectors.

### 5.4 Capabilities, Not Assumptions

Every endpoint should negotiate capabilities explicitly:

- stream support,
- datagram support,
- tunnel mode support,
- compression policy,
- telemetry policy,
- feature flags,
- and compatibility options.

### 5.5 Operational Agility Over “One Perfect Fingerprint”

The project should not depend on one rigid transport persona. It should support controlled profile updates, controlled fallbacks, and safe rollbacks.

### 5.6 Testability Is a Feature

No feature is complete without:

- spec text,
- logs,
- counters,
- conformance tests,
- fuzz targets where applicable,
- and failure injection coverage.

### 5.7 Default-Safe Behavior

Unknown extensions should be handled predictably. Feature downgrades should be explicit. Failure modes should preserve user safety and service stability.

---

## 6. Target Architecture

## 6.1 Major Components

### A. Remnawave Control Layer

Responsibilities:

- user lifecycle,
- quotas,
- device/subscription UX,
- squads/templates/routing rules,
- subscription page,
- optional HWID/device-related behaviors,
- administrative workflows,
- webhook source of truth for user changes.

### B. Bridge / Adapter Layer

Responsibilities:

- consume Remnawave webhooks,
- periodically reconcile state against Remnawave APIs,
- transform user/account policy into protocol-specific credentials and edge policies,
- generate client bootstrap manifests,
- maintain mapping between Remnawave entities and protocol entities,
- drive rollout/profile assignment.

### C. Protocol Control Plane

Responsibilities:

- credential issuance,
- key rotation,
- session ticket issuance,
- edge discovery,
- region selection,
- rollout channels,
- profile distribution,
- revocation,
- and possibly device registration.

### D. Rust Edge / Data Plane

Responsibilities:

- accept incoming sessions,
- authenticate clients,
- open and manage streams/datagrams,
- apply policies and quotas,
- proxy TCP and UDP,
- later support IP tunnel mode,
- emit metrics/logs/traces,
- and obey remote profiles.

### E. Client / Local Agent

Responsibilities:

- bootstrap from subscription,
- authenticate,
- expose local proxy endpoints,
- optionally provide TUN mode,
- update profiles,
- handle diagnostics,
- surface UX for device/account state,
- and report relevant client telemetry.

### F. Observability / Safety Layer

Responsibilities:

- logs,
- structured events,
- traces,
- qlog/transport debugging,
- metrics,
- crash reports,
- session audit records,
- redaction/scrubbing rules,
- and release health checks.

---

## 6.2 Logical Data Flow

1. Operator manages users and policy in Remnawave.
2. Remnawave emits lifecycle events via webhook or is polled/reconciled by the bridge.
3. Bridge converts user/account state into protocol-specific state.
4. Client obtains a bootstrap manifest through the subscription flow.
5. Client connects to control/edge services.
6. Control plane issues session-specific or short-lived access material.
7. Edge authenticates and serves stream/datagram/tunnel traffic.
8. Telemetry flows back into metrics/logging and rollout systems.
9. Profile changes can be published without redesigning the session core.

---

## 7. Product Modes

### 7.1 Mode A — Proxy Mode (Earliest Priority)

Support:

- TCP streams,
- UDP datagrams,
- local SOCKS5 / HTTP proxy exposure,
- per-user policy and quotas.

This is the shortest path to useful functionality.

### 7.2 Mode B — Enhanced Proxy Mode

Add:

- better multiplexing,
- improved session resumption,
- richer edge selection,
- stronger device management,
- richer telemetry,
- and advanced rollout/profile handling.

### 7.3 Mode C — Tunnel / VPN Mode

Add:

- full or split-tunnel routing,
- virtual interface support,
- route and DNS policy,
- IP packet transport,
- mobile-aware tunnel behavior.

This should come only after proxy mode is genuinely solid.

---

## 8. Recommended Repository and Workspace Layout

```text
repo/
  README.md
  LICENSE
  SECURITY.md
  CONTRIBUTING.md
  CODE_OF_CONDUCT.md

  docs/
    architecture/
    adr/
    runbooks/
    threat-model/
    release/
    benchmarks/

  specs/
    session-core/
    auth/
    carriers/
    profiles/
    subscription-manifest/
    error-codes/
    test-vectors/

  crates/
    core-types/
    core-codec/
    core-state/
    auth/
    policy/
    transport-quic/
    transport-h3/
    transport-h2/
    datagram/
    tunnel/
    edge-server/
    client-agent/
    client-cli/
    local-proxy/
    tun-platform/
    telemetry/
    bridge-remnawave/
    manifest/
    admin-api/
    test-harness/
    fuzz-common/

  fuzz/
  integration/
  benchmarks/
  packaging/
  scripts/
  examples/
```

### Workspace Rules

- no giant “everything” crate,
- explicit crate boundaries,
- semver discipline for public crates,
- feature flags for optional components,
- avoid exposing unstable internals too early,
- keep protocol types separate from platform glue,
- and isolate unsafe/platform-specific code into narrow modules.

---

## 9. Program Streams

This project should be managed as parallel streams, not one long linear to-do list.

### 9.1 Stream A — Protocol & Specification

- session core,
- auth,
- error model,
- extension registry,
- profile format,
- manifest format,
- carrier mapping,
- compatibility rules.

### 9.2 Stream B — Rust Server / Edge

- acceptor,
- authentication,
- stream/datagram engines,
- proxy handlers,
- quotas,
- observability,
- operational lifecycle.

### 9.3 Stream C — Client / Agent

- bootstrap,
- config,
- local proxy,
- TUN later,
- update channel,
- diagnostics,
- platform packaging.

### 9.4 Stream D — Control Plane / Bridge

- Remnawave integration,
- webhook receiver,
- state reconciliation,
- profile delivery,
- manifest generation,
- admin surfaces.

### 9.5 Stream E — Security & Review

- threat model,
- protocol review,
- fuzzing,
- secrets management,
- credential lifecycle,
- audit prep.

### 9.6 Stream F — Testing / Benchmarking / Interop

- deterministic tests,
- chaos/failure injection,
- compatibility corpus,
- load tests,
- packet-loss lab,
- NAT/rebinding tests,
- long-haul soak tests.

### 9.7 Stream G — Release, Documentation, Governance

- release process,
- changelogs,
- signed artifacts,
- docs site,
- contribution rules,
- compatibility matrix,
- deprecation policy.

---

# 10. Detailed Phased Roadmap

## Phase 00 — Charter, Naming, and Success Definition

### Objective

Create a project charter before any implementation pressure distorts the architecture.

### Deliverables

- working project name,
- one-page mission statement,
- scope statement,
- list of explicit non-goals,
- initial success metrics,
- program governance draft,
- risk appetite statement.

### Detailed Tasks

1. Define whether the initial public promise is:
   - “modern proxy protocol suite”,
   - “remote access platform”,
   - or “proxy now, tunnel later”.
2. Decide what will be shipped publicly in the first useful release.
3. Write the public narrative:
   - why this exists,
   - why Rust,
   - why Remnawave integration,
   - why a custom client is acceptable.
4. Define a naming scheme for:
   - the suite,
   - the session core,
   - the manifest,
   - profiles,
   - carriers,
   - and rollout channels.
5. Define project values and architecture red lines.

### Exit Criteria

- everyone can explain the project in two minutes,
- scope is narrow enough for an MVP,
- and the first release promise does not imply impossible compatibility claims.

### Deferred / Overkill Hook

- brand system,
- mascot,
- foundation/legal wrapper,
- trademark policy.

---

## Phase 01 — Landscape Study and Baseline Measurements

### Objective

Build a measured baseline so future work is not driven by vibes.

### Deliverables

- comparison matrix of current alternatives,
- operational pain matrix,
- benchmark methodology document,
- initial lab topology,
- baseline reports.

### Detailed Tasks

1. Benchmark representative stacks for:
   - TCP proxying,
   - UDP behavior,
   - reconnection under path change,
   - packet loss,
   - jitter,
   - and CPU/memory cost.
2. Separate “product UX issues” from “transport issues”.
3. Document lessons from:
   - WireGuard-like minimalism,
   - QUIC-based proxy approaches,
   - HTTP/3 proxying/tunneling standards,
   - and subscription-driven client ecosystems.
4. Define which metrics matter most:
   - connection establishment,
   - goodput,
   - p95/p99 latency,
   - session survival,
   - memory per connection,
   - CPU per throughput band,
   - and failure recovery.

### Exit Criteria

- baseline lab exists,
- baseline metrics are reproducible,
- future improvements can be measured against something real.

### Deferred / Overkill Hook

- Internet-scale distributed benchmarking,
- cross-continent external measurement volunteers.

---

## Phase 02 — Governance, Repo Bootstrap, and Engineering Standards

### Objective

Make the project maintainable before it becomes large.

### Deliverables

- repository bootstrap,
- CI skeleton,
- coding standards,
- lint/format rules,
- ADR template,
- issue templates,
- release note format.

### Detailed Tasks

1. Create the repository structure.
2. Add:
   - Rustfmt,
   - Clippy,
   - cargo-deny,
   - cargo-audit,
   - license checks,
   - dependency update policy.
3. Set CI rules:
   - format check,
   - lint check,
   - unit tests,
   - docs build,
   - minimal security scan.
4. Create ADR process:
   - every major design decision gets a short ADR.
5. Decide on public API stability policy for crates.
6. Create a compatibility matrix template.
7. Define ownership areas for maintainers.

### Exit Criteria

- contributors know how to add code safely,
- CI fails on obvious hygiene regressions,
- architecture decisions stop living only in chat history.

### Deferred / Overkill Hook

- RFC process for public contributors,
- bot-assisted review gates,
- automated changelog generation.

---

## Phase 03 — Threat Model, Abuse Model, and Trust Boundaries

### Objective

Define exactly what the system is protecting against, and what it is not.

### Deliverables

- threat model document,
- trust-boundary diagram,
- abuse model,
- secrets inventory,
- data classification map.

### Detailed Tasks

1. Define actors:
   - legitimate user,
   - operator,
   - compromised client,
   - compromised edge,
   - passive observer,
   - active disruptor,
   - buggy integration service.
2. Define protected assets:
   - user identity,
   - credentials,
   - session keys,
   - traffic confidentiality,
   - policy integrity,
   - server availability,
   - logs and telemetry.
3. Define trust zones:
   - client device,
   - Remnawave,
   - bridge,
   - protocol control plane,
   - edge nodes,
   - observability pipeline.
4. Define abuse concerns:
   - stolen bootstrap data,
   - replay,
   - downgrade,
   - abusive connection churn,
   - traffic amplification,
   - quota bypass attempts,
   - compromised device impersonation,
   - provisioning drift.
5. Decide which events must always be auditable.

### Exit Criteria

- threat model reviewed and approved,
- every future feature can point to its threat implications,
- no one is allowed to say “we’ll secure it later”.

### Deferred / Overkill Hook

- formal threat trees,
- public security whitepaper,
- independent red-team program.

---

## Phase 04 — Product Scope, Modes, and Operator Workflow

### Objective

Define what operators and users will actually do with the product.

### Deliverables

- operator workflow map,
- user journey map,
- mode split document,
- rollout channel design,
- supportability requirements.

### Detailed Tasks

1. Map the operator journey:
   - create user,
   - assign region/profile,
   - distribute subscription,
   - rotate credentials,
   - inspect diagnostics,
   - revoke access.
2. Map the user journey:
   - import subscription,
   - install client,
   - sign in/bootstrap,
   - connect,
   - switch region/profile,
   - diagnose failures.
3. Define MVP feature scope:
   - likely proxy mode first,
   - tunnel mode later.
4. Define rollout channels:
   - stable,
   - candidate,
   - experimental,
   - internal.
5. Decide how much self-update behavior the client will have.

### Exit Criteria

- product scope matches actual operator and user workflows,
- MVP is clearly separated from “future ideal”.

### Deferred / Overkill Hook

- multi-tenant MSP operator flows,
- enterprise policy packs,
- white-label support.

---

## Phase 05 — Remnawave Integration Contract

### Objective

Turn “compatible with Remnawave without a fork” into an explicit integration architecture.

### Deliverables

- bridge service architecture,
- webhook receiver design,
- reconciliation design,
- custom client detection strategy,
- manifest bootstrap strategy,
- Remnawave data mapping document.

### Detailed Tasks

1. Define which Remnawave entities are source-of-truth:
   - users,
   - subscription identity,
   - quotas,
   - squads/routing outcomes,
   - device-related settings if used.
2. Build a bridge contract:
   - webhook-driven updates for user lifecycle,
   - periodic reconciliation to heal drift,
   - idempotent provisioning into protocol control plane.
3. Define mapping rules:
   - Remnawave user -> protocol account,
   - host/profile/route -> edge region assignment,
   - quota/policy -> session policy bundle.
4. Define custom client identification:
   - stable custom user-agent,
   - optional device headers,
   - response-rule/client-detection compatibility.
5. Define bootstrap delivery:
   - app-config,
   - manifest link,
   - or direct custom subscription payload.
6. Define how the subscription page will promote the custom client:
   - featured app entry,
   - app instructions,
   - platform download links,
   - localized help.
7. Define how optional HWID/device semantics will be supported by the custom client.
8. Decide whether protocol-specific metadata is stored:
   - only in the bridge,
   - or mirrored into Remnawave metadata fields where appropriate.

### Exit Criteria

- an operator can manage users in Remnawave and see them propagated to the custom system,
- the custom client has a clear bootstrap path,
- and the architecture does not pretend the new protocol is natively executed by Remnawave Node.

### Deferred / Overkill Hook

- direct admin plugin UI,
- richer visual dashboards inside Remnawave via upstream collaboration,
- bidirectional metadata sync.

---

## Phase 06 — Protocol Vocabulary, Naming, Versioning, and Registries

### Objective

Prevent semantic chaos before bytes hit the wire.

### Deliverables

- terminology document,
- versioning policy,
- extension registry model,
- error namespace,
- compatibility policy.

### Detailed Tasks

1. Define canonical names:
   - session,
   - channel,
   - stream,
   - datagram,
   - tunnel,
   - ticket,
   - profile,
   - carrier,
   - capability,
   - manifest.
2. Version separately:
   - session-core spec,
   - manifest spec,
   - profile schema,
   - control-plane API,
   - client/server minimum compatibility.
3. Define registries for:
   - frame types,
   - capability IDs,
   - error codes,
   - transport profiles,
   - telemetry fields,
   - reserved/experimental ranges.
4. Decide extension rules:
   - unknown extension handling,
   - GREASE/reserved values,
   - safe negotiation behavior.

### Exit Criteria

- no ambiguity about names,
- protocol evolution has a roadmap,
- future contributors do not invent ad-hoc semantics.

### Deferred / Overkill Hook

- public registry website,
- compatibility linter for manifests/profiles.

---

## Phase 07 — Identity, Authentication, and Credential Lifecycle

### Objective

Design a robust account and session model without relying on a single long-lived static secret.

### Deliverables

- auth model spec,
- device identity policy,
- session credential format,
- rotation and revocation plan,
- bootstrap trust chain document.

### Detailed Tasks

1. Define the bootstrap identity:
   - subscription-derived bootstrap record,
   - operator-issued account identity,
   - and optional device registration state.
2. Prefer short-lived, signed access grants for sessions.
3. Define credential tiers:
   - account credential,
   - device credential,
   - session ticket,
   - recovery/reset flow.
4. Define revocation behavior:
   - immediate revoke,
   - next-refresh revoke,
   - device-only revoke.
5. Define replay and downgrade protections.
6. Define minimum logging requirements around auth failures.
7. Decide how offline grace periods work.
8. Define whether device binding is:
   - optional,
   - recommended,
   - or enforced only when Remnawave policy enables it.

### Exit Criteria

- auth can be explained clearly,
- rotation and revocation are operationally feasible,
- credentials are not permanently static by accident.

### Deferred / Overkill Hook

- hardware-backed device keys,
- WebAuthn-style account bootstrap,
- threshold-signature control-plane signing.

---

## Phase 08 — Session Core v0 Specification

### Objective

Write the core session protocol before writing the production transport code.

### Deliverables

- session-core v0 spec,
- state machine diagrams,
- handshake transcript definition,
- frame definitions,
- close/error semantics draft.

### Detailed Tasks

1. Define handshake phases:
   - transport ready,
   - protocol hello,
   - capability negotiation,
   - auth exchange,
   - session established.
2. Define channel types:
   - control stream,
   - reliable stream channels,
   - datagram channels,
   - tunnel channel placeholder.
3. Define control messages:
   - open,
   - accept,
   - reject,
   - flow update,
   - policy update,
   - close,
   - ping/keepalive.
4. Define stream lifecycle.
5. Define datagram lifecycle.
6. Define session-level feature negotiation.
7. Define transcript binding for negotiated features.
8. Define invariants:
   - unknown fields,
   - unsupported capabilities,
   - malformed frame behavior.

### Exit Criteria

- a reviewer can understand the session core without reading code,
- wire behavior is specified well enough for independent implementation.

### Deferred / Overkill Hook

- machine-readable schema generation,
- formal state-machine modeling.

---

## Phase 09 — Carrier Layer Strategy and Profiles v0

### Objective

Specify how the session core rides on standards-based carriers.

### Deliverables

- carrier strategy document,
- primary carrier spec mapping,
- fallback carrier plan,
- profile schema v0.

### Detailed Tasks

1. Select the initial carrier family:
   - QUIC + HTTP/3 as primary candidate,
   - fallback family later if needed.
2. Define carrier responsibilities vs session-core responsibilities.
3. Define profile structure:
   - carrier choice,
   - endpoint list,
   - ALPN/profile identifiers,
   - timeout policy,
   - retry policy,
   - telemetry level,
   - compatibility toggles.
4. Define profile publication and rollback behavior.
5. Define what may change dynamically and what requires a client upgrade.
6. Define minimum viable fallback behavior.
7. Define a compatibility matrix between profile version and client version.

### Exit Criteria

- the architecture does not conflate session and carrier,
- profiles are first-class configuration objects,
- profile changes are operationally safe.

### Deferred / Overkill Hook

- profile pack signing service,
- region-specific profile canaries,
- per-ASN rollout channels.

---

## Phase 10 — Error Model, Close Semantics, and Retry Discipline

### Objective

Make failure behavior predictable and debuggable.

### Deliverables

- error code registry,
- close semantics spec,
- retry matrix,
- client UX mapping.

### Detailed Tasks

1. Define session vs channel vs transport errors.
2. Distinguish:
   - fatal protocol violation,
   - unsupported feature,
   - auth failure,
   - quota denial,
   - transient edge overload,
   - remote target failure.
3. Define when retries are allowed.
4. Define backoff rules.
5. Define connection racing policy if multiple edges are available.
6. Define what error details are safe to expose to clients and users.
7. Define structured log fields for every major failure class.

### Exit Criteria

- support engineers can diagnose failures,
- client behavior under failure is deterministic,
- retries do not create self-inflicted load spikes.

### Deferred / Overkill Hook

- multilingual end-user diagnostics catalog,
- failure fingerprint clustering.

---

## Phase 11 — Policy Model, Quotas, and Operator Controls

### Objective

Translate operator intent into enforceable session behavior.

### Deliverables

- policy schema,
- quota semantics,
- edge policy mapping,
- operator override rules.

### Detailed Tasks

1. Define policies for:
   - allowed modes,
   - connection counts,
   - bandwidth quotas,
   - idle timeouts,
   - destination restrictions if needed,
   - split-tunnel permissions later.
2. Define how quotas are enforced:
   - edge-local,
   - control-plane synchronized,
   - eventual consistency boundaries.
3. Define policy caching rules.
4. Define how bridge maps Remnawave lifecycle and quotas into protocol policy.
5. Decide what must be hard-fail vs soft-fail on control-plane outage.

### Exit Criteria

- policy behavior is explicit,
- edge and control plane agree on enforcement semantics.

### Deferred / Overkill Hook

- hierarchical policies,
- time-window policies,
- commercial billing rule packs.

---

## Phase 12 — Rust Workspace Foundation and Core Libraries

### Objective

Create the minimal technical foundation for implementation work.

### Deliverables

- workspace bootstrap,
- core types crate,
- codec crate,
- config crate,
- tracing/logging scaffolding,
- test fixture crate.

### Detailed Tasks

1. Build the core type system:
   - IDs,
   - frame enums,
   - config structs,
   - error types.
2. Build serialization/codec boundaries.
3. Build a config loading and validation layer.
4. Standardize:
   - tracing spans,
   - structured logging fields,
   - metrics naming.
5. Create deterministic test fixtures and sample manifests/profiles.
6. Add property-based tests for codecs where appropriate.

### Exit Criteria

- protocol code can be written on clean abstractions,
- basic config and codec tests exist.

### Deferred / Overkill Hook

- code generation from spec schemas,
- no_std experiments for embedded use.

---

## Phase 13 — TLS, Certificates, Trust Stores, and Transport Security Plumbing

### Objective

Turn abstract security into concrete implementation rules.

### Deliverables

- certificate/trust model,
- TLS config policy,
- key rotation runbook,
- local dev PKI strategy.

### Detailed Tasks

1. Decide where TLS material lives:
   - edge only,
   - control plane,
   - local dev/test CA.
2. Standardize TLS settings and minimums.
3. Standardize certificate rotation behavior.
4. Define local development certificate flow.
5. Decide how the client validates trust anchors.
6. Define what is pinned, what is discoverable, and what is configurable.
7. Add telemetry for certificate/trust failures.

### Exit Criteria

- there is one approved transport security configuration path,
- operators can rotate certificates without guessing.

### Deferred / Overkill Hook

- automated ACME orchestration,
- hardware security modules,
- keyless edge patterns.

---

## Phase 14 — Edge Server Skeleton and Acceptor Pipeline

### Objective

Get the first nontrivial server path running.

### Deliverables

- edge server skeleton,
- listener lifecycle,
- acceptor pipeline,
- session bootstrap handler,
- graceful shutdown behavior.

### Detailed Tasks

1. Implement:
   - config loading,
   - listener start,
   - structured startup logs,
   - health endpoint or health signal.
2. Build the acceptor pipeline:
   - transport accepted,
   - session negotiation,
   - auth hook,
   - policy lookup,
   - session creation.
3. Add:
   - connection ID logging,
   - metrics counters,
   - error labels.
4. Define and test graceful shutdown:
   - drain,
   - stop accept,
   - session close semantics.

### Exit Criteria

- server accepts lab connections,
- startup/shutdown is deterministic,
- session bootstrap is observable.

### Deferred / Overkill Hook

- hot reload of all config classes,
- per-listener runtime reconfiguration.

---

## Phase 15 — Control Stream and Reliable Stream Channels

### Objective

Implement the first useful traffic path: multiplexed reliable streams.

### Deliverables

- control stream handler,
- stream open/close primitives,
- backpressure model,
- TCP proxy MVP.

### Detailed Tasks

1. Implement the control stream.
2. Implement stream lifecycle:
   - open,
   - data,
   - EOF,
   - reset,
   - close.
3. Define per-stream and per-session flow control behavior.
4. Implement local TCP proxy handling on the client side.
5. Implement remote connect on the edge side.
6. Add timeout behavior and logging for half-open streams.
7. Add integration tests:
   - HTTP over proxy,
   - large transfers,
   - concurrent streams,
   - abrupt remote close.

### Exit Criteria

- basic TCP proxying works correctly,
- backpressure works,
- multiple streams can coexist without corruption.

### Deferred / Overkill Hook

- advanced prioritization,
- stream classes,
- partial reliability experiments.

---

## Phase 16 — Datagram / UDP Mode

### Objective

Deliver first-class UDP support without turning the session model into chaos.

### Deliverables

- datagram channel support,
- UDP proxy MVP,
- datagram policy rules,
- UDP integration tests.

### Detailed Tasks

1. Define datagram framing and routing.
2. Handle:
   - target metadata,
   - idle cleanup,
   - MTU considerations,
   - fragmentation policy at system boundaries.
3. Implement client-side UDP association logic.
4. Implement edge-side UDP relay logic.
5. Define flow-control or rate-limit semantics suitable for datagram use.
6. Create test cases:
   - DNS,
   - QUIC target traffic,
   - bursty packet patterns,
   - packet loss/reorder.

### Exit Criteria

- UDP proxying works in the lab,
- session model remains debuggable,
- datagram behavior is documented.

### Deferred / Overkill Hook

- UDP acceleration modes,
- NAT behavior heuristics,
- advanced aggregation.

---

## Phase 17 — Client Agent MVP

### Objective

Ship the first real client that users can run.

### Deliverables

- CLI client,
- desktop/background agent MVP,
- local SOCKS5/HTTP endpoints,
- config storage,
- diagnostics UI/CLI output.

### Detailed Tasks

1. Implement bootstrap manifest fetch.
2. Implement local config storage and update flow.
3. Implement edge discovery and connect logic.
4. Expose local proxy endpoints.
5. Add:
   - logs,
   - diagnostics dump,
   - version info,
   - profile info,
   - connectivity test command.
6. Define secure local secret storage strategy per platform.
7. Decide whether early client UX is:
   - CLI only,
   - or minimal GUI wrapper.

### Exit Criteria

- a friendly alpha tester can install the client and connect,
- support engineers can collect enough diagnostics to help.

### Deferred / Overkill Hook

- polished GUI,
- auto-updater,
- deep OS integration,
- accessibility pass.

---

## Phase 18 — Manifest Format and Subscription Bootstrap

### Objective

Define how the client is provisioned from a subscription-driven world.

### Deliverables

- bootstrap manifest spec,
- signing rules,
- profile bundle format,
- client import flow.

### Detailed Tasks

1. Define manifest contents:
   - account ID reference,
   - profile set,
   - control-plane endpoints,
   - trust anchors,
   - rollout channel,
   - policy flags,
   - support URLs,
   - diagnostics hints.
2. Define whether manifests are:
   - static JSON,
   - signed JSON,
   - or encrypted/signed bundles.
3. Define refresh rules:
   - periodic fetch,
   - on-demand fetch,
   - cache TTL,
   - retry rules.
4. Define migration path for manifest schema evolution.
5. Define end-user import UX:
   - single click,
   - custom URI scheme,
   - QR code,
   - app-config entry.

### Exit Criteria

- the custom client can be bootstrapped in a subscription-like workflow,
- manifest evolution is future-safe.

### Deferred / Overkill Hook

- layered manifests,
- per-device manifests,
- encrypted manifest fields,
- offline bootstrap package.

---

## Phase 19 — Remnawave Bridge MVP

### Objective

Make the architecture useful to a real operator.

### Deliverables

- webhook receiver,
- state reconciler,
- user/account mapper,
- manifest generator,
- edge provisioning sync.

### Detailed Tasks

1. Build a secure webhook receiver:
   - signature verification,
   - timestamp validation,
   - idempotency handling,
   - event persistence for audit/replay.
2. Support user lifecycle events:
   - create,
   - modify,
   - revoke,
   - disable,
   - delete,
   - quota-related updates if available.
3. Build reconciliation jobs to recover from missed events.
4. Build mapping tables between Remnawave IDs and protocol IDs.
5. Build manifest generation endpoint or artifact pipeline.
6. Build device-awareness integration if optional HWID mode is enabled.
7. Add observability:
   - webhook processing success/failure,
   - drift counters,
   - provisioning latency.

### Exit Criteria

- changes in Remnawave propagate into the custom system reliably,
- missed events do not permanently desynchronize the deployment.

### Deferred / Overkill Hook

- bidirectional status sync into panel metadata,
- richer operator dashboard overlays.

---

## Phase 20 — Subscription Page and App Distribution Integration

### Objective

Make custom-client onboarding operator-friendly and user-friendly.

### Deliverables

- subscription page integration plan,
- app listing content,
- platform-specific install instructions,
- QR/bootstrap flows,
- localized content set.

### Detailed Tasks

1. Define how the custom app appears to users:
   - featured app,
   - direct download link,
   - platform filter,
   - import instructions.
2. Define how user-agent/client detection routes requests to the right response.
3. Define fallback behavior for unknown clients.
4. Define download security:
   - signed binaries,
   - checksums,
   - provenance documentation.
5. Define support content:
   - install docs,
   - error explanations,
   - HWID/device-limit explanations if used.

### Exit Criteria

- onboarding works from subscription page to installed client,
- support burden is manageable.

### Deferred / Overkill Hook

- app store integrations,
- Telegram mini-app deep linking,
- browser extension bootstrap helpers.

---

## Phase 21 — Observability and Diagnostics v1

### Objective

Make the system operable before it is scaled.

### Deliverables

- metrics catalog,
- structured log schema,
- tracing policy,
- qlog/transport capture strategy,
- user-safe diagnostics bundle format.

### Detailed Tasks

1. Define the minimum metrics set:
   - session counts,
   - auth failures,
   - stream counts,
   - datagram counts,
   - latency buckets,
   - error counts,
   - profile distribution,
   - reconnect behavior.
2. Define structured logs with stable field names.
3. Instrument major control flow with traces/spans.
4. Add a diagnostics bundle command on the client.
5. Define PII redaction rules.
6. Define high-cardinality guardrails.
7. Build dashboards and runbooks.

### Exit Criteria

- the system can be debugged without packet captures as the first resort,
- metrics and logs are good enough for production triage.

### Deferred / Overkill Hook

- session playback lab,
- automated anomaly clustering,
- support bundle upload service.

---

## Phase 22 — Conformance Tests and Interoperability Corpus

### Objective

Stop protocol drift between client and server.

### Deliverables

- protocol conformance suite,
- compatibility corpus,
- golden vectors,
- negative-test set.

### Detailed Tasks

1. Write test vectors for:
   - handshake,
   - auth,
   - stream open/close,
   - datagram open/use/close,
   - malformed inputs,
   - unsupported capabilities.
2. Create compatibility fixtures across client/server versions.
3. Add randomized ordering and malformed frame tests.
4. Ensure independent implementations would have enough material to validate against.
5. Add compatibility gates to release CI.

### Exit Criteria

- every protocol change must pass conformance tests,
- compatibility promises are enforceable.

### Deferred / Overkill Hook

- independent third-party interoperability bake-off.

---

## Phase 23 — Fuzzing, Hardening, and Parser Safety

### Objective

Treat input handling as a security-critical subsystem.

### Deliverables

- fuzz targets,
- corpus seeds,
- sanitizer-enabled test jobs,
- crash triage workflow.

### Detailed Tasks

1. Fuzz:
   - frame decoders,
   - manifest parser,
   - profile parser,
   - handshake state transitions,
   - control messages.
2. Add sanitizers and debug assertions where practical.
3. Maintain corpus minimization and regression cases.
4. Define crash triage rules:
   - reproduce,
   - minimize,
   - classify,
   - patch,
   - add regression tests.
5. Run fuzzing continuously or at least on protected branches.

### Exit Criteria

- all public parsers have fuzz coverage,
- parser bugs are not treated as normal product bugs.

### Deferred / Overkill Hook

- distributed fuzz farm,
- external fuzz bounty.

---

## Phase 24 — Performance Lab and Network-Adversity Benchmarks

### Objective

Measure reality under difficult but legitimate network conditions.

### Deliverables

- performance harness,
- adversity matrix,
- reproducible benchmark scripts,
- benchmark report template.

### Detailed Tasks

1. Build test matrix for:
   - clean network,
   - packet loss,
   - jitter,
   - reordering,
   - path changes,
   - constrained uplink,
   - bufferbloat,
   - connection churn.
2. Measure:
   - connection setup,
   - recovery,
   - throughput,
   - goodput,
   - memory,
   - CPU.
3. Compare profile variants.
4. Add long-running soak tests.
5. Track regressions per commit or release candidate.

### Exit Criteria

- performance claims are backed by lab data,
- profile decisions are evidence-based.

### Deferred / Overkill Hook

- region-specific public test network,
- crowdsourced measurement SDK.

---

## Phase 25 — Resilience, Profile Agility, and Safe Fallback Design

### Objective

Enable controlled adaptation without turning the product into undocumented behavior.

### Deliverables

- profile rollout controller design,
- rollback rules,
- safe fallback matrix,
- profile health dashboard.

### Detailed Tasks

1. Define profile lifecycle:
   - draft,
   - internal,
   - canary,
   - stable,
   - deprecated,
   - disabled.
2. Define how clients receive profile changes:
   - pull,
   - push hint,
   - channel-based rollout.
3. Define rollback guarantees.
4. Define guardrails:
   - minimum supported client version,
   - incompatible setting blocklists,
   - circuit breakers.
5. Define per-profile health metrics and alerting.
6. Define what changes are allowed through remote profiles and what requires a binary update.

### Exit Criteria

- operators can change deployment behavior safely,
- rollouts are observable and reversible.

### Deferred / Overkill Hook

- regional automated canary promotion,
- profile simulation before rollout,
- operator “what if” planner.

---

## Phase 26 — Linux TUN Prework and VPN/Tunnel Design

### Objective

Prepare tunnel mode without derailing proxy mode.

### Deliverables

- tunnel architecture document,
- route/DNS policy model,
- Linux TUN MVP design,
- split-tunnel rules document.

### Detailed Tasks

1. Decide whether tunnel mode uses:
   - separate carrier/profile rules,
   - or shares the same session core with a tunnel channel.
2. Define route management behavior.
3. Define DNS handling policy.
4. Define split vs full tunnel semantics.
5. Define platform-specific abstraction boundaries.
6. Define how tunnel mode interacts with quotas and policy.
7. Build Linux-only proof-of-concept path first.

### Exit Criteria

- tunnel mode design is concrete,
- proxy mode is not compromised by premature platform complexity.

### Deferred / Overkill Hook

- macOS Network Extension,
- Windows WFP/TUN deep integration,
- mobile always-on VPN modes.

---

## Phase 27 — Tunnel / VPN MVP

### Objective

Ship the first controlled tunnel implementation after proxy mode is stable.

### Deliverables

- Linux TUN MVP,
- tunnel channel implementation,
- route manager,
- DNS manager,
- tunnel diagnostics.

### Detailed Tasks

1. Implement tunnel channel semantics.
2. Carry IP packets with explicit policy boundaries.
3. Add route and DNS management on Linux.
4. Add split-tunnel support if the design allows.
5. Add tunnel-specific observability:
   - route install state,
   - DNS state,
   - packet counters,
   - MTU issues.
6. Add integration tests for:
   - connectivity,
   - split tunnel,
   - DNS resolution,
   - reconnects.

### Exit Criteria

- Linux tunnel mode works in controlled environments,
- tunnel mode is not yet declared “finished” on all platforms.

### Deferred / Overkill Hook

- mobile-native tunnel UX,
- route conflict auto-resolution,
- enterprise policy imports.

---

## Phase 28 — Cross-Platform Packaging and Update Strategy

### Objective

Move from lab software to distributable software.

### Deliverables

- packaging strategy,
- signed builds,
- version channel policy,
- update mechanism design,
- platform matrix.

### Detailed Tasks

1. Define supported platforms:
   - Linux,
   - Windows,
   - macOS,
   - Android,
   - iOS (later and carefully).
2. Define artifact formats per platform.
3. Sign binaries and publish checksums/provenance.
4. Define update channels:
   - stable,
   - candidate,
   - experimental.
5. Define client/server compatibility guarantees.
6. Decide on auto-update behavior and opt-in/opt-out semantics.

### Exit Criteria

- operators and users can install supported builds safely,
- rollback and downgrade policies exist.

### Deferred / Overkill Hook

- app store packaging,
- package manager integration,
- delta updates.

---

## Phase 29 — Security Review, Audit Prep, and Incident Readiness

### Objective

Prepare the project for serious public use.

### Deliverables

- internal security review checklist,
- audit scope document,
- incident response plan,
- disclosure policy,
- key compromise runbook.

### Detailed Tasks

1. Review auth and session code.
2. Review parser and manifest handling.
3. Review secrets storage and transport.
4. Review logging redaction.
5. Prepare a third-party audit package:
   - architecture summary,
   - spec,
   - threat model,
   - test results,
   - known limitations.
6. Define incident response:
   - revoke,
   - rotate,
   - patch,
   - communicate,
   - measure blast radius.
7. Add kill-switch or profile-disable procedures where appropriate.

### Exit Criteria

- the project can survive a serious bug report operationally,
- public security posture is credible.

### Deferred / Overkill Hook

- recurring external audits,
- public bounty program,
- formal verification experiments.

---

## Phase 30 — Canary Rollout and Production Readiness

### Objective

Move carefully from friendly alpha to serious production use.

### Deliverables

- canary rollout plan,
- support runbooks,
- SLO/SLI draft,
- production readiness checklist,
- rollback drills.

### Detailed Tasks

1. Define rollout cohorts:
   - internal,
   - trusted testers,
   - limited public,
   - broad stable.
2. Define release gates:
   - conformance passed,
   - fuzz health acceptable,
   - no major regression in benchmarks,
   - observability dashboards green,
   - rollback tested.
3. Run rollback drills.
4. Define support escalation paths.
5. Define what telemetry is needed before widening rollout.

### Exit Criteria

- the team can operate the system under real user load,
- rollback is practiced, not hypothetical.

### Deferred / Overkill Hook

- multi-region staged rollout controller,
- automatic canary analysis.

---

## Phase 31 — Documentation, Community, and Ecosystem Enablement

### Objective

Make the project usable and sustainable beyond the original authors.

### Deliverables

- docs site,
- operator guide,
- client guide,
- integration guide,
- protocol overview,
- contribution guide,
- changelog discipline.

### Detailed Tasks

1. Write docs for:
   - operators,
   - end users,
   - app developers,
   - protocol contributors,
   - security researchers.
2. Publish:
   - architecture overview,
   - FAQ,
   - compatibility matrix,
   - migration notes.
3. Build examples:
   - local dev environment,
   - simple edge deployment,
   - bridge deployment,
   - sample Remnawave integration.
4. Define contribution review expectations.
5. Define deprecation communication policy.

### Exit Criteria

- new contributors can join without private onboarding,
- operators can deploy without reverse-engineering the code.

### Deferred / Overkill Hook

- translated docs,
- conference talks,
- training material,
- certification/playbooks.

---

## Phase 32 — Upstream Strategy and Ecosystem Expansion

### Objective

Decide how the project relates to broader ecosystems after it is stable on its own terms.

### Deliverables

- ecosystem strategy memo,
- upstream collaboration map,
- external API policy,
- SDK strategy.

### Detailed Tasks

1. Decide whether to stay:
   - fully standalone,
   - bridge-only,
   - or eventually upstream parts elsewhere.
2. Define public APIs for:
   - control-plane integration,
   - manifest generation,
   - metrics/export.
3. Decide whether to publish:
   - client SDK,
   - operator SDK,
   - bridge SDK.
4. Define what “native compatibility” would really mean and whether it is worth the cost.

### Exit Criteria

- ecosystem strategy is intentional,
- the project is not forced into premature upstream complexity.

### Deferred / Overkill Hook

- reference implementation in another language,
- open interoperability working group,
- standardization effort.

---

# 11. Specialized Tracks That Must Run in Parallel

## 11.1 Security Track

Must be active from the beginning, not appended later.

### Core Responsibilities

- threat model maintenance,
- auth review,
- certificate handling review,
- parser hardening,
- incident response readiness,
- audit prep.

### Mandatory Gates

- no release without auth review,
- no parser changes without fuzz update,
- no major feature without threat impact note.

---

## 11.2 Performance Track

### Core Responsibilities

- benchmark harness,
- regression tracking,
- load/soak testing,
- memory budgeting,
- contention analysis.

### Mandatory Gates

- no performance claims without measurements,
- no profile promotion without health metrics.

---

## 11.3 Reliability Track

### Core Responsibilities

- graceful shutdown,
- retry/backoff correctness,
- reconnection behavior,
- state reconciliation,
- drift healing.

### Mandatory Gates

- no production rollout until rollback is rehearsed,
- no bridge release without reconciliation tests.

---

## 11.4 DX / Operator Experience Track

### Core Responsibilities

- config clarity,
- diagnostics,
- runbooks,
- subscription onboarding,
- understandable error messages.

### Mandatory Gates

- no “works on my machine” merge for operator-critical flows,
- no release with undocumented operational flags.

---

# 12. Team and Specialist Requirements

## 12.1 Minimum Core Team

### 1. Protocol Architect / Technical Lead

Owns:

- protocol boundaries,
- versioning policy,
- major ADRs,
- threat-model alignment,
- roadmap integrity.

### 2. Senior Rust Network Engineer (Server/Transport)

Owns:

- server runtime,
- carrier integration,
- stream/datagram engine,
- performance-critical paths.

### 3. Senior Rust Systems/Client Engineer

Owns:

- client agent,
- local proxy,
- platform integration,
- packaging foundations.

### 4. Integration / Platform Engineer

Owns:

- Remnawave bridge,
- webhook receiver,
- provisioning sync,
- operator workflows.

### 5. Security Reviewer (part-time at minimum)

Owns:

- auth review,
- key lifecycle,
- parser hardening,
- threat model and release gates.

### 6. QA / Reliability / Perf Engineer

Owns:

- test harnesses,
- adversity lab,
- benchmark discipline,
- soak tests,
- regression reporting.

## 12.2 Strongly Recommended Extended Team

- Technical writer / docs maintainer
- Product-minded operator advocate
- Mobile engineer (later)
- SRE / observability engineer
- Community/release maintainer

## 12.3 Optional Later Specialists

- Formal methods engineer
- Applied cryptography reviewer
- eBPF/kernel networking specialist
- Windows networking specialist
- Apple platform/network extension specialist

---

# 13. AI-Agent Skill Matrix

The safest way to use AI on this project is to assign narrow roles with human review gates.

## 13.1 AI Role: Protocol Spec Assistant

Must be able to:

- draft RFC-style text,
- derive state machines,
- track versioned registries,
- produce consistency checks across documents.

Human review required for:

- all invariants,
- compatibility rules,
- security assumptions,
- extension semantics.

## 13.2 AI Role: Rust Implementation Assistant

Must be able to:

- create crate scaffolding,
- write idiomatic async Rust,
- add tracing,
- write tests,
- propose refactors,
- preserve interface contracts.

Human review required for:

- unsafe code,
- concurrency correctness,
- performance-critical hot paths,
- networking edge cases.

## 13.3 AI Role: Security Review Assistant

Must be able to:

- enumerate attack surfaces,
- trace credential lifecycle,
- identify parser risk,
- generate negative tests,
- propose abuse cases.

Human review required for:

- any real security sign-off,
- final auth design acceptance.

## 13.4 AI Role: Test and Fuzz Assistant

Must be able to:

- generate fixture corpora,
- write property-based tests,
- scaffold fuzz targets,
- derive failure matrices.

Human review required for:

- acceptance criteria,
- regression triage,
- false-positive management.

## 13.5 AI Role: Docs and Release Assistant

Must be able to:

- maintain changelogs,
- draft migration notes,
- update compatibility tables,
- generate operator docs.

Human review required for:

- release claims,
- security statements,
- support instructions.

## 13.6 Mandatory Rules for AI Usage

- never invent cryptographic primitives,
- never silently change wire format,
- never merge parser changes without tests,
- never merge auth changes without review,
- never treat benchmark output as valid unless reproducible,
- always update docs/specs with code changes that affect behavior.

---

# 14. Quality Gates

Every meaningful phase should satisfy a common checklist.

## 14.1 Specification Gate

- behavior documented,
- version impact documented,
- compatibility story documented.

## 14.2 Implementation Gate

- code reviewed,
- tests added,
- logs/metrics added,
- config validated.

## 14.3 Security Gate

- threat impact assessed,
- secrets handling reviewed,
- parser exposure considered.

## 14.4 Operability Gate

- runbook or diagnostic path exists,
- failure modes are explainable,
- rollback path exists.

## 14.5 Release Gate

- changelog written,
- compatibility matrix updated,
- upgrade notes published.

---

# 15. Risk Register

## 15.1 Architecture Risk: Building Too Much Too Early

Mitigation:

- phase discipline,
- proxy mode first,
- tunnel later,
- “deferred/overkill” list maintained separately.

## 15.2 Integration Risk: Assuming Native Remnawave Execution

Mitigation:

- explicit bridge architecture,
- do not couple the data plane to Remnawave Node semantics.

## 15.3 Security Risk: Static Credentials and Weak Revocation

Mitigation:

- short-lived grants,
- explicit rotation rules,
- revocation design early.

## 15.4 Product Risk: Great Protocol, Poor Client UX

Mitigation:

- client/agent is a first-class workstream,
- subscription bootstrap and install flow get dedicated phases.

## 15.5 Reliability Risk: Control Plane and Edge Drift

Mitigation:

- webhook + reconciliation,
- drift metrics,
- idempotent provisioning.

## 15.6 Performance Risk: Premature Optimization and Wrong Bottleneck Assumptions

Mitigation:

- baseline lab,
- regression dashboards,
- measurement-first tuning.

## 15.7 Community Risk: OSS Without Governance

Mitigation:

- ADRs,
- contribution guide,
- release discipline,
- documented support boundaries.

---

# 16. “Too Much for Now, But Keep It in Mind” Backlog

This section exists on purpose. These items should not drive the MVP, but they should remain visible.

## 16.1 Protocol Evolution Ideas

- independent third-party implementation guide,
- richer extension registry,
- alternative manifest encodings,
- transport profile bundles signed separately from binaries,
- richer policy delta updates.

## 16.2 Performance / Systems Ideas

- io_uring exploration,
- eBPF telemetry probes,
- custom allocator experiments,
- zero-copy improvements,
- NUMA-aware tuning,
- kernel-bypass research.

## 16.3 Tunnel / Networking Ideas

- multipath support,
- advanced route learning,
- enterprise DNS policy packs,
- site-to-site mode,
- relay chaining,
- mesh overlays.

## 16.4 Security Ideas

- hardware-backed device keys,
- stronger device attestation,
- post-quantum hybrid experiments using standard libraries when mature,
- formally modeled handshake,
- reproducible secure enclave experiments.

## 16.5 Operator / Product Ideas

- policy marketplace/templates,
- commercial support tiering,
- billing adapters,
- role-based admin policies,
- compliance-oriented logging bundles.

## 16.6 Ecosystem Ideas

- public SDKs,
- reference implementations in other languages,
- client plugin ecosystem,
- interop consortium,
- standardization track.

---

# 17. Suggested Milestone Ladder

This section avoids calendar promises and instead defines maturity states.

## Milestone A — Architecture Complete

Must have:

- charter,
- threat model,
- versioning policy,
- session core spec,
- Remnawave integration contract,
- crate layout.

## Milestone B — Lab-Usable Proxy Prototype

Must have:

- server skeleton,
- client CLI,
- TCP streams,
- auth,
- basic logs/metrics.

## Milestone C — Friendly Alpha

Must have:

- UDP mode,
- bridge MVP,
- bootstrap manifest,
- subscription page onboarding,
- diagnostics bundle,
- conformance tests.

## Milestone D — Production Beta

Must have:

- profile rollout/rollback,
- fuzzing,
- adversity benchmarks,
- signed builds,
- support runbooks,
- canary rollout readiness.

## Milestone E — Production Stable Proxy Platform

Must have:

- strong observability,
- compatibility matrix,
- incident response readiness,
- docs and governance,
- stable release channel.

## Milestone F — Tunnel/VPN Beta

Must have:

- Linux TUN MVP,
- route and DNS handling,
- tunnel diagnostics,
- policy integration.

---

# 18. Recommended Initial Technical Stack

These are implementation recommendations, not immutable laws.

## 18.1 Runtime and Transport Building Blocks

- Tokio for async runtime and networking foundation
- rustls for modern TLS
- Quinn for Rust QUIC
- h3 crate for HTTP/3 mapping over QUIC traits

## 18.2 Supporting Libraries and Tooling

- tracing and tracing-subscriber
- bytes
- serde / serde_json / schemars where appropriate
- clap for CLI
- proptest for property-based tests
- criterion for benchmarks
- cargo-fuzz or libFuzzer-based workflows
- qlog-compatible capture where transport debugging matters

## 18.3 Why This Stack Is Sensible

- mature Rust async ecosystem,
- good portability story,
- standards-aligned transport path,
- future room for lower-level substitution if absolutely needed later.

---

# 19. Immediate Next Actions After This Plan

These are the first concrete actions to take once the team accepts this roadmap.

1. Finalize project name and product statement.
2. Write the project charter and non-goals.
3. Create the repository and engineering standards.
4. Draft the Remnawave integration contract.
5. Draft the session-core v0 spec.
6. Bootstrap the Rust workspace.
7. Build the benchmark/adversity lab harness.
8. Implement the edge acceptor skeleton.
9. Implement the manifest format draft.
10. Implement the first client CLI import/connect flow.

---

# 20. What “Ideal” Should Mean for This Project

An “ideal protocol” in practice should mean:

- **auditable**,
- **versioned**,
- **observable**,
- **replaceable at the edges**,
- **operationally agile**,
- **boring in the right places**,
- **fast enough under real network conditions**,
- **easy to reason about under failure**,
- and **supported by a healthy open-source process**.

If the project becomes fast but impossible to operate, it failed.
If it becomes flexible but impossible to audit, it failed.
If it becomes clever but impossible to evolve, it failed.

The winning architecture is the one that keeps the core small, the profiles replaceable, the implementation testable, and the operator workflow simple.

---

# 21. Reference Basis for This Plan

The following sources informed the integration and transport assumptions used in this roadmap:

- Remnawave Panel changelog and docs:
  - https://docs.rw/docs/changelog/remnawave-panel/
  - https://docs.rw/docs/learn-en/templates/
  - https://docs.rw/docs/install/remnawave-node/
  - https://docs.rw/docs/sdk/xtls-sdk/
  - https://docs.rw/docs/features/webhooks/
  - https://docs.rw/docs/changelog/remnawave-subscription-page/
  - https://docs.rw/docs/install/subscription-page/separate-server/
  - https://docs.rw/docs/features/hwid-device-limit/
- IETF / RFC references:
  - QUIC (RFC 9000): https://www.rfc-editor.org/info/rfc9000
  - HTTP/3 (RFC 9114): https://www.rfc-editor.org/info/rfc9114
  - CONNECT-UDP (RFC 9298): https://www.rfc-editor.org/info/rfc9298
  - CONNECT-IP (RFC 9484): https://www.rfc-editor.org/info/rfc9484
- Rust implementation references:
  - Tokio: https://tokio.rs/
  - rustls: https://docs.rs/rustls
  - Quinn: https://docs.rs/quinn/latest/quinn/
  - h3 crate: https://docs.rs/h3
