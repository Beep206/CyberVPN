# Verta v0.1 Performance Budgets

## Purpose

This document defines the first implementation baseline for Verta performance engineering.
It is intentionally conservative.
The goal is to make resource limits, queue bounds, and benchmark scope explicit before optimization work starts.

## Status Note

Historical milestone notes below still mention the planned `.github/workflows/udp-optional-gates.yml`.
The active sustained verification path is now the real `Phase K` workflow set:

- `.github/workflows/verta-udp-bounded-verification.yml`
- `.github/workflows/verta-udp-scheduled-verification.yml`
- `.github/workflows/verta-udp-release-evidence.yml`

The active required-check and artifact-retention policy lives in `docs/development/SUSTAINED_VERIFICATION_GATES.md`.

This baseline is grounded in:

- `docs/spec/verta_implementation_spec_rust_workspace_plan_v0_1.md`
  - section 13.3, Channels and backpressure
  - section 17, Observability implementation rules
  - section 18.3, Resource budget discipline
  - section 26, Benchmarking and performance engineering plan
- `docs/spec/verta_blueprint_v0.md`
  - section 27, Observability blueprint
  - section 28.3, Backpressure and memory discipline
  - section 30, Performance laboratory plan embedded into v0
- `docs/spec/verta_wire_format_freeze_candidate_v0_1.md`
  - section 6.6, Maximum lengths and counts
  - section 10.3, Recommended default timers
- `docs/spec/verta_threat_model_v0_1.md`
  - TM-DS-02, token exchange flood
  - TM-DS-03, gateway handshake flood
  - section 13.8, Privacy and observability threats

If implementation pressure conflicts with these budgets, the fix is to make the tradeoff explicit and measured rather than silently adding unbounded buffering or relaxed limits.

## Baseline Principles

- Pre-auth work must stay cheap, bounded, and observable.
- Queue sizes must be explicit and tied to resource limits.
- Per-session and per-connection budgets must exist in code, not only in docs.
- The first benchmarks must answer practical questions about codec cost, auth cost, and admission behavior, not chase vanity throughput.
- Performance work must preserve security posture, privacy redaction, and transport-agnostic session boundaries.

## Scope of This Baseline

These budgets apply to the first serious Rust baseline:

- `ns-wire`
- `ns-auth`
- `ns-manifest`
- `ns-session`
- `ns-bridge-domain`
- `ns-remnawave-adapter`
- `ns-carrier-h3`
- `ns-client-runtime`
- `ns-gateway-runtime`
- `ns-observability`
- app startup and dry-run validation paths

They do not yet claim production-grade tuning for:

- long-duration soak performance
- full WAN benchmarking matrix
- large-scale bridge fan-out
- carrier migration optimization
- qlog-heavy diagnostics in production

## Hard Ceilings from the Freeze Candidate

The wire freeze candidate already sets hard limits that the implementation must treat as non-negotiable ceilings for v0.1:

| Item | Hard ceiling |
|---|---:|
| Control frame payload | 65535 bytes |
| Relay preamble payload | 4096 bytes |
| Token field length | 4096 bytes |
| Generic string field unless overridden | 1024 bytes |
| Domain target host | 255 bytes |
| Carrier profile id | 128 bytes |
| Manifest id | 256 bytes |
| Device binding id | 128 bytes |
| Metadata TLV count per frame | 16 |
| One TLV value length | 2048 bytes |
| Requested capabilities count | 64 |
| Selected capabilities count | 64 |
| Advertised concurrent relay streams | 65535 |
| Advertised concurrent UDP flows | 65535 |

The first implementation baseline should normally enforce stricter effective limits than the protocol hard ceilings, especially on pre-auth paths.

## Initial Runtime Budgets

These are the first code-level budgets to implement and measure.
They are baseline defaults, not protocol invariants.
They may be tightened or adjusted after measurement, but they should not be silently relaxed.

