# First Carrier Notes

## Purpose

This note defines the initial transport-layer implementation packet for Verta v0.1.
It is constrained by the workspace plan, the freeze candidate, the RFC draft, and the threat model.

This note is intentionally transport-scoped.
It does not redefine session semantics, wire format, Bridge behavior, or policy logic.

## Status Note

Several historical milestone sections in this file refer to the planned `.github/workflows/udp-optional-gates.yml`.
That file never landed in the root repo.
`Phase K` supersedes those references with the real sustained verification workflows and gate map in `docs/development/SUSTAINED_VERIFICATION_GATES.md`.

## Normative anchors

- Workspace split and dependency rules:
  - `docs/spec/verta_implementation_spec_rust_workspace_plan_v0_1.md`
  - Sections 4.1, 5.2, 9.1-9.3, 31, 32, 34
- Carrier and session semantics:
  - `docs/spec/verta_protocol_rfc_draft_v0_1.md`
  - Sections 3.2, 4.1-4.2, 5, 6.1, 7.2, 8-14, 19, Appendix A
- Frozen transport-facing wire and manifest/profile shape:
  - `docs/spec/verta_wire_format_freeze_candidate_v0_1.md`
  - Sections 5, 6, 8, 9, 10, 11, 12, 15, 18.3, 18.4, 19.3
- Security and launch controls:
  - `docs/spec/verta_threat_model_v0_1.md`
  - Sections 5.2-5.3, 14.3, 15.5, 16.2, 17, 18

## Non-negotiable transport rules

- `CarrierKind = h3` is the only required production carrier in v0.1.
- `ns-session` stays transport-agnostic and MUST NOT depend directly on Quinn, `h3`, `axum`, or database clients.
- `ns-carrier-h3` owns H3 tunnel creation, control stream binding, relay stream binding, datagram mapping, and carrier-specific error translation.
- The control stream is unique per session and the first frame on it MUST be `CLIENT_HELLO`.
- Before `SERVER_HELLO`, the client MUST NOT open relay streams, open UDP flows, emit `PATH_EVENT`, or send stats.
- Before handshake completion, gateway-side carrier composition must keep unauthenticated work within explicit body-size, concurrency, and wall-clock budgets.
- TCP relay uses dedicated carrier streams.
- UDP relay must support stream fallback even when datagrams are unavailable.
- The carrier layer owns confidentiality, integrity, multiplexing, optional datagram availability, and native connection-migration behavior.
- The session core owns capability negotiation, lifecycle semantics, error semantics, and protocol sequencing.

## Recommended crate names

Keep the workspace-plan crate names as-is.
Do not introduce a generic `ns-transport` or `ns-transport-quic` crate for v0.1.
That would cut across the normative crate graph and blur the session/carrier boundary.

Recommended transport-related crates:

- `crates/ns-session`
  - owns transport-agnostic carrier traits, transport-facing session I/O contracts, and transport-neutral error categories
- `crates/ns-carrier-h3`
  - owns Quinn, rustls, and `h3` integration for the first carrier
- `crates/ns-client-runtime`
  - owns client-side profile selection, config mapping, reconnect policy, and carrier composition
- `crates/ns-gateway-runtime`
  - owns listener composition, gateway admission sequencing, and carrier/session orchestration
- `crates/ns-observability`
  - owns tracing field names, redaction helpers, and span conventions used by the carrier
- `crates/ns-testkit`
  - owns fake carrier implementations and later H3 loopback/lab helpers

## Recommended trait ownership

The generic carrier traits belong in `ns-session`, not in `ns-carrier-h3`.
`ns-carrier-h3` should implement those traits and expose concrete connectors/acceptors.

Recommended `ns-session` modules:

```text
crates/ns-session/src/
  lib.rs
  carrier.rs
  control.rs
  relay.rs
  udp.rs
  error.rs
  client_engine.rs
  gateway_engine.rs
  registry.rs
  timing.rs
```

Recommended `ns-session::carrier` surface:

```rust
pub trait PendingCarrierSession {
    type Control: ControlFrameIo;
    type Established: EstablishedCarrierSession;

    fn info(&self) -> &CarrierSessionInfo;
    fn control(&mut self) -> &mut Self::Control;
    fn into_established(self) -> Result<Self::Established, TransportError>;
}

pub trait EstablishedCarrierSession {
    type Control: ControlFrameIo;
    type Relay: RelayStreamIo;
    type Datagram: DatagramIo;
    type UdpFallback: UdpFallbackStreamIo;

    fn info(&self) -> &CarrierSessionInfo;
    fn control(&mut self) -> &mut Self::Control;
    async fn open_relay_stream(&mut self, open: StreamOpen) -> Result<Self::Relay, TransportError>;
    async fn accept_relay_stream(&mut self) -> Result<IncomingRelayStream<Self::Relay>, TransportError>;
    async fn open_udp_fallback_stream(
        &mut self,
        open: UdpStreamOpen,
    ) -> Result<Self::UdpFallback, TransportError>;
    async fn accept_udp_fallback_stream(
        &mut self,
    ) -> Result<IncomingUdpFallbackStream<Self::UdpFallback>, TransportError>;
    fn datagrams(&self) -> Option<&Self::Datagram>;
}

pub trait ControlFrameIo {
    async fn read_frame(&mut self) -> Result<ns_wire::Frame, TransportError>;
    async fn write_frame(&mut self, frame: &ns_wire::Frame) -> Result<(), TransportError>;
}

pub trait RelayStreamIo {
    async fn write_preamble(&mut self, frame: &ns_wire::Frame) -> Result<(), TransportError>;
    async fn read_preamble(&mut self) -> Result<ns_wire::Frame, TransportError>;
    async fn send_raw(&mut self, chunk: Bytes) -> Result<(), TransportError>;
    async fn recv_raw(&mut self) -> Result<Option<Bytes>, TransportError>;
    async fn finish_raw(&mut self) -> Result<(), TransportError>;
}

pub trait DatagramIo {
    async fn send(&self, datagram: UdpDatagram) -> Result<(), TransportError>;
    async fn recv(&self) -> Result<Option<UdpDatagram>, TransportError>;
}

pub trait UdpFallbackStreamIo {
    async fn write_frame(&mut self, frame: &ns_wire::Frame) -> Result<(), TransportError>;
    async fn read_frame(&mut self) -> Result<ns_wire::Frame, TransportError>;
}
```

