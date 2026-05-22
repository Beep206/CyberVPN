# Stage 2 Observability And Analytics

**Stage:** `S2-STAGE-11`
**Status:** Prepared for Public Release 1.0 readiness
**Date:** 2026-05-23
**Owner:** `@Sasha_Beep`

---

## 1. Purpose

Stage 2 observability must give the owner enough visibility to open CyberVPN beyond a narrow beta cohort without guessing. The target is not "more graphs"; the target is fast answers to operational questions:

- can users open the website, API, Mini App and admin login;
- can users receive subscription URLs and connect through the VPN node;
- are payments, refunds, renewals and reconciliation healthy;
- are subscriptions expiring and disabling correctly;
- is support overloaded or missing SLA;
- are frontend errors, release gates, backups and restore evidence healthy;
- are product analytics useful without slowing auth, checkout or VPN access.

The home server remains the main observability and GitLab/CI host. Customer-facing runtime remains on rented production infrastructure. Observability is important, but it must not become the only source of production truth.

---

## 2. Runtime Distribution

| Area | Stage 2 placement | Reason |
|---|---|---|
| Public website/frontend | Rented production app server | Must stay available if home power/internet is down |
| Public API/backend | Rented production app server | Required for auth, payment, trial, subscription and Mini App flows |
| Telegram Bot/Mini App runtime | Rented production app server | Customer path must not depend on home power |
| Remnawave control-plane | Rented production app server/private runtime | Required for provisioning and subscription state |
| VPN node | Dedicated node server only | Node must remain node-only; no observability relay or unrelated services |
| PostgreSQL/Valkey for production runtime | Production app topology | Must not depend on home server |
| GitLab, Grafana, Prometheus, Loki, Sentry, Alertmanager | Home server | Cost control and owner visibility |
| Evidence/archive/backup cold storage | Home server plus off-host where available | Keeps release and incident evidence accessible |

If home observability goes down, the customer service should continue to work. The loss is visibility, CI convenience and alerting, not the VPN itself.

---

## 3. Dashboard Contract

| Dashboard | File | Covers |
|---|---|---|
| Stage 2 Payment Reconciliation | `infra/grafana/dashboards/stage2-payment-reconciliation-dashboard.json` | payment success, failed payments, paid-but-no-access, reconciliation age, webhook failures/retries |
| Stage 2 Refund And Renewal | `infra/grafana/dashboards/stage2-refund-renewal-dashboard.json` | refunds, chargebacks, renewal success/failure, refund reasons |
| Stage 2 Subscription Expiry | `infra/grafana/dashboards/stage2-subscription-expiry-dashboard.json` | expiring subscriptions, disable failures, grace risk, expiry logs |
| Stage 2 Support SLA | `infra/grafana/dashboards/stage2-support-sla-dashboard.json` | open support items, overdue SLA, first-response p95, resolution p95 |
| Stage 2 Status Page Data Source | `infra/grafana/dashboards/stage2-status-page-dashboard.json` | `.net` customer edge, subscription route, `.org` VPN node TCP, home ops edge, TLS, synthetic failures |
| Stage 2 Product Analytics | `infra/grafana/dashboards/stage2-product-analytics-dashboard.json` | ingestion drops, Web Vitals, checkout conversion, funnel events |
| Stage 2 Release Quality Gates | `infra/grafana/dashboards/stage2-release-quality-dashboard.json` | security gates, SBOM age, restore drill age, Sentry frontend errors |

Dashboard generation source:

```text
scripts/grafana/generate-stage2-dashboards.py
```

The dashboards intentionally use `or vector(0)` for several future/full-S2 metrics. That makes them provision-safe before every backend metric exists, but it also means a zero panel can mean "no events" or "metric not emitted yet". The runbook must be used when interpreting those panels.

---

## 4. Prometheus And Blackbox Contract

### 4.1 Rule File

```text
infra/prometheus/rules/stage2_analytics_alerts.yml
```

The rule file provides:

