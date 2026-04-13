# Northstar Spec v0.1 — Wire Format Freeze Candidate

**Status:** Freeze Candidate v0.1  
**Codename:** Northstar  
**Document type:** wire-format, manifest, token-profile, and public-API freeze candidate  
**Audience:** protocol architects, Rust implementers, bridge/control-plane implementers, client engineers, test engineers, security reviewers, AI coding agents  
**Supersedes:** Blueprint v0 by making selected parts implementation-grade and temporarily frozen  
**Core version covered:** `1`  
**Primary carrier covered:** `h3` (`CarrierKind = 1`)  
**Manifest schema covered:** `schema_version = 1`  
**Bridge public API covered:** `/v0/*`

---

## 1. Why this document exists

Blueprint v0 defined the architecture and first implementation shape.

This document freezes the parts that must stop drifting before real implementation begins:

- exact control-stream frame envelope
- exact field order for v0.1 frames
- exact registries and enums used by client, gateway, and bridge
- initial size limits and canonical encoding rules
- fixture ids and binary examples
- manifest schema v1
- bridge public API draft
- session-token verification profile

This is not yet a permanent RFC. It is a **working freeze candidate**.  
Its purpose is to let multiple implementations move in parallel **without silently diverging**.

---

## 2. What “freeze candidate” means here

For the scope listed below, the project now treats these items as **stable enough to implement**.

### 2.1 Frozen in this document

The following are frozen for v0.1 unless a compatibility review explicitly approves a change:

1. control-frame envelope
2. frame type ids
3. error code ids
4. capability ids
5. carrier kind ids
6. target type ids
7. field order and on-wire encoding of all v0.1 frames
8. mandatory receiver behavior for malformed or out-of-order frames
9. manifest top-level schema version `1`
10. bridge public endpoint names under `/v0`
11. JWT/JWS verification profile for the reference bridge/gateway stack
12. conformance fixture ids referenced by tests

### 2.2 Not frozen yet

The following remain intentionally adjustable:

- profile/persona content and rollout heuristics
- endpoint-selection strategy details
- congestion-control tuning
- retry backoff constants within manifest policy limits
- telemetry semantics beyond the TLV ids already listed
- future carrier mappings (`raw_quic`, `h2_tls`, others)
- session resumption and 0-RTT
- full IP tunnel mode
- extension frame range `0x80-0xBF`

---

## 3. Normative language

The key words **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** are normative.

When this document says **receiver**, it means whichever side is currently decoding bytes for the frame being described.

When this document says **control stream**, it means the unique carrier-native reliable stream that carries Northstar control frames for the lifetime of the session.

---

## 4. Versioning and compatibility policy

### 4.1 Version numbers in scope

- **Session core version:** `1`
- **Manifest schema version:** `1`
- **Bridge public API version prefix:** `/v0`
- **Freeze document revision:** `0.1`

### 4.2 Compatibility promises for v0.1

The reference implementation MUST preserve compatibility across:

- the same core version (`1`)
- the same manifest schema version (`1`)
- additive manifest properties that clients ignore safely
- additive non-critical TLV values

The reference implementation MUST NOT silently reinterpret:

- an existing frame type
- an existing field position
- an existing error code
- an existing capability id

### 4.3 Allowed post-freeze changes without a major version bump

Allowed:

- adding optional manifest properties
- adding new TLV types that old receivers ignore safely
- adding new capability ids
- adding new error details inside TLVs
- tightening implementation-side limits if the manifest or hello already advertises the effective limits

Not allowed without a new core version or explicit compatibility path:

- changing frame field order
- reusing old ids for new meanings
- changing fixed-size field length
- changing the semantic type of an existing field
- redefining an enum value

---

## 5. Transport and session assumptions

Northstar v0.1 assumes:

1. the carrier provides one reliable bidirectional control stream
2. the carrier provides additional reliable bidirectional streams
3. datagrams may or may not be available
4. carrier confidentiality and integrity are provided by standard TLS/QUIC libraries
5. the session core stays transport-agnostic above the carrier binding

The only required carrier in v0.1 is:

- `CarrierKind = 1` → `h3`

---

## 6. Canonical encoding profile

### 6.1 Primitive types

Unless explicitly stated otherwise:

- integers use **QUIC-style varint**
- booleans use one byte: `0x00` or `0x01`
- strings use UTF-8 preceded by a varint byte length
- opaque byte arrays use a varint byte length followed by raw bytes
- fixed-size fields remain fixed-size and are not length-prefixed
- enums are encoded as varints
- bitsets are encoded as varints
- TLV values are opaque bytes

### 6.2 QUIC-style varint profile

Northstar adopts the QUIC variable-length integer layout:

- 1 byte: values `0..63`
- 2 bytes: values `64..16383`
- 4 bytes: values `16384..1073741823`
- 8 bytes: values `1073741824..4611686018427387903`

### 6.3 Canonical integer rule

Senders MUST use the **shortest valid varint encoding**.

Receivers MUST reject a non-canonical varint encoding with:

- `ERROR(PROTOCOL_VIOLATION, terminal = true)` on the control stream, or
- immediate relay/fallback stream close for a preamble frame

This rule is stricter than some generic varint ecosystems on purpose; it keeps parsers small, deterministic, and fuzzable.

### 6.4 String normalization

For v0.1:

- identifiers such as `ManifestId`, `CarrierProfileId`, `DeviceBindingId`, and endpoint ids are case-sensitive UTF-8 strings
- DNS names sent in `TargetHost` for `TargetType = domain` SHOULD already be ASCII A-label form (punycode if needed)
- clients SHOULD lowercase domain targets before sending unless a future profile explicitly preserves case for diagnostics
- receivers MUST treat zero-length target domain strings as invalid

### 6.5 Opaque bytes

`Token` is carried as opaque bytes on wire even though the reference stack uses compact JWS/JWT text at the bridge/API layer.

### 6.6 Maximum lengths and counts

These are v0.1 reference limits. A stricter implementation MAY enforce smaller limits only if it does not violate the effective session contract already negotiated.

| Item | v0.1 hard ceiling |
|---|---:|
| Control frame payload | 65535 bytes |
| Relay preamble payload | 4096 bytes |
| `Token` field length | 4096 bytes |
| Any string field unless otherwise stated | 1024 bytes |
| Domain `TargetHost` | 255 bytes |
| `CarrierProfileId` | 128 bytes |
| `ManifestId` | 256 bytes |
| `DeviceBindingId` | 128 bytes |
| Metadata TLV count in one frame | 16 |
| One TLV value length | 2048 bytes |
| `RequestedCapabilitiesCount` | 64 |
| `SelectedCapabilitiesCount` | 64 |
| Concurrent relay streams advertised by hello | 65535 |
| Concurrent UDP flows advertised by hello | 65535 |

### 6.7 Boolean validity

