
# Blueprint v0 — Adaptive Proxy/VPN Protocol Suite (Verta)

> Canonical public protocol name: `Verta`. Canonical filename: `verta_blueprint_v0.md`.
> Compatibility note: stable technical identifiers and compatibility surfaces may still use legacy lowercase `verta` or env aliases such as `VERTA_*` below.

**Status:** Draft v0  
**Audience:** protocol architects, Rust engineers, client engineers, gateway engineers, control-plane engineers, security reviewers  
**Document type:** technical blueprint and implementation-spec baseline  
**Language style:** normative where required (`MUST`, `SHOULD`, `MAY`), descriptive elsewhere  
**Goal:** define the first buildable protocol blueprint for an adaptive proxy/VPN protocol suite implemented in Rust, integrated with an external control-plane bridge and custom client, without forking the panel.

---

## 1. Why this document exists

The roadmap explains **what to build and in which order**.

This blueprint explains **what the first version actually is**:

- the protocol layers
- the handshake
- the frame model
- the authentication model
- the subscription/manifest contract
- the bridge contract
- the Rust workspace structure
- the gateway and client state machines
- the testing, observability, and rollout baseline

This document is the first “source of truth” for implementation. It is intentionally opinionated. It should eliminate ambiguity before code generation begins.

---

## 2. Executive summary

Verta is defined as a **protocol suite**, not a single wire trick.

It consists of:

1. a **stable session core**
2. one or more **carrier transports**
3. a **profile/persona system** that can be updated remotely
4. a **control-plane bridge** that translates subscription/control data into a custom client manifest
5. a **Rust reference implementation** for client, gateway, and bridge

### 2.1 v0 architecture decision

For v0, the suite is intentionally constrained:

- **Control plane:** external bridge connected to the existing panel/control plane
- **Client:** custom Verta client
- **Gateway/server:** Rust implementation
- **Primary carrier:** HTTP/3 over QUIC with a long-lived control tunnel plus carrier-native relay streams
- **Fallback carrier:** reserved, not implemented in v0
- **Traffic modes in v0:** TCP relay + UDP relay
- **Full IP tunnel mode:** explicitly deferred, but data structures reserve room for it
- **Auth model:** short-lived bridge-issued session token + optional longer-lived refresh credential in manifest/bootstrap flow
- **Adaptation model:** remote manifest + carrier profile update, not hard-coded transport behavior

### 2.2 Design philosophy

The protocol core must remain small and boring.

Agility against network interference must come from:

- multiple carriers
- remotely switchable carrier profiles
- capability negotiation
- strict observability
- controlled rollout
- compatibility discipline

Not from mixing all adaptation logic into one giant opaque handshake.

---

## 3. Scope

### 3.1 In scope for v0

Verta v0 includes:

- custom session protocol
- session handshake
- stream relay semantics
- UDP flow semantics
- auth token verification model
- control stream frames
- datagram fallback design
- Rust crate layout
- manifest JSON schema
- bridge API contract
- control-plane integration strategy via external adapter
- gateway/client state machines
- metrics/logging/tracing baseline
- security baseline
- interoperability and fuzzing baseline

### 3.2 Explicitly out of scope for v0

These are important, but **not in the first implementation**:

- kernel-mode tunnel drivers
- multipath transport
- FEC / erasure coding
- custom congestion control
- full remote-access Layer-3 VPN mode
- split tunnel policy enforcement in kernel
- mesh mode / peer-to-peer mode
- post-quantum hybrid transport handshakes
- covert timing systems
- cover traffic generation
- hardware-backed attestation requirements
- cross-provider global load balancing
- billing engine
- on-device ML profile selection
- in-protocol plugin execution
- compatibility with third-party Xray clients without separate implementation in their cores

These deferred items still appear later in this document so they are not forgotten.

---

## 4. Product context and non-fork integration model

Verta does **not** fork the control plane.

Instead, Verta introduces an external component called the **Bridge**.

### 4.1 Control-plane architecture

```text
Existing Panel / Nodes / Subscription Layer
                |
                | adapter / polling / webhook ingestion
                v
        Verta Bridge Service
                |
        -------------------------
        |                       |
        v                       v
 Verta Manifest API   Verta Session Token API
        |
        v
  Verta Client
        |
        v
  Verta Gateway (Rust)
```

### 4.2 Why this is the correct v0 path

This path keeps responsibilities separated:

- the existing control plane remains the user/account/subscription authority
- the Bridge converts control-plane data into Verta-native manifest and tokens
- the Verta client understands the Verta protocol
- the Verta gateway speaks the data plane

This avoids waiting on external core support and avoids maintaining a panel fork.

### 4.3 Bridge responsibilities

The Bridge MUST:

- ingest account/device/subscription state from the control plane
- produce a Verta manifest for the custom client
- issue short-lived session tokens
- expose server and carrier profiles
- enforce revocation and policy versioning
- provide compatibility metadata to the client
- publish capability/version compatibility information
- support a no-downtime profile switch model

The Bridge MUST NOT:

- terminate or proxy user data traffic
- become a mandatory data-plane hop
- hold long-lived session state for active traffic forwarding
- invent new cryptographic primitives
- contain target-specific per-packet manipulation logic

---

## 5. Principles and invariants

These are protocol-level invariants.

### 5.1 Core invariants

1. The **session core** MUST be transport-agnostic.
2. The **carrier profile** MUST be remotely replaceable without changing the session core.
3. The protocol MUST NOT invent custom cryptography.
4. Every parser MUST have a fuzz target.
5. Every on-wire field MUST have either:
   - immediate use in v0, or
   - an explicit extension rationale.
6. The gateway MUST enforce hard resource limits.
7. The client MUST tolerate profile rotation and endpoint churn.
8. The protocol MUST fail closed on version/auth/policy mismatch.
9. The Bridge MUST be able to revoke access without waiting for a software update.
10. All observability data MUST be privacy-aware and sampling-capable.

### 5.2 Operational invariants

1. A broken profile update MUST be reversible quickly.
2. A carrier profile rollout MUST support staged/canary deployment.
3. The client MUST be able to fetch a manifest delta or full manifest.
4. Gateway upgrades MUST preserve compatibility across at least one stable version window.
5. Old clients MUST receive explicit compatibility signals rather than undefined failures.

### 5.3 Anti-goals

Verta is **not** trying to:

- become a giant kitchen-sink transport
- hide protocol complexity in undocumented magic
- depend on one fragile fingerprint
- encode product policy directly into data-plane frame logic
- depend on permanent client-side secrets that are hard to rotate

---

## 6. Terminology

- **Session Core:** the stable Verta application protocol.
- **Carrier:** the outer transport substrate (v0: HTTP/3 over QUIC).
- **Carrier Profile / Persona:** a remotely-configurable package that defines how the carrier is used.
- **Bridge:** the service that translates control-plane/subscription state into Verta-native clients/gateways.
- **Manifest:** the client-consumable JSON configuration document.
- **Gateway:** the Rust data-plane server speaking Verta.
- **Relay Stream:** a carrier-native reliable byte stream used for one proxied TCP connection.
- **UDP Flow:** a logical UDP association carried over datagrams or fallback streams.
- **Refresh Credential:** longer-lived credential used to obtain short-lived session tokens.
- **Session Token:** short-lived token presented in the Verta handshake.
- **Policy Epoch:** monotonic version of effective access policy.
- **Capability:** protocol-level feature that can be negotiated.
- **Extension:** versioned optional protocol behavior identified by an extension id.

---

## 7. Threat model and trust boundaries

### 7.1 Threats considered in v0

Verta v0 assumes exposure to:

- passive traffic observation
- active network interference
- packet loss, jitter, reordering
- NAT rebinding and path changes
- stolen manifest URLs
- replay attempts using stale tokens
- abusive clients opening too many streams/flows
- malformed packet/frame fuzzing
- gateway resource exhaustion
- control-plane desynchronization
- partial bridge compromise
- software version skew between client and gateway

### 7.2 Threats not fully solved in v0

Verta v0 does **not** claim complete protection against:

- fully compromised client device
- fully compromised gateway host
- nation-state scale endpoint enumeration
- advanced traffic correlation against the entire path
- malicious OS or kernel instrumentation
- trusted client binary extraction
- all side channels introduced by outer carriers

### 7.3 Trust boundaries

```text
[Existing Control Plane]
        |
        | policy + identity data
        v
[Bridge] ---- signs session tokens ----> [Client]
   |                                         |
   | endpoint/profile metadata               | encrypted carrier session
   v                                         v
[Gateway] <------ Verta data plane ------
```

Key trust rules:

- the Client trusts the Bridge signing keys published in the manifest
- the Gateway trusts the Bridge token issuer keys
- the Client does **not** trust unsigned remote profile data
- the Gateway does **not** trust any client-supplied identity field without token validation
- external control-plane data must be normalized before use by the Bridge

