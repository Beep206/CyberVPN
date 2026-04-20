# CyberVPN Partner Portal Backend Integration Closure Spec

**Date:** 2026-04-20  
**Status:** Integration closure specification  
**Purpose:** define how every partner portal section moves from local, scaffold, or hybrid state to backend-owned canonical runtime truth.

---

## 1. Document Role

This is the primary closure document for the partner portal.

It closes the gap between:

- backend source of truth
- partner portal frontend
- admin portal actions
- local scaffold state
- runtime route guards and sidebar visibility
- production-readiness expectations

It translates the current frontend assessment into an actionable integration closure plan.

It must be read with:

- `2026-04-19-partner-frontend-implementation-and-pre-backend-integration-assessment.md`
- `2026-04-20-partner-realm-session-auth-access-verification-spec.md`
- `2026-04-20-partner-application-onboarding-backend-contract-spec.md`
- `2026-04-20-partner-admin-openapi-dto-contract-freeze-spec.md`
- `2026-04-20-partner-notification-inbox-case-event-spec.md`

---

## 2. Closure Principles

1. Backend-owned canonical data must replace local state wherever a durable business truth exists.
2. Local state is allowed only as cache, autosave buffer, optimistic UI, or dev-only simulation.
3. Dashboard, sidebar, route guards, and visibility policy must share one backend bootstrap truth.
4. Application, organization, team, legal, settings, and notifications are not allowed to remain portal-local domains.
5. Production runtime must not expose simulation controls.

---

## 3. Page-By-Page Integration Table

| Portal Section | Current State | Backend Source Of Truth | API / DTO Family | Write Actions | Local State Allowed? | Done Condition |
|---|---|---|---|---|---|---|
| `/dashboard` | hybrid runtime plus simulation controls | portal bootstrap summary + workspace runtime summary | `partnerSessionBootstrap`, `workspaceSummary`, `pendingTaskSummary`, `notificationCounterSummary` | no primary writes | dev-only simulation only | dashboard cards, sidebar, guards, and counters all come from bootstrap payload; no production scenario selector |
| `/application` | local foundation draft | workspace application lifecycle | `applicationDraft`, `applicationSubmission`, `reviewRequest`, `applicationAttachment` | save draft, upload evidence, submit, resubmit, withdraw | autosave cache only | application state survives reload and device change; submission and review state are backend-owned |
| `/organization` | local starter profile | workspace organization profile | `workspaceOrganizationProfile` | update organization profile, add domains/links, save contacts | temporary form buffer only | organization data is read from and persisted to backend profile contract |
| `/team` | mostly local portal state | workspace membership and invitation domain | `workspaceMember`, `workspaceInvitation`, `workspaceRoleAssignment` | invite, add member, disable member, change role | no durable local truth | team page reflects canonical membership list and role permissions |
| `/programs` | largely canonical-ready | workspace programs and lane memberships | `workspaceProgramsSnapshot`, `laneMembershipSummary` | apply for lane, acknowledge restrictions | no durable local truth | lane memberships, probation state, and restrictions are fully backend-backed |
| `/legal` | local legal document model | legal document sets + policy acceptance history | `legalDocumentSet`, `policyAcceptanceRecord`, `requiredAcceptanceTask` | accept policy, acknowledge version update | no durable local truth | legal surface shows required, accepted, and superseded policy versions from backend |
| `/codes` | close to canonical | workspace codes domain | `workspaceCode`, `codeActionAvailability` | create/request code, pause, request approval if allowed | optimistic mutation only | code inventory and status reasons come from canonical code resources |
| `/campaigns` | partner UI exists, backend read-model still needs freeze | campaign catalog + creative approval overlays | `campaignAsset`, `campaignEligibility`, `creativeApprovalRecord` | submit creative approval, request campaign access | UI cache only | campaign availability and approval status come from backend read model |
| `/conversions` | close to canonical | conversion records and explainability | `conversionRecord`, `conversionExplainability` | no primary writes | query cache only | conversion list and explainability are fully backend-backed |
| `/analytics` | close to canonical | analytics metrics and export inventory | `analyticsMetric`, `reportExport`, `scheduledExportRequest` | schedule export | optimistic mutation only | analytics cards, reports, and export statuses are backend-backed |
| `/finance` | hybrid but strong | statements, payout accounts, payout readiness, payout history | `financeStatement`, `payoutAccount`, `payoutEligibility`, `payoutExecutionSummary` | create payout account, set default, submit finance details | form buffer only | finance page no longer derives truth from local readiness; statements and payout readiness are backend-owned |
| `/compliance` | close to canonical | traffic declarations, creative approvals, compliance tasks | `trafficDeclaration`, `creativeApprovalRecord`, `complianceTask` | submit declaration, submit creative approval, upload evidence | optimistic mutation only | compliance state, requests, and approvals are backend-backed |
| `/integrations` | close to canonical | integration credentials, delivery logs, postback readiness | `integrationCredential`, `deliveryLog`, `postbackReadiness` | rotate credential, test delivery, acknowledge failures where allowed | no durable local truth | integrations page reflects canonical credentials/logs/readiness |
| `/cases` | close to canonical | cases, review requests, thread events | `partnerCase`, `reviewRequest`, `threadEvent` | reply, mark ready for ops, upload evidence | optimistic reply buffer only | cases and review threads are backend event driven |
| `/notifications` | local placeholder | notification feed and read-state domain | `partnerNotification`, `notificationReadState`, `notificationCounterSummary` | mark read, archive, update preferences | no durable local truth | notifications feed is event-driven and linked to cases/review/application events |
| `/settings` | local foundation | partner operator settings + workspace preferences | `partnerOperatorSettings`, `workspacePreferenceSet`, `securityStatusSummary` | update preferences, notification settings, security options | temporary form buffer only | settings persist through canonical backend contracts; placeholder profile API removed from critical path |
| `/reseller` | hybrid and gated | reseller console read model | `resellerConsoleSummary`, `storefrontScopeSummary`, `supportOwnershipSummary` | request storefront activation, update technical contact, acknowledge restrictions | UI cache only | reseller surface is backend-backed and lane-gated |

