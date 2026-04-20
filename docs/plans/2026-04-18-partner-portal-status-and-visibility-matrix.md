# CyberVPN Partner Portal Status And Visibility Matrix

**Date:** 2026-04-18  
**Status:** Status and visibility specification  
**Purpose:** define the portal status model and the visibility behavior of modules across workspace, lane, code, and readiness states.

---

## 1. Document Role

This document defines how product visibility changes based on status.

It covers:

- workspace status
- lane membership status
- code status
- readiness overlays
- module visibility bands

It must be read together with:

- `2026-04-18-partner-portal-ia-and-menu-map.md`
- `2026-04-18-partner-portal-lane-capability-matrix.md`
- `2026-04-18-partner-portal-surface-policy-matrix.md`

---

## 2. Status Model Principles

1. Workspace, lane, and code status must remain separate.
2. Readiness is not the same thing as status.
3. Governance constraints may reduce capabilities without changing every underlying status object.
4. Visibility and writability must be treated separately.
5. Workspace-level activation uses `active`; `approved_active` is lane-only language.

---

## 3. Workspace Statuses

| Status | Meaning |
|---|---|
| `draft` | workspace created, application not ready for submission |
| `email_verified` | identity is verified, workspace may continue profile completion |
| `submitted` | application submitted, awaiting full review entry |
| `needs_info` | reviewer or pre-screen requested more information |
| `under_review` | application in active review |
| `waitlisted` | application is not declined, but activation is deferred pending capacity, timing, or policy fit |
| `approved_probation` | approved with limited operational access |
| `active` | workspace activated for allowed lanes and capabilities |
| `restricted` | workspace remains active in part, but some capabilities are limited |
| `suspended` | major operational capability is blocked pending resolution |
| `rejected` | application declined or later terminated before active operation |
| `terminated` | workspace ended as a partner relationship |

---

## 4. Lane Membership Statuses

| Status | Meaning |
|---|---|
| `not_applied` | lane not requested |
| `pending` | lane requested and under review |
| `approved_probation` | lane approved with limited capability |
| `approved_active` | lane fully active |
| `declined` | lane request denied |
| `paused` | lane temporarily not operating |
| `suspended` | lane blocked due to governance or risk action |
| `terminated` | lane permanently ended |

---

## 5. Code Statuses

| Status | Meaning |
|---|---|
| `draft` | code exists but not submitted or launched |
| `pending_approval` | code awaiting approval or governance review |
| `active` | code is live and usable |
| `paused` | code temporarily disabled |
| `revoked` | code withdrawn and not restorable by partner self-service |
| `expired` | code naturally ended or timed out |

---

## 6. Readiness Overlays

These are independent overlays that may gate modules without changing the base status.

### 6.1 Finance Readiness

- `not_started`
- `in_progress`
- `ready`
- `blocked`

### 6.2 Compliance Readiness

- `not_started`
- `declarations_complete`
- `evidence_requested`
- `approved`
- `blocked`

### 6.3 Technical Readiness

- `not_required`
- `in_progress`
- `ready`
- `blocked`

### 6.4 Governance State

- `clear`
- `watch`
- `warning`
- `limited`
- `frozen`

### 6.5 Workflow Outcomes That Are Not Canonical Status Objects

The following labels may appear in workflow or reviewer tooling, but they do not replace the canonical status model above:

- `ready_for_active` = readiness outcome meaning the workspace can be promoted from `approved_probation` to `active`
- `blocked_pending_finance` = readiness outcome represented by base status plus `finance_readiness = blocked`
- `blocked_pending_compliance` = readiness outcome represented by base status plus `compliance_readiness = blocked`
- `blocked_pending_technical` = readiness outcome represented by base status plus `technical_readiness = blocked`

---

## 7. Module Visibility Bands

Legend:

- `H` = hidden
- `R` = visible read-only
- `T` = visible task-driven or partial
- `L` = visible with limited operations
- `F` = full

Status bands:

- `pre_submit` = `draft`, `email_verified`
- `review` = `submitted`, `needs_info`, `under_review`, `waitlisted`
- `probation` = `approved_probation`
- `active` = `active`
- `constrained` = `restricted`, `suspended`
- `terminal` = `rejected`, `terminated`

| Module | Pre-submit | Review | Probation | Active | Constrained | Terminal |
|---|---|---|---|---|---|---|
| Home | T | T | L | F | R | R |
| Application / Onboarding | F | F | T | R | R | R |
| Organization | F | F | F | F | R | R |
| Team & Access | H | H | L | F | R | H |
| Programs | H | R | L | F | R | R |
| Contracts & Legal | R | R | F | F | R | R |
| Codes & Tracking | H | H | L | F | R | H |
| Campaigns / Assets / Enablement | H | H | L | F | R | H |
| Conversions / Orders / Customers | H | H | L | F | R | H |
| Analytics & Exports | H | H | L | F | R | H |
| Finance | H | H | T | F | R | R |
| Traffic & Compliance | H | T | L | F | R | R |
| Integrations | H | H | H | F | R | H |
| Support & Cases | T | L | L | F | F | R |
| Notifications / Inbox | F | F | F | F | F | R |
| Settings & Security | F | F | F | F | F | R |
| Reseller Console | H | H | H | lane-conditional | R | H |

---

## 8. Additional Gating Rules

### 8.1 Finance Gating

Even in `active`, Finance module behavior changes:

- `finance_readiness = in_progress` -> payout accounts editable, payout availability read-only
- `finance_readiness = blocked` -> payout actions hidden or blocked with explanation
- `ready_for_active` is satisfied only when finance gating does not block the promotion path

### 8.2 Compliance Gating

If `compliance_readiness = evidence_requested`:

- Traffic & Compliance becomes task-driven
- Campaign and code-expansion actions may be blocked
- `blocked_pending_compliance` maps to this readiness layer rather than introducing a new workspace status

### 8.3 Governance Gating

If `governance_state = limited` or `frozen`:

- new code creation may be blocked
- payout account changes may be blocked
- new creative submissions may be blocked
- traffic expansion tools may be blocked
- technical activation may remain blocked without changing the canonical workspace status object

---

## 9. Lane-Specific Visibility Rules

### 9.1 Creator / Affiliate

Expected module priority:

- Codes & Tracking
- Campaigns / Assets / Enablement
- Analytics & Exports
- Finance

### 9.2 Performance / Media Buyer

Expected module priority:

- Codes & Tracking
- Traffic & Compliance
- Integrations
- Analytics & Exports
- Finance

Performance lane may remain `approved_probation` longer than other lanes.

### 9.3 Reseller / API / Distribution

Expected module priority:

- Programs
- Conversions / Orders / Customers
- Finance
- Integrations
- Reseller Console

Reseller Console remains hidden unless reseller lane is approved.

---

## 10. Terminal State Rules

### 10.1 `rejected`

Visible:

- Home with decision explanation
- Application / Onboarding history
- Contracts / Legal read-only
- Notifications / Inbox
- Support & Cases if appeal flow is allowed
- Settings & Security

### 10.2 `terminated`

Visible:

- Home with termination state
- Contracts / Legal history
- Finance history where policy requires it
- Support & Cases
- Settings & Security read-only or reduced

Not visible:

- operational modules for codes, campaigns, and integrations

---

## 11. Acceptance Conditions

This status matrix is acceptable only when:

- workspace, lane, code, and readiness states remain separate
- every blocked module can explain why it is blocked
- restricted and suspended states preserve historical visibility where required
- the product does not confuse approval state with finance or compliance readiness
