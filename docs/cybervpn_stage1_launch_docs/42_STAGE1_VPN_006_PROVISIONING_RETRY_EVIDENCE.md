> CyberVPN Launch Program
> Evidence ID: S1-VPN-006
> Date: 2026-05-04
> Status: local retry contract evidence completed; durable worker/DB and staging/prod Remnawave outage evidence still required before beta.

# S1-VPN-006 Provisioning Retry Evidence

## Scope

`S1-VPN-006` proves the local retry contract for Remnawave-backed provisioning outages:

1. Remnawave outage does not lose a paid provisioning state;
2. failed paid provisioning preserves `payment_state=paid`;
3. failed trial/paid provisioning creates a retry job;
4. retry jobs use capped exponential backoff;
5. a later retry can succeed and mark provisioning ready;
6. repeated failures move to dead-letter/reconciliation instead of looping forever;
7. retry metadata is safe for support/admin surfaces.

This evidence is deliberately local/mockable. It does not prove durable PostgreSQL-backed worker processing or real staging/prod Remnawave outage behavior.

## Code Added

| File | Purpose |
|---|---|
| `backend/src/application/use_cases/subscriptions/stage1_provisioning_retry.py` | Provider-neutral retry policy, retry job, queue protocol and retry service |
| `backend/tests/security/test_stage1_provisioning_retry.py` | Component and feature-level retry tests |

## Contract

| Rule | S1 behavior |
|---|---|
| Queue name | `stage1_provisioning_retry` |
| Retryable operation types | `paid_access`, `trial_access` |
| First failed attempt | creates a queued retry job |
| Paid failure | preserves `payment_state=paid` |
| Provisioning state during retry | `retrying` |
| Support state during outage | `ops_escalation` |
| Initial retry delay | 60 seconds |
| Backoff | exponential, multiplier `2` |
| Max delay | 15 minutes |
| Max attempts | 6 |
| Exhaustion | `dead_letter` + `reconciliation_required` |
| Success after retry | `succeeded` + `ready` |
| Safe payload | no email, Telegram id, raw config, subscription URL, provider payment id, secret or token |

## Durable Queue Rule

The current implementation defines a queue protocol:

```text
Stage1ProvisioningRetryQueue.save_retry_job(job)
```

For production S1, this must be backed by durable storage, preferably PostgreSQL. Redis/Valkey may transport work, but it is not the source of truth for S1 critical provisioning jobs. This follows DEC-S1-005 and DEC-S1-015: Redis/Valkey is not durable source of truth, and critical jobs must recover from PostgreSQL/payment provider/Remnawave state.

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
python -m pytest backend/tests/security/test_stage1_provisioning_retry.py -q --no-cov
```

Result:

```text
collected 7 items
backend/tests/security/test_stage1_provisioning_retry.py ....... [100%]
7 passed in 0.24s
```

## What Was Verified

| Check | Result |
|---|---|
| Capped exponential backoff is deterministic | Passed |
| Paid Remnawave outage preserves paid state | Passed |
| Paid outage creates retry job | Passed |
| Retry job hides email/provider payment id/raw error details/secrets | Passed |
| Later paid retry succeeds and marks job `succeeded` | Passed |
| Retry failure before max attempts keeps job retrying | Passed |
| Retry exhaustion moves job to `dead_letter` / reconciliation | Passed |
| Trial Remnawave outage also queues retry | Passed |
| Flow status serialization is customer-safe | Passed |

## Remaining Evidence Before Beta

| Evidence | Status |
|---|---|
| PostgreSQL-backed retry job table/repository | Open |
| Worker claim/lock/skip-locked behavior | Open |
| Worker replay after Redis/Valkey restart | Open |
| Real staging Remnawave outage test | Open |
| Real staging retry later succeeds | Open |
| Production low-risk retry smoke | Open |
| Alert delivery on retry age / dead-letter | Open |
| Payment webhook -> provisioning failure handling | Closed locally by `45_STAGE1_PAY_008_PAYMENT_PROVISIONING_FAILURE_EVIDENCE.md`; durable/live provider/staging evidence remains open |

## Conclusion

`S1-VPN-006` is locally complete for implementation confidence. It proves the retry semantics and safe payload shape, but does not yet prove the production worker, durable retry persistence, alert delivery or real Remnawave outage recovery.
