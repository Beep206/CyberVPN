# Helix Analysis Metrics

## Purpose

This document describes the full metric set used to analyze `Helix` as a desktop-first transport platform.

It is intentionally broader than release gates alone. For `Helix`, we do not decide quality from one headline number like throughput or connect time in isolation. We analyze:

- user-perceived performance;
- recovery and continuity behavior;
- stream scheduler and queue pressure;
- route quality and failover behavior;
- control-plane health and rollout policy posture;
- canary evidence and automatic reaction signals.

This file complements:

- `docs/helix/benchmarking.md`
- `docs/helix/slo-sla.md`
- `docs/testing/helix-benchmark-plan.md`

## Analysis Principles

When analyzing `Helix`, the preferred order of interpretation is:

1. verify whether users can connect and stay connected;
2. verify whether `Helix` is competitive against the current best baseline on the same target matrix;
3. verify whether recovery, continuity, and failover behavior stay inside acceptable bounds;
4. verify whether queue pressure, RTT drift, and stream fairness explain any regression;
5. verify whether control-plane policy, canary evidence, or automatic actuation indicates rollout risk.

In other words, `Helix` is judged as a system, not just as a tunnel.

## Metric Families

### 1. Primary Competitive Metrics

These are the first metrics used to judge whether `Helix` is actually competitive with `VLESS`, `XHTTP`, `sing-box`, or `xray` on the same environment.

| Metric | What it measures | Why it matters | Main source |
|---|---|---|---|
| `connect_success_rate` | Portion of attempts that establish a healthy transport and do not immediately fallback | Baseline requirement for viability | desktop runtime, adapter rollout summary |
| `median_connect_time_ms` | Median time from connect request to healthy runtime state | User-perceived startup responsiveness | benchmark reports |
| `p95_connect_time_ms` | Tail connect latency | Detects unstable or noisy startup under load or bad routes | benchmark reports |
| `median_first_byte_latency_ms` | Median time from stream open to first successful response byte | Stronger signal than connect time alone for real usage | desktop benchmark |
| `p95_first_byte_latency_ms` | Tail first-byte latency | Shows interactive pain under congestion or scheduler problems | desktop benchmark |
| `median_open_to_first_byte_gap_ms` | Median gap between logical stream open and first byte | Helps isolate scheduler or remote-path overhead after the transport is already connected | desktop benchmark |
| `p95_open_to_first_byte_gap_ms` | Tail open-to-first-byte gap | Important for detecting fairness regressions under many streams | desktop benchmark |
| `average_throughput_kbps` | Aggregate data transfer rate through the local proxy path | Measures real desktop runtime throughput, not synthetic raw socket speed | desktop benchmark |
| `relative_connect_latency_ratio` | Candidate connect latency relative to baseline | Makes comparisons meaningful across the same target matrix | comparison reports |
| `relative_first_byte_latency_ratio` | Candidate first-byte latency relative to baseline | Shows whether `Helix` is faster or slower in actual user traffic terms | comparison reports |
| `relative_open_to_first_byte_gap_ratio` | Candidate stream-gap ratio relative to baseline | Important for scheduler analysis | comparison reports |
| `relative_throughput_ratio` | Candidate throughput relative to baseline | Core competitiveness metric | comparison reports, canary evidence |

### 2. Recovery And Continuity Metrics

These metrics are used to understand how `Helix` behaves during reconnects, route degradation, and failover.

| Metric | What it measures | Why it matters | Main source |
|---|---|---|---|
| `ready_recovery_latency_ms` | Time until runtime becomes healthy again after controlled recovery action | Primary measure of visible recovery speed | recovery benchmark |
| `proxy_ready_latency_ms` | Time until the local proxy is usable again after recovery | Better reflects user impact than health-only timing | recovery benchmark |
| `proxy_ready_open_to_first_byte_gap_ms` | Stream-open to first-byte gap immediately after recovery | Helps distinguish fast health recovery from slow usable recovery | recovery benchmark |
| `continuity_success_rate` | Portion of observed continuity events that recover successfully | Core measure for session resumption quality | adapter rollout summary |
| `cross_route_recovery_rate` | Portion of continuity events that recover successfully across route changes | Shows whether failover preserves useful session semantics | adapter rollout summary |
| `continuity_observed_events` | Number of observed continuity cases | Prevents over-trusting tiny sample sizes | adapter rollout summary |
| `successful_continuity_recovers` | Count of successful same-session recoveries | Useful diagnostic for runtime tuning | sidecar health / telemetry |
| `failed_continuity_recovers` | Count of failed continuity recoveries | Failure pressure signal | sidecar health / telemetry |
| `last_continuity_recovery_ms` | Last measured continuity recovery latency | Fast debugging clue for recent regressions | sidecar health / telemetry |
| `successful_cross_route_recovers` | Count of successful cross-route recovery events | Important for path-change confidence | sidecar health / telemetry |
| `last_cross_route_recovery_ms` | Last measured cross-route recovery latency | Helps correlate route switches with user-visible impact | sidecar health / telemetry |
| `continuity_grace_active` | Whether sidecar is holding a continuity grace window before aggressive failover | Important for interpreting route behavior | sidecar health |
| `continuity_grace_remaining_ms` | Remaining grace time before continuity-preserving logic expires | Explains why failover did or did not happen yet | sidecar health |

