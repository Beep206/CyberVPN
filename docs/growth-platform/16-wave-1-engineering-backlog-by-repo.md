# Wave 1 Engineering Backlog by Repo

## Purpose

This document converts the Wave 1 execution backlog into repo-by-repo engineering work. It is intended to be close enough to implementation that engineering leads can assign slices without reinterpreting the platform dossier.

## Wave 1 Scope Reminder

Wave 1 covers:

- `Group 1 — Shared Runtime Context`
- Mini App routing and auth continuity
- Mini App bootstrap foundation
- Telegram Stars payment foundation
- payment-to-entitlement correctness
- minimum observability and QA coverage

## Repo Overview

| Repo Area | Wave 1 Role |
|---|---|
| `backend/` | source of truth for runtime context, quote/invoice/payment state, entitlement correctness |
| `frontend/` | canonical Mini App routing, bootstrap-driven UI, invoice lifecycle UX |
| `services/telegram-bot/` | Telegram payment event handling, pre-checkout validation, successful payment handoff |
| `partner/` | mostly untouched in Wave 1 except for contract awareness |
| `infra/` | no major public rollout work in Wave 1, limited observability support only |

## Backend Backlog

## B1. Runtime Context Foundation

### Objective

Introduce a canonical runtime commercial context and attribution contract that Mini App and later partner-branded flows can consume.

### Likely existing anchors

- `backend/src/presentation/dependencies/auth_realms.py`
- `backend/src/presentation/dependencies/partner_workspace.py`
- `backend/src/presentation/api/v1/auth/realm_context.py`
- `backend/src/domain/entities/auth_realm.py`
- `backend/src/domain/entities/storefront.py`
- `backend/src/domain/entities/customer_commercial_binding.py`
- `backend/src/domain/entities/attribution_touchpoint.py`
- `backend/src/domain/entities/order_attribution_result.py`
- `backend/src/application/use_cases/auth_realms/resolve_realm.py`
- `backend/src/application/use_cases/commerce_sessions/context_resolution.py`
- `backend/src/application/use_cases/attribution/*`

### Tasks

- define a reusable runtime commercial context DTO or domain contract;
- include tenant, brand, commercial policy, attribution, and surface data;
- align auth realm resolution with runtime context resolution;
- ensure attribution resolution can survive into quote and payment creation.

### Acceptance criteria

- backend exposes one canonical runtime context shape for Mini App bootstrap;
- runtime context can represent both `platform` and future `partner` tenant modes;
- attribution fields are explicit and not inferred ad hoc by every endpoint.

## B2. Migration Group 1

### Objective

Implement the first migration wave that supports shared runtime context and attribution.

### Likely existing anchors

- `backend/alembic/versions/20260417_phase1_auth_realms.py`
- `backend/alembic/versions/20260417_phase1_storefront_core.py`
- `backend/alembic/versions/20260417_phase1_partner_workspace.py`
- `backend/alembic/versions/20260421_phase14_mobile_telegram_oidc_subject.py`

### Tasks

- create new Alembic revision for runtime context and attribution support;
- extend existing realm/session/attribution tables as needed;
- document backfill behavior for existing Mini App and Telegram-linked users.

### Acceptance criteria

- no Wave 1 logic depends on undocumented schema shortcuts;
- migration order is explicit and compatible with current Alembic structure.

## B3. Mini App Namespace

### Objective

Add a Mini App-specific backend namespace that aggregates existing use cases into Telegram-optimized contracts.

### Likely existing anchors

- `backend/src/presentation/api/v1/auth/routes.py`
- `backend/src/presentation/api/v1/telegram/routes.py`
- `backend/src/presentation/api/v1/trial/routes.py`
- `backend/src/presentation/api/v1/payments/routes.py`
- `backend/src/presentation/api/v1/quotes/routes.py`
- `backend/src/presentation/api/v1/payment_attempts/routes.py`
- `backend/src/application/use_cases/auth/telegram_miniapp.py`
- `backend/src/application/use_cases/trial/activate_trial.py`
- `backend/src/application/use_cases/payments/checkout.py`
- `backend/src/application/use_cases/payments/commit_checkout.py`
- `backend/src/application/use_cases/subscriptions/get_current_entitlements.py`

