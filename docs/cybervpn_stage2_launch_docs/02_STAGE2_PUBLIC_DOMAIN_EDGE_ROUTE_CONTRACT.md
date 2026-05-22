# Stage 2 Public Domain, Edge, And Route Contract

**Stage:** `S2-STAGE-03`
**Status:** Approved route contract
**Date:** 2026-05-22
**Product stage:** CyberVPN Public Release 1.0

---

## 1. Purpose

This document freezes the public domain, edge, route and node/subscription contract for S2.

S2 must not keep changing route meaning while we implement payments, auth, catalog, subscription lifecycle and public release. If a later task changes this contract, it must create new evidence and explicitly reference `S2-STAGE-03`.

---

## 2. Hard Route Rules

1. `cyber-vpn.net` is the primary public customer domain.
2. `www.cyber-vpn.net` redirects to `cyber-vpn.net`.
3. `api.cyber-vpn.net` is the production API and webhook domain.
4. `admin.cyber-vpn.net` is the production admin/support domain.
5. `.org` is reserved for VPN node and subscription delivery only.
6. `.org` must not be used as a general customer-site mirror.
7. `cyber-vpn.org` may expose subscription routes and otherwise redirect to `.net`.
8. `admin.cyber-vpn.org` redirects to `admin.cyber-vpn.net`.
9. `de-1.cyber-vpn.org` is a VPN node hostname.
10. The VPN node server must run only node workload and operating-system basics.
11. HTTP/3/QUIC must remain enabled and must never be disabled as a troubleshooting shortcut.
12. Telegram/payment webhooks must be reachable without Cloudflare/Caddy challenge pages, while application-layer signatures remain mandatory.

---

## 3. Current Production Edge Topology

| Area | Current State | S2 Contract |
|---|---|---|
| Edge runtime | `cybervpn-edge-caddy`, image `caddy:2.10.2-alpine` | Containerized Caddy is the active edge, not host `/etc/caddy/Caddyfile` |
| Public ports | `80/tcp`, `443/tcp`, `443/udp` | `443/udp` remains required for HTTP/3/QUIC |
| App release tag at check time | `stage1-direct-suburl-refresh-20260522T091303Z` | S2 deploys must move to immutable S2 tags/SHAs later |
| Edge health path | `/.well-known/cybervpn-edge-health` and `/healthz` | Must remain available on public domains where useful |
| Caddy validation | `Valid configuration` | Warnings about formatting/auto HTTPS are not S2 blockers |

The active Caddy config includes:

```text
servers {
    protocols h1 h2 h3
}
```

This is the contract-level proof that edge HTTP/3 is configured. Public response headers also expose `alt-svc: h3=":443"`.

---

## 4. DNS Contract

| Name | Current Resolution | Contract |
|---|---|---|
| `cyber-vpn.net` | Cloudflare proxied A/AAAA | Main public site |
| `www.cyber-vpn.net` | Cloudflare proxied A/AAAA | Redirect to `cyber-vpn.net` |
| `api.cyber-vpn.net` | Cloudflare proxied A/AAAA | API and webhook domain |
| `admin.cyber-vpn.net` | Cloudflare proxied A/AAAA | Admin/support domain |
| `cyber-vpn.org` | `45.87.41.146` | Subscription route plus redirect for non-subscription paths |
| `admin.cyber-vpn.org` | `45.87.41.146` | Redirect to `admin.cyber-vpn.net` |
| `de-1.cyber-vpn.org` | `77.90.13.29`, `2a0a:51c1:9:c3::a` | VPN node hostname |
| `api.cyber-vpn.org` | No production record observed | Do not introduce unless explicitly required for subscription delivery |
| `sub.cyber-vpn.org` | No production record observed | Do not introduce unless explicitly required for subscription delivery |

S2 keeps subscription delivery in `.org`, but the currently active subscription path is `https://cyber-vpn.org/api/sub/...`, not a separate `sub.cyber-vpn.org` host.

---

## 5. TLS And QUIC Contract

| Host | Observed TLS/Route State | S2 Requirement |
|---|---|---|
| `cyber-vpn.net` | Let's Encrypt certificate, expires 2026-08-01; Cloudflare path advertises HTTP/3 | Monitor TLS expiry and keep HTTP/3 enabled |
| `api.cyber-vpn.net` | Let's Encrypt certificate, expires 2026-08-01; Cloudflare path advertises HTTP/3 | Monitor TLS expiry and webhook reachability |
| `admin.cyber-vpn.net` | Let's Encrypt certificate, expires 2026-08-01; Cloudflare path advertises HTTP/3 | Monitor TLS expiry and admin login route |
| `cyber-vpn.org` | Let's Encrypt certificate, expires 2026-08-17; direct Caddy path advertises HTTP/3 | Keep only subscription/non-sub redirect behavior |
| `admin.cyber-vpn.org` | Let's Encrypt certificate, expires 2026-08-17; direct Caddy path advertises HTTP/3 | Redirect only |
| `de-1.cyber-vpn.org` | REALITY/Xray-style node endpoint, not normal web TLS | Do not validate as a web page certificate |

`de-1.cyber-vpn.org` may present camouflage/SNI behavior expected for the VPN transport. It must not be treated as a failed website TLS check.

---

## 6. Route Map

