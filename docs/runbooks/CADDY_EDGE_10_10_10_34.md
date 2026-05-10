# Caddy Edge On 10.10.10.34

## Purpose

`10.10.10.34` is the central HTTP/HTTPS edge for CyberVPN. Caddy runs as a systemd service and owns public ports `80` and `443`.

## Files

```text
/etc/caddy/Caddyfile
/var/log/caddy/access.log
/srv/storage/evidence/edge-caddy/
```

## Public Routes

| Domain | Upstream |
|---|---|
| `gitlab.h.cyber-vpn.net` | `127.0.0.1:8081` |
| `registry.h.cyber-vpn.net` | `127.0.0.1:5050` |
| `grafana.h.cyber-vpn.net` | `127.0.0.1:3000` |
| `sentry.h.cyber-vpn.net` | `127.0.0.1:9000` |
| `prometheus.h.cyber-vpn.net` | `127.0.0.1:9090` |
| `loki.h.cyber-vpn.net` | `127.0.0.1:3100` |
| `alerts.h.cyber-vpn.net` | `127.0.0.1:9093` |
| `uptime.h.cyber-vpn.net` | `127.0.0.1:3001` |

## Listener Policy

```text
0.0.0.0:80      public HTTP and ACME HTTP-01
0.0.0.0:443     public HTTPS
127.0.0.1:2019  Caddy admin API
127.0.0.1:9123  on-demand TLS allowlist endpoint
```

UFW should allow only:

```text
22/tcp from 10.10.10.0/24
80/tcp from anywhere
443/tcp from anywhere
```

## Validate And Reload

```bash
sudo caddy validate --config /etc/caddy/Caddyfile
sudo chown -R caddy:caddy /var/log/caddy
sudo systemctl reload caddy || sudo systemctl restart caddy
sudo systemctl status caddy --no-pager
```

If `caddy validate` creates `/var/log/caddy/access.log` as root, fix ownership before restarting:

```bash
sudo chown -R caddy:caddy /var/log/caddy
```

## Local Checks

```bash
systemctl is-active caddy
ss -tulpen | awk 'NR==1 || /:(80|443|2019|9123)[[:space:]]/'
curl -i http://127.0.0.1/
curl -I -H 'Host: gitlab.h.cyber-vpn.net' http://127.0.0.1/
curl -i 'http://127.0.0.1:9123/ask?domain=gitlab.h.cyber-vpn.net'
curl -i 'http://127.0.0.1:9123/ask?domain=evil.example'
```

Expected:

```text
caddy active
2019 and 9123 bound to 127.0.0.1
domain HTTP requests return 308 to HTTPS
allowed TLS ask returns 200
unknown TLS ask returns 403
```

## Router Cutover

Change router NAT:

```text
TCP 80  -> 10.10.10.34:80
TCP 443 -> 10.10.10.34:443
```

Do not forward SSH or any app/database/internal service port.

## RouterOS Current State

Applied on `2026-05-09`:

```text
WAN: sfp-sfpplus1
WAN IP: 95.82.233.131
LAN: 10.10.10.0/24
HTTP dst-nat: 95.82.233.131:80  -> 10.10.10.34:80
HTTPS dst-nat: 95.82.233.131:443 -> 10.10.10.34:443
```

RouterOS static DNS for CyberVPN LAN access:

```text
gitlab.h.cyber-vpn.net        -> 10.10.10.34
registry.h.cyber-vpn.net      -> 10.10.10.34
grafana.h.cyber-vpn.net       -> 10.10.10.34
sentry.h.cyber-vpn.net        -> 10.10.10.34
prometheus.h.cyber-vpn.net    -> 10.10.10.34
loki.h.cyber-vpn.net          -> 10.10.10.34
alerts.h.cyber-vpn.net        -> 10.10.10.34
uptime.h.cyber-vpn.net        -> 10.10.10.34
```

Evidence:

```text
docs/evidence/caddy/phase11-service-routes-20260509T165414Z.txt
/srv/storage/evidence/edge-caddy/caddy-cloudflare-dns-20260509T160511Z
/srv/storage/evidence/edge-caddy/caddy-dns01-enable-20260509T161747Z
```

## Current Public HTTPS State

Observed on `2026-05-09`: `*.h.cyber-vpn.net` is issued through Cloudflare DNS-01 and served by Caddy on `10.10.10.34`.

Current h-domain behavior before application deployment:

```text
gitlab.h.cyber-vpn.net      -> valid TLS, 503 until authenticated upstream exists
registry.h.cyber-vpn.net    -> valid TLS, 503 until authenticated upstream exists
grafana.h.cyber-vpn.net     -> valid TLS, Caddy Basic Auth, then 503 until upstream exists
sentry.h.cyber-vpn.net      -> valid TLS, 503 until authenticated upstream exists
prometheus.h.cyber-vpn.net  -> valid TLS, Caddy Basic Auth, then 503 until upstream exists
loki.h.cyber-vpn.net        -> valid TLS, Caddy Basic Auth, then 503 until upstream exists
alerts.h.cyber-vpn.net      -> valid TLS, Caddy Basic Auth, then 503 until upstream exists
uptime.h.cyber-vpn.net      -> valid TLS, Caddy Basic Auth, then 503 until upstream exists
```

The Caddyfile uses one wildcard site block for `*.h.cyber-vpn.net`, with host matchers for each upstream. This avoids many simultaneous ACME DNS-01 orders.

The observability Basic Auth secret is stored on `10.10.10.34`:

```text
/srv/cybervpn-h/secrets/caddy/observability-basic-auth.env
```

The public edge health endpoint is available on all h-domains:

```text
/.well-known/cybervpn-edge-health -> 200 ok
```

See [CADDY_DNS01_CLOUDFLARE.md](CADDY_DNS01_CLOUDFLARE.md).
