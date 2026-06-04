# CYBA-440 Passkey/WebAuthn QA Evidence

Date: 2026-06-04
QA: Quill QA
Workspace checked: `/srv/paperclip/data/instances/default/projects/b412bbf0-42d3-4803-913b-15951083d2fb/55092778-1c70-4f8a-aa61-869c6d0f33ae/_default/VPNBussiness-main`
Commit: `116407a` with dirty implementation changes from CYBA-435/CYBA-436/CYBA-437

## Scope And Data Safety

- Test data only; no production secrets, real customer/payment data, raw credential payloads, VPN credentials, or production deploy.
- Backend settings validation used synthetic values only: `REMNAWAVE_TOKEN=test-remnawave`, `JWT_SECRET=<synthetic-jwt-secret>`, `CRYPTOBOT_TOKEN=test-cryptobot`.
- Initial scoped CYBA-440 checkout at `4328a69c-.../_default/VPNBussiness-cyba216-telegram-ftl-parity` did not contain the passkey implementation/test files. Actual validation used the populated `VPNBussiness-main` workspace found under `55092778-.../_default`.

## Commands Run

| Area | Command | Result |
|---|---|---|
| Backend security/API | `REMNAWAVE_TOKEN=test-remnawave JWT_SECRET=<synthetic-jwt-secret> CRYPTOBOT_TOKEN=test-cryptobot uv run pytest tests/unit/test_passkey_challenges.py tests/unit/test_passkey_fresh_auth.py tests/integration/test_passkey_webauthn_api.py tests/contract/test_passkey_openapi_contract.py -q --no-cov` | PASS: `31 passed in 36.68s` |
| Customer frontend | `npm run test:run -w frontend -- src/features/auth/lib/passkey-fresh-auth.test.ts src/lib/api/__tests__/passkeys.test.ts src/widgets/settings-cabinet/__tests__/settings-cabinet-dashboard.test.tsx src/app/'[locale]'/'(auth)'/login/__tests__/login-client-passkeys.test.tsx` | PASS: `4 passed`, `36 passed` |
| Admin targeted | `npm run test:run -w admin -- src/features/auth/lib/passkey-webauthn.test.ts src/features/auth/lib/passkey-fresh-auth.test.ts src/lib/api/__tests__/passkeys.test.ts` | PASS: `3 passed`, `6 passed` |
| Partner targeted | `npm run test:run -w partner -- src/features/auth/lib/passkey-webauthn.test.ts src/features/auth/lib/passkey-fresh-auth.test.ts src/lib/api/__tests__/passkeys.test.ts src/features/partner-settings/lib/workspace-settings-contract.test.ts` | PASS: `4 passed`, `11 passed` |
| Browser smoke | `env NODE_ENV=development NEXT_TELEMETRY_DISABLED=1 npm run check:login-passkey-smoke -w frontend` against `http://127.0.0.1:9001/en-EN/login` | PASS: `status: passed`, `autocomplete: username webauthn`, policy/options/login sequence observed |
| Admin conformance | `npm run conformance:partner-admin:admin` | PASS: generated API types in sync, lint pass, Next build pass |
| Partner conformance | `npm run conformance:partner-admin:partner` | PASS: generated API types in sync, lint pass, Next build pass |
| Diff hygiene | `git diff --check` | PASS |

## Required Matrix

