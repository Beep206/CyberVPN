# S2-STAGE-03 Evidence: Public Domain, Edge, And Route Contract

**Date:** 2026-05-22
**Stage:** `S2-STAGE-03`
**Result:** PASS with assigned S2 security watch item
**Next stage:** `S2-STAGE-04: Public Catalog And Pricing Finalization`

---

## 1. Scope

This evidence records the S2 route contract check for:

1. `.net` public/customer routes;
2. `.org` node/subscription-only policy;
3. API and webhook reachability;
4. admin route behavior;
5. HTTP/3/QUIC presence;
6. production VPN node workload boundary;
7. owner scope amendment for referral/promo/gift/autoprolongation.

---

## 2. Documents Updated

| File | Purpose |
|---|---|
| `docs/cybervpn_stage2_launch_docs/01_STAGE2_SCOPE_BACKLOG_FREEZE.md` | Moved referral/promo/gift/autoprolongation from optional to approved gated S2 scope |
| `docs/cybervpn_stage2_launch_docs/02_STAGE2_PUBLIC_DOMAIN_EDGE_ROUTE_CONTRACT.md` | Added S2 route, edge, domain, webhook and node contract |
| `docs/plans/2026-05-22-cybervpn-stage2-public-release-master-plan.md` | Reflected gated S2 work for referral/promo/gift/autoprolongation in fixed S2 stages |

---

## 3. Production Edge Facts

Checked on `prod-app-1` (`45.87.41.146`).

```text
edge container: cybervpn-edge-caddy
edge image: caddy:2.10.2-alpine
active app tag: stage1-direct-suburl-refresh-20260522T091303Z
published ports: 80/tcp, 443/tcp, 443/udp
```

Caddy validation:

```text
Valid configuration
```

The active Caddyfile contains:

```text
servers {
    protocols h1 h2 h3
}
```

Conclusion: HTTP/3/QUIC is configured at edge level and UDP 443 is published.

---

## 4. DNS Snapshot

| Host | Observed Result | Status |
|---|---|---|
| `cyber-vpn.net` | Cloudflare A/AAAA | PASS |
| `www.cyber-vpn.net` | Cloudflare A/AAAA | PASS |
| `api.cyber-vpn.net` | Cloudflare A/AAAA | PASS |
| `admin.cyber-vpn.net` | Cloudflare A/AAAA | PASS |
| `cyber-vpn.org` | `45.87.41.146` | PASS |
| `admin.cyber-vpn.org` | `45.87.41.146` | PASS |
| `de-1.cyber-vpn.org` | `77.90.13.29`, `2a0a:51c1:9:c3::a` | PASS |
| `api.cyber-vpn.org` | No record observed | ACCEPTED |
| `sub.cyber-vpn.org` | No record observed | ACCEPTED |

`api.cyber-vpn.org` and `sub.cyber-vpn.org` are not required while the canonical subscription route is `https://cyber-vpn.org/api/sub/...`.

---

## 5. TLS And HTTP/3 Checks

| Route | Observed |
|---|---|
| `https://cyber-vpn.net/` | `307` to `/en-EN`, `alt-svc: h3=":443"; ma=86400`, HSTS |
| `https://api.cyber-vpn.net/health` | `200 {"status":"ok"}`, `alt-svc: h3=":443"; ma=86400`, HSTS |
| `https://admin.cyber-vpn.net/ru-RU` | `307` to `/ru-RU/login`, `alt-svc: h3=":443"; ma=86400`, HSTS |
| `https://cyber-vpn.org/` | `301` to `https://cyber-vpn.net/`, `alt-svc: h3=":443"; ma=2592000` |
| `https://admin.cyber-vpn.org/` | `301` to `https://admin.cyber-vpn.net/`, `alt-svc: h3=":443"; ma=2592000` |

Certificate expiry snapshot:

| Host | Expiry |
|---|---|
| `cyber-vpn.net` | 2026-08-01 |
| `cyber-vpn.org` | 2026-08-17 |
| `admin.cyber-vpn.org` | 2026-08-17 |

