# CyberVPN Partner Portal Phase And Workboard Decomposition

**Date:** 2026-04-18  
**Status:** Decomposition plan  
**Purpose:** translate the partner portal product package into execution phases, workboards, and the first implementation slice for the separate `partner` application.

---

## 1. Document Role

This document is the execution bridge for the portal surface.

It sits on top of:

- `2026-04-18-partner-portal-prd.md`
- `2026-04-18-partner-portal-ia-and-menu-map.md`
- `2026-04-18-partner-portal-status-and-visibility-matrix.md`
- `2026-04-18-partner-portal-role-matrix.md`
- `2026-04-18-partner-portal-lane-capability-matrix.md`
- `2026-04-18-partner-portal-onboarding-workflow-spec.md`
- `2026-04-18-partner-portal-application-review-and-approval-policy.md`
- `2026-04-18-partner-portal-surface-policy-matrix.md`
- `2026-04-18-partner-app-bootstrap-plan.md`
- `2026-04-18-partner-portal-traceability-matrix.md`

It does not replace the broader backend platform phase documents from 2026-04-17 and 2026-04-18.

---

## 2. Decomposition Principles

1. The portal ships as a separate `partner` app, not as an extension of `frontend` or `admin`.
2. Canonical route families are established early, even when some sections are still placeholder or read-only.
3. Applicant-safe and probation-safe behavior must arrive before advanced active-lane features.
4. Creator / Affiliate is the first production lane, but Performance and Reseller are modeled from day one.
5. No phase may collapse workspace status, lane status, code status, and readiness overlays into one flag.

---

## 3. Portal Phases

### `PP0` App Bootstrap And Canonical Shell

Goal:

- keep the separate `partner` workspace bootable
- replace admin navigation with the canonical partner route skeleton
- establish placeholder pages and stable top-level navigation

Primary outcomes:

- canonical routes exist
- shell copy is partner-native
- route registry is not admin-shaped anymore
- initial status-aware navigation contract exists

Primary workboards:

- `WB-PORTAL-SHELL`
- `WB-PLATFORM-QA`

### `PP1` Identity, Workspace Creation, And Application Foundation

Goal:

- make the portal usable for account creation and staged application

Primary outcomes:

- login, register, verify, forgot/reset flows
- workspace creation
- application draft save
- organization starter profile
- settings and security baseline

Primary workboards:

- `WB-IDENTITY-ONBOARDING`
- `WB-PORTAL-SHELL`

### `PP2` Review, Status-Aware UX, And Applicant Messaging

Goal:

- make pending applicants understandable and operable instead of dead-ended

Primary outcomes:

- status-aware home
- requested-info and review-state UX
- applicant-safe support/contact channel
- notifications and inbox
- waitlisted and blocked-state explanations

Primary workboards:

- `WB-APPLICATION-OPS`
- `WB-NOTIFICATIONS-CASES`

### `PP3` Core Workspace Operations

Goal:

- establish the non-commercial operating core for approved and active workspaces

Primary outcomes:

- organization hardening
- team and access
- programs
- contracts and legal
- settings and security hardening

Primary workboards:

- `WB-WORKSPACE-OPS`
- `WB-LEGAL-COMPLIANCE`

### `PP4` Commercial Operations Foundation

Goal:

- enable the first real partner operating loops for Creator and probation-safe Performance

Primary outcomes:

- codes and tracking
- campaigns / assets / enablement
- traffic and compliance
- lane-aware gating

Primary workboards:

- `WB-GROWTH-OPS`
- `WB-LEGAL-COMPLIANCE`

### `PP5` Reporting, Finance, And Case Operations

Goal:

- make the portal financially and operationally useful

Primary outcomes:

- analytics and exports
- finance readiness and statements
- payout account setup
- support and dispute cases

Primary workboards:

- `WB-ANALYTICS-FINANCE`
- `WB-NOTIFICATIONS-CASES`

### `PP6` Advanced Operational Surfaces

Goal:

- add the advanced lane capabilities that depend on deeper backend maturity

