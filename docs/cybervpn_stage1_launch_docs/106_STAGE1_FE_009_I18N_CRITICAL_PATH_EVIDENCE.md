> CyberVPN Launch Program
> Версия: 0.1-draft
> Дата evidence: 2026-05-07
> Backlog ID: `S1-FE-009`
> Статус: PASS for local/no-cost i18n critical-path validation. Not a full human translation approval for every locale.

# S1-FE-009 i18n Critical-Path Validation Evidence

## Purpose

`S1-FE-009` validates that the Stage 1 customer-critical frontend message surface does not break for enabled locales.

The practical S1 decision is:

- `en-EN` is the default source-of-truth fallback locale.
- `ru-RU` is the second directly reviewed S1 locale.
- All enabled locales must be runtime fallback-complete for critical S1 flows.
- Secondary locales must not be marketed as fully translated until a later human locale review closes that claim.

This follows the current `next-intl` model in the app: locale-specific messages are loaded and merged over `en-EN` fallback messages in `frontend/src/i18n/request.ts`.

## Critical Message Files Audited

The local audit covers these S1 critical message files:

```text
auth.json
dashboard.json
servers.json
subscriptions.json
wallet.json
payment-history.json
settings.json
devices.json
MiniApp.json
Pricing.json
HelpCenter.json
Status.json
Download.json
Terms.json
Privacy.json
AcceptableUse.json
RefundPolicy.json
CookiePolicy.json
```

These files cover registration/login/recovery, customer dashboard states, server/config access, subscriptions, wallet/payment history, settings/devices, Telegram Mini App, pricing/help/status/download and public legal-policy pages.

## Changes Made

| Path | Change |
|---|---|
| `frontend/scripts/stage1-i18n-critical-path-audit.mjs` | Added deterministic local audit for enabled locales, fallback coverage, direct EN/RU coverage, unsafe placeholders and ICU argument parity |
| `frontend/package.json` | Added `precheck:i18n:s1` and `check:i18n:s1` scripts |
| `frontend/messages/ru-RU/devices.json` | Added missing Russian devices namespace copy |
| `frontend/src/i18n/messages/generated/ru-RU.json` | Regenerated locale bundle through `npm run prepare:i18n` |

## Local Audit Result

Command:

```bash
npm --prefix frontend run check:i18n:s1
```

Result:

```text
PASS
Enabled locales: 39
Default fallback locale: en-EN
Critical message files: 18
Default critical string keys: 1512
Runtime fallback-merged checks: 58968
Direct reviewed S1 locales: en-EN, ru-RU; threshold >=85%
en-EN direct source coverage: 1512/1512 (100.0%)
ru-RU direct source coverage: 1351/1512 (89.4%)
Fallback-supported locales with at least one default en-EN critical key: 38
PASS: all enabled locales are runtime fallback-complete for S1 critical paths.
PASS: direct reviewed S1 locales meet the local launch coverage threshold.
PASS: critical locale overrides keep ICU argument parity with the default locale.
```

## Important Limitation

This is not proof that all 39 enabled locales are fully translated by a human reviewer.

Current direct source coverage for most secondary locales is `662/1512 (43.8%)` across the audited critical message files. The missing direct files commonly include:

```text
subscriptions.json
wallet.json
payment-history.json
settings.json
devices.json
```

This is acceptable for S1 only because runtime fallback coverage is proven and because S1 does not claim full translation quality for every enabled locale. If the project wants to publicly claim full support for a specific secondary locale, that locale needs a separate human translation pass and audit.

## Go-Live Requirements Still Open

- Deployed staging/RC browser spot-check for `en-EN` and `ru-RU` on registration/login, dashboard, pricing, wallet, devices, Mini App and legal/status pages.
- At least one RTL smoke check for an enabled RTL locale such as `ar-SA` or `fa-IR`.
- Product decision before public marketing copy: secondary locales are `fallback-supported`, not `fully translated`.
- Repeat `npm --prefix frontend run check:i18n:s1` on the immutable RC tag.

## Verification Commands

| Check | Result |
|---|---|
| `npm --prefix frontend run check:i18n:s1` | PASS |
| `npm --prefix frontend run lint -- scripts/stage1-i18n-critical-path-audit.mjs src/i18n/config.ts src/i18n/request.ts` | PASS |
| `npm --prefix frontend run test:run -- src/i18n/__tests__/request.test.ts src/shared/lib/__tests__/locale-rollout-policy.test.ts` | PASS: 2 files, 4 tests |
| `npm --prefix frontend run build` | PASS: Next.js 16.2.4, Cache Components enabled, 2801 static pages generated |
| `npm --prefix frontend audit --omit=dev --audit-level=high` | PASS for high/critical; existing low/moderate advisories remain `icu-minify`, `next-intl` and `postcss` through `next` |
| High-confidence secret scan over touched S1-FE-009 files | PASS: no matches |
| Static dangerous-pattern scan over the new audit script and evidence doc | PASS: no matches |
| `git diff --check` over touched S1-FE-009 files | PASS |
| `docker ps --format '{{.Names}}\t{{.Status}}'` | PASS: no running containers reported |

## Documentation References Used

- `next-intl` messages usage: https://next-intl.dev/docs/usage/messages
- `next-intl` TypeScript workflow: https://next-intl.dev/docs/workflows/typescript
- `next-intl` messages workflow: https://next-intl.dev/docs/workflows/messages

## Acceptance Result

`S1-FE-009` is **completed locally** for Stage 1 i18n critical-path validation.

The project can proceed with S1 frontend work under this rule: `en-EN` and `ru-RU` are the reviewed S1 launch locales; all other enabled locales are allowed only as fallback-supported unless separately reviewed.

Next ID to execute after `S1-FE-001` and `S1-PAY-011`: `S1-PAY-013` - PayRam readiness if enabled.
