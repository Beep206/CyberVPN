# Northstar Protocol RFC Draft v0.1

**Status:** Draft RFC v0.1  
**Codename:** Northstar  
**Document type:** protocol RFC-style draft for the Northstar adaptive proxy/VPN protocol suite  
**Audience:** protocol architects, Rust implementers, bridge/control-plane engineers, client engineers, security reviewers, SREs, test engineers, AI coding agents  
**Intended role:** normative protocol document for semantics and interoperability; companion documents remain authoritative for exact binary encoding, bridge specifics, security validation, and workspace structure  
**Companion documents:**
- `Adaptive Proxy/VPN Protocol Master Plan`
- `Blueprint v0 — Adaptive Proxy/VPN Protocol Suite (Northstar)`
- `Northstar Spec v0.1 — Wire Format Freeze Candidate`
- `Northstar Remnawave Bridge Spec v0.1`
- `Northstar Threat Model v0.1`
- `Northstar Security Test & Interop Plan v0.1`
- `Northstar Implementation Spec / Rust Workspace Plan v0.1`

---

## Abstract

Northstar is an adaptive proxy/VPN protocol suite designed for long-term operational agility rather than dependence on one static transport persona. The protocol suite separates a compact session core from carrier bindings, rollout profiles, and control-plane integration. In v0.1, Northstar is scoped to a custom client, a Rust gateway, and an external Bridge service that integrates with Remnawave without forking the panel.

This document describes the protocol in RFC style: architecture, roles, session lifecycle, capability negotiation, traffic modes, security properties, interoperability requirements, extension rules, and deployment guidance. The exact wire layout for v0.1 remains frozen in the companion freeze-candidate document; this draft focuses on normative protocol behavior and semantics.

---

## 1. Why this document exists

The Northstar document set now has:

- a strategic plan
- a high-level technical blueprint
- a frozen wire contract
- a Bridge integration spec
- a threat model
- a security and interoperability plan
- a Rust workspace and implementation plan

What was still missing was a protocol document that developers, reviewers, and future third-party implementers can read as the main protocol reference.

This document fills that role.

It explains:

- what Northstar is
- what problems it is explicitly trying to solve
- how the protocol suite is decomposed
- how a session is established, used, drained, and closed
- how TCP and UDP relay are modeled
- how tokens, manifests, and device policy interact with the protocol
- how backward compatibility and extension safety are preserved

This document is intentionally more formal than the Blueprint and more architectural than the Freeze Candidate. In the current document family, it acts as the central semantic specification.

---

## 2. Status of this draft

This is **not** a public standards-track RFC.

It is a project-internal RFC-style draft that serves five purposes:

1. provide one normative protocol narrative for the entire Northstar stack
2. reduce ambiguity before substantial implementation work begins
3. keep human developers and AI coding agents aligned
4. make future external review easier
5. prepare the protocol for eventual public specification work if the project matures

For v0.1:

- this document is **normative for semantics and interoperability expectations**
- the **Freeze Candidate** remains **authoritative for exact binary field order, ids, and canonical encoding**
- the **Bridge Spec** remains **authoritative for Remnawave adapter behavior and Bridge-owned state**

If a contradiction appears:

1. the Freeze Candidate wins for exact wire format
2. the Bridge Spec wins for Bridge/API behavior
3. this RFC draft wins for high-level protocol semantics not already frozen elsewhere

---

## 3. Design goals

Northstar exists to satisfy a specific engineering goal set.

### 3.1 Primary goals

Northstar MUST:

1. provide reliable TCP relay with a small, reviewable session core
2. provide UDP relay with both datagram and stream-fallback modes
3. keep protocol semantics stable while allowing transport persona changes over time
4. support remote policy updates and graceful drain behavior
5. support Bridge-issued short-lived session credentials
6. support external control-plane integration without requiring a Remnawave fork
7. support strict observability, testing, and controlled rollout
8. remain practical to implement and audit in Rust

### 3.2 Secondary goals

Northstar SHOULD:

1. keep the session core transport-agnostic above the carrier binding
2. isolate fingerprint-sensitive behavior in carrier profiles rather than in the session core
3. preserve compatibility discipline from the first release
4. make future carriers possible without redesigning the session layer
5. allow future IP tunnel mode without breaking v0.1 sessions