Any boolean field with a value other than `0x00` or `0x01` MUST be treated as `PROTOCOL_VIOLATION`.

---

## 7. Core object identifiers

### 7.1 SessionId

- fixed size: **16 bytes**
- chosen by the server
- unique only for active session scope
- opaque to the client
- not an authentication secret

### 7.2 RelayId

- session-scoped varint chosen by the client
- MUST be unique among active relay streams
- MUST NOT be reused until the session is fully closed

### 7.3 FlowId

- session-scoped varint chosen by the client
- MUST be unique among active UDP flows
- MUST NOT be reused until the session is fully closed

---

## 8. Registries and enums

### 8.1 Capability registry

| ID | Name | v0.1 status |
|---|---|---|
| 1 | `tcp_relay` | required |
| 2 | `udp_relay_datagram` | optional |
| 3 | `udp_relay_stream_fallback` | required |
| 4 | `policy_push` | optional |
| 5 | `resume_hint` | reserved |
| 6 | `path_change_signal` | optional |
| 7 | `ip_tunnel_reserved` | reserved |
| 8 | `stats_push` | optional |
| 9 | `manifest_delta` | reserved |
| 10 | `gateway_goaway` | optional |

v0.1 client and gateway MUST support:

- `1` (`tcp_relay`)
- `3` (`udp_relay_stream_fallback`)

If datagrams are available and enabled, they SHOULD also support:

- `2` (`udp_relay_datagram`)

### 8.2 Carrier kind registry

| ID | Name | v0.1 status |
|---|---|---|
| 1 | `h3` | primary |
| 2 | `raw_quic` | reserved |
| 3 | `h2_tls` | reserved |
| 4 | `ws_tls` | reserved |
| 5 | `tcp_tls_custom` | reserved |

### 8.3 Frame type registry

| Type ID | Name | Direction | Context |
|---|---|---|---|
| `0x01` | `CLIENT_HELLO` | C → S | control |
| `0x02` | `SERVER_HELLO` | S → C | control |
| `0x03` | `PING` | both | control |
| `0x04` | `PONG` | both | control |
| `0x05` | `ERROR` | both | control / preamble failure |
| `0x06` | `GOAWAY` | S → C | control |
| `0x07` | `POLICY_UPDATE` | S → C | control |
| `0x08` | `UDP_FLOW_OPEN` | C → S | control |
| `0x09` | `UDP_FLOW_OK` | S → C | control |
| `0x0A` | `UDP_FLOW_CLOSE` | both | control |
| `0x0B` | `SESSION_STATS` | both | control |
| `0x0C` | `PATH_EVENT` | C → S | control |
| `0x0D` | `RESUME_TICKET` | S → C | reserved, not used |
| `0x0E` | `SESSION_CLOSE` | both | control |
| `0x40` | `STREAM_OPEN` | C → S | relay preamble |
| `0x41` | `STREAM_ACCEPT` | S → C | relay preamble |
| `0x42` | `STREAM_REJECT` | S → C | relay preamble |
| `0x43` | `UDP_STREAM_OPEN` | C → S | fallback stream preamble |
| `0x44` | `UDP_STREAM_ACCEPT` | S → C | fallback stream preamble |
| `0x45` | `UDP_STREAM_PACKET` | both | fallback stream framed mode |
| `0x46` | `UDP_STREAM_CLOSE` | both | fallback stream framed mode |

Range policy:

- `0x00-0x3F`: control frames
- `0x40-0x7F`: preamble/fallback stream frames
- `0x80-0xBF`: future extension range
- `0xC0-0xFF`: experimental/private use only

### 8.4 Error code registry

| Code | Name |
|---:|---|
| 0 | `NO_ERROR` |
| 1 | `PROTOCOL_VIOLATION` |
| 2 | `UNSUPPORTED_VERSION` |
| 3 | `AUTH_FAILED` |
| 4 | `TOKEN_EXPIRED` |
| 5 | `POLICY_DENIED` |
| 6 | `RATE_LIMITED` |
| 7 | `TARGET_DENIED` |
| 8 | `FLOW_LIMIT_REACHED` |
| 9 | `INTERNAL_ERROR` |
| 10 | `CARRIER_UNSUPPORTED` |
| 11 | `PROFILE_MISMATCH` |
| 12 | `REPLAY_SUSPECTED` |
| 13 | `IDLE_TIMEOUT` |
| 14 | `DRAINING` |
| 15 | `RESOLUTION_FAILED` |
| 16 | `CONNECT_FAILED` |
| 17 | `NETWORK_UNREACHABLE` |
| 18 | `FRAME_TOO_LARGE` |
| 19 | `UNSUPPORTED_TARGET_TYPE` |
| 20 | `UDP_DATAGRAM_UNAVAILABLE` |

### 8.5 Target type registry

| ID | Name | Encoding of target field |
|---|---|---|
| 1 | `domain` | UTF-8 string (normally ASCII A-label) |
| 2 | `ipv4` | opaque bytes, length MUST equal 4 |
| 3 | `ipv6` | opaque bytes, length MUST equal 16 |

### 8.6 Datagram mode registry

| ID | Name |
|---|---|
| 0 | unavailable |
| 1 | available_and_enabled |
| 2 | disabled_by_policy |

### 8.7 Stats mode registry

| ID | Name |
|---|---|
| 0 | off |
| 1 | sampled_client_push_allowed |
| 2 | sampled_bidirectional |

### 8.8 `OpenFlags` for `STREAM_OPEN`

| Bit | Meaning | v0.1 use |
|---:|---|---|
| 0 | `prefer_ipv6` | hint |
| 1 | `low_latency` | hint |
| 2 | `allow_rebind` | reserved |
| 3 | `metadata_present` | informational only |
| 4-63 | reserved | MUST be zero |

Receivers MUST ignore bit `3` because metadata presence is already known from `MetadataCount`.  
Receivers MUST reject unknown non-zero reserved bits with `PROTOCOL_VIOLATION`.

### 8.9 `FlowFlags` for `UDP_FLOW_OPEN`

| Bit | Meaning | v0.1 use |
|---:|---|---|
| 0 | `prefer_datagram` | hint |
| 1 | `allow_stream_fallback` | required for robust clients |
| 2 | `dns_optimized` | hint |
| 3 | `client_keepalive` | hint |
| 4-63 | reserved | MUST be zero |

### 8.10 `Flags` for `POLICY_UPDATE`

| Bit | Meaning |
|---:|---|
| 0 | datagram disabled immediately |
| 1 | stats push enabled |
| 2 | session draining |
| 3 | endpoint migration advised |
| 4-63 | reserved |

### 8.11 `PATH_EVENT.EventType`

| ID | Name |
|---|---|
| 1 | `network_changed` |
| 2 | `nat_rebinding_suspected` |
| 3 | `mtu_decreased` |
| 4 | `mtu_increased` |