- S2 payment/reconciliation recording rules;
- refund, chargeback and renewal signals;
- subscription expiry signals;
- support SLA signals;
- customer edge, subscription route, VPN node and home ops synthetic success ratios;
- TLS certificate age;
- product analytics ingestion signals;
- release quality signals.

### 4.2 Target Files

| File | Prometheus job | Module | Purpose |
|---|---|---|---|
| `infra/prometheus/targets/stage2-public-endpoints.json` | `stage2-public-endpoints` | `http_2xx` | `.net` website/API/Mini App/admin/status and `*.h.cyber-vpn.net` home ops |
| `infra/prometheus/targets/stage2-subscription-route.json` | `stage2-subscription-route` | `http_2xx_3xx_4xx` | Cloudflare-proxied subscription route existence using a synthetic unknown token |
| `infra/prometheus/targets/stage2-vpn-node-tcp.json` | `stage2-vpn-node-tcp` | `tcp_connect` | `.org` VPN node TCP ports |

The `.org` zone is reserved for subscription delivery and VPN node records. It is not a general website mirror. Continuous home monitoring currently probes the subscription route through the Cloudflare-proxied customer path because direct home-to-`45.87.41.146` probing is unreliable; `.org` subscription delivery still needs external release-smoke evidence before unrestricted S2 opening.

### 4.3 Why The Subscription Probe Accepts 4xx

The subscription route probe uses a fake token:

```text
https://cyber-vpn.net/api/sub/stage2-observability-synthetic-probe
```

A healthy system may answer `404`, `401` or `403` for an unknown token. That still proves the route, TLS, ingress and application path are alive. Timeout and `5xx` are failures.

---

## 5. Alert Matrix

| Alert | Priority | Meaning | First response |
|---|---:|---|---|
| `Stage2StatusEndpointDown` | P0 | Overall synthetic success ratio is below 95% | Open status dashboard, split customer vs home ops |
| `Stage2CustomerEdgeProbeFailed` | P0 | Website/API/Mini App/admin/status `.net` path failed | Check Cloudflare, Caddy, app containers and recent deploy |
| `Stage2SubscriptionRouteProbeFailed` | P0 | Subscription URL route failed | Check API route, Caddy, DNS/TLS and subscription proxy |
| `Stage2VpnNodeTcpProbeFailed` | P0 | VPN node ports failed | Check node server, firewall, Xray/Remnawave node state |
| `Stage2SecurityQualityGateFailed` | P0 | CI security gate failed | Stop release unless owner accepts documented risk |
| `Stage2PaymentReconciliationBacklog` | P1 | Paid-but-no-access or stale reconciliation exists | Open payment dashboard and support queue |
| `Stage2RefundSpike` | P1 | Refunds/chargebacks crossed threshold | Check provider and support reasons |
| `Stage2RenewalFailures` | P1 | Renewal ratio is low while traffic exists | Check payment provider and renewal jobs |
| `Stage2SubscriptionExpiryBacklog` | P1 | Expiry disable job has failures | Check worker and Remnawave state |
| `Stage2SupportSlaBreach` | P1 | Support SLA is overdue | Triage support queue and payment/access incidents |
| `Stage2HomeOpsEdgeProbeFailed` | P1 | Home ops public services have a probe failure | Check home server, Cloudflare tunnel/proxy and power/network |
| `Stage2TlsCertificateExpiresSoon` | P1 | Public TLS cert under 14 days | Check Cloudflare/Caddy certificate lifecycle |
| `Stage2AnalyticsIngestionDroppingEvents` | P1 | Product analytics drops/rejects events | Confirm analytics is not blocking checkout/auth |
| `Stage2RestoreDrillOverdue` | P1 | Restore drill evidence older than 30 days | Run restore drill under S2-STAGE-12 |
| `Stage2SentryFrontendErrorsElevated` | P1 | Frontend Sentry errors crossed threshold | Check release health and recent frontend deploy |

P0 alerts block S2 expansion. P1 alerts require owner review, but they do not automatically block customer runtime unless customer impact is confirmed.

---

## 6. Product Analytics Policy

