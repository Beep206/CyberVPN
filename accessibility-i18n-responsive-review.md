# Accessibility, i18n and Responsive Post-Fix Smoke

Issue: [CYBA-577](/CYBA/issues/CYBA-577)
Parent: [CYBA-568](/CYBA/issues/CYBA-568)
Baseline references: [CYBA-460](/CYBA/issues/CYBA-460), [CYBA-549](/CYBA/issues/CYBA-549)
Date: `2026-06-06`
Reviewer: `qa-accessibility-i18n-reviewer`

## Scope Tested

Environment:

- Client local dev: `http://127.0.0.1:9001`
- Admin local dev: `http://127.0.0.1:3003`
- Partner local dev: `http://127.0.0.1:3002`
- Note: `127.0.0.1:3001` was occupied by an unrelated `Uptime Kuma` service, so admin was intentionally started on `3003`.
- Browser: Chromium via Playwright headless
- User state: anonymous only; no cookies, storage state, HAR, traces, JWT, Telegram `initData`, payment data, or production data saved

Viewport matrix:

- `390x844`
- `768x1024`
- `1366x768`
- `1440x900`

Locale matrix:

- Client: `en-EN`, `ru-RU`, `ar-SA` RTL smoke
- Admin: `en-EN`, `ru-RU`; `ar-SA` redirects to `ru-RU` because admin supports only `ru-RU` and `en-EN`
- Partner: `en-EN`, `ru-RU`; `ar-SA` redirects to `ru-RU` because partner supports only `ru-RU` and `en-EN`

Evidence:

- `evidence/a11y-i18n-responsive/CYBA-577-client-partner-20260606T072341Z/manifest.md`
- `evidence/a11y-i18n-responsive/CYBA-577-client-partner-20260606T072341Z/audit-results.json`
- `evidence/a11y-i18n-responsive/CYBA-577-client-partner-20260606T072341Z/delayed-client-visibility-check.json`
- `evidence/a11y-i18n-responsive/CYBA-577-client-partner-20260606T072341Z/screenshots/**`
- `evidence/a11y-i18n-responsive/CYBA-577-admin-3003-20260606T072828Z/manifest.md`
- `evidence/a11y-i18n-responsive/CYBA-577-admin-3003-20260606T072828Z/audit-results.json`
- `evidence/a11y-i18n-responsive/CYBA-577-admin-3003-20260606T072828Z/delayed-visibility-check.json`
- `evidence/a11y-i18n-responsive/CYBA-577-admin-3003-20260606T072828Z/screenshots/**`

Docs evidence:

- Context7 docs checked: N/A - manual UI/accessibility/i18n smoke; no source code or framework-dependent fix recommendation was made.

## Result Summary

Post-fix smoke found one P1 and one P2 issue.

| ID | Severity | Area | Summary | Follow-up |
|---|---|---|---|---|
| BUG-001 | P1 | admin visual accessibility | Admin login form exists in DOM but is visually absent/near-invisible after 5 seconds | [CYBA-583](/CYBA/issues/CYBA-583) |
| BUG-002 | P2 | client accessibility | Client floating bottom-left icon button has no accessible name | [CYBA-584](/CYBA/issues/CYBA-584) |

Positive checks:

- Client `ar-SA` login/pricing now renders `html lang="ar-SA"` and `dir="rtl"` with Arabic text and no tracked English fallback phrase hits in the smoke cases.
- Client `ru-RU` login/pricing and partner/admin `ru-RU` login cases had no tracked English fallback phrase hits.
- Partner login/application smoke passed at `200` with no horizontal overflow, unlabeled visible inputs, nameless controls, or clipped visible controls.
- Client/partner/admin tested cases had `0` page-level horizontal overflow and `0` unlabeled visible input cases in the DOM audit.
- Delayed client visibility check confirmed the client login form is visible after the entry animation; the earlier 1-second screenshots are timing artifacts, not a client form visibility bug.

## Bugs

### BUG-001 - Admin login form is visually absent after load

Severity: P1
Type: visual accessibility / responsive regression
Surface: `admin-panel`
Environment: local dev `http://127.0.0.1:3003`, Chromium via Playwright headless, anonymous, `ru-RU` `390x844` and `en-EN` `1440x900`

Steps to reproduce:

1. Start admin with `NEXT_TELEMETRY_DISABLED=1 HOST=0.0.0.0 PORT=3003 npm run dev -w admin`.
2. Open `http://127.0.0.1:3003/ru-RU/login`.
3. Set viewport to `390x844`.
4. Wait 5 seconds after `domcontentloaded`.
5. Repeat with `http://127.0.0.1:3003/en-EN/login` at `1440x900`.

Expected:

- The admin login form should be visible: heading, passkey button, email/password fields, password reveal, submit button and helper copy should have usable contrast and be visually discoverable.

Actual:

- Screenshots after 5 seconds show only the header/language controls and grey scanline background; the central login form is not visually discernible.
- DOM evidence still contains in-viewport form elements and body text, including `Email адрес`, `Пароль`, `Войти`, `Email address`, `Password`, and `Sign In`, so the route returns `200` and the form exists but the visual flow is effectively blocked.

Evidence:

- `evidence/a11y-i18n-responsive/CYBA-577-admin-3003-20260606T072828Z/screenshots/CYBA-577__admin-panel__anonymous__ru-RU__mobile390__login-after-5s__20260606T072828Z.png`
- `evidence/a11y-i18n-responsive/CYBA-577-admin-3003-20260606T072828Z/screenshots/CYBA-577__admin-panel__anonymous__en-EN__desktop1440__login-after-5s__20260606T072828Z.png`
- `evidence/a11y-i18n-responsive/CYBA-577-admin-3003-20260606T072828Z/delayed-visibility-check.json`
- `evidence/a11y-i18n-responsive/CYBA-577-admin-3003-20260606T072828Z/audit-results.json`

Context7 docs checked: N/A - manual UI/accessibility visual finding.

### BUG-002 - Client floating icon button has no accessible name

Severity: P2
Type: accessibility bug
Surface: `client-frontend`
Environment: local dev `http://127.0.0.1:9001`, Chromium via Playwright headless, anonymous, `390x844`, `768x1024`, `1366x768`

Steps to reproduce:

1. Start client with `NEXT_TELEMETRY_DISABLED=1 npm run dev -w frontend`.
2. Open `http://127.0.0.1:9001/en-EN/login` at `390x844`.
3. Inspect visible controls or run a screen-reader/accessibility smoke.
4. Repeat on `http://127.0.0.1:9001/ar-SA/pricing` at `390x844` and `http://127.0.0.1:9001/en-EN/login` at `768x1024`.

Expected:

- Every visible icon-only button should expose a meaningful accessible name, for example through `aria-label`, `aria-labelledby`, or visible text.

Actual:

- A visible bottom-left floating `button` at `48x48` has empty text and empty accessible name.
- DOM audit records the nameless button on client login/pricing/dashboard smoke cases, including `en-EN`, `ru-RU`, and `ar-SA`.
- Touch size is acceptable and the control is not clipped; the defect is the missing accessible name.

Evidence:

- `evidence/a11y-i18n-responsive/CYBA-577-client-partner-20260606T072341Z/audit-results.json`
- `evidence/a11y-i18n-responsive/CYBA-577-client-partner-20260606T072341Z/screenshots/CYBA-577__client-frontend__anonymous__en-EN__mobile390__login-after-3s__20260606T072341Z.png`
- `evidence/a11y-i18n-responsive/CYBA-577-client-partner-20260606T072341Z/screenshots/CYBA-577__client-frontend__anonymous__ar-SA__mobile390__-pricing__20260606T072341Z.png`

Context7 docs checked: N/A - manual UI/accessibility finding.

## Product Gaps / Not Tested

- Admin RTL smoke is not available: admin supports only `ru-RU` and `en-EN`; `http://127.0.0.1:3003/ar-SA/login` redirects to `http://127.0.0.1:3003/ru-RU/login`.
- Partner RTL smoke is not available: partner supports only `ru-RU` and `en-EN`; `http://127.0.0.1:3002/ar-SA/login` redirects to `http://127.0.0.1:3002/ru-RU/login`.
- Authenticated client/partner/admin dashboards, RBAC states, payment/VPN/OAuth/email/Telegram flows, and account-dependent long-text states remain not tested because no approved synthetic accounts or fixtures were provided through a secret-safe channel.
- Managed Paperclip runtime workspace was not available for this issue; smoke used local dev servers in this checkout.
- Console/server logs included local backend proxy connection failures for anonymous client passkey policy calls to `127.0.0.1:8000`; those were not classified as a11y/i18n/responsive bugs because the anonymous pages rendered and no production data was used.

## Coverage Matrix

| Surface | Routes checked | Locales | Viewports | State | Result |
|---|---|---|---|---|---|
| Client | `/login`, `/pricing`, `/dashboard` status/DOM smoke | `en-EN`, `ru-RU`, `ar-SA` | `390x844`, `768x1024`, `1366x768`, `1440x900` | anonymous | P2 unnamed floating button; no overflow/clipping/unlabeled inputs; `ar-SA` RTL text smoke passed |
| Admin | `/login`, `/dashboard` status/DOM smoke | `en-EN`, `ru-RU`; `ar-SA` redirect smoke | `390x844`, `768x1024`, `1440x900` | anonymous | P1 visual login form issue; no overflow/clipping/unlabeled inputs in DOM audit |
| Partner | `/login`, `/application` | `en-EN`, `ru-RU`; `ar-SA` redirect smoke | `390x844`, `768x1024`, `1440x900` | anonymous | Passed within anonymous scope |

## Sanitization Review

- PASS: screenshots contain anonymous login/public UI only.
- PASS: no cookies, storage state, HAR, trace, video, `.env`, payment data, production PII, Telegram `initData`, JWT, refresh token, or password values were saved.
- PASS: strict value scan over `evidence/a11y-i18n-responsive/**` found no bearer/JWT/token/API-key/secret/password assignments. Broader word scan produced only benign policy labels such as `Cookie Policy` and manifest text.

## Recommended Handoff

- [CYBA-583](/CYBA/issues/CYBA-583): Prism Admin Partner Frontend Engineer owns the P1 admin login visibility fix and revalidation.
- [CYBA-584](/CYBA/issues/CYBA-584): Neon Customer Frontend Engineer owns the P2 client floating icon accessible-name fix and revalidation.
- QA Lead / Flow Mapper: treat this smoke as complete, but keep final acceptance gated on the two follow-up findings above.
