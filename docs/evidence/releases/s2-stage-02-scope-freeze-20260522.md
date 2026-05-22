# S2-STAGE-02 Scope, Backlog, And Decision Freeze Evidence

**Date:** 2026-05-22
**Stage:** `S2-STAGE-02: S2 Scope, Backlog, And Decision Freeze`
**Result:** `GO to S2-STAGE-03`

---

## 1. Purpose

This stage freezes the Stage 2 Public Release 1.0 scope so implementation does not drift into Stage 3 partner work, Stage 4 mobile release, Stage 5 device expansion, Stage 6 private transport, or Stage 7 platform migration.

---

## 2. Created Document

Primary freeze document:

```text
docs/cybervpn_stage2_launch_docs/01_STAGE2_SCOPE_BACKLOG_FREEZE.md
```

It defines:

- S2 scope statement;
- frozen launch surface;
- S2 hard rules;
- required S2 backlog;
- optional S2 backlog;
- deferred S3+ backlog;
- owner decisions frozen for S2;
- S2 Go/No-Go and No-Go rules;
- change-control rules.

---

## 3. Required Scope Confirmed

S2 remains **Public Release 1.0 for B2C only**.

Required S2 surfaces:

| Surface | Status |
|---|---|
| Public website on `cyber-vpn.net` | Required |
| API on `api.cyber-vpn.net` | Required |
| Telegram Bot | Required |
| Telegram Mini App | Required |
| Web customer cabinet | Required |
| Admin/support surface | Required |
| `.org` subscription/node surface | Required |

Required S2 work areas:

- route/domain contract;
- final public catalog and pricing;
- public-safe auth/registration;
- production-ready payment path;
- subscription lifecycle;
- VPN provisioning and XHTTP/subscription URL proof;
- support/admin operations;
- legal/trust copy;
- observability and analytics;
- backup/restore/rollback;
- security/abuse/privacy gate;
- GitLab CI/CD and release speed;
- release rehearsal, canary, Go/No-Go and stabilization.

---

## 4. Optional Scope Confirmed

Optional S2 items are allowed only after the required public-release path is stable. They are not blockers.

| Optional Item | Gate |
|---|---|
| Additional payment methods | after primary payment path is stable |
| True autoprolongation | only with recurring support, consent, cancel, failed-renewal, webhook, refund and staging/prod evidence |
| Second VPN node | if canary/load/availability evidence requires it |
| Load balancer / second app server | if traffic or availability evidence requires it |
| Managed PostgreSQL HA | if budget/recovery goals require it |
| Managed Redis/Valkey | if worker/cache availability requires it |
| Public status page | after status source is reliable |
| More languages beyond en/ru | after reviewed copy exists |
| Public referral/promo/gift/checkout discounts | only with anti-abuse, idempotency, payment/refund tests, support workflow, legal copy and kill-switch evidence |
| VMess/Trojan/Shadowsocks | only if real user need is proven |

---

## 5. Deferred Scope Confirmed

These items are explicitly not S2 blockers:

| Deferred Item | Target |
|---|---|
| Partner payouts | S3 |
| Full partner/reseller portal production launch | S3 |
| Reseller storefronts and settlement cycle | S3 |
| iOS/Android store release | S4 |
| RevenueCat/mobile billing strategy | S4 |
| Desktop client release | S5 |
| Android TV release | S5 |
| Browser extension release | S5 |
| Helix/Verta/Beep private transport beta | S6 |
| Helix as default/mass transport | S6+ |
| Kubernetes/Talos/GitOps migration | S7 |
| Enterprise policies/mature RBAC/abuse operations at scale | S7 |

---

## 6. Hard Rules Reconfirmed

| Rule | Result |
|---|---|
| `cyber-vpn.net` is main public B2C domain | Frozen |
| `.org` is for node/subscription only | Frozen |
| `.org` is not a `.net` mirror | Frozen |
| HTTP/3/QUIC must remain enabled | Frozen |
| Production VPN node must run only node workload | Frozen |
| GitLab is first; GitHub is fallback/mirror | Frozen |
| Production deploys use immutable SHA/tag | Frozen |
| S2 does not open public release until `S2-STAGE-17` | Frozen |

---

## 7. Go/No-Go Rules Confirmed

S2 public opening requires:

- `S2-STAGE-03` through `S2-STAGE-16` complete or explicitly accepted;
- healthy public website, Mini App, Bot, API and subscription delivery;
- at least one production-ready monitored payment path;
- no paid-but-no-access/orphan payment older than 24 hours;
- working Remnawave provisioning;
- `.org` subscription/node delivery;
- XHTTP proof where promised;
- support/admin operational readiness;
- final legal/trust copy;
- working alert delivery;
- backup/restore/rollback evidence;
- no high/critical security blocker;
- owner acceptance of residual risks.

---

## 8. Security Review Notes

This stage added documentation only. No runtime code or production configuration was changed.

Security relevance:

- no secrets should be present in docs;
- no public release is enabled by this stage;
- optional risky features such as autoprolongation and public referral/promo/gift flows remain gated and not required.

Verification:

| Check | Result |
|---|---|
| `git diff --check` | PASS |
| Targeted secret-pattern scan on new S2 docs/evidence | PASS: matches were policy words such as `secret scan` and `Email/password`, not secret values |
| Targeted dangerous-pattern scan on new S2 docs/evidence | PASS: no matches |
| Full repository secret scan | PASS: no leaks found |
| `npm audit --omit=dev --audit-level=high` | PASS for high/critical; existing moderate advisories remain |

Moderate dependency watch items remain unchanged from previous S2 gates:

- `brace-expansion` moderate advisory through transitive dependencies;
- `postcss` moderate advisory through the bundled Next dependency.

Track dependency cleanup under `S2-STAGE-13` and `S2-STAGE-14`.

---

## 9. Decision

`S2-STAGE-02` is complete.

Decision:

```text
GO: proceed to S2-STAGE-03: Public Domain, Edge, And Route Contract.
```

Rationale:

- S2 is now frozen as B2C Public Release 1.0;
- required, optional and deferred work are separated;
- S3/S4/S5/S6/S7 work is not allowed to block S2;
- owner Go/No-Go rules are explicit;
- top-level stage numbering remains unchanged.

---

## 10. Next Stage

```text
S2-STAGE-03: Public Domain, Edge, And Route Contract
```
