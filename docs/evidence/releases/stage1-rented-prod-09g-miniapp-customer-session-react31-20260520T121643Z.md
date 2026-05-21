# Stage 1 Rented Prod 09G - Mini App Customer Session And React 31 Fix

Date: 2026-05-20

## Purpose

Close the Telegram Mini App runtime blocker reported during owner smoke:

- the Mini App still showed the red Telegram auth warning after earlier hotfixes;
- production React crashed with minified React error `#31`, caused by rendering an API error object with keys `{code, message}` as a React child;
- backend Telegram Mini App auth returned an admin/legacy session, while `/api/v1/miniapp/*` endpoints require a customer/mobile session.

## Root Cause

Two issues were present at the same time:

1. Frontend components assumed `response.data.detail` was always a string. Some backend auth dependencies return structured errors like `{"code": "...", "message": "..."}`. Rendering that object directly triggers React error `#31`.
2. `/api/v1/auth/telegram/miniapp` authenticated the Telegram user against the admin user store and set admin cookies/tokens. Mini App runtime endpoints use `get_current_mobile_user_id`, so the subsequent Mini App bootstrap/config requests could still return `401`.

## Change

Frontend:

- Added `frontend/src/lib/api/error-message.ts`.
- Normalized structured API errors to safe strings before rendering.
- Updated Mini App VPN config card error handling.
- Updated Telegram Mini App auth store error handling.
- Added regression tests for structured API error details.

Backend:

- Telegram Mini App auth now ensures a matching `MobileUserModel` exists for the Telegram identity.
- Telegram Mini App auth now issues customer-scoped access/refresh tokens:
  - audience: `cybervpn:customer`;
  - realm key: `customer`;
  - principal type: `customer`;
  - scope family: `customer`;
  - cookie namespace: `customer`.
- Response user is shaped for the existing frontend contract while representing the customer/mobile principal.
- Temporary owner bootstrap allowlist from 09F was removed from production runtime secrets after owner account creation.

## Runtime Deployment

Built production images:

```text
cybervpn/cybervpn-backend:stage1-rent09g-miniapp-customer-session-20260520t121643z
cybervpn/cybervpn-frontend:stage1-rent09g-miniapp-customer-session-20260520t121643z
```

Tagged unchanged runtime images to keep the compose tag set complete:

```text
cybervpn/cybervpn-admin:stage1-rent09g-miniapp-customer-session-20260520t121643z
cybervpn/cybervpn-telegram-bot:stage1-rent09g-miniapp-customer-session-20260520t121643z
cybervpn/cybervpn-task-worker:stage1-rent09g-miniapp-customer-session-20260520t121643z
```

Recreated only:

```text
cybervpn-stage1-cybervpn-backend-1
cybervpn-stage1-cybervpn-frontend-1
```

## Verification

### Local Component Tests

Backend:

```bash
REMNAWAVE_TOKEN=... JWT_SECRET=... CRYPTOBOT_TOKEN=... \
backend/.venv/bin/python -m pytest --no-cov \
  backend/tests/security/test_stage1_registration_kill_switch.py \
  backend/tests/integration/api/v1/auth/test_telegram_miniapp_flow.py
```

Result:

```text
16 passed
```

Frontend:

```bash
npm --workspace frontend test -- TelegramMiniAppAuthProvider error-message
```

Result:

```text
2 files passed
8 tests passed
```

Lint and build:

```text
frontend targeted lint: passed
backend py_compile: passed
frontend production build: passed
```

### Runtime Health

Production containers after deploy:

```text
cybervpn-stage1-cybervpn-frontend-1 cybervpn/cybervpn-frontend:stage1-rent09g-miniapp-customer-session-20260520t121643z healthy
cybervpn-stage1-cybervpn-backend-1 cybervpn/cybervpn-backend:stage1-rent09g-miniapp-customer-session-20260520t121643z healthy
```

Public route:

```text
https://cyber-vpn.net/ru-RU/miniapp/home -> 200 text/html
```

Internal Mini App auth smoke with redacted synthetic Telegram initData:

```text
telegram_auth_status=200
telegram_auth_user_present=True
telegram_auth_access_token_present=True
/api/v1/miniapp/bootstrap_status=200
/api/v1/miniapp/config_status=404
```

Interpretation:

- `200` for Telegram auth proves the Mini App auth route accepts valid signed Telegram initData.
- `200` for `/api/v1/miniapp/bootstrap` proves the issued token is accepted by customer/mobile Mini App endpoints.
- `404` for `/api/v1/miniapp/config` is expected for a user without an active subscription/trial config; it is not an auth failure and must render as a safe no-config state.

## Current Status

GO for owner/internal Telegram Mini App retest.

NO-GO remains for external Telegram beta cohort until owner confirms in the real Telegram client:

- no red auth warning after a full close/reopen;
- no React crash;
- profile no longer shows the normal web guest state;
- Home/Plans/Profile navigation stays inside `/miniapp/*`;
- trial/config state is understandable.

## Known Follow-Up

Customer/mobile refresh-token persistence is still not fully equivalent to admin refresh persistence because the existing `refresh_tokens.user_id` relationship is admin-user oriented. The current Mini App access token and customer cookies work for immediate Mini App endpoints; a dedicated customer refresh/session persistence path should be added before a wider beta cohort.

## Rollback

Rollback backend/frontend to the previous known tag:

```bash
cd /srv/cybervpn/compose/app
sed -i 's/^CYBERVPN_IMAGE_TAG=.*/CYBERVPN_IMAGE_TAG=stage1-rent09d-miniapp-auth-gate-20260520T083000Z/' .env
docker compose --env-file .env up -d --no-deps cybervpn-backend cybervpn-frontend
```

If rolling back only the backend, use the 09F backend image and explicitly restore the required image tag strategy in compose.
