# CyberVPN Partner Portal Application Review And Approval Policy

**Date:** 2026-04-18  
**Status:** Review and approval policy  
**Purpose:** define how partner applications are screened, reviewed, approved, rejected, or moved into probation across the partner revenue lanes.

---

## 1. Document Role

This document defines the partner approval policy used by:

- partner ops
- risk and compliance
- finance ops
- support
- product and engineering teams implementing the portal and workflow logic

---

## 2. Policy Principles

1. Application is self-serve; activation is governed.
2. Approval is not a binary one-time event. It includes screening, review, and probation.
3. Different lanes require different review depth.
4. High-risk or high-impact applicants should never bypass human review.
5. Approval may grant probation instead of full activation.

---

## 3. Three-Layer Review Model

### 3.1 Eligibility Screening

Purpose:

- reject obviously unqualified or prohibited applicants early

### 3.2 Business Fit Review

Purpose:

- determine whether the applicant is a good commercial and operational fit for the requested lane

### 3.3 Post-Approval Probation

Purpose:

- validate real behavior after approval before granting full active capability

---

## 4. Intake Channels

The approval policy must support:

- public application
- invite-only onboarding
- existing-user upgrade request

All three channels still respect lane-specific review policy.

---

## 5. Hard Reject Rules

Applications should be rejected or blocked immediately if any of the following are confirmed:

- no real owned channel or business presence
- fake, dead, or obviously fabricated social profiles
- adult, warez, malware, scam, or deceptive content
- refusal to accept traffic, compliance, or payout rules
- clear history of spam, fake reviews, trademark abuse, or bot traffic
- performance applicant refuses traffic declaration or postback readiness
- reseller applicant lacks legal entity or support ownership capacity
- high-risk self-referral or payout-abuse cluster is detected

---

## 6. Automated Pre-Screen Requirements

The pre-screen engine should evaluate at least:

- email verification
- domain existence
- website and social link validity
- business email versus claimed business identity
- blocked geos or denied categories
- linked risk subjects
- prior rejected or suspended workspace links
- suspicious dead-profile patterns
- obvious self-referral or self-purchase risk clusters

Possible outputs:

- `pass`
- `needs_info`
- `auto_reject`
- `manual_review_required`

---

## 7. Manual Review Scorecard

Use a 100-point scorecard.

| Category | Weight | Evaluation themes |
|---|---|---|
| Identity and legitimacy | 20 | business presence, contact integrity, legal consistency |
| Traffic or audience quality | 25 | real reach, ownership, quality signals, channel sanity |
| Compliance and risk posture | 20 | policy awareness, low fraud indicators, transparent methods |
| Commercial fit | 20 | privacy/security fit, geo fit, realistic lane fit |
| Operational and technical maturity | 15 | support, finance, technical readiness, reporting maturity |

Threshold guidance:

- `< 60` -> reject or move to `waitlisted` only when re-entry is intentionally allowed
- `60-79` -> manual review plus needs info or probation-only
- `80+` -> eligible for approval to probation if no hard-fail flags exist

---

## 8. Lane-Specific Review Rules

### 8.1 Creator / Affiliate

Default review model:

- public application allowed
- auto-screen plus manual-lite review
- approve to probation by default

Expected evidence:

- real owned channels
- content fit with privacy or security audiences
- disclosure awareness
- no obvious coupon-spam or brand-abuse profile

### 8.2 Performance / Media Buyer

Default review model:

- application allowed, but no instant activation
- mandatory manual review
- mandatory traffic declaration
- mandatory postback or tracking readiness
- mandatory probation

Required checks:

- source-by-source traffic plan
- creatives or creative categories
- sub_id / click_id capability
- geo plan
- anti-fraud posture

### 8.3 Reseller / API / Distribution

Default review model:

- public interest form or application allowed
- mandatory manual review
- discovery call or equivalent review often required

Required checks:

- legal entity posture
- support ownership
- billing and support responsibility understanding
- storefront or API plan
- technical contact and readiness

---

## 9. Review Outcomes

Possible outcomes:

- `needs_info`
- `under_review`
- `approved_probation`
- workspace `active` only in tightly controlled invited cases after readiness gates are satisfied
- `rejected`
- `waitlisted`

Recommended default:

- do not jump directly from review to unrestricted active
- prefer `approved_probation` for most first-time partner approvals
- `approved_active` remains lane-level language and must not be used as a workspace-level canonical state
- reviewer language such as "decline" must map to the canonical workspace state `rejected`

---

## 10. Probation Policy

Probation should grant:

- workspace access
- contract visibility
- limited codes or a starter code
- asset access
- lite analytics
- payout setup

Probation should not automatically grant:

- unrestricted code creation
- unrestricted integrations
- unrestricted reseller storefront setup
- unrestricted performance traffic scale
- full payout availability without finance readiness

Probation exit criteria may include:

- readiness tasks completed
- no critical compliance issues
- acceptable early conversion quality
- no major fraud or abuse signals

---

## 11. Review Governance

### 11.1 Internal Reviewer Ownership

Suggested ownership:

- partner ops owns standard creator review
- risk owns suspicious traffic and policy concerns
- finance owns payout-bearing readiness concerns
- legal or compliance owns material declarations and policy exceptions

### 11.2 SLA Guidance

Recommended internal SLA targets:

- public creator applications: short-cycle review
- performance and reseller applications: slower, evidence-driven review
- `needs_info` tasks: partner-facing due date with auto-reminder

---

## 12. Appeals And Re-Entry

The policy should support:

- resubmission after `needs_info`
- appeal path for decline where policy allows
- reactivation request for previously restricted partners where policy allows

The policy should not promise automatic reinstatement.

---

## 13. Acceptance Conditions

This approval policy is acceptable only when:

- it supports auto-screen plus human review
- lane-specific differences are explicit
- probation is treated as a first-class stage
- hard rejects are explicit enough for product and backend enforcement
- activation and approval remain distinct concepts