### 1. Handshake and admission

| Budget | Baseline |
|---|---:|
| Client handshake timeout | 10 seconds |
| Ping response deadline | 10 seconds |
| Graceful drain deadline after `GOAWAY` | 30 seconds |
| Pre-auth wall-clock handling target per attempt | 250 ms steady-state target |
| Pre-auth absolute handling deadline per attempt | 1 second |
| Max concurrent unauthenticated handshakes per gateway worker or shard | explicit config, default 256 |
| Max malformed handshakes processed before local shedding is allowed | explicit rate-limited guard |

Notes:

- The 10 second handshake timeout comes from the freeze candidate default timers.
- The 250 ms target is a measurement target for healthy local conditions, not a wire guarantee.
- The 1 second absolute pre-auth deadline is a resource-defense budget; work that exceeds it should fail closed.
- Milestone 5 now implements `max_pending_hellos = 256`, `max_control_body_bytes = 16 KiB`, and `handshake_deadline_ms = 1000` as the default gateway pre-auth budgets in `ns-gateway-runtime`.

### 2. Session and stream state

| Budget | Baseline |
|---|---:|
| Default effective relay stream limit exposed in early test profiles | 64 |
| Default effective UDP flow limit exposed in early test profiles | 16 |
| Max pending stream-open operations per session before rejection or drain behavior | 32 |
| Max pending UDP-flow-open operations per session before rejection or drain behavior | 16 |
| Max live session state retained after terminal failure | bounded cleanup only, no deferred indefinite caches |

Notes:

- The `64` and `16` values align with the freeze candidate example `SERVER_HELLO`, making them good baseline test-profile defaults for the first implementation wave.
- The implementation may advertise other values per manifest or policy later, but benchmarks should start from stable, reviewable defaults.
- Milestone 6 now implements gateway-side accepted-relay budgets in `ns-gateway-runtime` with defaults of `max_active_relays = 256`, `max_relay_prebuffer_bytes = 64 KiB`, and `relay_idle_timeout_ms = 30_000`.
- Milestone 7 now exercises those accepted-relay budgets through the reusable `ns-carrier-h3` raw relay runtime instead of only through live-test-local forwarding code.
- Milestone 12 now implements the first explicit gateway datagram defaults in code with `max_udp_flows = 8`, `max_udp_payload = 1200`, and `DatagramMode` passed from runtime policy into admission instead of being inferred inside the carrier.
- Milestone 13 keeps those datagram limits unchanged, adds explicit local rollout controls in runtime and CLI composition with safe defaults of `disabled`, and keeps fallback fail closed unless the client explicitly allowed it.
- Milestone 14 keeps those datagram limits unchanged, adds staged local rollout with `canary`, and clarifies that the `8 KiB` queue budget currently applies to bounded outbound buffered datagrams in the first H3 runtime slice.
- Milestone 15 keeps those datagram limits unchanged, derives `SERVER_HELLO` UDP limits from effective policy instead of optimistic defaults, and adds explicit datagram burst ceilings of `max_buffered_datagrams = 8` and `max_buffered_datagrams_per_flow = 4` on top of the existing `8 KiB` buffered-byte budget.

### 3. Queue and backpressure discipline

| Queue or budget | Baseline |
|---|---:|
| Internal `mpsc` channels in hot paths | bounded only |
| Gateway pending hello queue | explicit config, default 256 |
| High-volume telemetry channel depth | 1024 max, sampling or drop accounting required |
| Per-session outbound control queue depth | 64 max |
| Per-stream buffered write budget | 256 KiB max before backpressure or close logic |
| Per-session aggregate buffered write budget | 2 MiB max before admission tightening or drops |
| Bridge signer queue depth | 256 max with depth metric and rejection accounting |
| Manifest refresh or webhook reconciliation work queue | 128 max with bounded retry policy |

Notes:

- These are intentionally conservative starting points.
- Any queue that can affect public ingress, token issuance, or gateway admission must expose depth and drop metrics.
- Any request path that needs a larger queue must carry a written justification and measurement result.
- The first shared bridge-store path may use SQLite on the bridge side, but that storage work must stay off the gateway pre-auth hot path.
- Milestone 6 now implements `BridgeHttpBudgets` in `ns-bridge-api` with defaults of `16 KiB` for JSON request bodies and `64 KiB` for verified webhook bodies so public bridge ingress stays visibly bounded.
- Milestone 7 keeps those body budgets route-scoped and requires a `SharedDurable` backend for public bridge serve mode so public ingress is not accidentally paired with local-only trust state.
- Milestone 8 adds a real HTTP-backed service-store path and requires a passing remote health check before the public bridge app can treat that backend as shared durable.
- Milestone 9 keeps the service-backed store path fail-closed and adds explicit internal auth plus request-timeout enforcement to that remote/shared backend path so multi-instance bridge coordination stays bounded under failure.
- Milestone 10 keeps remote/shared bridge-store auth mandatory at app-composition time, redacts internal `500` bodies on the store-service surface, and adds a deployment-shaped topology path where the public bridge runtime still health-checks the internal store service before serving traffic.
- Milestone 11 adds ordered fallback endpoints for the remote/shared service-backed store path, but keeps unauthorized primaries terminal instead of failover-eligible so auth drift does not get hidden by operator redundancy.
- Milestone 11 also adds explicit topology lifecycle coverage for startup, health, auth-failure, and shutdown so operator deployment posture is measured instead of assumed.

### 4. Memory discipline

| Budget | Baseline |
|---|---:|
| Heap allocations in wire decode hot paths | minimize per-frame transient allocation; benchmark and track |
| Extra retained metadata per session | only negotiated or operator-required values |
| Per-session memory budget target before carrier buffers | 64 KiB target |
| Per-stream memory budget target before payload buffering | 16 KiB target |
| Per-UDP-flow memory budget target before payload buffering | 8 KiB target |
| Crash diagnostics or failure memory on client | bounded local ring buffer only |

Notes:

- The blueprint requires bounded local failure memory and bounded buffering under slow-peer conditions.
- These values are first-baseline planning targets for review and benchmark scaffolding.
- They must be validated with actual measurements once the session tables and carrier glue compile.

### 5. Payload handling

| Budget | Baseline |
|---|---:|
| Default requested max UDP payload | 1200 bytes |
| Oversize UDP payload handling | reject or drop early according to policy |
| H3 datagram buffered queue budget | 8 KiB max before guard event and rejection |
| Unknown or malformed control frame over hard ceiling | reject with typed error, then close if required |
| Metadata TLV parsing | stop at configured max count and max value length |

Notes:

- `1200` aligns with the freeze candidate example and is a safe first benchmark payload size.
- Oversize datagrams must not trigger in-protocol fragmentation work.
- Milestone 12 now enforces `1200` as the first live H3 datagram payload ceiling and `8 KiB` as the first bounded datagram queue budget in `ns-carrier-h3`.
- Milestone 13 keeps those ceilings stable and adds deterministic live coverage for bounded datagram loss, payload oversize rejection, wrong-associated-stream rejection, and bounded queue-overflow visibility before any broader operator rollout.
- Milestone 15 keeps those payload ceilings stable and adds count-based burst rejection so small packets cannot evade the bounded datagram budget purely by staying under the byte ceiling.
- Milestone 17 keeps those payload ceilings stable and adds a maintained queue-full reject threshold to the UDP perf gate so one bounded saturation surface is tracked beyond benchmark buildability.

## Budget Assertions Required in Code

The following budget checks should exist as named constants, config defaults, or typed limit structures in code:

- handshake timeout
- pre-auth deadline
- max concurrent handshakes
- max control-body size before hello admission
- max control frame size
- max metadata count
- max string and token lengths
- per-session stream limit
- per-session UDP flow limit
- per-stream write budget
- per-session write budget
- per-stream relay prebuffer budget
- relay idle timeout budget
- bridge signer queue depth
- webhook or refresh worker queue depth
- bridge HTTP JSON body budget
- bridge webhook body budget
- bridge store-service request timeout
- bridge store-service auth failure visibility
- bridge store-service unauthorized failover suppression
- bridge topology startup health before public serve

If a subsystem cannot point to the code location that enforces its budget, the budget is not real yet.

## Metrics and Alerts Required for These Budgets

At minimum, the first baseline should expose:

- handshake attempts, success, and rejection counts
- handshake latency histogram
- token verification latency histogram
- manifest verification latency histogram
- active sessions, active streams, active UDP flows
- queue depth gauges for bridge signer and ingress-facing worker queues
- queue drop or shed counters
- gateway pending-hello queue depth, capacity, and shed counters
- stream-fallback usage counters
- datagram-mode selection, unavailable, and fallback-selection counters
- datagram success and datagram-I/O direction counters or events
- UDP payload oversize and datagram-buffer overflow counters
- oversize payload rejection counts
- rate-limit hit counts
- memory and queue pressure signals
- remote/shared store health and failure-kind visibility for primary and fallback endpoints

## First Benchmark Sequence

The first benchmark sequence should stay narrow and reproducible:

1. `ns-wire` decode and encode microbenchmarks for frozen fixtures.
2. `ns-auth` token verification cost for valid, expired, and invalid-signature tokens.
3. `ns-manifest` parse plus signature verification cost for realistic manifests.
4. `ns-session` admission-state benchmark with synthetic `CLIENT_HELLO` inputs and explicit stream or flow limits.
5. `ns-bridge-domain` token issuance path benchmark with bounded signer queue simulation.
6. `ns-carrier-h3` UDP datagram encode/decode and queue-guard microbenchmarks; milestone 14 now adds `cargo bench -p ns-carrier-h3 --bench datagram_runtime` as the first active carrier-side bench.

Milestone 15 additionally adds an opt-in threshold harness:

- `cargo run -p ns-testkit --example udp_perf_gate`

Milestone 16 additionally adds a repo-native optional workflow path for the same UDP smoke and perf gates:

- `.github/workflows/udp-optional-gates.yml`

Milestone 25 additionally keeps the same datagram budgets but makes rollout-facing comparison more reusable:

- `udp_rollout_validation_lab` now projects `selected_datagram_lifecycle_passed` so sticky datagram selection can be reviewed as a maintained summary fact instead of inferred from host-local logs
- `udp_rollout_validation_lab` now projects `queue_guard_limiting_path` so staged rollout review can identify the currently limiting queue-guard surface without comparing raw threshold timings by hand
- `udp_rollout_compare` now emits a stable reusable operator-verdict schema with explicit evidence-state, gate-state, and blocking-reason detail fields across maintained profiles
- `udp_rollout_matrix` now consumes compatible-host comparison summaries and produces a cross-host machine-readable verdict for staged rollout review without introducing host-specific runtime metrics

Milestone 26 additionally keeps the same datagram budgets but strengthens release-facing comparison discipline:

- `udp_rollout_validation_lab` now projects `longer_impairment_recovery_stable` so repeated bounded-loss recovery is reviewed as a maintained summary fact instead of inferred from one live test log
- maintained CLI validation outputs now expose `comparison_scope=surface` and `comparison_profile=validation_surface`, which keeps rollout tooling aligned with the same comparison vocabulary used by host-level and matrix-level verdict consumers
- the optional UDP workflow now includes a compatible-host macOS staged-rollout lane, so active-fuzz-backed staged evidence is no longer Linux-only for comparable host review

The gate uses wide ratio-based thresholds rather than machine-specific absolute timings:

- wrapped send-path cost must stay within `6x` baseline encode cost plus grace
- wrapped receive-path cost must stay within `6x` baseline decode cost plus grace
- oversize reject-path cost must stay within `3x` the bounded send-path cost plus grace

Milestone 27 additionally keeps the same datagram budgets but tightens reusable release-candidate rollout evidence:

- `udp_rollout_compare` and `udp_rollout_matrix` now share explicit `all_required_inputs_present` and `all_required_inputs_passed` facts on operator-verdict schema version `6`, so host-level and matrix-level rollout decisions consume the same required-input semantics
- the optional UDP workflow now includes a workflow-backed Linux staged-rollout matrix lane, so staged Linux and macOS evidence can be compared without introducing host-specific perf artifacts
- reviewed malformed `UDP_FLOW_OK` and UDP fallback-packet seeds now flow through conformance, corpus sync, and regression paths, which keeps the maintained perf and fuzz lanes aligned with the same rejection envelope

The default run uses `25_000` iterations per case and can be tuned with `VERTA_UDP_PERF_GATE_ITERATIONS` during the rename window; the legacy `VERTA_UDP_PERF_GATE_ITERATIONS` alias remains accepted.

Milestone 16 keeps queue and burst saturation regression coverage deterministic rather than time-based:

- burst and queue ceilings continue to use stable boundary assertions and structured guard events
- the maintained perf threshold remains the ratio-based send, receive, and oversize-reject harness

Milestone 17 keeps that deterministic posture and extends the maintained threshold surface with:

- `H3DatagramSocket.queue_full_reject`
- the same ratio-based harness style instead of absolute host-specific timing
- explicit workflow iterations through `VERTA_UDP_PERF_GATE_ITERATIONS=10000` on `.github/workflows/udp-optional-gates.yml`
- `cargo bench -p ns-carrier-h3 --bench datagram_runtime` remains the exploratory microbenchmark surface

Milestone 18 keeps that deterministic posture and extends the maintained threshold surface with:

- `decode_received_udp_datagram[1201-reject]`
- `H3DatagramSocket.session_burst_reject`
- `H3DatagramSocket.flow_burst_reject`
- the same ratio-based harness style instead of absolute host-specific timing
- a machine-readable UDP interoperability summary for operator review alongside the existing perf gate

Milestone 19 keeps that deterministic posture and extends the maintained rollout-facing perf surface with:

- a default machine-readable UDP perf summary at `target/verta/udp-perf-gate-summary.json`
- explicit optional workflow artifact upload for that summary on the Windows-first UDP gate path
- reviewed-corpus sync before compatible-host active fuzz so perf and fuzz runs stay aligned on the maintained seed set

Milestone 20 keeps that deterministic posture and extends the maintained rollout-facing perf surface with:

- `H3DatagramSocket.queue_recovery_send`
- a stable ratio-based threshold for the first successful post-drain datagram send after short queue saturation
- the same machine-readable summary surface instead of host-specific absolute timing claims
- compatible-host rollout-readiness workflow coverage that exercises the queue-recovery threshold alongside the maintained interop harness

Milestone 21 keeps that deterministic posture and extends the maintained rollout-facing surface with:

- a reusable `udp_rollout_validation_lab` summary at `target/verta/udp-rollout-validation-summary.json`
- repeated queue-pressure sticky-selection verification as a maintained rollout-readiness check rather than an ad-hoc one-off test
- a compatible-host Windows rollout-validation workflow lane that uploads the same summary shape instead of introducing a new host-specific artifact format

Milestone 22 keeps that deterministic posture and extends the maintained rollout-facing surface with:

- `H3DatagramSocket.repeated_queue_recovery_send`
- a stable threshold for repeated post-drain datagram recovery after queue saturation, not only the first recovery send
- `udp_rollout_validation_lab` pass/fail projection fields for fuzz smoke, perf thresholds, and the combined queue-saturation surface
- a compatible-host macOS rollout-readiness workflow lane that uploads the same summary family instead of introducing a host-specific perf artifact shape

