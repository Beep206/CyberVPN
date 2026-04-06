# Helix Benchmark Plan

## Purpose

This plan defines how benchmark runs are executed and reported.

The benchmark harness must exercise the same desktop connect path that end users run in the app:

- `helix` through the embedded desktop sidecar and its local `SOCKS5` ingress
- `sing-box` and `xray` through the existing desktop local `SOCKS5` ingress

This keeps benchmark numbers comparable at the desktop runtime boundary instead of mixing protocol numbers with unrelated UI or provisioning differences.

## Desktop Execution Path

The desktop runtime now exposes a first-class local proxy path for every supported core.

- `helix` uses the prepared runtime `proxy_url` from the signed manifest flow.
- `sing-box` and `xray` use the configured local desktop `SOCKS5` port.
- Benchmarks must target these local proxy URLs instead of connecting directly to remote nodes.

The benchmark command surface is the desktop IPC command `run_transport_benchmark`, which produces a transport report with:

- active core
- proxy URL
- target host, port, and path
- connect latency distribution
- first-byte latency distribution
- aggregate throughput
- per-attempt success and failure details

For apples-to-apples desktop comparisons, prefer the orchestration command `run_transport_core_comparison`, which:

- switches the requested desktop core in a controlled sequence
- waits for the local proxy ingress to become ready
- runs the same benchmark scenario against each core
- emits one comparison report with baseline-relative ratios

For multi-target evidence, use `run_transport_target_matrix_comparison`, which:

- runs the same core-comparison workflow across a shared target matrix
- keeps target host, port, path, and attempt policy explicit per target
- emits per-target comparison reports plus aggregate core summaries
- keeps the baseline selection visible instead of hiding it inside one headline number

For Helix recovery drills, use `run_helix_recovery_benchmark`, which:

- connects Helix through the normal desktop launch path
- triggers a controlled sidecar action in either `failover` or `reconnect` mode
- measures ready-recovery latency and proxy-ready latency separately
- captures pre-recovery and post-recovery telemetry snapshots for the perf bundle

For headless lab execution outside the Desktop UI, use:

- `apps/desktop-client/scripts/run_helix_lab_bench.ps1` for a focused single-target Helix bench
- `apps/desktop-client/scripts/run_helix_recovery_lab.ps1` for controlled `failover` or `reconnect` recovery drills
- `apps/desktop-client/scripts/run_helix_target_matrix.ps1` for a Helix-only multi-target matrix across shared benchmark policy
- `apps/desktop-client/scripts/run_helix_soak_cycle.ps1` for sustained live-session traces with repeated probe samples and controlled churn actions
- `apps/desktop-client/scripts/run_helix_live_comparison.ps1` for Helix vs `sing-box` live baseline evidence and adapter benchmark ingest

The headless scripts launch the same embedded Helix sidecar entrypoint from the desktop binary,
write JSON artifacts under `apps/desktop-client/.artifacts`, and are intended for repeatable lab
runs where UI interaction would add noise.

Helix runtime startup should also record which manifest route was selected after route probing and the measured probe latency for that selected route.

Helix diagnostics and support bundles must also capture:

- recent RTT samples from the active sidecar session
- active frame queue depth and peak frame queue depth
- pending-open stream count and max concurrent streams
- recent per-stream telemetry with bytes, duration, and sampled queue depth
- last recovery benchmark report
- last target-matrix comparison report

## Required Scenarios

### Scenario 1: Clean Network Connect

- desktop platform from the active support matrix
- same node group for baseline and candidate
- minimum `100` connection attempts
- report connect success, median connect time, and `p95` connect time

### Scenario 2: Clean Network Sustained Session

- continuous sessions on baseline and candidate
- minimum `20` sessions per runtime
- report unexpected disconnects, fallback events, and user-visible recovery time

### Scenario 3: Challenged Network Connect

- controlled challenged-network profile
- same desktop and node class
- minimum `100` connection attempts
- report connect success, connect time distribution, and fallback rate

### Scenario 4: Throughput and Latency Stability

- same region, node group, and desktop build
- compare throughput ratio and latency variance
- report whether candidate stays within threshold relative to best baseline

### Scenario 4A: Synthetic Lab Throughput Isolation

- use the embedded desktop sidecar through the same local `SOCKS5` ingress path
- target the `helix-bench-target` lab service over `socks5h`, so DNS resolution happens inside the Helix route path
- use a deterministic large object such as `/8mb.bin`
- treat this scenario as the transport-isolation benchmark for validating runtime buffer, framing, and stream scheduling changes
- archive both the Helix report and the direct non-Helix control result when possible

### Scenario 5: First-Class Desktop Core Comparison

- resolve or prepare the active runtime for the candidate core
- run the same local-proxy benchmark workflow for `helix`, `sing-box`, and `xray`
- use the same target host, port, path, sample count, and desktop build
- compare median connect time, `p95` connect time, first-byte latency, and throughput from the same desktop ingress layer
- use a readiness gate before each run so cold proxy startup does not pollute transport comparisons

### Scenario 6: Controlled Route Degradation And Failover Recovery

- launch Helix through the normal desktop connect path
- trigger a controlled local sidecar failover action
- measure route-before, route-after, ready-recovery latency, and proxy-ready latency
- capture pre-action and post-action telemetry snapshots in the exported perf bundle
- treat failures to recover proxy readiness as benchmark failures, not informational warnings

### Scenario 7: Controlled Reconnect Recovery

- launch Helix through the normal desktop connect path
- trigger a controlled local sidecar reconnect on the active route
- measure ready-recovery latency and proxy-ready latency independently
- run one post-recovery benchmark sample against the same target to verify restored usability

### Scenario 8: Shared Target Matrix Comparison

- define a fixed target matrix for the test window
- run `helix`, `sing-box`, and `xray` against the exact same matrix
- emit both per-target comparison reports and aggregate per-core summaries
- treat a core with missing targets as degraded evidence, even if one target looks excellent

### Scenario 9: Sustained Soak and Churn Cycle

- launch Helix through the normal desktop sidecar path for a long-lived run
- keep repeated probe samples running on one shared target while collecting health and telemetry snapshots
- optionally inject `failover` and `reconnect` during the same session window
- record route switches, queue-depth peaks, RTT drift, and sustained throughput windows
- treat the soak report as required evidence for long-lived desktop stability, not just an informational lab artifact

## Report Format

Every benchmark report must include:

- report ID
- date and environment
- candidate manifest version and sidecar version
- baseline transport
- benchmark proxy URL and ingress mode
- selected route endpoint reference for Helix runs
- selected route probe latency for Helix runs when available
- RTT sample window and queue-depth summary for Helix runs
- recent stream telemetry summary for Helix runs
- recovery action type and recovery latencies for recovery drills
- target matrix definition for matrix runs
- sample size
- all threshold comparisons
- final pass or fail summary

## Frequency

- before promotion from `lab` to `canary`
- before promotion from `canary` to `stable`
- after any protocol-significant or runtime-significant change

## Storage

Benchmark results must be represented in the shared `benchmark-report` contract and archived with the rollout evidence set.