Conclusion: HTTP/3/QUIC remains enabled. TLS expiry must be monitored under `S2-STAGE-11`.

---

## 6. Route Checks

| Route | Expected | Observed | Result |
|---|---|---|---|
| `https://cyber-vpn.net/` | Public site locale redirect | `307` to `/en-EN` | PASS |
| `https://api.cyber-vpn.net/health` | API health | `200 {"status":"ok"}` | PASS |
| `https://api.cyber-vpn.net/webhook/telegram` | POST-only webhook | GET returns `405`, `Allow: POST` | PASS |
| `https://api.cyber-vpn.net/api/v1/webhooks/cryptobot` | Signature-protected webhook | unsigned POST returns `401 Invalid webhook signature` | PASS |
| `https://cyber-vpn.org/` | Non-subscription redirect to `.net` | `301` to `.net` | PASS |
| `https://cyber-vpn.org/api/sub/route-contract-smoke` | Reaches Remnawave subscription surface | Remnawave-style `404 Resource not found`, not redirect | PASS |
| `https://admin.cyber-vpn.org/` | Redirect to primary admin domain | `301` to `admin.cyber-vpn.net` | PASS |

---

## 7. Admin Route Watch Item

Observed:

```text
https://admin.cyber-vpn.net/ru-RU -> 307 /ru-RU/login
```

The admin app login is reachable publicly through Cloudflare/Caddy. No separate Caddy basic-auth or IP allowlist was observed in this route check.

Decision for S2:

1. This is not a blocker for documenting `S2-STAGE-03`.
2. It is a required watch item for `S2-STAGE-13`.
3. Before broad public opening, owner must choose and prove one of:
   - Cloudflare Access;
   - IP allowlist;
   - VPN/private access;
   - Caddy basic-auth in front of app login;
   - explicit owner risk acceptance for app-auth-only admin exposure.

---

## 8. VPN Node Boundary Check

Checked on `de-1.cyber-vpn.org` (`77.90.13.29`).

```text
hostname: de-1.cyber-vpn.org
container: cybervpn-remnawave-node remnawave/node:2.7.0 Up 2 days
```

Listening services observed:

| Port | Purpose |
|---|---|
| `22/tcp` | SSH |
| `443/tcp` | node transport |
| `8443/tcp` | Remnawave node/core |
| `22230/tcp` | Remnawave node service |
| localhost DNS/time/system ports | OS basics |

Conclusion: no extra customer app, GitLab, observability, mail, database or public web workload was observed on the VPN node. Node-only policy remains intact.

---

## 9. Scope Amendment Captured

Owner instruction on 2026-05-22:

```text
we do referral/promo/gift/autoprolongation in S2
```

Documentation update:

1. referral is now approved gated S2 scope under `S2-STAGE-13`;
2. promo/checkout discounts are approved gated S2 scope under `S2-STAGE-06` and `S2-STAGE-13`;
3. gift purchase/redeem is approved gated S2 scope under `S2-STAGE-06`, `S2-STAGE-09` and `S2-STAGE-13`;
4. true autoprolongation is approved gated S2 scope under `S2-STAGE-07`;
5. all four remain disabled/hidden until their gates pass.

This does not change `S2-STAGE-03` route behavior.

---

## 10. Decision

`S2-STAGE-03` is accepted as complete.

Residual watch items:

1. `S2-STAGE-11`: add/confirm TLS expiry, HTTP/3/edge health and route probes in observability.
2. `S2-STAGE-13`: close admin edge protection decision before broad public opening.
3. `S2-STAGE-13`: prove referral/promo/gift abuse controls before enabling them publicly.
4. `S2-STAGE-07`: prove autoprolongation consent/cancel/failure/refund lifecycle before enabling recurring billing.

Next step:

```text
S2-STAGE-04: Public Catalog And Pricing Finalization
```
