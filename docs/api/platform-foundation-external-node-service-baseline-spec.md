# CyberVPN Platform Foundation External Node Service Baseline Spec

**Date:** 2026-04-22  
**Status:** frozen implementation companion for `P3.3`

This spec freezes the first controller-side contract for external node baseline,
observed-state ingestion, synthetic verification, and traffic-eligibility evaluation.

## 1. Canonical Decisions

1. `Node Fleet Controller` owns the durable contract for external node baseline and
   traffic-eligibility evaluation.
2. `Alloy` is a required baseline service for external nodes.
3. Health agents, enrollment hooks, synthetic checks, and runtime-adapter acknowledgements
   are separate controller inputs; none of them alone is sufficient for traffic admission.
4. `traffic_eligible` remains a durable controller fact, not just a runtime-adapter hint.

## 2. Baseline Profile

The first canonical baseline profile is:

- shared required services:
  - `alloy`
  - `fleet-health-agent`
- role-specific primary service:
  - `vpn-daemon` for `vpn`
  - `edge-daemon` for `edge`
- required hooks:
  - `node-enrollment-hook`
- synthetic probe:
  - `egress-connectivity`
- runtime adapter:
  - `helix-adapter`

## 3. Observed-State Contract

The controller must persist a separate observed-state record with:

- `observed_lifecycle_state`
- `enrollment_status`
- `services_status`
- `synthetic_status`
- `health_state`
- `alloy_telemetry_flowing`
- `enrollment_hook_completed`
- `runtime_adapter_ack_state`
- `last_seen_at`
- `last_synthetic_at`
- `last_runtime_ack_at`

## 4. Health Signal Contract

The normalized health signal shape is:

- `signal_id`
- `node_id`
- `signal_type`
- `severity`
- `source`
- `component`
- `observed_at`
- `details`

Severity mapping:

- `info` -> `healthy`
- `warning` -> `degraded`
- `critical` -> `failed`

## 5. Traffic Eligibility Contract

A node may become `traffic_eligible` only when:

1. enrollment is complete;
2. required services are running;
3. `Alloy` telemetry is flowing;
4. certificates are active;
5. provider resources are active;
6. synthetic checks are passing;
7. runtime adapter acknowledged readiness;
8. the node is not quarantined.

Controller-side evaluation states:

- `blocked`
- `ready`
- `eligible`

Rules:

- `ready` means verification passed but runtime adapter acknowledgement is still missing.
- `eligible` means all gates passed and lifecycle advances to `traffic_eligible`.
- `blocked` means at least one verification gate is still red.