### Tasks

- create `backend/src/presentation/api/v1/miniapp/`;
- implement `bootstrap`, `offers`, `quote`, `invoice`, and `payment status` paths for Wave 1;
- reuse existing domain logic instead of cloning it;
- include freshness and runtime context in bootstrap.

### Acceptance criteria

- home and plans flows can depend on Mini App-specific contracts instead of uncontrolled generic fan-out;
- bootstrap endpoint is fast, stable, and Telegram-oriented.

## B4. Payment and Entitlement Correctness

### Objective

Establish the correct baseline Telegram Stars purchase contract.

### Likely existing anchors

- `backend/src/domain/entities/payment.py`
- `backend/src/domain/entities/payment_attempt.py`
- `backend/src/domain/entities/quote_session.py`
- `backend/src/domain/entities/checkout_session.py`
- `backend/src/application/use_cases/payments/checkout.py`
- `backend/src/application/use_cases/payments/commit_checkout.py`
- `backend/src/application/use_cases/payments/post_payment.py`
- `backend/src/application/use_cases/payments/payment_webhook.py`
- `backend/src/application/use_cases/orders/create_order_from_checkout.py`
- `backend/src/application/services/entitlements_service.py`
- `backend/src/presentation/api/v1/payment_attempts/*`
- `backend/src/presentation/api/v1/checkout_sessions/*`
- `backend/src/presentation/api/v1/payments/*`

### Tasks

- make quote creation runtime-context-aware;
- create invoice generation path for `XTR` purchase flows;
- define authoritative state transitions for payment success and replay handling;
- ensure entitlement activation occurs only after authoritative success.

### Acceptance criteria

- invoice UI close alone never fulfills service;
- duplicate success events do not double-activate entitlement;
- payment state can be observed through backend contracts.

## B5. Minimum Refund and Reversal Hooks

### Objective

Prepare the system for refund-safe behavior without implementing the full settlement layer yet.

### Likely existing anchors

- `backend/src/presentation/api/v1/refunds/*`
- `backend/src/presentation/api/v1/payment_disputes/*`
- `backend/src/application/use_cases/payment_disputes/*`
- `backend/alembic/versions/20260418_phase2_refunds_and_disputes.py`

### Tasks

- define refund-aware payment state mapping;
- add explicit reversal hooks for later ledger integration;
- ensure refund does not imply destructive history mutation.

### Acceptance criteria

- refund path is represented in code contracts and tests;
- later White-Label finance can attach ledger entries without redesigning payment history.

## Frontend Backlog

## F1. Route and Auth Continuity

### Likely existing anchors

- `frontend/src/app/[locale]/miniapp/page.tsx`
- `frontend/src/features/auth/components/TelegramMiniAppAuthProvider.tsx`
- `frontend/src/stores/auth-store.ts`
- `frontend/src/features/auth/lib/pending-twofa-client.ts`
- `frontend/src/i18n/navigation.ts`

### Tasks

- fix Mini App root redirect;
- keep auth success inside Mini App namespace;
- keep 2FA completion inside Mini App namespace;
- add or update route regression tests.

### Acceptance criteria

- no normal Mini App auth path exits to `/dashboard`;
- root entry always lands in `/miniapp/home`.

## F2. Runtime and Bootstrap Adoption

### Likely existing anchors

- `frontend/src/app/[locale]/miniapp/layout.tsx`
- `frontend/src/app/[locale]/miniapp/hooks/useTelegramWebApp.ts`
- `frontend/src/app/[locale]/miniapp/home/page.tsx`
- `frontend/src/app/[locale]/miniapp/plans/page.tsx`
- `frontend/src/lib/api/auth.ts`
- `frontend/src/lib/api/payments.ts`
- `frontend/src/lib/api/vpn.ts`
- `frontend/src/lib/api/referral.ts`
- `frontend/src/lib/api/servers.ts`

