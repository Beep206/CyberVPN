# Wave 1 Execution Backlog — Shared Runtime Context and Mini App Foundation

## Purpose

This document decomposes the first implementation wave into concrete execution streams, task groups, dependencies, and acceptance criteria.

## Wave 1 Scope

Wave 1 includes:

- `Group 1 — Shared Runtime Context`
- `Mini App routing and auth continuity`
- `Mini App bootstrap foundation`
- `Mini App Telegram Stars payment foundation`
- `payment-to-entitlement correctness`
- `minimum observability and QA coverage`

## Delivery Streams

| Stream | Focus | Primary Owners |
|---|---|---|
| W1-A | Shared runtime and attribution core | Backend |
| W1-B | Mini App routing and auth continuity | Frontend |
| W1-C | Mini App bootstrap and read model | Backend + Frontend |
| W1-D | Telegram Stars payment foundation | Backend + Bot Service + Frontend |
| W1-E | Observability, QA, and release readiness | Platform + QA |

## Stream W1-A — Shared Runtime Context

### W1-A1: Define Runtime Commercial Context Contract

Objective:

- introduce a canonical runtime context that can serve both platform and partner-branded surfaces.

Tasks:

- define runtime context type and backend serialization contract;
- include tenant, brand, commercial policy, and attribution sections;
- align surface taxonomy with dossier.

Primary areas:

- `backend/src/domain/*`
- `backend/src/application/use_cases/*`
- `frontend/src/*` shared types where required

Acceptance criteria:

- one canonical runtime contract exists;
- both `platform` and `partner` tenant modes are represented;
- Mini App bootstrap can depend on it without ad hoc extensions.

### W1-A2: Identity and Attribution Linkage Expansion

Objective:

- make attribution and Telegram identity reliable enough for Mini App and later partner flows.

Tasks:

- expand identity link model where needed;
- normalize `source`, `surface`, `partner`, `bot`, `storefront`, `campaign`, and `start_param`;
- ensure attribution survives into payment intent creation.

Acceptance criteria:

- backend can resolve attribution for Mini App quote creation;
- unresolved or malformed attribution fails safely.

### W1-A3: Migration Group 1 Implementation

Objective:

- implement the first migration group from the dossier.

Tasks:

- add shared runtime context support fields/tables;
- add surface and attribution metadata support;
- add any transitional backfill logic needed for existing users or sessions.

Acceptance criteria:

- schema supports runtime context without JSON-only shortcuts;
- migration order is documented in code comments or migration metadata.

## Stream W1-B — Mini App Routing and Auth Continuity

### W1-B1: Fix Canonical Root Routing

Objective:

- make Mini App entry deterministic.

Tasks:

- change Mini App root redirect to `/[locale]/miniapp/home`;
- review any route guards or navigation assumptions that still point to `/home` or `/dashboard`.

Acceptance criteria:

- direct Mini App root entry always lands in Mini App namespace;
- no auth success path escapes to regular dashboard routes.

### W1-B2: Preserve Mini App Namespace Through Auth and 2FA

Objective:

- keep all return paths Mini App-safe.

Tasks:

- update Mini App auth provider redirects;
- update 2FA return handling;
- review any global auth fallback that assumes web dashboard as destination.

Acceptance criteria:

- authenticated Mini App users stay in `/miniapp/*`;
- 2FA completion returns into Mini App flow.

### W1-B3: Add Route Regression Tests

Objective:

- prevent future route drift.

Tasks:

- add route and auth continuity coverage;
- cover root entry, auth success, and 2FA return.

Acceptance criteria:

- regressions fail in automated tests.

## Stream W1-C — Mini App Bootstrap and Read Model

### W1-C1: Create `/api/v1/miniapp/bootstrap`

Objective:

- replace broad client fan-out with one consolidated bootstrap.

Tasks:

- create Mini App namespace if absent;
- assemble runtime, user, subscription, trial, wallet, devices, referral, support, and primary CTA;
- include freshness metadata.

Acceptance criteria:

- home state can render from bootstrap;
- runtime tenant context is included;
- bootstrap response is small and stable enough for Telegram webview usage.

### W1-C2: Refactor Home and Plans to Use Mini App Contracts

Objective:

- reduce generic API fan-out and align UI with new read model.

Tasks:

- introduce Mini App API client layer;
- move critical home/plans rendering to bootstrap or Mini App-specific contracts;
- keep fallback handling explicit.

Acceptance criteria:

- home and plans screens do not depend on large uncontrolled request fans;
- failures degrade predictably.

### W1-C3: Prepare Server-Picker Input Contract