Product analytics for Stage 2 should answer these questions:

- visit to registration conversion;
- registration to trial/payment conversion;
- plan selection and checkout start;
- payment success/failure by provider;
- subscription URL issued;
- VPN config viewed/copied;
- support contact opened;
- refund/cancel reason, if collected.

Rules:

1. Product analytics must be asynchronous.
2. Analytics must not block auth, checkout, provisioning, Mini App rendering or VPN config display.
3. Events must use stable names and low-cardinality labels.
4. Do not send raw Telegram init data, payment payloads, provider secrets, access tokens, refresh tokens, subscription URLs, VPN config URLs, private support notes or full request bodies.
5. Prefer aggregate counters and redacted event properties over user-level logs.

---

## 7. Sentry And Frontend Release Health

Stage 2 supports Sentry source map upload through:

```text
scripts/sentry/upload-frontend-sourcemaps.sh
```

Policy:

- source maps may be uploaded to Sentry, but must not be served publicly;
- `SENTRY_RELEASE` must match the deployed frontend release SHA/tag;
- source map upload remains opt-in through `SENTRY_UPLOAD_SOURCEMAPS=true`;
- Sentry events must be scrubbed for PII, tokens, payment payloads and subscription URLs;
- Sentry is an error investigation tool, not the authoritative source for billing or subscription state.

---

## 8. Status Page Source

The status page data exporter is:

```text
scripts/status/export-status-page-data.sh
```

It exports a machine-readable sample from Prometheus with:

- overall S2 probe success;
- customer `.net` edge success;
- subscription route success;
- `.org` VPN node TCP success;
- home ops edge success;
- TLS minimum days;
- synthetic failures and slow probes.

This file is a data source, not a public incident report. Human-readable incident wording should still be controlled by the owner.

---

## 9. Sensitive Logging Boundaries

The following must not appear in Loki, Grafana panels, Sentry events, analytics events or release evidence:

- payment provider API tokens and webhook secrets;
- Telegram bot token or raw `initData`;
- access/refresh JWTs;
- subscription URL tokens;
- raw VPN config links if they contain user-specific secrets;
- full payment webhook payloads;
- private support notes;
- full request/response bodies from auth, payment or subscription routes.

Allowed:

- aggregate counts;
- redacted IDs;
- provider name;
- payment status;
- plan code;
- route name;
- HTTP status;
- synthetic probe result;
- incident/evidence references.

---

## 10. Known Gaps And Recommendations

| Gap | Stage 2 decision | Recommendation |
|---|---|---|
| Some S2 metrics are future/full-S2 names | Dashboards show zero safely until emitters exist | Add backend/worker emitters incrementally as S2 payment, refund, renewal, support and analytics flows mature |
| Bot has no public health endpoint | Accepted | Use internal bot metrics plus Mini App/API/webhook/payment evidence; add public bot health only if it reveals no secrets |
| `.org` subscription route is not continuously probed from home | Accepted with explicit release-smoke requirement | Keep continuous probe on the Cloudflare-proxied route and prove real `.org` config delivery from an external network before unrestricted S2 opening |
| HTTP/3/QUIC is not proven by default blackbox exporter | Accepted with constraint | Keep HTTP/3/QUIC enabled; add a QUIC-capable external probe later if needed |
| Home observability can go offline | Accepted by architecture | Customer runtime must continue; keep backup email/Telegram and evidence workflow |
| Product analytics can create privacy risk | Controlled by policy | Use aggregate, asynchronous, redacted events only |

---

## 11. Acceptance Gate

`S2-STAGE-11` is ready when:

1. Stage 2 dashboards are valid and generated from source.
2. Prometheus loads Stage 2 rules and target jobs.
3. Customer `.net`, subscription route, VPN node `.org` and home ops probes are separated by labels.
4. P0/P1 alert names exist and point to runbooks.
5. The artifact validator passes.
6. Public endpoint smoke checks are captured as evidence.
7. Sensitive logging boundaries are documented.
8. Remaining gaps are explicit and do not block customer runtime.
