# CyberVPN Partner Portal Notification, Inbox And Case Event Spec

**Date:** 2026-04-20  
**Status:** Integration closure specification  
**Purpose:** define the event-driven communication layer for partner notifications, inbox behavior, case-linked messaging, and admin-to-partner communication.

---

## 1. Document Role

This document replaces the current placeholder notification model with a real event-driven contract.

It covers:

- notification feed
- read and unread lifecycle
- case and review-linked events
- admin-created partner messages
- routing from events to portal sections

---

## 2. Design Principles

1. Notifications are not local UI hints; they are backend-owned events.
2. Cases remain the canonical conversational workflow object.
3. Notification feed and cases may be separate surfaces, but they must be linked.
4. Every notification must route to a real portal section.
5. Notification counters in dashboard/bootstrap must reconcile with feed truth.

---

## 3. Canonical Event Types

| Event Type | Primary Source | Route Target | Action Required |
|---|---|---|---|
| `application_submitted` | application submit | `/application` | no |
| `application_needs_info` | review request | `/application` or `/cases` | yes |
| `application_under_review` | review intake | `/application` | no |
| `application_waitlisted` | review decision | `/application` | no |
| `application_approved_probation` | review decision | `/dashboard` and `/programs` | yes |
| `lane_membership_changed` | lane decision | `/programs` | sometimes |
| `legal_acceptance_required` | policy publish or readiness block | `/legal` | yes |
| `policy_updated` | policy version update | `/legal` | yes |
| `case_created` | support or ops action | `/cases` | yes |
| `case_reply_received` | case thread event | `/cases` | yes |
| `review_request_opened` | reviewer action | `/cases` or `/application` | yes |
| `traffic_declaration_approved` | compliance review | `/compliance` | no |
| `creative_rejected` | creative review | `/campaigns` or `/compliance` | yes |
| `statement_ready` | finance close | `/finance` | no |
| `payout_blocked` | finance or risk action | `/finance` | yes |
| `payout_executed` | payout completion | `/finance` | no |
| `integration_delivery_failed` | integration delivery log | `/integrations` | yes |
| `risk_review_opened` | governance action | `/compliance` or `/cases` | yes |
| `governance_action_applied` | governance action | `/dashboard` and affected section | yes |

---

## 4. Recipient Scope Matrix

| Notification Type | Recipient Scope | Required Role Or Permission | Visible In |
|---|---|---|---|
| `application_submitted` | workspace owner and workspace admin-equivalent launch roles | `workspace_read` | dashboard, notifications |
| `application_needs_info` | workspace owner plus members with application or operations visibility | `workspace_read` | application, cases, notifications |
| `application_approved_probation` | workspace owner and launch roles | `workspace_read` | dashboard, programs, notifications |
| `lane_membership_changed` | workspace owner, analyst, traffic manager where relevant | `workspace_read` | programs, notifications |
| `legal_acceptance_required` | workspace owner and legal/compliance manager | legal acceptance required capability | legal, notifications |
| `policy_updated` | workspace owner, legal/compliance manager, finance manager if finance terms affected | `workspace_read` | legal, notifications |
| `case_created` | owner plus roles with case visibility | `workspace_read` | cases, notifications |
| `case_reply_received` | owner plus roles with case visibility | `workspace_read` | cases, notifications |
| `review_request_opened` | owner plus roles allowed to respond operationally | `operations_write` or equivalent | application, cases, notifications |
| `traffic_declaration_approved` | owner plus traffic manager | `traffic_read` | compliance, notifications |
| `creative_rejected` | owner plus traffic manager | `traffic_read` | campaigns, compliance, notifications |
| `statement_ready` | owner plus finance manager | `earnings_read` or finance visibility | finance, notifications |
| `payout_blocked` | owner plus finance manager | `payouts_read` | finance, notifications |
| `payout_executed` | owner plus finance manager | `payouts_read` | finance, notifications |
| `integration_delivery_failed` | owner plus technical manager and support where policy allows | `integrations_read` | integrations, notifications |
| `risk_review_opened` | owner plus legal/compliance manager and finance/support depending on severity policy | `workspace_read` | compliance, cases, notifications |
| `governance_action_applied` | owner plus impacted role scopes | `workspace_read` | dashboard, affected section, notifications |

