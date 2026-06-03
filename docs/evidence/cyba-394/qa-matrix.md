# CYBA-394 QA matrix: Passkey/WebAuthn

Дата: 2026-06-03
Commit: `0b509f6`
Issue: `CYBA-394`
Scope: QA verification для `CYBA-386` Passkey/WebAuthn rollout across `frontend`, `admin`, `partner`.

## Итог

Результат: **PASS**

`CYBA-431` снял runtime blocker после `CYBA-428`: customer `frontend /en-EN/login` в реальном Next dev/browser render теперь hydrates, запрашивает passkey policy, показывает CTA `Sign in with passkey`, ставит `autocomplete="username webauthn"` и сохраняет обычный React submit для password login.

Текущих blocker defects для `CYBA-394` не осталось.

## Final rerun после CYBA-431

Дата: 2026-06-03
Commit: `0b509f6`
Результат: **PASS**

### Final rerun commands

```bash
npm run test:run -w frontend -- 'src/app/[locale]/(auth)/login/__tests__/login-client-passkeys.test.tsx' src/features/auth/components/__tests__/PasskeyUpgradePrompt.test.tsx src/widgets/settings-cabinet/__tests__/settings-cabinet-dashboard.test.tsx src/lib/api/__tests__/passkeys.test.ts
env NODE_ENV=development NEXT_TELEMETRY_DISABLED=1 npm run dev -w frontend
```

Playwright Chromium smoke was run against `http://127.0.0.1:9001/en-EN/login` with mocked enabled customer passkey policy and mocked browser WebAuthn/Conditional UI support.

### Final rerun results

| Check | Expected | Actual | Result | Evidence |
| --- | --- | --- | --- | --- |
| `frontend` passkey login, upgrade prompt, settings CRUD, API client | targeted customer passkey bundle passes | 4 files, 30 tests passed | PASS | terminal output |
| `frontend` desktop browser route | policy request, passkey CTA, `username webauthn`, password fallback | policy request: 1; auth options request: 1; passkey button: 1; `username webauthn`: 1; password input: 1 | PASS | `screenshots/frontend-login-desktop-post-cyba-431.png` |
| `frontend` mobile browser route | same as desktop without clipping/overflow | policy request: 1; auth options request: 1; passkey button: 1; `username webauthn`: 1; password input: 1 | PASS | `screenshots/frontend-login-mobile-post-cyba-431.png` |
| `frontend` normal login hydration smoke | clicking `Sign In` calls React submit handler and `/api/v1/auth/login` | `POST /api/v1/auth/login` observed; final URL stays `http://127.0.0.1:9001/en-EN/login` | PASS | Playwright route trace |

Observed browser details:

- Desktop inputs: `["username webauthn", "current-password", null]`.
- Mobile inputs: `["username webauthn", "current-password", null]`.
- DOM body contains `passkey`.
- Password fallback remains visible.
- Synthetic invalid password submit returns mocked `401`, which is expected for submit interception proof.
- A console `500` was observed during the smoke after the synthetic `401`; it did not affect the acceptance assertions and appears related to the mocked invalid login path rather than passkey rendering.

## Rerun после CYBA-428

Дата: 2026-06-03
Commit: `0b509f6`
Результат: **FAIL**

### Rerun commands

```bash
npm run test:run -w frontend -- 'src/app/[locale]/(auth)/login/__tests__/login-client-passkeys.test.tsx' src/features/auth/components/__tests__/PasskeyUpgradePrompt.test.tsx src/widgets/settings-cabinet/__tests__/settings-cabinet-dashboard.test.tsx src/lib/api/__tests__/passkeys.test.ts
npm run test:run -w frontend -- 'src/app/[locale]/(auth)/login/__tests__/login-client-passkeys.test.tsx'
npm run test:run -w frontend -- --pool=forks 'src/app/[locale]/(auth)/login/__tests__/login-client-passkeys.test.tsx'
npm run test:run -w frontend -- src/lib/api/__tests__/passkeys.test.ts
env NODE_ENV=development NEXT_TELEMETRY_DISABLED=1 npm run dev -w frontend
```

Playwright Chromium smoke was run against `http://127.0.0.1:9001/en-EN/login` with mocked enabled customer passkey policy and mocked browser WebAuthn/Conditional UI support.

### Rerun results

| Check | Expected | Actual | Result | Evidence |
| --- | --- | --- | --- | --- |
| `frontend` passkey API client | passkey policy/options/verify/list/rename/delete client contract still passes | 1 file, 3 tests passed | PASS | `src/lib/api/__tests__/passkeys.test.ts` |
| `frontend` component passkey login test | reaches passkey assertions | fails before assertions with `Invalid hook call` / `TypeError: Cannot read properties of null (reading 'useState')` at `useIsRateLimited()` | FAIL | terminal output |
| `frontend` desktop browser route | policy request, passkey CTA, `username webauthn`, password fallback | policy requests: `0`; passkey button: `0`; `username webauthn`: `0`; password input: `1` | FAIL | `screenshots/frontend-login-desktop-rerun.png` |
| `frontend` mobile browser route | same as desktop without clipping/overflow | policy requests: `0`; passkey button: `0`; `username webauthn`: `0`; password input: `1` | FAIL | `screenshots/frontend-login-mobile-rerun.png` |
| `frontend` normal login hydration smoke | clicking `Sign In` calls React submit handler and `/api/v1/auth/login` | no `/api/v1/auth/login`; browser navigates to `http://127.0.0.1:9001/en-EN/login?` | FAIL | Playwright route trace |

