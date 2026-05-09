> CyberVPN Launch Program
> Evidence ID: S1-PAY-008
> Date: 2026-05-08
> Status: local payment -> provisioning failure contract completed and revalidated; durable DB/worker/live-provider evidence remains required before paid beta.

# S1-PAY-008 Payment -> Provisioning Failure Evidence

## Scope

`S1-PAY-008` proves the local no-cost contract for the paid webhook critical path:

```text
verified final paid provider event
-> webhook idempotency side-effect gate
-> paid provisioning request
-> Remnawave failure
-> paid state preserved
-> provisioning retry queued
-> support/orphan policy receives a safe review item
```

This does not enable production payments. It does not replace provider-specific signature evidence, durable idempotency persistence, PostgreSQL-backed retry storage, real admin/support queues, alert delivery or staging/prod Remnawave proof.

Revalidated on 2026-05-08 as the active execution step after `S1-PAY-007`. No runtime code changes were required; the existing orchestration still proves the S1 safety rule for paid webhook -> provisioning failure.

## Code Added

| File | Purpose |
|---|---|
| `backend/src/application/use_cases/subscriptions/stage1_payment_provisioning.py` | S1 orchestration contract linking payment mapping, webhook idempotency, paid provisioning, retry and orphan policy |
| `backend/tests/security/test_stage1_payment_provisioning_failure.py` | Component and ASGI feature tests for payment -> provisioning failure handling |

Updated:

```text
backend/src/application/use_cases/subscriptions/__init__.py
```

## Contract

| Rule | S1 behavior |
|---|---|
| Non-final payment status | no provisioning attempt |
| Final paid status with automatic access allowed | provisioning may be attempted |
| Webhook duplicate | no second provisioning attempt |
| `PROVISIONING_JOB` side effect already applied | no second retry job |
| Remnawave/provisioning failure | preserve `payment_state=paid` |
| Remnawave/provisioning failure | queue `stage1_provisioning_retry` job |
| Customer-facing state during retry | `access_state=provisioning_pending`, `provisioning_state=retrying` |
| Support state during retry | `ops_escalation` plus orphan/SLA safe reference |
| Safe output | no raw provider payment id, internal payment id, email, provider hash, token, raw error, config link or subscription URL |

## Test Coverage

| Scenario | Result |
|---|---|
| Paid CryptoBot fixture + Remnawave failure | `payment_state=paid`, `provisioning_state=retrying`, retry job queued |
| Duplicate paid webhook | no second provisioning call and no second retry job |
| Non-final payment | no provisioning attempt |
| Successful provisioning | active access, ready provisioning, no manual review |
| ASGI webhook route feature test | first webhook queues retry; duplicate webhook is idempotent; response is safe |

## Targeted Test Result

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
python -m pytest backend/tests/security/test_stage1_payment_provisioning_failure.py -q --no-cov
```

Result:

```text
collected 5 items
backend/tests/security/test_stage1_payment_provisioning_failure.py ..... [100%]
5 passed in 0.04s
```

## Regression Pack

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
python -m pytest \
  backend/tests/security/test_stage1_webhook_idempotency.py \
  backend/tests/security/test_stage1_orphan_payment_policy.py \
  backend/tests/security/test_stage1_paid_provisioning.py \
  backend/tests/security/test_stage1_provisioning_retry.py \
  backend/tests/security/test_stage1_payment_provisioning_failure.py \
  -q --no-cov
```

Result:

```text
collected 89 items
89 passed in 0.49s
```

The 2026-05-08 regression covered:

- webhook idempotency;
- orphan payment policy;
- paid provisioning;
- provisioning retry;
- payment -> provisioning failure;
- payment reconciliation;
- admin payment-attempt safe view;
- support ticket path;
- support escalation.

Ruff:

```text
python -m ruff check \
  backend/src/application/use_cases/subscriptions/stage1_payment_provisioning.py \
  backend/src/application/use_cases/subscriptions/__init__.py \
  backend/tests/security/test_stage1_payment_provisioning_failure.py

All checks passed.
```

Full S1 security pack:

```text
backend/tests/security/test_stage1_*.py
215 passed in 13.12s
```

