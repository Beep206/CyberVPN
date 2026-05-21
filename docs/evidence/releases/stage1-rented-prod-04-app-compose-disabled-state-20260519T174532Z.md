# STAGE1-RENT-04: App Compose And Disabled-State Deploy

Date: `2026-05-19`

UTC evidence time: `2026-05-19T17:45:32Z`

Target: `prod-app-1`

Host: `45.87.41.146`

Result: `PASS_WITH_NOTES`

## Purpose

Deploy the Stage 1 customer-facing app/control-plane runtime on `prod-app-1` in a safe disabled state before VPN node, live payments, public registration, Telegram live webhook, and production provisioning are enabled.

This step intentionally publishes the web/admin/API shell, not the full paid/trial VPN flow.

## Source Snapshot

| Field | Value |
|---|---|
| Git commit | `90f5b4b5` |
| Runtime image tag | `stage1-rent04-90f5b4b5` |
| Server source path | `/srv/cybervpn/releases/src-90f5b4b5-rent04` |
| Compose path | `/srv/cybervpn/compose/app/docker-compose.yml` |
| Runtime env path | `/srv/cybervpn/compose/app/.env` |
| Secret path | `/srv/cybervpn/secrets/*.env` |
| Runtime evidence path on server | `/srv/cybervpn/evidence/rent04-runtime-stage1-rent04-90f5b4b5` |
| Build evidence path on server | `/srv/cybervpn/evidence/rent04-build-stage1-rent04-90f5b4b5` |

## Images Built On `prod-app-1`

| Image | Image ID | Notes |
|---|---|---|
| `cybervpn/cybervpn-backend:stage1-rent04-90f5b4b5` | `sha256:480edbc6d7be...` | backend API |
| `cybervpn/cybervpn-task-worker:stage1-rent04-90f5b4b5` | `sha256:c26f2769f4bc...` | worker and scheduler |
| `cybervpn/cybervpn-telegram-bot:stage1-rent04-90f5b4b5` | `sha256:905e4d796c3e...` | bot runtime, network calls disabled |
| `cybervpn/cybervpn-frontend:stage1-rent04-90f5b4b5` | `sha256:cd15c2f2c46a...` | public frontend |
| `cybervpn/cybervpn-admin:stage1-rent04-90f5b4b5` | `sha256:02473dd2847f...` | admin frontend |

Build logs are stored only on `prod-app-1` under:

```text
/srv/cybervpn/evidence/rent04-build-stage1-rent04-90f5b4b5/
```

## Runtime Layout

Created or updated:

```text
/srv/cybervpn/compose/app
/srv/cybervpn/secrets
/srv/cybervpn/configs/app
/srv/cybervpn/logs
```

Security evidence:

```text
/srv/cybervpn/compose/app/.env       root:root 0600
/srv/cybervpn/secrets/*.env          root:root 0600
/srv/cybervpn/configs/app/*.yml      root:root
```

Secrets are not copied into this repository.

## Services Started

Started with the Stage 1 compose file and `local-data` profile:

| Service | Status |
|---|---|
| `cybervpn-postgres` | `healthy` |
| `cybervpn-valkey` | `healthy` |
| `cybervpn-postgres-exporter` | `healthy` |
| `cybervpn-redis-exporter` | `healthy` |
| `cybervpn-backend` | `healthy` |
| `cybervpn-worker` | `healthy` |
| `cybervpn-scheduler` | `healthy` |
| `cybervpn-frontend` | `healthy` |
| `cybervpn-admin` | `healthy` |
| `cybervpn-telegram-bot` | `healthy` |

Local ports remain loopback-only:

```text
127.0.0.1:13000 -> frontend
127.0.0.1:13001 -> admin
127.0.0.1:18080 -> backend
127.0.0.1:18088 -> telegram bot
127.0.0.1:19091 -> backend metrics
```

Public ports remain:

```text
22/tcp
80/tcp
443/tcp
```

## Database Migration Note

The first public registration probe returned `500` because the app database was empty and `auth_realms` had not been created yet.

Fix applied in this step:

```text
alembic upgrade head
```

The migration was run inside `cybervpn-backend` with `DATABASE_URL` injected from the runtime environment.

Final Alembic revision:

```text
20260423_p27_partner_events (head) (mergepoint)
```

Migration output is stored on `prod-app-1`:

```text
/srv/cybervpn/evidence/rent04-runtime-stage1-rent04-90f5b4b5/backend-alembic-upgrade-head.log
```

## Disabled-State Gates

Verified from backend settings:

```text
environment=production
registration_enabled=False
registration_invite_required=True
payments_enabled=False
telegram_stars_enabled=False
payment_reconciliation_enabled=False
payment_autorenewal_enabled=False
stage1_trial_provisioning_enabled=False
stage1_paid_provisioning_enabled=False
referral_enabled=False
promo_codes_enabled=False
gift_codes_enabled=False
checkout_code_discounts_enabled=False
helix_enabled=False
admin_2fa_required=True
swagger_enabled=False
csrf_protection_enabled=True
cookie_secure=True
enable_metrics=True
```