### 3. Stream Scheduler And Queue Metrics

These metrics are used when performance is degraded but connect success is still good. They explain whether the protocol engine itself is causing pressure.

| Metric | What it measures | Why it matters | Main source |
|---|---|---|---|
| `frame_queue_depth` | Current outbound frame backlog | Direct signal of current pressure inside the transport | sidecar telemetry |
| `frame_queue_peak` | Peak observed outbound frame backlog | Detects burst or sustained queue overload | sidecar telemetry |
| `pending_open_streams` | Number of streams waiting to open | Indicates stream admission pressure | sidecar telemetry |
| `active_streams` | Number of active streams currently carried by the session | Required context for interpreting fairness | sidecar telemetry |
| `max_concurrent_streams` | Max observed concurrent streams during the sample | Shows how hard the runtime was pushed | sidecar telemetry |
| `recent_stream_peak_frame_queue_depth` | Worst queue depth seen in recent stream samples | Helps identify whether one stream or many are contributing | benchmark queue summary |
| `recent_stream_peak_inbound_queue_depth` | Peak inbound queue pressure in sampled streams | Useful for return-path fairness analysis | benchmark queue summary |
| `bytes_sent` | Total bytes sent during runtime | Baseline context for throughput and queue readings | sidecar health |
| `bytes_received` | Total bytes received during runtime | Baseline context for throughput and queue readings | sidecar health |

### 4. RTT And Route Quality Metrics

These metrics are used to explain why a route is selected, why a standby route is trusted, and why failover did or did not happen.

| Metric | What it measures | Why it matters | Main source |
|---|---|---|---|
| `active_route_probe_latency_ms` | Probe latency of the currently selected route | Startup route-selection quality signal | sidecar health |
| `active_route_score` | Policy score of the current route | Shows the combined quality evaluation, not just raw RTT | sidecar health |
| `standby_route_probe_latency_ms` | Probe latency of the warm standby route | Important for fast failover readiness | sidecar health |
| `standby_route_score` | Policy score of the standby route | Helps explain why a standby route is kept or replaced | sidecar health |
| `standby_ready` | Whether a standby route is already warmed and ready | Strong predictor of fast failover quality | sidecar health |
| `last_ping_rtt_ms` | Most recent ping RTT | Immediate route health indicator | sidecar health |
| `recent_rtt_p50_ms` | Median RTT from recent samples | Better than a single ping for trend reading | benchmark queue summary |
| `recent_rtt_p95_ms` | Tail RTT from recent samples | Useful for jitter and degradation analysis | benchmark queue summary |
| `active_route_failover_count` | Number of failovers from the active route | Route instability indicator | sidecar health |
| `active_route_healthy_observations` | Count of successful healthy checks | Helps separate short noise from sustained health | sidecar health |
| `active_route_quarantined` | Whether current route is under quarantine policy | Important to understand policy-driven avoidance | sidecar health |
| `active_route_quarantine_remaining_ms` | Remaining quarantine time | Indicates when a route may be re-admitted | sidecar health |
| `active_route_successful_activations` | Number of successful route activations | Historical trust signal | sidecar health |
| `active_route_failed_activations` | Number of failed route activations | Historical failure pressure signal | sidecar health |

### 5. Stability And Fallback Metrics

These metrics are used to decide whether `Helix` is safe enough to remain first-class in the desktop client.

