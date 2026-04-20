# CyberVPN Partner Portal Traceability Matrix

**Date:** 2026-04-18  
**Status:** Traceability matrix  
**Purpose:** connect each canonical portal section to its source documents, state rules, roles, lanes, backend domains, owner workstreams, target phase, and release ring.

---

## 1. Document Role

This document is the bridge between the portal product package and execution decomposition.

It exists so frontend, backend, partner ops, finance, support, and QA can answer the same questions consistently:

- which source documents define this section?
- which roles, statuses, and lanes must it honor?
- which backend domains or API families does it depend on?
- which workstream owns delivery?
- which phase and release ring should deliver it?

---

## 2. Phase And Ring Legend

### 2.1 Portal Phase Targets

- `PP0` = app bootstrap and canonical route skeleton
- `PP1` = auth, workspace creation, and staged application
- `PP2` = review, status-aware navigation, applicant messaging
- `PP3` = core workspace operations and legal foundations
- `PP4` = codes, campaigns, compliance, and partner enablement
- `PP5` = analytics, finance, and case operations
- `PP6` = conversions, integrations, and reseller advanced surfaces
- `PP7` = hardening, QA, and release readiness

### 2.2 Release Rings

- `R0` = internal scaffold only
- `R1` = applicant and probation-safe release
- `R2` = active Creator / Affiliate launch
- `R3` = controlled Performance rollout
- `R4` = controlled Reseller / API rollout

---

## 3. Section Traceability