Design intent:

- `PendingCarrierSession` keeps pre-auth state bounded.
- `EstablishedCarrierSession` is the only surface that can open or accept relay streams or expose datagrams.
- `ns-session` deals in Verta frames, relay ids, flow ids, and transport-neutral errors.
- `ns-session` never sees Quinn types, H3 request builders, rustls configs, ALPN arrays, or path templates.

## Recommended `ns-carrier-h3` module boundaries

```text
crates/ns-carrier-h3/src/
  lib.rs
  config.rs
  connect.rs
  accept.rs
  request_template.rs
  control.rs
  relay.rs
  udp.rs
  tls.rs
  quic.rs
  error.rs
  observability.rs
```

Recommended responsibilities:

- `config.rs`
  - map manifest carrier-profile objects into validated `H3TransportConfig`
  - validate `carrier_kind = "h3"`
  - validate `origin_host`, `origin_port`, `alpn`, templates, timeout/backoff ranges, and `datagram_enabled`
- `connect.rs`
  - client-side QUIC endpoint setup
  - outbound connection bootstrap
  - H3 client session bootstrap
- `accept.rs`
  - gateway-side QUIC listener setup
  - inbound connection acceptance
  - H3 server session bootstrap
- `request_template.rs`
  - build control-stream and relay-stream request metadata from `control_template`, `relay_template`, shared headers, host/port, and SNI-derived context
  - keep this isolated so pseudo-header policy is in one place
- `control.rs`
  - open or accept the unique control stream
  - frame I/O using `ns-wire`
  - enforce exactly one control stream per session
- `relay.rs`
  - open or accept dedicated relay streams
  - run preamble exchange (`STREAM_OPEN`, `STREAM_ACCEPT`, `STREAM_REJECT`)
  - switch accepted relay streams into raw byte mode after `STREAM_ACCEPT`
- `udp.rs`
  - expose datagram availability
  - send and receive `UDP_DATAGRAM` payloads if the selected backend is available
  - open and accept fallback streams when the session selects `stream_fallback`
- `tls.rs`
  - rustls client/server config assembly
  - ALPN application
  - SNI handling
  - explicit 0-RTT disablement for the first baseline
- `quic.rs`
  - Quinn endpoint and connection wrappers
  - connection metadata extraction
  - transport-parameter and idle-timeout wiring
- `error.rs`
  - map Quinn/H3/rustls failures into a narrow `TransportError` taxonomy
  - preserve detail for tracing without leaking secrets
- `observability.rs`
  - connection, control-stream, relay-stream, datagram, and shutdown spans/counters

## Recommended public types in `ns-carrier-h3`

```rust
pub struct H3TransportConfig { /* validated transport profile */ }
pub struct H3ClientConnector { /* client-side bootstrap */ }
pub struct H3GatewayAcceptor { /* gateway-side bootstrap */ }
pub struct H3PendingSession { /* implements PendingCarrierSession */ }
pub struct H3EstablishedSession { /* implements EstablishedCarrierSession */ }
pub enum H3TransportError { /* narrow transport-specific error set */ }
```

Keep Quinn and `h3` concrete types private where practical.
Expose Verta-focused types instead.

## Config mapping rules

The first carrier skeleton should map the manifest profile into one validated transport config object.

Minimum required mapping from manifest profile:

- `id` -> carrier-profile identifier
- `carrier_kind` -> must equal `h3`
- `origin_host` + `origin_port` -> QUIC remote address target and HTTP authority source
- `sni` -> rustls SNI override if present, otherwise derive from `origin_host`
- `alpn` -> rustls ALPN list
- `control_template.method` + `control_template.path` -> H3 control request template
- `relay_template.method` + `relay_template.path` -> H3 relay request template
- `headers` -> shared operator-controlled request headers

## Milestone 9 Implementation Notes

Milestone 9 does not change the transport contract.
It broadens confidence in the existing reusable `ns-carrier-h3` runtime:

- both-direction clean half-close is now asserted explicitly
- bounded relay shutdown still preserves stable close-reason strings
- overload, timeout, and prebuffer surfaces now map into low-cardinality observability events
- the live localhost relay harness continues to exercise the reusable runtime instead of a test-only forwarding loop

These are runtime and diagnostics notes only.
They do not change the frozen wire behavior or the rule that `ns-session` stays transport-agnostic.

## Milestone 10 Implementation Notes

Milestone 10 keeps datagrams deferred and stays inside the existing carrier/session split:

