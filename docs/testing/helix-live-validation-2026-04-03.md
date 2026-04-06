# Helix Live Validation - 2026-04-03

## Scope

This validation cycle focused on the live `internal beta` blockers that still matter after the core protocol work:

- reproducible Docker lab bring-up after destructive resets;
- honest desktop-first live evidence from headless Helix runs;
- rollback and failure-drill verification on the live lab;
- formal canary evidence driven by real comparison, recovery, and soak data rather than missing observations.

## Fixed Constraints

- `Remnawave` stays authoritative for users, subscriptions, and node inventory.
- `Helix` remains desktop-first for phase one.
- `sing-box` remains the current honest stable baseline for local lab comparison.
- Control-plane state remains in `helix-adapter + backend facade + worker`, not in `Remnawave`.

## What Was Fixed In This Cycle

### 1. Stable proxy healthcheck noise

Problem:

- `helix-stable-http-proxy` used `wget` even though the image was `python:3.12-slim`, so Docker marked it unhealthy even when the proxy was serving traffic.

Fix:

- [docker-compose.yml](/C:/project/CyberVPN/infra/docker-compose.yml)

Result:

- the stable baseline proxy is now healthy in Docker and usable in live comparison runs.

### 2. Bootstrap became self-healing after destructive reset

Problem:

- `reset_helix_lab_history.sh` deletes lab node containers and volumes.
- after that, the lab depended on the caller remembering the correct `docker compose --profile helix-lab up -d ...` sequence before bootstrap.

Fix:

- [bootstrap_helix_lab.sh](/C:/project/CyberVPN/infra/tests/bootstrap_helix_lab.sh)

Result:

- bootstrap now self-heals the `helix-lab` profile before seeding DB state and publishing rollout batches.

### 3. Headless desktop evidence now publishes `ready` events correctly

Problem:

- headless comparison/recovery/soak scripts were publishing benchmark evidence, but `ready` evidence was failing with `422`.
- formal canary therefore kept showing `connect_success_rate = 0.0` even after successful live sessions.

Fix:

- [helix_lab_common.ps1](/C:/project/CyberVPN/apps/desktop-client/scripts/helix_lab_common.ps1)
- [run_helix_live_comparison.ps1](/C:/project/CyberVPN/apps/desktop-client/scripts/run_helix_live_comparison.ps1)
- [run_helix_recovery_lab.ps1](/C:/project/CyberVPN/apps/desktop-client/scripts/run_helix_recovery_lab.ps1)
- [run_helix_soak_cycle.ps1](/C:/project/CyberVPN/apps/desktop-client/scripts/run_helix_soak_cycle.ps1)

Result:

- headless lab sessions now publish accepted `ready` events;
- recovery drills publish accepted recovery-backed `ready` events;
- formal canary now sees real `connect_success_rate` and continuity observations.

### 4. Internal beta evidence collector became much more useful

Problem:

- the collector still skipped local canary snapshot fetch unless a backend bearer token was manually provided.
- latest live comparison/recovery/soak artifacts also had to be attached by hand.

Fix:

- [collect_helix_internal_beta_evidence.sh](/C:/project/CyberVPN/infra/tests/collect_helix_internal_beta_evidence.sh)

Result:

- the collector now falls back to the adapter internal canary endpoint via `HELIX_INTERNAL_AUTH_TOKEN`;
- it also copies the latest live comparison, recovery, and soak artifact directories into the evidence pack automatically.

## Live Docker / Rollback Validation

### Stack validation

- `HELIX_REQUIRE_LIVE=true bash infra/tests/test_helix_stack.sh`
- result: `Passed: 26`, `Warnings: 0`, `Failed: 0`

### Destructive rollback drill

- `HELIX_RUN_DESTRUCTIVE_DRILL=true bash infra/tests/verify_helix_rollback.sh`
- result: `Passed: 26`, `Warnings: 0`, `Failed: 0`

Relevant scripts:

- [verify_helix_rollback.sh](/C:/project/CyberVPN/infra/tests/verify_helix_rollback.sh)
- [bootstrap_helix_lab.sh](/C:/project/CyberVPN/infra/tests/bootstrap_helix_lab.sh)
- [test_helix_stack.sh](/C:/project/CyberVPN/infra/tests/test_helix_stack.sh)
- [reset_helix_lab_history.sh](/C:/project/CyberVPN/infra/tests/reset_helix_lab_history.sh)

