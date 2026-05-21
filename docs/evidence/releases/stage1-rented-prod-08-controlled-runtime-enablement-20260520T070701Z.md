# Stage 1 Rented Production Evidence - RENT-08 Controlled Runtime Enablement

Date: 2026-05-20
Stage: S1 - Controlled Public Beta
Step: `STAGE1-RENT-08`
Environment: rented production runtime

## Decision

`STAGE1-RENT-08` was executed in trial-only controlled mode.

The production runtime is now ready for controlled internal/owner trial smoke with the rented app server and rented VPN node. Public account creation remains paused because the current backend code does not enforce invite-only mode across every B2C registration entrypoint.

## Safety Boundary

Enabled:

- `STAGE1_TRIAL_PROVISIONING_ENABLED=true`

Kept disabled:

- `REGISTRATION_ENABLED=false`
- `STAGE1_PAID_PROVISIONING_ENABLED=false`
- `STAGE1_ADDONS_ENABLED=false`
- `REFERRAL_ENABLED=false`
- `PROMO_CODES_ENABLED=false`
- `GIFT_CODES_ENABLED=false`
- `CHECKOUT_CODE_DISCOUNTS_ENABLED=false`
- `TELEGRAM_STARS_ENABLED=false`
- `PAYMENT_AUTORENEWAL_ENABLED=false`
- `HELIX_ENABLED=false`
- `HELIX_ADMIN_ENABLED=false`

Reason: S1 must stay controlled. Trial provisioning can be exercised by known/manual identities, but global registration cannot be opened until invite-only control is proven on mobile, Telegram, Mini App, magic-link and OAuth-created-user flows.

## Pre-Enable Backup

Server-only backup directory:

```text
/srv/cybervpn/backups/rent08-controlled-runtime-20260520T070421Z
```

Files created on `prod-app-1`:

| File | Size | SHA-256 |
|---|---:|---|
| `cybervpn-postgres.sql.gz` | 43K | `28e4cc6e0aab059bea7d9834dfa03322894215fc9b566d676e4eaeebfd76752c` |
| `remnawave-postgres.sql.gz` | 63K | `b90da9a14aaa11dd68ee7cc065fd34c556647713cb35134c0a9274819fbaa173` |
| `app.env.pre-rent08.secret` | 3.3K | server-only secret copy, not stored in repo |

## Runtime Evidence

Server-only evidence directory:

```text
/srv/cybervpn/evidence/rent08-controlled-runtime-20260520T070701Z
```

Public probes:

| Probe | Result |
|---|---|
| `https://cyber-vpn.net/` | `307`, then `200 https://cyber-vpn.net/en-EN` |
| `https://api.cyber-vpn.net/health` | `200` |
| `https://admin.cyber-vpn.net/` | `307`, then `200 https://admin.cyber-vpn.net/ru-RU/login` |
| `https://api.cyber-vpn.net/.well-known/cybervpn-edge-health` | `200` |
| `https://api.cyber-vpn.net/webhook/telegram` | `200 disabled`, reason `live_bot_webhook_not_enabled` |

Registration guard:

```text
POST /api/v1/mobile/auth/register -> 403
code: REGISTRATION_DISABLED
channel: mobile_password
```

Docker health after flag change:

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

Backend settings proof from the running backend container:

```text
registration_enabled=False
registration_invite_required=True
stage1_trial_provisioning_enabled=True
stage1_paid_provisioning_enabled=False
stage1_addons_enabled=False
referral_enabled=False
promo_codes_enabled=False
gift_codes_enabled=False
checkout_code_discounts_enabled=False
telegram_stars_enabled=False
payment_autorenewal_enabled=False
helix_enabled=False
helix_admin_enabled=False
```

## Pause / Rollback Controls

Created on `prod-app-1`:

```text
/srv/cybervpn/runbooks/pause-provisioning.md
/srv/cybervpn/runbooks/pause-registration.md
/srv/cybervpn/runbooks/pause-payments.md
```

Primary emergency pause command for trial provisioning:

```bash
cd /srv/cybervpn/compose/app
sudo sed -i "s|^STAGE1_TRIAL_PROVISIONING_ENABLED=.*|STAGE1_TRIAL_PROVISIONING_ENABLED=false|" /srv/cybervpn/secrets/app.env
sudo docker compose up -d --no-deps --force-recreate cybervpn-backend cybervpn-worker cybervpn-scheduler cybervpn-telegram-bot
sudo docker compose ps
```

## Current Go/No-Go Result

Result:

```text
GO for controlled internal/owner trial smoke.
NO-GO for opening public B2C registration.
NO-GO for paid beta users.
```

Why:

- rented app runtime is healthy;
- rented Remnawave/VPN proof exists from `STAGE1-RENT-07`;
- trial provisioning flag is enabled in the running backend;
- public registration is intentionally paused;
- paid/growth/autorenew/private-transport surfaces remain disabled;
- Telegram webhook is still intentionally disabled at the edge and should be handled in `STAGE1-RENT-09`;
- invite-only enforcement is not yet proven for every public B2C registration surface.

## Next Recommended Step

```text
STAGE1-RENT-09: Telegram Bot/Mini App live beta smoke with the first real owner/internal user.
```

Before opening external users, close the invite-only gap or keep registration closed and onboard beta users through a manual/admin-controlled identity process.