- `ns-core::ProtocolErrorCode` and `ns-gateway-runtime` are now aligned with the frozen v0.1 error registry
- accepted relay lifetime in gateway composition is now reclaimed through `ActiveRelayGuard`, so relay ids are released on the tested success, timeout, and overload paths without moving carrier logic into `ns-session`
- live QUIC/H3 coverage now asserts relay release after idle-timeout exit and overload rejection in addition to the earlier success and half-close paths

These changes are compatibility and runtime-hardening work only.
They do not widen carrier ownership or enable datagrams or 0-RTT.

## Milestone 11 Implementation Notes

Milestone 11 keeps datagrams deferred and tightens compatibility and runtime assertions:

- `ns-core` now table-locks the frozen v0.1 `ProtocolErrorCode` registry with an explicit round-trip test
- live relay overload rejection over QUIC/H3 now emits `STREAM_REJECT` with frozen `FLOW_LIMIT_REACHED` instead of using a generic `ERROR` frame
- stable runtime observability assertions for relay overload, prebuffer overflow, and idle timeout now live in `ns-gateway-runtime`
- the live carrier harness still covers hello, relay preamble, bounded raw forwarding, both-direction half-close, timeout, overload, and release behavior without widening session-core transport ownership

These are compatibility and runtime-hardening changes only.
They do not enable datagrams or 0-RTT.

## Milestone 12 Implementation Notes

Milestone 12 starts the first real UDP/datagram slice while preserving the carrier/session ownership split.

### Datagram backend choice for the current v0.1 baseline

The frozen docs require:

- `h3` as the first carrier
- UDP relay with both datagram and stream-fallback modes
- explicit `DatagramMode` negotiation
- manifest-side `udp_template.mode = "h3-datagram"`

For the current implementation baseline, `ns-carrier-h3` now binds that path to:

- RFC 9297-style associated HTTP datagrams
- `h3-datagram`
- `h3-quinn` datagram support
- the active control request stream id as the associated stream for this first live slice

This choice remains carrier-internal.
`ns-session` stays unaware of Quinn, `h3`, or associated-stream mechanics.

### Transport-neutral consequences now implemented

- `ns-session` now owns UDP flow-open admission and transport-mode selection
- `UDP_FLOW_OPEN` now resolves to either `TransportMode::Datagram` or `TransportMode::StreamFallback`
- datagram-only requests now reject with frozen `UDP_DATAGRAM_UNAVAILABLE` when datagrams are unavailable and fallback was not allowed
- `DatagramIo` is now typed on `UdpDatagram`
- explicit fallback-stream traits now sit beside datagram I/O instead of being implied

### Live scope added in milestone 12

The live localhost carrier harness now proves:

- hello plus `UDP_FLOW_OPEN` -> `UDP_FLOW_OK(datagram)` with round-trip `UDP_DATAGRAM`
- hello plus `UDP_FLOW_OPEN` -> `UDP_FLOW_OK(stream_fallback)` when datagrams are disabled by policy
- explicit datagram-only rejection when `DatagramMode = unavailable`

The first datagram runtime remains intentionally bounded:

- effective gateway default `max_udp_flows = 8`
- effective max UDP payload `1200` bytes
- H3 datagram buffered queue ceiling `8 KiB`
- 0-RTT remains disabled

The signed transport config fields still mapped at this stage are:
- `datagram_enabled` -> whether datagram path may be attempted
- `heartbeat_interval_ms` -> control keepalive cadence
- `idle_timeout_ms` -> transport idle timeout target
- `connect_backoff.*` -> reconnect/backoff policy consumed by runtime, not session core

## Milestone 13 Implementation Notes

Milestone 13 hardens the first UDP/datagram slice without widening session-core ownership.

### Local rollout posture is now explicit

`datagram_enabled` remains the signed carrier-profile intent.
Milestone 13 adds a separate local rollout gate through `H3DatagramRollout`:

- `Disabled`
- `Automatic`

The current app-facing default is conservative:

- client-side planning defaults to `Disabled`
- runtime must opt into `Automatic`

This keeps rollout decisions operator-shaped and local, not folded back into signed manifest semantics.

### Effective datagram behavior is now fail-closed

The live H3 carrier now derives its effective datagram posture from:

- signed profile intent
- local rollout policy
- actual carrier support

If any of those say “no,” the carrier must not behave as if datagrams are available.

### Per-flow selection is now strict and explicit

`ns-session` now keeps the selection rule simple and transport-neutral:

- if datagrams are negotiated and effectively available, choose `TransportMode::Datagram`
- otherwise, choose `TransportMode::StreamFallback` only when fallback was explicitly requested
- otherwise, reject with frozen `UDP_DATAGRAM_UNAVAILABLE`

This prevents silent downgrade to fallback when datagrams were actually available.

### Live hardening added in milestone 13

The live localhost H3 harness now covers:

- forced stream fallback when rollout disables datagrams
- bounded-loss continuation for datagram flows
- payload-oversize rejection without flow corruption
- wrong-associated-stream rejection as a protocol violation

### Datagram observability is now explicit on success and guard paths

Milestone 13 keeps these low-cardinality datagram surfaces visible:

- `verta.carrier.datagram.selection`
- `verta.carrier.datagram.guard`
- `verta.carrier.datagram.io`

The new guard reason added in this milestone is:

- `udp_associated_stream_mismatch`

These changes harden the first carrier slice only.
They do not change bridge topology, session-core transport ownership, or 0-RTT posture.

## Milestone 14 Implementation Notes

Milestone 14 hardens the datagram slice for broader interoperability and bounded rollout without widening session-core ownership.

### Staged local rollout is now explicit

`H3DatagramRollout` now supports:

- `Disabled`
- `Canary`
- `Automatic`