Observed browser details:

- `frontend/.next/dev/static/chunks/frontend_src_0pumutz._.js` contains `passkeysApi.getPolicy()`, `getPasskeyBrowserSupport()`, `passkeyButton`, and `username webauthn`, so the code is present in the compiled dev bundle.
- Loaded page has normal customer login SSR content and client chunks, but no `/api/v1/auth/passkeys/*` requests are observed after 25 seconds.
- DOM body does not contain `passkey`.
- Inputs remain `["username", "current-password", null]`.
- Repeated dev HMR websocket errors appear in console; no `pageerror` or explicit hydration exception surfaced.

### Rerun defect

1. `CYBA-431`: Customer `frontend /en-EN/login` remains non-compliant after `CYBA-428`.
   - Severity: `P1`
   - Expected: mounted route runs passkey policy/capability checks, renders `Sign in with passkey`, sets `autocomplete="username webauthn"`, and preserves normal React login submit.
   - Actual: no passkey policy request, no passkey CTA, username autocomplete remains `username`, and normal `Sign In` behaves like an unhydrated HTML form.
   - Requested fix: fix customer frontend route hydration/passkey runtime and add route-level/browser regression coverage. Component-only coverage is not sufficient.

## Команды

```bash
npm run test:run -w frontend -- src/app/[locale]/\(auth\)/login/__tests__/login-client-passkeys.test.tsx src/features/auth/components/__tests__/PasskeyUpgradePrompt.test.tsx src/widgets/settings-cabinet/__tests__/settings-cabinet-dashboard.test.tsx src/lib/api/__tests__/passkeys.test.ts
npm run test:run -w admin -- src/features/auth/lib/passkey-webauthn.test.ts src/lib/api/__tests__/passkeys.test.ts
npm run test:run -w partner -- src/lib/api/__tests__/passkeys.test.ts
ENVIRONMENT=test SKIP_TEST_DB_BOOTSTRAP=1 REMNAWAVE_TOKEN=synthetic-remnawave-token JWT_SECRET=synthetic-jwt-secret-for-cyba-394-qa-only CRYPTOBOT_TOKEN=synthetic-cryptobot-token uv run pytest tests/integration/test_passkey_webauthn_api.py tests/contract/test_passkey_openapi_contract.py -q --no-cov
npm run test:run -w admin -- src/app/[locale]/\(auth\)/login/login-client.test.tsx
npm run test:run -w partner -- src/app/[locale]/\(auth\)/login/login-client.test.tsx
env NODE_ENV=development NEXT_TELEMETRY_DISABLED=1 PORT=3101 npm run dev -w admin
env NODE_ENV=development NEXT_TELEMETRY_DISABLED=1 PORT=3002 npm run dev -w partner
env NODE_ENV=development NEXT_TELEMETRY_DISABLED=1 npm run dev -w frontend
```

## Automated results

| Area | Result | Evidence |
| --- | --- | --- |
| `frontend` passkey login, upgrade prompt, settings CRUD, API client | PASS | Final rerun after `CYBA-431`: 4 files, 30 tests passed |
| `admin` WebAuthn helper + passkey API client | PASS | 2 files, 3 tests passed |
| `partner` passkey API client / `X-Auth-Realm=partner` client behavior | PASS | 1 file, 2 tests passed |
| Backend passkey integration + OpenAPI contract | PASS | 14 tests passed |
| Existing admin login smoke | PASS | 1 file, 1 test passed |
| Existing partner login smoke | PASS | 1 file, 1 test passed |

Backend setup note: first backend run failed before collection because `remnawave_token`, `jwt_secret`, and `cryptobot_token` were unset. Rerun used synthetic test-only values and `SKIP_TEST_DB_BOOTSTRAP=1`; this is environment setup, not a product defect.

## Browser / UI evidence