### 3.3 Non-goals for v0.1

Northstar v0.1 does **not** attempt to:

- be a full general-purpose VPN tunnel in the initial release
- standardize GUI behavior
- standardize all operator/admin APIs
- support all possible carriers from day one
- include 0-RTT or session resumption
- define post-quantum migration behavior
- define multi-path, FEC, or mobile-first optimization as launch requirements

---

## 4. Conventions and terminology

The key words **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** are normative.

### 4.1 Roles

**Client**  
The Northstar endpoint running on the user device. It imports a manifest, obtains a session token, establishes the carrier connection, opens relay streams and UDP flows, and enforces local policy.

**Gateway**  
The Rust server-side data-plane endpoint. It terminates the carrier session, validates session authorization indirectly through Bridge-issued credentials, applies session policy, and relays TCP/UDP traffic.

**Bridge**  
The service that adapts Remnawave lifecycle and subscription state into Northstar-native manifests, refresh credentials, session tokens, and endpoint/profile policy.

**Carrier**  
The transport substrate below the Northstar session core. In v0.1, the only required production carrier is HTTP/3 over QUIC.

**Manifest**  
The signed client-consumable configuration object that tells the client which endpoints, profiles, policies, and capabilities it may use.

**Carrier profile**  
A remotely selectable configuration set that determines how the carrier is presented and tuned. Carrier profiles are intentionally external to the session core.

### 4.2 Session objects

**Control stream**  
The unique reliable bidirectional stream for control frames.

**Relay stream**  
A reliable stream dedicated to one TCP relay connection.

**UDP flow**  
A session-scoped logical UDP relay object opened over the control stream and then carried using datagrams or stream fallback.

**Policy epoch**  
A monotonically increasing server-selected policy version identifier for the active session.

---

## 5. Protocol suite overview

Northstar is a **protocol suite**, not a single packet format.

Its architecture is intentionally layered.

```text
+------------------------------------------------------------+
| Control plane integration (Remnawave + Bridge)             |
+------------------------------------------------------------+
| Manifest / token / device policy / endpoint selection      |
+------------------------------------------------------------+
| Northstar session core                                     |
|   - hello negotiation                                      |
|   - control frames                                         |
|   - relay semantics                                        |
|   - policy updates                                         |
|   - error signaling                                        |
+------------------------------------------------------------+
| Carrier binding                                            |
|   - h3 over QUIC in v0.1                                   |
|   - future raw_quic / h2_tls / others reserved             |
+------------------------------------------------------------+
| TLS / QUIC / OS networking                                 |
+------------------------------------------------------------+
```

The architectural principle is simple:

- the **session core** stays small and stable
- the **carrier** can evolve
- the **profile/persona layer** can change faster than the session core
- the **Bridge** handles control-plane translation and rollout policy

This separation is mandatory. Northstar MUST NOT encode control-plane, device-lifecycle, and transport-persona logic into one monolithic handshake.

---

## 6. Scope of v0.1

### 6.1 In scope

Northstar v0.1 covers:

- custom Northstar client
- Rust gateway
- external Bridge service
- Remnawave integration without panel fork
- one session core version: `1`
- one manifest schema version: `1`
- one public Bridge API namespace: `/v0/*`
- one primary carrier: `h3`
- TCP relay
- UDP relay via datagram when available
- UDP relay via stream fallback when datagrams are unavailable or disabled
- policy push
- graceful drain
- session-scoped telemetry and path hints

### 6.2 Explicitly deferred

The following are intentionally deferred:

- full IP tunnel mode
- multipath semantics
- resumption / 0-RTT
- alternate carriers as production-grade defaults
- mobile SDK stability guarantees
- public multi-language reference libraries
- public third-party gateway interoperability commitments beyond the project itself

---

## 7. Versioning model

Northstar has multiple version axes.

### 7.1 Version axes

1. **Session core version** — the on-wire protocol version
2. **Manifest schema version** — the configuration object version understood by clients
3. **Bridge API version** — the public HTTP API namespace for client bootstrap and refresh
4. **Carrier profile generation** — the operational profile revision used by clients and gateways

