# Helix Live Validation - 2026-04-03

## Scope

This validation cycle focused on the remaining `internal beta` blockers around:

- live desktop-to-Helix evidence ingestion;
- rollback and failure-drill verification on the live Docker lab;
- backend admin/control-plane load behavior under beta-like polling;
- canary evidence promotion from `no-go` caused by missing observations to a real `watch` state backed by live desktop/runtime data.

## Fixed Constraints

- `Remnawave` remains authoritative for users, subscriptions, and node inventory.
- `Helix` remains desktop-first for phase one.
- Existing `xray` and `sing-box` paths remain available as stable fallback cores.
- Control-plane state remains in the `adapter + backend facade + worker` stack, not in `Remnawave`.

## What Was Validated

### Docker / Rollback / Failure Drill

- Live stack verification passed.
- Destructive rollback drill passed earlier in the same cycle.
- Current rollback verifier output in the internal-beta pack shows:
  - `Passed: 23`
  - `Warnings: 1`
  - `Failed: 0`
- The only warning in the pack is that the destructive drill was not re-executed inside the collector wrapper itself.

Relevant scripts:

- [verify_helix_rollback.sh](/C:/project/CyberVPN/infra/tests/verify_helix_rollback.sh)
- [bootstrap_helix_lab.sh](/C:/project/CyberVPN/infra/tests/bootstrap_helix_lab.sh)
- [test_helix_stack.sh](/C:/project/CyberVPN/infra/tests/test_helix_stack.sh)

### Live Desktop Runtime Evidence

The adapter received live desktop runtime events derived from real lab runs:

- `5` recovery `ready` events
- `1` `benchmark` event

Resulting live canary snapshot:

- `decision = watch`
- `connect_success_rate = 1.0`
- `fallback_rate = 0.0`
- `continuity_observed_events = 5`
- `continuity_success_rate = 1.0`
- `cross_route_recovery_rate = 0.4`
- `benchmark_observed_events = 1`
- `average_benchmark_throughput_kbps = 96206.87`

Current remaining evidence gaps:

- `throughput evidence observations=0`
- `gap ratio evidence unavailable in rollout status`

This is an expected and honest `watch` state, not a synthetic `go`.

### Live Helix Bench / Recovery Numbers

Synthetic lab benchmark:

- `median connect latency = 1.66 ms`
- `median first-byte latency = 11.77 ms`
- `average throughput = 96206.87 kbps`

Recovery drill samples used for continuity evidence:

- failover sample:
  - `ready recovery latency = 16 ms`
  - `proxy ready latency = 34.03 ms`
  - `post-recovery throughput = 59091.35 kbps`
- reconnect sample:
  - `ready recovery latency = 25.02 ms`
  - `proxy ready latency = 42.03 ms`
  - `post-recovery throughput = 40136.88 kbps`

Additional live recovery observations were collected to reach the minimum continuity evidence threshold.

### Backend Admin Load

After hardening fixes, a live `Locust` run against the Helix admin surface completed with:

- `1495` total requests
- `0` failures
- aggregated median latency `30 ms`
- aggregated average latency `43 ms`

Per-route results:

- `/api/v1/helix/admin/nodes`
  - `206 reqs`
  - `0 failures`
  - average `40 ms`
- `/api/v1/helix/admin/rollouts/[rollout_id]`
  - `427 reqs`
  - `0 failures`
  - average `42 ms`
- `/api/v1/helix/admin/rollouts/[rollout_id]/canary-evidence`
  - `862 reqs`
  - `0 failures`
  - average `44 ms`

## Hardening Fixes Applied In This Cycle

### 1. Adapter node inventory fallback

Problem:

- `/admin/nodes` could fail if `Remnawave` sync failed at request time.

Fix:

- [service.rs](/C:/project/CyberVPN/services/helix-adapter/src/node_registry/service.rs)

Behavior now:

- if live sync from `Remnawave` fails, the adapter logs a warning and returns cached registry state instead of failing the request.

Coverage:

- [node_registry.rs](/C:/project/CyberVPN/services/helix-adapter/tests/node_registry.rs)

### 2. Helix admin read-path rate-limit budget

Problem:

- beta-like polling on Helix admin routes triggered large numbers of `429` responses because the global per-IP budget was too low for legitimate operator polling.

Fix:

- [rate_limit.py](/C:/project/CyberVPN/backend/src/presentation/middleware/rate_limit.py)
- [settings.py](/C:/project/CyberVPN/backend/src/config/settings.py)
- [test_rate_limiter.py](/C:/project/CyberVPN/backend/tests/security/test_rate_limiter.py)

Behavior now:

- `GET /api/v1/helix/admin/*` uses a separate higher read budget while other routes keep the default global rate limit.

### 3. Redis connection-pool starvation under admin polling

Problem:

- after the `429` issue was reduced, one remaining live `500` was caused by `redis.exceptions.MaxConnectionsError` in the auth / revocation path.

Fix:

- [redis_client.py](/C:/project/CyberVPN/backend/src/infrastructure/cache/redis_client.py)
- [settings.py](/C:/project/CyberVPN/backend/src/config/settings.py)
- [test_redis_client.py](/C:/project/CyberVPN/backend/tests/unit/infrastructure/cache/test_redis_client.py)

Behavior now:

- backend uses `BlockingConnectionPool` with configurable `REDIS_MAX_CONNECTIONS` and `REDIS_POOL_WAIT_SECONDS` instead of a tiny fixed non-blocking pool.

## Evidence Pack

Current pack:

- [20260403-live-cycle-02](/C:/project/CyberVPN/.artifacts/helix-internal-beta/20260403-live-cycle-02)

Included:

- [rollback-verification.txt](/C:/project/CyberVPN/.artifacts/helix-internal-beta/20260403-live-cycle-02/rollback-verification.txt)
- [backend-canary-evidence-budget.txt](/C:/project/CyberVPN/.artifacts/helix-internal-beta/20260403-live-cycle-02/backend-canary-evidence-budget.txt)
- [canary-evidence.json](/C:/project/CyberVPN/.artifacts/helix-internal-beta/20260403-live-cycle-02/canary-evidence.json)
- [live-admin-load-summary.txt](/C:/project/CyberVPN/.artifacts/helix-internal-beta/20260403-live-cycle-02/live-admin-load-summary.txt)

## Current Internal Beta Status After This Cycle

Status moved forward materially:

- Docker live lab: strong
- rollback/failure drill tooling: strong
- desktop runtime evidence: present
- canary gate: real `watch`
- backend admin/control-plane under load: clean for the tested profile

Remaining blockers before a stronger `internal beta` recommendation:

- collect honest baseline-relative throughput evidence
- collect honest baseline-relative `open -> first-byte gap` evidence
- run longer soak-style live sessions
- run installer/update/restart/crash-recovery passes on clean desktop environments

## Next Recommended Steps

1. Run live comparative `Helix / sing-box / xray` evidence to populate:
   - `relative_throughput_ratio_vs_baseline`
   - `relative_open_to_first_byte_gap_ratio_vs_baseline`
2. Run a longer soak cycle with sustained admin polling plus desktop traffic.
3. Export at least one beta desktop support bundle from the installed build and attach it to the next evidence pack.
4. Re-evaluate whether the rollout can move from `watch` toward `go` once the remaining evidence gaps are closed.