`Canary` keeps datagrams narrowly enabled:

- only flows that explicitly prefer datagrams may select them
- fallback-allowed flows that do not prefer datagrams stay on stream fallback
- carrier availability still stays explicit in negotiated mode and observability

### Datagram live coverage now proves more than the happy path

The localhost H3 harness now additionally covers:

- repeated bounded datagram loss
- bounded reordering
- successful round-trip at the effective MTU ceiling
- stream fallback when carrier availability is negotiated as unavailable
- queue-overflow guard visibility plus successful recovery after the queue drains

### Datagram perf and fuzz paths are now locally runnable

Milestone 14 now keeps these carrier-adjacent validation paths active:

- `cargo bench -p ns-carrier-h3 --bench datagram_runtime`
- `cargo run -p ns-testkit --example sync_udp_fuzz_corpus`
- `cargo run -p ns-testkit --example udp_fuzz_smoke`

These changes harden carrier behavior and validation only.
They do not change bridge topology, signed manifest meaning, or 0-RTT posture.

## Milestone 15 Implementation Notes

Milestone 15 closes the first post-hello datagram validation gap without widening carrier ownership.

### `SERVER_HELLO` is now checked against the full local UDP posture

`ns-session` now rejects hello responses when any of these drift from the effective local session contract:

- `policy_epoch`
- negotiated `datagram_mode`
- `max_udp_flows`
- `effective_max_udp_payload`
- unusable zero-valued limits

This keeps the first datagram slice aligned with the frozen rule that `SERVER_HELLO` commits the active session contract rather than suggesting it.

### Active UDP flow tracking is now transport-mode aware

The session core now keeps the selected UDP transport mode per active flow.

That keeps these cases transport-neutral and fail closed:

- datagram input after close
- datagram input for unknown flow ids
- fallback stream opens for the wrong flow id
- datagram traffic sent against a flow that was admitted as stream fallback

### Datagram burst budgets are now explicit alongside byte limits

The first H3 datagram runtime slice now bounds buffered datagrams by:

- `max_buffered_datagrams = 8`
- `max_buffered_datagrams_per_flow = 4`
- existing buffered-byte ceiling `8 KiB`

Guard events for these limits stay carrier-local and low-cardinality.

### Local verification now includes opt-in fuzz and perf gates

Milestone 15 keeps the existing Windows-first smoke path and adds opt-in wrapper gates through `scripts/check.*`:

- `VERTA_ENABLE_UDP_FUZZ_SMOKE=1`
- `VERTA_ENABLE_UDP_PERF_GATE=1`

The new perf gate stays local and ratio-based.
It does not change carrier semantics or imply a WAN-performance claim.

Recommended split:

- `ns-manifest` validates the JSON schema and carrier-profile object shape.
- `ns-carrier-h3::config` validates H3-specific operational assumptions and produces a concrete transport config.
- `ns-client-runtime` owns connect-attempt loops, backoff execution, and selection of signed endpoint/profile data for the launch plan.

Milestone-3 implementation note:

- client launch planning now derives H3 dial target and carrier presentation settings from verified signed manifest data instead of local defaults
- endpoint `host` and `port` are the dial target
- carrier-profile `origin_host`, `origin_port`, optional `sni`, `alpn`, templates, and timing fields are the signed transport settings

Milestone-4 implementation note:

- `headers`, `connect_backoff`, and `zero_rtt_policy` now survive into `H3TransportConfig`
- request-template construction is centralized in `ns-carrier-h3`
- milestone-4 request synthesis uses `https` plus `origin_host:origin_port` as the authority source
- non-empty manifest headers are accepted only as ordinary lowercase headers, never as pseudo-headers
- effective transport behavior still keeps 0-RTT disabled even when the signed policy value is preserved

Milestone-5 implementation note:

- `control_template.path` and `relay_template.path` must start with `/`
- signed manifest headers are now limited to ordinary lowercase end-to-end request headers
- the following signed request headers are rejected during request-template construction: `connection`, `proxy-connection`, `keep-alive`, `upgrade`, `transfer-encoding`, `te`, `trailer`, `content-length`, `host`, and `expect`
- tunnel-frame payloads used for live control and relay preambles are size-bounded to `16 KiB` in `ns-carrier-h3`
- the first live relay milestone now reaches `STREAM_OPEN` and `STREAM_ACCEPT` over a real localhost QUIC/H3 relay request after a successful hello
- raw relay payload forwarding still remains deferred

Milestone-6 implementation note:

- the first live relay-data slice now forwards bounded raw TCP bytes over a real localhost QUIC/H3 relay stream after `STREAM_ACCEPT`
- `ns-carrier-h3` now bounds relay-side raw prebuffering with a default `64 KiB` ceiling before backpressure is reported
- `ns-gateway-runtime` now exposes accepted-relay budgets with defaults of `max_active_relays = 256`, `max_relay_prebuffer_bytes = 64 KiB`, and `relay_idle_timeout_ms = 30_000`
- overload, relay prebuffer overflow, and relay idle-timeout conditions are mapped to stable Verta protocol error categories before the carrier layer reports them upward
- datagrams remain disabled and 0-RTT remains disabled
- the current raw relay slice is proven through live QUIC/H3 composition and integration coverage; promoting it into a fuller reusable carrier-session abstraction remains follow-on work

Milestone-7 implementation note:

- `ns-session::RelayStreamIo` now exposes `send_raw`, `recv_raw`, and `finish_raw` directly instead of requiring a carrier-specific raw handoff object
- `ns-session::EstablishedCarrierSession::open_relay_stream` now takes the full `StreamOpen` preamble so carrier implementations do not reconstruct relay intent from only a relay id
- `ns-session::SessionController` now exposes relay-release lifecycle hooks so accepted-relay limits can be reclaimed explicitly
- `ns-carrier-h3` now promotes the live raw relay logic into a reusable `forward_raw_tcp_relay` runtime that handles clean client half-close, upstream EOF, bounded raw prebuffering, idle timeout, and stable close-reason reporting
- the live QUIC/H3 relay integration test now exercises that reusable runtime rather than keeping raw byte forwarding as test-local orchestration

Milestone-8 implementation note:

- the reusable `forward_raw_tcp_relay` runtime now has direct unit coverage for client-first half-close, upstream-first half-close, idle-timeout closure, and oversized-client-prebuffer rejection without relying only on the live H3 harness
- relay close reporting now emits stable structured close events with byte totals and clean-half-close state through `ns-observability`
- milestone-8 does not change live datagram posture or 0-RTT posture; both remain deferred or disabled

## First QUIC/H3 skeleton scope

The first carrier milestone should be real, but deliberately narrow.

### In scope

- validated H3 transport config mapping from manifest carrier profiles
- Quinn endpoint bootstrap for client and gateway
- rustls config assembly with manifest-driven ALPN and SNI
- one H3 connection per Verta session
- one unique control stream per session
- control-stream frame I/O using `ns-wire`
- a real localhost QUIC/H3 control-stream hello exchange
- relay-stream open and accept path for TCP relay preambles
- raw relay-mode handoff after `STREAM_ACCEPT`
- bounded raw relay-byte forwarding after `STREAM_ACCEPT`
- UDP flow mode selection plumbing
- explicit UDP stream-fallback support
- datagram capability exposure behind a transport-neutral interface
- carrier-specific error translation
- structured tracing around connect, accept, control, relay, datagram, and shutdown paths

### Explicitly out of scope for the first carrier skeleton

- alternate carriers
- multipath behavior
- session resumption
- 0-RTT data
- custom congestion-control experiments
- IP tunnel or `CONNECT-IP` behavior
- profile hot-swap without reconnect
- operator camouflage heuristics encoded as core logic

## Recommended implementation sequence

1. Finish `ns-session` transport-neutral traits and error taxonomy.
2. Add `ns-carrier-h3::config` and make profile-to-config conversion deterministic and unit-tested.
3. Add `tls.rs` and `quic.rs` wrappers without exposing Quinn types outside the crate.
4. Add client-side control-stream bootstrap only.
5. Add gateway-side control-stream accept path only.
6. Run hello exchange over the control stream end-to-end.
7. Add TCP relay stream bootstrap and raw-mode handoff.
8. Add UDP stream-fallback path.
9. Add datagram path behind the same `DatagramIo` abstraction; milestone 12 now provides the first H3-associated implementation.
10. Add targeted transport integration tests and error-mapping tests.

This sequence preserves the rule from the workspace plan: the session engine must be testable without a real QUIC stack, and the first live carrier work happens after that trait line is stable.

## Security and abuse controls at the carrier edge

The H3 carrier skeleton must visibly enforce the threat-model rules:

- bound pre-auth state before token verification succeeds
- default gateway pre-auth budgets now include `max_pending_hellos = 256`, `max_control_body_bytes = 16 KiB`, and `handshake_deadline_ms = 1000`
- do not accept relay streams or UDP flows before handshake completion
- keep unauthenticated error output terse
- classify auth failures separately from transport failures in tracing
- bound concurrent pending sessions and pending H3 requests
- keep control-stream read loops size-bounded and codec-driven
- never log raw session tokens, bootstrap strings, or refresh material
- do not silently enable 0-RTT
- do not let transport-level datagram availability bypass negotiated session capability checks

Recommended observability points:

- `carrier.connect.start`
- `carrier.connect.ok`
- `carrier.connect.fail`
- `carrier.accept.start`
- `carrier.accept.ok`
- `carrier.control.open`
- `carrier.control.fail`
- `carrier.relay.open`
- `carrier.relay.reject`
- `carrier.udp.mode_selected`
- `carrier.udp.datagram_unavailable`
- `carrier.session.closed`

## Minimum tests for the first carrier slice

- profile-to-config validation accepts a minimal valid H3 profile
- profile-to-config validation rejects non-`h3` carrier kinds
- profile-to-config validation rejects missing or empty ALPN lists
- session bootstrap enforces one control stream per session
- live localhost QUIC/H3 control-stream hello succeeds from `CLIENT_HELLO` to `SERVER_HELLO`
- auth failure over the live control path returns a terminal rejection before session establishment
- client cannot open relay streams before `SERVER_HELLO`
- gateway rejects relay attempts before session establishment
- gateway rejects oversized hello bodies and expired pre-auth attempts before session admission
- TCP relay preamble switches to raw mode only after `STREAM_ACCEPT`
- bounded raw relay bytes round-trip over the live localhost QUIC/H3 path after `STREAM_ACCEPT`
- live localhost UDP datagrams round-trip after `UDP_FLOW_OPEN` when datagrams are negotiated
- UDP fallback works when datagrams are unavailable
- datagram-only UDP requests reject with frozen `UDP_DATAGRAM_UNAVAILABLE` when fallback is not allowed
- transport errors map to stable session-facing categories
- tracing and redaction tests confirm tokens are never emitted

## Ambiguities that must stay explicit

### 1. Datagram backend for the H3 carrier

