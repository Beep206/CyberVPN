# CyberVPN Partner Application And Onboarding Backend Contract Spec

**Date:** 2026-04-20  
**Status:** Integration closure specification  
**Purpose:** define the canonical backend contract for self-serve partner application, review, evidence exchange, lane requests, and promotion from application to workspace activation.

---

## 1. Document Role

This document closes the main product seam between:

- staged onboarding UI already built in the partner portal
- governed backend application lifecycle
- admin review workflow
- lane-specific approval logic

It defines one shared state machine for:

- applicant-facing `/application`
- admin review and approval tooling
- workspace status transitions
- lane membership approvals

---

## 2. Design Principles

1. Application may be self-serve; activation is governed.
2. Application state must be backend-owned.
3. Workspace status and lane status remain separate.
4. Review comments, requested info, evidence, and decisions must be auditable.
5. One workspace may carry multiple lane applications.
6. Waitlist remains a canonical workspace status in this contract.

---

## 3. Core Entities

| Entity | Purpose |
|---|---|
| `partner_application_draft` | mutable applicant draft before formal submission |
| `partner_workspace_application` | submitted workspace-level application record |
| `partner_lane_application` | per-lane request and evaluation record |
| `partner_review_request` | structured reviewer request for missing information |
| `partner_application_attachment` | evidence or requested document upload |
| `partner_review_decision` | explicit decision and reason record |
| `partner_application_event` | append-only audit/event trail |

---

## 4. Lifecycle Model

## 4.1 Workspace-Level Statuses

Canonical statuses:

- `draft`
- `email_verified`
- `submitted`
- `needs_info`
- `under_review`
- `waitlisted`
- `approved_probation`
- `active`
- `restricted`
- `suspended`
- `rejected`
- `terminated`

These statuses represent the pre-activation and operational workspace lifecycle as exposed to the partner portal.

Implementation note:

- the portal may expose this unified lifecycle model;
- backend persistence may still store `application_status` and `workspace_status` separately if that produces a cleaner internal state model;
- any split persistence model must map deterministically back into the canonical portal status contract above.

## 4.2 Lane-Level Statuses

Canonical lane statuses:

- `not_applied`
- `pending`
- `approved_probation`
- `approved_active`
- `declined`
- `paused`
- `suspended`
- `terminated`

## 4.3 Required Transition Rules

| From | To | Trigger |
|---|---|---|
| `draft` | `email_verified` | partner identity verifies email |
| `email_verified` | `submitted` | applicant submits application |
| `submitted` | `under_review` | review intake accepted |
| `submitted` | `needs_info` | pre-screen or reviewer requests data |
| `needs_info` | `under_review` | applicant responds and review restarts |
| `under_review` | `waitlisted` | reviewer defers activation |
| `under_review` | `rejected` | reviewer declines application |
| `under_review` | `approved_probation` | reviewer approves workspace for probation |
| `approved_probation` | `active` | readiness and approval conditions satisfied |
| `active` | `restricted` | governance or readiness limitation applied |
| `active` or `restricted` | `suspended` | severe governance or risk action |
| `restricted` or `suspended` | `active` | remediation approved |
| any non-terminal | `terminated` | partner relationship ended |

---

## 5. Draft API Contract

## 5.1 Required Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/v1/partner-application-drafts/current` | `GET` | read current applicant draft |
| `/api/v1/partner-application-drafts` | `POST` | create initial draft and workspace shell |
| `/api/v1/partner-application-drafts/{draft_id}` | `PATCH` | update draft fields |
| `/api/v1/partner-application-drafts/{draft_id}/attachments` | `POST` | upload evidence or requested docs |
| `/api/v1/partner-application-drafts/{draft_id}/submit` | `POST` | submit application |
| `/api/v1/partner-application-drafts/{draft_id}/withdraw` | `POST` | withdraw before review completion |
| `/api/v1/partner-application-drafts/{draft_id}/resubmit` | `POST` | resubmit after `needs_info` |

## 5.2 Draft Update Rules