Milestone 23 keeps that deterministic posture and extends the maintained rollout-facing surface with:

- a machine-readable staged-rollout comparison summary at `target/verta/udp-rollout-comparison-summary.json`
- normalized queue-saturation comparison fields in `udp_rollout_validation_lab`, specifically `queue_saturation_worst_case` and `queue_saturation_worst_utilization_pct`
- maintained sticky-selection and rollout-surface pass/fail facts that project from existing smoke, perf, interop, and rollout-validation summaries instead of host-specific raw timing claims
- a compatible-host Windows rollout-readiness workflow lane that uploads the same summary family, including the rollout-comparison verdict, instead of inventing a new host-specific perf artifact shape

Milestone 24 keeps that deterministic posture and extends the maintained rollout-facing surface with:

- normalized queue-guard headroom facts in `udp_rollout_validation_lab`, specifically `queue_guard_headroom_passed`, `queue_guard_headroom_band`, `queue_guard_rejection_path_passed`, `queue_guard_recovery_path_passed`, and `queue_guard_burst_path_passed`
- staged-rollout comparison semantics that treat active-fuzz as a first-class blocking input instead of a side-channel note
- stable blocking reasons such as `missing_active_fuzz_summary`, `active_fuzz_summary_failed`, `missing_queue_guard_headroom_surface`, `queue_guard_headroom_exhausted`, and `queue_guard_headroom_failed`
- the same machine-readable summary posture instead of host-specific raw timing claims, with `queue_guard_headroom_band` carrying the rollout-facing capacity verdict

This sequence matches the implementation spec priority order:

- codec throughput and allocation behavior
- token verification cost
- manifest verification and parse cost
- session engine overhead per stream or flow
- gateway admission latency under load

## Recommended First Bench Scaffold

Start with a crate-local microbenchmark in `crates/ns-wire/benches/frozen_fixtures.rs`.

Why this should go first:

- the wire format is already frozen enough to benchmark without guessing protocol behavior
- codec cost is on every client and gateway path
- it exposes allocation and malformed-input cost before carrier or runtime complexity obscures the results
- it is cross-platform and Windows-friendly, unlike heavier fuzz or network-lab setups

The first bench scaffold should measure:

- encode and decode of fixture-backed `CLIENT_HELLO`
- encode and decode of fixture-backed `SERVER_HELLO`
- encode and decode of `UDP_FLOW_OPEN` and `UDP_DATAGRAM`
- malformed-frame rejection cost for oversize length, invalid varint, duplicate or illegal values, and metadata-count overflow
- allocation count or allocated bytes per operation where the harness can capture it

The first bench scaffold should record:

- fixture id
- operation name
- payload size
- iteration count
- compiler version
- build profile
- mean and percentile timings if the harness supports them

The first scaffold should explicitly avoid:

- WAN simulation
- full carrier bring-up
- handshake end-to-end latency claims
- throughput marketing numbers

After the `ns-wire` bench is stable, the next two benches should be:

1. `crates/ns-auth/benches/token_verify.rs`
2. `crates/ns-manifest/benches/manifest_verify.rs`

## Explicit Non-Goals for the First Baseline

Do not spend the first benchmark wave on:

- peak localhost throughput charts
- transport tuning before codec and admission costs are visible
- speculative lock-free rewrites
- `unsafe` micro-optimizations
- full WAN simulation before baseline correctness and budgets are stable

## Review Checklist

Performance-sensitive changes should not merge unless reviewers can answer:

- Which explicit budget does this code path obey?
- Which queue is bounded, and what happens on saturation?
- Which metrics or spans will explain a regression here?
- Does this change keep pre-auth work cheap and bounded?
- Does this change preserve privacy-safe observability?
- Is the benchmark or measurement plan concrete enough to detect regressions?