Milestone 12 resolves the implementation baseline to H3-associated HTTP datagrams as recorded above.

Implementation rule remains:

- keep `ns-session` unaware of this choice
- hide the backend behind `ns-carrier-h3::udp`
- do not spread datagram-assumption code across the runtime crates
- treat any future change to a different carrier datagram binding as a compatibility-sensitive decision that needs an ADR or spec update

### 2. Exact H3 pseudo-header synthesis

The profile schema freezes `method = CONNECT`, `path`, shared headers, `origin_host`, and `origin_port`, but it does not fully spell out the exact pseudo-header derivation rules for all H3 requests.

Implementation rule:

- centralize request construction in `request_template.rs`
- record the chosen `:scheme` and `:authority` synthesis in an implementation note before making the path public or stable
- milestone 4 uses `https` and `origin_host:origin_port`

### 3. `zero_rtt_policy` vs deferred 0-RTT

The manifest schema includes `zero_rtt_policy`, but the RFC and workspace plan explicitly defer 0-RTT and session resumption for the first baseline.

Implementation rule:

- parse the field
- keep transport behavior at `0-RTT disabled`
- fail closed or explicitly reject launch profiles that attempt to require non-disabled 0-RTT behavior until the specs define the compatibility and security model

### 4. Gateway-side pre-auth request handling depth

The threat model requires strict token verification before expensive allocation where practical, but the exact H3 request-accept depth is not frozen.

Implementation rule:

- keep pre-auth session objects small
- do not create relay or UDP handling tasks before `CLIENT_HELLO` is decoded and authorization has passed
- keep this sequencing in one accept-path module so later hardening is localized

## Concrete recommendation

Implement the first transport milestone with this shape:

- `ns-session` defines the carrier-neutral I/O contracts and session-facing transport errors
- `ns-carrier-h3` implements those contracts using private Quinn, rustls, and `h3` integration
- `ns-client-runtime` owns backoff, endpoint selection, and connector invocation
- `ns-gateway-runtime` owns listener lifecycle and admission orchestration
- the first live milestone now achieves: QUIC/H3 connect, unique control stream, hello exchange, TCP relay-stream preamble exchange, and bounded raw relay-byte forwarding after `STREAM_ACCEPT`
- the next transport milestone should harden the reusable raw relay runtime, expand non-localhost live coverage, and add UDP stream fallback on top of that live control path
- datagram support now lives behind that narrow backend seam, and broader interop, loss behavior, and fallback heuristics should remain follow-on transport milestones

This is the narrowest transport baseline that is still serious, testable, and aligned with the normative docs.

## Milestone 16 Implementation Notes

Milestone 16 keeps the bridge and control-plane boundaries unchanged and hardens only the datagram transport slice:

- local startup or planning now fails closed if operator rollout enables datagrams while the signed carrier profile disables them
- once a compatible `SERVER_HELLO` is accepted, negotiated `datagram_mode`, `max_udp_flows`, and `effective_max_udp_payload` now become the active local session contract rather than remaining validation-only hints
- deterministic live localhost coverage now includes delayed delivery plus a short datagram black hole, and the established transport mode stays pinned to datagrams throughout that degradation
- no silent mid-flow migration to stream fallback is allowed after an established datagram selection unless the frozen spec grows an explicit rule for it

These are carrier and runtime-hardening notes only.
They do not widen the session-core transport boundary, change bridge topology, or enable `0-RTT`.

## Milestone 17 Implementation Notes

Milestone 17 keeps bridge and control-plane boundaries unchanged and makes the datagram transport slice more reusable and operator-auditable:

- `ns-testkit` now defines a reusable UDP WAN-lab profile catalog for bounded loss, bounded reordering, delayed delivery plus short degradation, MTU pressure, and carrier-unavailable fallback
- the Windows-first and Bash verification wrappers can now opt into that deterministic WAN-lab path without turning it into a default required gate
- gateway-side startup composition now derives advertised `DatagramMode` from signed intent, rollout posture, and carrier availability instead of trusting a raw optimistic operator value
- client launch planning now exposes the expected `SERVER_HELLO.datagram_mode` contract directly from signed transport intent and rollout posture
- maintained queue-pressure validation now includes a queue-full ratio threshold in the UDP perf gate instead of relying only on buildable benchmarks

These are transport hardening and verification-discipline notes only.
They do not widen the session-core transport boundary, change bridge topology, or enable `0-RTT`.

## Milestone 18 Implementation Notes

Milestone 18 keeps bridge and control-plane boundaries unchanged and promotes the datagram transport slice toward clearer operator verification and public runtime/config validation:

- `ns-testkit` now provides `udp_interop_lab`, which executes the maintained deterministic impairment profiles and emits a machine-readable JSON summary instead of only human-readable wrapper output
- `ns-client-runtime` now exposes both a public startup datagram contract and a reusable negotiated datagram-contract validation helper so signed intent, rollout posture, carrier support, and negotiated UDP limits can be checked through public tooling instead of only library tests
- `ns-clientd` and `nsctl` now surface that client-side contract explicitly, while `ns-gatewayd` now prints the derived advertised datagram posture directly in its validation output
- wrong associated-stream recovery and post-close rogue datagram handling now also assert that an established datagram selection does not silently degrade into stream fallback
- the optional UDP verification lane now includes a short active-fuzz path while keeping 0-RTT disabled and leaving the bridge topology unchanged

These are transport-hardening and verification-lane notes only.
They do not widen the session-core transport boundary, change bridge topology, or enable `0-RTT`.