### 8.12 TLV registry

| TLV ID | Name | Value encoding in v0.1 |
|---|---|---|
| 1 | `client_platform` | UTF-8 string |
| 2 | `client_version` | UTF-8 string |
| 3 | `install_channel` | UTF-8 string |
| 4 | `gateway_region` | UTF-8 string |
| 5 | `gateway_build` | UTF-8 string |
| 6 | `policy_name` | UTF-8 string |
| 7 | `dns_mode` | UTF-8 string |
| 8 | `rtt_hint_ms` | varint stored as opaque bytes |
| 9 | `mtu_hint` | varint stored as opaque bytes |
| 10 | `target_tag` | UTF-8 string |
| 11 | `trace_sampling` | UTF-8 string or numeric text |
| 12 | `reason_detail_code` | UTF-8 string |
| 13 | `bridge_manifest_hash` | UTF-8 string |
| 14 | `profile_generation` | UTF-8 string |
| 15 | `observability_profile` | UTF-8 string |

Unknown TLVs MUST be ignored unless and until a future extension marks them critical through an extension-level negotiation rule.

---

## 9. Generic frame envelope

### 9.1 Control stream frame envelope

All control-stream frames MUST use:

```text
Frame =
  Type        (varint)
  Length      (varint)
  Payload     (Length bytes)
```

There is no application checksum. Integrity is delegated to the carrier.

### 9.2 Preamble stream frame envelope

Relay preambles and UDP fallback frames also use the same `Type + Length + Payload` envelope **until raw data mode starts**.

### 9.3 Raw relay data mode

After `STREAM_ACCEPT`, the relay stream switches to raw byte forwarding mode and MUST NOT carry additional Northstar frame envelopes on that stream.

### 9.4 Unknown frame handling

For v0.1:

- unknown control-frame type → `ERROR(PROTOCOL_VIOLATION, terminal = true)` then close session
- unknown relay/fallback stream frame type in preamble/framed mode → immediate stream close
- receiving `RESUME_TICKET` in v0.1 → `PROTOCOL_VIOLATION`

---

## 10. Session sequencing and timing

### 10.1 Control stream sequencing

The first frame on the control stream MUST be `CLIENT_HELLO`.

Before `SERVER_HELLO` is received, the client MUST NOT:

- open relay streams
- open UDP flows
- send `PATH_EVENT`
- send `SESSION_STATS`

The server MUST NOT send any control frame before `SERVER_HELLO` except:

- `ERROR`

### 10.2 Session states

```text
INIT
  -> HANDSHAKING
  -> ESTABLISHED
  -> DRAINING
  -> CLOSED
```

### 10.3 Recommended default timers

These are v0.1 implementation defaults, not immutable protocol ids:

- handshake timeout: `10_000 ms`
- control-stream idle probe interval: `20_000 ms`
- ping response deadline: `10_000 ms`
- graceful drain deadline after `GOAWAY`: `30_000 ms`
- UDP flow idle timeout default request: `15_000 ms`
- session token TTL recommendation: `300 s`

### 10.4 Required timeout behaviors

- if the client does not receive `SERVER_HELLO` before handshake timeout, it MUST tear down the session
- if the gateway receives malformed hello data, it SHOULD send `ERROR` with the best specific code and then close
- if the control stream becomes unreadable, the whole session MUST be considered closed

---

## 11. Exact frame definitions

The field order below is frozen for v0.1.

### 11.1 `CLIENT_HELLO` (`0x01`)

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

#### Receiver rules

The server MUST reject `CLIENT_HELLO` if:

- `MinVersion > MaxVersion`
- `ClientNonce` length is not exactly 32 bytes
- `RequestedCapabilitiesCount` does not match the number of encoded entries
- `CarrierKind` is unsupported
- `CarrierProfileId` is empty
- `ManifestId` is empty
- `Token` is empty
- metadata count exceeds limits
- any reserved capability id is treated as already negotiated

The server SHOULD validate at minimum:

- token authenticity
- token expiry / not-before
- device binding, if policy requires it
- allowed carrier profile
- allowed core version
- allowed capabilities subset

### 11.2 `SERVER_HELLO` (`0x02`)

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

#### Receiver rules

The client MUST reject `SERVER_HELLO` if:

- `SelectedVersion` is outside the range it requested
- `SessionId` is not 16 bytes
- `ServerNonce` is not 32 bytes
- `SelectedCapabilities` is not a subset of requested capabilities
- `DatagramMode` is unknown
- `StatsMode` is unknown
- any advertised limit is zero when that would make the session unusable

### 11.3 `PING` (`0x03`)

```text
PING =
  PingId     (varint)
  Timestamp  (varint)
```

`Timestamp` is advisory only. It is not a synchronized clock.

### 11.4 `PONG` (`0x04`)

```text
PONG =
  PingId     (varint)
  Timestamp  (varint)
```

`PingId` MUST match an outstanding ping if the receiver tracks outstanding probes.

### 11.5 `ERROR` (`0x05`)

```text
ERROR =
  ErrorCode        (varint)
  ErrorMessage     (string)
  IsTerminal       (bool)
  DetailsCount     (varint)
  Details[]        (TLV)
```

Rules:

- implementations MUST key logic on `ErrorCode`, not message text
- if `IsTerminal = true` on control stream, the receiver SHOULD expect imminent session closure
- for preamble-stream failure cases, `ERROR` MAY be replaced by direct stream close if the carrier binding cannot or should not deliver a structured frame

### 11.6 `GOAWAY` (`0x06`)

```text
GOAWAY =
  ReasonCode             (varint)
  RetryAfterMs           (varint)
  PreferredEndpointCount (varint)
  PreferredEndpoints[]   (string)
  Message                (string)
```

Recommended `ReasonCode` values for v0.1:

| ID | Name |
|---|---|
| 1 | planned_maintenance |
| 2 | overload |
| 3 | policy_change |
| 4 | profile_rotated |
| 5 | endpoint_deprecated |

Client behavior:

- MUST stop opening new relay streams
- SHOULD stop opening new UDP flows
- MAY keep existing streams until closure or deadline
- SHOULD prefer the listed endpoints if available

### 11.7 `POLICY_UPDATE` (`0x07`)

```text
POLICY_UPDATE =
  PolicyEpoch                  (varint)
  EffectiveIdleTimeoutMs       (varint)
  MaxConcurrentRelayStreams    (varint)
  MaxUdpFlows                  (varint)
  EffectiveMaxUdpPayload       (varint)
  Flags                        (varint)
  MetadataCount                (varint)
  Metadata[]                   (TLV)
```

The client MUST treat `POLICY_UPDATE` as authoritative immediately for the active session.

### 11.8 `UDP_FLOW_OPEN` (`0x08`)

