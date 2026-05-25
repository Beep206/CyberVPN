# Stage 3 Scope, Backlog, And Decision Freeze

**Stage:** `S3-STAGE-01`
**Status:** Approved execution baseline
**Date:** 2026-05-24
**Product stage:** CyberVPN Partner / Reseller Platform
**Prior gate:** `S3-STAGE-00_DECISION=APPROVE_OPTION_A`

---

## 1. Stage 3 Scope Statement

Stage 3 is the Partner / Reseller Platform stage for CyberVPN.

The goal is to prepare and then safely launch controlled partner growth without damaging the S2 public B2C runtime. A successful S3 means approved partners can apply, operate in a dedicated partner workspace, use approved tracking/codes/storefront contracts, see trustworthy reporting, pass finance and support gates, and participate in a controlled partner pilot under observable, reversible production controls.

Stage 3 is not a broad uncontrolled affiliate launch. It is not a mobile release, not a desktop release, not a Helix rollout, and not a full platform migration.

The S3 execution model is:

1. freeze scope and decisions;
2. freeze partner domain and roles;
3. prove event backbone in non-production;
4. prove transactional outbox dispatch and durable consumers;
5. deploy partner surfaces disabled-by-default;
6. prove onboarding, attribution, reporting, settlement sandbox, support, observability, security and legal gates;
7. deploy production disabled-state safely;
8. run a controlled partner pilot;
9. stabilize and decide whether to expand, pause, rollback, or prepare the next stage.

---

## 2. Frozen S3 Launch Surface

### 2.1 Included S3 Surfaces

| Surface | S3 Status | Notes |
|---|---|---|
| Partner portal | Required, gated | External partner workspace surface. Production access remains disabled until S3 gates. |
| Partner application flow | Required | Public or invite-only application, review state, status visibility and requested-info handling. |
| Partner workspace model | Required | Separate partner account/workspace, not a customer account with a flag. |
| Partner roles and permissions | Required | `workspace_owner`, `finance_manager`, `analyst`, `traffic_manager`, `support_manager`; extended roles modelled. |
| Partner admin/support operations | Required | Internal admin/support can review, approve, suspend, diagnose and audit partner flows. |
| Partner codes and attribution | Required | Creator/affiliate, performance and reseller attribution with anti-abuse gates. |
| Reseller storefront contract | Required, gated | Contract and route behavior frozen before any public storefront pilot. |
| Event backbone | Required, non-prod first | Real broker/dispatcher/consumer proof before production fan-out. |
| Reporting and analytics | Required | Partner reports must be explainable and reconcile to backend source of truth. |
| Settlement sandbox | Required | Payout logic simulated before any real payout process. |
| Controlled payouts | Required only for pilot gate | No broad payout launch. Manual/maker-checker only after S3 evidence. |
| Partner observability | Required | Grafana/Prometheus/Sentry/Loki coverage for S3 flows, lag, errors, risk and support. |
| Partner legal/support copy | Required | Partner terms, payout policy, support escalation and disclosure boundaries. |

### 2.2 Excluded From S3

| Surface | S3 Decision | Target |
|---|---|---|
| iOS/Android store release | Excluded | S4 |
| Desktop client release | Excluded | S5 |
| Android TV release | Excluded | S5 |
| Browser extension release | Excluded | S5 |
| Helix/Verta/Beep mass rollout | Excluded | S6 |
| Kubernetes/Talos/GitOps migration as mandatory blocker | Excluded | S7 |
| Enterprise hardening as full platform target | Excluded | S7 |
| Classical MLM | Prohibited | Never |
| Public broad partner payouts without maker-checker/evidence | Prohibited | Never |
| Treating customer invite/referral as cash payout ownership | Prohibited | Never |

---

## 3. Frozen Product Principles

1. S3 must not break S2 customer runtime.
2. S3 production functionality is disabled-by-default until the relevant S3 gate is passed.
3. Partner event backbone must be proven with real broker delivery before production partner fan-out.
4. `accepted_no_transport` is S2 stabilization evidence only; it is not S3 broker delivery evidence.
5. Partner portal is a separate partner workspace surface, not a customer dashboard tab with extra permissions.
6. One order has at most one cash payout owner.
7. Invite and consumer referral rewards never become cash payout owners.
8. Consumer growth and partner revenue programs stay separate across actor class, ledger, payout semantics, support and compliance.
9. Official CyberVPN surfaces do not expose self-serve reseller markup.
10. Partner-branded storefront pricing must be native storefront pricing, not visible "base price plus markup".
11. No real payout path is enabled without finance maker-checker, audit log, support workflow and rollback evidence.
12. Every partner-sensitive action must be auditable and redacted.
13. Every runtime change must reference an `S3-STAGE-*` identifier.
14. No new top-level `S3-STAGE-19+` number may be created without an explicit owner decision.
15. GitLab remains first for CI/CD; GitHub remains mirror/fallback.
16. Production deploys use immutable commit SHA or immutable tags.