## Milestone 19 Implementation Notes

Milestone 19 keeps bridge and control-plane boundaries unchanged and promotes the datagram transport slice toward broader compatible-host interoperability evidence and rollout-readiness:

- `ns-clientd` now exposes negotiated datagram-contract validation directly through a public CLI surface instead of keeping that check inside library-only tests
- `ns-gatewayd` now exposes startup datagram posture validation directly from signed intent, rollout stage, and carrier-support inputs
- the maintained compatible-host workflow now runs the machine-readable UDP interoperability harness on Linux while leaving the Windows-first smoke, perf, and WAN-lab wrappers unchanged
- active UDP fuzz wrappers now sync reviewed corpora before fuzzing so compatible-host runs stay aligned with the maintained fixture-derived seed set
- clean datagram shutdown and queue-pressure behavior now assert that an established datagram selection does not silently degrade into stream fallback
- the UDP perf gate now emits a machine-readable summary file in addition to its ratio-based pass or fail thresholds

These are transport-hardening and verification-lane notes only.
They do not widen the session-core transport boundary, change bridge topology, or enable `0-RTT`.

## Milestone 20 Implementation Notes

Milestone 20 keeps bridge and control-plane boundaries unchanged and tightens the public startup-validation and rollout-evidence story around the existing datagram slice:

- the H3 transport layer now exposes a shared startup-contract resolver so client and gateway validation surfaces derive the same advertised datagram posture from signed intent, rollout stage, and carrier availability
- `ns-clientd`, `ns-gatewayd`, and `nsctl` now label manual readiness facts as `simulated_inputs=true` so operator-facing validation output is not mistaken for a live transport probe
- the broader compatible-host rollout-readiness lane now combines maintained smoke, perf, interop, queue-pressure, and shutdown checks while preserving the existing Windows-first wrappers and machine-readable summaries
- active fuzz keeps using the narrow decoder surface, but now replays smoke first, includes `control_frame_decoder`, and stays aligned with the reviewed hello, ping, and UDP-control corpus
- the maintained perf threshold surface now includes `H3DatagramSocket.queue_recovery_send` so short saturation recovery remains observable without changing transport semantics or adding a new event family

These are transport-hardening and verification-discipline notes only.
They do not widen the session-core transport boundary, change bridge topology, or enable `0-RTT`.

## Milestone 21 Implementation Notes

Milestone 21 keeps bridge and control-plane boundaries unchanged and pushes the existing datagram slice toward deployment-candidate operator validation:

- maintained startup and negotiated datagram-contract checks are now covered across `ns-clientd`, `nsctl`, and `ns-gatewayd`, including explicit client-version inputs and fail-closed boolean parsing for signed datagram intent on the public CLI surfaces
- repeated queue pressure and prolonged impairment now both assert that an established datagram selection stays pinned and does not emit a later `stream_fallback` selection unless the frozen spec grows an explicit allowance
- the maintained compatible-host verification story now includes `udp_rollout_validation_lab`, which replays the public CLI validation surfaces plus the sticky-selection live tests and writes a machine-readable summary for staged rollout review
- reviewed corpus growth now includes an MTU-boundary valid `UDP_DATAGRAM` fixture and a truncated datagram regression fixture so decoder fuzz and conformance stay aligned with the hardened transport slice

These are transport-hardening and verification-discipline notes only.
They do not widen the session-core transport boundary, change bridge topology, or enable `0-RTT`.

## Milestone 22 Implementation Notes

Milestone 22 keeps bridge and control-plane boundaries unchanged and broadens the rollout-readiness evidence around the existing datagram slice:

- `ns-clientd`, `nsctl`, and `ns-gatewayd` now emit consistent text and JSON startup or negotiated datagram-contract output so maintained operator-facing validation surfaces line up across public CLI entry points
- repeated queue pressure now proves both low-cardinality guard emission and post-drain datagram recovery without later `stream_fallback` selection
- the maintained delayed-delivery plus short-black-hole live test now runs one more impairment-and-recovery cycle before shutdown so longer degradation windows stay covered without changing transport semantics
- reviewed corpus growth now includes truncated `UDP_FLOW_CLOSE` and truncated `UDP_STREAM_CLOSE` regressions so close or rejection paths stay aligned with conformance and fuzz seeds
- the maintained compatible-host verification story now includes `udp-rollout-readiness.*`, which combine corpus sync, smoke, perf, interop, and rollout-validation summaries into one fail-evident operator recipe
- `.github/workflows/udp-optional-gates.yml` now includes a compatible-host macOS rollout-readiness lane in addition to the Linux rollout-readiness and Windows rollout-validation lanes while keeping Windows-first local wrappers unchanged

These are transport-hardening and rollout-discipline notes only.
They do not widen the session-core transport boundary, change bridge topology, or enable `0-RTT`.

## Milestone 24 Implementation Notes

Milestone 24 keeps bridge and control-plane boundaries unchanged and strengthens the staged-rollout discipline around the existing datagram slice:

- the maintained rollout-comparison surface now supports a stricter `staged_rollout` profile that consumes the same smoke, perf, interop, and rollout-validation summaries plus the active-fuzz summary on compatible hosts
- staged rollout blocking reasons are now stable and reusable across hosts instead of being inferred from ad hoc wrapper failures
- maintained public validation commands in `ns-clientd`, `nsctl`, and `ns-gatewayd` now expose comparison-friendly `comparison_family` and `comparison_label` fields in both text and JSON modes
- rollout-validation summaries now project normalized queue-guard headroom bands and path-level queue-guard pass/fail facts from the maintained perf thresholds
- a compatible-host Linux staged-rollout workflow lane now exercises that stricter comparison profile while leaving the Windows-first local wrappers intact