| Metric | What it measures | Why it matters | Main source |
|---|---|---|---|
| `unexpected_disconnect_rate` | Portion of sessions that break without a user action or planned revoke | Core reliability metric | benchmarking / runtime events |
| `desktop_fallback_rate` | Portion of attempts or sessions that recover to a stable core | Strongest user-visible quality warning | benchmarking / adapter rollout summary |
| `time_to_recover_after_failure_ms` | Time from failure to a usable recovered state | Important for the felt severity of failures | benchmarking / recovery drills |
| `fallback_rate` | Rollout summary fallback rate seen in typed desktop evidence | Drives canary and policy posture | adapter rollout summary |

### 6. Control-Plane And Node Health Metrics

These metrics matter even when the transport engine is fast, because a premium protocol still fails if manifests, revoke, or node state are stale.

| Metric | What it measures | Why it matters | Main source |
|---|---|---|---|
| `manifest_resolve_p95_ms` | Tail latency of manifest resolution | Desktop startup cannot be considered healthy if control-plane is slow | benchmarking / SLO |
| `manifest_revoke_propagation_seconds` | Time for revoke or invalidate actions to propagate | Critical for safe emergency response | benchmarking / SLO |
| `heartbeat_freshness_seconds` | Freshness of node heartbeat data | Prevents acting on stale node state | benchmarking / SLO |
| `rollback_recovery_p95_seconds` | Tail time to restore last-known-good state | Required for operational safety | benchmarking / SLO |
| `failed_nodes` | Number of nodes currently failing in a rollout snapshot | Canary blast-radius indicator | canary snapshot |
| `rolled_back_nodes` | Number of nodes rolled back in a rollout snapshot | Operational instability indicator | canary snapshot |

### 7. Policy, Profile, And Automatic Reaction Metrics

These metrics are used to decide whether `Helix` should keep issuing a profile, suppress it, rotate it, or pause a rollout channel.

| Metric | What it measures | Why it matters | Main source |
|---|---|---|---|
| `policy_score` | Overall score of a selected transport profile | Condenses performance, continuity, and stability posture | selected profile policy |
| `observed_events` | Count of profile-observed events used for scoring | Prevents over-confidence from tiny samples | selected profile policy |
| `degraded` | Whether profile is in degraded state | Immediate policy warning | selected profile policy |
| `advisory_state` | Profile advisory class such as `healthy`, `watch`, `degraded`, `avoid-new-sessions` | Human-readable policy state | selected profile policy |
| `selection_eligible` | Whether profile is still eligible for selection | Explains control-plane choice behavior | selected profile policy |
| `new_session_issuable` | Whether new sessions should still receive this profile | Key issuance-safety gate | selected profile policy |
| `new_session_posture` | Preferred, guarded, or blocked posture for new sessions | Stronger signal than a plain boolean | selected profile policy |
| `suppression_active` | Whether profile suppression is currently active | Important for understanding why issuance changed | selected profile policy |
| `suppression_window_seconds` | Duration of the active suppression window | Helps interpret cooloff behavior | selected profile policy |
| `suppression_remaining_seconds` | Remaining suppression time | Useful for operations and debugging | selected profile policy |
| `healthy_candidate_count` | Number of healthy compatible profile candidates | Shows how much safe headroom exists | rollout policy summary |
| `eligible_candidate_count` | Number of eligible compatible profile candidates | Distinguishes compatibility from health | rollout policy summary |
| `suppressed_candidate_count` | Number of suppressed candidates | Indicates policy pressure | rollout policy summary |
| `active_profile_suppressed` | Whether currently active profile is suppressed | Strong sign of required action | rollout policy summary |
| `channel_posture` | Rollout-level posture from policy evaluation | High-level canary readiness signal | rollout policy summary |
| `automatic_reaction` | Recommended automatic reaction | Control-plane recommendation signal | rollout policy summary |
| `applied_automatic_reaction` | Reaction already applied in control-plane | Important for current rollout state | rollout policy summary |
| `recommended_action` | Human-readable next action | Helps admin and ops follow-up | rollout policy summary |

### 8. Formal Canary Evidence Metrics

These are the metrics most directly tied to `go`, `watch`, and `no-go` canary decisions.

