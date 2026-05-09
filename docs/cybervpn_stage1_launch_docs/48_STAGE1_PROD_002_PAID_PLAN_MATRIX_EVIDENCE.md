> CyberVPN Launch Program
> Evidence ID: S1-PROD-002
> Date: 2026-05-04
> Status: local S1 paid plan matrix completed; deployed pricing/payment provider evidence remains required before beta.

# S1-PROD-002 Paid Plan Matrix Evidence

## Scope

`S1-PROD-002` fixes the controlled public beta paid catalog as a narrow B2C matrix:

```text
Public paid families: Basic, Plus, Pro, Max
Public paid periods: 30, 90, 180, 365 days
Public paid channels: web, miniapp, telegram_bot
Hidden/internal plans: not public and not purchasable by public checkout
Non-S1 public terms: not public and not purchasable by public checkout
```

This closes the local code/test gate for visible and purchasable beta plans. It does not enable real payment providers, production prices, production checkout, receipt/fiscalization, deployed browser evidence or provider callback evidence.

## Code Added / Changed

| File | Purpose |
|---|---|
| `backend/src/application/services/stage1_plan_policy.py` | Canonical S1 paid plan policy and public checkout guard |
| `backend/src/application/services/pricing_catalog_seed.py` | Seeds only S1 durations `30/90/180/365`, tags seed version and retires old canonical unsupported durations |
| `backend/src/application/use_cases/payments/checkout.py` | Rejects out-of-policy public paid plans before quote/commit can proceed |
| `backend/src/presentation/api/v1/plans/routes.py` | Filters public `/plans` response to S1 paid matrix |
| `backend/src/presentation/api/v1/miniapp/routes.py` | Filters Mini App offers to S1 paid matrix |
| `frontend/src/widgets/pricing/catalog.ts` | Aligns marketing fallback catalog and API normalization with S1 terms |
| `frontend/src/widgets/pricing/pricing-dashboard.tsx` | Aligns period selector layout with 4 public terms |
| `frontend/messages/*/Pricing.json` | Keeps pricing copy aligned to 4 public terms |
| `frontend/src/i18n/messages/generated/*.json` | Regenerated frontend message bundles |

## S1 Contract

| Rule | S1 behavior |
|---|---|
| Public plan families | `basic`, `plus`, `pro`, `max` |
| Public periods | `30`, `90`, `180`, `365` days |
| Public channels | `web`, `miniapp`, `telegram_bot` |
| Hidden/internal plan families | `start`, `test`, `development` remain non-public |
| Unsupported public period | Non-S1 durations such as `60` days are not returned by public catalog and are rejected by public checkout |
| Admin channel | Admin-only handling remains separate; public guard does not redefine admin tooling |
| Price source | Bootstrap prices are seed defaults only; production prices remain admin-editable |
| Add-ons | Existing add-on catalog remains present, but add-on launch decision stays under `S1-PROD-006` |
| Autoprolongation | Not promised or enabled by this task; `DEC-S1-020` remains active |

## Public Beta Seed Matrix

| Plan | 30 days | 90 days | 180 days | 365 days |
|---|---:|---:|---:|---:|
| Basic | `$5.99` | `$14.99` | `$27.99` | `$49.99` |
| Plus | `$8.99` | `$22.99` | `$39.99` | `$79.00` |
| Pro | `$11.99` | `$29.99` | `$49.99` | `$89.00` |
| Max | `$14.99` | `$36.99` | `$59.99` | `$99.00` |

These are bootstrap values, not final production pricing approval. Real production price approval and provider-specific minimum amount/currency checks remain separate evidence.

## Test Coverage

| Scenario | Result |
|---|---|
| Seed contains `7 families x 4 terms = 28` total canonical rows | Passed |
| Public seed contains `4 families x 4 terms = 16` paid rows | Passed |
| Public seed includes 180-day term | Passed |
| Public filter removes hidden/internal, inactive, wrong-channel and unsupported-period plans | Passed |
| Checkout accepts each public S1 term | Passed |
| Checkout accepts public 180-day term | Passed |
| Checkout rejects unsupported non-S1 terms | Passed |
| `/plans?channel=web` filters out unsupported non-S1 terms and preserves 180-day term | Passed |
| Mini App offers filters out unsupported non-S1 terms and preserves 180-day term | Passed |
| Frontend fallback catalog has only 30/90/180/365 terms | Passed |
| Frontend generated messages parse successfully | Passed |
| S1 security regression pack | Passed |

## Targeted Backend Test Result

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
  backend/tests/security/test_stage1_paid_plan_policy.py \
  backend/tests/unit/pricing/test_pricing_catalog_seed.py \
  backend/tests/unit/pricing/test_checkout_quote.py \
  backend/tests/unit/api/v1/test_plans.py \
  backend/tests/unit/presentation/api/v1/miniapp/test_routes.py \
  -q --no-cov