These are transport-hardening and rollout-discipline notes only.
They do not widen the session-core transport boundary, change bridge topology, or enable `0-RTT`.

## Milestone 25 Implementation Notes

Milestone 25 does not widen carrier ownership or transport semantics.
It tightens how maintained datagram rollout evidence is summarized and reviewed:

- `udp_rollout_compare` now emits one stable reusable operator-verdict schema across readiness and staged-rollout profiles
- maintained CLI validation surfaces in `ns-clientd`, `nsctl`, and `ns-gatewayd` now emit stable `comparison_schema` and `comparison_schema_version` fields in both text and JSON modes
- `udp_rollout_validation_lab` now projects `selected_datagram_lifecycle_passed` and `queue_guard_limiting_path` so sticky datagram selection and the currently limiting queue-guard surface stay machine-readable
- `.github/workflows/udp-optional-gates.yml` now includes a workflow-backed Linux rollout-matrix lane that consumes compatible-host rollout-comparison summaries and emits a machine-readable cross-host verdict
- reviewed malformed-input coverage now includes non-canonical `UDP_FLOW_CLOSE`, `UDP_STREAM_OPEN`, and `UDP_STREAM_ACCEPT` seeds to keep control and fallback decoding aligned with the frozen rejection rules

These are verification, comparison, and observability notes only.
They do not change the frozen carrier contract, datagram backend choice, or the rule that `ns-session` stays transport-agnostic.

## Milestone 26 Implementation Notes

Milestone 26 keeps the carrier contract and bridge boundaries unchanged and strengthens reusable operator-verdict evidence around the existing datagram slice:

- host-level rollout comparison and cross-host rollout-matrix summaries now share the same operator-verdict schema, family, decision-scope fields, and stable blocking-reason semantics
- rollout-validation summaries now record `longer_impairment_recovery_stable` from the maintained repeated bounded-loss path instead of treating only a simple happy-path round trip as shutdown evidence
- maintained public validation commands in `ns-clientd`, `nsctl`, and `ns-gatewayd` now emit comparison-friendly `comparison_scope` and `comparison_profile` fields in both text and JSON modes
- reviewed malformed-input coverage now includes non-canonical `UDP_DATAGRAM`, `UDP_FLOW_OK`, and `UDP_STREAM_CLOSE` seeds so conformance, corpus sync, and active fuzz stay aligned with frozen rejection behavior
- `.github/workflows/udp-optional-gates.yml` now adds a compatible-host macOS staged-rollout lane with active-fuzz evidence and machine-readable comparison output while keeping the Windows-first local wrappers unchanged

These are verification, comparison, and observability notes only.
They do not change the frozen carrier contract, datagram backend choice, or the rule that `ns-session` stays transport-agnostic.

## Milestone 27 Implementation Notes

Milestone 27 keeps the carrier contract and bridge boundaries unchanged and tightens release-candidate rollout evidence around the existing datagram slice:

- host-level rollout comparison and cross-host rollout-matrix summaries now share operator-verdict schema version `6`, including explicit `all_required_inputs_present` and `all_required_inputs_passed` facts for reusable staged-rollout decisions
- the same operator-verdict surfaces now fail closed on unsupported upstream summary/schema versions and expose stable required-input counts plus blocking-reason key aggregation instead of relying on host-specific reason strings alone
- `.github/workflows/udp-optional-gates.yml` now adds a workflow-backed Linux staged-rollout matrix lane that compares Linux and macOS staged-rollout evidence without introducing new carrier or session semantics
- reviewed malformed-input coverage now includes non-canonical `UDP_FLOW_OK` flow ids and non-canonical UDP fallback-packet lengths so maintained conformance and active fuzz stay aligned with the frozen rejection rules
- rollout-validation summaries now make longer-impairment recovery, shutdown-sequence stability, and passed/failed command counts explicit for release-candidate operator review
- longer impairment, repeated queue pressure, and clean shutdown still preserve the no-silent-fallback rule under the existing live UDP degradation coverage; milestone 27 does not introduce a transport-mode change path

These are verification, comparison, and observability notes only.
They do not change the frozen carrier contract, datagram backend choice, or the rule that `ns-session` stays transport-agnostic.

## Milestone 23 Implementation Notes

Milestone 23 keeps bridge and control-plane boundaries unchanged and promotes the existing datagram slice toward an alpha-candidate staged-rollout workflow:

- the maintained rollout recipe now ends with a machine-readable comparison surface in `udp_rollout_compare`, which consumes smoke, perf, interop, and rollout-validation summaries and emits one staged-rollout verdict per host or lane
- the maintained rollout-validation summary now records normalized queue-saturation evidence through `queue_saturation_worst_case`, `queue_saturation_worst_utilization_pct`, `sticky_selection_surface_passed`, and `rollout_surface_passed`
- public CLI startup and negotiated validation surfaces across `ns-clientd`, `nsctl`, and `ns-gatewayd` now emit consistent `validation_result=valid|invalid` text and JSON output instead of mixing success-only structured output with unstructured mismatch failures
- a compatible-host Windows rollout-readiness lane now exists alongside the Linux and macOS readiness lanes while keeping the existing Windows-first local wrappers unchanged

These are transport-hardening and rollout-discipline notes only.
They do not widen the session-core transport boundary, change bridge topology, or enable `0-RTT`.
