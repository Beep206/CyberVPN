# CyberVPN Partner Portal PRD

**Date:** 2026-04-18  
**Status:** Product requirements document  
**Purpose:** define the product requirements for the external CyberVPN partner portal as the operator-facing surface for partner workspaces in the separate partner realm.

---

## 1. Document Role

This PRD defines the product layer for the partner portal.

It does not redefine:

- canonical lane rules from `2026-04-17-partner-platform-rulebook.md`
- target-state architecture from `2026-04-17-partner-platform-target-state-architecture.md`
- API family boundaries from `2026-04-17-partner-platform-api-specification-package.md`
- reporting truth definitions from `2026-04-17-analytics-and-reporting-spec.md`

This PRD translates those canonical documents into an operator-facing product surface that can be implemented by frontend, backend, partner ops, finance, risk, and support.

---

## 2. Problem And Why Now

CyberVPN already has a target-state partner platform specification package, but it does not yet have a single product document that defines the partner portal itself.

Without a portal-specific product layer:

- partner workspace requirements remain implicit inside backend and admin specs
- onboarding and approval flows risk being designed as ad hoc forms instead of a governed lifecycle
- reporting, finance, compliance, and governance features risk being shipped as disconnected modules
- partner portal implementation can collapse into a shallow affiliate cabinet instead of a real partner operating workspace

The partner portal must therefore be defined as a first-class product surface before decomposition and implementation continue.

---

## 3. Product Vision

CyberVPN Partner Portal is a state-aware, lane-aware, role-aware workspace in a separate partner realm.

It is not:

- a customer dashboard extension
- a simple referral cabinet
- a payout-only console
- an internal admin tool exposed externally

It is the external operating surface for partner operators across the full lifecycle:

1. application
2. review
3. contract and compliance onboarding
4. tracking and campaign operations
5. reporting and explainability
6. settlement and payout readiness
7. governance, remediation, and support

---

## 4. Primary Users

### 4.1 External Personas

| Persona | Description | Primary needs |
|---|---|---|
| Applicant | person or company applying to become a partner | simple application flow, transparency, status visibility |
| Workspace Owner | main accountable operator for the partner workspace | approvals, legal acceptance, team management, sensitive changes |
| Finance Manager | partner-side finance contact | statements, payout accounts, payout readiness, tax and invoice context |
| Analyst | partner-side reporting user | dashboards, exports, explainability, performance visibility |
| Traffic Manager | growth and campaign operator | codes, links, campaigns, traffic declarations, attribution diagnostics |
| Support Manager | partner-side operations and customer issue handler | cases, order visibility, dispute context, support messaging |
| Technical Manager | partner-side technical owner | API tokens, postbacks, webhooks, integration diagnostics |
| Legal / Compliance Manager | partner-side policy and legal contact | contract review, declarations, remediation, policy updates |

### 4.2 Internal Secondary Users

The portal is external-facing, but internal teams depend on its contracts and state model:

- partner ops
- finance ops
- risk and compliance
- support
- admin and internal operations

---

## 5. Product Principles

1. Unit of access is the partner workspace, not the customer account.
2. Activation is not self-serve. Application may be self-serve, approval is governed.
3. Workspace status, lane status, code status, and finance readiness remain separate concepts.
4. Portal behavior depends on role, workspace status, lane membership status, and surface policy.
5. Reporting and finance are row-level scoped on the server.
6. Consumer growth programs are excluded from partner portal semantics.
7. The portal must expose explainability, not just metrics.
8. Internal moderation, overrides, and raw governance control stay in admin surfaces.

---

## 6. Entry Scenarios

The portal must support three entry models.

### 6.1 Public Apply

Used for:

- Creator / Affiliate
- selected Reseller / API applicants
- self-serve content, SEO, community, and Telegram partners

### 6.2 Invite-Only Onboarding

Used for:

- Performance / Media Buyer
- strategic Reseller / API / Distribution partners
- partner-manager sourced opportunities

### 6.3 Existing User Upgrade Request

Used for:

- strong current users
- strong consumer referrers
- creator candidates discovered through internal growth signals

Constraint:

- this creates or links to a separate partner workspace in the partner realm
- it does not convert the customer account into the partner workspace itself

---

## 7. Goals

### 7.1 Business Goals

- create a durable external partner operating surface for all partner revenue lanes
- reduce partner-ops manual work through structured onboarding, statusing, and guided workflows
- improve partner quality by gating activation through review, probation, and compliance controls
- give finance, risk, and support explainable portal contracts instead of ad hoc tickets and spreadsheets

### 7.2 User Goals

- let partners understand their current status and next steps
- let partners manage workspace identity, team, codes, and campaigns without internal ops dependency for routine tasks
- let partners see trustworthy reporting, finance status, and compliance obligations
- let partners understand why access is blocked, limited, or changed

---

## 8. Non-Goals

The partner portal does not own:

- Invite / Gift mechanics
- Consumer Referral Credits and customer viral loops
- internal maker-checker approval queues
- global fraud search across all partner workspaces
- global reserve controls
- raw internal override tooling
- canonical system-of-record ownership for finance or risk decisions

Those remain in customer surfaces, admin surfaces, or internal operations.

---

## 9. Required Product Areas

The partner portal must cover these product areas.

1. Home
2. Application / Onboarding
3. Organization
4. Team & Access
5. Programs
6. Contracts & Legal
7. Codes & Tracking
8. Campaigns / Assets / Enablement
9. Conversions / Orders / Customers
10. Analytics & Exports
11. Finance
12. Traffic & Compliance
13. Integrations
14. Support & Cases
15. Notifications / Inbox
16. Settings & Security
17. Reseller Console

Each area is elaborated in the companion documents of this portal pack.

---

## 10. Functional Requirements

### 10.1 Workspace And Access Model

The portal must:

- operate in a separate partner realm
- issue partner-operator session tokens
- support multi-user workspaces
- enforce role-based access inside the workspace
- enforce row-level isolation for workspace data and exports

### 10.2 Status-Aware Product Behavior

The portal must adapt to:

- workspace lifecycle state
- lane membership lifecycle state
- finance readiness
- governance state
- lane-specific restrictions

### 10.3 Lane-Aware Product Behavior

The portal must support these revenue lanes:

- Creator / Affiliate
- Performance / Media Buyer
- Reseller / API / Distribution

The portal may share common modules, but capabilities must differ by lane.

### 10.4 Explainability

The portal must expose enough context for partners to understand:

- why an order was attributed or not attributed
- why earnings are on hold, reserved, adjusted, or unavailable
- why a payout account or payout execution is blocked
- why a code or lane is restricted or suspended

### 10.5 Governance And Remediation

The portal must expose partner-facing governance consequences without exposing internal control panels.

It must support:

- requested information tasks
- remediation tasks
- policy acceptance visibility
- warning visibility
- code suspension visibility
- payout freeze visibility
- appeal or request-review flows where policy allows

---

## 11. Core User Journeys

### 11.1 Applicant Journey

1. Create account in partner realm
2. Verify email and set MFA
3. Create workspace
4. Complete general profile
5. Complete lane modules
6. Complete compliance declarations
7. Submit application
8. Respond to requests for additional information
9. Receive decision and next steps

### 11.2 Approved Probation Journey

1. Accept contracts and policies
2. Complete payout and finance setup tasks
3. Receive starter code or starter capabilities
4. Launch first approved activities
5. Monitor limited reporting and readiness tasks
6. Progress to active if quality and readiness conditions pass

### 11.3 Active Partner Journey

1. Manage codes, links, campaigns, and assets
2. Review conversions, orders, and reporting
3. Track statements, holds, reserves, and payout readiness
4. Manage team, access, and integrations
5. Resolve compliance, support, and finance cases

### 11.4 Restricted Or Suspended Journey

1. See current restrictions and affected modules
2. Review governance reason and remediation steps
3. Upload evidence or complete tasks
4. Communicate with ops, finance, or risk
5. Regain access if reinstated

---

## 12. Success Metrics

The product is successful when it improves:

- application completion rate
- percentage of qualified applications entering review with complete information
- median time from application submission to decision
- median time from approval to first live code or first approved launch
- median time from approval to payout readiness
- percentage of partner questions resolved through portal status, docs, or messaging without ad hoc manual intervention
- percentage of partner reporting and finance views that reconcile to canonical operational sources
- percentage of access decisions correctly enforced by workspace, lane, role, and status

Guardrail metrics:

- unauthorized row-level data exposure must remain zero
- no partner portal action may create unauthorized payout execution or internal override behavior
- no consumer growth features may leak into partner finance surfaces

---

## 13. Release Scope Guidance

### 13.1 V1 Must-Have

- separate partner workspace app
- separate partner-realm auth
- application and onboarding area
- organization and team management
- programs overview
- codes and tracking
- analytics and explainability basics
- finance basics: statements, payout accounts, payout readiness
- traffic and compliance center
- support and cases
- settings and security

### 13.2 V1 Conditional By Backend Readiness

- full payout execution history
- advanced integrations
- reseller customer and storefront views
- performance-specific postback diagnostics

### 13.3 Later Expansion

- scheduled exports
- more advanced campaign enablement
- richer reseller operations console
- partner API developer experience layer

---

## 14. Acceptance Conditions

This PRD is acceptable only if the final portal:

- is implemented as a partner workspace in a separate partner realm
- treats application as self-serve but activation as governed
- separates workspace, lane, code, finance, and governance state
- supports org users instead of a single-user affiliate model
- exposes reporting, statements, payout accounts, and compliance obligations as first-class surfaces
- enforces server-side row-level visibility
- excludes customer referral and internal admin-only functions from the portal