## 2026-05-08 Verification

| Check | Result |
|---|---|
| `cd backend && PYENV_VERSION=3.13.11 uv run pytest tests/security/test_stage1_payment_provisioning_failure.py -q --no-cov` | PASS: 5 passed |
| `cd backend && PYENV_VERSION=3.13.11 uv run pytest tests/security/test_stage1_webhook_idempotency.py tests/security/test_stage1_orphan_payment_policy.py tests/security/test_stage1_paid_provisioning.py tests/security/test_stage1_provisioning_retry.py tests/security/test_stage1_payment_provisioning_failure.py tests/security/test_stage1_payment_reconciliation_job.py tests/security/test_stage1_admin_payment_attempts_view.py tests/security/test_stage1_support_ticket_path.py tests/security/test_stage1_support_escalation.py -q --no-cov` | PASS: 89 passed |
| `cd backend && PYENV_VERSION=3.13.11 uv run ruff check src/application/use_cases/subscriptions/stage1_payment_provisioning.py src/application/use_cases/subscriptions/__init__.py tests/security/test_stage1_payment_provisioning_failure.py` | PASS after sorting `subscriptions/__init__.py` imports |
| Paid-state preservation on Remnawave failure | PASS |
| Duplicate paid webhook safety | PASS: no second provisioning call and no second retry job |
| Non-final payment safety | PASS: no provisioning attempt |
| Safe ASGI feature response | PASS: raw provider id, internal payment id, email, provider hash, token and subscription URL are not serialized |
| Stale next-step scan for `S1-PAY-008` as current next ID | PASS: no matches |
| `git diff --check -- <S1-PAY-008 touched files>` | PASS |
| Trailing whitespace scan over touched files | PASS |
| Secret scan over touched files | PASS after excluding explicit test placeholders and documentation terms |
| Static dangerous-pattern scan over touched files | PASS |
| Root `npm audit --omit=dev --audit-level=high` | PASS for high/critical; existing low/moderate advisories remain tracked outside this task |
| Backend `pip-audit --skip-editable backend` | PASS: no known vulnerabilities found |
| Running containers after task | PASS: no task containers started |

## Security Review Notes

- `payment_state=paid` is preserved when provisioning fails.
- Duplicate paid webhook events cannot queue duplicate provisioning/retry side effects.
- Non-final provider statuses never attempt provisioning.
- Safe output excludes raw provider ids, internal payment ids, email, provider hash, exception token text and subscription/config URLs.
- This task did not start Docker containers or require external provider credentials.

## What This Closes Locally

| Item | Status |
|---|---|
| `S1-PAY-008` local paid webhook -> provisioning failure orchestration | Closed locally |
| Paid state preservation on provisioning failure | Closed locally |
| Retry job queueing after paid provisioning failure | Closed locally |
| Duplicate webhook does not duplicate provisioning/retry | Closed locally |
| Safe response/flow status for paid-but-no-access retry | Closed locally |

## Remaining Evidence Before Paid Beta

| Evidence | Status |
|---|---|
| Provider-specific signature verification with real callback samples | Open |
| Durable Redis/DB webhook idempotency persistence | Open |
| PostgreSQL-backed provisioning retry table/repository | Open |
| Worker claim/lock/replay evidence | Open |
| Real admin/support paid-but-no-access queue | Open |
| Telegram/email alert delivery for paid-without-access | Open |
| Staging provider-paid webhook -> Remnawave paid create/extend transcript | Open |
| Staging Remnawave outage -> retry -> success transcript | Open |
| Production low-risk paid provisioning smoke | Open |

## Conclusion

`S1-PAY-008` is locally complete as an orchestration contract. It proves the critical safety rule: a verified paid event does not lose paid state when VPN provisioning fails, and duplicate webhooks cannot create duplicate provisioning/retry side effects. Paid beta remains blocked until durable persistence, live provider callback/signature evidence, real support queue/alerts and staging/prod Remnawave evidence are attached.

## Next ID

Next ID superseded by `81_STAGE1_PAY_009_REFUND_DISPUTE_PROCESS_EVIDENCE.md`; current next ID to execute is `S1-OBS-004` - live alert delivery evidence follow-up.
