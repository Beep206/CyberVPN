# CyberVPN Partner Portal IA And Menu Map

**Date:** 2026-04-18  
**Status:** Information architecture and menu map  
**Purpose:** define the partner portal navigation model, section hierarchy, and visibility logic for the external partner workspace surface.

---

## 1. Document Role

This document defines how the partner portal is organized for navigation and discovery.

It assumes:

- the partner portal is a separate workspace app
- portal behavior is workspace-aware, lane-aware, role-aware, and status-aware
- visibility rules are further refined in `2026-04-18-partner-portal-status-and-visibility-matrix.md`

---

## 2. IA Principles

1. The menu must reflect lifecycle, not just features.
2. Pending applicants must understand what is blocked and why.
3. Active partners must not hunt through settings to find finance, reporting, or compliance.
4. High-risk and low-frequency actions belong in dedicated modules, not hidden inside generic profile pages.
5. Lane-specific modules may appear conditionally, but the base portal structure should remain stable.

---

## 3. Top-Level Navigation Groups

### Group A. Workspace Overview

- Home
- Notifications / Inbox

### Group B. Application And Identity

- Application / Onboarding
- Organization
- Team & Access
- Programs
- Contracts & Legal

### Group C. Commercial Operations

- Codes & Tracking
- Campaigns / Assets / Enablement
- Conversions / Orders / Customers
- Analytics & Exports
- Finance
- Traffic & Compliance
- Integrations

### Group D. Operational Support

- Support & Cases
- Settings & Security
- Reseller Console

---

## 4. Canonical Menu Sections

| Section | Primary purpose | Typical users | Visibility rule |
|---|---|---|---|
| Home | status, tasks, KPIs, alerts, messages | all | always visible, but content varies by status |
| Application / Onboarding | application timeline, missing steps, requested info | applicants, owners | always visible until terminal end-state |
| Organization | business profile, domains, countries, contacts | owner, admin, finance, legal | visible after workspace creation |
| Team & Access | members, roles, sessions, MFA posture | owner, admin | hidden until workspace exists |
| Programs | lane memberships, restrictions, assigned manager | owner, analyst, traffic | visible after submission |
| Contracts & Legal | terms, policy history, accepted docs, PDFs | owner, finance, legal | visible after workspace creation |
| Codes & Tracking | codes, links, QR, link builder, sub_id macros | traffic, analyst, owner | visible from approved probation onward |
| Campaigns / Assets / Enablement | creative library, approval flow, disclosure templates | traffic, support, analyst | visible from approved probation onward |
| Conversions / Orders / Customers | attributed conversions, orders, dispute context | analyst, support, finance | visible from approved probation onward, lane-conditional |
| Analytics & Exports | dashboards, cohorts, exports, explainability | analyst, owner, finance | lite on probation, full on active |
| Finance | earnings, holds, statements, payout accounts | finance, owner | onboarding on probation, full on active |
| Traffic & Compliance | declarations, approvals, policy tasks, governance state | traffic, legal, owner | visible when lane or status requires it |
| Integrations | API tokens, postbacks, webhooks, logs | technical, traffic | hidden until active or lane-enabled |
| Support & Cases | messages, disputes, technical cases, ops communication | support, owner, finance | visible from workspace creation in limited applicant-contact mode, then expands after submission |
| Notifications / Inbox | status changes, requested info, policy updates | all | always visible |
| Settings & Security | password, passkey, MFA, sessions, notification prefs | all with own-user scope | always visible |
| Reseller Console | storefront, domain, pricebook, support ownership, customer scope | reseller roles only | reseller lane only |

---

## 5. Default Menu Map By Status Band

### 5.1 Pre-Submission

- Home
- Application / Onboarding
- Organization
- Contracts & Legal
- Support & Cases
- Settings & Security
- Notifications / Inbox

Pre-submission `Support & Cases` is intentionally limited to:

- applicant help and contact
- requested clarification handoff
- lightweight message thread with partner ops

It is not yet the full post-submission dispute and operations surface.

### 5.2 Submitted / Under Review

- Home
- Application / Onboarding
- Organization
- Programs
- Contracts & Legal
- Support & Cases
- Settings & Security
- Notifications / Inbox

### 5.3 Approved Probation

- Home
- Application / Onboarding
- Organization
- Team & Access
- Programs
- Contracts & Legal
- Codes & Tracking
- Campaigns / Assets / Enablement
- Analytics & Exports
- Finance
- Traffic & Compliance
- Support & Cases
- Settings & Security
- Notifications / Inbox

### 5.4 Active

- all core sections above
- Integrations
- Conversions / Orders / Customers
- Reseller Console when reseller lane is enabled

### 5.5 Restricted / Suspended

Remain visible:

- Home
- Application / Onboarding
- Organization
- Programs
- Contracts & Legal
- Analytics & Exports
- Finance
- Traffic & Compliance
- Support & Cases
- Settings & Security
- Notifications / Inbox

May be hidden or read-only:

- Codes & Tracking
- Campaigns / Assets / Enablement
- Integrations
- Reseller Console

---

## 6. Lane-Specific IA Overlays

### 6.1 Creator / Affiliate

Core emphasis:

- Codes & Tracking
- Campaigns / Assets / Enablement
- Analytics & Exports
- Finance
- Support & Cases

### 6.2 Performance / Media Buyer

Core emphasis:

- Codes & Tracking
- Traffic & Compliance
- Integrations
- Analytics & Exports
- Finance

### 6.3 Reseller / API / Distribution

Core emphasis:

- Programs
- Contracts & Legal
- Codes & Tracking
- Conversions / Orders / Customers
- Finance
- Integrations
- Reseller Console

---

## 7. Home Section Composition

Home is not a generic dashboard. It must always answer:

- what is my current workspace status?
- what are my lane statuses?
- what do I need to do next?
- what is blocked right now?
- what changed recently?
- what are my top-line KPIs?

Required cards:

- workspace status
- lane status summary
- pending tasks
- approvals or requested info
- payout readiness
- compliance readiness
- KPI summary
- latest alerts
- latest messages

---

## 8. Navigation Rules

1. Hidden sections must not appear as dead links.
2. Restricted sections should show clear blocked-state explanations where appropriate.
3. The menu should prefer stable section names over lane-specific jargon.
4. Reseller-only capabilities should sit under one clear console entry instead of scattering across the main menu.
5. Notifications / Inbox should be globally accessible from all states.

---

## 9. Recommended Route Skeleton

Suggested route family map:

- `/dashboard`
- `/application`
- `/organization`
- `/team`
- `/programs`
- `/legal`
- `/codes`
- `/campaigns`
- `/conversions`
- `/analytics`
- `/finance`
- `/compliance`
- `/integrations`
- `/cases`
- `/notifications`
- `/settings`
- `/reseller`

This route map is intentionally stable even when visibility changes by lane or status.
