# Stage 2 Scope, Backlog, And Decision Freeze

**Stage:** `S2-STAGE-02`
**Status:** Approved execution baseline
**Date:** 2026-05-22
**Product stage:** CyberVPN Public Release 1.0

---

## 1. Stage 2 Scope Statement

Stage 2 is **Public Release 1.0** for the CyberVPN B2C product.

The goal is to move from S1 Controlled Public Beta to a stable public B2C release where real users can:

1. open the public website or Telegram Mini App;
2. register or log in safely;
3. choose a public plan or use an approved trial path;
4. pay through a production-ready payment path;
5. receive VPN access through Remnawave;
6. receive a subscription URL/QR/config suitable for real VPN clients;
7. get support if payment, provisioning, login, or connection fails;
8. be covered by monitoring, alerts, backup, restore, rollback, legal, and support processes.

Stage 2 is not a rewrite, not a partner launch, not a native-client launch, and not an enterprise platform migration.

---

## 2. Frozen Launch Surface

### 2.1 Included Customer Surfaces

| Surface | S2 Status | Notes |
|---|---|---|
| Public website on `cyber-vpn.net` | Required | Main public web entry |
| API on `api.cyber-vpn.net` | Required | Customer/API runtime |
| Telegram Bot | Required | Bot remains a real S2 channel |
| Telegram Mini App | Required | Mini App remains a real S2 channel |
| Web customer cabinet | Required | Must support account/subscription/config/support basics |
| Admin/support surface | Required | Operational, not marketing |
| `.org` subscription/node surface | Required | `.org` is for VPN node/subscription only |

### 2.2 Excluded Customer Surfaces

| Surface | S2 Decision | Target |
|---|---|---|
| Full partner portal production launch | Excluded from S2 | S3 |
| Partner payouts | Excluded from S2 | S3 |
| Reseller storefronts | Excluded from S2 | S3 |
| iOS/Android store release | Excluded from S2 | S4 |
| Desktop client release | Excluded from S2 | S5 |
| Android TV release | Excluded from S2 | S5 |
| Browser extension release | Excluded from S2 | S5 |
| Helix/Verta/Beep mass rollout | Excluded from S2 | S6 |
| Kubernetes/Talos/GitOps migration as blocker | Excluded from S2 | S7 |

---

## 3. Hard Rules Frozen For S2

1. `cyber-vpn.net` remains the main public B2C domain.
2. `api.cyber-vpn.net` remains the customer API domain.
3. `admin.cyber-vpn.net` remains the admin domain.
4. `.org` is reserved for VPN node and subscription delivery only.
5. `.org` must not be reintroduced as a mirror of `.net`.
6. HTTP/3/QUIC must stay enabled.
7. The production VPN node must run only VPN node workload.
8. GitLab is first for CI/CD; GitHub remains fallback/mirror.
9. Production deploys use immutable commit SHA or immutable tag.
10. Public production deploy is not the first validation step for small fixes.
11. Payment, auth, provisioning, database, and security changes require local tests plus staging/prod-like evidence.
12. S2 does not open full public release until `S2-STAGE-17` Go/No-Go.

---

## 4. Required S2 Backlog

These items are required before CyberVPN can be called Public Release 1.0.

