# CyberVPN Admin Portal Partner Operations Integration Spec

**Date:** 2026-04-20  
**Status:** Integration closure specification  
**Purpose:** define how admin portal surfaces and actions manage the complete partner lifecycle and how each admin action maps to partner-visible state.

---

## 1. Document Role

This document closes the operational seam between:

- partner portal external workspace surface
- admin portal internal operator surface
- risk, finance, compliance, and support workflows

It defines the target admin operating surface for partner lifecycle management.

---

## 2. Integration Principles

1. Partner lifecycle must be operable without direct SQL.
2. Admin actions must have explicit partner-facing consequences.
3. Sensitive actions must support maker-checker where required.
4. Admin RBAC must be explicit and narrow.
5. Every privileged action must be auditable.

---

## 3. Target Admin Menu Map For Partner Operations

| Admin Area | Purpose | Primary Domains |
|---|---|---|
| Partner Applications | intake, review, decisions | applications, review requests, attachments |
| Partner Accounts / Workspaces | workspace identity and membership | partner accounts, memberships, roles |
| Lane Memberships | lane approval and restrictions | program memberships, readiness |
| Partner Codes | code lifecycle and governance | partner codes, code versions |
| Traffic Declarations | declared traffic review | traffic declarations |
| Creative Approvals | creative review and decisions | creative approvals |
| Review Requests | applicant and workspace requested-info loop | review requests, thread events |
| Cases / Disputes | support, finance, compliance casework | partner cases, dispute cases |
| Payout Accounts | payout destination verification | partner payout accounts |
| Statements | statement generation, review, reopen | partner statements, adjustments |
| Payout Executions | maker-checker payout workflow | payout instructions, executions |
| Risk Reviews | risk and abuse review queue | risk reviews, governance actions |
| Governance Actions | restriction, freeze, suspension, override | governance actions |
| Legal / Policy Acceptance | acceptance history and required updates | policy acceptance, legal docs |
| Reporting / Exports | operational exports and reconciliation | reporting snapshots, exports |
| Audit Log | privileged action history | audit events |

---

## 4. Admin-To-Partner State Mapping

| Admin Action | Partner Portal Effect |
|---|---|
| request more application info | workspace moves to `needs_info`; applicant sees task in `/application` and `/cases` |
| approve workspace to probation | workspace becomes `approved_probation`; limited portal sections unlock |
| waitlist application | workspace becomes `waitlisted`; applicant sees deferred activation explanation |
| reject application | workspace becomes `rejected`; terminal-state explanation appears |
| approve lane to probation | lane appears as `approved_probation` in `/programs` |
| approve lane to active | lane appears as `approved_active`; lane-specific sections deepen |
| decline lane | lane appears as `declined`; partner sees reason code |
| suspend code | code shows `paused` or `revoked` with reason in `/codes` |
| approve traffic declaration | compliance item changes to approved in `/compliance` |
| reject creative | creative approval record shows rejection notes in `/campaigns` or `/compliance` |
| open risk review | governance state updates; restrictions become visible |
| freeze payout | finance page shows payout blocked reason |
| verify payout account | payout account becomes eligible/verified in `/finance` |
| reopen statement | finance page shows new statement version or review state |
| close case | case thread becomes resolved in `/cases` |

---

## 5. Maker-Checker Actions

Maker-checker is required for:

- payout account verification where policy requires dual control
- payout execution approval
- statement reopen after close
- reserve release
- manual settlement adjustment
- partner suspension
- reactivation from suspended state
- merchant/billing-sensitive overrides

## 5.1 Maker-Checker Outcome Requirements

Each maker-checker action must record:

- maker actor
- checker actor
- decision result
- reason
- linked evidence
- before and after values

---

## 6. Admin RBAC

| Role | Read | Create | Approve | Reject | Suspend | Override | Export |
|---|---|---|---|---|---|---|---|
| `super_admin` | full | full | full | full | full | full | full |
| `partner_ops` | broad partner domain | review requests, workspace actions | workspace and lane approval | application or lane reject | limited partner suspensions | no finance override by default | operational exports |
| `support` | cases, workspace read, reporting lite | cases, partner messages | no | no | no | no | limited |
| `finance_ops` | finance domain, statements, payout accounts | payout instructions, adjustments | payout and finance approvals | payout or finance rejects | payout freezes | limited finance override | finance exports |
| `fraud_risk` | risk, codes, traffic, reporting, partner read | risk reviews, governance actions | risk resolutions | traffic or governance rejects | code/workspace restrictions | limited risk override | risk exports |
| `compliance` | legal, policy, declarations, creative approvals | requests, policy updates, compliance cases | declaration/creative approvals | declaration/creative rejects | limited compliance restrictions | no financial override | compliance exports |
| `readonly_auditor` | broad read | no | no | no | no | no | audit exports only |

---

## 7. Audit Requirements

Every privileged action must emit an audit record with:

- actor id
- actor role
- timestamp
- action kind
- object kind
- object id
- workspace id where relevant
- before value
- after value
- reason code
- human-readable reason summary
- linked case or review id if applicable
- evidence attachment reference if required

Required audit visibility:

- operator-facing audit log in admin portal
- machine-readable export
- immutable backend persistence

---

## 8. Minimum Admin Screens Required Before Closure

The following admin screens are required for integration closure:

- application queue
- application detail
- workspace detail
- lane membership detail
- code action console
- traffic declaration review console
- creative approval review console
- partner cases console
- payout account review console
- payout execution maker-checker console
- governance action console
- policy acceptance viewer

If any of these remain absent, the partner portal may expose actions that internal teams cannot safely govern.

---

## 9. Closure Conditions

This spec is complete only when:

1. admin team can manage every partner lifecycle phase without direct SQL;
2. admin actions produce deterministic partner-facing state changes;
3. maker-checker is defined for sensitive actions;
4. admin RBAC is explicit enough for implementation and audit review.