These version axes MUST remain independent.

### 7.2 v0.1 baseline

For the first serious implementation baseline:

- Session core version = `1`
- Manifest schema version = `1`
- Bridge API prefix = `/v0`
- Primary carrier = `h3`

### 7.3 Compatibility rule

Changes that alter existing frame meaning, field order, fixed-size field length, or enum semantics MUST NOT occur without an explicit compatibility plan.

Additive changes MAY be introduced when:

- they are safely ignorable by older peers
- they do not reinterpret frozen ids
- they are reflected in the compatibility and conformance corpus

---

## 8. Carrier binding model

### 8.1 Required carrier in v0.1

Northstar v0.1 requires support for:

- `CarrierKind = h3`

The carrier is responsible for:

- confidentiality
- integrity
- stream multiplexing
- optional datagrams
- connection migration behavior native to the carrier stack

The Northstar session core is responsible for:

- capability negotiation
- relay semantics
- policy semantics
- error semantics
- session lifecycle semantics

### 8.2 Carrier assumptions

The carrier MUST provide:

1. one reliable bidirectional control stream
2. additional reliable bidirectional streams
3. a mechanism to expose datagram availability or lack thereof

If datagrams are unavailable, the session MUST still be able to function for TCP relay and UDP stream fallback if those capabilities were negotiated.

### 8.3 Carrier profile separation

Carrier-specific presentation, tuning, and anti-fingerprinting behavior MUST be treated as profile data, not as hard-coded protocol logic.

This requirement is central to Northstar’s long-term adaptability.

---

## 9. Session lifecycle

Northstar sessions proceed through a small set of states.

```text
INIT
  -> HANDSHAKING
  -> ESTABLISHED
  -> DRAINING
  -> CLOSED
```

### 9.1 Pre-session bootstrap

Before the network session begins, the client typically performs:

1. manifest acquisition or refresh from the Bridge
2. local policy validation
3. endpoint selection
4. optional refresh-token exchange for a short-lived session token
5. carrier profile selection from manifest policy

These bootstrap steps are outside the raw session wire protocol but are required operationally.

### 9.2 Handshake start

The first frame on the control stream MUST be `CLIENT_HELLO`.

Before the client receives `SERVER_HELLO`, it MUST NOT:

- open relay streams
- open UDP flows
- emit path hints
- send stats

### 9.3 Session establishment

A session becomes **established** when:

1. the client has sent a valid `CLIENT_HELLO`
2. the server has accepted the session
3. the server has sent a valid `SERVER_HELLO`
4. the client has validated the server response against its local expectations

### 9.4 Normal active phase

In the established phase the client MAY:

- open relay streams
- open UDP flows
- send keepalive probes
- send path-change hints
- send stats if allowed

The gateway MAY:

- accept or reject new relay attempts
- accept or reject UDP flows
- push policy updates
- send `GOAWAY`
- send terminal or non-terminal errors

### 9.5 Draining

A session enters **draining** when the gateway sends `GOAWAY` or policy indicates drain-only behavior.

In draining state:

- the client MUST stop opening new relay streams
- the client SHOULD stop opening new UDP flows
- existing streams MAY continue until completion or deadline
- the client SHOULD prefer alternate endpoints if such guidance exists

### 9.6 Closure

A session becomes closed when:

- either side sends terminal session closure and the carrier is shut down
- the control stream fails irrecoverably
- the handshake times out
- the underlying carrier connection terminates

---

## 10. Handshake and capability negotiation

### 10.1 Purpose of the handshake

The Northstar handshake is not a transport disguise layer.

Its function is limited to:

- selecting a compatible protocol version
- selecting an allowed carrier profile
- validating that the client’s session token authorizes this session
- selecting a subset of capabilities
- advertising effective policy and resource limits

The handshake MUST remain small and auditable.

### 10.2 Client obligations

The client MUST send a `CLIENT_HELLO` containing, at minimum:

- supported version range
- client nonce
- requested capabilities
- carrier kind
- carrier profile identifier
- manifest identifier
- device binding identifier
- requested idle timeout
- requested max UDP payload
- session token

The client SHOULD send metadata only when useful for diagnostics, rollout segmentation, or operational policy.

