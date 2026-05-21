# STAGE1-RENT-11D - Cloudflare User-Path Probe Evidence

Date: `2026-05-20T17:56:19Z`
Scope: close the Stage 1 public endpoint monitoring authority gap without using the VPN node as a relay.
Result: `PASS_CLOUDFLARE_USER_PATH_PROBES_GREEN`

## Summary

`STAGE1-RENT-11D` switches the public `.net` Stage 1 user-path hostnames to Cloudflare-proxied DNS and validates home Prometheus blackbox probes through the same public hostnames users open.

This closes the monitoring-authority gap for public web/API/admin/status probes:

```text
home observability server
-> Cloudflare edge
-> prod-app-1 origin
```

The direct home public IP to `prod-app-1` origin path remains a known upstream/provider issue from `STAGE1-RENT-11C`, but it is no longer the active user-path monitoring authority for Stage 1 public endpoints.

The VPN node remains node-only. No probe relay/exporter/support/backend/payment workload was added to `prod-vpn-node-1`.

## Cloudflare DNS Changes

The following `cyber-vpn.net` A records were switched to Cloudflare proxy:

| Hostname | Origin | Proxied | TTL |
|---|---:|---:|---:|
| `cyber-vpn.net` | `45.87.41.146` | `true` | `1` |
| `www.cyber-vpn.net` | `45.87.41.146` | `true` | `1` |
| `api.cyber-vpn.net` | `45.87.41.146` | `true` | `1` |
| `admin.cyber-vpn.net` | `45.87.41.146` | `true` | `1` |
| `status.cyber-vpn.net` | `45.87.41.146` | `true` | `1` |

No `.org` VPN-node records were changed.

## DNS Evidence

After the prior DNS-only TTL expired, home resolution returned Cloudflare edge IPs:

| Hostname | A records |
|---|---|
| `cyber-vpn.net` | `104.21.85.196`, `172.67.209.233` |
| `www.cyber-vpn.net` | `104.21.85.196`, `172.67.209.233` |
| `api.cyber-vpn.net` | `104.21.85.196`, `172.67.209.233` |
| `admin.cyber-vpn.net` | `104.21.85.196`, `172.67.209.233` |
| `status.cyber-vpn.net` | `104.21.85.196`, `172.67.209.233` |

## Home User-Path Curl Evidence

From `cybervpn-h-ops`, probes now reach Cloudflare and return user-facing responses:

| URL | Result | Remote IP | Notes |
|---|---:|---:|---|
| `https://cyber-vpn.net/.well-known/cybervpn-edge-health` | `200` | Cloudflare edge | `server: cloudflare`, `alt-svc: h3=":443"` |
| `https://api.cyber-vpn.net/health` | `200` | Cloudflare edge | `server: cloudflare`, `alt-svc: h3=":443"` |
| `https://admin.cyber-vpn.net/` | `307` | Cloudflare edge | redirect to locale path, `server: cloudflare` |
| `https://status.cyber-vpn.net/.well-known/cybervpn-edge-health` | `302` | Cloudflare edge | redirect to canonical status page |

`HTTP/3/QUIC` was not disabled on the origin. Cloudflare responses advertise `h3` to clients through `alt-svc`.

## Prometheus Evidence

Home Prometheus `blackbox-stage1-public-web` now reports all Stage 1 public targets green:

| Instance | `probe_success` | `probe_http_status_code` |
|---|---:|---:|
| `https://admin.cyber-vpn.net/ru-RU/login` | `1` | `200` |
| `https://api.cyber-vpn.net/health` | `1` | `200` |
| `https://cyber-vpn.net/` | `1` | `200` |
| `https://cyber-vpn.net/en-EN` | `1` | `200` |
| `https://cyber-vpn.net/ru-RU/miniapp/home` | `1` | `200` |
| `https://cyber-vpn.net/ru-RU/miniapp/plans` | `1` | `200` |
| `https://status.cyber-vpn.net/` | `1` | `200` |
| `https://www.cyber-vpn.net/` | `1` | `200` |

No active `Stage1PublicEndpointProbeFailed` alert was returned by the Prometheus alert query after the user-path probes went green.

## Operational Decision

For Stage 1 controlled beta:

```text
Use Cloudflare-proxied public hostnames as the public endpoint monitoring authority.
Keep direct home -> origin failure recorded as an upstream/provider-path known issue.
Do not use prod-vpn-node-1 as a probe relay.
```

## Remaining Risk

Cloudflare user-path probes prove the public user path, not direct home-origin reachability. If origin-only monitoring is required later, close the `STAGE1-RENT-11C` provider/upstream issue through:

- JustHost/home ISP ticket;
- source whitelist;
- separate external probe host;
- or another approved non-node monitoring location.

Before enabling real paid webhooks or strict abuse/rate-limit decisions behind Cloudflare, verify:

- provider webhook paths are not challenged or cached by Cloudflare;
- origin/app logs preserve the real client IP through approved trusted proxy handling;
- webhook signature verification remains the source of truth, not source IP alone.

## Status

```text
GO for Stage 1 public endpoint user-path monitoring.
NO-GO remains for paid beta until catalog/prices and real payment -> provisioning evidence are complete.
NO relay on prod-vpn-node-1.
```
