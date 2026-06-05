# Accessibility, i18n and Responsive Review

Issue: [CYBA-460](/CYBA/issues/CYBA-460)
Parent audit: [CYBA-451](/CYBA/issues/CYBA-451)
Date: `2026-06-04`
Reviewer: `qa-accessibility-i18n-reviewer`

## Scope Tested

Environment:

- Client approved local-stage: `http://127.0.0.1:13000`
- Admin approved local-stage: `http://127.0.0.1:13001`
- Backend health: `http://127.0.0.1:18080/health`
- Partner local-dev only: `http://127.0.0.1:3002`; no approved partner stage container was available
- Browser: Chromium via Playwright headless
- User state: anonymous only; no cookies, storage state, HAR, traces, JWT, Telegram `initData`, payment data, or production data saved

Viewport matrix:

- `1440x900`
- `1366x768`
- `768x1024`
- `390x844`

Locale matrix:

- Client: `en-EN`, `ru-RU`, `ar-SA` RTL smoke
- Admin: `en-EN`, `ru-RU`; `ar-SA` redirects to `ru-RU` because `admin/src/i18n/config.ts` has only `ru-RU` and `en-EN`
- Partner: `en-EN`, `ru-RU`; `ar-SA` redirects to `ru-RU` because `partner/src/i18n/config.ts` has only `ru-RU` and `en-EN`

Evidence:

- `evidence/a11y-i18n-responsive/manifest.md`
- `evidence/a11y-i18n-responsive/audit-results.json`
- `evidence/a11y-i18n-responsive/screenshots/**`
- Revalidation after gate resolution: `evidence/a11y-i18n-responsive/revalidation/20260604T162940Z/manifest.md`
- Revalidation raw results: `evidence/a11y-i18n-responsive/revalidation/20260604T162940Z/revalidation-results.json`

Docs evidence:

- Context7 docs checked: unavailable - MCP quota exceeded.
- Fallback docs checked: `ctx7 docs /microsoft/playwright` for screenshot, viewport and keyboard APIs.
- Web Interface Guidelines fetched from `https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md` on `2026-06-04`.

## Revalidation After Readiness Gate Resolution

Triggered by [CYBA-460](/CYBA/issues/CYBA-460) `issue_blockers_resolved` wake on `2026-06-04`.

Scope:

- Client/admin anonymous bounded smoke only; no authenticated, payment, VPN, OAuth, email or Telegram flows were exercised.
- Browser: Chromium via Playwright headless.
- Viewports: `390x844` and `1440x900` targeted smoke.
- Locales: client `en-EN`, `ru-RU`, `ar-SA`; admin `en-EN`, `ru-RU`, `ar-SA` redirect smoke.
- Backend health: `http://127.0.0.1:18080/health`.

Result:

- PASS: 8 client/admin cases loaded at `200`.
- PASS: backend health returned `200`.
- PASS: DOM smoke found no page-level horizontal overflow, no unlabeled visible inputs and no nameless visible controls in the revalidated cases.
- PASS: 5 new anonymous/public screenshots saved under `evidence/a11y-i18n-responsive/revalidation/20260604T162940Z/screenshots/`.
- PASS: strict token/value scan over new non-binary revalidation artifacts found no bearer/JWT/token/cookie/password/secret/API-key values.
- No new P0/P1 issue was found. The original 3 P2 bugs remain the active findings and follow-up ownership remains unchanged.

Partner revalidation note:

- Partner local-dev was probed but not revalidated in this heartbeat because `http://127.0.0.1:3002/en-EN/login` was not serving and `npm run dev` in `partner/` failed during `partner/scripts/ensure-local-next-deps.sh`.
- Failure reason: `npm ci` lockfile/package mismatch, missing `@simplewebauthn/browser@13.3.0` in the lock file.
- I did not update dependencies or lockfiles in this QA issue. Existing partner evidence remains `local-dev only` from the earlier pass, and the absence of an approved partner stage container remains a limitation.

Context7 docs checked: unavailable - monthly quota exceeded; fallback `ctx7 docs /microsoft/playwright` checked for viewport, `newContext`, `page.goto` and screenshot APIs.

## Result Summary

No P0/P1 issue was found in the anonymous/read-only a11y/i18n/responsive smoke.

Found bugs:

| ID | Severity | Area | Summary |
|---|---|---|---|
| BUG-CYBA-460-001 | P2 | client i18n/RTL | `ar-SA` client auth/pricing pages are declared RTL but remain largely English |
| BUG-CYBA-460-002 | P2 | mobile responsive/a11y | Login password reveal/input adornments are clipped or off-card on `390x844` |
| BUG-CYBA-460-003 | P2 | keyboard focus | Login text inputs have weak/non-obvious focus indication |