Primary outcomes:

- conversions / orders / customers
- integrations
- reseller console
- performance technical controls

Primary workboards:

- `WB-INTEGRATIONS-RESELLER`
- `WB-ANALYTICS-FINANCE`

### `PP7` Hardening, QA, And Release Readiness

Goal:

- turn the built portal into a safe production surface

Primary outcomes:

- route and role tests
- status visibility regression coverage
- copy cleanup and dead-route cleanup
- release-ring gating
- rollout readiness checklist

Primary workboards:

- `WB-PLATFORM-QA`
- all workboards for closure evidence

---

## 4. Workboards

| Workboard | Scope | Primary owners | Main phases |
|---|---|---|---|
| `WB-PORTAL-SHELL` | app shell, navigation, route skeleton, page placeholders | frontend platform | `PP0`, `PP1` |
| `WB-IDENTITY-ONBOARDING` | auth, registration, verification, workspace creation, application draft | frontend, identity/backend | `PP1` |
| `WB-APPLICATION-OPS` | review-state UX, onboarding flow, requested-info loops, applicant visibility | frontend, partner ops/backend | `PP2` |
| `WB-WORKSPACE-OPS` | organization, team, programs, settings | frontend, partner domain/backend | `PP3` |
| `WB-LEGAL-COMPLIANCE` | contracts, declarations, compliance tasks, governance visibility | frontend, legal/compliance/backend | `PP3`, `PP4` |
| `WB-GROWTH-OPS` | codes, links, campaigns, assets, traffic controls | frontend, growth backend | `PP4` |
| `WB-ANALYTICS-FINANCE` | analytics, explainability, statements, payout readiness, finance history | frontend, analytics, finance backend | `PP5`, `PP6` |
| `WB-NOTIFICATIONS-CASES` | inbox, messages, applicant contact, support/dispute cases | frontend, notifications, support backend | `PP2`, `PP5` |
| `WB-INTEGRATIONS-RESELLER` | tokens, webhooks, postbacks, reseller console, storefront-linked scope | frontend, integrations/backend, commerce | `PP6` |
| `WB-PLATFORM-QA` | route guards, test coverage, release gating, rollout readiness | frontend platform, QA | `PP0`, `PP7` |

---

## 5. First Implementation Slice

The correct implementation start is not full feature depth. It is the portal shell plus route truth.

### Slice `S1` Goals

- finish the `partner` app bootstrap
- align the menu and route tree to the canonical portal IA
- remove admin-shaped section names and leftover referral-first assumptions
- make status-aware hiding possible even if backend capability is still placeholder

### Slice `S1` Expected Deliverables

- partner section registry rewritten to canonical route families
- canonical sidebar and dashboard navigation
- placeholder pages for the canonical sections
- route-level metadata and labels aligned with portal pack
- basic status-aware menu gating stub

### Slice `S1` Explicitly Out Of Scope

- full application workflow logic
- real review queue behavior
- final finance and analytics contracts
- reseller and performance deep capability
- internal ops tooling

### Slice `S1` Dependencies

- existing `partner` app workspace bootstrap
- canonical IA and status model already frozen
- no new backend contract required beyond bootable placeholder surfaces

---

## 6. Recommended Execution Order

1. Close `PP0 / S1` in the `partner` app.
2. Open `PP1` only after the shell and route skeleton are stable.
3. Open `PP2` before commercial modules so applicants do not hit dead ends.
4. Open `PP3` and `PP4` in parallel where backend contracts permit.
5. Open `PP5` after analytics and finance contract slices are stable enough for partner-facing read models.
6. Open `PP6` only for release rings that truly need advanced lane capability.
7. Use `PP7` as a hard production gate, not a soft cleanup bucket.

---

## 7. Acceptance Conditions

This decomposition is acceptable only when:

- every canonical portal section is assigned to a phase and workboard
- applicant-safe and probation-safe surfaces arrive before advanced active-only surfaces
- route truth is established before deep feature work
- Creator can launch before Performance and Reseller without corrupting the shared model