```text
UDP_FLOW_OPEN =
  FlowId             (varint)
  TargetType         (varint)
  TargetHost         (string or bytes depending on TargetType)
  TargetPort         (varint)
  IdleTimeoutMs      (varint)
  FlowFlags          (varint)
  MetadataCount      (varint)
  Metadata[]         (TLV)
```

Rules:

- `TargetType = 1` → `TargetHost` is a string
- `TargetType = 2` → `TargetHost` is bytes with length 4
- `TargetType = 3` → `TargetHost` is bytes with length 16
- `TargetPort` MUST be in `1..65535`
- the server MUST reject a new flow if the flow id is already active
- the server MUST reject reserved flag bits if any are set

### 11.9 `UDP_FLOW_OK` (`0x09`)

```text
UDP_FLOW_OK =
  FlowId                   (varint)
  TransportMode            (varint)
  EffectiveIdleTimeoutMs   (varint)
  EffectiveMaxPayload      (varint)
  MetadataCount            (varint)
  Metadata[]               (TLV)
```

`TransportMode` values:

- `1` = datagram
- `2` = stream_fallback

### 11.10 `UDP_FLOW_CLOSE` (`0x0A`)

```text
UDP_FLOW_CLOSE =
  FlowId         (varint)
  ErrorCode      (varint)
  Message        (string)
```

Either side MAY send it. After receipt, both sides SHOULD consider the flow terminal.

### 11.11 `SESSION_STATS` (`0x0B`)

```text
SESSION_STATS =
  StatsKind        (varint)
  SampleStartMs    (varint)
  SampleEndMs      (varint)
  MetricCount      (varint)
  Metrics[]        (TLV)
```

Recommended `StatsKind` values:

| ID | Name |
|---|---|
| 1 | client_sample |
| 2 | gateway_sample |
| 3 | bidirectional_compare |

### 11.12 `PATH_EVENT` (`0x0C`)

```text
PATH_EVENT =
  EventType        (varint)
  PreviousNetwork  (string)
  NewNetwork       (string)
  ClientHintCount  (varint)
  ClientHints[]    (TLV)
```

The gateway MAY ignore it.  
The client MUST NOT rely on any direct response.

### 11.13 `SESSION_CLOSE` (`0x0E`)

```text
SESSION_CLOSE =
  ErrorCode      (varint)
  Message        (string)
```

Either side MAY send `SESSION_CLOSE` before closing the control stream.

### 11.14 `STREAM_OPEN` (`0x40`)

```text
STREAM_OPEN =
  RelayId            (varint)
  TargetType         (varint)
  TargetHost         (string or bytes depending on TargetType)
  TargetPort         (varint)
  OpenFlags          (varint)
  MetadataCount      (varint)
  Metadata[]         (TLV)
```

Rules mirror `UDP_FLOW_OPEN` for target encoding.  
`RelayId` MUST be unique within the active session.

### 11.15 `STREAM_ACCEPT` (`0x41`)

```text
STREAM_ACCEPT =
  RelayId              (varint)
  BindAddressType      (varint)
  BindAddress          (string or bytes depending on BindAddressType)
  BindPort             (varint)
  MetadataCount        (varint)
  Metadata[]           (TLV)
```

`BindAddress` MAY be empty only if a future carrier profile explicitly allows that optimization.  
For v0.1 reference implementation, the server SHOULD send the actual local bind address it used unless privacy policy disables it.

### 11.16 `STREAM_REJECT` (`0x42`)

```text
STREAM_REJECT =
  RelayId          (varint)
  ErrorCode        (varint)
  Retryable        (bool)
  Message          (string)
  MetadataCount    (varint)
  Metadata[]       (TLV)
```

After `STREAM_REJECT`, the stream MUST be closed.

### 11.17 Relay raw-data phase

After `STREAM_ACCEPT`, the stream becomes raw full-duplex bytes.  
No further framed Northstar messages are allowed on that stream.

### 11.18 `UDP_STREAM_OPEN` (`0x43`)

```text
UDP_STREAM_OPEN =
  FlowId          (varint)
  MetadataCount   (varint)
  Metadata[]      (TLV)
```

This is only valid when the flow was previously accepted with `TransportMode = 2`.

### 11.19 `UDP_STREAM_ACCEPT` (`0x44`)

```text
UDP_STREAM_ACCEPT =
  FlowId          (varint)
  MetadataCount   (varint)
  Metadata[]      (TLV)
```

### 11.20 `UDP_STREAM_PACKET` (`0x45`)

```text
UDP_STREAM_PACKET =
  PacketLength    (varint)
  Payload         (PacketLength bytes)
```

This frame is only valid inside an accepted UDP fallback stream.

### 11.21 `UDP_STREAM_CLOSE` (`0x46`)

```text
UDP_STREAM_CLOSE =
  FlowId          (varint)
  ErrorCode       (varint)
  Message         (string)
```

---

## 12. UDP datagram payload format

If `UDP_FLOW_OK.TransportMode = 1`, per-packet payloads MUST use:

```text
UDP_DATAGRAM =
  FlowId         (varint)
  Flags          (varint)
  PayloadBytes   (remaining bytes)
```

Reserved flag bits:

| Bit | Meaning |
|---:|---|
| 0 | more_fragments_reserved |
| 1 | ecn_present_reserved |
| 2-63 | reserved |

v0.1 does **not** define session-layer fragmentation.  
Oversized payloads MUST be rejected or dropped according to policy rather than fragmented in-protocol.

---

## 13. Receiver error handling rules

### 13.1 General malformed-input rules

A receiver MUST treat the following as `PROTOCOL_VIOLATION`:

- non-canonical varint
- truncated frame envelope
- declared length larger than available bytes
- unknown enum value in a frozen field
- illegal frame for current state
- reserved bits set in a v0.1 bitset
- target/address length mismatch
- duplicate active `RelayId`
- duplicate active `FlowId`

### 13.2 Frame-size handling

If a frame payload exceeds the hard ceiling, the receiver SHOULD respond with:

- `FRAME_TOO_LARGE` if possible, else
- immediate stream/session termination

### 13.3 Policy vs protocol distinction

Use:

- `POLICY_DENIED`, `TARGET_DENIED`, `RATE_LIMITED`, `FLOW_LIMIT_REACHED` for validly encoded requests blocked by policy
- `PROTOCOL_VIOLATION` for malformed or out-of-sequence traffic

---

## 14. Binary fixtures

These fixtures are intentionally simple and deterministic.  
They are not secrets, not production tokens, and not cryptographic test vectors.

### 14.1 Fixture `NS-FX-HELLO-001` — `CLIENT_HELLO`

Decoded fields:

- `MinVersion = 1`
- `MaxVersion = 1`
- `ClientNonce = 00 01 02 ... 1f`
- requested capabilities = `[1, 2, 3, 4, 6, 8, 10]`
- `CarrierKind = 1`
- `CarrierProfileId = "h3-main-v1"`
- `ManifestId = "man-2026-04-01-001"`
- `DeviceBindingId = "dev-01-abc"`
- `RequestedIdleTimeoutMs = 30000`
- `RequestedMaxUdpPayload = 1200`
- `Token = "tok_v0_demo_0001"`
- metadata:
  - `client_platform = "windows-x64"`
  - `client_version = "0.1.0"`

```hex
0140800101000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f070102030406080a010a68332d6d61696e2d7631126d616e2d323032362d30342d30312d3030310a6465762d30312d6162638000753044b010746f6b5f76305f64656d6f5f3030303102010b77696e646f77732d7836340205302e312e30
```

### 14.2 Fixture `NS-FX-HELLO-ACK-001` — `SERVER_HELLO`

Decoded fields:

- `SelectedVersion = 1`
- `SessionId = a0 a1 ... af`
- `ServerNonce = 20 21 ... 3f`
- selected capabilities = `[1, 2, 3, 4, 8, 10]`
- `PolicyEpoch = 7`
- `EffectiveIdleTimeoutMs = 45000`
- `SessionLifetimeMs = 300000`
- `MaxConcurrentRelayStreams = 64`
- `MaxUdpFlows = 16`
- `EffectiveMaxUdpPayload = 1200`
- `DatagramMode = 1`
- `StatsMode = 1`
- metadata:
  - `gateway_region = "kz-alm-1"`
  - `gateway_build = "g-0.1.0"`

```hex
02405c01a0a1a2a3a4a5a6a7a8a9aaabacadaeaf202122232425262728292a2b2c2d2e2f303132333435363738393a3b3c3d3e3f0601020304080a078000afc8800493e040401044b001010204086b7a2d616c6d2d310507672d302e312e30
```

### 14.3 Fixture `NS-FX-PING-001` — `PING`

Decoded fields:

- `PingId = 55`
- `Timestamp = 123456`

```hex
0305378001e240
```

### 14.4 Fixture `NS-FX-ERR-001` — terminal `ERROR(AUTH_FAILED)`

Decoded fields:

- `ErrorCode = 3`
- `ErrorMessage = "auth failed"`
- `IsTerminal = true`
- detail TLV:
  - `reason_detail_code = "sig_invalid"`

```hex
051c030b61757468206661696c656401010c0b7369675f696e76616c6964
```

### 14.5 Fixture `NS-FX-STREAM-OPEN-001` — `STREAM_OPEN`

Decoded fields:

- `RelayId = 1`
- `TargetType = domain`
- `TargetHost = "example.com"`
- `TargetPort = 443`
- `OpenFlags = 0`
- metadata:
  - `target_tag = "web"`

```hex
40401701010b6578616d706c652e636f6d41bb00010a03776562
```

### 14.6 Fixture `NS-FX-STREAM-ACCEPT-001` — `STREAM_ACCEPT`

Decoded fields:

- `RelayId = 1`
- `BindAddressType = ipv4`
- `BindAddress = 203.0.113.10`
- `BindPort = 51000`

```hex
40410c010204cb00710a8000c73800
```

### 14.7 Fixture `NS-FX-UDP-OPEN-001` — `UDP_FLOW_OPEN`

Decoded fields:

- `FlowId = 7`
- `TargetType = domain`
- `TargetHost = "1.1.1.1"` (string form kept for fixture simplicity)
- `TargetPort = 53`
- `IdleTimeoutMs = 15000`
- `FlowFlags = prefer_datagram | allow_stream_fallback`
- metadata:
  - `target_tag = "dns"`

```hex
0814070107312e312e312e31357a9803010a03646e73
```

### 14.8 Fixture `NS-FX-UDP-OK-001` — `UDP_FLOW_OK`

Decoded fields:

- `FlowId = 7`
- `TransportMode = 1` (`datagram`)
- `EffectiveIdleTimeoutMs = 15000`
- `EffectiveMaxPayload = 1200`
- metadata:
  - `policy_name = "dns-fast"`

```hex
091107017a9844b0010608646e732d66617374
```

### 14.9 Fixture `NS-FX-UDP-DGRAM-001` — `UDP_DATAGRAM`

Decoded fields:

- `FlowId = 7`
- `Flags = 0`
- payload bytes = `12 34 ab cd`

```hex
07001234abcd
```

---

## 15. Manifest schema v1 freeze candidate

The manifest is a control document, not a session frame.  
Still, it is part of the implementation contract and therefore frozen here as schema version `1`.