## Current Live Canary State

Latest formal canary snapshot after the repaired headless evidence flow:

- `decision = no-go`
- `desired_state = paused`
- `applied_automatic_reaction = pause-channel`
- `channel_posture = critical`
- `active_profile_advisory_state = avoid-new-sessions`
- `active_profile_new_session_posture = blocked`

Observed metrics:

- `connect_success_rate = 1.0`
- `fallback_rate = 0.0`
- `continuity_observed_events = 7`
- `continuity_success_rate = 0.142857`
- `cross_route_recovery_rate = 0.0`
- `benchmark_observed_events = 2`
- `throughput_evidence_observed_events = 2`
- `average_benchmark_throughput_kbps = 59063.595`
- `average_relative_throughput_ratio = 0.5679`
- `average_relative_open_to_first_byte_gap_ratio = 1.43795`

Formal no-go reasons:

- `rollout desired state=paused`
- `applied actuation=pause-channel`
- `continuity success rate=14.29%`
- `cross-route recovery rate=0.00%`
- `new-session posture=blocked`
- `relative throughput ratio=0.57`
- `relative open->first-byte gap ratio=1.44`

Meaning:

- we are no longer blocked by missing desktop evidence;
- we are now blocked by honest live performance and recovery quality relative to the current policy thresholds.

## Live Helix Metrics Collected

### Latest live comparison

Artifact:

- [20260403-161711-1207e9](/C:/project/CyberVPN/apps/desktop-client/.artifacts/helix-live-comparison/20260403-161711-1207e9)

Headline numbers:

- `Helix avg throughput = 39526.99 kbps`
- `sing-box avg throughput = 83912.12 kbps`
- `relative throughput ratio = 0.4711`
- `relative open->first-byte gap ratio = 1.3658`

### Latest recovery drills

Failover artifact:

- [20260403-161755-42cbb7](/C:/project/CyberVPN/apps/desktop-client/.artifacts/helix-recovery-lab/20260403-161755-42cbb7)

Metrics:

- `ready recovery latency = 14.2 ms`
- `proxy ready latency = 73.56 ms`
- `post-recovery throughput = 71795.69 kbps`

Reconnect artifact:

- [20260403-161755-a413bb](/C:/project/CyberVPN/apps/desktop-client/.artifacts/helix-recovery-lab/20260403-161755-a413bb)

Metrics:

- `ready recovery latency = 25.56 ms`
- `proxy ready latency = 83.2 ms`
- `post-recovery throughput = 90161.31 kbps`

### Latest soak cycle

Artifact:

- [20260403-161755-c55403](/C:/project/CyberVPN/apps/desktop-client/.artifacts/helix-soak/20260403-161755-c55403)

Metrics:

- `sample_count = 9`
- `median connect latency = 4.09 ms`
- `median first-byte latency = 12.88 ms`
- `average throughput = 37483.95 kbps`
- `route_switch_count = 1`

## What This Means For Internal Beta

The important progress is real:

- live Docker lab is stable after reset;
- destructive rollback drill is reproducible;
- formal canary now sees honest desktop `ready` and recovery evidence;
- control-plane auto-reaction is no longer theoretical; it actually paused the channel on live evidence.

The blockers are also now real and explicit:

- `Helix` is still materially behind the current `sing-box` baseline on throughput ratio;
- `Helix` is still above the allowed baseline-relative `open -> first-byte gap` threshold;
- continuity quality under the current live evidence set is not good enough yet.

## Current Internal Beta Recommendation

Status:

- `not ready for internal beta expansion`

Reason:

- evidence quality is now strong enough to trust the `no-go`;
- remaining problems are performance and recovery-quality problems, not observability gaps.

## Next Recommended Steps

1. Improve `Helix` live throughput against the current stable baseline.
2. Reduce baseline-relative `open -> first-byte gap`.
3. Improve continuity quality under route churn and recovery drills until:
   - `continuity_success_rate >= 0.8`
   - `cross_route_recovery_rate >= 0.2`
4. Re-run the same comparison + recovery + soak cycle and confirm that auto-actuation no longer pauses the channel.
5. Export a fresh internal beta evidence pack after that improved cycle.