Draft update must support:

- partial updates
- staged save
- lane-specific modules
- compliance declarations
- evidence uploads
- autosave-safe idempotent patching

Frontend local autosave may exist, but a server draft record is the durable source of truth.

---

## 6. Review Loop Contract

## 6.1 Reviewer Actions

Required reviewer actions:

- request more info
- accept applicant response
- add reviewer note
- approve to probation
- reject
- waitlist
- reopen review

## 6.2 Applicant Actions

Required applicant actions:

- view status
- view requested items
- upload requested evidence
- respond to review request
- resubmit after `needs_info`

## 6.3 Review Request Model

Each review request must include:

- `id`
- `workspace_application_id`
- `lane_application_id` if lane-specific
- `request_kind`
- `message`
- `required_fields`
- `required_attachments`
- `status`
- `requested_by_admin_user_id`
- `requested_at`
- `response_due_at` if policy requires

## 6.4 Review Decision Model

Each decision must include:

- decision kind
- workspace decision or lane decision scope
- reason code
- reason summary
- reviewer actor
- timestamp
- linked evidence if applicable

---

## 7. Lane Application Contract

## 7.1 Lane Families

Supported lanes:

- `creator_affiliate`
- `performance_media`
- `reseller_api`

## 7.2 Lane-Specific Required Data

### Creator / Affiliate

Required at minimum:

- owned channels
- traffic or audience profile
- public links
- promotion plan
- disclosure acceptance

### Performance / Media Buyer

Required at minimum:

- traffic source declaration
- geo plan
- funnel model
- sub_id and click_id capability
- postback readiness
- anti-fraud controls

### Reseller / API / Distribution

Required at minimum:

- legal entity details
- support ownership
- technical contact
- storefront or API mode
- domain/storefront plan

## 7.3 Lane Review Levels

| Lane | Review Level |
|---|---|
| `creator_affiliate` | pre-screen + manual-lite |
| `performance_media` | mandatory manual review |
| `reseller_api` | mandatory manual review plus operational checks |

## 7.4 Lane Application Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/v1/partner-workspaces/{workspace_id}/lane-applications` | `GET` | list lane applications |
| `/api/v1/partner-workspaces/{workspace_id}/lane-applications` | `POST` | submit additional lane request |
| `/api/v1/partner-workspaces/{workspace_id}/lane-applications/{lane_application_id}` | `PATCH` | update lane-specific draft fields while open |
| `/api/v1/partner-workspaces/{workspace_id}/lane-applications/{lane_application_id}/submit` | `POST` | submit lane application |

---

## 8. Admin Integration Contract

Admin portal must be able to read:

- submitted applications
- applicant profile
- lane requests
- attachments
- reviewer notes
- risk signals
- current status and readiness blockers

Admin portal must be able to act:

- request more info
- approve to probation
- waitlist
- reject
- approve lane
- decline lane
- reopen review

No admin action should require direct SQL.

---

## 9. Attachment And Evidence Rules

Attachments must support:

- uploaded by applicant
- requested by reviewer
- linked to workspace application or lane application
- MIME and size constraints
- audit trail
- review visibility

Required attachment categories:

- business identity
- channel evidence
- compliance evidence
- traffic evidence
- technical readiness evidence
- payout/finance evidence where needed later in lifecycle

---

## 10. Bootstrap Relationship To Workspace Runtime

Once the application is approved to probation:

- a real partner workspace becomes available through the partner portal bootstrap payload;
- `workspace_status = approved_probation`;
- lane memberships become visible through the canonical programs surface;
- review requests and cases become normal portal runtime resources.

The application system must not fork into a separate frontend truth after probation begins.

---

## 11. Closure Conditions

This contract is complete only when:

1. `/application` can be implemented without local-only status logic;
2. admin review queue and partner application UI use the same state machine;
3. review requests, responses, and attachments are fully auditable;
4. workspace-level and lane-level statuses remain separate;
5. `waitlisted` is treated as canonical and not as an undefined side label.
