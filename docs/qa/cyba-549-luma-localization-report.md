# CYBA-549 Luma Localization Report

Date: `2026-06-05`
Owner: `Luma Localization Translator`
Issue: `CYBA-549`
Parent: `CYBA-540`

## 1. Executive summary

Closed the localization part of the P2 a11y/i18n/responsive backlog for the client frontend:

- `ar-SA` auth and pricing no longer rely on broad English fallback text for public login/register/password/OAuth/Telegram/profile and pricing plan/add-on/catalog strings.
- `ru-RU` public mixed-copy cleanup was applied to auth, pricing, landing, features, footer and status namespaces.
- Generated runtime bundles were refreshed for the changed locale sources.

Changed source paths:

- `frontend/messages/ar-SA/auth.json`
- `frontend/messages/ar-SA/Pricing.json`
- `frontend/messages/ru-RU/auth.json`
- `frontend/messages/ru-RU/Pricing.json`
- `frontend/messages/ru-RU/landing.json`
- `frontend/messages/ru-RU/Features.json`
- `frontend/messages/ru-RU/footer.json`
- `frontend/messages/ru-RU/Status.json`
- `frontend/src/i18n/messages/generated/ar-SA.json`
- `frontend/src/i18n/messages/generated/ru-RU.json`

Representative before/after examples:

- `frontend/messages/ar-SA/auth.json` `login.title`: `Sign In` -> `تسجيل الدخول`
- `frontend/messages/ar-SA/Pricing.json` `periods.label`: `Choose your billing term` -> `اختر مدة الفوترة`
- `frontend/messages/ru-RU/Pricing.json` `labels.trafficFairUse`: `Fair-use policy` -> `Политика добросовестного использования`
- `frontend/messages/ru-RU/Status.json` `subtitle`: `Public release monitoring surface` -> `Поверхность мониторинга публичного релиза`

## 2. Decisions needed from Board

Нет. Эти изменения остаются внутри уже одобренного localization/a11y polish scope.

## 3. Proposed next tasks

- `CYBA-550`: Quill QA / Scribe and Astra acceptance should revalidate `390x844`, `768x1024`, `1440x900`, including `ar-SA` RTL auth/pricing smoke and `ru-RU` public pages.
- Engineering owners should keep any mobile input clipping/focus-ring implementation evidence separate from this localization report.

## 4. Risks

- Arabic strings are longer than the previous English fallback on several CTA/helper labels; visual RTL screenshot revalidation is still required.
- Some technical tokens intentionally remain untranslated where they are product/protocol identifiers: `CyberVPN`, `Telegram`, `OAuth`, `VLESS Reality`, `XHTTP`, `Stealth`, `IP`, `SKU`, `backend`.
- This heartbeat did not verify authenticated flows, payment, Telegram `initData`, VPN provisioning, or production data.

## 5. Approval requests

Нет.

## 6. Verification plan

Completed in this heartbeat:

- `jq empty frontend/messages/ar-SA/auth.json frontend/messages/ar-SA/Pricing.json frontend/messages/ru-RU/auth.json frontend/messages/ru-RU/Pricing.json frontend/messages/ru-RU/landing.json frontend/messages/ru-RU/Features.json frontend/messages/ru-RU/footer.json frontend/messages/ru-RU/Status.json`
- Custom key/ICU placeholder parity check against `en-EN` for touched namespaces: PASS for `ar-SA/auth`, `ar-SA/Pricing`, `ru-RU/auth`, `ru-RU/Pricing`, `ru-RU/landing`, `ru-RU/Features`, `ru-RU/footer`, `ru-RU/Status`.
- English fallback phrase scan over touched files: no hits for the known regression phrases from CYBA-460/CYBA-549.
- `npm --prefix frontend run prepare:i18n`: PASS, generated 39 locale bundles.
- `npm --prefix frontend run check:i18n:s1`: PASS.

Documentation evidence:

- Context7 MCP checked for `next-intl`: unavailable due monthly quota.
- `ctx7 library next-intl "message JSON ICU placeholders and plural syntax"` returned `/amannn/next-intl`.
- Official `next-intl` docs checked: `https://next-intl.dev/docs/usage/messages`, including JSON messages and ICU message syntax sections.

## 7. What was not done

- No runtime layout code was changed by Luma.
- No screenshots were captured in this heartbeat.
- No full build or Playwright matrix was run; this should remain with final QA revalidation.
- No production secrets, customer data, payment data, Telegram `initData`, VPN provisioning, or deployment actions were touched.
