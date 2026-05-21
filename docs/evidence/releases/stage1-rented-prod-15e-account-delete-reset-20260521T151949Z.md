# Stage 1 Rented Production 15E - Account Delete Reset

Date: 2026-05-21 15:19:49 UTC

Release tag: `stage1-rent15e-account-delete-20260521t150443z`

## Scope

- Reset the internal beta Telegram test account `Sasha_Beep_KZ` so it can register again and redeem invite access.
- Fix the Telegram Mini App Profile `Delete Account` action.
- Keep HTTP/3/QUIC enabled.

## Production Account Reset

Result:

- Target mobile account removed from CyberVPN production database.
- Existing Remnawave VPN user was removed before local account cleanup.
- Previously used invite assignment was released for retest.
- Related beta growth redemption was marked reversed for audit trail.

Post-reset verification:

- `mobile_users` rows matching the target Telegram username/id: `0`.
- No raw invite codes, subscription URLs, Remnawave UUIDs or secrets are recorded in this evidence.

## Code Changes

Backend:

- Added `MobileDeleteAccountUseCase`.
- Added authenticated `DELETE /api/v1/mobile/auth/me`.
- The mobile delete flow now revokes Remnawave access when present, anonymizes/releases unique Telegram identifiers, clears VPN config pointers, disables the account and revokes JWT sessions.
- Cookie cleanup is performed for the current customer auth realm.

Frontend:

- Mini App Profile deletion now uses the auth store `deleteAccount` action.
- Mini App deletion calls the mobile endpoint instead of the web account endpoint.
- Telegram `showConfirm` is handled using the real callback-style Telegram WebApp API.
- Query cache is cleared after logout/delete.
- The delete button has a pending state and localized `deletingAccount` text.

## Production Deploy Evidence

Images built/tagged:

- `cybervpn/cybervpn-backend:stage1-rent15e-account-delete-20260521t150443z`
- `cybervpn/cybervpn-frontend:stage1-rent15e-account-delete-20260521t150443z`
- Existing admin, worker/scheduler and Telegram bot images were retagged to the same release tag for compose compatibility.

Runtime status after deploy:

- `cybervpn-backend`: healthy
- `cybervpn-frontend`: healthy
- Public Mini App profile route: HTTP 200
- Public unauthenticated `DELETE /api/v1/mobile/auth/me`: HTTP 401, confirming the route exists and requires authentication.
- Public response still includes `alt-svc: h3=":443"; ma=86400`.

Log check:

- No backend/frontend errors, exceptions or tracebacks were found in the post-deploy log window.

## Verification

Local checks:

- `npm --prefix frontend run lint -- 'src/app/[locale]/miniapp/profile/page.tsx' 'src/app/[locale]/miniapp/profile/__tests__/page.test.tsx'`
- `npm --prefix frontend test -- --run 'src/app/[locale]/miniapp/profile/__tests__/page.test.tsx'`
- `cd backend && uv run pytest tests/unit/application/use_cases/mobile_auth/test_delete_account.py tests/unit/presentation/api/v1/invites/test_invites_routes.py --no-cov`
- `cd backend && uv run ruff check src/application/use_cases/mobile_auth/delete_account.py src/presentation/api/v1/mobile_auth/routes.py tests/unit/application/use_cases/mobile_auth/test_delete_account.py`
- `git diff --check`

Production build checks:

- Backend Docker image build: passed.
- Frontend Docker image build: passed after fixing a production TypeScript check around optional `showConfirm`.
- Next.js production build generated all locale Mini App routes.

Security sanity:

- Static scan found no `dangerouslySetInnerHTML`, `eval`, `new Function`, shell execution or subprocess patterns in the changed runtime files.
- Secret-pattern scan found only benign request password variable references in existing auth route code; no literal secrets were found in changed files.
- `npm --prefix frontend audit --audit-level=high --omit=dev` passed the high-severity gate. Existing moderate advisories remain in transitive frontend dependencies.

## Residual Risk

- The owner should retest the Mini App delete flow from a real Telegram WebView because Telegram confirmation dialogs are platform-provided.
- If a future delete request fails while Remnawave is unavailable, the backend returns `VPN_REVOKE_FAILED` instead of leaving VPN access active silently.

## Next Owner Action

Close and reopen the Telegram Mini App for `Sasha_Beep_KZ`, register again, redeem invite access and verify that VPN config delivery appears without manual backend cleanup.
