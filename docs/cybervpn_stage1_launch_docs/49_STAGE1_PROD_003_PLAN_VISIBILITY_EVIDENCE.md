> CyberVPN Launch Program
> Evidence ID: S1-PROD-003
> Date: 2026-05-04
> Status: local public/private plan visibility guard completed; deployed API/UI evidence remains required before beta.

# S1-PROD-003 Plan Visibility Evidence

## Scope

`S1-PROD-003` verifies that public plan surfaces expose only the intended S1 B2C paid catalog and do not leak private/internal plans.

S1 public catalog:

```text
Public plan families: Basic, Plus, Pro, Max
Public periods: 30, 90, 180, 365 days
Public channels: web, miniapp, telegram_bot
Private/internal plan families: Start, Test, Development
Private/internal channel: admin only
```

This task does not create production plans, approve final production prices, enable add-ons, or replace deployed browser/API evidence.

## Code Added / Changed

| File | Purpose |
|---|---|
| `backend/src/application/services/stage1_plan_policy.py` | Adds explicit private plan families to the S1 catalog policy and keeps public filtering centralized |
| `backend/src/presentation/api/v1/telegram/routes.py` | Applies the same S1 public paid plan filter to Telegram Bot `/bot/plans` |
| `frontend/src/widgets/pricing/catalog.ts` | Adds defensive frontend filtering for `catalog_visibility=public` and `web` sale channel before rendering pricing |
| `backend/tests/security/test_stage1_paid_plan_policy.py` | Adds seed visibility checks for private families and hidden public-family rows |
| `backend/tests/unit/api/v1/test_telegram_plans.py` | Adds Telegram Bot plan visibility regression coverage |

## Visibility Contract

| Surface | Visibility rule |
|---|---|
| Public web `/api/v1/plans?channel=web` | Only active `basic/plus/pro/max` public plans with web channel and S1 terms |
| Mini App `/api/v1/miniapp/offers` | Only active `basic/plus/pro/max` public plans with miniapp channel and S1 terms |
| Telegram Bot `/api/v1/telegram/bot/plans` | Only active `basic/plus/pro/max` public plans with telegram_bot channel and S1 terms |
| Checkout quote/commit | Public channels reject hidden/private plans and non-S1 terms |
| Admin plans endpoint | Admin-only surface may list hidden/internal plans for controlled operations |
| Frontend pricing fallback/API normalization | Hidden/private or non-web rows are ignored defensively |

## Private Plan Seed Matrix

| Plan family | Visibility | Sale channels | Public exposure |
|---|---|---|---|
| Start | `hidden` | `admin` | Not public |
| Test | `hidden` | `admin` | Not public |
| Development | `hidden` | `admin` | Not public |

## Test Coverage

| Scenario | Result |
|---|---|
| Seed exposes only `basic/plus/pro/max` as public paid families | Passed |
| Seed keeps `start/test/development` hidden and admin-only | Passed |
| Public filter removes hidden internal plan rows | Passed |
| Public filter removes hidden rows even if the plan family is otherwise public | Passed |
| Public filter removes inactive rows | Passed |
| Public filter removes wrong-channel rows | Passed |
| Public filter removes unsupported non-S1 terms | Passed |
| Web `/plans` keeps S1 public rows and removes unsupported rows | Passed |
| Mini App `/offers` keeps S1 public rows and removes unsupported rows | Passed |
| Telegram Bot `/bot/plans` keeps S1 public rows and removes private/wrong-channel/unsupported rows | Passed |
| Frontend pricing normalization ignores hidden/private or non-web rows defensively | Covered by static code path and lint; deployed UI screenshot remains open |

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
  backend/tests/unit/api/v1/test_telegram_plans.py \
  backend/tests/unit/presentation/api/v1/miniapp/test_routes.py \
  -q --no-cov
```

Result:

```text
collected 34 items
backend/tests/security/test_stage1_paid_plan_policy.py ........          [ 23%]
backend/tests/unit/pricing/test_pricing_catalog_seed.py ....             [ 35%]
backend/tests/unit/pricing/test_checkout_quote.py ...                    [ 44%]
backend/tests/unit/api/v1/test_plans.py .                                [ 47%]
backend/tests/unit/api/v1/test_telegram_plans.py .                       [ 50%]
backend/tests/unit/presentation/api/v1/miniapp/test_routes.py .......... [ 79%]
.......                                                                  [100%]

34 passed in 0.29s
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
collected 234 items
234 passed in 12.85s
```

## Static Validation

Ruff:

```text
python -m ruff check \
  backend/src/application/services/stage1_plan_policy.py \
  backend/src/presentation/api/v1/telegram/routes.py \
  backend/tests/security/test_stage1_paid_plan_policy.py \
  backend/tests/unit/api/v1/test_telegram_plans.py \
  backend/tests/unit/api/v1/test_plans.py \
  backend/tests/unit/presentation/api/v1/miniapp/test_routes.py

All checks passed.
```

Python compile:

```text
python -m py_compile backend/src/application/services/stage1_plan_policy.py [...]
```

Result: passed.

Frontend lint:

```text
npm --prefix frontend run lint -- src/widgets/pricing/catalog.ts
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
| Private/internal plan family seed visibility | Closed locally |
| Public web catalog visibility guard | Closed locally |
| Mini App catalog visibility guard | Closed locally |
| Telegram Bot catalog visibility guard | Closed locally |
| Public checkout hidden/private plan rejection | Closed locally via S1 paid plan policy |
| Frontend pricing defensive visibility filter | Closed locally |

## Remaining Evidence Before Beta

| Evidence | Status |
|---|---|
| Deployed `/api/v1/plans?channel=web` response showing no hidden/private plans | Open |
| Deployed `/api/v1/miniapp/offers` response showing no hidden/private plans | Open |
| Deployed `/api/v1/telegram/bot/plans` response showing no hidden/private plans | Open |
| Browser screenshot of pricing UI showing only public plans | Open |
| Admin-only screenshot/API evidence showing hidden plans remain admin-visible | Open |
| Production DB seed/output evidence after real catalog seed | Open |

## Security Review Notes

| Check | Result |
|---|---|
| Public API exposure | Hidden/private plan rows are filtered before serialization on public catalog surfaces |
| Telegram Bot exposure | Bot catalog now uses the same S1 public paid plan policy as web/Mini App |
| Frontend fallback | Pricing UI ignores hidden/private rows defensively if a bad API response is ever received |
| Secrets | No real secrets are introduced; test commands use explicit placeholder tokens only |
| `pip-audit` | Existing dependency vulnerabilities remain tracked by `TD-S1-SEC-001`; no new dependency was added |
| `npm --prefix frontend audit --omit=dev` | Existing moderate `postcss` issue through `next`; force-fix would downgrade Next and was not applied; tracked by `TD-S1-SEC-001` |
| Targeted secret scan | Only placeholder/test token names matched in this evidence file; no real secret was found in changed files |
| Static dangerous-pattern scan | No new `eval`, shell execution, pickle/YAML unsafe load or string-built SQL pattern found in changed Python files |

## Conclusion

`S1-PROD-003` is locally complete. CyberVPN public plan visibility is now guarded across web, Mini App, Telegram Bot and checkout. Beta go-live still requires deployed API/UI evidence and admin-only visibility proof on staging or production.
