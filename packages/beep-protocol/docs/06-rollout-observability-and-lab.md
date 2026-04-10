# Rollout, Observability, and Lab Plan

## Why this matters

`Beep` is viable only if transport behavior can evolve faster than binary release cycles. That requires:

- signed artifact rollout,
- profile-specific telemetry,
- deterministic rollback,
- a permanent validation environment.

Without these, transport agility becomes a slogan.

## Rollout model

### Unit of rollout

The control plane should roll out these units independently:

- `session_core_version`
- `transport_profile`
- `presentation_profile`
- `policy_bundle`
- `probe_recipe`

### Stages

Recommended rollout stages:

1. `lab`
2. `internal`
3. `canary`
4. `regional`
5. `global`

Every stage should have a clear promote and rollback rule.

### Rollback triggers

Automatic rollback should trigger on:

- handshake success collapse,
- session-open failure spike,
- median RTT regression beyond threshold,
- CPU per active session regression,
- packet loss increase beyond threshold,
- crash loops or memory growth in node runtime.

## Metrics model

Metrics must be keyed by:

- transport profile ID,
- presentation profile ID,
- session core version,
- client platform,
- node region,
- ASN or network class,
- rollout cohort.

### Minimum required metrics

- outer connect success rate
- session open success rate
- session duration
- resumption hit rate
- median RTT and p95 RTT
- packet loss estimate
- bytes per session
- CPU per active session
- memory per active session
- rekey success rate
- error code distribution

## Event tracing

The system needs two levels of observability.

### Fleet metrics

Cheap counters and histograms for continuous operation.

### Session traces

Structured, opt-in traces for:

- canaries,
- debug sessions,
- benchmark runs,
- replay failures.

The format should be qlog-like in spirit:

- event name,
- timestamp,
- session ID,
- profile IDs,
- key transport and protocol state transitions,
- compact numeric fields rather than verbose strings where possible.

## Benchmark matrix

Every profile change should be tested against a fixed matrix.

| Scenario | cover_h2 | cover_h3 | native_fast |
| --- | --- | --- | --- |
| clean low-latency path | yes | yes | yes |
| high-loss mobile path | yes | yes | yes |
| UDP blocked | yes | yes, expect fail | optional |
| NAT rebinding / network change | partial | yes | optional |
| MTU cliff | yes | yes | yes |
| long-lived session 60 min | yes | yes | yes |
| churn: many short sessions | yes | yes | yes |
| 1 Gbps throughput | yes | yes | yes |

Each matrix run should record:

- throughput,
- tail latency,
- CPU,
- memory,
- reconnect rate,
- success rate,
- rekey behavior.

## Beep Lab

`Beep Lab` is a permanent subsystem, not a one-time project.

### Test groups

1. Standards interoperability
2. Adverse path simulation
3. Performance regression
4. Replay of previously observed failures

### Adverse path catalog

The lab should simulate:

- UDP unavailable,
- UDP throttled,
- packet loss bursts,
- asymmetric paths,
- NAT rebinding,
- captive portal interference,
- aggressive idle timeouts,
- TLS middleboxes,
- MTU fragmentation cliffs,
- connection churn at scale.

### Replay harness

Replay should be possible from:

- captured artifact set,
- recorded network context,
- trace token,
- selected profile IDs,
- representative packet/event stream.

This is how rollout bugs become fixable instead of anecdotal.

## Operating rules

- never ship a new profile directly to global;
- never reuse a revoked artifact ID;
- always keep the last known good profile per cohort;
- always retain one compatibility path that does not depend on UDP;
- require benchmark evidence before promoting a transport family change.

## Release phases for Beep

### Phase A. Freeze the core ABI

Deliverables:

- session core frame schema,
- artifact schema,
- error code registry.

### Phase B. Ship `cover_h2`

Deliverables:

- client and node runtime over H2,
- full tunnel support,
- rollout hooks,
- baseline metrics.

### Phase C. Ship `cover_h3`

Deliverables:

- MASQUE-compatible H3 path,
- datagram carriage,
- profile scoring integration,
- H2/H3 comparative benchmarks.

### Phase D. Activate independent artifacts

Deliverables:

- signed `transport_profile`,
- signed `presentation_profile`,
- signed `policy_bundle`,
- signed `probe_recipe`.

### Phase E. Mature the lab

Deliverables:

- nightly matrix,
- replay runner,
- adverse-path simulation,
- promotion gates tied to evidence.

### Phase F. Optimize runtime efficiency

Deliverables:

- buffer pools,
- per-core sharding,
- batched I/O,
- QUIC socket tuning,
- H2/H3 cost comparisons.

### Phase G. Research branch

Candidates:

- alternate H3 provider path,
- experimental outer presentation control,
- multipath prototypes,
- additional PQ modes,
- module/plugin system for future transport experiments.

None of these should be dependencies for the first production release.

## Exit criteria for v1

`Beep v1` is ready only when:

- H2 and H3 paths both work end to end,
- rollback can disable a bad profile without client redeploy,
- trace-driven replay can reproduce a rollout regression,
- session core rekey and resumption are stable,
- benchmark evidence exists for all three profile families.