| Metric | What it measures | Why it matters | Main source |
|---|---|---|---|
| `benchmark_observed_events` | Number of benchmark evidence events observed | Evidence confidence signal | canary snapshot |
| `throughput_evidence_observed_events` | Number of benchmark events that include valid throughput evidence | Prevents promoting with incomplete data | canary snapshot |
| `average_benchmark_throughput_kbps` | Average throughput across benchmark evidence | Baseline canary throughput summary | canary snapshot |
| `average_relative_throughput_ratio` | Mean throughput ratio against baseline | Main comparative canary metric | canary snapshot |
| `average_relative_open_to_first_byte_gap_ratio` | Mean gap ratio against baseline | Main scheduler-quality canary metric | canary snapshot |
| `min_relative_throughput_ratio` | Minimum acceptable throughput ratio | Hard canary guardrail | canary threshold summary |
| `max_relative_open_to_first_byte_gap_ratio` | Maximum acceptable gap ratio | Hard canary guardrail | canary threshold summary |
| `min_connect_success_rate` | Minimum acceptable connect success rate | Hard canary guardrail | canary threshold summary |
| `max_fallback_rate` | Maximum acceptable fallback rate | Hard canary guardrail | canary threshold summary |
| `min_continuity_success_rate` | Minimum acceptable continuity success rate | Hard canary guardrail | canary threshold summary |
| `min_cross_route_recovery_rate` | Minimum acceptable cross-route recovery rate | Hard canary guardrail | canary threshold summary |
| `require_throughput_evidence` | Whether throughput evidence is mandatory for the decision | Blocks premature promotion | canary threshold summary |

## Which Metrics Are Primary Vs Diagnostic

### Primary Decision Metrics

These directly influence whether `Helix` is considered healthy, competitive, or promotable:

- `connect_success_rate`
- `fallback_rate`
- `median_connect_time_ms`
- `p95_connect_time_ms`
- `median_first_byte_latency_ms`
- `p95_first_byte_latency_ms`
- `median_open_to_first_byte_gap_ms`
- `p95_open_to_first_byte_gap_ms`
- `average_throughput_kbps`
- `relative_throughput_ratio`
- `continuity_success_rate`
- `cross_route_recovery_rate`
- `ready_recovery_latency_ms`
- `proxy_ready_latency_ms`
- `manifest_resolve_p95_ms`
- `rollback_recovery_p95_seconds`

### Supporting Diagnostic Metrics

These usually explain the cause of regressions rather than serving as the final product verdict:

- `frame_queue_depth`
- `frame_queue_peak`
- `pending_open_streams`
- `active_streams`
- `recent_rtt_p50_ms`
- `recent_rtt_p95_ms`
- `active_route_score`
- `standby_route_score`
- `active_route_failover_count`
- `active_route_quarantined`
- `suppression_remaining_seconds`
- `healthy_candidate_count`
- `suppressed_candidate_count`

## Which Metrics Trigger Automatic Reaction

The current policy and worker loops pay special attention to combinations of:

- low `connect_success_rate`
- high `fallback_rate`
- poor `continuity_success_rate`
- poor `cross_route_recovery_rate`
- low `average_relative_throughput_ratio`
- high `average_relative_open_to_first_byte_gap_ratio`
- `active_profile_suppressed`
- `new_session_posture` becoming guarded or blocked
- applied `pause-channel` or `rotate-profile-now`

When these signals stay bad with enough observed events, `Helix` can move from advisory posture to real control-plane reaction.

## Minimal Required Evidence Set For A Serious Analysis Run

For a benchmark or canary session to be considered useful, the following evidence set should exist together:

- connect success and fallback result;
- connect latency distribution;
- first-byte latency distribution;
- open-to-first-byte gap distribution;
- throughput result;
- queue-pressure summary;
- RTT summary;
- selected route and standby state;
- continuity and recovery summary;
- relative baseline ratios;
- applied policy or actuation state if present.

If one of these is missing, the result is still useful for debugging, but weaker for promotion decisions.

## Current Source Of Truth Files

The most important implementation-level sources for these metrics today are:

- `apps/desktop-client/src-tauri/src/engine/helix/config.rs`
- `apps/desktop-client/src-tauri/src/engine/helix/benchmark.rs`
- `services/helix-adapter/src/node_registry/model.rs`
- `docs/helix/benchmarking.md`
- `docs/helix/slo-sla.md`
- `docs/testing/helix-benchmark-plan.md`
- `packages/helix-contract/schema/benchmark-report.schema.json`

## Final Rule

For `Helix`, no single metric is enough.

If throughput looks excellent but `open_to_first_byte_gap` is bad, the protocol is not yet good enough.
If failover is fast but fallback is too frequent, the protocol is not yet good enough.
If connect success is high but control-plane revoke or rollback is weak, the platform is not yet good enough.

The correct question is never "what is the speed number?" alone.
The correct question is "is `Helix` fast, stable, recoverable, controllable, and promotable at the same time?"