---

## 8. Protocol suite overview

### 8.1 Layer model

```text
+-----------------------------------------------------------+
| Verta Control Plane Bridge / Manifest / Token Issuer  |
+-----------------------------------------------------------+
| Verta Session Core                                    |
| - handshake                                               |
| - control stream                                          |
| - stream relay                                            |
| - UDP flow management                                     |
| - errors / policy / keepalive                             |
+-----------------------------------------------------------+
| Carrier Layer                                             |
| - H3/QUIC in v0                                           |
| - raw QUIC later                                          |
| - H2/TLS fallback later                                   |
+-----------------------------------------------------------+
| TLS 1.3 / QUIC crypto provided by battle-tested libraries |
+-----------------------------------------------------------+
```

### 8.2 Capability registry (initial)

Capabilities are negotiated explicitly. Unknown capabilities are ignored unless marked critical by a future extension.

Initial capability ids:

| Capability ID | Name | v0 status |
|---|---|---|
| 1 | `tcp_relay` | required |
| 2 | `udp_relay_datagram` | optional |
| 3 | `udp_relay_stream_fallback` | required |
| 4 | `policy_push` | optional |
| 5 | `resume_hint` | optional, reserved |
| 6 | `path_change_signal` | optional |
| 7 | `ip_tunnel_reserved` | reserved only |
| 8 | `stats_push` | optional |
| 9 | `manifest_delta` | optional |
| 10 | `gateway_goaway` | optional |

v0 client and gateway MUST support:

- `tcp_relay`
- `udp_relay_stream_fallback`

If carrier datagrams are available, they SHOULD support:

- `udp_relay_datagram`

### 8.3 Extension registry policy

Extensions MUST use:

- numeric extension id
- explicit version
- compatibility note
- critical vs non-critical behavior flag
- security note
- test vector

Extensions MUST NOT overload existing frame semantics in undefined ways.

---

## 9. Verta objects and data model

### 9.1 Device

```json
{
  "device_id": "uuid-or-stable-random-id",
  "device_name": "user visible name",
  "platform": "windows",
  "client_version": "0.1.0",
  "capabilities": ["h3", "udp_datagram", "dns_cache"],
  "created_at": "2026-04-01T10:00:00Z"
}
```

### 9.2 Endpoint descriptor

```json
{
  "endpoint_id": "gw-eu-1",
  "host": "gw-eu-1.example.net",
  "port": 443,
  "region": "eu-central",
  "carrier_profiles": ["h3-generic-v1", "h3-generic-v2"],
  "public_token_issuers": ["bridge-key-2026-01"],
  "weight": 100,
  "health": "unknown"
}
```

### 9.3 Carrier profile

```json
{
  "id": "h3-generic-v1",
  "carrier": "h3",
  "priority": 100,
  "properties": {
    "alpn": ["h3"],
    "sni_mode": "manifest",
    "control_template": {
      "method": "CONNECT",
      "path": "/.well-known/ns/control"
    },
    "relay_template": {
      "method": "CONNECT",
      "path": "/.well-known/ns/stream"
    },
    "udp_template": {
      "mode": "h3-datagram"
    },
    "heartbeat_seconds": 20,
    "idle_timeout_seconds": 60,
    "max_0rtt": false,
    "padding_policy": "off"
  }
}
```

### 9.4 Session token claims (logical model)

The exact token encoding is opaque to the wire protocol; however the token MUST logically encode:

- issuer id
- audience (`verta-gateway`)
- subject/user id
- device id or device binding id
- issued-at
- not-before
- expiry
- session policy id
- allowed carrier profiles or policy groups
- concurrency limits
- allowed traffic modes
- gateway scope / region scope if needed
- token id for replay/revocation tracking

### 9.5 Effective policy snapshot

A policy snapshot MAY include:

- `max_concurrent_tcp_streams`
- `max_udp_flows`
- `idle_timeout_ms`
- `session_lifetime_ms`
- `allow_private_targets`
- `allowed_ports`
- `blocked_ports`
- `dns_mode`
- `stats_sampling`
- `rate_limit_profile`
- `carrier_profile_override`

This snapshot is authoritative only for the active session.

---

## 10. Wire protocol overview

### 10.1 Encoding rules

Unless otherwise noted:

- integers use **QUIC-style varint**
- fixed-size binary fields remain fixed-size
- strings are UTF-8 with varint length prefix
- byte arrays are varint-length-prefixed
- booleans are encoded as `0x00` or `0x01`
- unknown non-critical fields MUST be ignored
- unknown critical fields MUST fail the frame or extension negotiation

### 10.2 Control stream

A Verta session begins with exactly one **control stream**.

The control stream:

- is a reliable, ordered, bidirectional byte stream provided by the carrier
- carries framed Verta control messages
- exists for the life of the session
- is used for handshake, keepalive, policy changes, UDP flow registration, and session drain/close
- MUST be opened before any relay stream or UDP flow registration

### 10.3 Relay streams

Each TCP relay connection uses one dedicated **relay stream**.

A relay stream:

- is carrier-native and reliable
- starts with a `STREAM_OPEN` preamble frame
- receives either `STREAM_ACCEPT` or `STREAM_REJECT`
- then transitions to raw byte forwarding
- maps half-close to carrier half-close where possible

### 10.4 UDP flows

A UDP flow is a logical association bound to a target and optional metadata.

A UDP flow is created on the control stream and carried by:

- carrier datagrams if available, else
- a fallback reliable stream mode

### 10.5 Session id

The server chooses a **16-byte random session id** after successful authentication.

The session id is:

- opaque
- unique for active session scope
- included in logs, traces, and telemetry correlation
- not treated as authentication

---

## 11. Frame model

### 11.1 Generic frame envelope

All control-stream frames use this envelope:

```text
Frame =
  Type        (varint)
  Length      (varint)
  Payload     (Length bytes)
```

There is no generic frame checksum at the application layer; integrity is provided by the carrier.

### 11.2 Frame type registry (v0)

| Type ID | Name | Direction | Context |
|---|---|---|---|
| 0x01 | `CLIENT_HELLO` | C -> S | control stream |
| 0x02 | `SERVER_HELLO` | S -> C | control stream |
| 0x03 | `PING` | both | control stream |
| 0x04 | `PONG` | both | control stream |
| 0x05 | `ERROR` | both | control stream or relay preamble |
| 0x06 | `GOAWAY` | S -> C | control stream |
| 0x07 | `POLICY_UPDATE` | S -> C | control stream |
| 0x08 | `UDP_FLOW_OPEN` | C -> S | control stream |
| 0x09 | `UDP_FLOW_OK` | S -> C | control stream |
| 0x0A | `UDP_FLOW_CLOSE` | both | control stream |
| 0x0B | `SESSION_STATS` | both | control stream, optional |
| 0x0C | `PATH_EVENT` | C -> S | control stream, optional |
| 0x0D | `RESUME_TICKET` | S -> C | reserved |
| 0x0E | `SESSION_CLOSE` | both | control stream |
| 0x40 | `STREAM_OPEN` | C -> S | relay stream preamble |
| 0x41 | `STREAM_ACCEPT` | S -> C | relay stream preamble |
| 0x42 | `STREAM_REJECT` | S -> C | relay stream preamble |
| 0x43 | `UDP_STREAM_OPEN` | C -> S | fallback stream preamble |
| 0x44 | `UDP_STREAM_ACCEPT` | S -> C | fallback stream preamble |
| 0x45 | `UDP_STREAM_PACKET` | both | fallback stream framed mode |
| 0x46 | `UDP_STREAM_CLOSE` | both | fallback stream framed mode |

Type ranges:

- `0x00-0x3F`: control frames
- `0x40-0x7F`: preamble and relay/fallback stream frames
- `0x80-0xBF`: reserved for extensions
- `0xC0-0xFF`: experimental/private use

### 11.3 Error code registry

| Code | Name | Meaning |
|---|---|---|
| 0 | `NO_ERROR` | normal closure |
| 1 | `PROTOCOL_VIOLATION` | invalid sequence or malformed message |
| 2 | `UNSUPPORTED_VERSION` | no compatible core version |
| 3 | `AUTH_FAILED` | token invalid |
| 4 | `TOKEN_EXPIRED` | token expired or not yet valid |
| 5 | `POLICY_DENIED` | policy disallows request |
| 6 | `RATE_LIMITED` | too many sessions/streams/flows |
| 7 | `TARGET_DENIED` | target or port not allowed |
| 8 | `FLOW_LIMIT_REACHED` | UDP or stream limit exceeded |
| 9 | `INTERNAL_ERROR` | server-side error |
| 10 | `CARRIER_UNSUPPORTED` | carrier lacks mandatory capability |
| 11 | `PROFILE_MISMATCH` | token/profile/manifest mismatch |
| 12 | `REPLAY_SUSPECTED` | replay or reuse attempt detected |
| 13 | `IDLE_TIMEOUT` | idle timeout reached |
| 14 | `DRAINING` | server draining, reconnect required |
| 15 | `RESOLUTION_FAILED` | DNS or address resolution failed |
| 16 | `CONNECT_FAILED` | upstream connection failure |
| 17 | `NETWORK_UNREACHABLE` | target network unreachable |
| 18 | `FRAME_TOO_LARGE` | payload too large |
| 19 | `UNSUPPORTED_TARGET_TYPE` | bad target type |
| 20 | `UDP_DATAGRAM_UNAVAILABLE` | datagram mode unavailable |