| ID | Stage | Work Item | Required Output |
|---|---|---|---|
| `S2-REQ-001` | `S2-STAGE-03` | Final route contract | `.net` public/customer routes, `.org` node/subscription routes, admin/API protections documented |
| `S2-REQ-002` | `S2-STAGE-03` | HTTP/3/QUIC proof | Evidence that QUIC is enabled and not disabled during edge changes |
| `S2-REQ-003` | `S2-STAGE-04` | Final public plan catalog | Public plans, hidden plans, RU-specific plans, traffic/device limits and visibility rules frozen |
| `S2-REQ-004` | `S2-STAGE-04` | Pricing/quote proof | Quote and plan display tested for en/ru critical paths |
| `S2-REQ-005` | `S2-STAGE-05` | Public registration policy | Signup mode, invite fallback, abuse controls, auth methods and rate limits documented/tested |
| `S2-REQ-006` | `S2-STAGE-05` | Auth flow proof | Email/password, Telegram linking, magic/OTP and approved OAuth paths tested |
| `S2-REQ-007` | `S2-STAGE-06` | Primary payment path proof | At least one production-ready payment path with success/failure/duplicate/webhook evidence |
| `S2-REQ-008` | `S2-STAGE-06` | Orphan payment controls | Paid-but-no-access/orphan queue with `<24h` escalation policy proven |
| `S2-REQ-009` | `S2-STAGE-06` | Reconciliation proof | Payment reconciliation process and dashboard evidence |
| `S2-REQ-010` | `S2-STAGE-07` | Subscription lifecycle proof | Active/expired/grace/manual-renewal/refund state behavior documented and tested |
| `S2-REQ-011` | `S2-STAGE-07` | Customer-visible lifecycle copy | No misleading autoprolongation or refund promises |
| `S2-REQ-012` | `S2-STAGE-08` | Remnawave provisioning proof | Trial/paid/manual grant provisioning proof |
| `S2-REQ-013` | `S2-STAGE-08` | Subscription URL proof | Primary config delivery uses subscription URL where appropriate, not raw `vless://` by default |
| `S2-REQ-014` | `S2-STAGE-08` | XHTTP proof | XHTTP available through subscription output where expected |
| `S2-REQ-015` | `S2-STAGE-08` | Node capacity decision | Decide if one node is enough for S2 canary/full opening or add second node |
| `S2-REQ-016` | `S2-STAGE-09` | Support workflow proof | Support can diagnose login/payment/provisioning/config issues |
| `S2-REQ-017` | `S2-STAGE-09` | Admin audit proof | Dangerous/manual support actions are audited and redacted |
| `S2-REQ-018` | `S2-STAGE-10` | Legal pack final pass | Terms, Privacy, AUP, Refund, Cookie and seller/contact copy confirmed |
| `S2-REQ-019` | `S2-STAGE-10` | Trust copy review | No unsupported no-logs/SLA/privacy/protocol claims |
| `S2-REQ-020` | `S2-STAGE-11` | S2 observability dashboards | Payment, refund/renewal, subscription expiry, support SLA, status, product, release quality dashboards active |
| `S2-REQ-021` | `S2-STAGE-11` | Alert delivery proof | Telegram/email alert delivery proven |
| `S2-REQ-022` | `S2-STAGE-12` | Backup/restore proof | PostgreSQL, Remnawave and critical evidence restore/rollback tested |
| `S2-REQ-023` | `S2-STAGE-13` | Security gate | Dependency audit, secret scan, bundle/env scan, WAF/rate limits, log redaction evidence |
| `S2-REQ-024` | `S2-STAGE-14` | GitLab CI/CD path | GitLab first, GitHub fallback, repeatable CI and deploy jobs |
| `S2-REQ-025` | `S2-STAGE-15` | Full release rehearsal | Full public-release user journey completed before production canary |
| `S2-REQ-026` | `S2-STAGE-16` | Production canary | Small public cohort proves register/pay/provision/connect/support |
| `S2-REQ-027` | `S2-STAGE-17` | Owner Go/No-Go | Formal owner decision for public B2C opening |
| `S2-REQ-028` | `S2-STAGE-18` | Stabilization loop | Daily post-launch checks and S3 readiness decision |

---

## 5. Optional S2 Backlog

These are allowed during S2 only if the required public-release path remains stable. They are not blockers for S2 Public Release 1.0.

| ID | Stage | Optional Item | Gate |
|---|---|---|---|
| `S2-OPT-001` | `S2-STAGE-06` | Additional payment methods | Only after primary payment path is stable |
| `S2-OPT-002` | `S2-STAGE-07` | True autoprolongation | Only after provider recurring support, user consent, cancel flow, failed-renewal handling, webhook idempotency, refund policy and staging/prod evidence |
| `S2-OPT-003` | `S2-STAGE-08` | Second VPN node | Add if canary/load/availability evidence requires it |
| `S2-OPT-004` | `S2-STAGE-03` | Load balancer / second app server | Add if traffic or availability evidence requires it |
| `S2-OPT-005` | `S2-STAGE-12` | Managed PostgreSQL HA | Add if budget and recovery goals require it |
| `S2-OPT-006` | `S2-STAGE-12` | Managed Redis/Valkey | Add if worker/cache availability requires it |
| `S2-OPT-007` | `S2-STAGE-11` | Public status page | Allowed after status source is reliable |
| `S2-OPT-008` | `S2-STAGE-04` | More languages beyond en/ru | Only after critical path copy is reviewed, not fallback-only |
| `S2-OPT-009` | `S2-STAGE-13` | Public referral/promo/gift/checkout discounts | Only after anti-abuse, idempotency, payment/refund tests, support workflow, legal copy and kill-switch evidence |
| `S2-OPT-010` | `S2-STAGE-08` | VMess/Trojan/Shadowsocks | Only if real S2 user need is proven; not part of default release |