Objective:

- make sure later server picker work is unblocked.

Tasks:

- define recommended server shape in bootstrap or servers endpoint;
- ensure contract is compatible with future Network Intelligence snapshot data.

Acceptance criteria:

- server recommendation is represented in the Mini App contract even if full server picker UI is not complete yet.

## Stream W1-D — Telegram Stars Payment Foundation

### W1-D1: Create Quote Foundation

Objective:

- establish a server-side commercial intent before invoice creation.

Tasks:

- create quote endpoint;
- validate plan, add-ons, tenant context, attribution, and pricing;
- make quote idempotent where appropriate.

Acceptance criteria:

- quote is stable enough to be the basis for invoice creation;
- malformed attribution or invalid tenant context is rejected.

### W1-D2: Create Telegram Invoice Foundation

Objective:

- create server-side invoice generation for Stars purchases.

Tasks:

- create invoice endpoint returning payment ID and invoice URL;
- enforce `XTR` flow assumptions;
- persist payment intent before returning invoice data.

Acceptance criteria:

- Mini App can open Telegram invoice from backend-created data;
- no client-side price tampering path exists.

### W1-D3: Pre-Checkout Validation Integration

Objective:

- ensure Telegram payment flow is checked before checkout proceeds.

Tasks:

- define how bot runtime validates quote, tenant state, suspension state, and policy state on `pre_checkout_query`;
- reject inconsistent or unsafe purchase attempts;
- log failures for investigation.

Acceptance criteria:

- pre-checkout rejects invalid or stale payment attempts;
- validation path is explicit and testable.

### W1-D4: Authoritative Successful Payment Fulfillment

Objective:

- tie service delivery to authoritative payment success only.

Tasks:

- implement `successful_payment` authoritative transition;
- map payment success to order finalization and entitlement activation;
- add replay-safe handling for duplicate success events.

Acceptance criteria:

- entitlement is not activated on invoice close alone;
- duplicate success events do not double-fulfill.

### W1-D5: Refund and Reversal Baseline

Objective:

- make refund handling non-destructive from the beginning.

Tasks:

- define refund-aware payment state transitions;
- create settlement reversal design hooks for later White-Label finance;
- ensure refund does not require mutating historical sale facts.

Acceptance criteria:

- refund path is represented in the model and tests;
- later ledger implementation can consume it without redesign.

## Stream W1-E — Observability, QA, and Release Readiness

### W1-E1: Event Instrumentation for the First Critical Path

Objective:

- instrument the exact path being built.

Required events:

- `miniapp_opened`
- `miniapp_bootstrap_loaded`
- `miniapp_auth_success`
- `checkout_started`
- `miniapp_invoice_opened`
- `payment_success`
- `config_delivered`

Acceptance criteria:

- events are visible in development and test environments;
- event payload includes surface and runtime context.

### W1-E2: Core Test Matrix

Objective:

- validate Wave 1 before broader feature work begins.

Required tests:

- route continuity tests;
- bootstrap contract tests;
- quote and invoice idempotency tests;
- duplicate `successful_payment` handling tests;
- pre-checkout rejection tests;
- payment-to-entitlement integration tests.

Acceptance criteria:

- Wave 1 critical path has automated coverage across unit, integration, and E2E layers where appropriate.

### W1-E3: Release Gate for Wave 1 Completion

Objective:

- define the point where the team can start Wave 2 work safely.

Wave 1 release gate:

- routing fixed;
- runtime context implemented;
- bootstrap live;
- quote and invoice flows live in development or staging;
- successful payment path authoritative;
- regression tests passing;
- required telemetry live.

## Dependencies

| Dependency | Required By |
|---|---|
| Runtime context contract | Bootstrap, quote creation, later partner branding |
| Telegram Stars payment policy | Quote and invoice foundation |
| Surface taxonomy | Observability and analytics |
| Migration Group 1 | Runtime context persistence |
| Existing entitlement model | Payment fulfillment |

## Explicit Non-Goals for Wave 1

- full White-Label onboarding UX
- public partner launch
- public Speed Map rollout
- recurring Telegram Stars subscriptions
- payout automation
- full admin control plane implementation

## Recommended PR / Slice Order

1. Runtime context contract + migration group 1
2. Mini App route and auth corrections
3. Mini App bootstrap API + frontend adoption
4. Quote and invoice backend foundation
5. Pre-checkout + successful-payment authoritative path
6. Observability + regression tests

## Wave 1 Done State

The team may consider Wave 1 complete only when the first end-to-end Mini App conversion path is technically correct and reusable by later platform layers, not merely visually functional.