---

## 12. Session handshake

### 12.1 Handshake goals

The handshake MUST:

- negotiate a compatible session-core version
- authenticate the client via token
- advertise and negotiate capabilities
- communicate authoritative policy parameters
- complete with one application-layer round trip
- provide clear failure reasons
- avoid carrier-specific semantics in the session core

### 12.2 Versioning model

Verta core versions are monotonically increasing integers.

v0 uses:

- `core_version = 1`

The client sends:

- `min_version`
- `max_version`

The server selects one version within that range or fails with `UNSUPPORTED_VERSION`.

### 12.3 `CLIENT_HELLO`

`CLIENT_HELLO` payload:

```text
CLIENT_HELLO =
  MinVersion                 (varint)
  MaxVersion                 (varint)
  ClientNonce                (32 bytes)
  RequestedCapabilitiesCount (varint)
  RequestedCapabilities[]    (varint each)
  CarrierKind                (varint)
  CarrierProfileId           (string)
  ManifestId                 (string)
  DeviceBindingId            (string)
  RequestedIdleTimeoutMs     (varint)
  RequestedMaxUdpPayload     (varint)
  Token                      (bytes)
  ClientMetadataCount        (varint)
  ClientMetadata[]           (TLV)
```

#### Field notes

- `ClientNonce`: fresh random 32 bytes
- `CarrierKind`: logical outer carrier enum (`1 = h3`, `2 = raw_quic`, `3 = h2_tls`, etc.)
- `CarrierProfileId`: profile chosen from manifest
- `ManifestId`: manifest version or content-hash identifier
- `DeviceBindingId`: stable opaque device id or installation id
- `Token`: opaque session token issued by Bridge
- `ClientMetadata`: optional TLV bag for platform/version/telemetry preference hints

### 12.4 `SERVER_HELLO`

`SERVER_HELLO` payload:

```text
SERVER_HELLO =
  SelectedVersion                 (varint)
  SessionId                       (16 bytes)
  ServerNonce                     (32 bytes)
  SelectedCapabilitiesCount       (varint)
  SelectedCapabilities[]          (varint each)
  PolicyEpoch                     (varint)
  EffectiveIdleTimeoutMs          (varint)
  SessionLifetimeMs               (varint)
  MaxConcurrentRelayStreams       (varint)
  MaxUdpFlows                     (varint)
  EffectiveMaxUdpPayload          (varint)
  DatagramMode                    (varint)
  StatsMode                       (varint)
  ServerMetadataCount             (varint)
  ServerMetadata[]                (TLV)
```

#### Field notes

- `PolicyEpoch` increments when meaningful access policy changes
- `DatagramMode`:
  - `0 = unavailable`
  - `1 = available and enabled`
  - `2 = disabled by policy`
- `StatsMode`:
  - `0 = off`
  - `1 = sampled client push allowed`
  - `2 = sampled bidirectional`

### 12.5 Handshake success condition

The session becomes **ESTABLISHED** when:

1. the client sends a valid `CLIENT_HELLO`
2. the server validates the token, version, and policy
3. the server returns `SERVER_HELLO`

After `SERVER_HELLO`, the client MAY immediately open relay streams and UDP flows.

### 12.6 Handshake failure condition

On failure, the server SHOULD send an `ERROR` frame with a specific code, then close the control stream and session.

### 12.7 Token validation rules

The server MUST validate, at minimum:

- signature / authenticity
- issuer key id
- audience
- `nbf` / `exp` with bounded skew tolerance
- device binding if required
- token id replay status if enabled
- permitted carrier profile / policy group
- session mode permissions
- server scope or region scope if encoded

### 12.8 Clock skew

Gateway SHOULD allow limited clock skew:

- suggested default: ±120 seconds

This value must be configurable.

### 12.9 Resume behavior

v0 defines the field space for resume but does not require implementation.

If resume is not implemented, `RESUME_TICKET` MUST NOT be sent and clients MUST reconnect with a new token.

---

## 13. Control stream frame definitions

### 13.1 `PING`

```text
PING =
  PingId     (varint)
  Timestamp  (varint, ms since local monotonic epoch or zero)
```

### 13.2 `PONG`

```text
PONG =
  PingId     (varint)
  Timestamp  (varint)
```

`PING`/`PONG` are for liveness and RTT estimation only, not time synchronization.

### 13.3 `ERROR`

```text
ERROR =
  ErrorCode        (varint)
  ErrorMessage     (string)
  IsTerminal       (bool)
  DetailsCount     (varint)
  Details[]        (TLV)
```

The message is diagnostic, not stable API. Clients MUST key logic on `ErrorCode`, not text.

### 13.4 `GOAWAY`

```text
GOAWAY =
  ReasonCode             (varint)
  RetryAfterMs           (varint)
  PreferredEndpointCount (varint)
  PreferredEndpoints[]   (string)
  Message                (string)
```

When `GOAWAY` is received:

- new relay streams MUST NOT be opened
- existing streams MAY continue until closure or timeout
- client SHOULD reconnect to preferred endpoint when possible

### 13.5 `POLICY_UPDATE`

```text
POLICY_UPDATE =
  PolicyEpoch                  (varint)
  EffectiveIdleTimeoutMs       (varint)
  MaxConcurrentRelayStreams    (varint)
  MaxUdpFlows                  (varint)
  EffectiveMaxUdpPayload       (varint)
  Flags                        (varint bitset)
  MetadataCount                (varint)
  Metadata[]                   (TLV)
```

Use cases:

- limit reduction
- stats mode change
- drainer signal
- feature disable
- datagram disable

Clients MUST treat `POLICY_UPDATE` as authoritative for the session.

### 13.6 `SESSION_STATS`

Optional telemetry frame.

```text
SESSION_STATS =
  StatsKind        (varint)
  SampleStartMs    (varint)
  SampleEndMs      (varint)
  MetricCount      (varint)
  Metrics[]        (TLV)
```

v0 recommendation: keep disabled by default unless explicitly needed for performance labs.

### 13.7 `PATH_EVENT`

Client-originated optional signal.

```text
PATH_EVENT =
  EventType        (varint)
  PreviousNetwork  (string)
  NewNetwork       (string)
  ClientHintCount  (varint)
  ClientHints[]    (TLV)
```

Examples:

- Wi-Fi -> mobile
- NAT rebinding suspected
- local network changed
- MTU suspicion change

Gateways MAY ignore this frame.

### 13.8 `SESSION_CLOSE`

```text
SESSION_CLOSE =
  ErrorCode      (varint)
  Message        (string)
```

Either side MAY send `SESSION_CLOSE` before closing the control stream.

---

## 14. Relay stream model (TCP mode)

### 14.1 Relay stream lifecycle

For every outbound TCP connection request:

1. client opens a new carrier-native reliable stream
2. client sends `STREAM_OPEN`
3. server validates target/policy and attempts upstream connect
4. server replies with `STREAM_ACCEPT` or `STREAM_REJECT`
5. on accept, both sides switch to raw byte forwarding mode
6. stream closes when either side closes and all buffered bytes are flushed or aborted

### 14.2 `STREAM_OPEN`

```text
STREAM_OPEN =
  RelayId            (varint)
  TargetType         (varint)
  TargetHost         (bytes or string depending on TargetType)
  TargetPort         (varint)
  OpenFlags          (varint bitset)
  MetadataCount      (varint)
  Metadata[]         (TLV)
```

`TargetType`:

- `1 = domain`
- `2 = ipv4`
- `3 = ipv6`

#### `OpenFlags` reserved bits

- bit 0: `prefer_ipv6`
- bit 1: `low_latency`
- bit 2: `allow_rebind` (reserved)
- bit 3: `metadata_present` (informational)
- remaining bits reserved

### 14.3 `STREAM_ACCEPT`

```text
STREAM_ACCEPT =
  RelayId              (varint)
  BindAddressType      (varint)
  BindAddress          (bytes/string)
  BindPort             (varint)
  MetadataCount        (varint)
  Metadata[]           (TLV)
```

`BindAddress` is optional from a privacy perspective. It MAY be blank/omitted in low-verbosity mode.

### 14.4 `STREAM_REJECT`