### 15.1 JSON Schema draft

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://northstar.example/spec/manifest-v1.schema.json",
  "title": "Northstar Manifest v1",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version",
    "manifest_id",
    "generated_at",
    "expires_at",
    "client_constraints",
    "token_service",
    "carrier_profiles",
    "endpoints",
    "routing",
    "retry_policy",
    "telemetry",
    "signature"
  ],
  "properties": {
    "schema_version": { "const": 1 },
    "manifest_id": { "type": "string", "minLength": 8, "maxLength": 256 },
    "generated_at": { "type": "string", "format": "date-time" },
    "expires_at": { "type": "string", "format": "date-time" },
    "user": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "account_id": { "type": "string", "minLength": 1, "maxLength": 128 },
        "plan_id": { "type": "string", "minLength": 1, "maxLength": 128 },
        "display_name": { "type": "string", "maxLength": 128 }
      }
    },
    "device_policy": {
      "type": "object",
      "additionalProperties": false,
      "required": ["max_devices", "require_device_binding"],
      "properties": {
        "max_devices": { "type": "integer", "minimum": 1, "maximum": 64 },
        "require_device_binding": { "type": "boolean" }
      }
    },
    "client_constraints": {
      "type": "object",
      "additionalProperties": false,
      "required": ["min_client_version", "recommended_client_version", "allowed_core_versions"],
      "properties": {
        "min_client_version": { "type": "string", "minLength": 1, "maxLength": 32 },
        "recommended_client_version": { "type": "string", "minLength": 1, "maxLength": 32 },
        "allowed_core_versions": {
          "type": "array",
          "minItems": 1,
          "maxItems": 16,
          "items": { "type": "integer", "minimum": 1, "maximum": 65535 }
        }
      }
    },
    "token_service": {
      "type": "object",
      "additionalProperties": false,
      "required": ["url", "issuer", "jwks_url", "session_token_ttl_seconds"],
      "properties": {
        "url": { "type": "string", "format": "uri" },
        "issuer": { "type": "string", "minLength": 1, "maxLength": 128 },
        "jwks_url": { "type": "string", "format": "uri" },
        "session_token_ttl_seconds": { "type": "integer", "minimum": 30, "maximum": 3600 }
      }
    },
    "refresh": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "mode": { "type": "string", "enum": ["opaque_secret", "signed_proof", "bootstrap_only"] },
        "credential": { "type": "string", "minLength": 1, "maxLength": 4096 },
        "rotation_hint_seconds": { "type": "integer", "minimum": 60, "maximum": 31536000 }
      }
    },
    "carrier_profiles": {
      "type": "array",
      "minItems": 1,
      "maxItems": 64,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "id",
          "carrier_kind",
          "origin_host",
          "origin_port",
          "alpn",
          "control_template",
          "relay_template",
          "datagram_enabled",
          "heartbeat_interval_ms",
          "idle_timeout_ms",
          "connect_backoff"
        ],
        "properties": {
          "id": { "type": "string", "minLength": 1, "maxLength": 128 },
          "carrier_kind": { "type": "string", "enum": ["h3"] },
          "origin_host": { "type": "string", "minLength": 1, "maxLength": 255 },
          "origin_port": { "type": "integer", "minimum": 1, "maximum": 65535 },
          "sni": { "type": "string", "maxLength": 255 },
          "alpn": {
            "type": "array",
            "minItems": 1,
            "maxItems": 8,
            "items": { "type": "string", "minLength": 1, "maxLength": 16 }
          },
          "control_template": {
            "type": "object",
            "additionalProperties": false,
            "required": ["method", "path"],
            "properties": {
              "method": { "type": "string", "enum": ["CONNECT"] },
              "path": { "type": "string", "minLength": 1, "maxLength": 256 }
            }
          },
          "relay_template": {
            "type": "object",
            "additionalProperties": false,
            "required": ["method", "path"],
            "properties": {
              "method": { "type": "string", "enum": ["CONNECT"] },
              "path": { "type": "string", "minLength": 1, "maxLength": 256 }
            }
          },
          "headers": {
            "type": "object",
            "maxProperties": 32,
            "additionalProperties": { "type": "string", "maxLength": 1024 }
          },
          "datagram_enabled": { "type": "boolean" },
          "heartbeat_interval_ms": { "type": "integer", "minimum": 5000, "maximum": 300000 },
          "idle_timeout_ms": { "type": "integer", "minimum": 10000, "maximum": 1800000 },
          "zero_rtt_policy": { "type": "string", "enum": ["disabled", "allow", "force_disabled"] },
          "connect_backoff": {
            "type": "object",
            "additionalProperties": false,
            "required": ["initial_ms", "max_ms", "jitter"],
            "properties": {
              "initial_ms": { "type": "integer", "minimum": 50, "maximum": 60000 },
              "max_ms": { "type": "integer", "minimum": 50, "maximum": 600000 },
              "jitter": { "type": "number", "minimum": 0.0, "maximum": 1.0 }
            }
          }
        }
      }
    },
    "endpoints": {
      "type": "array",
      "minItems": 1,
      "maxItems": 256,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["id", "host", "port", "region", "carrier_profile_ids", "priority", "weight"],
        "properties": {
          "id": { "type": "string", "minLength": 1, "maxLength": 128 },
          "host": { "type": "string", "minLength": 1, "maxLength": 255 },
          "port": { "type": "integer", "minimum": 1, "maximum": 65535 },
          "region": { "type": "string", "minLength": 1, "maxLength": 64 },
          "routing_group": { "type": "string", "maxLength": 64 },
          "carrier_profile_ids": {
            "type": "array",
            "minItems": 1,
            "maxItems": 16,
            "items": { "type": "string", "minLength": 1, "maxLength": 128 }
          },
          "priority": { "type": "integer", "minimum": 0, "maximum": 1000 },
          "weight": { "type": "integer", "minimum": 1, "maximum": 1000 },
          "tags": {
            "type": "array",
            "maxItems": 32,
            "items": { "type": "string", "minLength": 1, "maxLength": 64 }
          }
        }
      }
    },
    "routing": {
      "type": "object",
      "additionalProperties": false,
      "required": ["selection_mode", "failover_mode"],
      "properties": {
        "selection_mode": { "type": "string", "enum": ["latency_weighted", "priority_first", "sticky_region"] },
        "failover_mode": { "type": "string", "enum": ["same_region_then_global", "global", "strict_region"] }
      }
    },
    "retry_policy": {
      "type": "object",
      "additionalProperties": false,
      "required": ["connect_attempts", "initial_backoff_ms", "max_backoff_ms"],
      "properties": {
        "connect_attempts": { "type": "integer", "minimum": 1, "maximum": 16 },
        "initial_backoff_ms": { "type": "integer", "minimum": 50, "maximum": 60000 },
        "max_backoff_ms": { "type": "integer", "minimum": 50, "maximum": 600000 }
      }
    },
    "telemetry": {
      "type": "object",
      "additionalProperties": false,
      "required": ["allow_client_reports", "sample_rate"],
      "properties": {
        "allow_client_reports": { "type": "boolean" },
        "sample_rate": { "type": "number", "minimum": 0.0, "maximum": 1.0 }
      }
    },
    "signature": {
      "type": "object",
      "additionalProperties": false,
      "required": ["alg", "key_id", "value"],
      "properties": {
        "alg": { "type": "string", "enum": ["EdDSA"] },
        "key_id": { "type": "string", "minLength": 1, "maxLength": 128 },
        "value": { "type": "string", "minLength": 32, "maxLength": 8192 }
      }
    }
  }
}
```

### 15.2 Manifest signature rules

For v0.1 reference clients:

- the manifest MUST be signed
- `signature.alg` MUST equal `EdDSA`
- `signature.key_id` MUST correspond to a currently trusted public key
- the client MUST verify the manifest signature before trusting:
  - endpoints
  - carrier profiles
  - token service metadata
  - client constraints

### 15.3 Manifest freshness rules

Clients MUST reject a manifest if:

- current time is later than `expires_at`, unless a local grace mode is explicitly enabled for emergency offline behavior
- `schema_version != 1`
- signature verification fails
- no usable endpoint/carrier profile remains after validation

Clients SHOULD cache the last known-good manifest and use conditional fetch with `ETag` when available.

---

## 16. Reference session-token verification profile

The wire protocol treats `Token` as opaque bytes.  
For the **reference bridge and gateway stack**, this document freezes the **bridge/API profile** below.

### 16.1 Token container

The v0.1 reference token MUST be a compact JWS/JWT string signed with:

- `alg = EdDSA`
- key type: `OKP`
- curve: `Ed25519`

The token is carried over bridge APIs as UTF-8 text and over the session wire as opaque bytes.

### 16.2 Required JOSE header members

- `alg`
- `kid`
- `typ` SHOULD equal `JWT`

### 16.3 Required JWT claims

| Claim | Type | Meaning |
|---|---|---|
| `iss` | string | bridge issuer id |
| `aud` | string or array | MUST include `northstar-gateway` |
| `sub` | string | account or device subject |
| `jti` | string | unique token id |
| `iat` | integer | issued-at |
| `nbf` | integer | not-before |
| `exp` | integer | expiry |
| `device_id` | string | device binding identifier |
| `manifest_id` | string | manifest version the token was minted against |
| `policy_epoch` | integer | effective policy epoch |
| `core_versions` | array[int] | allowed session core versions |
| `carrier_profiles` | array[string] | allowed carrier profiles |
| `capabilities` | array[int] | allowed capabilities |
| `session_modes` | array[string] | allowed modes, e.g. `["tcp","udp"]` |

### 16.4 Optional JWT claims

| Claim | Meaning |
|---|---|
| `region_scope` | allowed region or endpoint group |
| `max_relay_streams` | tighter cap than manifest default |
| `max_udp_flows` | tighter cap than manifest default |
| `max_udp_payload` | tighter cap than manifest default |
| `telemetry_profile` | bridge-selected telemetry policy |
| `trace_sampling` | sampled diagnostics hint |

### 16.5 Verification rules at the gateway

The gateway MUST verify:

1. signature validity
2. `kid` resolves to a trusted active or overlapping rotation key
3. `iss` is trusted
4. `aud` contains `northstar-gateway`
5. current time is within `nbf..exp` using bounded skew tolerance
6. requested core version is included in `core_versions`
7. requested `CarrierProfileId` is allowed
8. requested capabilities are a subset of `capabilities`
9. `device_id` matches `DeviceBindingId` when device binding is required
10. `manifest_id` matches the hello value or an explicitly allowed replacement rule

### 16.6 Clock skew

Recommended default skew tolerance: **±120 seconds**.  
Implementations MUST make this configurable.

### 16.7 Replay strategy

v0.1 recommendation:

- soft replay detection keyed by `jti + device_id`
- short session-token TTL (`300 s` recommended)
- logging and optional adaptive rate-limit on suspicious concurrent reuse

Hard single-use tokens are deferred.

### 16.8 JWKS publication

The bridge MUST publish verification keys at:

- `GET /.well-known/jwks.json`

Key rotation requirements:

- support overlapping old/new keys during rollout
- never remove an old verification key before all unexpired tokens signed by it have aged out

---

## 17. Bridge public API freeze candidate

### 17.1 OpenAPI draft

```yaml
openapi: 3.1.0
info:
  title: Northstar Bridge Public API
  version: "0.1.0"
