# Helix Release Gates

## Purpose

This document defines the mandatory entry and exit rules for `lab`, `canary`, and `stable`.

## Lab Channel

### Entry Requirements

- `Phase 0` and `Phase 1` are complete
- contract validation is green
- adapter skeleton health endpoints exist
- node daemon rollback path exists in lab
- benchmark harness can collect core transport metrics

### Exit Requirements

- benchmark report passes lab thresholds
- manifest revoke path tested
- node rollback drill passes
- desktop fallback to stable core passes
- no unresolved `P0` or `P1` defects in startup, rollback, or revoke flow

### Automatic Pause Triggers

- rollback failure
- manifest signature validation defect
- baseline transport disruption caused by private runtime

## Canary Channel

### Entry Requirements

- lab exit requirements all green
- [internal-beta-checklist.md](/C:/project/CyberVPN/docs/helix/internal-beta-checklist.md) reviewed for the current build
- at least one `prod-like` node validated
- signed desktop build available for internal users
- dashboards and alerts green for manifest, heartbeat, rollback, and fallback metrics
- benchmark evidence exists for the target desktop platform and network profile
- rollback drill passes via `infra/tests/verify_helix_rollback.sh`
- load evidence exists via `backend/tests/load/test_helix_canary_evidence_budget.py`
- live Helix admin route load scenario is ready via `backend/tests/load/test_helix_load.py`

### Exit Requirements

- connect success remains at or above canary target
- throughput ratio remains acceptable
- fallback rate remains below threshold
- canary evidence remains readable during concurrent benchmark ingest
- no unresolved rollback failures
- no unexplained metric blind spots
- one full release window completes without severe transport incident

### Automatic Pause Triggers

- sustained canary metric breach for more than `15 minutes`
- revoke propagation failure
- unexplained fallback spike above threshold
- repeated node rollback anomaly

## Stable Channel

### Entry Requirements

- canary exit requirements all green
- threat model and hardening review complete
- load and rollback verification complete
- signing key rotation and adapter token rotation procedures documented
- named `admin`, `ops`, and `sre` owners assigned

### Exit Requirements

- not applicable as a rollout gate; stability is continuously monitored

### Automatic Rollback or Pause Triggers

- confirmed auth boundary defect
- confirmed manifest signing defect
- confirmed rollback failure in production
- sustained user-facing fallback spike beyond stable threshold

## Authority Rules

- `ops` may pause `lab` and `canary`
- `sre` may pause or force rollback in any channel
- `stable` promotion requires `admin` approval and `sre` execution authority
