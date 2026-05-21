# Stage 1 Rented Prod 09F - Telegram Mini App Owner Bootstrap

Date: 2026-05-20

## Purpose

Close the remaining owner/internal Telegram Mini App auth blocker without opening public registration.

The previous blocker changed from `401` HMAC validation failure to `403` registration disabled. That means Telegram `initData` now reaches backend with the correct bot-token validation path, but the first Telegram-linked account cannot be created while `REGISTRATION_ENABLED=false`.

## Change

- Added backend setting `TELEGRAM_MINIAPP_BOOTSTRAP_USERNAMES`.
- Added Telegram Mini App username allowlist handling inside `TelegramMiniAppUseCase`.
- Kept public registration disabled by default.
- Kept blocked behavior unchanged for users not in the allowlist.
- Passed the setting from the `/api/v1/auth/telegram/miniapp` route.
- Added security regression coverage for:
  - Mini App new account creation blocked while registration is paused.
  - Allowlisted owner username can bootstrap while registration is paused.

## Runtime Deployment

- Built backend image:
  - `cybervpn/cybervpn-backend:stage1-rent09f-telegram-bootstrap-20260520t090407z`
- Recreated only backend:
  - `cybervpn-stage1-cybervpn-backend-1`
- Other runtime services were not recreated.
- Runtime bootstrap allowlist is temporarily enabled for the owner username only.

## Verification

### Component

Command:

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

### Runtime

Checks:

```text
backend container image: cybervpn/cybervpn-backend:stage1-rent09f-telegram-bootstrap-20260520t090407z
backend status: healthy
backend /health: {"status":"ok"}
bootstrap allowlist: loaded
```

## Pending Owner Action

Owner must fully close and reopen the Telegram Mini App from `@C_y_b_e_r_VPN_Bot`.

Expected result:

- `POST /api/v1/auth/telegram/miniapp` returns success.
- Owner Telegram-linked account is created once.
- Mini App no longer shows the red auth warning.
- `Profile` no longer shows `Guest User`, `No email set`, or raw `Refresh token not provided`.

If the request still returns `403`, the most likely cause is Telegram username mismatch or missing username in Telegram `initData`. In that case, do not open public registration; use a stricter manual Telegram ID linking/bootstrap path.

## Cleanup Required After Success

After owner auth succeeds:

1. Remove `TELEGRAM_MINIAPP_BOOTSTRAP_USERNAMES` from runtime secrets.
2. Recreate only backend with the same backend image tag.
3. Confirm existing linked Telegram owner account still logs in.
4. Capture redacted auth success evidence.

## Rollback

Rollback backend only:

```bash
cd /srv/cybervpn/compose/app
CYBERVPN_IMAGE_TAG=stage1-rent04-90f5b4b5 docker compose --env-file .env up -d --no-deps cybervpn-backend
```

Remove the temporary runtime allowlist from secrets if rollback is used.
