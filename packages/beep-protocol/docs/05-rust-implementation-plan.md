# Rust Implementation Plan

## Objectives

The Rust implementation has to preserve three things simultaneously:

- a stable session-core API,
- swappable transport implementations,
- operational performance under high connection churn and long-lived sessions.

That requires a monorepo design with narrow, explicit crate boundaries.

## Proposed workspace

```text
crates/
  beep-core/               # session core, handshake, frames, key schedule
  beep-core-types/         # shared protocol types and artifact schemas
  beep-cover-h2/           # HTTP/2 transport
  beep-cover-h3/           # HTTP/3 + MASQUE transport
  beep-cover-fast/         # native fast transport
  beep-policy/             # path policy, scoring, fallback ladder
  beep-present/            # presentation_profile parsing and validation
  beep-node-runtime/       # node coordinator, listeners, reload, metrics
  beep-client-runtime/     # client sidecar, probes, TUN integration
  beep-control-api/        # control-plane client and signed artifact fetching
  beep-ffi/                # desktop/mobile bindings
  beep-bench/              # benchmark harness
  beep-lab/                # replay, interop, adverse-path simulation
```

## Ownership model by crate

### `beep-core`

Owns:

- frame encoding and decoding,
- handshake state machine,
- key schedule,
- resumption tickets,
- rekey logic,
- stream and datagram abstractions,
- protocol errors.

This crate must not know anything about HTTP/2 pseudo-headers, MASQUE capsules, or OS-specific socket APIs.

### `beep-cover-*`

Each cover crate owns only its outer transport behavior.

Responsibilities:

- establish and accept outer connections,
- expose a normalized `CoverConn`,
- surface capabilities,
- translate transport-specific failures into `TransportError`.

These crates must not implement the session core.

### `beep-policy`

Owns:

- scoring of candidate profiles,
- sticky decisions,
- fallback decisions,
- network classification,
- rollout gating.

It must be deterministic enough to replay in tests from recorded inputs.

### `beep-node-runtime` and `beep-client-runtime`

Own the process lifecycle, hot reload, socket setup, TUN I/O, metrics, and integration concerns.

## Suggested trait boundary

```rust
pub trait CoverTransport {
    fn name(&self) -> &'static str;
    fn capabilities(&self) -> TransportCapabilities;

    async fn dial(&self, profile: &TransportProfile) -> Result<CoverConn, TransportError>;
    async fn accept(&self, profile: &TransportProfile) -> Result<CoverConn, TransportError>;
}

pub trait SessionCore {
    async fn open(
        &self,
        conn: CoverConn,
        policy: &PolicyBundle,
    ) -> Result<Session, SessionError>;
}

pub trait PathPolicy {
    fn choose(
        &self,
        ctx: &NetworkContext,
        history: &SuccessHistory,
    ) -> CandidateSet;
}
```

The goal is explicit: outer transport and inner session logic should only touch through a small, audited interface.

## Library posture

Because library maturity changes over time, `Beep` should prefer abstractions over hard coupling. Still, the current Rust ecosystem supports a practical starting point.

### Recommended v1 starting stack

- async runtime: `tokio`
- buffer management: `bytes`
- H2 transport: `h2` plus a TLS adapter
- pure-Rust QUIC baseline: `quinn`
- tracing: `tracing` and structured event export
- artifact serialization: `serde`

### Evaluation track for high-scale H3 edge

Public Cloudflare material makes `quiche` and `tokio-quiche` relevant evaluation candidates for a high-scale H3 edge. This does not mean they should replace the architecture. It means the H3 transport boundary should be clean enough that `Beep` can evaluate:

- a pure-Rust path,
- a battle-tested QUIC/H3 stack used at large scale,
- or both for different deployment tiers.

### TLS provider boundary

`rustls` is a strong default for safe, standard TLS. The implementation should still hide it behind a provider boundary because:

- the product may later need a different TLS provider for operational reasons,
- the presentation profile should not leak library internals into the rest of the codebase.

`Beep v1` should not be blocked on exact third-party client impersonation.

## Runtime model

### Client runtime

The client sidecar should be responsible for:

- profile selection,
- local socket/TUN lifecycle,
- storing resumption state,
- maintaining sticky path history,
- exporting compact telemetry.

### Node runtime

The node runtime should use:

- per-core sharding for connection ownership,
- bounded memory arenas or pools for packet buffers,
- explicit queues between accept, session, and forwarding stages,
- backpressure metrics at every stage.

Avoid a giant single event loop with mixed responsibilities.

## Performance engineering rules

### For QUIC paths

Plan for:

- larger UDP buffers,
- batched send and receive,
- GSO/GRO when available,
- minimized copy count,
- packet pacing awareness,
- metrics for drops caused by buffer exhaustion.

### For H2/TCP paths

Plan for:

- careful stream budgeting,
- low lock contention around flow control,
- connection reuse where policy allows,
- explicit separation of control and packet carriage streams.

### For all paths

- use pooled `BytesMut` or equivalent reusable buffers;
- avoid per-packet heap churn;
- keep cryptographic state small and short-lived where possible;
- expose queue depth and buffer pressure as first-class metrics.

## Suggested implementation phases

### Phase 1

- finalize artifact schemas,
- implement `beep-core-types`,
- implement frame codec and handshake state machine,
- stand up `cover_h2`.

### Phase 2

- connect client and node runtimes with real TUN plumbing,
- ship `cover_h2` end to end,
- establish resumption and rekey.

### Phase 3

- add `cover_h3`,
- add datagram carriage,
- benchmark `cover_h2` vs `cover_h3`.

### Phase 4

- add `native_fast`,
- harden telemetry and rollback,
- make profile artifacts independently rollable.

### Phase 5

- evaluate alternate H3 provider path if the scale model requires it,
- extend crypto agility and PQ options,
- expand lab replay coverage.

## FFI boundary

The FFI layer should remain thin.

Expose:

- connect and disconnect,
- selected profile,
- session health summary,
- current policy and assignment IDs,
- compact trace token for diagnostics.

Do not expose internal frame-level details to UI code.

## What to avoid

- shared mutable global state across transports,
- business logic embedded in transport crates,
- transport-specific auth semantics,
- artifact parsing duplicated in client and node code,
- feature flags that silently alter wire semantics.