---

## 4. Stage 3 Personas

| Persona | Required For S3 | Primary Needs |
|---|---|---|
| Partner applicant | Yes | Apply, verify identity, see status and next requested action. |
| Workspace owner | Yes | Accept contracts, manage workspace authority, team and sensitive confirmations. |
| Finance manager | Yes | See statements, payout readiness, payout accounts and blocked reasons. |
| Analyst | Yes | See dashboards, exports and attribution explanations. |
| Traffic manager | Yes | Manage codes, links, campaigns, traffic declarations and diagnostics. |
| Support manager | Yes | Work partner support cases and order/attribution issues inside workspace scope. |
| Technical manager | Modelled | Manage webhooks, API tokens, postbacks and diagnostics when enabled. |
| Legal/compliance manager | Modelled | Review contracts, declarations, policy history and remediation tasks. |
| Internal partner ops | Yes | Review applications, lane access, suspensions and support escalations. |
| Internal finance ops | Yes | Review settlement sandbox, payout readiness and manual payout gates. |
| Internal risk/support | Yes | Investigate abuse, disputes, attribution issues and partner cases. |

---

## 5. Required S3 Backlog

These items are required before CyberVPN can call S3 production-ready.

| ID | Stage | Work Item | Required Output |
|---|---|---|---|
| `S3-REQ-001` | `S3-STAGE-01` | S3 scope freeze | This document approved; no S4/S5/S6/S7 scope creep. |
| `S3-REQ-002` | `S3-STAGE-01` | S3 backlog freeze | All required work maps to `S3-REQ-*` and `S3-STAGE-*`. |
| `S3-REQ-003` | `S3-STAGE-01` | S3 kill switch matrix | Partner portal, storefronts, event backbone, attribution, payouts and exports independently pausable. |
| `S3-REQ-004` | `S3-STAGE-02` | Partner domain model | Partner account/workspace/user/role/status model frozen. |
| `S3-REQ-005` | `S3-STAGE-02` | Partner role contract | Required and modelled roles, permission matrix and sensitive action rules approved. |
| `S3-REQ-006` | `S3-STAGE-02` | Realm and auth boundary | Customer, partner, admin and service realms cannot be confused. |
| `S3-REQ-007` | `S3-STAGE-03` | Non-prod broker topology | NATS JetStream or approved equivalent chosen, deployed and documented outside customer runtime. |
| `S3-REQ-008` | `S3-STAGE-03` | Broker proof | Stream creation, publish, consume, ack and replay evidence. |
| `S3-REQ-009` | `S3-STAGE-03` | Event taxonomy | Subjects, stream names, event families, retention and replay rules frozen. |
| `S3-REQ-010` | `S3-STAGE-04` | Outbox dispatcher proof | `pending -> claimed -> submitted -> published` lifecycle proven. |
| `S3-REQ-011` | `S3-STAGE-04` | Consumer receipt proof | Durable consumer receipts/projections proven for at least one partner/growth event family. |
| `S3-REQ-012` | `S3-STAGE-04` | Idempotency proof | Duplicate/replay does not double-apply rewards, attribution, statements or settlements. |
| `S3-REQ-013` | `S3-STAGE-04` | Dead-letter and retry proof | Retry, lease, poison event and dead-letter behavior tested. |
| `S3-REQ-014` | `S3-STAGE-05` | Partner portal disabled boundary | Production can deploy partner code with external access disabled and safe fallback copy. |
| `S3-REQ-015` | `S3-STAGE-05` | Admin/backend gating | Partner APIs and admin actions hidden or blocked unless feature flags and roles allow them. |
| `S3-REQ-016` | `S3-STAGE-06` | Partner application flow | Application, review, requested-info and rejection/approval flows tested locally/staging. |
| `S3-REQ-017` | `S3-STAGE-06` | Partner onboarding evidence | Email/Telegram/support notifications and audit events proven. |
| `S3-REQ-018` | `S3-STAGE-07` | Workspace/team/RBAC | Team invites, role assignment, row-level scope and privilege escalation tests pass. |
| `S3-REQ-019` | `S3-STAGE-08` | Partner code lifecycle | Issue, redeem, expire, suspend and audit behavior proven. |
| `S3-REQ-020` | `S3-STAGE-08` | Attribution and anti-abuse | Explicit code, passive click, reseller binding, self-referral, duplicate and fraud gates proven. |
| `S3-REQ-021` | `S3-STAGE-09` | Storefront contract | Domain, route, pricing, legal, support and attribution behavior frozen. |
| `S3-REQ-022` | `S3-STAGE-09` | Storefront disabled proof | Public storefront routes do not open before pilot approval. |
| `S3-REQ-023` | `S3-STAGE-10` | Partner reporting | Dashboards/exports reconcile to backend source of truth and explain attribution. |
| `S3-REQ-024` | `S3-STAGE-10` | Analytics quality | Metrics dictionary, owner/no-owner ratios, lag and report freshness proven. |
| `S3-REQ-025` | `S3-STAGE-11` | Settlement sandbox | Statement, commission, hold, adjustment and payout simulation tested with synthetic data. |
| `S3-REQ-026` | `S3-STAGE-11` | Payout policy | Manual/maker-checker policy, hold periods, reserves, disputes and rollback approved. |
| `S3-REQ-027` | `S3-STAGE-12` | Partner support/admin ops | Support can diagnose partner application, code, attribution, reporting and finance issues. |
| `S3-REQ-028` | `S3-STAGE-12` | Audit and redaction | Sensitive actions audited; logs and exports do not leak secrets/PII beyond approved scope. |
| `S3-REQ-029` | `S3-STAGE-13` | Partner observability | Stage 3 Grafana dashboards, Prometheus rules, Sentry/Loki coverage and alerts active. |
| `S3-REQ-030` | `S3-STAGE-13` | Alert proof | Event lag, publish failure, consumer lag, payout risk, storefront errors and support backlog alerts tested. |
| `S3-REQ-031` | `S3-STAGE-14` | Security/privacy/legal gate | Partner terms, payout policy, privacy disclosures, abuse policy and security scans accepted. |
| `S3-REQ-032` | `S3-STAGE-14` | Abuse gate | Partner fraud, traffic quality, self-dealing, code leakage and suspicious payout handling documented/tested. |
| `S3-REQ-033` | `S3-STAGE-15` | Full partner staging rehearsal | End-to-end partner apply/review/code/attribution/reporting/settlement/support rehearsal evidence. |
| `S3-REQ-034` | `S3-STAGE-16` | Production disabled-state deploy | Production code deployed with partner runtime disabled and rollback documented. |
| `S3-REQ-035` | `S3-STAGE-17` | Controlled partner pilot | Limited approved partners operate under manual controls and active support watch. |
| `S3-REQ-036` | `S3-STAGE-18` | S3 stabilization | Continue/expand/pause/rollback decision based on evidence, not optimism. |

