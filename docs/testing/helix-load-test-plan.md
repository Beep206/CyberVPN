# Helix Load and Failure Drill Plan

## Purpose

This plan defines the minimum production-hardening checks required before `Helix`
can exit internal desktop beta.

It complements the benchmark plan by focusing on:

- control-plane evidence under concurrent access
- rollback verification without a live lab dependency
- the exact artifacts that must be attached to the internal beta evidence pack

## Check 1: Formal Canary Evidence Under Load

Artifact:

- `backend/tests/load/test_helix_load.py`
- `backend/tests/load/test_helix_canary_evidence_budget.py`

Scope:

- `test_helix_load.py` is the live `locust` scenario for operator-facing Helix admin routes
- `test_helix_canary_evidence_budget.py` is the deterministic in-process budget test for
  `GET /api/v1/helix/admin/rollouts/{rollout_id}/canary-evidence`
- the deterministic test runs through FastAPI `ASGITransport`
- the deterministic test avoids Docker and external dependencies

Acceptance:

- all requests succeed
- route returns formal canary evidence with follow-up action intact
- local `p95` request latency stays within the internal beta budget

Run:

```bash
pytest backend/tests/load/test_helix_canary_evidence_budget.py -q
```

Optional live load run:

```bash
locust -f backend/tests/load/test_helix_load.py --host=http://localhost:8000 \
  --tags canary-evidence -u 60 -r 10 -t 5m --headless
```

## Check 2: Rollback Verification

Artifact:

- `infra/tests/verify_helix_rollback.sh`

Scope:

- validates node rollback regression tests
- validates state restoration after restart
- validates worker actuation/control lifecycle tests
- can optionally include live lab checks when `HELIX_REQUIRE_LIVE=true`

Run:

```bash
bash infra/tests/verify_helix_rollback.sh
```

Optional live mode:

```bash
HELIX_REQUIRE_LIVE=true bash infra/tests/verify_helix_rollback.sh
```

## Evidence Pack For Internal Beta

Every internal beta readiness review must attach:

- latest `helix` benchmark report
- latest recovery drill report
- latest target-matrix report
- latest `pytest backend/tests/load/test_helix_load.py -q` result
- latest `pytest backend/tests/load/test_helix_canary_evidence_budget.py -q` result
- latest live `locust` run for `backend/tests/load/test_helix_load.py` when a beta environment is available
- latest `bash infra/tests/verify_helix_rollback.sh` result
- latest canary evidence snapshot for the rollout under review

## Beta Blocking Conditions

- rollback verification fails
- canary evidence route fails the local load check
- missing follow-up action in formal canary snapshot
- unexplained `fallback` or `continuity` regression in the current evidence window