```text
STREAM_REJECT =
  RelayId          (varint)
  ErrorCode        (varint)
  Retryable        (bool)
  Message          (string)
  MetadataCount    (varint)
  Metadata[]       (TLV)
```

After `STREAM_REJECT`, the relay stream MUST be closed.

### 14.5 Relay stream data mode

After `STREAM_ACCEPT`, the stream contains only raw bytes.

No per-chunk framing is used in raw data mode.

This is intentional:

- minimum overhead
- simpler backpressure
- direct mapping to carrier and socket semantics

### 14.6 Half-close behavior

If supported by the carrier and runtime:

- client half-close maps to upstream socket write shutdown
- upstream half-close maps to client stream write shutdown

If precise half-close is not possible, the implementation MAY buffer and full-close, but this SHOULD be documented.

### 14.7 Stream ids

`RelayId` is a logical session-scoped identifier chosen by the client.

Recommendations:

- monotonically increasing varint
- odd/even split not required
- MUST NOT be reused during an active session

`RelayId` exists for control-plane diagnostics and telemetry correlation; it does not replace the carrier stream id.

### 14.8 Target resolution policy

The gateway SHOULD support two resolution modes:

- `gateway_resolve`
- `client_resolve` (future or profile-controlled)

v0 recommendation:

- use `gateway_resolve` for domain targets

This keeps policy enforcement centralized.

---

## 15. UDP flow model

### 15.1 Why UDP is separate

UDP is not modeled as a raw byte stream.

It uses logical **flow registration** followed by per-packet transmission over either:

- carrier datagrams, or
- fallback reliable stream framing

### 15.2 UDP flow registration

Client sends `UDP_FLOW_OPEN` on the control stream.

```text
UDP_FLOW_OPEN =
  FlowId             (varint)
  TargetType         (varint)
  TargetHost         (bytes/string)
  TargetPort         (varint)
  IdleTimeoutMs      (varint)
  FlowFlags          (varint bitset)
  MetadataCount      (varint)
  Metadata[]         (TLV)
```

`FlowFlags` initial reserved bits:

- bit 0: `prefer_datagram`
- bit 1: `allow_stream_fallback`
- bit 2: `dns_optimized` (hint only)
- bit 3: `client_keepalive`

Server answers with `UDP_FLOW_OK` or `ERROR`/policy denial.

### 15.3 `UDP_FLOW_OK`

```text
UDP_FLOW_OK =
  FlowId                   (varint)
  TransportMode            (varint)
  EffectiveIdleTimeoutMs   (varint)
  EffectiveMaxPayload      (varint)
  MetadataCount            (varint)
  Metadata[]               (TLV)
```

`TransportMode`:

- `1 = datagram`
- `2 = stream_fallback`

### 15.4 Datagram payload format

If datagram mode is selected, each UDP payload is carried as:

```text
UDP_DATAGRAM =
  FlowId         (varint)
  Flags          (varint)
  PayloadBytes   (remaining bytes)
```

Suggested flags:

- bit 0: `more_fragments_reserved`
- bit 1: `ecn_present_reserved`
- remaining bits reserved

v0 does **not** define fragmentation at the session layer. Oversized payloads MUST be rejected or truncated by policy before transmission.

### 15.5 UDP stream fallback

If datagram mode is unavailable, client MAY open a fallback reliable stream and send:

#### `UDP_STREAM_OPEN`

```text
UDP_STREAM_OPEN =
  FlowId          (varint)
  MetadataCount   (varint)
  Metadata[]      (TLV)
```

Server replies:

#### `UDP_STREAM_ACCEPT`

```text
UDP_STREAM_ACCEPT =
  FlowId          (varint)
  MetadataCount   (varint)
  Metadata[]      (TLV)
```

Then packets are framed as:

#### `UDP_STREAM_PACKET`

```text
UDP_STREAM_PACKET =
  PacketLength    (varint)
  Payload         (PacketLength bytes)
```

Close with `UDP_STREAM_CLOSE`.

This mode is less efficient and higher latency, but mandatory as a compatibility mechanism.

### 15.6 Flow closure

Either side may close a flow using `UDP_FLOW_CLOSE`.

```text
UDP_FLOW_CLOSE =
  FlowId         (varint)
  ErrorCode      (varint)
  Message        (string)
```

---

## 16. TLV registry for metadata bags

Metadata bags exist so the core protocol can stay stable while implementations evolve.

### 16.1 TLV format

```text
TLV =
  Type      (varint)
  Length    (varint)
  Value     (Length bytes)
```

### 16.2 Initial TLV ids

| TLV ID | Name | Context |
|---|---|---|
| 1 | `client_platform` | `CLIENT_HELLO` |
| 2 | `client_version` | `CLIENT_HELLO` |
| 3 | `install_channel` | `CLIENT_HELLO` |
| 4 | `gateway_region` | `SERVER_HELLO` |
| 5 | `gateway_build` | `SERVER_HELLO` |
| 6 | `policy_name` | `SERVER_HELLO` / `POLICY_UPDATE` |
| 7 | `dns_mode` | `POLICY_UPDATE` / flow open |
| 8 | `rtt_hint_ms` | stats or path event |
| 9 | `mtu_hint` | path event |
| 10 | `target_tag` | relay/flow open |
| 11 | `trace_sampling` | server hello |
| 12 | `reason_detail_code` | error or reject |
| 13 | `bridge_manifest_hash` | hello |
| 14 | `profile_generation` | hello |
| 15 | `observability_profile` | hello/update |

Unknown TLVs MUST be ignored unless a future extension defines them as critical.

---

## 17. Carrier abstraction

### 17.1 Carrier requirements

A carrier usable by Verta MUST provide:

- one reliable bidirectional stream for the control channel
- multiple reliable bidirectional streams for relay streams
- optional datagram support
- end-to-end confidentiality/integrity
- explicit capability detection at session establishment time

### 17.2 Carrier kinds

Reserved carrier ids:

| Carrier ID | Name | v0 status |
|---|---|---|
| 1 | `h3` | primary |
| 2 | `raw_quic` | reserved |
| 3 | `h2_tls` | reserved |
| 4 | `ws_tls` | reserved, not preferred |
| 5 | `tcp_tls_custom` | reserved, avoid unless necessary |

Verta v0 implements only `h3`.

---

## 18. H3 carrier specification (v0 primary carrier)

### 18.1 Purpose

The H3 carrier is the outer transport for v0. It provides:

- QUIC transport
- TLS 1.3 security
- reliable request streams
- optional H3 datagrams
- deployment familiarity

### 18.2 H3 carrier assumptions

The v0 H3 carrier assumes:

- QUIC v1
- TLS 1.3
- ALPN includes `h3`
- the client and gateway support long-lived H3 streams/tunnels
- H3 datagrams may or may not be present

### 18.3 H3 carrier profile fields

A carrier profile for H3 SHOULD define:

- origin host and port
- SNI mode
- ALPN list
- control route template
- relay route template
- datagram enable flag
- heartbeat interval
- idle timeout
- 0-RTT policy
- header map template if needed
- max concurrent control attempts
- retry/backoff profile

### 18.4 H3 control tunnel

The control channel is opened as a dedicated long-lived H3 request/tunnel defined by the profile.

The core protocol does **not** hard-code one path shape. Instead, the profile defines it.

Example profile:

```json
{
  "control_template": {
    "method": "CONNECT",
    "path": "/.well-known/ns/control"
  }
}
```

Once the request is accepted, the request body tunnel becomes the Verta control stream.

### 18.5 H3 relay stream mapping

Each TCP relay uses a dedicated H3 tunnel/request according to the profile.

The relay request itself is carrier-specific. The first bytes in the tunnel are always the Verta `STREAM_OPEN` preamble.

### 18.6 H3 datagram mapping

If H3 datagrams are supported and enabled:

- UDP payloads use `UDP_DATAGRAM` format
- association with the active session is profile/carrier defined
- the gateway MUST reject datagram use if not negotiated in `SERVER_HELLO`

### 18.7 Carrier binding and telemetry

The client SHOULD collect per-carrier measurements:

- handshake duration
- connection RTT estimate
- number of path changes
- datagram success ratio
- stream open latency
- reconnect count

This data SHOULD be sampled and privacy-bounded.

### 18.8 0-RTT

v0 recommendation:

- disable 0-RTT by default

Reason:

- simpler replay model
- less operational surprise
- easier correctness in early versions

### 18.9 H3 carrier failure handling

If the H3 carrier fails:

- client SHOULD attempt endpoint/profile failover
- client MUST obey backoff and retry ceilings from the manifest
- repeated profile failures SHOULD mark that profile degraded locally for a bounded TTL

---

## 19. Session manifest and subscription contract

### 19.1 Manifest purpose

The manifest is the client’s control document. It is delivered via the Bridge and derived from control-plane state.

The manifest MUST contain enough information for the client to:

- know which protocol suite version it should speak
- know how to obtain a session token
- know which gateways/endpoints are valid
- know which carrier profiles it may use
- know retry/rollout/update constraints
- trust the Bridge signing keys

### 19.2 Manifest top-level schema

```json
{
  "schema_version": 1,
  "manifest_id": "sha256:...",
  "generated_at": "2026-04-01T10:00:00Z",
  "expires_at": "2026-04-01T16:00:00Z",
  "user": {
    "account_id": "acct_123",
    "plan_id": "plan_pro",
    "display_name": "optional"
  },
  "device_policy": {
    "max_devices": 5,
    "require_device_binding": true
  },
  "client_constraints": {
    "min_client_version": "0.1.0",
    "recommended_client_version": "0.1.2",
    "allowed_core_versions": [1]
  },
  "token_service": {
    "url": "https://bridge.example.net/v0/token/exchange",
    "issuer": "bridge-main",
    "jwks_url": "https://bridge.example.net/.well-known/jwks.json",
    "session_token_ttl_seconds": 300
  },
  "refresh": {
    "mode": "opaque_secret",
    "credential": "redacted-or-bootstrap-only",
    "rotation_hint_seconds": 86400
  },
  "carrier_profiles": [],
  "endpoints": [],
  "routing": {
    "selection_mode": "latency_weighted",
    "failover_mode": "same_region_then_global"
  },
  "retry_policy": {
    "connect_attempts": 3,
    "initial_backoff_ms": 500,
    "max_backoff_ms": 10000
  },
  "telemetry": {
    "allow_client_reports": true,
    "sample_rate": 0.05
  },
  "signature": {
    "alg": "EdDSA",
    "key_id": "bridge-manifest-2026-01",
    "value": "..."
  }
}
```

### 19.3 Manifest signatures

The manifest MUST be signed.

The client MUST verify the manifest signature against a trusted Bridge key before using:

- endpoints
- carrier profiles
- token-service metadata
- compatibility constraints

Unsigned or unverifiable manifests MUST be rejected.

### 19.4 Manifest update model

The client SHOULD support:

- full manifest fetch
- conditional fetch with `ETag` / `If-None-Match`
- future manifest delta mode

The client MUST cache the last known-good manifest until it expires or is superseded.

### 19.5 Bootstrap vs steady-state manifest fetch

Two modes are recommended:

1. **Bootstrap mode**
   - used when the client imports a new subscription URL
   - may carry a longer-lived bootstrap secret
2. **Steady-state mode**
   - uses refresh credential / device binding
   - keeps session tokens short-lived

### 19.6 Compatibility flags

The manifest SHOULD communicate:

- required core versions
- known-bad carrier profiles for certain client versions
- feature flags
- forced migration windows
- deprecation deadlines

---

## 20. Bridge API contract

### 20.1 Purpose

The Bridge is the contract boundary between the external control plane and Verta-native clients/gateways.

### 20.2 Required endpoints

Suggested Bridge API surface:

#### `POST /v0/device/register`
Purpose:
- first-time device registration
- optional device binding creation

#### `GET /v0/manifest`
Purpose:
- fetch signed manifest

#### `POST /v0/token/exchange`
Purpose:
- exchange refresh/bootstrap credential + device identity for a short-lived session token

#### `POST /v0/network/report`
Purpose:
- optional sampled client-side network feedback

#### `GET /.well-known/jwks.json`
Purpose:
- publish verification keys for token and/or manifest signatures

### 20.3 Example token exchange request

```json
{
  "manifest_id": "sha256:abc...",
  "device_id": "dev_123",
  "client_version": "0.1.0",
  "core_version": 1,
  "carrier_profile_id": "h3-generic-v1",
  "requested_capabilities": [1, 2, 3],
  "refresh_credential": "opaque-secret-or-proof"
}
```

### 20.4 Example token exchange response

```json
{
  "session_token": "opaque-or-jwt-token",
  "expires_at": "2026-04-01T10:05:00Z",
  "policy_epoch": 42,
  "recommended_endpoints": ["gw-eu-1", "gw-eu-2"],
  "profile_overrides": [],
  "warnings": []
}
```

### 20.5 Device registration notes

The Bridge SHOULD support device registration metadata:

- device name
- platform
- client version
- install channel
- capabilities
- optional local key material (future)

### 20.6 Control-plane ingestion strategies

The Bridge MAY integrate with the control plane using:

- webhook ingestion
- periodic polling
- signed export feed
- direct API adapter

The choice is operational, not protocol-defining.

### 20.7 Bridge security rules

The Bridge MUST:

- sign tokens with rotating keys
- publish current verification keys
- support key overlap during rotation
- audit token issuance
- rate-limit token exchange
- normalize external account data
- isolate admin/control APIs from public client APIs

---

## 21. Authentication and identity model

### 21.1 Why short-lived session tokens

Verta uses short-lived session tokens so that:

- revocation can be fast
- stolen tokens age out quickly
- profile changes can take effect quickly
- compatibility can be enforced without client reinstall

### 21.2 Suggested token encoding

The wire protocol treats the token as opaque bytes.

Implementation recommendation for v0:

- signed token using a standard scheme such as Ed25519-backed JWT/JWS or PASETO public token
- key id included
- short expiry (for example 5 minutes)

The exact library choice is an implementation detail, but it MUST be standards-based.

### 21.3 Refresh credential

The refresh/bootstrap credential SHOULD have narrower scope than a session token. It SHOULD:

- only be valid against the Bridge
- never be accepted by gateways
- support rotation
- be invalidatable independent of sessions

### 21.4 Device binding

Device binding SHOULD be supported in v0 as a policy option.

Baseline approach:

- Bridge issues refresh credential bound to device id
- token exchange requires device id
- gateway verifies token device binding id

Stronger binding (device keypair, attestation) is deferred.

### 21.5 Revocation model

Bridge SHOULD support:

- account revocation
- device revocation
- refresh credential revocation
- signer key rotation
- policy epoch increments

Gateways SHOULD cache revocation metadata for a short period if online verification is not used.

### 21.6 Replay handling

Session token replay handling options:

1. **Soft detection**
   - detect suspicious parallel reuse by token id and device binding
   - log and optionally rate-limit
2. **Hard single-use**
   - stronger, but more stateful and operationally expensive

v0 recommendation:

- start with soft detection and short TTL

---

## 22. Gateway behavior

### 22.1 High-level gateway responsibilities

The gateway MUST:

- terminate the carrier
- parse Verta control frames
- verify session tokens
- enforce policy
- open upstream TCP/UDP sockets
- manage resource limits
- emit observability data
- support session drain and graceful shutdown
- reject malformed or abusive inputs early

### 22.2 Gateway pipeline

```text
accept carrier connection
    -> open control tunnel
    -> parse CLIENT_HELLO
    -> verify token
    -> establish session context
    -> allow relay streams / UDP flows
    -> track quotas and limits
    -> close gracefully or on policy/timeout/error
```

### 22.3 Session context object

Suggested internal session context:

```rust
struct SessionContext {
    session_id: [u8; 16],
    core_version: u64,
    account_id: String,
    device_id: String,
    policy_epoch: u64,
    capabilities: CapSet,
    limits: SessionLimits,
    profile_id: String,
    started_at: Instant,
}
```

### 22.4 Resource limits

Gateway MUST enforce configurable limits at minimum for:

- total sessions
- sessions per account
- sessions per device
- relay streams per session
- UDP flows per session
- max frame size
- max metadata items
- per-stream write buffer
- global upstream socket count
- DNS resolution concurrency

### 22.5 DNS and target control

Gateway SHOULD centralize target resolution and policy checks.

Suggested policy checks before upstream connect:

- account active?
- token expired?
- target type allowed?
- private IP targets allowed?
- blocked/allowed ports?
- max concurrent streams exceeded?
- region restriction?
- profile restriction?

### 22.6 Graceful drain

When draining:

- gateway sends `GOAWAY`
- new streams are rejected with `DRAINING`
- active streams continue until completion or cap timeout
- session is closed after grace period

### 22.7 Logging model

Gateway logs SHOULD be structured and include:

- session id
- account/device ids (hashed or redacted as policy requires)
- endpoint id
- profile id
- error codes
- stream/flow counts
- latency buckets
- bytes in/out
- close reason

Sensitive targets/domains SHOULD be redacted or sampled according to privacy policy.

---

## 23. Client behavior

### 23.1 High-level responsibilities

The client MUST:

- import bootstrap/subscription URL
- fetch and verify manifest
- register device if necessary
- exchange refresh credential for short-lived token
- select endpoint and carrier profile
- establish carrier and Verta session
- open relay streams for local proxy requests
- manage UDP flow lifecycles
- recover from endpoint/profile failures
- keep last known-good manifest
- expose diagnostic logs

### 23.2 Local interfaces

v0 client SHOULD support:

- local SOCKS5 inbound
- local HTTP proxy inbound
- optional TUN/TAP mode deferred to later phase

This allows practical desktop integration without kernel-mode requirements on day one.

### 23.3 Endpoint selection algorithm (baseline)

Recommendation:

1. filter endpoints by manifest policy/profile compatibility
2. prefer same-region recommendation from Bridge if present
3. optionally use cached RTT/availability scores
4. fall back by weight and health TTL
5. avoid retrying a just-failed profile/endpoint combination for a bounded window

### 23.4 Failure memory

The client SHOULD keep bounded local memory of:

- failed endpoint/profile combos
- average handshake duration
- last manifest generation
- last successful endpoint per network fingerprint

This supports faster reconnect after local network changes.

### 23.5 Network change handling

On local network change:

- client MAY send `PATH_EVENT` on active session
- client SHOULD refresh endpoint ranking
- client SHOULD reconnect if session quality degrades beyond thresholds
- client MUST avoid reconnect loops

### 23.6 Diagnostics

The client SHOULD expose:

- current endpoint
- carrier profile id
- session id
- core version
- RTT estimate
- stream count
- UDP flow count
- last error code
- manifest version
- client and gateway build versions where available

This is essential for support and debugging.

---

## 24. State machines

### 24.1 Session state machine

```text
IDLE
  -> MANIFEST_READY
  -> TOKEN_READY
  -> CARRIER_CONNECTING
  -> CONTROL_OPEN
  -> HELLO_SENT
  -> ESTABLISHED
  -> DRAINING
  -> CLOSED
```

### 24.2 Client session state details

| State | Meaning |
|---|---|
| `IDLE` | no active bootstrap or session |
| `MANIFEST_READY` | signed manifest available and valid |
| `TOKEN_READY` | fresh session token available |
| `CARRIER_CONNECTING` | outer carrier connecting |
| `CONTROL_OPEN` | control tunnel established, handshake pending |
| `HELLO_SENT` | `CLIENT_HELLO` sent, awaiting `SERVER_HELLO` |
| `ESTABLISHED` | data plane active |
| `DRAINING` | `GOAWAY` or local graceful shutdown |
| `CLOSED` | session terminated |

### 24.3 Relay stream state machine

```text
INIT
  -> OPEN_SENT
  -> ACCEPTED
  -> DATA
  -> HALF_CLOSED_LOCAL
  -> HALF_CLOSED_REMOTE
  -> CLOSED
```

### 24.4 UDP flow state machine

```text
UNBOUND
  -> OPEN_SENT
  -> DATAGRAM_ACTIVE | STREAM_FALLBACK_ACTIVE
  -> CLOSING
  -> CLOSED
```

### 24.5 Invalid transitions

Examples that MUST fail fast:

- relay stream before session established
- `SERVER_HELLO` before `CLIENT_HELLO`
- duplicate `STREAM_ACCEPT`
- duplicate `UDP_FLOW_OK` for same active flow
- datagram for unknown flow id
- policy update lowering limits without enforcement path

---

## 25. Rust workspace blueprint

### 25.1 Workspace layout

```text
verta/
  Cargo.toml
  rust-toolchain.toml
  crates/
    ns-core/
    ns-wire/
    ns-auth/
    ns-manifest/
    ns-bridge-api/
    ns-carrier-h3/
    ns-client-runtime/
    ns-gateway-runtime/
    ns-policy/
    ns-observability/
    ns-testkit/
    ns-fuzz/
  apps/
    ns-client/
    ns-gateway/
    ns-bridge/
  docs/
  fixtures/
  fuzz/
  integration-tests/
```

### 25.2 Crate responsibilities

#### `ns-core`
- protocol types
- state machine enums
- version/capability registries
- target/flow/relay structures
- error codes

#### `ns-wire`
- frame encoders/decoders
- varint utilities
- TLV parsing
- golden vectors
- strict parse limits

#### `ns-auth`
- token verification interface
- key rotation helpers
- issuer/jwks cache
- device binding logic

#### `ns-manifest`
- manifest schema structs
- signature verification
- endpoint/profile selection helpers
- compatibility checks

#### `ns-bridge-api`
- HTTP models for register/manifest/token exchange
- response validation
- retryable error mapping

#### `ns-carrier-h3`
- H3 connection orchestration
- control tunnel open/close
- relay stream open/close
- datagram send/receive
- carrier metrics

#### `ns-client-runtime`
- local inbound listeners (SOCKS/HTTP)
- session manager
- token refresh
- endpoint/profile failover
- network change reactions

#### `ns-gateway-runtime`
- session accept loop
- token validation
- policy engine integration
- upstream dialers
- flow/stream quotas
- graceful drain

#### `ns-policy`
- effective session policy
- target allow/deny logic
- update translation from bridge token claims

#### `ns-observability`
- tracing spans
- metrics
- structured log fields
- redaction helpers

#### `ns-testkit`
- fake bridge
- fake gateway
- deterministic time helpers
- property tests and fault injection

#### `ns-fuzz`
- corpus management
- libFuzzer targets
- parser harnesses

### 25.3 Apps

#### `ns-client`
Desktop CLI/daemon that:
- loads manifest
- exposes local proxy ports
- maintains active session

#### `ns-gateway`
Server binary that:
- terminates carrier
- validates tokens
- forwards traffic

#### `ns-bridge`
Control-plane adapter/service that:
- serves manifest
- issues tokens
- ingests external control data

### 25.4 Runtime stack recommendation

For v0:

- `tokio` for async runtime
- `rustls` for TLS
- `quinn` for QUIC
- `h3` for HTTP/3 integration where practical
- `tracing` + `tracing-subscriber`
- `serde` / `serde_json`
- `thiserror` / `anyhow` at boundaries only
- `bytes`
- `governor` or equivalent for rate limiting if needed
- property/fuzz libraries as appropriate

### 25.5 Coding rules

- no panics on untrusted input
- bounded allocations on frame parse
- explicit timeouts for every I/O phase
- structured errors at crate boundaries
- avoid `unsafe` unless profiled and justified
- protocol enums must preserve unknown values when useful
- every frame parser has max-size limits

---

## 26. Suggested Rust interfaces

### 26.1 Wire codec interface

```rust
pub trait FrameCodec {
    fn encode(&self, frame: &ControlFrame, out: &mut bytes::BytesMut) -> Result<(), EncodeError>;
    fn decode(&self, src: &mut bytes::BytesMut) -> Result<Option<ControlFrame>, DecodeError>;
}
```

### 26.2 Auth verifier interface

```rust
pub trait TokenVerifier {
    type Claims;

    fn verify_session_token(&self, token: &[u8]) -> Result<Self::Claims, AuthError>;
}
```

### 26.3 Carrier interface

```rust
#[async_trait::async_trait]
pub trait CarrierSession {
    type BidiStream;
    type Datagram;

    async fn open_control_stream(&mut self) -> Result<Self::BidiStream, CarrierError>;
    async fn open_relay_stream(&mut self) -> Result<Self::BidiStream, CarrierError>;
    async fn send_datagram(&mut self, payload: bytes::Bytes) -> Result<(), CarrierError>;
    async fn recv_datagram(&mut self) -> Result<Option<Self::Datagram>, CarrierError>;
    fn supports_datagrams(&self) -> bool;
}
```

### 26.4 Policy interface

```rust
pub trait PolicyEngine {
    fn authorize_session(&self, claims: &VerifiedClaims, hello: &ClientHello) -> Result<SessionPolicy, PolicyError>;
    fn authorize_target(&self, session: &SessionPolicy, target: &TargetAddr, mode: TrafficMode) -> Result<(), PolicyError>;
}
```

### 26.5 Manifest selector interface

```rust
pub trait EndpointSelector {
    fn choose_endpoint(
        &self,
        manifest: &Manifest,
        network_hint: Option<&NetworkHint>,
        history: &SelectionHistory,
    ) -> Result<SelectedRoute, SelectionError>;
}
```

These APIs are examples, not frozen interfaces.

---

## 27. Observability blueprint

### 27.1 Why observability is part of v0

If the protocol is supposed to be adaptive, it must be measurable from day one.

Without observability, adaptation becomes guesswork.

### 27.2 Metrics

Gateway metrics SHOULD include:

- `sessions_opened_total`
- `sessions_rejected_total`
- `session_duration_seconds`
- `relay_streams_opened_total`
- `relay_stream_open_latency_ms`
- `udp_flows_opened_total`
- `udp_datagrams_in_total`
- `udp_datagrams_out_total`
- `udp_datagram_drop_total`
- `hello_failures_total{code=...}`
- `token_verify_failures_total`
- `policy_denials_total`
- `target_resolution_failures_total`
- `upstream_connect_failures_total`
- `bytes_in_total`
- `bytes_out_total`
- `goaway_sent_total`
- `active_sessions`
- `active_streams`
- `active_udp_flows`

