# Stage 1 Rented Production DNS/TLS Temporary Health Evidence

Date: `2026-05-19T17:09:39Z`

Stage: `STAGE1-RENT-03`

Scope: `prod-app-1` public DNS cutover, temporary Caddy edge, TLS issuance, temporary health routes and mirror redirects.

## Result

```text
PASS_WITH_NOTE
```

Core Stage 1 public names now point to `prod-app-1`, terminate TLS on the rented app server, and return temporary health responses or expected redirects.

Non-blocking note:

```text
www.cyber-vpn.org was created in Cloudflare and Caddy obtained a certificate for it, but public resolver checks still showed inconsistent resolution at evidence time. The launch-critical mirror cyber-vpn.org and admin mirror admin.cyber-vpn.org are working.
```

## Host

| Field | Value |
|---|---|
| Role | `prod-app-1` |
| IPv4 | `45.87.41.146` |
| IPv6 on host | `2a0d:2787:1b:12f5::a/64` |
| Edge container | `cybervpn-edge-caddy` |
| Edge image | `caddy:2.10.2-alpine` |
| Compose file | `/srv/cybervpn/compose/edge/docker-compose.yml` |
| Caddyfile | `/srv/cybervpn/edge/caddy/Caddyfile` |

## Server-Side Changes

Created temporary edge runtime:

```text
/srv/cybervpn/compose/edge/docker-compose.yml
/srv/cybervpn/edge/caddy/Caddyfile
/srv/cybervpn/edge/caddy/data
/srv/cybervpn/edge/caddy/config
/srv/cybervpn/edge/caddy/site
```

Caddy is running through Docker Compose:

```text
cybervpn-edge-caddy: running
published ports: 80/tcp, 443/tcp
```

Configuration validation:

```text
caddy validate --config /etc/caddy/Caddyfile -> ok
```

## DNS Changes

Cloudflare DNS was changed to DNS-only A records for the temporary Stage 1 edge:

| Name | Target | Mode | Status |
|---|---:|---|---|
| `cyber-vpn.net` | `45.87.41.146` | DNS-only | verified |
| `www.cyber-vpn.net` | `45.87.41.146` | DNS-only | verified |
| `api.cyber-vpn.net` | `45.87.41.146` | DNS-only | verified |
| `admin.cyber-vpn.net` | `45.87.41.146` | DNS-only | verified |
| `status.cyber-vpn.net` | `45.87.41.146` | DNS-only | verified |
| `cyber-vpn.org` | `45.87.41.146` | DNS-only | verified |
| `admin.cyber-vpn.org` | `45.87.41.146` | DNS-only | verified |
| `www.cyber-vpn.org` | `45.87.41.146` | DNS-only | created, resolver propagation inconsistent |

IPv6 was not published as public DNS evidence for this step. The host has IPv6 configured, but the local verifier had no IPv6 route, so inbound IPv6 evidence is deferred.

## TLS Evidence

Caddy obtained Let’s Encrypt certificates for:

```text
admin.cyber-vpn.net
admin.cyber-vpn.org
api.cyber-vpn.net
cyber-vpn.net
cyber-vpn.org
status.cyber-vpn.net
www.cyber-vpn.net
www.cyber-vpn.org
```

Certificate spot checks:

```text
cyber-vpn.net:
  issuer: Let's Encrypt E8
  subject: CN = cyber-vpn.net
  notBefore: May 19 16:06:43 2026 GMT
  notAfter: Aug 17 16:06:42 2026 GMT

api.cyber-vpn.net:
  issuer: Let's Encrypt E8
  subject: CN = api.cyber-vpn.net
  notBefore: May 19 16:06:43 2026 GMT
  notAfter: Aug 17 16:06:42 2026 GMT
```

## Public Route Checks

| URL | Expected | Result |
|---|---|---|
| `http://cyber-vpn.net/` | `308` to HTTPS | pass |
| `http://cyber-vpn.net/.well-known/cybervpn-edge-health` | `200` | pass |
| `https://cyber-vpn.net/.well-known/cybervpn-edge-health` | `200`, TLS verified | pass |
| `https://www.cyber-vpn.net/.well-known/cybervpn-edge-health` | `200`, TLS verified | pass |
| `https://api.cyber-vpn.net/healthz` | `200`, TLS verified | pass |
| `https://admin.cyber-vpn.net/healthz` | `200`, TLS verified | pass |
| `https://status.cyber-vpn.net/` | `200`, TLS verified | pass |
| `https://cyber-vpn.org/en-EN/status` | `301` to `https://cyber-vpn.net/en-EN/status` | pass |
| `https://admin.cyber-vpn.org/ru-RU/login` | `301` to `https://admin.cyber-vpn.net/ru-RU/login` | pass |

All verified HTTPS checks returned:

```text
ssl_verify_result=0
```

## Edge Safety

Temporary Caddy policy:

```text
HTTP health endpoints are available for basic edge checks.
Regular HTTP traffic redirects to HTTPS.
HTTPS routes return temporary Stage 1 health responses.
.org web mirror redirects to cyber-vpn.net.
.org admin mirror redirects to admin.cyber-vpn.net.
```

Security headers on temporary responses:

```text
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: no-referrer
Permissions-Policy: interest-cohort=()
Cache-Control: no-store
```

Public listening ports after this step:

```text
22/tcp
80/tcp
443/tcp
```

UFW remains active with default deny incoming.

## Deferred Items

These are intentionally not completed in `STAGE1-RENT-03`:

| Item | Reason |
|---|---|
| Real frontend/API/admin routing | Belongs to `STAGE1-RENT-04` |
| Cloudflare proxy/WAF mode | Enable after app routing and webhook behavior are proven |
| IPv6 public DNS | Needs independent inbound IPv6 evidence |
| Production VPN node DNS | Belongs to VPN node proof step |
| Admin auth protection at app level | Belongs to app deploy and admin deploy steps |

## Next Step

```text
STAGE1-RENT-04: App compose and disabled-state deploy
```
