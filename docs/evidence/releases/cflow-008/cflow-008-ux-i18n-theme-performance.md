# CFLOW-008 UX/i18n/theme/performance QA Pack

Date: 2026-05-28

## Scope

CFLOW-008 covers production-facing UX QA for:

- light and dark theme screenshots;
- desktop and mobile public pages;
- Telegram Mini App viewport behavior;
- auth form focus performance;
- text overflow and basic contrast checks across representative locales.

## Automated Browser Coverage

Tooling:

- Python Playwright 1.55.0
- Chromium headless
- production URLs under `cyber-vpn.net` and `my.cyber-vpn.net`

Evidence files:

- Raw JSON: `docs/evidence/releases/cflow-008/cflow-008-results.json`
- Screenshots: `docs/evidence/releases/cflow-008/screenshots/`
- Scenarios captured: 46
- Screenshots captured: 45

Covered surfaces:

- Public: `/ru-RU`, `/ru-RU/pricing`, `/ru-RU/features`, `/ru-RU/download`, `/ru-RU/network`
- Locale sample: `en-EN`, `ru-RU`, `de-DE`, `ar-SA`, `zh-CN`, `sv-SE`
- Mini App: `/ru-RU/miniapp/home`, `/plans`, `/profile`, `/referral`
- Auth: `/ru-RU/login`, `/register`, `/verify`

## Findings

### Fixed In This Batch

1. Registration legal links caused CORS/RSC prefetch errors from `my.cyber-vpn.net`.

   Fix: registration Terms and Privacy links now use explicit public URLs on `https://cyber-vpn.net/{locale}/...` with prefetch disabled.

2. Auth desktop focus performance showed frame gaps around 116 ms on login/register password/email focus.

   Fix: the auth WebGL canvas now switches to `frameloop="demand"` while an input, textarea or select is focused. This keeps the scene present but avoids continuous WebGL work while the user is typing.

3. Light theme live-status green was too bright on light backgrounds.

   Fix: light theme status variables now use darker accessible OKLCH values while dark theme keeps vivid neon colors.

4. Public pricing badges used dark-theme neon colors in light mode.

   Fix: tier badge text now has separate light-mode colors and keeps neon accents in dark mode.

### Non-Blocking Observations

1. Public and auth pages still produce unauthenticated 401/403 console noise for private bootstrap/capability calls when visited anonymously.

   Recommendation: treat as separate cleanup if we want a silent console for anonymous marketing pages. It is not a visual blocker.

2. The automated overflow detector reports skip-link overflow and several fixed-format pricing cards.

   Recommendation: keep monitoring with screenshots. No horizontal page scroll was detected in the tested scenarios.

3. One Arabic pricing screenshot timed out while Playwright waited for fonts.

   Recommendation: rerun manually if Arabic visual evidence is needed for sign-off. The page returned HTTP 200 and no horizontal scroll was detected.

## Acceptance Status

- Light theme black-rectangle regression: not reproduced.
- Mini App light/dark viewport: screenshots captured.
- Public mobile/desktop light/dark: screenshots captured.
- Auth focus jank: mitigated in code.
- Text overflow: no horizontal page scroll detected; fixed-format card overflow remains under watch.
- Representative locale coverage: captured for six locales.

## Follow-Up

- Rerun the QA pack after production deploy.
- Keep CFLOW-008 screenshots as baseline evidence for future theme/i18n regressions.
