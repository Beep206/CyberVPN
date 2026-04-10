# Beep Transport Profiles

## Why transport profiles exist

`Beep` should never ship with one global transport assumption. Different networks prefer different failure modes:

- some paths block or degrade UDP,
- some paths dislike large handshake flights,
- some paths reward QUIC migration and datagrams,
- some environments care more about throughput and CPU than maximum compatibility.

The answer is a profile system, not a single default transport.

## Profile taxonomy

`Beep` uses three profile classes:

### 1. `cover_h2`

HTTP/2 Extended CONNECT over TLS/TCP on 443.

Use when:

- UDP is unavailable or unstable,
- middleboxes strongly prefer TCP,
- consistent enterprise compatibility matters more than raw transport features.

Strengths:

- broad deployability,
- mature TCP/TLS behavior,
- simpler operational path on restrictive networks.

Tradeoffs:

- no native QUIC datagrams,
- higher risk of nested recovery if proxying already-reliable inner traffic carelessly,
- less graceful handling of mobility than QUIC-based transports.

### 2. `cover_h3`

HTTP/3 over QUIC using MASQUE building blocks such as CONNECT-IP, CONNECT-UDP, and HTTP Datagrams.

Use when:

- the path supports UDP well,
- mobility and datagrams matter,
- low-latency session establishment is valuable,
- the node fleet is tuned for QUIC.

Strengths:

- standardized tunneling semantics,
- better fit for datagram-heavy traffic,
- better recovery from head-of-line effects than TCP-based carriage.

Tradeoffs:

- stronger dependence on UDP path quality,
- more sensitivity to socket tuning and offloads,
- transport behavior depends more heavily on host and kernel characteristics.

### 3. `native_fast`

A lower-overhead mode for friendly networks.

Use when:

- the client and node both mark the network as low-risk and high-quality,
- throughput and CPU efficiency are prioritized,
- strict HTTP cover semantics are not required.

This profile still uses the same session core. The difference is the outer transport and the policy posture.

## Profile selection policy

The client should rank profiles using measured evidence, not static preference.

Minimum inputs:

- UDP reachability,
- handshake success rate,
- recent RTT and jitter,
- packet loss,
- MTU behavior,
- prior session survival time,
- current policy overrides.

Recommended selection order:

1. try the last good profile for the same network class;
2. if unknown network, start with `cover_h3` if UDP probes pass;
3. fall back to `cover_h2` if UDP is weak or failed recently;
4. use `native_fast` only for explicitly qualified friendly paths.

Profile selection should be sticky for a bounded time window to avoid churn.

## Signed artifacts

The transport system uses three independent artifacts.

### `transport_profile`

Defines:

- transport family,
- required capabilities,
- connect timeout,
- idle timeout,
- keepalive cadence,
- stream/datagram availability,
- migration policy,
- MTU hints.

### `presentation_profile`

Defines:

- TLS provider family,
- ALPN list,
- H2 settings or H3 behavior knobs,
- retry posture,
- idle behavior,
- resumption posture.

For `v1`, this should remain standards-compliant and conservative. Do not make exact browser impersonation the default engineering burden.

### `policy_bundle`

Defines:

- candidate profile list,
- ordering rules,
- rollout cohort,
- retry ladder,
- backoff,
- failure thresholds,
- telemetry budget.

## Example artifact

```toml
[transport_profile]
id = "h3-global-stable"
family = "cover_h3"
session_core_version = "1"
connect_timeout_ms = 3500
idle_timeout_ms = 45000
keepalive_ms = 15000
supports_streams = true
supports_datagrams = true
allows_migration = true

[presentation_profile]
id = "h3-standard-1"
alpn = ["h3"]
tls_provider = "default"
ech_mode = "opportunistic"
retry_mode = "standard"

[policy_bundle]
id = "default-eurasia"
candidates = ["h3-global-stable", "h2-global-stable"]
max_failures_before_switch = 2
sticky_ttl_seconds = 21600
telemetry_budget = "normal"
```

## ECH policy

ECH is worth supporting, but the protocol must not depend on universal ECH availability.

Rules for `Beep`:

- `ech_mode = opportunistic` is the sensible default;
- never require ECH to make a profile viable;
- treat ECH failure as a path signal, not as proof that the entire transport family is unusable;
- keep ECH decisions inside the `presentation_profile`, not the session core.

## PQ policy

Default rule:

- do not force large post-quantum outer `ClientHello` flights across every profile by default.

Instead:

- keep hybrid KEM negotiation inside the inner session core;
- enable outer PQ only on profiles and paths that have been qualified;
- stage rollout by cohort because larger handshake flights can stress middleboxes and MTU behavior.

## Node-side switching

Nodes must support atomic activation of new profiles.

That means:

- new listeners can be started before old ones are drained;
- profile revocation can happen without process restarts where possible;
- failures must be reportable by profile ID, not only by generic protocol family.

## Recommended v1 matrix

| Profile | Role in product | Required in v1 |
| --- | --- | --- |
| `cover_h2` | compatibility baseline | yes |
| `cover_h3` | performance baseline | yes |
| `native_fast` | friendly-network optimization | yes, but can start behind a flag |
| advanced presentation control | optional edge capability | no |
| multipath | future work | no |

## Hard rules

- Do not make `cover_h3` the only supported production path.
- Do not tie artifact semantics to a specific Rust TLS library.
- Do not hide policy in code branches that cannot be rolled back independently.
- Do not ship profile logic that cannot report profile-specific outcomes.