Positive checks:

- Client/admin/partner anonymous login surfaces loaded at `200` for `en-EN` and `ru-RU`.
- Representative pages had `html` scroll width equal to viewport width in the DOM audit; no page-level horizontal scroll was detected.
- Skip links were present on tested login/marketing pages.
- Visible form inputs had programmatic labels in the DOM audit.
- Icon-only theme/language controls had accessible names in the DOM audit.

## Bugs

### BUG-CYBA-460-001 - Client `ar-SA` pages are RTL but largely English

Severity: P2
Type: i18n/RTL bug
Surface: `client-frontend`
Environment: local-stage `http://127.0.0.1:13000`, Chromium, anonymous, `ar-SA`, `390x844` and `1440x900`

Steps to reproduce:

1. Open `http://127.0.0.1:13000/ar-SA/login`.
2. Set viewport to `390x844`.
3. Observe heading, subtitle, field labels, buttons and helper links.
4. Open `http://127.0.0.1:13000/ar-SA/pricing`.
5. Observe plan duration labels, selected-term copy and price card text.

Expected:

- `ar-SA` should render a coherent Arabic RTL experience for user-facing auth and pricing text.
- English should remain only for brand names, protocol names, code tokens or explicit `translate="no"` content.

Actual:

- `html lang="ar-SA"` and `dir="rtl"` are set, but login renders English strings such as `Sign In`, `Access your secure connection`, `Email address`, `Password`, `Remember me`, `Forgot password?`, and `Sign up`.
- Pricing renders English strings such as `CHOOSE YOUR BILLING TERM`, `DAYS 30`, `SELECTABLE TERM`, `BEST VALUE`, `BASIC`, and English supporting copy.
- Source evidence confirms the issue is data-backed: `frontend/messages/ar-SA/auth.json` contains many English values under `login`.

Evidence:

- `evidence/a11y-i18n-responsive/screenshots/client-frontend/login/CYBA-460__client-frontend__anonymous-rtl-smoke__ar-SA__mobile390__login__20260604T160112Z.png`
- `evidence/a11y-i18n-responsive/screenshots/client-frontend/pricing/CYBA-460__client-frontend__anonymous-rtl-smoke__ar-SA__mobile390__pricing__20260604T160112Z.png`
- `evidence/a11y-i18n-responsive/audit-results.json`

Context7 docs checked: N/A - manual UI/i18n finding; repo-local locale messages confirm the content mismatch.

### BUG-CYBA-460-002 - Mobile login adornments are clipped/off-card

Severity: P2
Type: responsive/accessibility bug
Surfaces: `client-frontend`, `partner-portal`; same layout risk visible in `admin-panel` input adornments
Environment: client/admin local-stage, partner local-dev, Chromium, anonymous, `ru-RU`, `390x844`

Steps to reproduce:

1. Open `http://127.0.0.1:13000/ru-RU/login` at `390x844`.
2. Observe the password field and password reveal button area.
3. Open `http://127.0.0.1:3002/ru-RU/login` at `390x844`.
4. Observe the email/password terminal-prefix adornments and password reveal area.
5. Repeat with `http://127.0.0.1:13001/ru-RU/login` for admin input adornments.

Expected:

- Input text, terminal-prefix adornments and password reveal controls should remain fully inside the card/input bounds.
- Touch targets should be fully visible and at least `44x44` where they are interactive.

Actual:

- Client mobile login reports password reveal control at `x=368`, `width=38`, `right=406` against a `390px` viewport.
- Partner mobile login reports password reveal control at `x=390`, `width=38`, `right=428` against a `390px` viewport.
- Admin mobile login reports the password reveal control at `x=410`, `width=40`, `right=450` against a `390px` viewport in the DOM audit.
- Partner/admin screenshots show terminal-prefix text clipped at the left side of inputs; the reveal control is not fully visible.

Evidence:

- `evidence/a11y-i18n-responsive/screenshots/client-frontend/login/CYBA-460__client-frontend__anonymous__ru-RU__mobile390__login__20260604T160112Z.png`
- `evidence/a11y-i18n-responsive/screenshots/partner-portal/login/CYBA-460__partner-portal__anonymous-local-dev__ru-RU__mobile390__login__20260604T160112Z.png`
- `evidence/a11y-i18n-responsive/screenshots/admin-panel/login/CYBA-460__admin-panel__anonymous__ru-RU__mobile390__login__20260604T160112Z.png`
- `evidence/a11y-i18n-responsive/audit-results.json`

Context7 docs checked: N/A - manual UI/responsive finding; Web Interface Guidelines touch/layout rules were used as QA criteria.

### BUG-CYBA-460-003 - Login text inputs do not show a clear focus indication

