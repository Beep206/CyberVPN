# Stage 1 Rented Production Evidence - RENT-09E Backend Telegram Token Reload

Date: 2026-05-20
Step: `STAGE1-RENT-09A` continuation
Scope: Telegram Mini App backend HMAC validation
Environment: rented `prod-app-1`

## Result

GO for another owner/internal Telegram Mini App retest.

After the `09D` frontend hotfix, the Mini App no longer rendered the normal guest profile. The owner retest reached the backend, but the Mini App still showed the Telegram sign-in error state.

Backend logs showed:

```text
POST /api/v1/auth/telegram/miniapp 401
initData HMAC validation failed
```

## Root Cause

The backend container still had an older `TELEGRAM_BOT_TOKEN` loaded in its process environment.

The runtime secret file already had the correct token fingerprint matching the Telegram bot runtime, but the backend container had not been recreated after the production bot token was corrected.

No raw bot token, Telegram initData, hash, JWT, cookie or VPN config value was captured in this evidence.

## Action

Recreated only `cybervpn-backend` with the existing backend image and current runtime env:

```text
CYBERVPN_IMAGE_TAG=stage1-rent04-90f5b4b5 docker compose --env-file .env up -d --no-deps cybervpn-backend
```

This avoided touching frontend, Telegram bot, Remnawave or data services.

## Verification

Backend container token fingerprint after recreate matched the redacted runtime secret fingerprint:

```text
TELEGRAM_BOT_TOKEN present=true len=46 sha256_12=47941adbf8f1
TELEGRAM_BOT_USERNAME=C_y_b_e_r_VPN_Bot
```

Runtime status:

```text
cybervpn-backend: healthy
cybervpn-frontend: healthy
cybervpn-telegram-bot: healthy
```

Public probes:

```text
200 https://api.cyber-vpn.net/health
200 https://cyber-vpn.net/ru-RU/miniapp/profile
```

## Remaining Owner Smoke

Owner should fully close and reopen the Telegram Mini App from `@C_y_b_e_r_VPN_Bot`, then open `Profile`.

Expected next behavior:

- HMAC validation should no longer fail.
- If the owner already has a linked account, Mini App auth should complete.
- If the owner does not have a linked account, the next expected blocker is controlled registration/linking because public registration remains paused for S1.

If the next backend result is `403 REGISTRATION_DISABLED`, create/link the owner Telegram account through an audited owner bootstrap/support path, or temporarily approve a tightly controlled Telegram canary onboarding path.