| Surface | Route | Expected | Actual | Result | Screenshot |
| --- | --- | --- | --- | --- | --- |
| `admin` desktop | `http://127.0.0.1:3101/en-EN/login` | passkey CTA, password fallback, `username webauthn` | passkey button: 1, `username webauthn`: 1, password input: 1 | PASS | `screenshots/admin-login-desktop.png` |
| `admin` mobile | `http://127.0.0.1:3101/en-EN/login` | same as desktop without clipping/overflow | passkey button: 1, `username webauthn`: 1, password input: 1 | PASS | `screenshots/admin-login-mobile.png` |
| `partner` storefront boundary desktop | `http://127.0.0.1:3102/en-EN/login` | no partner operator passkey controls on storefront | passkey button: 0, `username webauthn`: 0, password input: 1 | PASS | `screenshots/partner-login-desktop.png` |
| `partner` storefront boundary mobile | `http://127.0.0.1:3102/en-EN/login` | no partner operator passkey controls on storefront | passkey button: 0, `username webauthn`: 0, password input: 1 | PASS | `screenshots/partner-login-mobile.png` |
| `partner` portal desktop | `http://portal.localhost:3002/en-EN/login` | passkey CTA, password fallback, `username webauthn` | passkey button: 1, `username webauthn`: 1, password input: 1 | PASS | `screenshots/partner-portal-login-desktop.png` |
| `partner` portal mobile | `http://portal.localhost:3002/en-EN/login` | same as desktop without clipping/overflow | passkey button: 1, `username webauthn`: 1, password input: 1 | PASS | `screenshots/partner-portal-login-mobile.png` |
| `frontend` desktop | `http://127.0.0.1:9001/en-EN/login` with mocked enabled passkey policy | passkey CTA, password fallback, `username webauthn` | passkey button: 1, `username webauthn`: 1, password input: 1, policy request: 1 | PASS | `screenshots/frontend-login-desktop-post-cyba-431.png` |
| `frontend` mobile | `http://127.0.0.1:9001/en-EN/login` with mocked enabled passkey policy | same as desktop without clipping/overflow | passkey button: 1, `username webauthn`: 1, password input: 1, policy request: 1 | PASS | `screenshots/frontend-login-mobile-post-cyba-431.png` |

Customer frontend debug evidence after `CYBA-431`:

- Playwright mocked `**/api/v1/auth/passkeys/policy` and browser Conditional UI capability.
- Request to `/api/v1/auth/passkeys/policy` was observed from the hydrated route.
- Conditional auth options request to `/api/v1/auth/passkeys/authentication/options` was observed.
- DOM body contains `passkey`.
- Inputs were `["username webauthn", "current-password", null]`.
- Component test `login-client-passkeys.test.tsx` now reaches and passes passkey assertions.
- Normal login submit is hydrated: clicking `Sign In` calls `POST /api/v1/auth/login` and does not navigate to `/login?`.

## Matrix coverage

| Scenario | Result | Notes |
| --- | --- | --- |
| Customer explicit passkey login visible | PASS | Browser screenshot + DOM selector after `CYBA-431`. |
| Customer Conditional UI anchor | PASS | Real route sets `autocomplete="username webauthn"` under mocked enabled policy/capability. |
| Customer password/OAuth/Telegram/magic-link fallback visibility | PASS | Real route keeps existing fallback methods visible. |
| Customer normal login submit hydration | PASS | Clicking `Sign In` calls `POST /api/v1/auth/login` and stays on `/en-EN/login` under mocked 401. |
| Customer settings passkey empty/list/add/rename/delete | PASS | Covered by `settings-cabinet-dashboard.test.tsx`; no live backend fixture used. |
| Customer post-login upgrade prompt | PASS | Covered by `PasskeyUpgradePrompt.test.tsx`; no live authenticated browser fixture used. |
| Admin explicit passkey login visible | PASS | Browser screenshot + DOM selector. |
| Admin Conditional UI anchor | PASS | Browser screenshot + DOM selector. |
| Admin WebAuthn serialization/cancel/unsupported handling | PASS | Targeted Vitest helper tests. |
| Admin policy/compliance API client | PASS | Targeted Vitest API tests. |
| Partner portal explicit passkey login visible | PASS | Browser screenshot + DOM selector on `portal.localhost:3002`. |
| Partner portal Conditional UI anchor | PASS | Browser screenshot + DOM selector. |
| Partner `X-Auth-Realm=partner` client behavior | PASS | Targeted partner API client test. |
| Partner storefront boundary | PASS | Browser screenshot proves storefront route does not expose operator passkey controls. |
| Backend registration/login/reauthentication/session/OpenAPI contract | PASS | 14 backend tests passed. |
| Rollback behavior | PARTIAL | Runbook and backend flag contract inspected; no production/staging flag toggle or DB rollback executed by QA. |
| RTL/browser matrix | NOT RUN | Not enough authenticated/browser fixture coverage in this heartbeat; residual risk recorded. |

## Defects

No open blocker defects after `CYBA-431`.

Historical defects:

1. `CYBA-431`: Customer `frontend` login route remained non-compliant after `CYBA-428`.
   - Severity: `P1`
   - Status: fixed and QA rerun PASS on 2026-06-03.
   - Evidence: `screenshots/frontend-login-desktop-post-cyba-431.png`, `screenshots/frontend-login-mobile-post-cyba-431.png`, Playwright route trace.

## Residual risk

- No real authenticator ceremony was executed in browser; backend verifies ceremonies through synthetic integration tests.
- No authenticated live CRUD screenshots for customer/admin/partner settings because the heartbeat had no QA account/backend fixture for logged-in state.
- No full Chrome/Edge/Safari/Firefox matrix; only Chromium headless browser evidence was captured.
- No destructive rollback or DB downgrade executed, per issue restrictions.
- Context7 docs checked: N/A, no code/library implementation was changed by QA in this heartbeat.
