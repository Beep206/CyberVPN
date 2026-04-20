# CyberVPN Partner Portal Onboarding Workflow Spec

**Date:** 2026-04-18  
**Status:** Workflow specification  
**Purpose:** define the staged onboarding flows for creating and activating a partner workspace in the separate partner realm.

---

## 1. Document Role

This document defines how a partner enters the portal and progresses from application to usable workspace access.

It covers:

- public apply
- invite-only onboarding
- existing-user upgrade request
- review, probation, and finance activation steps

It does not define the internal reviewer UI in detail.

---

## 2. Workflow Principles

1. Application may be self-serve; activation is governed.
2. The portal must favor staged onboarding over one giant form.
3. Approval must be separate from account creation.
4. Finance, compliance, and technical readiness may complete after approval, but before full activation where required.
5. Different lanes require different evidence and different review depth.

---

## 3. Entry Scenarios

### 3.1 Public Apply

Primary lanes:

- Creator / Affiliate
- selected Reseller / API applicants

### 3.2 Invite-Only Onboarding

Primary lanes:

- Performance / Media Buyer
- strategic Reseller / API / Distribution

### 3.3 Existing User Upgrade Request

Primary use:

- current CyberVPN customer requests partner application

Constraint:

- creates a new partner workspace in the partner realm
- does not turn the customer account into the partner workspace itself

---

## 4. Shared Workflow Stages

## Stage A. Account And Workspace Creation

Required:

- email
- password or passkey
- email verification
- MFA setup
- workspace name
- country
- initial legal acceptance for portal entry
- partner type chooser:
  - Creator / Affiliate
  - Performance / Media Buyer
  - Reseller / API / Distribution

Primary output:

- partner operator account
- `workspace_status = draft` then `email_verified`
- owner membership established

## Stage B. General Partner Profile

Required:

- business or brand name
- contact person
- business email
- website
- country and region
- languages
- company type
- business description
- target audience
- main acquisition channels
- public links
- top geos
- estimated monthly reach or volume band

Primary output:

- workspace profile completed enough for submission

## Stage C. Lane-Specific Modules

### Creator / Affiliate

Collect:

- content categories
- audience size by channel
- example content links
- owned domains
- channel mix
- mention plan
- code / landing / QR needs

### Performance / Media Buyer

Collect:

- paid traffic sources
- ad networks
- geos
- funnel model
- prelanding domains
- creative plan
- sub_id / click_id support
- postback capability
- anti-fraud controls
- monthly spend band

### Reseller / API / Distribution

Collect:

- legal entity details
- business registration country
- expected support and sales volume
- intended commercial model
- planned storefront or domains
- API-only vs storefront mode
- technical contact
- support ownership expectation
- target geos and currencies

## Stage D. Compliance Declarations

Required explicit attestations:

- material connection disclosure compliance
- no fake reviews or fake testimonials
- no misleading privacy claims
- no spam, bot traffic, or cookie stuffing
- no trademark bidding without approval
- no unauthorized earnings claims
- acceptance of traffic rules
- acceptance of payout and hold rules
- acceptance of audit and evidence requests

## Stage E. Automated Pre-Screen

Required checks:

- email verified
- domain or website live
- social links live
- domain and business consistency
- blocked geos or denied categories
- duplicate or linked risk subjects
- existing rejected or suspended links
- obvious prohibited traffic indicators
- self-referral and abuse cluster hints

Outputs:

- pass
- needs_info
- auto_reject
- escalate_to_review

## Stage F. Human Review

Required review posture:

- manual-lite for low-risk creators
- always manual for Performance
- always manual for Reseller / API

Possible outcomes:

- approve to probation
- needs info
- reject
- waitlisted

## Stage G. Approved Probation Activation

Probation may unlock:

- workspace access
- contracts view
- basic code creation or starter code
- assets
- lite reporting
- support access
- payout profile setup

Probation should not automatically unlock:

- unlimited code creation
- unrestricted API credentials
- unrestricted performance traffic launch
- reseller storefront launch
- payout execution rights

## Stage H. Finance And Operational Readiness

Progressive onboarding:

- payout account setup
- tax and invoice details
- finance review if required
- reseller or performance technical readiness
- contract completion

Outputs:

- `ready_for_active` as a workflow readiness outcome
- workspace promotion to `active`
- `blocked_pending_finance` as a workflow outcome represented by readiness overlays, not a new workspace status
- `blocked_pending_compliance` as a workflow outcome represented by readiness overlays, not a new workspace status
- `blocked_pending_technical` as a workflow outcome represented by readiness overlays, not a new workspace status

---

## 5. Scenario-Specific Flows

### 5.1 Public Apply Flow

1. Create account
2. Verify email and MFA
3. Create workspace
4. Complete general profile
5. Complete one or more lane modules
6. Complete declarations
7. Submit application
8. Pass pre-screen
9. Enter human review
10. Move to `approved_probation`, `needs_info`, `rejected`, or `waitlisted`

### 5.2 Invite-Only Flow

1. Open invite link
2. Validate invite token and intended lane
3. Create partner-realm account or attach to partner-realm identity
4. Prefill workspace and lane info from invite
5. Complete missing profile, compliance, and finance tasks
6. Enter manual review if policy requires it
7. Move to probation or active according to invite policy and review result

If invite policy allows direct activation, workspace state still becomes `active`; `approved_active` remains lane-level language only.

### 5.3 Existing User Upgrade Flow

1. Authenticated customer requests partner application
2. System creates or links a partner-realm identity reference
3. New partner workspace is created in the partner realm
4. Shared profile data may be suggested, not silently copied as final truth
5. Applicant completes the same staged application as other partners
6. Review follows normal lane rules

---

## 6. Required Status Transitions

Expected workspace path:

`draft -> email_verified -> submitted -> under_review -> approved_probation -> active`

Alternative paths:

- `submitted -> needs_info -> under_review`
- `under_review -> rejected`
- `approved_probation -> restricted`
- `active -> restricted`
- `restricted -> active`
- `active -> suspended`
- `suspended -> terminated`

Lane status progresses separately and must not be collapsed into workspace status.

Workflow outcomes such as `ready_for_active` and `blocked_pending_*` are transition labels layered on top of the canonical statuses defined in `2026-04-18-partner-portal-status-and-visibility-matrix.md`.

---

## 7. Notifications And Messaging Requirements

The workflow must emit partner-visible events for:

- email verified
- application submitted
- review started
- requested information
- decision issued
- probation started
- finance task requested
- finance ready
- lane activated
- governance restriction applied

Pending applicants must have a messaging path to partner ops before full activation.

---

## 8. UX Requirements

The onboarding flow must:

- save progress by step
- show missing required items clearly
- explain why some fields are requested
- show current review status
- show what is blocked and why
- support document or evidence upload where needed
- support later re-entry without losing prior progress

---

## 9. Acceptance Conditions

This workflow spec is acceptable only when:

- it supports public, invite-only, and upgrade-based entry
- it separates application from activation
- it produces a governed probation stage
- it supports lane-specific evidence collection
- it supports finance and compliance readiness after approval where appropriate