```

Result:

```text
collected 32 items
backend/tests/security/test_stage1_paid_plan_policy.py .......           [ 21%]
backend/tests/unit/pricing/test_pricing_catalog_seed.py ....             [ 34%]
backend/tests/unit/pricing/test_checkout_quote.py ...                    [ 43%]
backend/tests/unit/api/v1/test_plans.py .                                [ 46%]
backend/tests/unit/presentation/api/v1/miniapp/test_routes.py .......... [ 78%]
.......                                                                  [100%]

32 passed in 0.28s
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
python -m pytest backend/tests/security/test_stage1_*.py -q --no-cov
```

Result:

```text
collected 233 items
233 passed in 12.52s
```

Ruff:

```text
python -m ruff check \
  backend/src/application/services/stage1_plan_policy.py \
  backend/src/application/services/pricing_catalog_seed.py \
  backend/src/application/use_cases/payments/checkout.py \
  backend/src/presentation/api/v1/plans/routes.py \
  backend/src/presentation/api/v1/miniapp/routes.py \
  backend/tests/security/test_stage1_paid_plan_policy.py \
  backend/tests/unit/pricing/test_pricing_catalog_seed.py \
  backend/tests/unit/pricing/test_checkout_quote.py \
  backend/tests/unit/api/v1/test_plans.py \
  backend/tests/unit/presentation/api/v1/miniapp/test_routes.py

All checks passed.
```

Compile:

```text
python -m py_compile backend/src/application/services/stage1_plan_policy.py [...]
```

Result: passed.

## Frontend Validation

Command:

```bash
npm --prefix frontend run prepare:i18n
```

Result:

```text
[i18n] Generated 39 locale bundles in src/i18n/messages/generated.
```

JSON parse:

```text
node -e "...JSON.parse..."
json ok
```

Static stale-copy scan:

```text
rg '3 periods|3 периода|3 terms|30/90/365' frontend/messages frontend/src/i18n/messages/generated frontend/src/widgets/pricing
```

Result: no stale 3-term public pricing copy remains.

Frontend lint:

```text
npm --prefix frontend run lint -- src/widgets/pricing/catalog.ts src/widgets/pricing/pricing-dashboard.tsx
```

Result: passed.

Mini App plan UI tests:

```text
npm --prefix frontend run test:run -- \
  'src/app/[locale]/miniapp/plans/__tests__/page.test.tsx' \
  'src/app/[locale]/miniapp/plans/components/__tests__/PlansClient.test.tsx'
```

Result:

```text
Test Files  2 passed (2)
Tests       12 passed (12)
```

## What This Closes Locally

| Item | Status |
|---|---|
| `S1-PROD-002` canonical paid beta plan matrix | Closed locally |
| Backend seed for monthly/quarterly/semiannual/yearly public paid plans | Closed locally |
| Public API filtering for `/plans` | Closed locally |
| Mini App offers filtering | Closed locally |
| Public checkout accepts 180-day terms and rejects unsupported non-S1 terms | Closed locally |
| Frontend fallback pricing catalog | Closed locally |
| Public pricing copy aligned to 4 terms | Closed locally |

## Remaining Evidence Before Beta

| Evidence | Status |
|---|---|
| Deployed `/api/v1/plans?channel=web` response from staging/prod | Open |
| Deployed Mini App `/offers` response from staging/prod | Open |
| Browser screenshot for pricing page showing 4 terms | Open |
| Browser screenshot for Mini App plans showing 4 terms | Open |
| Real provider quote/invoice flow for at least one enabled payment provider | Open |
| Production price approval by owner/legal seller | Open |
| Payment minimum amount/currency evidence by provider | Open |
| Add-on launch decision and kill switch evidence under `S1-PROD-006` | Open |

## Security Review Notes

| Check | Result |
|---|---|
| `pip-audit` | Existing dependency vulnerabilities remain tracked by `TD-S1-SEC-001`; no new dependency was added |
| `npm --prefix frontend audit --omit=dev` | Existing moderate `postcss` issue through `next`; force-fix would downgrade Next and was not applied; tracked by `TD-S1-SEC-001` |
| Targeted secret scan | Only placeholder/test token names matched; no real secret was found in changed files |
| Static dangerous-pattern scan | No new `eval`, shell execution, pickle/YAML unsafe load or string-built SQL pattern found in changed Python files |

## Conclusion

`S1-PROD-002` is locally complete. CyberVPN now has a narrow S1 B2C paid catalog with public Basic/Plus/Pro/Max plans across 30/90/180/365-day terms, public catalog filtering and public checkout guards. Beta go-live still requires deployed API/UI evidence and at least one real payment path evidence.