### Tasks

- introduce Mini App API client layer for bootstrap-oriented reads;
- reduce page-level request fan-out in home and plans;
- add runtime hooks needed for invoice lifecycle and Telegram UX.

### Acceptance criteria

- home and plans render from Mini App-specific contracts;
- runtime hook layer supports later server picker and payment work.

## F3. Payment UX Foundation

### Likely existing anchors

- `frontend/src/app/[locale]/miniapp/plans/page.tsx`
- `frontend/src/app/[locale]/miniapp/payments/page.tsx`
- `frontend/src/lib/api/payments.ts`
- `frontend/src/lib/api/client.ts`
- `frontend/src/stores/__tests__/auth-store-miniapp.test.ts`

### Tasks

- integrate quote and invoice flow with backend Mini App API;
- handle invoice open, close, pending, paid, canceled, and failed states;
- refresh payment status server-authoritatively after invoice UI close.

### Acceptance criteria

- client UI never treats invoice close as delivery success;
- payment states are explicit and testable.

## Telegram Bot Service Backlog

## T1. Pre-Checkout Validation

### Current repo signal

The current `services/telegram-bot/src/handlers/payment.py` responds to pre-checkout with:

- `ok=False`
- `"Telegram Stars are not enabled in this flow"`

This is a direct Wave 1 gap.

### Likely existing anchors

- `services/telegram-bot/src/handlers/payment.py`
- `services/telegram-bot/src/services/payment_stars.py`
- `services/telegram-bot/src/services/api_client.py`
- `services/telegram-bot/src/services/payment_service.py`

### Tasks

- replace placeholder rejection with real pre-checkout validation;
- validate quote, user, tenant context, and suspension state;
- return user-safe error when checkout must be rejected.

### Acceptance criteria

- valid orders can pass pre-checkout;
- invalid or stale orders are rejected predictably and logged.

## T2. Successful Payment Handling

### Current repo signal

`successful_payment_handler` currently logs `unexpected_successful_payment_received`, which means the baseline flow is not production-ready yet.

### Tasks

- map successful payment payloads to backend payment finalization;
- ensure duplicate event safety;
- trigger config-ready or entitlement-ready state through the backend rather than local assumptions.

### Acceptance criteria

- successful payment no longer lands in an "unexpected" path;
- backend becomes the source of truth for fulfillment.

## T3. Deep Links and Support

### Likely existing anchors

- `services/telegram-bot/src/utils/deep_links.py`
- `services/telegram-bot/src/handlers/support.py`
- `services/telegram-bot/src/handlers/subscription.py`
- `services/telegram-bot/src/keyboards/payment.py`

### Tasks

- align `startapp` payload generation with signed attribution expectations;
- ensure payment-support path is available for Telegram payment issues;
- keep bot-generated links aligned with Mini App route policy.

### Acceptance criteria

- bot entry links are compatible with Mini App runtime expectations;
- payment-support path exists for operational use.

## Partner Repo Backlog

Wave 1 should avoid major `partner/` implementation, but should reserve compatibility work if shared runtime contracts need aligned TypeScript types or preview scaffolding.

Likely areas to watch:

- `partner/src/features/storefront-shell/lib/runtime.ts`
- `partner/src/features/partner-portal-state/lib/use-partner-portal-runtime-state.ts`

## Recommended Implementation Order

1. Backend runtime context and migration group 1
2. Frontend Mini App route/auth continuity
3. Backend Mini App bootstrap
4. Frontend bootstrap adoption
5. Backend quote/invoice foundation
6. Telegram bot pre-checkout and successful payment handling
7. Payment-to-entitlement tests and observability

## Wave 1 Completion Signal

This backlog is complete only when the first Mini App conversion path is both technically correct and reusable by later White-Label and Network Intelligence work.