---

## 6. Deferred To S3+

These must not be treated as S2 blockers.

| ID | Deferred Item | Target |
|---|---|---|
| `S2-DEF-001` | Partner payouts | S3 |
| `S2-DEF-002` | Full partner/reseller portal production launch | S3 |
| `S2-DEF-003` | Reseller storefronts and settlement cycle | S3 |
| `S2-DEF-004` | Partner anti-fraud and payout reserves | S3 |
| `S2-DEF-005` | iOS/Android store release | S4 |
| `S2-DEF-006` | RevenueCat/mobile billing strategy | S4 |
| `S2-DEF-007` | Desktop client release | S5 |
| `S2-DEF-008` | Android TV release | S5 |
| `S2-DEF-009` | Browser extension release | S5 |
| `S2-DEF-010` | Helix/Verta/Beep private transport beta | S6 |
| `S2-DEF-011` | Helix as default/mass transport | S6+ |
| `S2-DEF-012` | Kubernetes/Talos/GitOps migration as platform target | S7 |
| `S2-DEF-013` | Enterprise policies, mature RBAC, abuse operations at scale | S7 |

---

## 7. Owner Decisions Frozen For S2

| Decision | S2 Value |
|---|---|
| Launch model | Public B2C Release 1.0 after S2 gates |
| Customer runtime | Rented infrastructure, not home server |
| Home server role | GitLab, CI, observability, evidence, logs, operations; non-critical for customer runtime |
| Primary public domain | `cyber-vpn.net` |
| Subscription/node domain policy | `.org` only for node/subscription |
| HTTP/3/QUIC | Must remain enabled |
| Git authority | GitLab first; GitHub fallback/mirror |
| Release authority | Immutable SHA/tag |
| Public signup | To be opened only after `S2-STAGE-05` controls |
| Payment opening | To be opened only after `S2-STAGE-06` evidence |
| Autoprolongation | Not promised by default; optional only with full recurring evidence |
| Public growth/referral/promo/gift flows | Not required for S2; default disabled unless optional S2 gate is fully met |

---

## 8. S2 Go/No-Go Rules

### Go Criteria

CyberVPN can proceed to public B2C opening only if:

1. `S2-STAGE-03` through `S2-STAGE-16` are complete or explicitly accepted by owner.
2. Public website, Mini App, Bot, API and subscription delivery are healthy.
3. At least one payment path is production-ready and monitored.
4. Paid-but-no-access/orphan payment queue has no item older than 24 hours.
5. Trial/paid/manual provisioning works through Remnawave.
6. Subscription URL delivery works and uses `.org` for subscription/node surface.
7. XHTTP behavior is proven where promised.
8. Support can diagnose and escalate normal user problems.
9. Legal/trust copy is final and does not overpromise.
10. Alerts reach Telegram/email.
11. Backup/restore/rollback evidence exists.
12. Security/abuse/privacy gate has no high/critical blocker.
13. Owner accepts residual risks.

### No-Go Criteria

CyberVPN must not open public B2C release if any of these remain unresolved:

1. payment success/failure/duplicate webhook behavior is not proven;
2. users can pay but fail to receive access without escalation;
3. Remnawave provisioning is unreliable or opaque to support;
4. public signup lacks abuse/rate-limit controls;
5. `.org` node/subscription route policy is broken;
6. HTTP/3/QUIC is accidentally disabled;
7. admin/support access is exposed or unaudited;
8. legal/refund/support public copy is missing or misleading;
9. alert delivery is unproven;
10. rollback/restore is theoretical only;
11. high/critical security issue is open;
12. owner/support availability is not accepted for launch window.

---

## 9. Change Control

After this freeze:

1. new tasks must map to an existing `S2-STAGE-*`;
2. top-level S2 stage numbers must not change;
3. S3/S4/S5/S6/S7 ideas must be marked deferred unless owner explicitly changes the roadmap;
4. public production deploys must reference the relevant `S2-STAGE-*`;
5. changes to payment, auth, provisioning, DB, security or route policy require evidence before production enablement.

---

## 10. Next Stage

After this freeze, proceed to:

```text
S2-STAGE-03: Public Domain, Edge, And Route Contract
```
