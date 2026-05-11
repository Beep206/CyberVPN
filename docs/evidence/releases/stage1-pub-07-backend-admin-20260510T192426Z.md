# STAGE1-PUB-07 Backend/API/Admin Deploy Evidence

Date: 2026-05-10T19:24:26Z
Stage: STAGE1-PUB-07
Release candidate: `stage1-beta-rc.1`
Server: `cybervpn-h-ops` (`10.10.10.34`)

## Scope

Deployed the Stage 1 backend/API and admin runtime on the home server with the system Caddy service as the public edge. App containers bind only to loopback host ports; system Caddy owns `80/443`.

## Repository Changes

- `admin/next.config.ts`
  - Replaced legacy `admin.ozoxy.ru` server action origin with `admin.cyber-vpn.net`.
  - Changed admin `/api/v1/*` rewrite destination from hardcoded `http://localhost:8000` to `API_INTERNAL_ORIGIN` / `API_URL`, defaulting to local development.
- `backend/pyproject.toml`
  - Added `email-validator>=2.2.0` because Pydantic `EmailStr` requires the optional email validator package.
- `backend/uv.lock`
  - Locked `email-validator==2.3.0` and `dnspython==2.8.0`.
- `infra/deploy/stage1/Dockerfile.next-workspace`
  - Added a Stage 1 Next.js workspace image for admin/frontend-style builds.
- `infra/deploy/stage1/docker-compose.stage1.yml`
  - Moved compose Caddy behind the `container-edge` profile for this host because system Caddy already owns `80/443`.
  - Bound backend to `127.0.0.1:18080->8000` and metrics to `127.0.0.1:19091->9091`.
  - Bound admin to `127.0.0.1:13001->3000`.
- `infra/deploy/stage1/Caddyfile.system-stage1.snippet`
  - Added system Caddy routes for `cyber-vpn.net`, `cyber-vpn.org`, `admin.cyber-vpn.net`, and `admin.cyber-vpn.org`.

## Runtime Images

Local and server image IDs:

```text
local/cybervpn-backend:stage1-beta-rc.1 a42197ab5163 380MB
local/cybervpn-admin:stage1-beta-rc.1 cfd1c27e4d3a 2.14GB
```

## Runtime Secrets And Env

Updated root-only server env files under `/srv/cybervpn-h/secrets`:

- `app.env`
- `payments.env`
- `remnawave.env`
- `sentry-runtime.env`
- `admin.env`
- `first-admin-bootstrap.env`

Modes:

- secrets directory: `0700 root:root`
- env files: `0600 root:root`

Notes:

- No secret values are recorded in this evidence.
- `SENTRY_DSN` is intentionally empty for this stage until live Sentry runtime evidence is enabled.
- Payment credentials are production-shape placeholders only; live payment remains blocked until payment provider evidence is completed.
- First admin credentials and TOTP secret are stored only in `/srv/cybervpn-h/secrets/first-admin-bootstrap.env`.

## Containers

Final server state:

```text
cybervpn-stage1-cybervpn-admin-1      local/cybervpn-admin:stage1-beta-rc.1     Up healthy   127.0.0.1:13001->3000/tcp
cybervpn-stage1-cybervpn-backend-1    local/cybervpn-backend:stage1-beta-rc.1   Up healthy   127.0.0.1:18080->8000/tcp, 127.0.0.1:19091->9091/tcp
cybervpn-stage1-cybervpn-postgres-1   postgres:17.7-alpine                      Up healthy   5432/tcp
cybervpn-stage1-cybervpn-valkey-1     valkey/valkey:8.1-alpine                  Up healthy   6379/tcp
```

## Backend/API Smoke

Loopback backend smoke:

```text
GET http://127.0.0.1:18080/health        -> 200 {"status":"ok"}
GET http://127.0.0.1:18080/docs          -> 404
GET http://127.0.0.1:18080/openapi.json  -> 404
GET http://127.0.0.1:18080/redoc         -> 404
```

