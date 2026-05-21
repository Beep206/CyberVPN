# Stage 1 Rented Production Evidence - RENT-09A Owner Telegram Mini App Auth Hotfix

Date: 2026-05-20
Step: `STAGE1-RENT-09A`
Scope: owner Telegram Mini App onboarding/linking smoke
Environment: rented `prod-app-1`

## Result

PARTIAL GO for the Telegram Mini App frontend runtime fix.

Owner/internal user onboarding is not fully closed yet because the production database still has no Telegram-linked user after the first owner open. The next proof must be a fresh owner `/start` plus Mini App reopen after this hotfix.

## Trigger

Owner opened the Telegram Mini App and observed two states:

1. first open redirected to the normal frontend login page;
2. second open showed the Mini App bottom navigation: `Home`, `Plans`, `Wallet`, `Profile`.

That meant the Mini App shell was reachable, but it did not prove Telegram Mini App authentication or user linking.

## Diagnosis

Server-side evidence before the fix showed:

- Telegram webhook was configured and healthy;
- Mini App public page returned `200`;
- unauthenticated webhook requests without Telegram secret were rejected with `401`;
- backend received unauthenticated Mini App API calls with `401`;
- production DB had no mobile Telegram-linked users;
- bot logs showed startup/webhook readiness, not a processed owner `/start` update.

The frontend root cause was a stale Mini App detection path:

- `TelegramMiniAppAuthProvider` depended on `isMiniApp` from the auth store;
- the auth store can be initialized before Telegram injects `window.Telegram.WebApp`;
- when that happens, `isMiniApp=false` remains stale and Mini App auto-auth never starts.

## Code Change

Changed:

- `frontend/src/features/auth/components/TelegramMiniAppAuthProvider.tsx`
- `frontend/src/features/auth/components/__tests__/TelegramMiniAppAuthProvider.test.tsx`

Behavior after the fix:

- the provider still respects the store `isMiniApp` flag;
- additionally, after mount it checks for `window.Telegram.WebApp.initData` for a short bounded period;
- if Telegram init data appears after store creation, Mini App auto-auth starts;
- standard browser login flow is unchanged outside Telegram Mini App.

Security note:

- no Telegram init data, JWT, access token, refresh token, bot token, VLESS/subscription URL or private key is stored in this evidence;
- all runtime evidence paths are redacted.

## Verification

Local targeted test:

```text
npm --workspace frontend run test -- TelegramMiniAppAuthProvider.test.tsx
```

Result:

```text
Test Files  1 passed (1)
Tests       4 passed (4)
```

Production image build:

```text
cybervpn/cybervpn-frontend:stage1-rent09a-miniapp-auth-20260520T074800Z
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
api-health=200 https://api.cyber-vpn.net/health
webhook-no-secret=401 https://api.cyber-vpn.net/webhook/telegram
```

DB counts after deployment, before a fresh owner reopen:

```text
mobile_total|0
mobile_telegram_linked|0
admin_total|0
```

Remote redacted evidence directory:

```text
/srv/cybervpn/evidence/rent09a-miniapp-auth-hotfix-20260520T074800Z
```

Files captured there:

```text
docker-compose-ps.txt
public-probes.status
frontend-logs-redacted.txt
backend-logs-redacted.txt
telegram-bot-logs-redacted.txt
db-counts-redacted.txt
```

## Current Decision

GO for another owner/internal Telegram Mini App smoke after the frontend hotfix.

NO-GO for external Telegram beta cohort until owner smoke proves:

- `/start` update is processed;
- Mini App auth request is sent from the frontend;
- backend either links/creates the expected controlled owner user or fails safely because public registration is still disabled;
- no raw sensitive payloads appear in evidence.

## Next Owner Action

1. Send `/start` to `@C_y_b_e_r_VPN_Bot`.
2. Fully close the Telegram Mini App.
3. Reopen it from the Telegram bot menu.
4. Report the exact screen/state shown.

If the next backend result is a safe `REGISTRATION_DISABLED` response, the next engineering decision is whether to manually bootstrap/link the owner Telegram identity or implement strict invite-gated Telegram user creation before inviting external beta users.