| Requirement | Expected | Actual | Status |
|---|---|---|---|
| Challenge replay and expired challenge | Challenge consume is one-time, expired challenges rejected, fallback fails closed if no atomic path | Covered by `test_challenge_consume_*` and integration challenge expiry/consume test | PASS |
| Fresh-auth replay, wrong action, wrong endpoint scope, wrong realm, wrong principal | Grant is one-time and scoped to action/endpoint/realm/principal | Covered by `test_passkey_fresh_auth.py` and reauthentication credential scope mismatch integration test | PASS |
| Origin/RP mismatch at options/verify | Wrong origin/RP rejected | Covered by `test_passkey_wrong_origin_rejected` and WebAuthn service tests in integration pack | PASS |
| Realm/audience mismatch, partner/admin endpoint confusion | Partner policy requires partner realm and exact action; admin grant does not satisfy partner endpoint | Covered by partner workspace policy integration tests and partner API targeted tests | PASS |
| Revoked credential rejected | Revoked passkey must not authenticate | Covered by `test_revoked_passkey_authentication_is_rejected` | PASS |
| Disabled passkey feature blocks options/verify/list/rename/delete | Global disable blocks management even with existing grants | Covered by `test_passkey_management_endpoints_honor_global_disable_with_existing_grants` | PASS |
| `sign_count` anomaly | Clone suspicion audited; no session/grant issued | Covered by reauthentication/authentication sign-count anomaly integration tests | PASS |
| Discoverable `userHandle` mismatch/null | Mismatch rejected; missing/null behavior follows security decision | Covered by `test_passkey_discoverable_authentication_rejects_user_handle_mismatch` and `allows_missing_user_handle` | PASS |
| Customer rename/delete fresh-auth | UI reauthenticates before PATCH/DELETE and sends `X-Fresh-Auth-Grant-Id` | Covered by settings cabinet tests and customer API tests | PASS |
| WebAuthn cancel on destructive customer flow | No destructive request; non-fatal feedback | Covered by settings cabinet cancel/unsupported tests | PASS |
| 403 fresh-auth required no optimistic mutation | Credential list not mutated as success | Covered by settings cabinet rename/delete 403 tests | PASS |
| Admin/partner approved wrapper/fallback | Runtime path uses `@simplewebauthn/browser`; unsupported browsers reported before ceremony | Covered by admin/partner `passkey-webauthn.test.ts` and package dependency checks | PASS |
| Partner exact action | Uses `partner.passkeys.policy.update:{workspace_id}` with partner fresh-auth | Covered by backend integration and partner workspace contract tests | PASS |
| Unsupported/insecure fallback visible | Browser/device unsupported state remains non-breaking and password login remains available | Covered by login-client and admin/partner wrapper tests | PASS |
| Browser smoke: Chrome desktop | Chromium smoke passed with API sequence and `autocomplete="username webauthn"` | Existing server on `0.0.0.0:9001` used; Chrome/Chromium path available | PASS |
| Browser smoke: WebKit/Safari, Edge, iOS, Android | Run if available | WebKit/Firefox Playwright executables missing; Edge binary missing; no iOS/Android device in host | NOT RUN, non-blocking per issue wording |

## Screenshot Evidence

- `qa-artifacts/CYBA-440/login-passkey-explicit-desktop-chromium.png`
- `qa-artifacts/CYBA-440/login-passkey-explicit-mobile-chromium.png`
- `qa-artifacts/CYBA-440/login-passkey-desktop-chromium.png`
- `qa-artifacts/CYBA-440/login-passkey-mobile-chromium.png`
- `qa-artifacts/CYBA-440/screenshot-summary.json`

Visual check: passkey CTA visible on desktop and mobile; no clipping/overflow in the passkey login card. Dev server shows a dev-only fixed console button in the lower-left. Desktop screenshot also exposes raw `back_to_home` copy in the login nav; this is a non-passkey P3/i18n observation and not a CYBA-440 security blocker.

## Go/No-Go

- CYBA-435 backend hardening: GO for QA scope.
- CYBA-436 customer frontend passkey parity: GO for QA scope.
- CYBA-437 admin/partner passkey parity: GO for QA scope.
- Overall CYBA-440 result: PASS for available local/test environment.

## Residual Risk

- Real Safari/WebKit, real Edge, iOS Safari, and Android Chrome were not available in this host. Recommend Scribe/release evidence keep these as staging/device-lab smoke items before production rollout.
- No production deploy, staging enablement, real authenticator-device registration, or real account data test was performed in this QA heartbeat.
- Context7 docs checked: N/A for QA-only validation; no code changes were made by QA.