Runtime settings proof, redacted:

```text
environment=production
swagger_enabled=False
cors_origins=['https://cyber-vpn.net', 'https://admin.cyber-vpn.net']
cookie_domain=cyber-vpn.net
cookie_secure=True
csrf_protection_enabled=True
rate_limit_enabled=True
rate_limit_fail_open=False
mobile_rate_limit_fail_open=False
rate_limit_auth_sensitive_requests=20
rate_limit_payment_write_requests=30
rate_limit_support_write_requests=30
admin_host_protection_enabled=True
admin_allowed_hosts=['admin.cyber-vpn.net']
admin_2fa_required=True
registration_enabled=False
registration_invite_required=True
```

## First Admin Bootstrap

Bootstrap command path:

```text
python scripts/bootstrap_first_admin.py
```

First run:

```json
{"audit_action":"admin.bootstrap.first_admin_created","auth_realm":"admin","email":"owner@cyber-vpn.net","login":"sasha_beep","role":"owner/super_admin","status":"created","totp_enabled":true}
```

Repeat guard:

```json
{"message":"first admin bootstrap is locked because admin or bootstrap audit state already exists","reason":"bootstrap_locked","status":"failed"}
```

Database proof:

```text
admin_count=1
totp_enabled_count=1
bootstrap_audit_count=1
```

## System Caddy Edge

System Caddy remains the public edge authority for this host.

Backup before modification:

```text
/etc/caddy/Caddyfile.stage1-pub-07.20260510T191724Z.bak
```

Caddy route block:

```text
/etc/caddy/Caddyfile lines 160-211
```

Certificate directories after issuance:

```text
/var/lib/caddy/.local/share/caddy/certificates/acme-v02.api.letsencrypt.org-directory/admin.cyber-vpn.net
/var/lib/caddy/.local/share/caddy/certificates/acme-v02.api.letsencrypt.org-directory/admin.cyber-vpn.org
/var/lib/caddy/.local/share/caddy/certificates/acme-v02.api.letsencrypt.org-directory/cyber-vpn.net
/var/lib/caddy/.local/share/caddy/certificates/acme-v02.api.letsencrypt.org-directory/cyber-vpn.org
```

Note: Caddy logged temporary Cloudflare cleanup timeouts while deleting DNS-01 TXT records, but certificates were issued successfully and locks were cleared.

Final edge smoke with local resolve:

```text
https://cyber-vpn.net/health              -> 200
https://cyber-vpn.net/docs                -> 404
https://cyber-vpn.net/openapi.json        -> 404
https://admin.cyber-vpn.net/ru-RU/login   -> 200
https://admin.cyber-vpn.org/ru-RU/login   -> 301 Location: https://admin.cyber-vpn.net/ru-RU/login
https://cyber-vpn.org/health              -> 301 Location: https://cyber-vpn.net/health
```

CORS preflight through Caddy/backend:

```text
HTTP/2 200
access-control-allow-credentials: true
access-control-allow-origin: https://admin.cyber-vpn.net
vary: Origin
```

## Verification

Local checks:

```text
docker compose -f infra/deploy/stage1/docker-compose.stage1.yml --profile local-data config --quiet
git diff --check
cd backend && uv run python EmailStr smoke
```

All passed after the `email-validator` dependency fix.

## Residual Items

- Public frontend is intentionally not deployed in this step; `STAGE1-PUB-08` owns frontend/public web.
- Sentry DSN is disabled until observability runtime evidence is configured.
- Live payment credentials are not active in this step.
- Compose Caddy is kept as optional `container-edge`; this server uses system Caddy because host ports `80/443` are already occupied by the existing edge.

## References

- Pydantic `EmailStr` optional dependency requirement: https://docs.pydantic.dev/2.11/api/networks/
- Next.js rewrites support external destinations: https://nextjs.org/docs/app/api-reference/config/next-config-js/rewrites
- Next.js Node.js deployment model: https://nextjs.org/docs/app/getting-started/deploying
