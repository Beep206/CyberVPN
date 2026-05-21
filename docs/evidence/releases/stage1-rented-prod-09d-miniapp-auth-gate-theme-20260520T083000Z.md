# Stage 1 Rented Production Evidence - RENT-09D Mini App Auth Gate And Theme Hotfix

Date: 2026-05-20
Step: `STAGE1-RENT-09A` continuation
Scope: Telegram Mini App owner/internal smoke blocker
Environment: rented `prod-app-1`

## Result

GO for another owner/internal Telegram Mini App retest.

The previous retest still showed unauthenticated web fallback content inside the Mini App profile:

- `Guest User`
- `No email set`
- `No VPN config available`
- `Refresh token not provided`

Backend logs also still showed no `POST /api/v1/auth/telegram/miniapp`, which means the frontend was rendering the Mini App screens before Telegram init data was available to the app runtime.

## Code Change

Changed Mini App auth behavior:

- `frontend/src/features/auth/components/TelegramMiniAppAuthProvider.tsx`
- `frontend/src/features/auth/components/__tests__/TelegramMiniAppAuthProvider.test.tsx`

The provider now gates all `/miniapp/*` routes until Telegram Mini App auth is either detected or fails safely. It no longer renders the normal web children on Mini App routes while `window.Telegram.WebApp.initData` is missing. This prevents raw guest profile state and refresh-token errors from being shown inside Telegram.

Changed Mini App visual fallback behavior:

- `frontend/src/app/[locale]/miniapp/components/MiniAppBottomNav.tsx`
- `frontend/src/app/[locale]/miniapp/components/MiniAppBottomSheet.tsx`
- `frontend/src/app/[locale]/miniapp/components/VpnConfigCard.tsx`
- `frontend/src/app/[locale]/miniapp/home/page.tsx`
- `frontend/src/app/[locale]/miniapp/plans/page.tsx`
- `frontend/src/app/[locale]/miniapp/profile/page.tsx`
- `frontend/src/app/[locale]/miniapp/wallet/page.tsx`
- `frontend/src/app/[locale]/miniapp/payments/page.tsx`
- `frontend/src/app/[locale]/miniapp/referral/page.tsx`
- `frontend/src/app/[locale]/miniapp/components/__tests__/MiniAppBottomNav.test.tsx`

Mini App cards, sheets and bottom navigation now use stable CyberVPN dark surfaces instead of light Telegram theme background fallbacks. Telegram accent/link colors are still used where intended, but light theme no longer turns the app panels gray.

## Verification

Local targeted tests:

```text
npm --workspace frontend run test -- TelegramMiniAppAuthProvider.test.tsx MiniAppBottomNav.test.tsx session.test.ts auth.test.ts VpnConfigCard.test.tsx MiniAppBottomSheet.test.tsx
```

Result:

```text
Test Files  6 passed | 1 skipped (7)
Tests       132 passed | 7 skipped (139)
```

Local production build:

```text
NEXT_TELEMETRY_DISABLED=1 npm --workspace frontend run build
```

Result:

```text
Compiled successfully
TypeScript completed
Generated static pages: 2801/2801
```

Production image:

```text
cybervpn/cybervpn-frontend:stage1-rent09d-miniapp-auth-gate-20260520T083000Z
```

Runtime status after frontend recreate:

```text
cybervpn-frontend: healthy
```

Public probes after deployment:

```text
200 https://cyber-vpn.net/ru-RU/miniapp/profile
200 https://cyber-vpn.net/ru-RU/miniapp/home
200 https://cyber-vpn.net/ru-RU/miniapp/plans
200 https://api.cyber-vpn.net/health
telegram-sdk-script=present
```

DB counts before owner retest:

```text
mobile_total|0
mobile_telegram_linked|0
admin_total|0
```

Remote redacted evidence directory:

```text
/srv/cybervpn/evidence/rent09d-miniapp-auth-gate-theme-20260520T083000Z
```

Captured files:

```text
docker-compose-ps.txt
public-probes.status
frontend-logs-redacted.txt
backend-miniapp-logs-redacted.txt
db-counts-redacted.txt
```

## Remaining Owner Smoke

Owner should fully close and reopen the Telegram Mini App from `@C_y_b_e_r_VPN_Bot`, then open `Profile`.

Expected result after this hotfix:

- the profile must not show normal web guest state;
- the profile must not show raw `Refresh token not provided`;
- light Telegram theme must not make Mini App panels gray;
- backend evidence should show `POST /api/v1/auth/telegram/miniapp` if Telegram init data reaches the frontend runtime.

If `POST /api/v1/auth/telegram/miniapp` still does not appear, the next blocker is likely BotFather/Mini App launch mode or Telegram client context rather than the frontend route guard.
