# Stage 1 Rented Production 14C - Mini App Session Restore Hotfix

Date: 2026-05-21 06:52:47 UTC

Status: `DEPLOYED_FRONTEND_HOTFIX`

## Context

After the owner confirmed a successful real-device VPN connection through the Telegram Bot/Mini App flow, the Mini App later showed a misleading guest/no-subscription state:

- Home showed no active subscription.
- Trial activation was not available again.
- Profile/config surfaces showed no VPN config.

The trial button behavior was expected because Stage 1 trial is single-use. The misleading part was the missing active trial/config display.

## Root Cause

Production backend state was still valid for the owner Telegram-linked account:

- user status: `active`
- trial used: `true`
- trial active: `true`
- trial days left at check time: about `2.49`
- Remnawave UUID present: `true`
- subscription URL present: `true`

The frontend/Mini App session was stale or missing a valid cookie, while the client-side auth store could still render an authenticated-looking state. Protected Mini App API calls returned `401`, and the UI rendered the business fallback instead of restoring Telegram Mini App auth through `window.Telegram.WebApp.initData`.

## Fix

Implemented a Mini App re-authentication restore path:

1. `frontend/src/lib/api/client.ts`
   - dispatches `cybervpn:miniapp-auth-restore-required` when a Mini App protected API request gets `401` and refresh cannot recover the session.

2. `frontend/src/features/auth/components/TelegramMiniAppAuthProvider.tsx`
   - listens for the restore event;
   - re-runs Telegram Mini App auth when Telegram `initData` is available;
   - invalidates `miniapp-*` query keys after successful auth;
   - avoids synchronous state updates inside the initial effect.

3. `frontend/src/app/[locale]/miniapp/home/page.tsx`
   - shows a session-restore state instead of the misleading no-subscription state when bootstrap fails because auth is being restored.

4. `frontend/src/app/[locale]/miniapp/components/VpnConfigCard.tsx`
   - shows the same session-restore state for `401` config fetches.

5. `frontend/src/app/[locale]/(auth)/layout.tsx`
   - wraps `TelegramMiniAppAuthProvider` with `QueryProvider`.
   - This follows the TanStack Query contract: components using `useQueryClient` must be under a `QueryClientProvider`.
   - Reference: <https://tanstack.com/query/latest/docs/react/reference/QueryClientProvider>

6. `frontend/messages/en-EN/MiniApp.json` and `frontend/messages/ru-RU/MiniApp.json`
   - added localized session-restore copy.

## Deployment

New frontend image:

```text
cybervpn/cybervpn-frontend:stage1-rent14c-miniapp-session-restore-20260521t063728z
```

Deployment action:

```text
Only cybervpn-frontend was recreated.
Backend, Telegram Bot, worker, scheduler, Remnawave and VPN node were not changed.
HTTP/3/QUIC was not disabled.
```

Runtime state after deploy:

```text
cybervpn-frontend: running healthy
public /ru-RU/miniapp/home: HTTP 200
frontend logs: Next.js ready, no startup error
```

## Verification

Component and regression tests:

```text
npm run test:run -- \
  src/features/auth/components/__tests__/TelegramMiniAppAuthProvider.test.tsx \
  src/lib/api/__tests__/auth.test.ts \
  src/app/[locale]/miniapp/components/__tests__/VpnConfigCard.test.tsx \
  src/app/[locale]/miniapp/home/__tests__/page.test.tsx

Result: 4 files passed, 104 tests passed.
```

Lint:

```text
npx eslint \
  src/app/[locale]/(auth)/layout.tsx \
  src/lib/api/client.ts \
  src/features/auth/components/TelegramMiniAppAuthProvider.tsx \
  src/features/auth/components/__tests__/TelegramMiniAppAuthProvider.test.tsx \
  src/lib/api/__tests__/auth.test.ts \
  src/app/[locale]/miniapp/home/page.tsx \
  src/app/[locale]/miniapp/components/VpnConfigCard.tsx

Result: passed.
```

Production build:

```text
next build --turbopack
Result: compiled successfully, TypeScript passed, 2801 static pages generated.
```

Production backend state check:

```text
owner Telegram-linked user:
  status=active
  trial_used=true
  trial_active=true
  Remnawave UUID present=true
  subscription URL present=true
```

Security/sanity review:

```text
git diff --check: passed
secret scan on changed hotfix/docs files: no matches
dangerous frontend pattern scan on changed hotfix files: no matches
npm audit --audit-level=high: passed with no high/critical findings
known residual npm audit findings: 4 moderate advisories already outside this hotfix scope
```

## User Action Required

The owner should close and reopen the Telegram Mini App from the bot and verify:

1. Home no longer shows a misleading no-subscription state after session restore.
2. Trial is shown as already used/active rather than available again.
3. VPN config is visible again after Telegram auth restore completes.

## Decision

```text
GO to retest owner Mini App session restore on a real Telegram device.
NO-GO to expand cohort-2 until owner confirms the real-device retest after this hotfix.
```