servers:
  - url: https://bridge.example.net
paths:
  /v0/device/register:
    post:
      summary: Register device metadata and optionally mint a device-bound refresh credential
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              additionalProperties: false
              required: [device_id, platform, client_version]
              properties:
                device_id: { type: string, minLength: 1, maxLength: 128 }
                device_name: { type: string, maxLength: 128 }
                platform: { type: string, minLength: 1, maxLength: 64 }
                client_version: { type: string, minLength: 1, maxLength: 32 }
                install_channel: { type: string, maxLength: 32 }
                requested_capabilities:
                  type: array
                  items: { type: integer, minimum: 1, maximum: 65535 }
      responses:
        "200":
          description: Device accepted
          content:
            application/json:
              schema:
                type: object
                additionalProperties: false
                required: [device_id, binding_required]
                properties:
                  device_id: { type: string }
                  binding_required: { type: boolean }
                  refresh_credential: { type: string }
                  warnings:
                    type: array
                    items: { type: string }
  /v0/manifest:
    get:
      summary: Fetch the signed manifest
      parameters:
        - in: header
          name: Authorization
          required: false
          schema: { type: string }
        - in: query
          name: subscription_token
          required: false
          schema: { type: string, maxLength: 4096 }
        - in: header
          name: If-None-Match
          required: false
          schema: { type: string }
      responses:
        "200":
          description: Signed manifest
          headers:
            ETag:
              schema: { type: string }
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Manifest'
        "304":
          description: Not modified
  /v0/token/exchange:
    post:
      summary: Exchange refresh/bootstrap credential for short-lived session token
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              additionalProperties: false
              required:
                [manifest_id, device_id, client_version, core_version, carrier_profile_id, requested_capabilities, refresh_credential]
              properties:
                manifest_id: { type: string, minLength: 8, maxLength: 256 }
                device_id: { type: string, minLength: 1, maxLength: 128 }
                client_version: { type: string, minLength: 1, maxLength: 32 }
                core_version: { type: integer, minimum: 1, maximum: 65535 }
                carrier_profile_id: { type: string, minLength: 1, maxLength: 128 }
                requested_capabilities:
                  type: array
                  minItems: 1
                  maxItems: 32
                  items: { type: integer, minimum: 1, maximum: 65535 }
                refresh_credential: { type: string, minLength: 1, maxLength: 4096 }
      responses:
        "200":
          description: Token minted
          content:
            application/json:
              schema:
                type: object
                additionalProperties: false
                required: [session_token, expires_at, policy_epoch]
                properties:
                  session_token: { type: string, minLength: 32, maxLength: 8192 }
                  expires_at: { type: string, format: date-time }
                  policy_epoch: { type: integer, minimum: 0, maximum: 4294967295 }
                  recommended_endpoints:
                    type: array
                    items: { type: string }
                  profile_overrides:
                    type: array
                    items:
                      type: object
                      additionalProperties: true
                  warnings:
                    type: array
                    items: { type: string }
  /v0/network/report:
    post:
      summary: Submit sampled client network telemetry
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              additionalProperties: false
              required: [manifest_id, device_id, client_version, sample]
              properties:
                manifest_id: { type: string }
                device_id: { type: string }
                client_version: { type: string }
                sample:
                  type: object
                  additionalProperties: false
                  required: [timestamp, endpoint_id, carrier_profile_id]
                  properties:
                    timestamp: { type: string, format: date-time }
                    endpoint_id: { type: string }
                    carrier_profile_id: { type: string }
                    rtt_ms: { type: integer, minimum: 0, maximum: 600000 }
                    connect_ms: { type: integer, minimum: 0, maximum: 600000 }
                    datagram_success_ratio: { type: number, minimum: 0.0, maximum: 1.0 }
                    network_type: { type: string, maxLength: 32 }
      responses:
        "204":
          description: Accepted
  /.well-known/jwks.json:
    get:
      summary: Publish current verification keys
      responses:
        "200":
          description: JWKS document
          content:
            application/json:
              schema:
                type: object
                additionalProperties: false
                required: [keys]
                properties:
                  keys:
                    type: array
                    items:
                      type: object
                      additionalProperties: true
components:
  schemas:
    Manifest:
      type: object
      additionalProperties: true