If a workspace does not yet have a specialized role assigned, delivery falls back to workspace owner plus any role with the required permission.

---

## 5. Inbox And Notification Domain Model

## 5.1 Required Entities

| Entity | Purpose |
|---|---|
| `partner_notifications` | immutable workspace-scoped event records |
| `partner_notification_read_states` | per-recipient read/archive state |
| `partner_inbox_threads` | thread metadata for message-capable objects |
| `partner_inbox_messages` | explicit human-authored messages |
| `partner_case_events` | case-specific operational thread events |

## 5.2 Recommended Relationship Model

- notifications are immutable events
- cases are workflow objects
- inbox threads unify message history where a conversation is needed
- a notification may link to:
  - a case
  - a review request
  - an application
  - a legal acceptance task
  - a payout or statement object

---

## 6. Lifecycle Rules

## 6.1 Notification Statuses

Supported recipient states:

- `unread`
- `read`
- `archived`
- `resolved`
- `expired`

## 6.2 Action Requirement Overlay

A notification may additionally carry:

- `action_required = true`
- `action_required = false`

`resolved` does not mean the event is deleted. It means the linked task has been resolved.

## 6.3 Counter Rules

Unread counters shown in:

- dashboard
- header
- sidebar badges

must be derived from canonical unread read-state records, not from frontend local state.

---

## 7. Correlation And Idempotency Rules

Every notification generated from backend event processing must include:

- `source_event_id`
- `source_event_kind`
- `workspace_id`
- recipient principal or membership scope

The backend must guarantee:

- duplicate `source_event_id + recipient_scope` does not create duplicate unread notifications;
- counters are derived from read-state truth, not stored as mutable counters;
- replay of event publication is idempotent.

---

## 8. Routing Rules

| Notification Type | Primary Route | Secondary Route |
|---|---|---|
| application lifecycle events | `/application` | `/dashboard` |
| review and requested-info events | `/cases` | `/application` |
| compliance events | `/compliance` | `/campaigns` |
| legal/policy events | `/legal` | `/dashboard` |
| finance events | `/finance` | `/dashboard` |
| integration failure events | `/integrations` | `/cases` |
| governance events | affected section | `/dashboard` |

If a linked object is no longer accessible, routing must fall back to:

- `/dashboard`
- `/cases`

with an explanatory state message.

---

## 9. Admin-Created Messages

Admin users must be able to:

- send partner workspace message
- request additional information
- attach evidence request
- link message to application
- link message to case
- link message to review request

Each admin-created message must record:

- sender actor
- recipient scope
- linked object
- message body
- attachments if any
- created timestamp

---

## 10. Required Endpoint Families

| Endpoint Family | Purpose |
|---|---|
| `/api/v1/partner-notifications` | list feed |
| `/api/v1/partner-notifications/counters` | unread and action-required counters |
| `/api/v1/partner-notifications/{id}/read` | mark read |
| `/api/v1/partner-notifications/{id}/archive` | archive |
| `/api/v1/partner-notifications/preferences` | notification preferences |
| `/api/v1/partner-inbox/threads` | list inbox threads if message model is enabled |
| `/api/v1/partner-inbox/threads/{id}/messages` | list or create messages in a thread |

Cases and review requests remain under their own canonical endpoint families and link into this feed layer.

---

## 11. Closure Conditions

This spec is complete only when:

1. `/notifications` is backed by canonical notification records;
2. unread counters come from backend truth;
3. case and review events can generate notifications;
4. admin can send partner-facing messages without manual side channels;
5. routing from notifications to portal sections is deterministic.
