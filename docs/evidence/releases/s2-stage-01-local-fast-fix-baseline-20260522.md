# S2-STAGE-01 Local Fast-Fix And Test Baseline Evidence

**Date:** 2026-05-22
**Stage:** `S2-STAGE-01: Local Fast-Fix And Test Baseline`
**Result:** `GO to S2-STAGE-02`

---

## 1. Purpose

This stage defines the local-first validation baseline for Stage 2 so small fixes do not require a full public deployment loop before we know whether they work.

The baseline is intentionally targeted. It covers the S1/S2 areas that changed most often during beta:

- Mini App Home/Plans/Profile config UX;
- invite redemption refresh behavior;
- subscription URL preference over raw proxy URI;
- `.org` subscription URL normalization;
- XHTTP/RU bundle expectations;
- Telegram Bot config delivery;
- Russian/English locale leakage in critical paths;
- Docker compose contract checks without production secrets.

---

## 2. Current Baseline

| Item | Value |
|---|---|
| Branch | `main` |
| Starting commit | `28b8d312` / `Record S2 stage 00 entry decision` |
| Runtime code changes in this stage | No runtime code changes |
| Test-only cleanup | Removed one unused import from `services/telegram-bot/tests/unit/test_handlers/test_menu.py` |
| Docker containers before stage | None running locally |
| Production deployment performed | No |

---

## 3. Fast Local Command Set

### 3.1 Backend Targeted Baseline

Use for subscription/provisioning/catalog/Mini App API changes:

```bash
cd backend
.venv/bin/python -m pytest --no-cov \
  tests/unit/application/use_cases/subscriptions/test_generate_config.py \
  tests/unit/infrastructure/remnawave/test_subscription_urls.py \
  tests/unit/presentation/api/v1/miniapp/test_routes.py \
  tests/unit/pricing/test_pricing_catalog_seed.py \
  tests/unit/presentation/api/v1/invites/test_invites_routes.py \
  -q
```

Observed result:

```text
33 passed in 0.31s
```

Backend targeted lint:

```bash
cd backend
.venv/bin/python -m ruff check \
  src/application/use_cases/subscriptions/generate_config.py \
  src/infrastructure/remnawave/subscription_urls.py \
  src/infrastructure/remnawave/stage1_ru_bundle.py \
  src/presentation/api/v1/miniapp/routes.py \
  src/presentation/api/v1/telegram/routes.py \
  tests/unit/application/use_cases/subscriptions/test_generate_config.py \
  tests/unit/infrastructure/remnawave/test_subscription_urls.py \
  tests/unit/presentation/api/v1/miniapp/test_routes.py \
  tests/unit/pricing/test_pricing_catalog_seed.py \
  tests/unit/presentation/api/v1/invites/test_invites_routes.py
```

Observed result:

```text
All checks passed!
```

### 3.2 Frontend Mini App Targeted Baseline

Use for Mini App UI, Home, Plans, Profile, invite, and config-card changes:

```bash
npm run test:run -w frontend -- \
  src/app/'[locale]'/miniapp/components/__tests__/VpnConfigCard.test.tsx \
  src/app/'[locale]'/miniapp/home/__tests__/page.test.tsx \
  src/app/'[locale]'/miniapp/home/components/__tests__/HomeClient.test.tsx \
  src/app/'[locale]'/miniapp/plans/__tests__/page.test.tsx \
  src/app/'[locale]'/miniapp/plans/components/__tests__/PlansClient.test.tsx \
  src/app/'[locale]'/miniapp/profile/__tests__/page.test.tsx
```

Observed result:

```text
Test Files  6 passed (6)
Tests       45 passed (45)
```

Frontend targeted lint:

```bash
npm run lint -w frontend -- \
  src/app/'[locale]'/miniapp/components/VpnConfigCard.tsx \
  src/app/'[locale]'/miniapp/home/page.tsx \
  src/app/'[locale]'/miniapp/plans/page.tsx \
  src/app/'[locale]'/miniapp/profile/page.tsx \
  src/app/'[locale]'/miniapp/components/__tests__/VpnConfigCard.test.tsx \
  src/app/'[locale]'/miniapp/home/__tests__/page.test.tsx \
  src/app/'[locale]'/miniapp/home/components/__tests__/HomeClient.test.tsx \
  src/app/'[locale]'/miniapp/plans/__tests__/page.test.tsx \
  src/app/'[locale]'/miniapp/plans/components/__tests__/PlansClient.test.tsx \
  src/app/'[locale]'/miniapp/profile/__tests__/page.test.tsx
```

Observed result:

```text
PASS: command exited 0
```

### 3.3 Frontend i18n Critical Path Baseline

Use before public-visible copy, locale, Mini App navigation, tariff, invite, config, wallet, or profile changes:

```bash
npm run check:i18n:s1 -w frontend
```

Observed result:

```text
PASS: all enabled locales are runtime fallback-complete for S1 critical paths.
PASS: direct reviewed S1 locales meet the local launch coverage threshold.
PASS: critical locale overrides keep ICU argument parity with the default locale.
```

Important observed values:

- enabled locales: `39`;
- direct source coverage:
  - `en-EN`: `100.0%`;
  - `ru-RU`: `95.7%`;
- other locales rely on fallback for some critical keys.

For S2, `en-EN` and `ru-RU` remain the reviewed public-release locales unless the owner explicitly expands language scope.

### 3.4 Telegram Bot Targeted Baseline

Use for bot menu, config, invite, and API-client changes:

```bash
cd services/telegram-bot
.venv/bin/python -m pytest \
  tests/unit/test_stage1_command_entrypoints.py \
  tests/unit/test_api_client.py \
  tests/unit/test_handlers/test_menu.py \
  -q
```

Observed result:

```text
56 passed in 16.25s
```

Bot targeted lint:

```bash
cd services/telegram-bot
.venv/bin/python -m ruff check \
  src/handlers/config.py \
  src/handlers/menu.py \
  tests/unit/test_stage1_command_entrypoints.py \
  tests/unit/test_api_client.py \
  tests/unit/test_handlers/test_menu.py
```

Observed result after test-only cleanup:

```text
All checks passed!
```

### 3.5 Docker Compose Contract Baseline

Main lightweight compose contract:

```bash
docker compose -f infra/docker-compose.yml config --quiet
```

Observed result:

```text
PASS: command exited 0
```

Stage 1 production-like compose contract without production secrets:

```bash
rm -rf /tmp/cybervpn-empty-secrets
mkdir -p /tmp/cybervpn-empty-secrets
for f in app.env payments.env telegram-bot.env remnawave.env sentry-runtime.env frontend.env admin.env remnawave-panel.env remnawave-node.env; do
  : > /tmp/cybervpn-empty-secrets/$f
done

CYBERVPN_IMAGE_TAG=stage2-local-smoke \
CYBERVPN_SECRETS_DIR=/tmp/cybervpn-empty-secrets \
docker compose -f infra/deploy/stage1/docker-compose.stage1.yml config --quiet

rm -rf /tmp/cybervpn-empty-secrets
```

Observed result:

```text
PASS: command exited 0
```

Stage 1 compose services resolved with empty local env files:

```text
cybervpn-remnawave-postgres
cybervpn-telegram-bot
cybervpn-backend
cybervpn-remnawave-valkey
cybervpn-remnawave
cybervpn-scheduler
cybervpn-worker
cybervpn-admin
cybervpn-frontend
```

### 3.6 Compose Path Not Used For S2 Baseline

This command currently fails:

```bash
docker compose -f infra/docker-compose.dev.yml config --quiet
```

Observed result:

```text
service "helix-adapter" has neither an image nor a build context specified: invalid compose project
```

Decision:

- Do not use `infra/docker-compose.dev.yml` as the S2 local baseline.
- Do not fix it in S2-STAGE-01 because Helix is outside S2 public-release scope.
- Track this under S6 or platform cleanup if Helix lab work resumes.

---

## 4. Fast-Fix Workflows

### 4.1 Mini App UI Fix

Use for Home/Plans/Profile/Wallet visual or copy changes.

1. Reproduce locally or with the relevant component test.
2. Update component/page and tests.
3. Run:

```bash
npm run test:run -w frontend -- \
  src/app/'[locale]'/miniapp/components/__tests__/VpnConfigCard.test.tsx \
  src/app/'[locale]'/miniapp/home/__tests__/page.test.tsx \
  src/app/'[locale]'/miniapp/home/components/__tests__/HomeClient.test.tsx \
  src/app/'[locale]'/miniapp/plans/__tests__/page.test.tsx \
  src/app/'[locale]'/miniapp/plans/components/__tests__/PlansClient.test.tsx \
  src/app/'[locale]'/miniapp/profile/__tests__/page.test.tsx
npm run check:i18n:s1 -w frontend
```

4. Run targeted lint on touched files.
5. Deploy only after tests pass.

### 4.2 Telegram Bot Text Or Handler Fix

Use for `/connect`, `/invites`, config delivery, menu, and button behavior.

1. Update handler or locale text.
2. Run:

```bash
cd services/telegram-bot
.venv/bin/python -m pytest \
  tests/unit/test_stage1_command_entrypoints.py \
  tests/unit/test_api_client.py \
  tests/unit/test_handlers/test_menu.py \
  -q
.venv/bin/python -m ruff check src tests/unit/test_stage1_command_entrypoints.py tests/unit/test_api_client.py tests/unit/test_handlers/test_menu.py
```

3. For production bot changes, smoke the real bot after deploy with the owner/internal account.

### 4.3 Backend Subscription Or Provisioning Fix

Use for subscription URL, config generation, Remnawave mapping, invite provisioning, trial/paid provisioning.

1. Add/update backend unit test first.
2. Run:

```bash
cd backend
.venv/bin/python -m pytest --no-cov \
  tests/unit/application/use_cases/subscriptions/test_generate_config.py \
  tests/unit/infrastructure/remnawave/test_subscription_urls.py \
  tests/unit/presentation/api/v1/miniapp/test_routes.py \
  tests/unit/pricing/test_pricing_catalog_seed.py \
  tests/unit/presentation/api/v1/invites/test_invites_routes.py \
  -q
.venv/bin/python -m ruff check <touched backend files>
```

3. If Remnawave behavior changes, run production-like smoke only after local pass.

### 4.4 Payment Webhook Fix

Use for payment provider callback, idempotency, final statuses, orphan payment behavior.

Minimum local before deployment:

```bash
cd backend
.venv/bin/python -m pytest --no-cov \
  tests/security/test_stage1_paid_provisioning.py \
  tests/security/test_stage1_payment_provisioning_failure.py \
  tests/unit/presentation/api/v1/miniapp/test_routes.py \
  -q
```

Additional requirement:

- payment changes must not go directly to production after only unit tests;
- run provider sandbox or signed webhook replay where available;
- confirm no raw payment payloads or secrets are logged.

### 4.5 Admin/Support Fix

Use for support queue, manual grants, customer lookup, admin operations.

Minimum local before deployment:

```bash
cd backend
.venv/bin/python -m pytest --no-cov \
  tests/security/test_stage1_admin_manual_subscription_ops.py \
  tests/security/test_stage1_admin_audit_log.py \
  -q
```

Additional requirement:

- verify audit log redaction;
- verify no raw subscription URLs, secrets, or payment payloads are exposed to support/admin UI unless explicitly required and redacted.

---

## 5. Fragile Areas Coverage

