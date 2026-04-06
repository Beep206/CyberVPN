# Helix Benchmarking

## Purpose

This document defines how CyberVPN measures whether the Helix is competitive with `VLESS` and `XHTTP` and whether it is safe to promote between rollout channels.

Benchmarking is mandatory. No rollout may claim “fast enough” or “stable enough” without measured evidence.

## Benchmark Topology

### Comparison Targets

- `VLESS` on the current best production-ready baseline path
- `XHTTP` on the current best production-ready baseline path
- `helix` candidate under the same node class, region, and client platform

### Comparison Principle

For every benchmark run:

- baseline and candidate use the same region or closest equivalent region;
- the same desktop OS and desktop build class are used;
- the same node group is used where possible;
- the same network profile is used;
- the same measurement window is used.

### Required Environments

- `lab`
- `prod-like`
- `canary`

## Network Profiles

### Clean Network

A connection environment with low packet loss, low jitter, and no known selective transport interference.

### Challenged Network

A connection environment with one or more of:

- elevated RTT variance;
- moderate packet loss;
- constrained bandwidth;
- selective degradation or blocking pressure affecting mainstream transports.

Sensitive blocking simulation details belong in restricted internal materials, not in this document.

## Metrics

### Primary User Metrics

- `connect_success_rate`
- `median_connect_time_ms`
- `p95_connect_time_ms`
- `throughput_ratio_vs_baseline`
- `unexpected_disconnect_rate`
- `desktop_fallback_rate`
- `time_to_recover_after_failure_ms`

### Control-Plane Metrics

- `manifest_resolve_p95_ms`
- `manifest_revoke_propagation_seconds`
- `heartbeat_freshness_seconds`
- `rollback_recovery_p95_seconds`

## Metric Definitions

### Connect Success

A run counts as successful only if the desktop runtime establishes the transport, passes the startup health gate, routes test traffic, and does not immediately fallback.

### Connect Time

Measure from connect command issuance to first healthy state acknowledged by the desktop runtime.

### Throughput Ratio

`candidate_throughput / best_baseline_throughput`

for the same environment and scenario.

### Unexpected Disconnect

A disconnect is unexpected when it is not user initiated, not part of a controlled revoke or planned restart, and forces reconnect, fallback, or user-visible interruption.

### Fallback Rate

The portion of connection attempts or live sessions that require desktop recovery to a stable core because the Helix failed startup, became unhealthy, or was explicitly revoked.

## Pass/Fail Thresholds

### Hard Thresholds

- `median_connect_time_ms`: candidate must be no worse than `1.05x` the best baseline
- `p95_connect_time_ms`: candidate must be no worse than `1.15x` baseline
- `throughput_ratio_vs_baseline`: candidate must be `>= 0.95`
- `clean_network_connect_success_rate`: candidate must be `>= 99.5%`
- `challenged_network_connect_success_rate` in canary: candidate must be `>= 98.0%`
- `clean_network_fallback_rate`: candidate must be `< 1.0%`
- `challenged_network_fallback_rate`: candidate must be `< 3.0%`

### Operational Thresholds

- `manifest_resolve_p95_ms <= 200`
- `manifest_revoke_propagation_seconds <= 60`
- `rollback_recovery_p95_seconds <= 90`

## Sampling Rules

- At least `100` connect attempts per desktop and network scenario in lab
- At least `20` sustained-session observations before canary promotion
- Outliers may be flagged, but not silently removed

## Reporting Rules

Every benchmark report must state:

- baseline transport;
- candidate build or manifest version;
- desktop client version;
- sidecar version;
- node group;
- region;
- network profile;
- sample size;
- pass/fail result for each threshold.

## Promotion Rule

No rollout may advance from `lab` to `canary`, or from `canary` to `stable`, without a benchmark report that passes the thresholds defined here.