```

### 17.2 Bridge public API rules

- all bridge public endpoints MUST be served over HTTPS
- public client endpoints MUST be logically isolated from operator/admin APIs
- token issuance MUST be rate-limited
- device registration and token exchange MUST emit audit events
- manifest fetch SHOULD support `ETag`
- bridge responses SHOULD avoid leaking internal control-plane structure

### 17.3 Remnawave-facing adapter boundary

This document freezes the **Northstar public bridge API**, not the internals of how the bridge talks to the external control plane.

That adapter MAY use:

- polling
- webhooks
- signed export feeds
- internal API adapters

The public bridge API MUST remain stable even if the control-plane ingestion strategy changes.

---

## 18. Conformance and interoperability test set

The v0.1 reference test plan MUST include at least the following cases.

### 18.1 Hello and session establishment

| Test ID | Description |
|---|---|
| `T-HELLO-001` | accept `NS-FX-HELLO-001` and produce compatible `SERVER_HELLO` |
| `T-HELLO-002` | reject `MinVersion > MaxVersion` |
| `T-HELLO-003` | reject unknown `CarrierKind` |
| `T-HELLO-004` | reject empty token |
| `T-HELLO-005` | reject capability selected by server if not requested by client |
| `T-HELLO-006` | reject non-canonical varint in hello |

### 18.2 Frame parsing

| Test ID | Description |
|---|---|
| `T-FRAME-001` | reject truncated frame envelope |
| `T-FRAME-002` | reject declared length longer than actual bytes |
| `T-FRAME-003` | reject payload above hard ceiling |
| `T-FRAME-004` | reject illegal frame before hello completes |
| `T-FRAME-005` | ignore unknown TLV in metadata bag |

### 18.3 Relay streams

| Test ID | Description |
|---|---|
| `T-STREAM-001` | open `STREAM_OPEN` → accept → switch to raw bytes |
| `T-STREAM-002` | reject duplicate active `RelayId` |
| `T-STREAM-003` | reject reserved `OpenFlags` bits |
| `T-STREAM-004` | reject invalid target encoding length for ipv4/ipv6 |
| `T-STREAM-005` | verify half-close propagation where runtime supports it |

### 18.4 UDP flows

| Test ID | Description |
|---|---|
| `T-UDP-001` | `UDP_FLOW_OPEN` + datagram mode success |
| `T-UDP-002` | datagram unavailable → fallback stream success |
| `T-UDP-003` | reject duplicate active `FlowId` |
| `T-UDP-004` | reject oversized datagram payload |
| `T-UDP-005` | reject reserved `FlowFlags` bits |

### 18.5 Auth and policy

| Test ID | Description |
|---|---|
| `T-AUTH-001` | reject expired token |
| `T-AUTH-002` | reject token with wrong audience |
| `T-AUTH-003` | reject token whose `device_id` mismatches hello |
| `T-AUTH-004` | reject hello with carrier profile not allowed by token |
| `T-AUTH-005` | accept bounded clock skew within configured window |

### 18.6 Bridge and manifest

| Test ID | Description |
|---|---|
| `T-MAN-001` | verify manifest signature success |
| `T-MAN-002` | reject tampered manifest |
| `T-MAN-003` | reject unsupported manifest schema version |
| `T-BRIDGE-001` | token exchange returns token and policy epoch |
| `T-BRIDGE-002` | JWKS key rotation overlap works correctly |

### 18.7 Fuzzing minimum

The reference implementation MUST have fuzz targets for:

- varint decoder
- frame envelope decoder
- TLV parser
- `CLIENT_HELLO` parser
- `SERVER_HELLO` parser
- `STREAM_OPEN` parser
- `UDP_FLOW_OPEN` parser
- manifest JSON parser and validator
- JWT/JWKS validation boundary code

---

## 19. Crate-level implementation boundaries

This section exists so AI coding agents and human contributors do not blur responsibilities.

### 19.1 `northstar-wire`

Owns:

- varint encoding/decoding
- frame structs
- parser/serializer
- registries and enums
- fixture decoders

Must NOT own:

- networking
- TLS/QUIC
- bridge HTTP logic

### 19.2 `northstar-session`

Owns:

- session state machine
- control stream dispatch
- relay/flow table bookkeeping
- sequencing rules
- policy application

Must NOT own:

- QUIC/H3 primitives directly
- JWT verification details
- manifest download

### 19.3 `northstar-carrier-h3`

Owns:

- H3 tunnel creation
- control stream binding
- relay stream binding
- datagram mapping
- carrier-specific error translation

### 19.4 `northstar-auth`

Owns:

- JWT verification profile
- JWKS refresh/cache
- device binding checks
- replay detection hooks

### 19.5 `northstar-bridge-api`

Owns:

- public HTTP server/client models for `/v0/*`
- OpenAPI-aligned request/response types
- manifest signing helpers

### 19.6 `northstar-manifest`

Owns:

- manifest schema validation
- signature verification
- manifest caching and conditional fetch logic

### 19.7 `northstar-gateway`

Owns:

- socket outbound connects
- policy enforcement
- resource limits
- telemetry emission

### 19.8 `northstar-client`

Owns:

- manifest fetch
- token exchange
- endpoint/profile selection
- network-change observation
- Windows-first packaging and logs

---

## 20. Change-control rules after this freeze

### 20.1 Any change touching these items requires explicit compatibility review

- frame ids
- frame field order
- fixed-size field lengths
- error-code meanings
- token claim names required by the gateway
- bridge endpoint paths under `/v0`

### 20.2 Preferred evolution path

The preferred evolution path is:

1. add a new optional capability or TLV
2. ship behind manifest/bridge feature flags
3. add tests and fixtures
4. graduate into the next freeze candidate or stable spec

### 20.3 Breaking-change escape hatch

If a breaking change is unavoidable:

- increment session core version
- keep old parser for one compatibility window if feasible
- add explicit manifest constraints to prevent mismatched client/server combinations
- document migration steps

---

## 21. Open items intentionally deferred past v0.1

These are visible here so they stay on the radar, but they are not frozen:

- session resumption ticket format
- 0-RTT data policy
- multipath and path aggregation
- custom congestion controllers
- IP tunnel mode and `CONNECT-IP`-style carrier mapping
- extension-frame negotiation model
- post-quantum hybrid key-agreement experiments
- richer telemetry taxonomy
- client-side local policy engine
- cover traffic or decoy scheduling systems

---

## 22. Definition of done for this freeze candidate

This document can be considered successfully adopted when:

1. client and gateway can interoperate using the frozen hello, stream, and UDP formats
2. manifest validation passes against schema version `1`
3. bridge token exchange implements the public `/v0/token/exchange` contract
4. gateway validates JWT/JWKS according to Section 16
5. all fixture decoders pass
6. conformance tests in Section 18 are automated in CI
7. fuzz targets exist for all parsers listed in Section 18.7

---

## 23. Final implementation guidance

Northstar v0.1 should be built with discipline:

- keep the session core smaller than the transport ambitions around it
- keep the wire contract boring and explicit
- push changeability into manifests, carrier profiles, and rollout policy
- prefer one stable interpretation of every field
- treat fixtures and schemas as executable truth, not decorative docs

That is how the project stays adaptable without becoming unmaintainable.
