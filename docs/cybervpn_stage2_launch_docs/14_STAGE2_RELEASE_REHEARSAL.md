# Stage 2 Full Staging/Public-Release Rehearsal

**Stage:** `S2-STAGE-15`
**Status:** Passed with controlled gaps
**Date:** 2026-05-23
**Owner:** `@Sasha_Beep`

---

## 1. Purpose

`S2-STAGE-15` rehearses CyberVPN Release 1.0 before opening broader public traffic.

The goal is to prove that the current release candidate can be identified, deployed by the approved path, observed, rolled back and moved into a controlled production canary without changing scope in the middle of launch.

This is a rehearsal gate, not a traffic-expansion gate.

---

## 2. Release Candidate Identity

Stage 2 release candidates use immutable tags:

```text
stage2-public-rc.N
```

The first S2 public-release candidate is:

```text
stage2-public-rc.1
```

Deployment and rollback must use immutable tag or commit SHA. Floating `main` is not an accepted production release identity.

GitLab is the primary repository authority. GitHub remains a mirror/fallback.

---

## 3. Rehearsal Scope

Covered by this stage:

- RC tag policy and deploy dry-run contract;
- public frontend route probes;
- public admin route probe;
- API health probe;
- `.org` subscription-only boundary probe;
- production app container health inventory;
- VPN node-only inventory;
- home observability health inventory;
- rollback artifact availability;
- known issue classification before canary.

Not executed automatically by this stage:

- live real-money payment;
- new production trial activation;
- new provisioning mutation;
- new VPN client connection from a fresh user;
- admin/support destructive action;
- refund against a real payment.

These actions are intentionally moved to `S2-STAGE-16` with owner-controlled canary users because they mutate production customer state.

---

## 4. User Journey Rehearsal Matrix

| Journey step | S2-STAGE-15 status | Evidence path |
|---|---|---|
| Visit website | Pass | `https://cyber-vpn.net/ru-RU` returned `200` |
| Login page reachable | Pass | `https://cyber-vpn.net/ru-RU/login` returned `200` |
| Telegram Mini App shell reachable | Pass | `https://cyber-vpn.net/ru-RU/miniapp/home` returned `200` |
| Public plans page reachable | Pass | `https://cyber-vpn.net/ru-RU/pricing` returned `200` |
| API health | Pass | `https://api.cyber-vpn.net/health` returned `{"status":"ok"}` |
| Admin login route reachable | Pass | `https://admin.cyber-vpn.net/ru-RU/login` returned `200` |
| Subscription boundary | Pass | invalid `.org` subscription token returned `404` |
| VPN node availability | Pass | `cybervpn-remnawave-node` is the only app container on the node |
| Full payment/trial/provision/connect flow | Controlled gap | Execute in `S2-STAGE-16` canary with owner/internal users |
| Expiry/renewal/refund simulation | Controlled gap | Covered by tests/docs; live simulation requires canary data |

---

## 5. Public Route Contract

S2 public release keeps the S1 domain decisions:

- customer website and app: `cyber-vpn.net`;
- admin: `admin.cyber-vpn.net`;
- API: `api.cyber-vpn.net`;
- VPN node and subscription delivery only: `cyber-vpn.org`;
- `.org` is not a customer mirror.

HTTP/3/QUIC must remain enabled. This stage verifies `alt-svc: h3` headers and does not change edge protocol settings.

Expected header marker:

```text
alt-svc: h3=":443"; ma=86400
```

---

## 6. Runtime Boundary Contract

`prod-app-1` may run the customer runtime:

- edge/Caddy;
- frontend;
- backend;
- admin;
- Telegram Bot;
- worker/scheduler;
- PostgreSQL;
- Valkey/Redis;
- Remnawave control-plane.

The production VPN node must remain node-only:

```text
cybervpn-remnawave-node
```

No GitLab, Sentry, Grafana, Prometheus, backend, frontend, admin, payment, database or support services may be placed on the VPN node.

---

## 7. Observability Rehearsal

Home observability remains the operator visibility plane:

- Prometheus;
- Grafana;
- Alertmanager;
- Loki;
- cAdvisor;
- node-exporter;
- blackbox-exporter;
- Uptime Kuma;
- Sentry;
- GitLab and GitLab Runner.

Customer runtime must continue to work if home observability is unavailable. Loss of home observability reduces visibility, not the VPN service itself.

Before canary expansion, review:

1. public probes;
2. API health;
3. payment reconciliation;
4. provisioning failures;
5. orphan paid/no-access queue;
6. worker lag/retry/dead-letter;
7. VPN node health;
8. Sentry critical errors;
9. Alertmanager firing alerts;
10. backup freshness.

---

## 8. Rollback Rehearsal

Rollback must be available before canary.

Validated rollback artifacts from `S2-STAGE-12` remain the current baseline:

```text
/srv/cybervpn/backups/s2-stage12-20260523T050454Z/rollback.override.yml
/srv/cybervpn/backups/s2-stage12-20260523T050454Z/rollback-command.txt
/srv/cybervpn/backups/s2-stage12-20260523T050454Z/rollback-dry-run.log
```

Observed rollback dry-run status:

```text
rollback_dry_run_status=ok
```

Before any S2 canary deploy, run a new rollback dry-run if the runtime image inventory changes materially.

---

## 9. Go / No-Go For S2-STAGE-16

Proceed to `S2-STAGE-16` only if all are true:

1. `stage2-public-rc.1` exists in GitLab first and GitHub mirror;
2. deploy dry-run for all app services passes;
3. public customer routes return expected statuses;
4. API health returns `ok`;
5. admin route is reachable and protected by the admin host boundary;
6. `.org` stays subscription/node-only;
7. VPN node remains node-only;
8. observability stack is reachable;
9. rollback artifact is available;
10. owner accepts the controlled gaps for live canary execution.

No-Go if:

- API health fails;
- frontend/login/Mini App routes are not reachable;
- VPN node is running non-node services;
- rollback artifact is missing;
- HTTP/3/QUIC is intentionally disabled;
- payment/trial/provisioning kill switches are changed without evidence;
- secrets appear in evidence, logs or bundles.

---

## 10. Controlled Gaps

| Gap | Impact | Decision |
|---|---|---|
| Full live payment/trial/provision/connect flow was not executed automatically in this stage | Real production user mutation is still unproven for S2 RC | Accept for rehearsal; execute with owner/internal canary in `S2-STAGE-16` |
| `stage2-public-rc.1` deploy was dry-run only | Runtime deploy contract is proven, but no new production restart happened | Accept because current runtime is already live; real deploy requires owner approval |
| Expiry/renewal/refund was not run against a real payment | Real provider refund behavior remains canary/manual | Accept until payment canary |
| GitLab is home-hosted | CI visibility can be interrupted by home outage | Accept because production customer runtime and rollback do not depend on GitLab |

---

## 11. Exit Criteria Result

`S2-STAGE-15` is accepted as:

```text
PASS_WITH_CONTROLLED_GAPS
```

Next stage:

```text
S2-STAGE-16: Production Canary Release
```