Severity: P2
Type: keyboard accessibility bug
Surfaces: `client-frontend`, `admin-panel`, `partner-portal`
Environment: Chromium, anonymous, `ru-RU`, `390x844`

Steps to reproduce:

1. Open any of:
   - `http://127.0.0.1:13000/ru-RU/login`
   - `http://127.0.0.1:13001/ru-RU/login`
   - `http://127.0.0.1:3002/ru-RU/login`
2. Use keyboard `Tab` until the email field receives focus, or focus the first input programmatically.
3. Compare the field focus state to the visible focus rings on header buttons and CTA buttons.

Expected:

- Focused text inputs should have a clear visible focus state comparable to other interactive controls.
- The focus state should not rely only on subtle color/opacity changes or ambiguous decorative artifacts.

Actual:

- DOM audit recorded input focus styles as effectively transparent box-shadow/outline values on tested login fields.
- Focus screenshots show weak or ambiguous focus indication: the field changes are subtle and in some cases appear as a horizontal artifact through the input rather than a distinct focus ring.

Evidence:

- `evidence/a11y-i18n-responsive/screenshots/client-frontend/focus/CYBA-460__client-frontend__anonymous__ru-RU__mobile390__email-focus__20260604T160736Z.png`
- `evidence/a11y-i18n-responsive/screenshots/admin-panel/focus/CYBA-460__admin-panel__anonymous__ru-RU__mobile390__email-focus__20260604T160736Z.png`
- `evidence/a11y-i18n-responsive/screenshots/partner-portal/focus/CYBA-460__partner-portal__anonymous__ru-RU__mobile390__email-focus__20260604T160736Z.png`
- `evidence/a11y-i18n-responsive/audit-results.json`

Context7 docs checked: N/A - manual UI/a11y finding; Web Interface Guidelines focus-state rules were used as QA criteria.

## Product Gaps / Not Bugs

- Admin RTL smoke is not available in this pass: `admin/src/i18n/config.ts` declares only `ru-RU` and `en-EN`, and `ar-SA` requests redirect to `ru-RU`.
- Partner RTL smoke is not available in this pass: `partner/src/i18n/config.ts` declares only `ru-RU` and `en-EN`, and `ar-SA` requests redirect to `ru-RU`.
- Partner evidence is `local-dev` only. The operator handoff said the partner stage container was not found, so these captures should not be treated as full staging approval.
- Authenticated client/partner/admin dashboards, RBAC states, payment/VPN/OAuth/email/Telegram flows, and account-dependent long-text states remain blocked/not-tested because no approved synthetic accounts or fixtures were provided through a secret-safe channel.
- Console notes included local `401`/`403` resource messages on some anonymous pages. I did not classify those as bugs in this review because the tested pages still rendered at `200` and no user-facing failure was observed in the accessibility/i18n/responsive scope.

## Coverage Matrix

| Surface | Routes checked | Locales | Viewports | State | Result |
|---|---|---|---|---|---|
| Client | `/`, `/login`, `/pricing`, `/dashboard` status; `/login` and `/pricing` screenshots | `en-EN`, `ru-RU`, `ar-SA` | `1440x900`, `1366x768`, `768x1024`, `390x844` | anonymous | Tested with bugs above |
| Admin | `/login`, `/dashboard` status; `/login` screenshots | `en-EN`, `ru-RU`; `ar-SA` redirect smoke | `1440x900`, `1366x768`, `768x1024`, `390x844` | anonymous | Tested with bugs/RTL gap above |
| Partner | `/`, `/login`, `/dashboard`, `/application` status; `/login` and root redirect screenshots | `en-EN`, `ru-RU`; `ar-SA` redirect smoke | `1440x900`, `1366x768`, `768x1024`, `390x844` | anonymous local-dev | Limited evidence only |

## Sanitization Review

- PASS: screenshots contain anonymous login/public UI only.
- PASS: `audit-results.json` redacts token-like query parameters and bearer/JWT-like strings.
- PASS: no cookies, storage state, HAR, trace, video, `.env`, payment data, production PII, Telegram `initData`, JWT, refresh token, or password values were saved.

## Recommended Handoff

- [CYBA-469](/CYBA/issues/CYBA-469): Luma Localization Translator owns client `ar-SA` auth/pricing localization follow-up.
- [CYBA-470](/CYBA/issues/CYBA-470): Neon Customer Frontend Engineer owns client mobile login input/adornment/focus follow-up.
- [CYBA-471](/CYBA/issues/CYBA-471): Prism Admin Partner Frontend Engineer owns admin/partner mobile login input/adornment/focus follow-up.
- QA Lead / Flow Mapper: keep authenticated/RBAC/payment/VPN/Telegram/OAuth coverage blocked until synthetic accounts and integration fixtures are available.
