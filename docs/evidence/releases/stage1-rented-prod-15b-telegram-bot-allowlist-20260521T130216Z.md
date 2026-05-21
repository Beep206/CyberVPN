# Stage 1 Rented Prod 15B: Telegram Bot Registration Allowlist

Date: 2026-05-21T13:02:16Z

Scope: allow one controlled beta Telegram username to register through the Telegram Bot while keeping global public registration disabled.

## Runtime Boundary

- Production app host: `prod-app-1`
- VPN node: unchanged; node-only policy preserved.
- Public registration: remains disabled.
- HTTP/3/QUIC policy: unchanged; no edge change was made.

## Change

Added backend setting:

```text
TELEGRAM_BOT_BOOTSTRAP_USERNAMES
```

Added Telegram Bot registration behavior:

- If a new Telegram Bot user is already known, the existing refresh path is unchanged.
- If a new Telegram Bot user is not known:
  - username in `TELEGRAM_BOT_BOOTSTRAP_USERNAMES` may bootstrap while public registration is paused;
  - every other username remains blocked by the S1 public registration kill switch.

Configured production allowlist:

```text
@Sasha_Beep_KZ
```

## Immutable Runtime Snapshot

Backend image deployed:

```text
cybervpn/cybervpn-backend:stage1-rent15b-bot-allowlist-20260521t125934z
```

Compose snapshot tag set:

```text
stage1-rent15b-bot-allowlist-20260521t125934z
```

Only `cybervpn-backend` was recreated for this step. Frontend, Telegram Bot, admin, worker, data services, Remnawave and VPN node were not changed.

## Test Evidence

Local targeted tests:

```text
backend/tests/security/test_stage1_registration_kill_switch.py: 12 passed
backend/tests/unit/api/v1/test_telegram_plans.py: 3 passed
targeted ruff: passed
```

Production service state:

```text
cybervpn-backend: healthy
cybervpn-frontend: healthy
cybervpn-telegram-bot: healthy
```

Production runtime allowlist probe:

```text
registration_enabled: False
allowed_sasha_beep_kz: True
allowed_unknown: False
```

Public endpoint probes:

```text
200 https://cyber-vpn.net/health
200 https://cyber-vpn.net/api/v1/status
```

Fresh backend log scan:

```text
error/exception/traceback/critical scan: no matches
```

Security review:

```text
git diff --check: passed
targeted secret scan: no matches
targeted dangerous-pattern scan: no new dangerous pattern; existing helper call name match only
backend pip-audit: residual pyjwt PYSEC-2025-183, no fixed version reported by pip-audit
```

Home observability:

```json
{
  "status": "success",
  "firing_count": 0,
  "firing_names": []
}
```

## Owner Test Instructions

Ask `@Sasha_Beep_KZ` to open the production Telegram Bot and send:

```text
/start
```

Expected result:

- the bot registration path no longer returns the invite-only/public-registration block;
- the user can proceed to Mini App/bot flow and redeem one controlled beta invite;
- unknown usernames remain blocked while public registration is paused.

## Next Step

Use the first real `@Sasha_Beep_KZ` attempt as `STAGE1-RENT-15C: First invited user redemption and provisioning evidence`.
