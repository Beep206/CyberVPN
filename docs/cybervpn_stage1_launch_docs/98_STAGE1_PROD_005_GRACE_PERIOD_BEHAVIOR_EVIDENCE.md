> CyberVPN Launch Program
> Evidence ID: S1-PROD-005
> Date: 2026-05-06
> Status: local grace-period product contract completed; durable worker and staging/prod Remnawave evidence remain required before beta.

# S1-PROD-005 Grace Period Behavior Evidence

## Scope

`S1-PROD-005` closes the product-level Stage 1 grace-period rule:

```text
Paid subscription: 72h grace after expiry
Trial: no paid grace; disable at expiry
During grace: VPN access stays ready and user sees renewal action
After grace: access is disabled through the expiry/grace worker
Missing Remnawave UUID after grace: support/reconciliation review
```

This task links the existing worker-side `S1-VPN-007` contract to the customer/support-facing product behavior. It does not prove durable PostgreSQL scheduling, live Remnawave disable, deployed dashboard rendering or live alert delivery.

## Code Added / Changed

| File | Purpose |
|---|---|
| `backend/src/application/use_cases/subscriptions/stage1_expiry_grace_disable.py` | Keeps `grace` as self-service renewal instead of a support escalation |
| `backend/tests/security/test_stage1_grace_period_product_policy.py` | Product-level S1 grace policy checks for paid, trial, support review and safe flow status |
| `backend/tests/security/test_stage1_expiry_grace_disable.py` | Existing worker/adapter evidence reused for the disable boundary |
| `backend/tests/security/test_stage1_cors_cookie_config.py` | Fresh production-import test env now includes mandatory `ADMIN_2FA_REQUIRED=true` |
| `backend/tests/security/test_stage1_csrf_protection.py` | Fresh production-import test env now includes mandatory `ADMIN_2FA_REQUIRED=true` |
| `backend/tests/security/test_stage1_swagger_public_off.py` | Fresh production-import test env now includes mandatory `ADMIN_2FA_REQUIRED=true` |

## S1 Product Contract

| State | S1 behavior |
|---|---|
| Paid active before expiry | Access remains `active`; provisioning remains `ready` |
| Paid expired inside 72h grace | Access state is `grace`; provisioning remains `ready`; user action is manual renewal |
| Grace self-service | `support_state=self_service`, `support_escalation=false` |
| Paid expired at `expires_at + 72h` | Worker disables Remnawave access and returns `expired/suspended` |
| Trial expiry | Trial has no paid grace and disables at `access_expires_at` |
| Missing Remnawave UUID after grace | Access enters `reconciliation_required` / `support_review` |
| Safe response | Flow status contains no raw subscription URL, config file, password, token or provider secret |
| Support copy | Expired/grace template tells the user to renew manually and does not promise autoprolongation |

## Targeted Test Evidence

Command:

```bash
cd backend && uv run pytest \
  tests/security/test_stage1_grace_period_product_policy.py \
  tests/security/test_stage1_expiry_grace_disable.py \
  -q --no-cov
```

Result:

```text
collected 16 items
tests/security/test_stage1_grace_period_product_policy.py ......         [ 37%]
tests/security/test_stage1_expiry_grace_disable.py ..........            [100%]

16 passed in 0.24s
```

Ruff:

```bash
cd backend && uv run ruff check \
  src/application/use_cases/subscriptions/stage1_expiry_grace_disable.py \
  tests/security/test_stage1_grace_period_product_policy.py \
  tests/security/test_stage1_expiry_grace_disable.py
```

Result:

```text
All checks passed.
```

## Regression Pack

Command:

```bash
cd backend && ENVIRONMENT=test SWAGGER_ENABLED=false ADMIN_2FA_REQUIRED=false \
SKIP_TEST_DB_BOOTSTRAP=1 \
DATABASE_URL=postgresql+asyncpg://test:test@localhost:5432/test \
REDIS_URL=redis://localhost:6379/15 \
REMNAWAVE_TOKEN=test-remnawave-token \
JWT_SECRET=test-jwt-secret-that-is-long-enough-for-settings \
JWT_REFRESH_SECRET=test-refresh-secret-that-is-long-enough \
CRYPTOBOT_TOKEN=test-cryptobot-token \
PYENV_VERSION=3.13.11 \
uv run pytest tests/security/test_stage1_*.py -q --no-cov
```

Result:

```text
collected 344 items
344 passed in 17.22s
```

Note: the first broad pack run exposed a pre-existing test harness mismatch after `S1-ADM-003`: fresh production-import CORS/CSRF/Swagger tests did not pass the mandatory production `ADMIN_2FA_REQUIRED=true`. The tests now set that variable only inside the production fresh-import subprocesses, so RBAC tests can still run with admin 2FA disabled locally.

## What Was Verified

| Check | Result |
|---|---|
| `DEC-S1-012` 72h paid grace constant | Passed |
| Paid access inside grace is not disabled | Passed |
| Grace flow status is customer self-service, not support escalation | Passed |
| Grace flow status exposes `grace_ends_at` and `disable_required=false` | Passed |
| Paid access disables exactly at the 72h boundary | Passed |
| Trial access has no paid grace | Passed |
| Missing Remnawave UUID after grace escalates to support/reconciliation | Passed |
| Expired support template preserves manual renewal policy | Passed |
| Flow status does not leak runtime secrets, config URLs or tokens | Passed |

## Remaining Evidence Before Beta

| Evidence | Status |
|---|---|
| PostgreSQL-backed due-candidate query | Open |
| Durable worker schedule/claim/lock execution | Open |
| Staging Remnawave disable smoke | Open |
| Production low-risk disable smoke before paid go-live | Open |
| Deployed dashboard/Telegram `grace` and `expired` state screenshots | Open; belongs to `S1-FE-002` and live Telegram evidence |
| Alert delivery for failed disable/reconciliation queue | Open |

## Security Review Notes

| Check | Result |
|---|---|
| Secrets | No secret values or provider credentials added |
| Raw config exposure | Tests assert no subscription/config/token/password leakage in flow status |
| Support escalation semantics | `grace` is self-service; only `support_review` and `ops_escalation` set `support_escalation=true` |
| Dependencies | No dependency added or downgraded |
| Root `npm audit --omit=dev --audit-level=high` | PASS for high/critical; existing moderate `ip-address`/`postcss` advisories remain tracked and were not force-fixed because the proposed fixes are breaking |
| Backend `pip-audit` | PASS: no known vulnerabilities found; local editable package `cybervpn-backend` is skipped because it is not on PyPI |
| Secret scan | Only non-secret test value factories and documented placeholder/test env names matched |
| Dangerous-pattern scan | Only static `subprocess.run` production fresh-import tests matched; no shell execution or runtime user input is involved |
| Docker resource use | No Docker containers were started for this task |

## Conclusion

`S1-PROD-005` is locally complete as a product contract. CyberVPN now has a tested 72h paid grace behavior that keeps access ready during grace, pushes the user toward manual renewal, avoids false support escalation and disables access after the approved boundary.

Next ID to execute: `S1-FE-004` - devices page with devices, limits and actions. `S1-FE-003` is completed locally in `100_STAGE1_FE_003_CONFIG_DELIVERY_UI_EVIDENCE.md`.