### 10.3 Gateway obligations

The gateway MUST validate enough session context to answer these questions:

1. is the token authentic?
2. is the token valid now?
3. is the client allowed to use this profile and endpoint?
4. is the requested core version acceptable?
5. which capabilities are permitted?
6. which effective limits apply?

If validation fails, the gateway SHOULD send the most specific practical `ERROR` and terminate the session.

### 10.4 Server response

The gateway responds with `SERVER_HELLO`, which commits the active session contract:

- selected core version
- session id
- server nonce
- selected capabilities
- policy epoch
- effective idle timeout
- session lifetime
- concurrency limits
- UDP payload limit
- datagram mode
- stats mode
- optional server metadata

The client MUST reject a `SERVER_HELLO` that is inconsistent with its own request or with the frozen receiver rules.

### 10.5 Capability subset rule

The server MUST only select a subset of client-requested capabilities.

It MUST NOT introduce capabilities the client did not request.

### 10.6 No hidden negotiation

All semantics that meaningfully affect on-wire behavior MUST be explicitly represented by:

- version
- capability ids
- frame semantics
- policy fields
- manifest data

Northstar MUST NOT rely on implicit negotiation through packet timing or implementation quirks.

---

## 11. Control stream semantics

The control stream is the session backbone.

### 11.1 Uniqueness

Each session has exactly one control stream.

If the control stream becomes unreadable or corrupted, the session MUST be treated as failed.

### 11.2 Control responsibilities

The control stream carries:

- hello negotiation
- keepalive probes
- error signaling
- drain requests
- policy updates
- UDP flow control objects
- optional stats
- path-change hints
- session close semantics

### 11.3 Ordering expectations

Control frames are processed in order as received on the control stream.

Frame handling MUST follow the frozen sequencing rules.

### 11.4 Unknown control frames

Unknown control frames in v0.1 are fatal protocol errors.

This strictness is intentional for the first release because it reduces ambiguity, prevents silent feature mismatches, and simplifies conformance testing.

---

## 12. Relay stream semantics for TCP

### 12.1 Stream model

Each TCP relay connection uses one dedicated carrier stream.

That stream begins with a Northstar preamble (`STREAM_OPEN` from client, followed by either `STREAM_ACCEPT` or `STREAM_REJECT` from gateway). If accepted, the stream transitions to raw byte relay mode.

### 12.2 Client behavior

To open a TCP relay the client MUST:

1. allocate a session-unique `RelayId`
2. open a carrier stream
3. send `STREAM_OPEN`
4. wait for acceptance or rejection

The client MUST NOT reuse an active `RelayId`.

### 12.3 Gateway behavior

The gateway MUST decide whether the requested target is allowed under policy.

If allowed, it sends `STREAM_ACCEPT`; otherwise it sends `STREAM_REJECT` or closes the stream according to the frozen preamble behavior.

### 12.4 Raw relay mode

After `STREAM_ACCEPT`, the stream carries only raw relayed TCP bytes.

Northstar frame envelopes MUST NOT continue on that stream once raw relay mode begins.

### 12.5 Target addressing

Northstar v0.1 supports target types for:

- domain
- IPv4
- IPv6

Target validation MUST follow the frozen target-type rules and length constraints.

---

## 13. UDP relay semantics

Northstar v0.1 supports two UDP transport modes for an opened UDP flow.

### 13.1 Flow creation

The client opens a logical UDP relay object using `UDP_FLOW_OPEN` on the control stream.

The request includes:

- `FlowId`
- target type and target address
- target port
- requested idle timeout
- flow flags
- optional metadata

The server answers with `UDP_FLOW_OK` or rejects implicitly through `ERROR` or explicit flow closure, depending on the context and implementation path.

### 13.2 Datagram mode

If datagrams are available and allowed, the server MAY choose datagram mode.

In datagram mode:

- each datagram contains a small Northstar UDP payload header plus payload
- no additional stream is required for packets
- flow closure still occurs via the control stream

### 13.3 Stream fallback mode

If datagrams are unavailable, disabled, or unsuitable, the server MAY select stream fallback.

In fallback mode:

- the client opens a dedicated fallback stream for the flow
- the stream starts with `UDP_STREAM_OPEN`
- the gateway responds with `UDP_STREAM_ACCEPT`
- packets are exchanged using framed `UDP_STREAM_PACKET` messages
- closure uses `UDP_STREAM_CLOSE`

### 13.4 Required robustness rule

Northstar v0.1 clients MUST support UDP stream fallback.

This requirement exists so that UDP relay survives datagram-unfriendly environments.

### 13.5 Flow uniqueness and lifetime

`FlowId` is session-scoped and MUST remain unique among active flows.

A flow MUST be considered terminated after `UDP_FLOW_CLOSE` has been processed.

---

## 14. Keepalive, liveness, and timing

### 14.1 PING / PONG

Either side MAY send `PING` on the control stream.

The receiver SHOULD answer with `PONG` promptly.

### 14.2 Idle and deadline policy

The effective idle timeout and lifetime are committed by the server in `SERVER_HELLO` and may later be updated by `POLICY_UPDATE` if the protocol rules allow it.

### 14.3 Failure handling

If the handshake deadline expires before a valid `SERVER_HELLO` arrives, the client MUST terminate the session.

If the control stream fails, the session MUST be considered closed.

### 14.4 Operational tuning

Timer constants are implementation defaults, not protocol ids, unless specifically frozen elsewhere.

---

## 15. Policy updates and graceful drain

### 15.1 Dynamic policy model

Northstar supports limited mid-session policy adjustment.

The server MAY send `POLICY_UPDATE` to change effective session limits and policy flags for the active session.

### 15.2 Authoritative semantics

A received `POLICY_UPDATE` is authoritative for the active session.

The client MUST apply the new effective limits immediately.

### 15.3 Drain semantics

The server MAY send `GOAWAY` to initiate graceful drain.

Typical reasons include:

- planned maintenance
- overload
- endpoint deprecation
- profile rotation
- policy change

### 15.4 Client reaction to `GOAWAY`

On receiving `GOAWAY`, the client:

- MUST stop opening new relay streams
- SHOULD stop opening new UDP flows
- SHOULD prefer listed replacement endpoints when practical
- MAY allow existing traffic to complete until deadline or transport closure

---

## 16. Error model

### 16.1 General principles

Northstar distinguishes between:

- protocol errors
- policy rejections
- resource-limit failures
- target or relay failures
- session lifecycle events

### 16.2 Error signaling

Structured errors use the `ERROR` frame.

Implementations MUST key behavior on `ErrorCode`, not on human-readable error text.

### 16.3 Terminal vs non-terminal errors

The `ERROR` frame includes an explicit terminal flag.

If `IsTerminal = true` on the control stream, the receiver SHOULD expect imminent session termination.

### 16.4 Malformed input handling

Malformed, non-canonical, or out-of-order input MUST be handled according to the frozen receiver rules.

The implementation MUST prefer deterministic failure over ambiguous recovery for v0.1.

### 16.5 Unknown frames and ids

Unknown or illegal frame types in contexts where the peer cannot safely ignore them MUST be treated as protocol violations.

---

## 17. Authentication, authorization, and device binding

### 17.1 Design principle

Northstar does not treat a long-lived static user identifier as the entire authentication model.

Instead, it separates:

- longer-lived client provisioning state (manifest, refresh credential, device binding)
- short-lived session authorization (session token)
- per-session negotiation (hello and selected capabilities)

### 17.2 Session token

The client MUST present a Bridge-issued session token in `CLIENT_HELLO`.

The gateway MUST validate the token before establishing the session.

The token SHOULD be:

- short-lived
- scoped to allowed profiles/endpoints/capabilities as practical
- bound to the current manifest and device context where policy requires it

### 17.3 Device binding

If policy requires device binding, the client MUST send the relevant `DeviceBindingId` and the gateway MUST reject a session whose token or policy does not authorize that binding.

### 17.4 Manifest coupling

The manifest identifier supplied by the client is part of the operational contract. It allows the gateway and observability pipeline to reason about what configuration generation the client is attempting to use.

### 17.5 Deferred topics

Northstar v0.1 defers:

- session resumption credentials
- 0-RTT authorization
- final public token profile standardization beyond the frozen reference profile