---

## 4. Local State Elimination Plan

## 4.1 State Categories

| Category | Allowed? | Examples |
|---|---|---|
| Durable business truth in local storage | forbidden | application status, team members, legal acceptance |
| Autosave cache | allowed | in-progress application form fields before server save completes |
| Optimistic UI | allowed | mark-read, schedule export, case reply pending confirmation |
| Query cache | allowed | TanStack Query response cache |
| Dev-only scenario simulation | allowed outside production | dashboard scenario selector |

## 4.2 What Must Be Eliminated

The following local truth must be removed from production runtime:

- application lifecycle as local-only draft truth
- organization profile as local-only truth
- team members as local-only truth
- legal document acceptance state as local-only truth
- notification feed as local-only truth
- settings/profile persistence as local-only truth
- production dashboard scenario simulation

## 4.3 What May Remain As Local Cache

Allowed after closure:

- unsaved form buffer for application steps
- temporary buffer for organization/profile edit forms
- text draft for case replies
- optimistic read-state toggle for notifications
- optimistic scheduling or submission affordances

## 4.4 Where Local Draft Is Allowed

Allowed:

- application autosave cache before a successful backend draft write
- organization edit buffer while request is in flight
- settings form buffer while request is in flight

Not allowed:

- application status
- review decisions
- team roster
- legal acceptance history
- payout readiness
- notification counters
- workspace permissions

---

## 5. Simulation Controls Policy

## 5.1 Production Rule

The dashboard scenario selector and workspace-role simulation controls must not be available in production runtime.

## 5.2 Allowed Simulation Modes

Simulation is allowed only when all conditions are true:

- non-production environment
- explicit feature flag enabled
- no canonical workspace bootstrap is active for the session or a dedicated dev override is present

## 5.3 Required Implementation Rule

The simulation layer must be guarded by a dedicated environment flag such as:

- `NEXT_PUBLIC_PARTNER_PORTAL_SIMULATION_ENABLED=false` in production

The production build must render:

- no scenario selector
- no role simulator
- no release-ring override selector unless explicitly required for internal testing and access-restricted

---

## 6. Runtime Bootstrap Contract

The backend must expose one canonical bootstrap payload for partner portal initialization.

## 6.1 Required Bootstrap Fields

The payload must include:

- `principal`
- `realm`
- `session`
- `active_workspace`
- `workspace_membership`
- `permission_keys`
- `workspace_status`
- `lane_memberships`
- `readiness_overlays`
- `release_ring`
- `blocked_reasons`
- `notification_counters`
- `pending_tasks`
- `finance_readiness`
- `compliance_readiness`
- `technical_readiness`
- `governance_state`

## 6.2 Consumer Surfaces Of The Bootstrap Payload

The bootstrap payload is the source of truth for:

- sidebar visibility
- route guards
- dashboard summary cards
- primary call-to-action routing
- top-level counters
- status chips
- initial page redirection logic

## 6.3 Explicit Non-Goals

The bootstrap payload does not need to contain:

- full analytics datasets
- full statements list
- full notifications feed
- full case threads

Those remain page-level query families.

---

## 7. Integration Waves

## Wave 1. Auth And Bootstrap Truth

Close first:

- realm and session verification
- partner bootstrap payload
- sidebar and guard binding to bootstrap truth

## Wave 2. Applicant And Workspace Core

Close next:

- application workflow
- organization
- team
- legal
- settings
- notifications feed

## Wave 3. Deepen Operational Surfaces

Then deepen:

- finance write flows
- integrations write flows
- reseller read model
- campaign catalog read model

---

## 8. Closure Acceptance Criteria

This document is complete only when:

1. every portal route has an identified backend source of truth;
2. local scaffold dependencies are explicitly classified as remove, cache-only, or dev-only;
3. the runtime bootstrap payload is frozen;
4. simulation controls policy is fixed;
5. production no longer depends on portal-local durable state.
