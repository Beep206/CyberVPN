# Stage 1 Rented Production Evidence - RENT-09B Mini App Route Guard Hotfix

Date: 2026-05-20
Step: `STAGE1-RENT-09A` continuation
Scope: Telegram Mini App navigation/auth guard
Environment: rented `prod-app-1`

## Result

GO for another owner/internal Mini App navigation smoke.

The observed issue was reproduced from code path analysis: Mini App API `401` responses could trigger the shared browser auth interceptor and redirect the Telegram Mini App to the normal web login page. That redirect path has been blocked for Mini App routes and Mini App API requests.

## Owner Observation

Owner reported:

```text
Mini App opens with bottom navigation: Home, Plans, Wallet, Profile.
After pressing Plans and then Home, the normal frontend login page opens.
```

## Root Cause

The Mini App Home page loads `/api/v1/miniapp/bootstrap`.

When the current owner/internal Telegram user is not yet linked, that request can return `401`. The shared Axios response interceptor then:

1. tried `/auth/refresh`;
2. received `401`;
3. redirected to localized `/login`.

That behavior is correct for ordinary web dashboard routes, but wrong for Telegram Mini App routes. Mini App must stay inside `/miniapp/*` and let the Telegram-specific auth/linking flow or a safe in-app error state handle the unauthenticated case.

## Code Change

Changed:

- `frontend/src/features/auth/lib/session.ts`
- `frontend/src/lib/api/client.ts`
- `frontend/src/features/auth/lib/session.test.ts`
- `frontend/src/lib/api/__tests__/auth.test.ts`

Behavior after the fix:

- `isMiniAppRoute()` recognizes localized and internal Mini App routes;
- normal web auth session bootstrap is skipped inside `/miniapp/*`;
- shared `401` interceptor no longer redirects to `/login` for Mini App routes;
- shared `401` interceptor no longer redirects to `/login` for `/miniapp/*` API requests;
- ordinary dashboard/web protected routes still keep their login redirect behavior.

## Verification

Local targeted tests:

```text
npm --workspace frontend run test -- TelegramMiniAppAuthProvider.test.tsx session.test.ts auth.test.ts MiniAppBottomNav.test.tsx
```

Result:

```text
Test Files  4 passed | 1 skipped (5)
Tests       127 passed | 7 skipped (134)
```

Production image build:

```text
cybervpn/cybervpn-frontend:stage1-rent09b-miniapp-route-20260520T080000Z
```

Runtime status after frontend recreate:

```text
cybervpn-frontend: healthy
cybervpn-backend: healthy
cybervpn-telegram-bot: healthy
cybervpn-remnawave: healthy
```

Public probes after deployment:

```text
miniapp=200 https://cyber-vpn.net/ru-RU/miniapp
miniapp-home=200 https://cyber-vpn.net/ru-RU/miniapp/home
miniapp-plans=200 https://cyber-vpn.net/ru-RU/miniapp/plans
api-health=200 https://api.cyber-vpn.net/health
webhook-no-secret=401 https://api.cyber-vpn.net/webhook/telegram
```

DB counts after deployment:

```text
mobile_total|0
mobile_telegram_linked|0
admin_total|0
```

Remote redacted evidence directory:

```text
/srv/cybervpn/evidence/rent09b-miniapp-route-guard-20260520T080000Z
```

Captured files:

```text
docker-compose-ps.txt
public-probes.status
frontend-logs-redacted.txt
backend-logs-redacted.txt
telegram-bot-logs-redacted.txt
db-counts-redacted.txt
```

## Remaining Owner Smoke

Owner should now:

1. fully close Telegram Mini App;
2. send `/start` to `@C_y_b_e_r_VPN_Bot`;
3. reopen Mini App from the bot menu;
4. press `Plans`;
5. press `Home`;
6. report whether the app stays inside Mini App instead of opening the normal login page.

If it stays in Mini App but shows an auth/access error, that is the expected next state while production registration remains paused and no Telegram-linked user exists.
