# Helix Internal Beta Evidence Pack

## Goal

Перед запуском `Helix` internal beta команда должна собрать единый evidence pack, а не опираться на разрозненные артефакты.

## Minimum Pack

1. rollback verification output
2. deterministic backend canary-evidence budget output
3. live backend Locust report
4. current canary evidence snapshot
5. Desktop support bundle from the beta build
6. worker alert timeline for:
   - canary gate
   - canary control
   - applied actuations

## Collection Script

Use:

```bash
bash infra/tests/collect_helix_internal_beta_evidence.sh
```

This script always collects:

- [verify_helix_rollback.sh](/C:/project/CyberVPN/infra/tests/verify_helix_rollback.sh)
- [test_helix_canary_evidence_budget.py](/C:/project/CyberVPN/backend/tests/load/test_helix_canary_evidence_budget.py) when required env vars are present
- current canary snapshot when `HELIX_API_BASE_URL` and `HELIX_ADMIN_BEARER_TOKEN` are provided

## Required Manual Additions

### 1. Live Locust Run

Use:

```bash
cd backend
locust -f tests/load/test_helix_load.py --host=http://localhost:8000 -u 50 -r 10 -t 5m --headless
```

### 2. Canary Snapshot

Fetch:

```bash
GET /api/v1/helix/admin/rollouts/{rollout_id}/canary-evidence
```

### 3. Desktop Support Bundle

Export from:

- `Settings -> Diagnostics & Support`

### 4. Worker Alert Timeline

Capture:

- first `canary gate`
- first `canary control`
- first `actuation`
- recovery / resolved transitions if any

## Evidence Review Questions

- does rollback verification pass cleanly?
- does deterministic backend canary-evidence budget stay within limits?
- does live Locust run keep canary evidence readable under event ingest?
- do canary decision and follow-up action match the observed metrics?
- does Desktop support bundle confirm stable fallback and diagnostics integrity?

## Internal Beta Gate

Internal beta starts only after the evidence pack is reviewed by rollout owners and linked from the current beta decision record.