---

## 18. Remnawave integration model

### 18.1 Integration boundary

Northstar v0.1 uses Remnawave as the external control-plane authority for user lifecycle and subscription context, while the Bridge remains authoritative for:

- Northstar-native manifests
- refresh credentials
- session tokens
- device binding reconciliation
- endpoint/profile compilation

### 18.2 Non-fork principle

The protocol and deployment model are explicitly designed so the project does not need to fork Remnawave or embed itself into Xray-core for the chosen v0.1 path.

### 18.3 Bridge importance

The Bridge is not optional glue. It is a protocol-critical component because it turns external lifecycle state into Northstar-authoritative session context.

### 18.4 Contract source

Operational details, HTTP APIs, webhook handling, reconciliation, and ownership rules for this integration are defined in the Bridge Spec, not in this RFC draft.

---

## 19. Observability and path-change signaling

### 19.1 Telemetry principles

Northstar requires observability but MUST avoid turning telemetry into a protocol dependency for correctness.

The protocol MUST function correctly even when stats are disabled.

### 19.2 Stats

If negotiated and allowed, either side MAY send `SESSION_STATS` according to policy.

Stats payloads MUST be treated as advisory telemetry, not as protocol control.

### 19.3 Path hints

The client MAY send `PATH_EVENT` to signal likely network-path changes such as:

- network change
- suspected NAT rebinding
- MTU decrease
- MTU increase

These hints are advisory. They MUST NOT be trusted as security assertions.

### 19.4 Privacy constraint

Implementations SHOULD minimize metadata content and retention for stats and path hints.

---

## 20. Extensibility model

### 20.1 Principle

Northstar is designed for controlled extension, not informal mutation.

### 20.2 Extension surfaces

The following surfaces are intended to be extended over time:

- capability registry
- TLV registry
- future carrier kinds
- future control/preamble extension frame ranges
- manifest properties that older clients can ignore safely

### 20.3 Hard prohibition

Implementations MUST NOT reuse existing ids with different meanings.

### 20.4 Safe-addition rule

An extension is only safe when:

1. old peers can deterministically reject it or ignore it
2. the compatibility corpus is updated
3. the security analysis is updated if the extension changes attack surface
4. the implementation plan and tests are updated accordingly

### 20.5 Reserved future work

Northstar v0.1 reserves room for:

- resumption hints
- manifest delta delivery
- IP tunnel mode
- alternate carriers

Reserved ids are not active features.

---

## 21. Security considerations

### 21.1 Core security position

Northstar relies on well-reviewed carrier cryptography and keeps its own session core deliberately small.

The protocol MUST NOT invent custom cryptographic primitives or rely on secrecy of protocol structure.

### 21.2 Critical properties

The design aims to preserve:

- confidentiality and integrity at the carrier layer
- explicit authorization of each session
- downgrade resistance through explicit version and capability checks
- resistance to silent feature mismatch
- bounded resource consumption through policy and implementation limits

### 21.3 Mandatory controls

Any implementation claiming v0.1 compatibility MUST implement at least:

- strict version-range validation
- strict subset validation for negotiated capabilities
- canonical varint enforcement
- reserved-bit rejection where specified
- explicit limits for frame sizes, counts, and payload sizes
- deterministic malformed-input handling
- short-lived session tokens
- proper token expiry and not-before validation
- session and flow id uniqueness enforcement
- auditability of terminal failures

### 21.4 Anti-probing and agility posture

Northstar’s long-term adaptability MUST come primarily from carrier/profile agility and not from repeatedly mutating the session core.

### 21.5 Full security analysis source

Threat classes, attacker models, required controls, and launch gates are defined in detail in `Northstar Threat Model v0.1`.

---

## 22. Privacy considerations

Northstar deployments MUST treat privacy as a first-class operational property.

### 22.1 Data minimization

Clients and gateways SHOULD minimize:

- metadata sent in hello frames
- stats detail level
- retention of target-level observability
- personally identifying diagnostic fields

### 22.2 Token scope

Session tokens SHOULD contain only the minimum claims required for secure authorization and operational debugging.

### 22.3 Linkability

Long-lived identifiers SHOULD be avoided on the wire when short-lived or indirect identifiers are sufficient.