| Portal Section | Source docs | Required statuses | Required roles | Required lanes | Backend domains / APIs | Owner workstream | Phase target | Release ring |
|---|---|---|---|---|---|---|---|---|
| Home | PRD, IA, Status Matrix | `draft`, `email_verified`, `submitted`, `needs_info`, `under_review`, `waitlisted`, `approved_probation`, `active`, `restricted`, `suspended`, `rejected`, `terminated` | all | all | partner workspace, notifications, status summary, KPI summary | Portal FE, Partner Ops | `PP0`, `PP2` | `R0 -> R1` |
| Application / Onboarding | PRD, Onboarding Workflow, Review Policy, IA | `draft`, `email_verified`, `submitted`, `needs_info`, `under_review`, `waitlisted`, `approved_probation` | `workspace_owner`, `traffic_manager`, `finance_manager`, `support_manager`, `legal_compliance_manager` | Creator, Performance, Reseller | auth, partner application, applicant uploads, reviewer comments | Portal FE, Identity, Partner Ops | `PP1`, `PP2` | `R1` |
| Organization | PRD, IA, Role Matrix | `draft` through `restricted` | `workspace_owner`, `workspace_admin`, `finance_manager`, `traffic_manager`, `technical_manager`, `legal_compliance_manager` | all | workspace profile, domains, countries, contacts | Portal FE, Partner Domain | `PP1`, `PP3` | `R1 -> R2` |
| Team & Access | PRD, IA, Role Matrix, Surface Policy | `approved_probation`, `active`, `restricted` | `workspace_owner`, `workspace_admin` | all | membership, roles, MFA posture, sessions | Portal FE, Identity | `PP3` | `R2` |
| Programs | PRD, IA, Lane Matrix, Status Matrix | `submitted`, `needs_info`, `under_review`, `waitlisted`, `approved_probation`, `active`, `restricted` | `workspace_owner`, `workspace_admin`, `analyst`, `traffic_manager` | all | lane membership, lane status, program eligibility | Portal FE, Partner Domain, Partner Ops | `PP3` | `R1 -> R2` |
| Contracts & Legal | PRD, IA, Role Matrix, Surface Policy | `draft` through `terminated` | `workspace_owner`, `finance_manager`, `legal_compliance_manager` | all | legal documents, policy history, acknowledgements | Portal FE, Legal / Compliance | `PP3` | `R1 -> R2` |
| Codes & Tracking | PRD, IA, Lane Matrix, Surface Policy | `approved_probation`, `active`, `restricted` | `workspace_owner`, `workspace_admin`, `traffic_manager`, `analyst` | Creator, Performance, Reseller | partner codes, deep links, attribution, tracking utilities | Portal FE, Growth Backend | `PP4` | `R1 -> R3` |
| Campaigns / Assets / Enablement | PRD, IA, Lane Matrix, Surface Policy | `approved_probation`, `active`, `restricted` | `workspace_owner`, `workspace_admin`, `traffic_manager`, `analyst`, `support_manager` | Creator, Performance, Reseller | creative library, asset delivery, campaign eligibility, approvals | Portal FE, Growth Backend, Partner Ops | `PP4` | `R1 -> R3` |
| Conversions / Orders / Customers | PRD, IA, Lane Matrix, Analytics Spec | `approved_probation`, `active`, `restricted` | `analyst`, `support_manager`, `finance_manager`, `workspace_owner` | Creator, Performance, Reseller | attribution events, orders, commissionability, customer row scope | Portal FE, Commerce, Analytics | `PP6` | `R2 -> R4` |
| Analytics & Exports | PRD, IA, Analytics Spec, Status Matrix | `approved_probation`, `active`, `restricted`, `terminated` | `workspace_owner`, `finance_manager`, `analyst`, `traffic_manager` | all | reporting, exports, explainability, definitions | Portal FE, Analytics, Data Platform | `PP5` | `R1 -> R4` |
| Finance | PRD, IA, Status Matrix, Surface Policy | `approved_probation`, `active`, `restricted`, `terminated` plus finance readiness overlays | `workspace_owner`, `finance_manager`, `support_manager` | all | statements, payout readiness, payout accounts, reserves visibility | Portal FE, Finance Domain | `PP5` | `R1 -> R4` |
| Traffic & Compliance | PRD, IA, Review Policy, Status Matrix | `submitted`, `needs_info`, `under_review`, `approved_probation`, `active`, `restricted`, `suspended` | `workspace_owner`, `traffic_manager`, `legal_compliance_manager`, `support_manager` | Creator, Performance, Reseller | declarations, evidence uploads, governance visibility, policy tasks | Portal FE, Risk / Compliance | `PP4`, `PP5` | `R1 -> R3` |
| Integrations | PRD, IA, Lane Matrix, Surface Policy | `active`, `restricted` plus technical readiness overlays | `workspace_owner`, `workspace_admin`, `traffic_manager`, `technical_manager` | Performance, Reseller, selected Creator use cases | API tokens, webhooks, postbacks, delivery logs | Portal FE, Integration Platform | `PP6` | `R3 -> R4` |
| Support & Cases | PRD, IA, Status Matrix | `draft` through `terminated` | `workspace_owner`, `finance_manager`, `support_manager`, `traffic_manager`, `legal_compliance_manager` | all | cases, applicant messaging, dispute threads, attachments | Portal FE, Support Platform, Partner Ops | `PP2`, `PP5` | `R1 -> R4` |
| Notifications / Inbox | PRD, IA, Onboarding Workflow, Status Matrix | all workspace statuses | all | all | notifications, inbox events, task reminders | Portal FE, Notifications Platform | `PP0`, `PP2` | `R0 -> R4` |
| Settings & Security | PRD, IA, Role Matrix | all non-deleted user scopes | all with self-scope | all | password, passkeys, MFA, sessions, notification preferences | Portal FE, Identity | `PP1`, `PP3` | `R1 -> R4` |
| Reseller Console | PRD, IA, Lane Matrix, Surface Policy | reseller lane `approved_active` with workspace `active` or `restricted` | `workspace_owner`, `workspace_admin`, `technical_manager`, `support_manager`, `finance_manager` | Reseller only | storefront scope, domains, pricebooks, support ownership, API integration | Portal FE, Reseller Backend, Commerce | `PP6` | `R4` |

---

## 4. Execution Use

This matrix should be used to:

- derive workboards by owner workstream
- validate that a module is not opened in the wrong release ring
- stop frontend slices from shipping without the status and role rules they depend on
- stop backend slices from exposing APIs without a declared portal consumer
