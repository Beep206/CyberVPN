# CYBA-393 Passkey/WebAuthn localization review

Дата: 2026-06-03
Owner: Luma Localization Translator
Scope: `frontend`, `admin`, `partner` Passkey/WebAuthn user-facing copy after `CYBA-390` and `CYBA-391`.

## 1. Executive summary

Review выполнен для Passkey/WebAuthn copy на customer frontend, admin и partner web apps.

Проверенные source paths:

- `frontend/messages/en-EN/auth.json:18`, `frontend/messages/ru-RU/auth.json:14`
- `frontend/messages/en-EN/settings.json:47`, `frontend/messages/ru-RU/settings.json:47`
- `admin/messages/en-EN/auth.json:14`, `admin/messages/ru-RU/auth.json:14`
- `admin/messages/en-EN/security-admin.json:70`, `admin/messages/ru-RU/security-admin.json:70`
- `admin/messages/en-EN/security-admin.json:282`, `admin/messages/ru-RU/security-admin.json:282`
- `admin/messages/en-EN/navigation.json:129`, `admin/messages/ru-RU/navigation.json:129`
- `partner/messages/en-EN/auth.json:14`, `partner/messages/ru-RU/auth.json:14`
- `partner/messages/en-EN/partner.json:261`, `partner/messages/ru-RU/partner.json:257`
- `partner/messages/en-EN/partner.json:335`, `partner/messages/ru-RU/partner.json:331`

Functional/parser result: no placeholder mismatch found across reviewed Passkey keys. Critical placeholders remain intact:

- `frontend`: `{created}`, `{lastUsed}`, `{id}`, `{count}` where touched by surrounding Settings feedback.
- `admin`: `{label}`, `{value}`.
- `partner`: `{label}`, `{value}`.

Coverage result:

- `admin` and `partner`: source coverage complete for supported locales `en-EN` and `ru-RU`.
- `frontend`: direct source coverage for Passkey copy is complete for `en-EN` and `ru-RU`; 37 other enabled locales rely on runtime `en-EN` fallback for the new Passkey login/settings keys.
- `frontend/src/i18n/request.ts` deep-merges `defaultLocale` messages into non-default locale messages, so missing non-EN/RU source keys are a coverage/quality gap, not an observed runtime missing-message blocker.

Language quality result:

- `ru-RU` Passkey copy is understandable but has high English term density: `passkey`, `passkeys`, `security key`, `customer surface`, `credentials`, `compliance`, `workspace`, `raw credential data`, `principal`, `realm`.
- This is not a parser risk. It is a glossary/tone consistency risk for Mira CMO and QA screenshots.

## 2. Decisions needed from Board

No Board decision is required to close `CYBA-393`.

Non-blocking terminology decision for Mira CMO:

- Keep product term as `passkey/passkeys` in Russian UI, or localize to `ключ доступа/ключи доступа`.
- If `passkey` remains the glossary term, decide whether surrounding terms should still be localized: `security key` -> `аппаратный ключ безопасности`, `credentials` -> `учетные данные`, `compliance` -> `соответствие требованиям`, `workspace` -> `рабочая область`.

## 3. Proposed next tasks

1. Luma/Mira: approve Russian glossary for Passkey/WebAuthn terms before final public QA signoff.
2. Luma Localization: if Mira approves localization beyond `passkey`, update only `ru-RU` source locale files for `frontend`, `admin`, and `partner`; preserve all placeholders.
3. Luma Localization or a future locale batch owner: decide whether the 37 non-EN/RU `frontend` locales should receive direct Passkey translations or remain fallback-supported for this milestone.
4. Quill QA (`CYBA-394`): include a screenshot/readability pass for Russian admin/partner Passkey screens and customer settings/login, with attention to long mixed-language labels.

## 4. Risks

High:

- `frontend` direct source coverage gap: all non-`en-EN`/`ru-RU` customer locales are runtime fallback-supported but do not have direct source translations for 8 `Auth.login.passkey*` keys and 33 `Settings.cabinet.security.passkeys*` keys.

Medium:

- Russian copy is inconsistent in language mix. Examples:
  - `frontend/messages/ru-RU/settings.json:49`: `security key`
  - `frontend/messages/ru-RU/settings.json:51`: `customer surface`
  - `admin/messages/ru-RU/security-admin.json:70`: `credentials`, `compliance`
  - `admin/messages/ru-RU/security-admin.json:290`: `raw credential IDs`, `public keys`, `challenges`
  - `partner/messages/ru-RU/partner.json:259`: `workspace passkey coverage`, `raw credential data`
  - `partner/messages/ru-RU/partner.json:332`: `passkeys`, `workspace`

Low:

- `admin/src/stores/auth-store.ts` and `partner/src/stores/auth-store.ts` contain fallback string `Passkey login failed`, but current login clients set localized `passkeyGenericError`/specific keys with priority over store `error`.
- `frontend/src/app/[locale]/(dashboard)/layout.tsx:83` has `ErrorBoundary label="Passkey upgrade prompt"`; treat as a low-risk debug/fallback label unless QA sees it in user-facing error UI.

## 5. Approval requests

No code/runtime/security/payment approval requested.

Approval requested from Mira CMO only if copy edits are opened:

- Russian glossary policy for `passkey`, `security key`, `credential`, `compliance`, `workspace`.

## 6. Verification plan

Completed verification:

- `rg` inventory for Passkey/WebAuthn terms across `frontend/messages`, `admin/messages`, `partner/messages`, `frontend/src`, `admin/src`, `partner/src`.
- Structured JSON flatten/compare for source locale files:
  - `frontend/messages/*/{auth,settings}.json`
  - `admin/messages/{en-EN,ru-RU}/{auth,security-admin,navigation}.json`
  - `partner/messages/{en-EN,ru-RU}/{auth,partner,navigation}.json`
- Placeholder parity check for reviewed keys: no mismatches found.
- Generated bundle check:
  - `frontend/src/i18n/messages/generated/*.json`
  - `admin/src/i18n/messages/generated/{en-EN,ru-RU}.json`
  - `partner/src/i18n/messages/generated/{en-EN,ru-RU}.json`
- Runtime fallback evidence:
  - `frontend/src/i18n/request.ts` deep-merges `defaultLocale` (`en-EN`) into current locale messages.
- Command run:
  - `npm run check:i18n:s1 -w frontend`
  - Result: PASS. Audit reported 39 enabled locales, runtime fallback-merged checks `73359`, and "PASS: all enabled locales are runtime fallback-complete for S1 critical paths."

Context7 docs checked: N/A, no code/library/API changes were made.

## 7. What was not done

- No production data, secrets, deploy, auth behavior, payment behavior, VPN provisioning, or security permissions were touched.
- No locale strings were edited in this heartbeat; this was review/report scope.
- No screenshots were captured; Quill QA owns browser/user-facing verification in `CYBA-394`.
- No direct translations were added for the 37 fallback-supported customer locales.
