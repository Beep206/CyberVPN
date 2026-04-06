# Helix Internal Beta Checklist

## Purpose

This checklist defines the minimum operator workflow for opening or renewing an
internal desktop beta window for `Helix`.

## Required Commands

Run these checks in order:

1. Deterministic backend canary-evidence budget test

```bash
pytest backend/tests/load/test_helix_canary_evidence_budget.py -q
```

2. Rollback and failure-drill verification

```bash
bash infra/tests/verify_helix_rollback.sh
```

3. Current Helix worker monitoring suite

```bash
python -m pytest services/task-worker/tests/unit/tasks/test_helix_canary_gates.py \
  services/task-worker/tests/unit/tasks/test_helix_canary_control.py \
  services/task-worker/tests/unit/tasks/test_helix_actuations.py -q --no-cov
```

4. Desktop benchmark evidence

Run at least one of:

```powershell
powershell -ExecutionPolicy Bypass -File apps/desktop-client/scripts/run_helix_lab_bench.ps1 -UseSyntheticLabTarget
powershell -ExecutionPolicy Bypass -File apps/desktop-client/scripts/run_helix_recovery_lab.ps1 -Mode reconnect -UseSyntheticLabTarget
powershell -ExecutionPolicy Bypass -File apps/desktop-client/scripts/run_helix_target_matrix.ps1 -Preset mixed -UseSyntheticLabTarget
powershell -ExecutionPolicy Bypass -File apps/desktop-client/scripts/run_helix_soak_cycle.ps1 -DurationMinutes 5 -ProbeIntervalSeconds 15 -UseSyntheticLabTarget -InjectFailover -InjectReconnect
powershell -ExecutionPolicy Bypass -File apps/desktop-client/scripts/run_helix_live_comparison.ps1 -UseSyntheticLabTarget -PublishBenchmarkEvent
```

5. Internal beta evidence pack bootstrap

```bash
bash infra/tests/collect_helix_internal_beta_evidence.sh
```

## Required Artifacts

Attach all of the following to the beta decision record:

- latest `backend/tests/load/test_helix_canary_evidence_budget.py` result
- latest `infra/tests/verify_helix_rollback.sh` result
- latest Helix recovery report
- latest Helix target-matrix report
- latest Helix soak-cycle report
- latest Helix live comparison report with `sing-box` baseline
- latest formal canary evidence snapshot
- one desktop support bundle from the candidate build
- evidence pack checklist from [helix-internal-beta-evidence-pack.md](/C:/project/CyberVPN/docs/testing/helix-internal-beta-evidence-pack.md)

## Blocking Conditions

Do not open or extend internal beta if any of the following are true:

- rollback verification fails
- deterministic canary-evidence budget test fails
- formal canary evidence decision is `no-go`
- current formal canary evidence has unresolved follow-up action with severity `critical`
- current worker actuation state still requires `hold-channel-paused`

## Approval

- `ops` prepares the artifact bundle
- `sre` validates rollback and hardening results
- `admin` approves exposure beyond the existing internal cohort