Client metrics SHOULD include:

- `manifest_fetch_total`
- `manifest_verify_failures_total`
- `token_exchange_total`
- `carrier_connect_failures_total`
- `session_establish_latency_ms`
- `reconnect_total`
- `endpoint_switch_total`
- `profile_switch_total`
- `local_proxy_accept_total`
- `network_change_events_total`

### 27.3 Tracing

All main operations SHOULD be span-based:

- manifest fetch
- token exchange
- carrier connect
- session hello
- relay stream open
- UDP flow open
- upstream connect
- session drain
- graceful shutdown

Recommended trace keys:

- `session_id`
- `endpoint_id`
- `profile_id`
- `policy_epoch`
- `client_version`
- `gateway_build`
- `carrier_kind`

### 27.4 Logs

Logs MUST be structured. Free-form logs are allowed only for local development.

Recommended levels:

- `ERROR` for terminal session failure
- `WARN` for policy denial, profile mismatch, retryable transport failure
- `INFO` for lifecycle events
- `DEBUG` for developer diagnostics
- `TRACE` for parser and frame details in test/dev only

### 27.5 qlog / QUIC event capture

The H3 carrier SHOULD support optional qlog output during development and performance testing.

qlog SHOULD be:

- disabled by default in production
- enableable per endpoint or per test run
- rotated and sampled
- scrubbed for sensitive fields before external sharing

### 27.6 Privacy rules

Observability MUST obey:

- minimal target exposure
- token redaction
- secret redaction
- bounded retention
- user-visible diagnostic export that is scrubbed by default

---

## 28. Security requirements

### 28.1 General rules

- no custom cryptographic primitives
- no plaintext token or secret logging
- no unbounded parser recursion
- no unbounded metadata maps
- no compression of secret-bearing control messages by default
- no accepting a manifest without signature verification
- no accepting a session token without issuer validation

### 28.2 Parser safety

Each parser MUST define hard limits:

- max control frame size
- max metadata count
- max string length
- max number of capabilities
- max number of details TLVs
- max UDP payload size
- max concurrent stream opens pending

Malformed inputs MUST fail fast with a bounded CPU and memory cost.

### 28.3 Backpressure and memory discipline

The runtime MUST:

- avoid unbounded channel growth
- apply per-stream and per-session write budgets
- drop or reject over-limit UDP payloads early
- cap buffering during slow-client and slow-upstream conditions

### 28.4 Amplification and abuse control

The gateway MUST avoid becoming an amplification vector.

Minimum guards:

- authenticate before allowing meaningful upstream actions
- bound unauthenticated response size
- cap datagram payload sizes
- rate-limit token failures and repeated stream rejections

### 28.5 Secret handling

The client SHOULD store long-lived credentials using platform-provided secure storage where possible.

On platforms without secure storage:

- secrets MUST at least be encrypted at rest using a local key derivation strategy
- plaintext credential files MUST be avoided if possible

### 28.6 Build and release security

The project SHOULD adopt:

- signed releases
- SBOM generation
- dependency auditing
- reproducible build targets where practical
- security disclosure policy
- CI gating for fuzz and parser regression

---

## 29. Testing strategy

### 29.1 Required test layers

Verta v0 MUST include:

1. unit tests
2. property tests
3. fuzz tests
4. integration tests
5. soak tests
6. performance tests
7. compatibility tests
8. fault-injection tests

### 29.2 Unit tests

Unit tests cover:

- varint codec
- frame codec
- TLV codec
- hello validation
- stream open validation
- policy decisions
- token claim mapping
- endpoint selection logic

### 29.3 Property tests

Property tests SHOULD validate:

- encode/decode round-trip invariants
- parser rejection behavior on malformed length fields
- state machine transition safety
- selection stability under bounded input variance

### 29.4 Fuzzing

Required fuzz targets:

- control frame decoder
- hello parser
- relay preamble parser
- UDP fallback packet parser
- manifest parser
- token wrapper parser if custom envelope exists
- bridge API response deserializer

The initial corpus SHOULD include:

- minimal valid frames
- maximal valid frames
- nested metadata edge cases
- truncated inputs
- oversized lengths
- unknown frame ids
- duplicate frame sequences
- invalid UTF-8 strings

### 29.5 Integration tests

Integration tests SHOULD cover:

- manifest fetch + verify + token exchange
- client/gateway session establishment
- TCP relay basic flow
- UDP datagram flow
- UDP stream fallback flow
- idle timeout behavior
- GOAWAY drain
- token expiry between attempts
- policy update mid-session
- endpoint failover
- profile failover

### 29.6 Network fault injection

Simulate:

- packet loss
- latency spikes
- reordering
- temporary black holes
- NAT rebinding
- endpoint reset during active streams
- H3 datagram loss with fallback still available

### 29.7 Soak tests

Soak tests SHOULD include:

- long-lived idle session
- many short TCP streams
- mixed TCP/UDP profile
- repeated reconnect under token rotation
- drain and rolling restart scenarios

### 29.8 Compatibility corpus

Every released version SHOULD produce:

- golden frame encodings
- manifest fixtures
- token claim fixtures
- state transition fixture traces

These become the compatibility corpus for future versions.

---

## 30. Performance laboratory plan embedded into v0

### 30.1 Why performance lab belongs in the blueprint

If the protocol is supposed to become “faster and more stable,” performance measurement must be designed before implementation, not after.

### 30.2 Benchmarks to define immediately

Measure at minimum:

- session establishment latency
- TCP relay first-byte latency
- steady-state TCP throughput
- UDP one-way and round-trip latency
- stream open latency under concurrency
- reconnect latency after path change
- CPU cost per active stream
- memory cost per session / per stream / per UDP flow

### 30.3 Test matrix

Run benchmarks under:

- clean LAN
- modest WAN latency
- high-latency mobile-like network
- packet loss 1–5%
- reordering
- small MTU
- unstable path / NAT rebinding
- datagram available vs unavailable

### 30.4 Success reporting

Each benchmark run SHOULD record:

- git commit
- compiler version
- build profile
- carrier profile id
- endpoint region
- concurrency settings
- host CPU and memory
- result percentiles, not just averages

### 30.5 Regression gate

The CI/CD system SHOULD maintain performance budgets for:

- hello latency
- stream open latency
- CPU per stream
- memory per active session

Significant regressions SHOULD block release candidates.

---

## 31. Rollout and compatibility

### 31.1 Rollout model

Verta v0 SHOULD support:

- developer local mode
- staging
- canary
- partial production
- full production

### 31.2 Feature flags

Feature flags SHOULD exist for:

- datagram mode enablement
- policy push enablement
- stats push enablement
- path event enablement
- strict replay detection mode
- manifest delta mode
- profile overrides from token exchange

### 31.3 Compatibility windows

The project SHOULD define:

- minimum supported client version
- minimum supported manifest schema version
- gateway compatibility window
- profile deprecation timeline

### 31.4 Downgrade strategy

If a client is too old:

- manifest fetch may still succeed
- compatibility section MUST clearly state unsupported status
- client SHOULD surface actionable upgrade message
- gateway SHOULD reject with explicit error if connection still attempted

### 31.5 Key rotation playbook

Bridge and gateway MUST support overlapping verification keys.

Suggested key rotation steps:

1. publish new verification key
2. start issuing new tokens with new `kid`
3. maintain old key for overlap window
4. remove old key only after overlap and manifest refresh safety window pass

---

## 32. Windows-first implementation notes

Because the first production user environment is expected to include Windows, the project SHOULD treat Windows as a first-class client platform.

### 32.1 Client service model

For Windows, the client SHOULD support:

- foreground CLI mode for development
- background service mode for steady-state use
- local SOCKS/HTTP proxy ports
- rotating diagnostic log files
- secure storage integration where possible

### 32.2 Deferred Windows-specific backlog

Deferred but expected:

- Wintun-based TUN mode
- auto-start service management
- system proxy integration
- tray UI
- crash dump symbol pipeline
- network-change hooks tuned for Windows networking stack

These are not protocol features but are essential for practical adoption.

---

## 33. Documentation and governance requirements

### 33.1 Documents that MUST exist before public alpha

- this blueprint
- frame registry
- capability registry
- manifest schema doc
- bridge API doc
- gateway operator guide
- client operator guide
- security policy
- release process
- compatibility matrix

### 33.2 Governance rules

- protocol changes require documented rationale
- on-wire changes require fixture updates
- extension ids must not be reused
- experimental features must be clearly labeled
- deprecations require a removal plan and version target
- no undocumented “silent behavior” in released builds

### 33.3 Open source hygiene

The repository SHOULD include:

- `CONTRIBUTING.md`
- `SECURITY.md`
- `CODEOWNERS`
- changelog discipline
- issue templates
- RFC template for protocol changes

---

