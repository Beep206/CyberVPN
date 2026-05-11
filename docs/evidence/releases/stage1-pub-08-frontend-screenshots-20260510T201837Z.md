# STAGE1-PUB-08 Frontend And Public Web Deploy Evidence

Date: 2026-05-10T20:18:37Z
Stage: `STAGE1-PUB-08`
Release: `stage1-beta-rc.1`

## Result

Status: passed with note.

The public frontend is deployed and reachable through Cloudflare/Caddy:

- `cyber-vpn.net` serves the customer-facing Next.js frontend.
- `cyber-vpn.org` redirects to `cyber-vpn.net`.
- `www.cyber-vpn.net` redirects to `cyber-vpn.net`.
- `status.cyber-vpn.net` redirects to `/en-EN/status`.
- `admin.cyber-vpn.net` and `admin.cyber-vpn.org` remain routed for admin access.

Note: the server outbound IP is `168.100.10.132`, but the inbound public origin for Caddy is `95.82.233.131`. Cloudflare app records were corrected to `95.82.233.131`.

## Deployment Changes

- Built `local/cybervpn-frontend:stage1-beta-rc.1`.
- Deployed `cybervpn-frontend` on `127.0.0.1:13000->3000`.
- Routed `cyber-vpn.net` from system Caddy to `127.0.0.1:13000`.
- Added explicit forwarded headers for frontend/admin reverse proxy routes.
- Added redirect-only routes for `www.cyber-vpn.net` and `status.cyber-vpn.net`.
- Replaced legacy `vpn.ozoxy.ru` frontend Next.js origins with `cyber-vpn.net` and `www.cyber-vpn.net`.
- Changed frontend API rewrite to use `API_INTERNAL_ORIGIN`/`API_URL`.
- Tightened `.dockerignore` so RC builds do not include local build caches.

## Image Evidence

```text
local/cybervpn-frontend@sha256:a7af87babc14a8e0d41b48125dfa103a6a2233a70bb9799af36345cd61ca44df
image_id=sha256:a7af87babc14a8e0d41b48125dfa103a6a2233a70bb9799af36345cd61ca44df
size_bytes=836583072
```

Next.js build completed successfully with Cache Components enabled and generated 2801 static/PPR pages.

## Runtime Evidence

```text
cybervpn-stage1-cybervpn-frontend-1   local/cybervpn-frontend:stage1-beta-rc.1   Up healthy   127.0.0.1:13000->3000/tcp
cybervpn-stage1-cybervpn-backend-1    local/cybervpn-backend:stage1-beta-rc.1    Up healthy   127.0.0.1:18080->8000/tcp, 127.0.0.1:19091->9091/tcp
cybervpn-stage1-cybervpn-admin-1      local/cybervpn-admin:stage1-beta-rc.1      Up healthy   127.0.0.1:13001->3000/tcp
```

System Caddy reload result:

```text
active
```

## Public Smoke

```text
https://cyber-vpn.net/                         -> 307 https://cyber-vpn.net/en-EN
https://cyber-vpn.net/health                   -> 200
https://cyber-vpn.net/api/v1/status            -> 200
https://cyber-vpn.net/en-EN/pricing            -> 200
https://cyber-vpn.net/ru-RU/privacy-policy     -> 200
https://cyber-vpn.net/en-EN/terms              -> 200
https://cyber-vpn.net/en-EN/acceptable-use     -> 200
https://cyber-vpn.net/en-EN/refund-policy      -> 200
https://cyber-vpn.net/en-EN/cookie-policy      -> 200
https://cyber-vpn.net/en-EN/devices            -> 200
https://cyber-vpn.net/en-EN/help               -> 200
https://cyber-vpn.net/en-EN/status             -> 200
https://cyber-vpn.net/en-EN/dashboard          -> 200
https://cyber-vpn.net/en-EN/subscriptions      -> 200
https://cyber-vpn.org/                         -> 301 https://cyber-vpn.net/
https://status.cyber-vpn.net/                  -> 301 https://cyber-vpn.net/en-EN/status
https://admin.cyber-vpn.org/                   -> 301 https://admin.cyber-vpn.net/
```

Swagger/OpenAPI public exposure remains blocked:

```text
https://cyber-vpn.net/docs        -> 404
https://cyber-vpn.net/openapi.json -> 404
```

## DNS Evidence

Cloudflare records were set to the working inbound origin:

```text
A      cyber-vpn.net         -> 95.82.233.131 proxied=true
A      admin.cyber-vpn.net   -> 95.82.233.131 proxied=true
CNAME  www.cyber-vpn.net     -> cyber-vpn.net proxied=true
A      status.cyber-vpn.net  -> 95.82.233.131 proxied=true
A      cyber-vpn.org         -> 95.82.233.131 proxied=true
A      admin.cyber-vpn.org   -> 95.82.233.131 proxied=true
```

DoH confirmed Cloudflare edge answers for the new records:

```text
www.cyber-vpn.net       -> 104.21.85.196,172.67.209.233
admin.cyber-vpn.net     -> 104.21.85.196,172.67.209.233
status.cyber-vpn.net    -> 104.21.85.196,172.67.209.233
admin.cyber-vpn.org     -> 188.114.96.0,188.114.97.0
```

## Screenshots

- `docs/evidence/releases/screenshots/stage1-pub-08-pricing-en.png`
- `docs/evidence/releases/screenshots/stage1-pub-08-privacy-ru.png`
- `docs/evidence/releases/screenshots/stage1-pub-08-status-en.png`

Captured with Playwright using the local Google Chrome channel.

## Bundle And Env Scan

Client bundle/public scan found no matches for the checked private markers:

```text
CRYPTOBOT|NOWPAYMENTS|PAYRAM|YOOKASSA|JWT_SECRET|POSTGRES_PASSWORD|DATABASE_URL|REDIS_URL|SENTRY_AUTH_TOKEN|CLOUDFLARE_API_TOKEN|10.10.10.34|vpn.ozoxy.ru
```

The broader server-rendered route cache contains normal product text and config-delivery labels, but the targeted private marker scan returned no matches.

## Dependency Audit

`npm audit --omit=dev --workspace frontend --audit-level=high` found no high/critical frontend production vulnerabilities.

Residual note:

- npm reports a moderate `postcss` advisory through the current Next.js dependency tree. The automated fix proposes a breaking downgrade path, so it was not applied during deploy.

## Blackbox Probe Evidence

Prometheus job added:

```text
blackbox-stage1-public-web
```

Active targets after scrape:

```text
https://www.cyber-vpn.net/                 up
https://cyber-vpn.org/                     up
https://status.cyber-vpn.net/              up
https://admin.cyber-vpn.net/ru-RU/login    up
https://admin.cyber-vpn.org/               up
https://cyber-vpn.net/health               up
https://cyber-vpn.net/en-EN/pricing        up
https://cyber-vpn.net/en-EN/status         up
```

Prometheus config check:

```text
SUCCESS: /etc/prometheus/prometheus.yml is valid prometheus config file syntax
```

## Notes

- Local resolver temporarily returned stale NXDOMAIN for some new `.net` subdomains after Cloudflare record creation. DoH and Prometheus blackbox probes confirmed the records were live.
- No user payment/VPN provisioning flows were exercised in this step; that remains owned by later Stage 1 deploy steps.
