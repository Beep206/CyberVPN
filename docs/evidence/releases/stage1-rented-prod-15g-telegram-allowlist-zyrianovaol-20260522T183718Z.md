# Stage 1 Rented Prod 15G: Telegram Beta Allowlist Add ZyrianovaOl

Date: 2026-05-22T18:37:18Z

Scope: add one controlled beta Telegram username to the Telegram Bot and Mini App bootstrap allowlists while keeping global public registration disabled.

## Runtime Boundary

- Production app host: `prod-app-1`
- VPN node: unchanged; node-only policy preserved.
- Public registration: remains disabled.
- HTTP/3/QUIC policy: unchanged; no edge change was made.
- GitLab/GitHub: not used for this change by owner request.

## Change

Production backend env was updated:

```text
TELEGRAM_BOT_BOOTSTRAP_USERNAMES includes @ZyrianovaOl
TELEGRAM_MINIAPP_BOOTSTRAP_USERNAMES includes @ZyrianovaOl
```

Existing allowed username retained:

```text
@Sasha_Beep_KZ
```

Only `cybervpn-backend` was recreated so the backend settings reload. Frontend, Telegram Bot, admin, worker, data services, Remnawave and VPN node were not changed.

## Backup

Before editing `app.env`, a root-only backup was written on `prod-app-1` under:

```text
/srv/cybervpn/backups/app-env-before-zyrianovaol-*.env
```

## Verification

Production env check:

```text
TELEGRAM_BOT_BOOTSTRAP_USERNAMES=@Sasha_Beep_KZ,@ZyrianovaOl
TELEGRAM_MINIAPP_BOOTSTRAP_USERNAMES=@Sasha_Beep_KZ,@ZyrianovaOl
```

Backend health:

```text
cybervpn-stage1-cybervpn-backend-1: healthy
https://api.cyber-vpn.net/health -> {"status":"ok"}
```

Runtime allowlist probe:

```text
registration_enabled=False
bot_allowed_zyrianovaol=True
miniapp_allowed_zyrianovaol=True
bot_allowed_unknown=False
miniapp_allowed_unknown=False
```

Fresh backend log scan:

```text
error/exception/traceback/critical scan: no matches
```

## Owner Test Instructions

Ask `@ZyrianovaOl` to open the production Telegram Bot and send:

```text
/start
```

Expected:

1. Telegram Bot registration is allowed for this username while public registration remains paused.
2. Telegram Mini App login is allowed for this username.
3. Unknown usernames remain blocked.
4. Owner can provide one invite code for controlled beta testing.
