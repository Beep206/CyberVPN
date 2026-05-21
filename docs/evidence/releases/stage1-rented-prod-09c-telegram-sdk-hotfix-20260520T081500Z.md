# Stage 1 Rented Production Evidence - RENT-09C Telegram SDK Hotfix

Date: 2026-05-20
Step: `STAGE1-RENT-09A` continuation
Scope: Telegram Mini App SDK initialization
Environment: rented `prod-app-1`

## Result

GO for another owner/internal Mini App auth smoke.

The Mini App was reachable and route navigation no longer fell back to the normal web login page, but the backend still did not receive `POST /api/v1/auth/telegram/miniapp`. The profile therefore showed fallback unauthenticated UI (`Guest User`, `No email set`).

## Root Cause

The frontend used `window.Telegram.WebApp` but did not load Telegram's official Mini App SDK script in the application HTML.

Without the SDK script, `window.Telegram.WebApp.initData` may not be available, so the frontend cannot submit signed Telegram init data to the backend.

## Code Change

Changed:

- `frontend/src/app/[locale]/layout.tsx`

Added Telegram Mini App SDK:

```text
https://telegram.org/js/telegram-web-app.js
```

It is loaded through Next.js `Script` with `beforeInteractive`, because Telegram's Mini App initialization contract requires the WebApp bridge before application hydration.

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
cybervpn/cybervpn-frontend:stage1-rent09c-telegram-sdk-20260520T081500Z
```

Runtime status after frontend recreate:

```text
cybervpn-frontend: healthy
cybervpn-backend: healthy
cybervpn-telegram-bot: healthy
```

Public probes after deployment:

```text
miniapp-profile=200 https://cyber-vpn.net/ru-RU/miniapp/profile
miniapp-home=200 https://cyber-vpn.net/ru-RU/miniapp/home
miniapp-plans=200 https://cyber-vpn.net/ru-RU/miniapp/plans
api-health=200 https://api.cyber-vpn.net/health
telegram-sdk-script=https://telegram.org/js/telegram-web-app.js
```

DB counts before owner retest:

```text
mobile_total|0
mobile_telegram_linked|0
admin_total|0
```

Remote redacted evidence directory:

```text
/srv/cybervpn/evidence/rent09c-telegram-sdk-20260520T081500Z
```

Captured files:

```text
docker-compose-ps.txt
public-probes.status
frontend-logs-redacted.txt
db-counts-redacted.txt
```

## Remaining Owner Smoke

Owner should now fully close and reopen the Telegram Mini App from `@C_y_b_e_r_VPN_Bot`.

Expected next backend evidence:

- `POST /api/v1/auth/telegram/miniapp` appears in backend logs;
- either the controlled owner user is linked/created, or the flow fails safely because public registration is still disabled.

If the SDK fix works but registration remains blocked, the next operational action is to manually bootstrap/link the owner Telegram identity or implement strict invite-gated Telegram Mini App user creation.
