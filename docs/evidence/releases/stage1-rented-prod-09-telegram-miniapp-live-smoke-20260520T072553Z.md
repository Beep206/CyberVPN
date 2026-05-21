# Stage 1 Rented Production Evidence - RENT-09 Telegram Bot And Mini App Live Smoke

Date: 2026-05-20
Stage: S1 - Controlled Public Beta
Step: `STAGE1-RENT-09`
Environment: rented production runtime

## Decision

Telegram Bot and Mini App production runtime were moved from disabled edge state to live webhook surface.

This step is complete for infrastructure/API surface readiness, but the first real owner/internal user interaction is still pending because no `ADMIN_IDS` are configured and production DB currently has no Telegram-linked users.

## Pre-Change Snapshot

Server-only evidence directory:

```text
/srv/cybervpn/evidence/rent09-telegram-miniapp-20260520T072553Z
```

Server-only files captured before changes:

```text
Caddyfile.pre-rent09
telegram-bot.env.pre-rent09.secret
docker-compose-ps-before.txt
bot-flags-before-redacted.txt
```

Before change:

```text
BOT_MODE=webhook
TELEGRAM_BOT_SKIP_NETWORK_CALLS=true
TELEGRAM_BOT_MENU_BUTTON=commands
TELEGRAM_MINIAPP_URL=https://cyber-vpn.net/ru-RU/miniapp
WEBHOOK_URL=https://api.cyber-vpn.net
WEBHOOK_PATH=/webhook/telegram
CRYPTOBOT_ENABLED=false
TELEGRAM_STARS_ENABLED=false
TRIAL_ENABLED=false
REFERRAL_ENABLED=false
```

## Changes Applied

1. `api.cyber-vpn.net/webhook/telegram` now proxies to the Telegram bot container instead of returning the previous disabled placeholder response.
2. Bot runtime was switched to live Telegram API calls:

```text
TELEGRAM_BOT_SKIP_NETWORK_CALLS=false
```

3. Default Telegram menu was switched to Mini App:

```text
TELEGRAM_BOT_MENU_BUTTON=miniapp
TELEGRAM_MINIAPP_URL=https://cyber-vpn.net/ru-RU/miniapp
```

4. Telegram bot trial UI was enabled:

```text
TRIAL_ENABLED=true
```

5. Payments and growth remain disabled:

```text
CRYPTOBOT_ENABLED=false
TELEGRAM_STARS_ENABLED=false
REFERRAL_ENABLED=false
```

6. Production bot token on `prod-app-1` was updated to the owner-provided production token. The raw token is stored only in server secret files.

Token evidence:

```text
token_sha256_prefix=47941adbf8f1
```

## Runtime Proof

Docker after change:

```text
cybervpn-admin|running|healthy
cybervpn-backend|running|healthy
cybervpn-frontend|running|healthy
cybervpn-postgres-exporter|running|healthy
cybervpn-postgres|running|healthy
cybervpn-redis-exporter|running|healthy
cybervpn-remnawave-postgres|running|healthy
cybervpn-remnawave-valkey|running|healthy
cybervpn-remnawave|running|healthy
cybervpn-scheduler|running|healthy
cybervpn-telegram-bot|running|healthy
cybervpn-valkey|running|healthy
cybervpn-worker|running|healthy
```

Bot internal health:

```text
GET http://127.0.0.1:18088/health -> 200
```

Public webhook no-secret guard:

```text
POST https://api.cyber-vpn.net/webhook/telegram without Telegram secret header -> 401
```

Mini App page:

```text
GET https://cyber-vpn.net/ru-RU/miniapp -> 200
```

Telegram API proof:

```text
getMe.ok=true
getMe.username=C_y_b_e_r_VPN_Bot
getWebhookInfo.url=https://api.cyber-vpn.net/webhook/telegram
getWebhookInfo.pending_update_count=0
getWebhookInfo.last_error_date_present=false
getWebhookInfo.allowed_updates=message,callback_query,pre_checkout_query
getMyCommands.command_count=7
getMyCommands.commands=start,menu,connect,plans,trial,support,paysupport
getChatMenuButton.type=web_app
getChatMenuButton.web_app_url=https://cyber-vpn.net/ru-RU/miniapp
```

Startup log proof:

```text
bot_started username=C_y_b_e_r_VPN_Bot mode=webhook environment=production
stage1_telegram_surface_configured bot_menu_button=miniapp command_count=7
webhook_set url=https://api.cyber-vpn.net/webhook/telegram
```

Pause runbook:

```text
/srv/cybervpn/runbooks/pause-telegram-live-mode.md
```

## Current Safety State

Still disabled:

- public registration;
- paid provisioning;
- CryptoBot checkout;
- Telegram Stars;
- referral/growth rewards.

Reason: `STAGE1-RENT-08` confirmed that public registration is not invite-controlled across every B2C entrypoint. For S1, real beta user onboarding must remain manual/owner-controlled until that gap is closed.

## Remaining User-Action Gap

The first real owner/internal user smoke cannot be completed by automation alone.

Current production state:

```text
ADMIN_IDS: missing
admin_users with telegram_id: 0
mobile_users with telegram_id: 0
```

Required owner action:

```text
Open @C_y_b_e_r_VPN_Bot in Telegram and send /start.
```

Expected result after owner action:

```text
Telegram delivers the update to https://api.cyber-vpn.net/webhook/telegram.
Bot logs show update processing without Telegram API/auth errors.
Because public registration is paused, new-user onboarding must either be manually linked/created by admin or registration invite gating must be fixed before external users are invited.
```

## Result

```text
GO for Telegram Bot/Mini App infrastructure readiness.
GO for owner/internal manual Telegram smoke.
NO-GO for external beta cohort through Telegram until owner/internal user smoke is completed.
NO-GO for public Telegram registration until invite-only control covers all B2C entrypoints.
NO-GO for paid Telegram checkout.
```

## Next Recommended Step

```text
STAGE1-RENT-09A: Owner Telegram user onboarding/linking smoke.
```

After owner `/start`, capture redacted bot logs, decide whether to manually link the owner Telegram ID or implement a strict invite gate for Telegram/Mini App new-user creation, then continue to `STAGE1-RENT-10` only if the owner smoke is clean.