### 22.4 Logging discipline

Sensitive tokens, refresh credentials, and manifest secrets MUST NOT be logged in raw form.

---

## 23. Interoperability requirements

### 23.1 Conformance baseline

An implementation MUST NOT claim v0.1 compatibility unless it can pass the project’s conformance and interop suite for:

- hello negotiation
- relay stream handling
- UDP flow handling
- malformed input handling
- policy updates
- drain behavior
- token validation edge cases

### 23.2 Fixture discipline

Frozen fixture ids and binary examples MUST be used in tests to keep independent implementations aligned.

### 23.3 Unknown-feature behavior

Implementations MUST follow the frozen unknown-frame and unknown-id handling rules rather than inventing permissive local behavior.

### 23.4 Reference source

The detailed validation matrix is defined in `Northstar Security Test & Interop Plan v0.1`.

---

## 24. Operational considerations

### 24.1 Rollout philosophy

Northstar SHOULD be rolled out incrementally:

1. local development and conformance
2. synthetic impairment lab
3. closed alpha
4. limited canary by endpoint/profile segment
5. broader beta
6. public production rollout

### 24.2 Profile rotation

Carrier profiles SHOULD be remotely rotatable without changing the session core.

### 24.3 Graceful deprecation

When an endpoint or profile must be retired, implementations SHOULD prefer `GOAWAY` plus replacement guidance rather than abrupt failure, except when security or abuse conditions require immediate termination.

### 24.4 Resource budgeting

Implementations MUST enforce practical ceilings for:

- control-frame size
- stream counts
- flow counts
- token size
- metadata counts
- UDP payload size

### 24.5 Observability requirement

Deployments SHOULD include enough metrics, tracing, and structured logging to distinguish:

- protocol failures
- auth failures
- policy rejections
- target failures
- network-path instability
- performance regressions

---

## 25. Implementation status for v0.1

This section is informative.

The intended first implementation set is:

- Rust client
- Rust gateway
- Rust Bridge
- Remnawave adapter path without forking the panel

The reference repository structure and crate boundaries are defined in `Northstar Implementation Spec / Rust Workspace Plan v0.1`.

The existence of one reference implementation does not, by itself, redefine the protocol. The document set remains the source of truth.

---

## 26. IANA-style project registries

Northstar is not using IANA, but the project MUST maintain internal registries for:

- capability ids
- carrier kind ids
- frame type ids
- error code ids
- target type ids
- datagram mode ids
- stats mode ids
- policy flags
- path event ids
- TLV ids

The initial registry assignments are frozen in `Northstar Spec v0.1 — Wire Format Freeze Candidate`.

Any future assignment MUST include:

- rationale
- compatibility impact
- security review note
- test coverage update

---

## 27. Deferred topics and future standardization path

The following items are intentionally deferred from the first production-grade protocol baseline but remain important:

- full IP tunnel mode
- session resumption and 0-RTT
- alternate carrier bindings
- public extension registry policy
- third-party implementation guidance beyond the project itself
- mobile-specific power and roaming optimizations
- public governance for protocol evolution
- formal operator/admin APIs

If the project reaches a stable public maturity level, the likely future documentation path is:

1. merge semantic and binary specs into a cleaner `Protocol Spec v1.0`
2. publish a stand-alone public token/auth profile
3. publish a public carrier-binding document
4. publish a third-party interoperability profile

---

## 28. Companion document map

This RFC draft should be read with the rest of the Northstar document set.

| Document | Primary role |
|---|---|
| Master Plan | multi-phase roadmap and strategy |
| Blueprint v0 | high-level architecture and buildable design baseline |
| Freeze Candidate v0.1 | exact binary contract, ids, encoding, fixtures, manifest schema, Bridge API draft |
| Remnawave Bridge Spec v0.1 | control-plane integration and Bridge ownership rules |
| Threat Model v0.1 | attacker model, required controls, launch gates |
| Security Test & Interop Plan v0.1 | validation program, fuzzing, interop, release gates |
| Implementation Spec / Rust Workspace Plan v0.1 | repository structure, crate boundaries, implementation workflow |
| **This RFC Draft** | central normative semantic protocol description |

