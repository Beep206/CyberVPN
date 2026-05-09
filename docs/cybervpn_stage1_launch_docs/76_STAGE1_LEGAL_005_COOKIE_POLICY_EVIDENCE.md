> CyberVPN Stage 1 Evidence
> ID: S1-LEGAL-005
> Date: 2026-05-05
> Scope: local cookie-policy candidate, frontend/i18n guardrails and owner-approved S1 legal/text closure.

# S1-LEGAL-005 Cookie Policy Evidence

## Result

`S1-LEGAL-005` is completed locally for implementation readiness and S1 owner-approved legal/text closure.

The repository now contains a Stage 1 Cookie Policy candidate for Controlled Public Beta. Owner-approved S1 legal/text closure is recorded in `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md`. Deployed browser cookie inventory, redacted `Set-Cookie` proof, consent evidence where non-essential storage is enabled and observability PII evidence remain security/observability evidence.

## Implemented surfaces

| Surface | Result |
|---|---|
| Public route | Added `/cookie-policy` under the localized marketing app |
| i18n namespace | Added `CookiePolicy` and generated bundles for 39 locales |
| Primary copy | English and Russian S1 candidate copy added |
| Secondary locales | English fallback copy added to avoid missing or unsafe legal text |
| Footer | Added legal footer link to `/cookie-policy` |
| Tests | Added `stage1-cookie-policy-copy.test.ts` |

## S1 Cookie/Storage Model

The S1 candidate discloses the storage categories visible in the current monorepo:

- locale/routing state through `next-intl` where enabled, such as `NEXT_LOCALE`;
- backend web auth cookies: `access_token`, `refresh_token`, `{realm}_access_token`, `{realm}_refresh_token`;
- configured auth cookie posture: `HttpOnly`, `SameSite=Lax`, `Secure` in production, `path /api`, default access lifetime `15 minutes`, default refresh lifetime `7 days`;
- short-lived auth flow cookies: `oauth_tx`, `pending_2fa`, `oauth_result`;
- CSRF mitigation through `Origin`/`Referer` validation for unsafe cookie-authenticated requests;
- Sentry/Web Vitals/internal traffic telemetry and Telegram Mini App runtime analytics;
- Telegram Mini App runtime data and Telegram-controlled storage boundaries;
- payment/OAuth/provider-side storage on third-party domains where a provider is enabled.

The policy does not promise absence of cookies or tracking. It states that non-essential analytics, marketing, profiling and advertising storage must stay disabled by default until consent, legal approval and evidence exist.

## Default S1 Consent Rule

| Category | S1 default |
|---|---|
| Strictly necessary auth/security/routing/checkout storage | Allowed where required to provide the requested service |
| Sentry/Web Vitals/internal observability | Allowed only with PII controls and S1 observability evidence |
| GA4/PostHog/marketing pixels/ad retargeting | Disabled unless separately approved, consented where required and evidenced |
| Telegram-controlled cookies/storage | Disclosed as outside CyberVPN control |
| New SDK/cookie/storage provider | Requires owner approval and updated cookie inventory before public use |

## External Sources Checked

These sources were used as implementation/legal-copy guardrails, not as legal approval:

- ICO Storage and Access Technologies guidance, updated April 29, 2026: https://ico.org.uk/for-organisations/direct-marketing-and-privacy-and-electronic-communications/guidance-on-the-use-of-storage-and-access-technologies/
- European Commission cookies policy examples and cookie-category structure: https://commission.europa.eu/cookies-policy_en
- GDPR Article 13 transparency baseline: https://eur-lex.europa.eu/eli/reg/2016/679/art_13/oj/eng
- Next.js `generateMetadata` API reference for the App Router metadata pattern: https://nextjs.org/docs/app/api-reference/functions/generate-metadata

## Commands executed

```bash
npm run prepare:i18n
npm run test:run -- stage1-cookie-policy-copy
npm run test:run -- stage1-cookie-policy-copy stage1-refund-policy-copy stage1-acceptable-use-copy stage1-privacy-policy-copy stage1-terms-copy
npm run lint -- 'src/app/[locale]/(marketing)/cookie-policy/page.tsx' src/widgets/footer.tsx src/i18n/client-namespaces.ts src/shared/lib/__tests__/stage1-cookie-policy-copy.test.ts
npm audit --audit-level=high
```

## Verification summary

| Check | Result |
|---|---|
| i18n bundle generation | Passed; 39 locale bundles generated |
| Cookie Policy copy tests | Passed; 1 file and 4 tests |
| Legal-copy regression pack | Passed; 5 files and 18 tests across Cookie, Refund, AUP, Privacy and Terms |
| Targeted ESLint | Passed |
| Frontend high-severity audit gate | Passed; only existing moderate Next/PostCSS advisory remains |
| Root high-severity audit gate | Passed; only existing moderate Next/PostCSS advisory remains |
| Unsafe cookie/legal promise scan | Passed; no unsafe phrases found in Cookie Policy surfaces |
| Targeted secret pattern scan | Passed; no token/secret patterns found in Cookie Policy surfaces |
| `git diff --check` | Passed for touched code/docs paths |

## Remaining go-live blockers

| Blocker | Required before public beta |
|---|---|
| Final legal review | Owner/legal approval of Cookie Policy together with Terms, Privacy, AUP and Refund Policy |
| Browser inventory | Deployed browser inventory for public site, cabinet, auth, OAuth, Telegram Mini App, checkout, logout and admin flows |
| `Set-Cookie` proof | Redacted HTTPS evidence for cookie names, domain/path, `Secure`, `HttpOnly`, `SameSite` and expiry/max-age |
| Non-essential consent | Consent banner/settings evidence if GA4, PostHog, marketing pixels, profiling or advertising storage is enabled |
| Observability PII proof | Sentry replay/text/media masking, `sendDefaultPii=false`, `beforeSend` scrubbing, payload review and log redaction evidence |
| Localization | Decide whether English fallback is acceptable for S1 or provide reviewed translations |

## Files changed

| File / path | Purpose |
|---|---|
| `frontend/src/app/[locale]/(marketing)/cookie-policy/page.tsx` | Public localized Cookie Policy page |
| `frontend/messages/*/CookiePolicy.json` | Cookie Policy copy for all locales; EN/RU primary, EN fallback elsewhere |
| `frontend/messages/*/footer.json` | Footer legal link label |
| `frontend/scripts/generate-message-bundles.mjs` | Adds `CookiePolicy` namespace |
| `frontend/src/i18n/client-namespaces.ts` | Includes `CookiePolicy` in marketing namespace list |
| `frontend/src/widgets/footer.tsx` | Adds `/cookie-policy` legal link |
| `frontend/src/shared/lib/__tests__/stage1-cookie-policy-copy.test.ts` | Copy and guardrail tests |

## Next ID

Next ID to execute: `S1-FE-010` - Frontend bundle/env scan. Legal/text work is closed by `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md`.
