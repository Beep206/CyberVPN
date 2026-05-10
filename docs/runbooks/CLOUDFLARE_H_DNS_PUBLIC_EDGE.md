# Cloudflare DNS And Public Edge Runbook

## Purpose

This runbook describes how to publish CyberVPN ops services under `*.h.cyber-vpn.net` through the Caddy edge running on `10.10.10.34`.

## Current Public IP

RouterOS currently has this inbound WAN IP on `sfp-sfpplus1`:

```text
95.82.233.131
```

Do not create Cloudflare records pointing to private LAN addresses such as `10.10.10.34`.

## Required Router NAT

The home router should forward only HTTP/HTTPS to the new edge host:

```text
TCP 80  -> 10.10.10.34:80
TCP 443 -> 10.10.10.34:443
```

Keep a rollback note for router changes and debug Caddy on `10.10.10.34` offline if public HTTP/HTTPS stops responding.

Do not forward:

```text
22/tcp
Docker daemon ports
PostgreSQL
Redis
Prometheus
Loki
Sentry internal ports
GitLab internal ports
```

## Cloudflare DNS Records

Cloudflare zone:

```text
cyber-vpn.net
```

Create these records first:

| Type | Name | Content | Proxy status | TTL |
|---|---|---|---|---|
| A | `gitlab.h` | `95.82.233.131` | DNS only | Auto |
| A | `registry.h` | `95.82.233.131` | DNS only | Auto |
| A | `grafana.h` | `95.82.233.131` | DNS only initially | Auto |
| A | `sentry.h` | `95.82.233.131` | DNS only initially | Auto |
| A | `prometheus.h` | `95.82.233.131` | DNS only initially | Auto |
| A | `loki.h` | `95.82.233.131` | DNS only initially | Auto |
| A | `alerts.h` | `95.82.233.131` | DNS only initially | Auto |
| A | `uptime.h` | `95.82.233.131` | DNS only initially | Auto |

Keep `gitlab.h` and `registry.h` DNS-only at first. Cloudflare proxy can interfere with GitLab registry pushes, large uploads, and non-trivial GitLab request flows if not tuned.

Optional later simplification:

```text
A *.h 95.82.233.131
```

Do not use the wildcard until the explicit records are verified.

## Cloudflare UI Steps

1. Open Cloudflare dashboard.
2. Select the account.
3. Select the `cyber-vpn.net` website/zone.
4. Open `DNS` -> `Records`.
5. Click `Add record`.
6. Fill:
   - Type: `A`
   - Name: for example `gitlab.h`
   - IPv4 address / Content: `95.82.233.131`
   - Proxy status: `DNS only` for first bring-up
   - TTL: `Auto`
7. Click `Save`.
8. Repeat for each domain in the table.

## Verification Commands

From any machine:

```bash
dig +short gitlab.h.cyber-vpn.net @1.1.1.1
dig +short registry.h.cyber-vpn.net @1.1.1.1
dig +short grafana.h.cyber-vpn.net @1.1.1.1
```

For DNS-only records, each command should return:

```text
95.82.233.131
```

If a record is proxied, `dig` returns Cloudflare IP addresses instead. That is expected only after intentionally enabling proxy mode.

## Cloudflare SSL/TLS Settings

For proxied records later:

```text
SSL/TLS mode: Full (strict)
Always Use HTTPS: enabled after Caddy routes and certificates work
WAF managed rules: enabled before broad public launch
Rate limiting: add login-path rules where available
```

Do not switch admin interfaces to proxied/public mode until application login, 2FA, and proxy auth/access controls are confirmed.

## Current Caddy Edge On `10.10.10.34`

```text
Service: caddy.service
Config: /etc/caddy/Caddyfile
Public listeners: 80/tcp, 443/tcp
Admin API: 127.0.0.1:2019 only
On-demand TLS ask endpoint: 127.0.0.1:9123 only
Access log: /var/log/caddy/access.log
Evidence: /srv/storage/evidence/edge-caddy/
```

Caddy uses Cloudflare DNS-01 for the CyberVPN wildcard certificate `*.h.cyber-vpn.net`.

## Post-Router-Cutover Checks

After changing router NAT to `10.10.10.34`, verify from outside the LAN:

```bash
curl -I http://gitlab.h.cyber-vpn.net
curl -I http://grafana.h.cyber-vpn.net
```

Expected first response over HTTP:

```text
HTTP/1.1 308 Permanent Redirect
Location: https://...
```

Then test HTTPS:

```bash
curl -I https://gitlab.h.cyber-vpn.net
curl -I https://grafana.h.cyber-vpn.net
```

For CyberVPN service domains that do not have upstream containers yet, HTTPS should return a controlled `503`. Observability domains should return `401` before Basic Auth succeeds.