---

## Appendix A. Normative protocol summary

This appendix is a compact restatement of the minimum protocol shape.

### A.1 Session start

1. Client obtains manifest and session token.
2. Client selects endpoint and carrier profile.
3. Client establishes carrier connection.
4. Client opens control stream and sends `CLIENT_HELLO`.
5. Gateway validates session and responds with `SERVER_HELLO` or `ERROR`.
6. Session becomes established.

### A.2 TCP relay

1. Client opens carrier stream.
2. Client sends `STREAM_OPEN`.
3. Gateway sends `STREAM_ACCEPT` or `STREAM_REJECT`.
4. If accepted, stream switches to raw relay bytes.

### A.3 UDP relay

1. Client sends `UDP_FLOW_OPEN`.
2. Gateway replies with `UDP_FLOW_OK` and chosen transport mode.
3. Traffic uses datagrams or a fallback stream.
4. Either side may close the flow.

### A.4 Policy and drain

1. Gateway may send `POLICY_UPDATE`.
2. Gateway may send `GOAWAY` to start drain.
3. Client stops opening new work and migrates when practical.

### A.5 Closure

1. Either side may close session intentionally.
2. Control-stream failure closes the whole session.

---

## Appendix B. Frame catalog overview

The exact encodings are frozen elsewhere; this table exists for readability.

| Type ID | Name | Direction | Purpose |
|---|---|---|---|
| `0x01` | `CLIENT_HELLO` | C → S | session initiation |
| `0x02` | `SERVER_HELLO` | S → C | session acceptance and policy commit |
| `0x03` | `PING` | both | keepalive / liveness |
| `0x04` | `PONG` | both | keepalive response |
| `0x05` | `ERROR` | both | structured failure signaling |
| `0x06` | `GOAWAY` | S → C | graceful drain |
| `0x07` | `POLICY_UPDATE` | S → C | dynamic session policy update |
| `0x08` | `UDP_FLOW_OPEN` | C → S | open logical UDP relay |
| `0x09` | `UDP_FLOW_OK` | S → C | confirm UDP relay mode |
| `0x0A` | `UDP_FLOW_CLOSE` | both | close logical UDP relay |
| `0x0B` | `SESSION_STATS` | both | optional stats |
| `0x0C` | `PATH_EVENT` | C → S | advisory path-change hint |
| `0x0E` | `SESSION_CLOSE` | both | session-level closure |
| `0x40` | `STREAM_OPEN` | C → S | TCP relay preamble |
| `0x41` | `STREAM_ACCEPT` | S → C | TCP relay accepted |
| `0x42` | `STREAM_REJECT` | S → C | TCP relay rejected |
| `0x43` | `UDP_STREAM_OPEN` | C → S | UDP fallback stream preamble |
| `0x44` | `UDP_STREAM_ACCEPT` | S → C | UDP fallback stream accepted |
| `0x45` | `UDP_STREAM_PACKET` | both | framed UDP packet on fallback stream |
| `0x46` | `UDP_STREAM_CLOSE` | both | close UDP fallback stream |

---

## Appendix C. Capability baseline

The initial capability baseline for v0.1 is:

- `tcp_relay` — required
- `udp_relay_stream_fallback` — required
- `udp_relay_datagram` — optional but strongly recommended where carrier support exists
- `policy_push` — optional
- `path_change_signal` — optional
- `stats_push` — optional
- `gateway_goaway` — optional

---

## Appendix D. Editorial notes for future revision

Future protocol revisions should consider:

- whether `SESSION_CLOSE` should become the primary graceful terminal signal in more flows
- whether extension-frame handling can be relaxed safely after strong conformance coverage exists
- when to split carrier-binding documents from the main protocol RFC
- when full IP tunnel mode becomes mature enough to standardize
- when to publish a cleaner public-facing protocol suite document set

---

## Change log seed

### Draft v0.1

- first RFC-style protocol document for Northstar
- aligns with Blueprint v0, Freeze Candidate v0.1, Bridge Spec v0.1, Threat Model v0.1, Security Test & Interop Plan v0.1, and Rust Workspace Plan v0.1
- establishes semantic source of truth without replacing the frozen binary contract

