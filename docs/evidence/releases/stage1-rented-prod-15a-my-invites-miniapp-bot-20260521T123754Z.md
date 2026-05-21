# Stage 1 Rented Prod 15A: My Invites In Mini App And Bot

Date: 2026-05-21T12:37:54Z

Scope: expose manually issued invite codes to the owner/internal beta user in the Telegram Mini App profile and Telegram bot before using those codes with external beta users.

## Runtime Boundary

- Production app host: `prod-app-1`
- Public domain checked: `cyber-vpn.net`
- VPN node: unchanged; no app, bot, admin, payment, or observability workloads were deployed to the VPN node.
- HTTP/3/QUIC policy: unchanged; no edge change was made in this step.

## Immutable Runtime Snapshot

Initial image tag deployed:

```text
stage1-rent15a-my-invites-20260521t121946z
```

Final image tag deployed after dependency-audit closure:

```text
stage1-rent15a-my-invites-depaudit-20260521t124255z
```

Services switched to this tag:

- `cybervpn-backend`
- `cybervpn-frontend`
- `cybervpn-telegram-bot`

Unchanged services re-tagged to keep a single compose snapshot:

- `cybervpn-admin`
- `cybervpn-task-worker`

## Implemented Behavior

- Added backend endpoint for Telegram bot invite lookup:
  - `GET /api/v1/telegram/bot/user/{telegram_id}/invite-codes`
  - Protected by `X-Telegram-Bot-Secret`
  - Returns invite codes owned by the linked CyberVPN user.
- Added Telegram bot `/invites` command and invite menu callback.
- Replaced the bot invite menu surface with “My invites” behavior for S1, without enabling public referral rewards.
- Added Mini App profile section:
  - Russian: `Мои инвайты`
  - English: `My invites`
  - Shows invite status, free days, creation date, expiry date, and copy action.
- Added locale strings for bot and Mini App.
- Kept referral/promo/gift public flows disabled for Stage 1.

## Test Evidence

Local component and regression checks:

```text
frontend profile tests: 6 passed
frontend targeted eslint: passed
backend telegram route tests: 3 passed
backend targeted ruff: passed
telegram bot targeted unit tests: 48 passed
telegram bot targeted ruff: passed
```

Dependency audit follow-up:

```text
backend/bot idna: upgraded from 3.11 to 3.15
backend/bot urllib3: upgraded from 2.6.3 to 2.7.0
telegram bot pip-audit: no known vulnerabilities found
backend pip-audit: residual pyjwt PYSEC-2025-183, no fixed version reported by pip-audit
frontend npm audit --audit-level=high: exit 0, 4 moderate advisories remain
```

Production service state after deploy:

```text
cybervpn-backend: healthy
cybervpn-frontend: healthy
cybervpn-telegram-bot: healthy
```

Public endpoint probes:

```text
200 https://cyber-vpn.net/health
200 https://cyber-vpn.net/ru-RU
200 https://cyber-vpn.net/ru-RU/miniapp/profile
200 https://cyber-vpn.net/api/v1/status
```

Backend invite endpoint probe for the owner Telegram account:

```json
{
  "status": 200,
  "count": 3,
  "items": [
    {
      "code": "C46C****",
      "free_days": 7,
      "is_used": false,
      "expires_at_set": true
    },
    {
      "code": "A21E****",
      "free_days": 7,
      "is_used": false,
      "expires_at_set": true
    },
    {
      "code": "409F****",
      "free_days": 7,
      "is_used": false,
      "expires_at_set": true
    }
  ]
}
```

Telegram Bot command surface:

```json
{
  "ok": true,
  "has_invites_command": true,
  "commands": [
    "start",
    "menu",
    "connect",
    "plans",
    "trial",
    "invites",
    "support",
    "paysupport"
  ]
}
```

Fresh production logs after deploy:

```text
backend error/exception/traceback/critical scan: no matches
frontend error/exception/traceback/critical scan: no matches
telegram-bot error/exception/traceback/critical scan: no matches
```

Home observability check:

```json
{
  "status": "success",
  "firing_count": 0,
  "firing_names": []
}
```

## User Validation Required

The owner should verify in Telegram:

1. Open the CyberVPN Mini App.
2. Go to `Profile`.
3. Confirm the `Мои инвайты` section shows the issued invite codes.
4. Open the bot invite menu or send `/invites`.
5. Confirm the same invite codes are visible in the bot.

No external invite redemption should start until the owner confirms this view.

## Residual Risk

- This step only exposes existing manually issued invite codes. It does not prove redemption by a second user.
- The next evidence step must prove invite redemption, trial/subscription assignment, VPN config delivery, and support visibility for the invited user.

## Next Step

`STAGE1-RENT-15B: First invited user redemption/provisioning evidence`