| Fragile Area | Current Coverage | Status |
|---|---|---|
| Invite redemption refresh | `HomeClient.test.tsx`, `PlansClient.test.tsx`, Mini App route tests | Covered for local baseline |
| Subscription URL selection over raw proxy URI | `test_generate_config.py`, `test_subscription_urls.py`, bot command tests, `VpnConfigCard.test.tsx` | Covered |
| `.org` subscription URL normalization | `test_subscription_urls.py` | Covered |
| XHTTP/RU bundle expectations | `test_pricing_catalog_seed.py`, Remnawave RU bundle code path tests indirectly through catalog features | Covered for current S2 entry; deeper live proof remains `S2-STAGE-08` |
| Config unavailable states | `VpnConfigCard.test.tsx`, `HomeClient.test.tsx`, Mini App route tests | Covered |
| Russian/English locale leakage | `npm run check:i18n:s1 -w frontend`, targeted string scan | Covered for en/ru critical path |
| Bot direct `vless://` leakage | `test_stage1_command_entrypoints.py` | Covered |

Targeted string scan:

```bash
rg -n "Примерно|600 ₽|Guest User|No email set|No VPN config available|Refresh token not provided" \
  frontend/src/app/'[locale]'/miniapp services/telegram-bot/src backend/src -S
```

Observed result:

```text
backend/src/presentation/api/v1/auth/routes.py:698: detail="Refresh token not provided"
```

Interpretation:

- removed Mini App/Bot display-only price copy was not found;
- old visible Mini App guest/config strings were not found in Mini App/Bot surface;
- backend auth error string remains in API code and is not part of Mini App visible copy for this baseline.

---

## 6. Local-First Gate Rules For S2

Use this rule set before public deploys:

| Change Type | Required Before Deploy |
|---|---|
| Small Mini App copy/UI | targeted frontend tests + lint + i18n critical audit |
| Bot command/menu/config | targeted bot tests + ruff |
| Backend config/subscription/provisioning | targeted backend tests + ruff |
| Payment provider/webhook | backend payment tests + signed/sandbox webhook replay + no-secret logs |
| Auth/security/admin | targeted backend tests + security scan + audit-log redaction proof |
| Docker/deploy config | `docker compose config --quiet` with no production secrets |
| Public release candidate | local targeted baseline + GitLab CI + staging/prod-like smoke |

---

## 7. Security Review Notes

This stage changed one test-only import and added this evidence document.

Checks performed:

| Check | Result |
|---|---|
| Backend targeted tests | PASS: `33 passed` |
| Frontend targeted tests | PASS: `45 passed` |
| Bot targeted tests | PASS: `56 passed` |
| Backend targeted ruff | PASS |
| Frontend targeted lint | PASS |
| Bot targeted ruff | PASS after test-only cleanup |
| i18n critical-path audit | PASS |
| Main compose contract | PASS |
| Stage 1 compose contract with empty local env files | PASS |
| `git diff --check` | PASS |
| Full repository secret scan | PASS: no leaks found |
| Targeted dangerous-pattern scan on changed files | PASS: no matches |
| `npm audit --omit=dev --audit-level=high` | PASS for high/critical; existing moderate advisories remain |

No production secrets were required for the local baseline.

Moderate dependency watch items remain unchanged from `S2-STAGE-00`:

- `brace-expansion` moderate advisory through transitive dependencies;
- `postcss` moderate advisory through the bundled Next dependency.

Track dependency cleanup under `S2-STAGE-13` and `S2-STAGE-14`; do not run `npm audit fix --force` without a separate compatibility review because it proposes a breaking Next downgrade path.

---

## 8. Decision

`S2-STAGE-01` is complete.

Decision:

```text
GO: proceed to S2-STAGE-02: S2 Scope, Backlog, And Decision Freeze.
```

Rationale:

- local test commands are known and verified;
- local lint/static checks are known and verified;
- local compose contract can be checked without production secrets;
- fragile S1/S2 areas now have an explicit fast-fix baseline;
- public deployment is no longer the first validation step for small fixes.

---

## 9. Next Stage

```text
S2-STAGE-02: S2 Scope, Backlog, And Decision Freeze
```