| Route | Expected Behavior | Evidence State |
|---|---|---|
| `https://cyber-vpn.net/` | Redirect to locale path such as `/en-EN` | Observed `307`, HTTP/3 advertised |
| `https://www.cyber-vpn.net/` | Redirect to `https://cyber-vpn.net/` | Observed `301`, HTTP/3 advertised |
| `https://cyber-vpn.net/.well-known/cybervpn-edge-health` | Edge health JSON | Observed `200` |
| `https://api.cyber-vpn.net/health` | Backend/API health JSON | Observed `200 {"status":"ok"}` |
| `https://api.cyber-vpn.net/.well-known/cybervpn-edge-health` | Edge health JSON | Observed `200` |
| `https://api.cyber-vpn.net/webhook/telegram` | Telegram webhook endpoint, POST-only | Observed `405` on GET with `Allow: POST` |
| `https://api.cyber-vpn.net/api/v1/webhooks/cryptobot` | CryptoBot webhook, signature required | Observed `401 Invalid webhook signature` on unsigned POST |
| `https://api.cyber-vpn.net/api/v1/webhooks/remnawave` | Remnawave webhook, POST-only | Previously observed `405` on GET with `Allow: POST` |
| `https://admin.cyber-vpn.net/ru-RU` | Admin app route redirects unauthenticated user to login | Observed `307 /ru-RU/login` |
| `https://cyber-vpn.org/` | Redirect to `https://cyber-vpn.net/` | Observed `301`, HTTP/3 advertised |
| `https://cyber-vpn.org/api/sub/...` | Proxy to Remnawave subscription surface | Observed Remnawave-style `404 Resource not found` for fake token, not redirect |
| `https://admin.cyber-vpn.org/` | Redirect to `https://admin.cyber-vpn.net/` | Observed `301` |
| `https://de-1.cyber-vpn.org:443` | VPN node transport | Owned by Remnawave node/Xray runtime, not Caddy |

---

## 7. Admin Protection Contract

Current production behavior:

1. `admin.cyber-vpn.net` reaches the admin application.
2. Unauthenticated users are redirected to `/ru-RU/login`.
3. The route is not protected by a separate Caddy basic-auth or IP allowlist gate at this check.

S2 rule:

1. This is acceptable only as a documented current state for `S2-STAGE-03`.
2. Before broad public S2 opening, `S2-STAGE-13` must decide and prove the final admin protection model:
   - Cloudflare Access;
   - IP allowlist;
   - VPN/private access;
   - Caddy basic-auth in front of app login;
   - or an explicit owner-accepted app-auth-only risk.
3. Admin authentication, 2FA and audit trails remain mandatory regardless of edge gate choice.

---

## 8. Webhook Contract

Webhook paths belong on `api.cyber-vpn.net`.

| Webhook | Route | Required Gate |
|---|---|---|
| Telegram Bot | `https://api.cyber-vpn.net/webhook/telegram` | No challenge page; POST-only; bot token/handler validation |
| CryptoBot/Crypto Pay | `https://api.cyber-vpn.net/api/v1/webhooks/cryptobot` | No challenge page; provider signature mandatory; unsigned request rejected |
| Remnawave | `https://api.cyber-vpn.net/api/v1/webhooks/remnawave` | No challenge page; POST-only; application validation |

Do not use `https://cyber-vpn.net/webhook/telegram` as the canonical webhook URL. That path belongs to the frontend host and can be locale-routed.

---

## 9. VPN Node Contract

Current node:

```text
host: de-1.cyber-vpn.org
server: 77.90.13.29
ipv6: 2a0a:51c1:9:c3::a
container: cybervpn-remnawave-node remnawave/node:2.7.0
```

Observed public/listening node ports include:

| Port | Purpose |
|---|---|
| `443/tcp` | VLESS/REALITY/XHTTP-facing node transport |
| `8443/tcp` | Remnawave node core/control transport |
| `22230/tcp` | Remnawave node internal/service port |
| `22/tcp` | SSH administration |

Only OS basics, SSH and Remnawave node runtime are allowed on the VPN node server. Do not place GitLab, observability, frontend, API, database, Caddy public site, mail, or monitoring stack on the VPN node.

---

## 10. Growth And Recurring Scope Amendment

The owner changed the S2 scope on 2026-05-22: referral, promo, gift and true autoprolongation are approved for S2.

This does not change the domain/edge route contract. These features must map to later S2 gates:

| Feature | Primary Gate | Notes |
|---|---|---|
| Referral | `S2-STAGE-13` | Abuse, self-referral, duplicate subject, rate limits, kill switch, audit |
| Promo/checkout discounts | `S2-STAGE-06` and `S2-STAGE-13` | Payment/refund/idempotency plus abuse/stacking rules |
| Gift purchase/redeem | `S2-STAGE-06`, `S2-STAGE-09`, `S2-STAGE-13` | Payment ownership, redeem idempotency, support reversal and abuse controls |
| Autoprolongation | `S2-STAGE-07` | User consent, cancel flow, failed renewal, reminders, refund behavior |

Until those gates pass, the features must stay hidden or disabled by kill switch in production.

---

## 11. No-Go Conditions

Do not proceed to public opening if any of these become true:

1. HTTP/3/QUIC is disabled on the public edge.
2. `.org` becomes a general `.net` mirror again.
3. subscription URLs no longer use `.org` where expected.
4. webhook paths are blocked by a browser challenge page.
5. webhook signature validation is bypassed.
6. admin route is publicly open without either edge protection or an explicit owner risk acceptance before `S2-STAGE-17`.
7. the VPN node server runs non-node workloads.
8. TLS expiry monitoring is missing before public opening.

---

## 12. Exit Decision

`S2-STAGE-03` is complete when:

1. this route contract is committed;
2. evidence exists for public route checks;
3. HTTP/3/QUIC proof is recorded;
4. the `.org` node/subscription rule is recorded;
5. known residual admin-edge risk is assigned to `S2-STAGE-13`;
6. the next stage remains `S2-STAGE-04: Public Catalog And Pricing Finalization`.
