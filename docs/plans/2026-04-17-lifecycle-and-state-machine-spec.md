# CyberVPN Lifecycle And State Machine Spec

**Date:** 2026-04-17  
**Status:** Domain specification  
**Purpose:** define the canonical lifecycle expectations and state machine requirements for the major commercial, financial, risk, and entitlement objects in the CyberVPN partner platform.

---

## 1. Document Role

This document defines state-machine expectations for major platform objects.

Detailed implementation statuses may evolve, but all implementations must preserve the lifecycle constraints described here.

---

## 2. Objects Requiring Formal Lifecycle Specs

- `quote_session`
- `checkout_session`
- `order`
- `payment_attempt`
- `refund`
- `payment_dispute`
- `partner_statement`
- `payout_execution`
- `risk_review`
- `entitlement_grant`

---

## 3. Lifecycle Requirements

Every lifecycle spec must define:

- statuses;
- valid transitions;
- who can trigger each transition;
- idempotent transitions;
- terminal states;
- reopen rules if any;
- immutable fields after finalization.

---

## 4. Canonical Expectations By Object

## 4.1 Quote Session

Must:

- expire cleanly;
- never silently mutate into a completed order;
- be safe to recompute if stale.

## 4.2 Checkout Session

Must:

- capture customer interaction context;
- link to one eventual order at most;
- preserve idempotent commit boundaries.

## 4.3 Order

Must:

- become the immutable commercial record after finalization;
- preserve pricing and attribution snapshots;
- remain explainable after refunds and adjustments.

## 4.4 Payment Attempt

Must:

- support retry semantics without duplicating orders;
- map clearly to one order;
- expose provider-state transitions separately from order state.

## 4.5 Refund

Must:

- be explicit and typed;
- support provider-state synchronization;
- link back to order and financial adjustments.

## 4.6 Payment Dispute

Must:

- normalize inquiry, chargeback, and final-outcome states;
- support evidence attachment lifecycle;
- expose financial consequences separately from dispute state.

## 4.7 Partner Statement

Must:

- support open, close, adjust, and reconcile behavior;
- prevent silent mutation after closure;
- preserve adjustment lineage.

## 4.8 Payout Execution

Must:

- support approval, submission, completion, failure, and reconciliation states;
- preserve maker-checker evidence;
- avoid destructive mutation.

## 4.9 Risk Review

Must:

- support triage, evidence collection, decision, and closure;
- preserve actor attribution for decisions.

## 4.10 Entitlement Grant

Must:

- support pending, active, suspended, revoked, and expired states;
- remain separable from customer account state;
- drive service access consistently across channels.

---

## 5. Acceptance Conditions

This spec is acceptable only when:

- every critical platform object has a lifecycle contract;
- idempotency and terminality are defined for all sensitive flows;
- reopen rules are explicit rather than accidental.