Telegram Bot runtime is up, but:

```text
TELEGRAM_BOT_SKIP_NETWORK_CALLS=true
live production bot token not used in STAGE1-RENT-04
public /webhook/telegram returns disabled response from edge
```

## Edge Routing

The existing Caddy edge container was connected to the app backend network:

```text
cybervpn-edge
cybervpn_stage1_backend
```

Routing after this step:

| Host | Behavior |
|---|---|
| `https://cyber-vpn.net` | public frontend |
| `https://cyber-vpn.net/api/v1/*` | backend API |
| `https://cyber-vpn.net/health` | backend health |
| `https://api.cyber-vpn.net/healthz` | edge health |
| `https://api.cyber-vpn.net/health` | backend health |
| `https://api.cyber-vpn.net/webhook/telegram` | disabled response |
| `https://admin.cyber-vpn.net` | admin frontend |
| `https://cyber-vpn.org/*` | redirect to `https://cyber-vpn.net/*` |
| `https://admin.cyber-vpn.org/*` | redirect to `https://admin.cyber-vpn.net/*` |

Caddy validation passed. A non-blocking formatting warning remains from Caddy because the mounted file is not auto-formatted inside the read-only container mount.

## Public Checks

| Check | Result |
|---|---|
| `https://cyber-vpn.net/` | `307` to `https://cyber-vpn.net/en-EN` |
| `https://cyber-vpn.net/ru-RU` | `200` |
| `https://cyber-vpn.net/en-EN/status` | `200` |
| `https://cyber-vpn.net/health` | `200`, `{"status":"ok"}` |
| `https://cyber-vpn.net/api/v1/auth/me` | `401`, unauthenticated as expected |
| `https://api.cyber-vpn.net/healthz` | `200`, edge ok |
| `https://api.cyber-vpn.net/health` | `200`, backend ok |
| `https://api.cyber-vpn.net/webhook/telegram` | `200`, disabled |
| `https://admin.cyber-vpn.net/` | `307` to `/ru-RU` |
| `https://admin.cyber-vpn.net/ru-RU/login` | `200` |
| `https://status.cyber-vpn.net/` | `302` to `https://cyber-vpn.net/en-EN/status` |
| `https://cyber-vpn.org/ru-RU` | `301` to primary |
| `https://admin.cyber-vpn.org/ru-RU/login` | `301` to primary admin |

## Recheck Fix: Forwarded Port

Detailed recheck on `2026-05-19T17:56Z` found one public routing issue:

```text
https://cyber-vpn.net/
307 -> https://cyber-vpn.net:3000/en-EN
```

Cause:

```text
Next.js / next-intl locale redirect used the upstream container port because the edge proxy did not pass X-Forwarded-Port=443.
```

Fix applied on `prod-app-1`:

```text
Add header_up X-Forwarded-Port 443 to backend/frontend/admin reverse_proxy blocks.
Recreate only cybervpn-edge-caddy.
Reconnect cybervpn-edge-caddy to cybervpn_stage1_backend.
Validate Caddy configuration.
```

Post-fix check:

```text
https://cyber-vpn.net/
307 -> https://cyber-vpn.net/en-EN
```

No app/control-plane containers were recreated for this fix.

Disabled registration check after migrations:

```text
POST https://cyber-vpn.net/api/v1/auth/register
HTTP 403
{"detail":{"code":"REGISTRATION_DISABLED","message":"Public registration is currently paused.","channel":"web_password"}}
```

## Evidence Commands

Representative checks executed:

```bash
sudo docker compose --env-file .env --profile local-data config --quiet
sudo docker compose --env-file .env --profile local-data up -d ...
sudo docker compose --env-file .env --profile local-data ps
curl https://cyber-vpn.net/ru-RU
curl https://cyber-vpn.net/health
curl https://api.cyber-vpn.net/webhook/telegram
curl https://admin.cyber-vpn.net/ru-RU/login
curl -I https://cyber-vpn.org/ru-RU
sudo ufw status verbose
```

## Residual Blockers

This step does not make CyberVPN ready for beta users yet.

Remaining blockers:

| Blocker | Status |
|---|---|
| Production VPN node | not deployed in this step |
| Remnawave production control-plane proof | not enabled in this step |
| Trial provisioning proof | not done |
| First admin bootstrap | not done |
| Telegram live webhook | disabled |
| Live payment provider credentials | not configured |
| Backup/off-host restore evidence | still required before users |
| Rollback evidence on rented runtime | still required before users |
| Observability feed to home Grafana/Sentry/Loki | still required |

## Decision

`STAGE1-RENT-04` is accepted as a disabled-state app/control-plane deploy.

Next recommended step:

```text
STAGE1-RENT-05: Production VPN node proof
```
