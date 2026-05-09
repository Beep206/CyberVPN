# 44. Stage 1 VPN Expiry / Grace Disable Evidence

Task: `S1-VPN-007`  
Status: locally implemented and tested  
Scope: worker-side expiry/grace decision contract for Remnawave-backed B2C access.

## Owner Decision

`DEC-S1-012` sets the paid subscription grace period to 72 hours.

Related product-level closure: `S1-PROD-005` is recorded in `98_STAGE1_PROD_005_GRACE_PERIOD_BEHAVIOR_EVIDENCE.md`.

For S1:

- paid subscription access is not disabled before `access_expires_at + 72h`;
- trial access has no paid grace period and is disabled at expiry;
- if access is already disabled/expired, the worker does not disable it again;
- if Remnawave UUID is missing after grace, the item goes to reconciliation/support review;
- if Remnawave disable fails, the item stays due and moves to ops escalation.

## Implemented Contract

| Area | Implementation |
|---|---|
| Job name | `stage1_expiry_grace_disable` |
| Paid grace period | 72 hours |
| Trial grace period | 0 hours |
| Decision function | `evaluate_stage1_expiry_grace(...)` |
| Worker contract | `Stage1ExpiryGraceWorker.process_record/process_batch` |
| Remnawave adapter | `RemnawaveStage1ExpiryGraceGateway` |
| Remnawave operation | `PATCH /api/users` via existing `RemnawaveUserGateway.update(..., status=DISABLED)` |
| Safe output | no raw subscription URL, config link, payment id, provider secret or raw upstream error |

## Files Changed

| File | Purpose |
|---|---|
| `backend/src/application/use_cases/subscriptions/stage1_expiry_grace_disable.py` | Provider-neutral S1 expiry/grace policy, decision model and worker contract |
| `backend/src/infrastructure/remnawave/stage1_expiry_grace_gateway.py` | Remnawave adapter for disabling expired access |
| `backend/tests/security/test_stage1_expiry_grace_disable.py` | Local policy, worker and adapter evidence |

## Test Evidence

Command:

```bash
ENVIRONMENT=test \
SKIP_TEST_DB_BOOTSTRAP=1 \
DATABASE_URL=postgresql+asyncpg://test:test@localhost:5432/test \
REDIS_URL=redis://localhost:6379/15 \
REMNAWAVE_TOKEN=test-remnawave-token \
JWT_SECRET=test-jwt-secret-that-is-long-enough-for-settings \
JWT_REFRESH_SECRET=test-refresh-secret-that-is-long-enough \
CRYPTOBOT_TOKEN=test-cryptobot-token \
PYTHONPATH=backend \
PYENV_VERSION=3.13.11 \
python -m pytest backend/tests/security/test_stage1_expiry_grace_disable.py -q --no-cov
```

Result:

```text
collected 10 items
backend/tests/security/test_stage1_expiry_grace_disable.py .......... [100%]
10 passed in 0.26s
```

S1 security pack:

```text
backend/tests/security/test_stage1_*.py
210 passed in 13.49s
```

## What Was Verified

| Check | Result |
|---|---|
| Paid active access before expiry is not disabled | Passed |
| Paid expired access inside 72h grace is not disabled | Passed |
| Paid access disables at the 72h grace boundary | Passed |
| Trial access has no paid grace and disables at expiry | Passed |
| Already disabled access is not disabled again | Passed |
| Missing Remnawave UUID after grace becomes reconciliation/support review | Passed |
| Remnawave disable failure becomes ops escalation without raw error leakage | Passed |
| Batch worker disables only records past policy | Passed |
| Flow status exposes grace/disable details without raw secrets | Passed |
| Remnawave adapter updates upstream user to `DISABLED` | Passed |

## Remaining Evidence Before Go-Live

| Evidence | Status |
|---|---|
| PostgreSQL-backed query for due expiry candidates | Open |
| Durable worker schedule/claim/lock evidence | Open |
| Real staging Remnawave disable smoke | Open |
| Production low-risk disable smoke | Open |
| User-facing dashboard/Telegram grace state evidence | Open; belongs to `S1-FE-002` / Telegram tasks |
| Alert delivery for failed disable / reconciliation queue | Open |

## Conclusion

`S1-VPN-007` is locally complete for implementation confidence. It proves the 72-hour paid grace rule and disable boundary, but does not yet prove durable worker scheduling, database candidate selection, alert delivery or real staging/prod Remnawave disable behavior.
