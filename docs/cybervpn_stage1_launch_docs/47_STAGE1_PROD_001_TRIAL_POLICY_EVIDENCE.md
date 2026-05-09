> CyberVPN Launch Program
> Evidence ID: S1-PROD-001
> Date: 2026-05-04
> Status: local S1 trial policy contract completed; staging/prod trial activation evidence remains required before beta.

# S1-PROD-001 Trial Policy Evidence

## Scope

`S1-PROD-001` fixes the controlled public beta trial rule as a canonical product/API/provisioning contract:

```text
Trial duration: 3 days
Trial device limit: 1 device
Trial traffic limit: 2 GiB
Trial reuse rule: one trial per account
Activation rate limit: 3 activation attempts per 1 hour
```

This closes the local code/test gate for the visible beta rule. It does not replace staging/prod Remnawave activation evidence, deployed UI screenshots, real support escalation proof or external anti-abuse/fraud controls.

## Code Added / Changed

| File | Purpose |
|---|---|
| `backend/src/application/use_cases/trial/stage1_trial_policy.py` | Canonical S1 trial policy constants and immutable policy DTO |
| `backend/src/application/use_cases/trial/stage1_trial_provisioning.py` | Reuses the canonical policy for Remnawave trial provisioning limits |
| `backend/src/application/use_cases/trial/activate_trial.py` | Uses the canonical 3-day policy and exposes policy fields on activation result |
| `backend/src/application/use_cases/trial/get_trial_status.py` | Exposes the canonical policy on status result |
| `backend/src/application/services/entitlements_service.py` | Aligns trial entitlement snapshots with 3 days / 1 device |
| `backend/src/presentation/api/v1/trial/schemas.py` | Adds visible policy fields to `/trial/activate` and `/trial/status` responses |
| `backend/src/presentation/api/v1/trial/routes.py` | Uses canonical activation rate-limit policy and optional S1 Remnawave provisioning gate |
| `backend/src/presentation/api/v1/miniapp/routes.py` | Uses canonical activation rate-limit policy for Mini App trial activation |
| `backend/src/presentation/api/v1/telegram/schemas.py` | Adds visible policy fields to bot-facing trial status |
| `backend/src/presentation/api/v1/telegram/routes.py` | Aligns bot trial duration with canonical S1 policy |
| `frontend/messages/*/MiniApp.json` | Replaces stale 7-day trial copy with 3-day / 1-device copy |
| `frontend/messages/*/landing.json` | Replaces stale 2-day/2GB quick-start copy with 3-day / 1-device copy |
| `frontend/src/i18n/messages/generated/*.json` | Regenerated frontend message bundles |

## S1 Contract

| Rule | S1 behavior |
|---|---|
| Trial duration | `3` calendar days from activation time |
| Trial device limit | `1` device / HWID limit in Remnawave provisioning request |
| Trial traffic limit | `2 GiB` in the provisioning request |
| Trial traffic reset strategy | `NO_RESET` |
| Trial reuse | A second activation for the same account is rejected |
| Trial activation rate limit | 3 attempts per account per 1 hour in API and Mini App flows |
| API visibility | `/api/v1/trial/activate` and `/api/v1/trial/status` return `duration_days`, `device_limit`, `traffic_limit_bytes`, `one_trial_per_account` |
| Telegram visibility | Bot-facing trial status returns the same visible policy fields |
| Entitlement visibility | Active trial snapshots report `period_days=3` and `effective_entitlements.device_limit=1` |
| User-facing copy | Mini App and landing copy no longer advertise 7-day or 2-day trial terms |

## Test Coverage

| Scenario | Result |
|---|---|
| Provisioning request uses default S1 VPN profile and trial limits | Passed |
| Trial provisioning result remains safe and does not expose subscription URLs in safe metadata | Passed |
| Activation use case provisions VPN access after policy calculation | Passed |
| Activation use case exposes policy fields | Passed |
| Duplicate trial activation is rejected before state update | Passed |
| API `/trial/status` exposes policy fields | Passed |
| API `/trial/activate` exposes policy fields | Passed |
| API duplicate activation path returns `400` | Passed |
| Mini App trial activation preserves canonical policy fields | Passed |
| S1 security regression pack | Passed |
| Frontend source/generated JSON bundles parse successfully | Passed |

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
python -m pytest \
  backend/tests/security/test_stage1_trial_provisioning.py \
  backend/tests/unit/api/v1/test_trial.py \
  backend/tests/unit/presentation/api/v1/miniapp/test_routes.py \
  -q --no-cov