---

## 6. Kill Switch Matrix

All switches must default to disabled in production until their stage gate is passed.

| Switch | Default | Required Before Enablement | Owner |
|---|---|---|---|
| `PARTNER_PORTAL_ENABLED` | `false` | S3-STAGE-05 disabled boundary and S3-STAGE-16 production disabled-state proof | Product/ops |
| `PARTNER_APPLICATIONS_ENABLED` | `false` | S3-STAGE-06 onboarding flow evidence | Partner ops |
| `PARTNER_EVENT_BACKBONE_ENABLED` | `false` | S3-STAGE-03 and S3-STAGE-04 broker/dispatcher/consumer proof | Platform |
| `PARTNER_CODES_ENABLED` | `false` | S3-STAGE-08 lifecycle and anti-abuse evidence | Growth/ops |
| `PARTNER_ATTRIBUTION_ENABLED` | `false` | S3-STAGE-08 attribution/idempotency evidence | Backend/growth |
| `PARTNER_STOREFRONTS_ENABLED` | `false` | S3-STAGE-09 contract plus S3-STAGE-15 rehearsal | Product/ops |
| `PARTNER_REPORTING_ENABLED` | `false` | S3-STAGE-10 reconciliation and report freshness evidence | Analytics |
| `PARTNER_SETTLEMENT_SANDBOX_ENABLED` | `false` | S3-STAGE-11 synthetic settlement evidence | Finance |
| `PARTNER_PAYOUTS_ENABLED` | `false` | S3-STAGE-11/14/15/17 maker-checker, legal, staging and pilot evidence | Finance/owner |
| `PARTNER_EXPORTS_ENABLED` | `false` | S3-STAGE-10/14 redaction, access and audit evidence | Analytics/security |
| `PARTNER_WEBHOOKS_ENABLED` | `false` | S3-STAGE-03/04 event proof and S3-STAGE-13 alerting | Platform |
| `PAUSE_PARTNER_EXPANSION` | `true` | Cleared only during S3-STAGE-17 owner-approved pilot | Owner |