## 34. Implementation sequence implied by this blueprint

This is not the full roadmap; it is the execution order immediately implied by the blueprint.

### 34.1 Step 1 — Freeze core registries

Freeze:

- frame ids
- error codes
- capability ids
- TLV ids
- manifest schema version `1`
- core version `1`

### 34.2 Step 2 — Build codecs and fixtures

Implement:

- varint codec
- frame codec
- TLV codec
- golden test vectors
- parser fuzz harnesses

### 34.3 Step 3 — Build auth and manifest

Implement:

- signed manifest verification
- JWKS fetch/cache
- token exchange client
- token verification in gateway
- refresh/session credential handling

### 34.4 Step 4 — Build H3 carrier

Implement:

- carrier connect
- control tunnel
- relay stream open
- datagram send/receive
- fallback behaviors
- carrier metrics

### 34.5 Step 5 — Build gateway runtime

Implement:

- session accept loop
- hello validation
- policy engine
- upstream TCP dialer
- UDP flow manager
- drain/shutdown logic

### 34.6 Step 6 — Build client runtime

Implement:

- local SOCKS5 inbound
- local HTTP proxy inbound
- session manager
- endpoint/profile selection
- reconnect logic
- diagnostic output

### 34.7 Step 7 — Build bridge

Implement:

- manifest API
- token exchange API
- device register API
- control-plane adapter
- key rotation support

### 34.8 Step 8 — Build the performance and soak lab

Implement:

- automated scenario runner
- fault injection harness
- benchmark dashboard export
- qlog capture in test environment

---

## 35. Deferred “too much for now, but do not forget” backlog

This section is intentionally broad. These items are **not** v0, but they should remain visible.

### 35.1 Protocol evolution

- full IP tunnel mode
- multipath carrier support
- stream priorities
- connection migration hints
- application-aware traffic classes
- session resumption tickets
- encrypted endpoint hints
- richer policy push model
- structured GOAWAY retry semantics

### 35.2 Carrier evolution

- raw QUIC carrier
- H2/TLS fallback carrier
- profile-generated header and route variants
- ECH-aware carrier profiles when ecosystem support is mature
- adaptive keepalive policies by network type
- negotiated padding profiles if justified by measurements

### 35.3 Auth evolution

- device keypair binding
- stronger replay control
- attestation hooks
- out-of-band revocation feed
- delegated enterprise issuers
- offline-verifiable entitlement bundles

### 35.4 Client evolution

- TUN mode
- split tunnel UI and policy
- DNS proxy mode
- mobile client
- automatic local network quality scoring
- richer diagnostics bundle export
- self-healing profile quarantining

### 35.5 Gateway evolution

- policy cache invalidation bus
- regional steering
- connection pooling where appropriate
- smarter UDP idle reclamation
- kernel bypass experiments only if proven necessary
- eBPF visibility tooling for operators

### 35.6 Verification and assurance

- formal state machine modeling
- differential testing across implementations
- third-party security audit
- chaos testing in staging
- supply-chain hardening and hermetic builds
- long-term ABI/API stability policy

---

## 36. Open questions that should stay open until measurement answers them

These are not blockers for v0, but they should be tracked explicitly:

1. Should raw QUIC become carrier #2 before H2/TLS fallback, or after?
2. Is the datagram-vs-fallback threshold better chosen by profile, client measurement, or both?
3. Should token exchange optionally include network hints for better endpoint steering?
4. Is `PASETO` materially better than signed `JWT/JWS` for the team and ecosystem chosen?
5. What is the right session token TTL for usability vs revocation speed?
6. When IP tunnel mode arrives, should it be implemented as a distinct session mode or as an extension under the same hello?
7. How much client-side telemetry is acceptable before privacy and support costs outweigh its value?
8. Which Windows secure-storage mechanism gives the best UX/security trade-off for the first desktop release?
9. Which operational signals should drive automatic profile quarantine on the client?
10. Does the project eventually want a second independent implementation for interoperability assurance?

---

## 37. Example session timeline

This is illustrative, not normative.

```text
1. Client starts
2. Client fetches signed manifest from Bridge
3. Client verifies manifest signature
4. Client exchanges refresh credential for session token
5. Client selects endpoint + carrier profile
6. Client establishes H3 carrier
7. Client opens control tunnel
8. Client sends CLIENT_HELLO
9. Gateway verifies token and returns SERVER_HELLO
10. Session enters ESTABLISHED
11. Local SOCKS client requests TCP target
12. Verta client opens relay stream and sends STREAM_OPEN
13. Gateway connects upstream and replies STREAM_ACCEPT
14. Raw bytes flow
15. Local app sends UDP traffic
16. Client opens UDP_FLOW_OPEN on control stream
17. Gateway returns UDP_FLOW_OK (datagram or fallback)
18. UDP traffic flows
19. Gateway begins maintenance drain and sends GOAWAY
20. Client stops opening new streams, reconnects, then migrates load
21. Old session closes
```

---

## 38. Example manifest profile bundle

```json
{
  "schema_version": 1,
  "manifest_id": "sha256:fcc1d4...",
  "generated_at": "2026-04-01T10:00:00Z",
  "expires_at": "2026-04-01T16:00:00Z",
  "client_constraints": {
    "min_client_version": "0.1.0",
    "recommended_client_version": "0.1.1",
    "allowed_core_versions": [1]
  },
  "token_service": {
    "url": "https://bridge.example.net/v0/token/exchange",
    "issuer": "bridge-main",
    "jwks_url": "https://bridge.example.net/.well-known/jwks.json",
    "session_token_ttl_seconds": 300
  },
  "carrier_profiles": [
    {
      "id": "h3-generic-v1",
      "carrier": "h3",
      "priority": 100,
      "properties": {
        "alpn": ["h3"],
        "control_template": {"method": "CONNECT", "path": "/.well-known/ns/control"},
        "relay_template": {"method": "CONNECT", "path": "/.well-known/ns/stream"},
        "udp_template": {"mode": "h3-datagram"},
        "heartbeat_seconds": 20,
        "idle_timeout_seconds": 60
      }
    }
  ],
  "endpoints": [
    {
      "endpoint_id": "gw-eu-1",
      "host": "gw-eu-1.example.net",
      "port": 443,
      "region": "eu-central",
      "carrier_profiles": ["h3-generic-v1"],
      "weight": 100
    }
  ]
}
```

---

## 39. Example control-flow pseudocode

### 39.1 Client

```rust
loop {
    let manifest = fetch_and_verify_manifest().await?;
    let route = selector.choose_endpoint(&manifest, network_hint(), history())?;
    let token = exchange_session_token(&manifest, &route).await?;
    let mut carrier = connect_h3(&route).await?;
    let mut control = carrier.open_control_stream().await?;

    send_client_hello(&mut control, &manifest, &route, &token).await?;
    let hello = recv_server_hello(&mut control).await?;

    let session = establish_runtime(hello, carrier, control)?;
    run_local_proxy(session).await?;

    if should_retry() {
        backoff().await;
        continue;
    }
    break;
}
```

### 39.2 Gateway

```rust
loop {
    let conn = accept_carrier().await?;
    spawn(async move {
        let mut control = open_control_tunnel(conn).await?;
        let hello = recv_client_hello(&mut control).await?;
        let claims = verify_token(hello.token()).await?;
        let policy = authorize_session(&claims, &hello)?;
        let session = send_server_hello(&mut control, policy).await?;
        run_session(session, control).await
    });
}
```

---

## 40. Definition of done for Blueprint v0

Blueprint v0 is considered “done” when all of the following are true:

1. frame ids, error codes, capability ids, and TLV ids are frozen for core version `1`
2. manifest schema `1` is frozen
3. `CLIENT_HELLO` and `SERVER_HELLO` payloads are frozen
4. relay and UDP flow semantics are frozen
5. the H3 carrier mapping is frozen enough for one implementation
6. the Rust workspace split is accepted
7. the security baseline is accepted
8. the testing requirements are accepted
9. the deferred backlog is captured so it does not leak into v0 by accident

---

## 41. Recommended immediate next document after this one

After Blueprint v0, the next document should be:

**Verta Spec v0.1 — Wire Format and API Freeze Candidate**

That follow-up document should include:

- exact binary examples
- fixture ids
- JSON Schema for the manifest
- JWKS/token verification profile
- bridge OpenAPI draft
- crate-by-crate task breakdown
- conformance test definitions

This blueprint intentionally stops one layer above that freeze-candidate level so design can still be reviewed before implementation lock-in.

---

## 42. Final guidance

The central discipline for this project is simple:

- keep the session core small
- keep the carrier replaceable
- keep the profiles remote-controlled
- keep the observability first-class
- keep the compatibility story explicit
- keep “not yet” features visible but out of v0

That is how the project avoids becoming another brittle protocol with a clever first release and painful long-term maintenance.
