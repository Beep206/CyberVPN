# Implementation Start Point

## Purpose

This document fixes the exact starting boundary for implementation so the team does not begin with visually attractive but structurally premature work.

## Start Point Decision

The implementation starts with two tightly linked work packages:

1. `Group 1 — Shared Runtime Context`
2. `Mini App Routing and Payment Foundation`

These two packages are the correct first wave because:

- partner-branded runtime cannot be bolted on later without rework;
- payment, entitlement, and attribution correctness must be solved before White-Label scale;
- Mini App already exists in the repo and is the canonical conversion runtime;
- public Network Intelligence and White-Label will both depend on the same runtime and payment foundation.

## Why Not Start Elsewhere

### Why Not Start with White-Label UX First

Because that would encourage:

- static branding shortcuts;
- manual bot workflows;
- partner-specific payment or attribution hacks;
- tenant leakage risk.

### Why Not Start with Speed Map First

Because Speed Map is strategically important, but it does not unblock the core conversion contract. If we launched it first without the shared runtime and Mini App foundation, it would create traffic before the platform is ready to convert that traffic correctly.

## Wave 1 Objective

Wave 1 should leave the project in this state:

- runtime context exists as a first-class platform concept;
- Mini App routing is canonical and stable;
- Mini App auth and return paths never break out of `/miniapp/*`;
- Telegram Stars purchase flow has a correct baseline contract;
- payment fulfillment is authoritative and replay-safe;
- enough observability exists to validate the first integrated user path.

## Mandatory Preconditions Already Fixed by the Dossier

These are treated as accepted inputs to implementation:

- Mini App is the canonical conversion runtime.
- Telegram digital-goods flows use Stars / `XTR`.
- White-Label uses a shared multi-tenant runtime.
- Public network pages must use sanitized snapshots.
- CyberVPN remains platform-of-record in the baseline commercial model.
- Partner settlement history must be append-only.

## What Is In Scope for Wave 1

### Shared Runtime Context

- runtime tenant model
- attribution model
- identity link expansion
- surface taxonomy alignment
- bootstrap-ready runtime commercial context

### Mini App Foundation

- route and auth continuity
- bootstrap API foundation
- quote and invoice foundation
- pre-checkout-aware payment contract
- successful-payment-authoritative fulfillment
- config-delivery-safe post-payment flow

## What Is Explicitly Out of Scope for Wave 1

- full White-Label self-service wizard
- public partner onboarding launch
- recurring Telegram Stars subscriptions
- public DPI score launch
- partner widget rollout
- payout automation
- complete admin control plane implementation beyond what Wave 1 directly depends on

## Required Repositories and Areas to Touch First

### `backend/`

- runtime context and attribution expansion
- Mini App namespace
- payment contract extensions
- entitlement-safe fulfillment path

### `frontend/`

- Mini App routing corrections
- bootstrap-based data loading
- checkout state handling
- runtime hooks

### `services/telegram-bot/`

- payment event compatibility
- pre-checkout validation path
- successful payment handoff

### `partner/`

- no major UX implementation in Wave 1, except only if runtime context integration requires shared contract alignment

## Exit Criteria for Wave 1

Wave 1 is complete when:

1. runtime context and attribution contracts are implemented and documented in code;
2. Mini App root and auth flows are stable inside `/miniapp/*`;
3. a user can move from Mini App open to quote creation without route or tenant ambiguity;
4. invoice creation and payment reconciliation have a correct baseline Telegram Stars contract;
5. entitlement activation is driven only by authoritative payment success;
6. duplicate payment success events do not double-fulfill;
7. observability exists for bootstrap, checkout start, payment success, and config delivery;
8. the team can safely start White-Label bot provisioning and Public Network snapshot implementation on top of the shared base.

## Recommended Delivery Shape

Wave 1 should be implemented as a small number of coherent vertical slices, not dozens of unrelated commits:

1. Runtime context and attribution slice
2. Mini App route and auth continuity slice
3. Mini App bootstrap slice
4. Telegram Stars payment foundation slice
5. Payment-to-entitlement correctness and observability slice

## Go / No-Go Rule

Do not start broad White-Label feature work or public Speed Map launch work until Wave 1 exit criteria are met.