```

Result:

```text
collected 29 items
backend/tests/security/test_stage1_trial_provisioning.py .......         [ 24%]
backend/tests/unit/api/v1/test_trial.py .....                            [ 41%]
backend/tests/unit/presentation/api/v1/miniapp/test_routes.py .......... [ 75%]
.......                                                                  [100%]

29 passed in 0.09s
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
collected 226 items
226 passed in 13.27s
```

Ruff:

```text
python -m ruff check \
  backend/src/application/use_cases/trial/stage1_trial_policy.py \
  backend/src/application/use_cases/trial/stage1_trial_provisioning.py \
  backend/src/application/use_cases/trial/activate_trial.py \
  backend/src/application/use_cases/trial/get_trial_status.py \
  backend/src/application/use_cases/trial/__init__.py \
  backend/src/application/services/entitlements_service.py \
  backend/src/presentation/api/v1/trial/schemas.py \
  backend/src/presentation/api/v1/trial/routes.py \
  backend/src/presentation/api/v1/miniapp/routes.py \
  backend/src/presentation/api/v1/telegram/schemas.py \
  backend/src/presentation/api/v1/telegram/routes.py \
  backend/tests/security/test_stage1_trial_provisioning.py \
  backend/tests/unit/api/v1/test_trial.py \
  backend/tests/integration/api/v1/trial/test_trial_flows.py \
  backend/tests/unit/presentation/api/v1/miniapp/test_routes.py

All checks passed.
```

Compile:

```text
python -m py_compile backend/src/application/use_cases/trial/stage1_trial_policy.py [...]
```

Result: passed.

Frontend message validation:

```text
npm --prefix frontend run prepare:i18n
[i18n] Generated 39 locale bundles in src/i18n/messages/generated.

node -e "...JSON.parse..."
json ok
```

Stale copy scan:

```text
rg "7 days|7-Day|2 days / 2GB|2 дня / 2 ГБ|7-днев|7 дней" frontend/messages frontend/src/i18n/messages/generated -g "*.json"
```

Result: no matches.

## What This Closes Locally

| Item | Status |
|---|---|
| `S1-PROD-001` canonical beta trial rule | Closed locally |
| Backend trial activation duration | Closed locally |
| Backend entitlement snapshot duration/device limit | Closed locally |
| API response visibility for trial policy | Closed locally |
| Duplicate account trial rejection test | Closed locally |
| Mini App / landing stale trial copy removal | Closed locally |
| Generated i18n bundles synchronized | Closed locally |

## Remaining Evidence Before Beta

| Evidence | Status |
|---|---|
| Real staging Remnawave trial activation with `3 days / 1 device` | Open |
| Real production Remnawave trial activation before go-live | Open |
| Deployed browser screenshot for web/Mini App trial copy | Open |
| Deployed Telegram Bot/Mini App trial status response | Open |
| Redis/ingress/edge trial rate-limit evidence | Open |
| Trial abuse/fraud monitoring beyond one-account rule | Open |
| Support escalation path for trial provisioning failures | Open |

## Security Review Notes

| Check | Result |
|---|---|
| `pip-audit` | Existing dependency vulnerabilities remain tracked by `TD-S1-SEC-001`; no new dependency was added |
| `npm --prefix frontend audit --omit=dev` | Existing moderate `postcss` issue through `next`; force-fix would downgrade Next and was not applied; tracked by `TD-S1-SEC-001` |
| Targeted secret scan | Only placeholder/test token names matched; no real secret was found in changed files |
| Static dangerous-pattern scan | No new `eval`, shell execution, pickle/YAML unsafe load or string-built SQL pattern found in changed Python files |

## Conclusion

`S1-PROD-001` is locally complete. CyberVPN now has one canonical S1 trial policy shared by provisioning, activation, entitlement snapshots, API responses, Telegram-facing trial status and visible frontend copy. Beta go-live still requires staging/prod Remnawave and deployed UI/API evidence.
