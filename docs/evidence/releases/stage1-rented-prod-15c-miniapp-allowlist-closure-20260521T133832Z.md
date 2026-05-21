# Stage 1 Rented Prod 15C: Mini App Allowlist Closure

Date: 2026-05-21T13:38:32Z

Scope: close the invited-user Mini App auth blocker after the owner reported `Вход через Telegram...` with a red warning indicator.

## Finding

Production backend logs showed repeated Mini App auth blocks:

```text
POST /api/v1/auth/telegram/miniapp 403
```

Runtime probe before the fix:

```text
registration_enabled: False
miniapp_allowed_sasha_beep_kz: False
bot_allowed_sasha_beep_kz: True
```

The user was already allowed for Telegram Bot registration, but not for Telegram Mini App bootstrap. This kept the flow controlled but blocked the invited-user Mini App login.

## Change

Production runtime config updated:

```text
TELEGRAM_MINIAPP_BOOTSTRAP_USERNAMES includes @Sasha_Beep_KZ
```

Only `cybervpn-backend` was restarted. No frontend, bot, worker, data, Remnawave or VPN node changes were made.

## Verification

Production backend service:

```text
cybervpn-backend: healthy
```

Public probes:

```text
200 https://cyber-vpn.net/health
200 https://cyber-vpn.net/api/v1/status
```

Runtime allowlist probe after the fix:

```text
registration_enabled: False
miniapp_allowed_sasha_beep_kz: True
miniapp_allowed_unknown: False
bot_allowed_sasha_beep_kz: True
```

Fresh backend error scan:

```text
error/exception/traceback/critical scan: no matches
```

Home observability:

```json
{
  "status": "success",
  "firing_count": 0,
  "firing_names": []
}
```

## Owner Retest

Ask `@Sasha_Beep_KZ` to fully close and reopen the Telegram Mini App from the bot, then wait for the Telegram auth step again.

Expected:

- no red warning indicator on `Вход через Telegram...`;
- Mini App proceeds to the normal logged-in state;
- global public registration remains disabled for unknown usernames.

## Next Step

Continue with first invited-user redemption/provisioning evidence after the owner confirms Mini App login works for `@Sasha_Beep_KZ`.