If a code path exists before the final environment variable exists, the behavior must still be equivalent to disabled.

---

## 7. Production Push Policy For S3

Production push is allowed only in one of these modes:

1. **Documentation-only push:** S3 documents, evidence, dashboards, CI validators and runbooks. No runtime enablement.
2. **Disabled-state production push:** code is deployed, but partner runtime surfaces are hidden/blocked and kill switches are disabled.
3. **Controlled pilot push:** after `S3-STAGE-17`, limited approved partners only, with manual finance controls and active support watch.

Production push is not allowed if:

- a partner feature is publicly reachable without its gate;
- the event backbone is claimed as production-ready without broker/consumer evidence;
- payout code can execute without maker-checker and audit;
- partner portal exposes admin-only controls;
- S2 customer registration, payment, provisioning, Mini App, Bot, VPN or support runtime becomes unstable;
- rollback or pause procedure is theoretical only.

---

## 8. S3 Go/No-Go Rules

### 8.1 Go Criteria For S3 Preparation

S3 preparation can continue if:

1. `S3-STAGE-00` is approved as Option A.
2. S2 has no unresolved P0/P1 customer runtime issue.
3. Outbox open backlog is zero or explicitly explained.
4. Production partner event backbone remains disabled.
5. Production partner payouts and storefronts remain disabled.
6. All new work maps to existing `S3-STAGE-*` numbers.

### 8.2 Go Criteria For Production Disabled-State Deploy

`S3-STAGE-16` can proceed only if:

1. `S3-STAGE-01` through `S3-STAGE-15` are complete or explicitly accepted by owner.
2. Partner runtime defaults are disabled.
3. CI, security, migration, route and bundle/env scans pass.
4. Rollback and kill switches are tested.
5. S2 public customer runtime remains healthy.

### 8.3 Go Criteria For Controlled Partner Pilot

`S3-STAGE-17` can proceed only if:

1. S3 staging rehearsal passed end-to-end.
2. Partner pilot roster is explicit and limited.
3. Support/on-call owner and finance owner are named.
4. Payouts are manual or sandboxed unless finance gates explicitly approve limited payout execution.
5. Observability and alert delivery are proven.
6. Owner signs off on residual risk.

### 8.4 No-Go Criteria

S3 must not proceed to production partner runtime if any of these remain unresolved:

1. event delivery has no real broker/consumer proof;
2. outbox dispatcher idempotency is unproven;
3. partner RBAC has privilege escalation gaps;
4. partner application/review states are ambiguous;
5. attribution can assign more than one cash owner per order;
6. reseller/storefront route and pricing policy are not frozen;
7. settlement sandbox cannot reconcile to source data;
8. payout approval/audit/rollback is missing;
9. partner legal/support copy is missing or misleading;
10. S3 dashboards and alerts are not active;
11. S2 customer runtime is unstable;
12. high/critical security issue is open.

---

## 9. Change Control

After this freeze:

1. no top-level S3 stage numbers may be added or renamed;
2. new work must be inserted into the closest existing `S3-STAGE-*`;
3. every runtime pull request, commit, release note and evidence file must reference the relevant `S3-STAGE-*`;
4. production partner runtime defaults to disabled until the stage gate says otherwise;
5. any payment, payout, settlement, attribution, auth, DB migration or event-backbone change requires component and feature evidence;
6. broad partner activation requires owner approval after `S3-STAGE-17`;
7. unfinished work must remain visible as blockers, not as implicit technical debt.

---

## 10. Authoritative References

- `docs/plans/2026-05-23-cybervpn-s3-stage-roadmap-ru.md`
- `docs/plans/2026-05-23-cybervpn-s3-stage00-partner-event-backbone-readiness-decision.md`
- `docs/evidence/releases/s3-stage-00-readiness-decision-20260524.md`
- `docs/plans/2026-04-17-partner-platform-rulebook.md`
- `docs/plans/2026-04-17-partner-platform-target-state-architecture.md`
- `docs/plans/2026-04-18-partner-portal-prd.md`
- `docs/plans/2026-04-18-partner-portal-role-matrix.md`
- `docs/plans/2026-05-10-cybervpn-stage3-partner-reseller-platform-plan.md`

---

## 11. Next Stage

After this freeze, proceed to:

```text
S3-STAGE-02: Partner Domain Model And Role Contract
```

`S3-STAGE-02` must freeze the partner account/workspace/user/role/status model before any production partner UI or finance runtime is opened.
