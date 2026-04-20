# CyberVPN Partner Final Integration Implementation Decomposition

**Date:** 2026-04-20  
**Status:** Implementation decomposition  
**Purpose:** translate the final integration and closure package into concrete workboards and execution order for backend, partner frontend, admin portal, and QA.

---

## 1. Document Role

This document is the direct execution bridge after the final integration package.

It does not redefine product scope.

It converts the final closure specs into a practical delivery board for implementation.

It must be read after:

- `2026-04-20-partner-realm-session-auth-access-verification-spec.md`
- `2026-04-20-partner-portal-backend-integration-closure-spec.md`
- `2026-04-20-partner-application-onboarding-backend-contract-spec.md`
- `2026-04-20-admin-partner-operations-integration-spec.md`
- `2026-04-20-partner-admin-openapi-dto-contract-freeze-spec.md`
- `2026-04-20-partner-notification-inbox-case-event-spec.md`
- `2026-04-20-partner-admin-e2e-conformance-test-plan.md`

---

## 2. Execution Principles

1. Close auth and bootstrap truth before deeper page integration.
2. Remove local/scaffold truth in the same sequence as backend contracts become available.
3. Keep partner portal, admin portal, and backend work aligned per domain, not per screen only.
4. Every workboard must produce testable contract closure, not just UI progress.
5. E2E conformance runs continuously, not only at the end.

---

## 3. Workboard Map

| Workboard | Primary Scope | Main Owners |
|---|---|---|
| `WB-INT-01` | partner realm/auth runtime | backend auth, frontend platform |
| `WB-INT-02` | partner bootstrap and route guards | backend, partner frontend |
| `WB-INT-03` | application and onboarding | backend partner domain, partner frontend, admin |
| `WB-INT-04` | workspace core | backend partner domain, partner frontend |
| `WB-INT-05` | commercial partner surfaces | backend growth/reporting, partner frontend |
| `WB-INT-06` | finance | backend finance, admin, partner frontend |
| `WB-INT-07` | compliance, risk, and cases | backend ops/risk, admin, partner frontend |
| `WB-INT-08` | notifications and inbox | backend events/notifications, partner frontend, admin |
| `WB-INT-09` | admin portal integration | admin frontend, backend ops |
| `WB-INT-10` | E2E conformance and readiness | QA, backend, partner frontend, admin frontend |

---

## 4. Workboard Details

## Workboard 1 — Partner Realm/Auth Runtime

Goal:

- make partner portal a proven separate runtime surface

Scope:

- host-to-realm resolver
- partner auth endpoints
- partner session cookies
- refresh/logout/reset/MFA
- wrong-host negative tests
- bootstrap auth guard

Primary outputs:

- partner host resolves to partner realm
- partner token audience is correct
- cookie namespace is isolated
- wrong-host tokens are rejected

Done when:

- auth verification spec can be executed end-to-end

---

## Workboard 2 — Partner Bootstrap + Route Guards

Goal:

- make bootstrap payload the primary source of truth for the shell

Scope:

- `/api/v1/partner-session/bootstrap`
- sidebar visibility
- route guard model
- blocked reasons
- counters
- pending tasks
- remove production simulation

Primary outputs:

- dashboard, sidebar, and guards all bind to the same bootstrap contract
- production runtime has no scenario simulator

Done when:

- partner shell works without local scenario truth

---

## Workboard 3 — Application / Onboarding

Goal:

- replace local application foundation with canonical backend workflow

Scope:

- draft API
- submit/resubmit/withdraw
- review requests
- attachments
- lane applications
- admin review queue sync

Primary outputs:

- `/application` is backend-owned
- review loop is shared across partner and admin surfaces

Done when:

- applicant state survives reload, device change, and admin actions without local-only truth

---

## Workboard 4 — Workspace Core

Goal:

- canonicalize the non-commercial workspace core

Scope:

- organization profile
- team, members, invitations
- roles and permissions
- legal document sets
- policy acceptance
- settings and preferences

Primary outputs:

- organization, team, legal, and settings stop depending on local scaffold state

Done when:

- all workspace core pages read and mutate backend-owned contracts

---

## Workboard 5 — Commercial Partner Surfaces

Goal:

- complete live-data integration for commercial partner operations

Scope:

- programs
- codes
- campaigns
- conversions
- explainability
- analytics and export basics

Primary outputs:

- commercial sections use canonical backend read models and action rails

Done when:

- no commercial section depends on simulated operational truth

---

## Workboard 6 — Finance

Goal:

- close partner finance runtime and admin finance governance

Scope:

- statements
- payout accounts
- payout eligibility
- payout history
- finance readiness
- admin payout account review

Primary outputs:

- finance page becomes backend-owned
- partner-visible finance blockers are admin-driven and explainable

Done when:

- partner and admin finance views reconcile to backend truth

---

## Workboard 7 — Compliance / Risk / Cases

Goal:

- close the governed operational loop

Scope:

- traffic declarations
- creative approvals
- review requests
- cases
- governance state
- partner-visible restrictions

Primary outputs:

- partner-visible restrictions, review loops, and compliance tasks are event-driven and auditable

Done when:

- compliance and cases no longer rely on local placeholders or ad hoc state

---

## Workboard 8 — Notifications / Inbox

Goal:

- replace placeholder notifications with canonical communication layer

Scope:

- notification events
- read/archive state
- counters
- routing
- admin-created partner messages

Primary outputs:

- `/notifications` becomes backend-owned
- counters, unread state, and routing reconcile across surfaces

Done when:

- notification feed is generated by backend events and not by local portal state

---

## Workboard 9 — Admin Portal Integration

Goal:

- give internal teams the operational surface needed to manage the entire partner lifecycle

Scope:

- application queue
- workspace detail
- lane membership management
- code governance
- traffic and creative review
- payout maker-checker
- governance actions
- audit log

Primary outputs:

- admin portal can operate partner lifecycle without direct SQL

Done when:

- all major admin actions have partner-visible effects and audit records

---

## Workboard 10 — E2E Conformance

Goal:

- prove the integrated system works end-to-end

Scope:

- lifecycle happy path
- negative auth tests
- permission tests
- admin-to-partner sync tests
- evidence archive
- production-readiness gates

Primary outputs:

- executable conformance suite
- evidence artifacts per scenario id

Done when:

- final E2E plan scenarios are green in the target environments

---

## 5. Recommended Execution Order

Recommended order:

1. `WB-INT-01`
2. `WB-INT-02`
3. `WB-INT-03`
4. `WB-INT-04`
5. `WB-INT-09` in parallel with `WB-INT-03` and `WB-INT-04` where backend contracts are ready
6. `WB-INT-05`
7. `WB-INT-06`
8. `WB-INT-07`
9. `WB-INT-08`
10. `WB-INT-10` throughout, with final closure at the end

---

## 6. First Implementation Slice

The correct first implementation slice is:

### Slice `FIC-1`

- `WB-INT-01` Partner Realm/Auth Runtime
- `WB-INT-02` Partner Bootstrap + Route Guards
- contract freeze alignment for bootstrap DTOs
- initial negative auth tests

Reason:

Without this slice, every later page integration risks binding to the wrong runtime assumptions.

---

## 7. Closure Conditions

This decomposition is acceptable only when:

1. every workboard maps to at least one final integration spec;
2. auth and bootstrap work are first;
3. local/scaffold elimination is explicitly sequenced;
4. admin portal integration is treated as first-class work, not a later cleanup;
5. E2E conformance is part of implementation, not postponed after coding.
