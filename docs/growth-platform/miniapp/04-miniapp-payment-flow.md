# Mini App Payment Flow

## Policy

Telegram Mini App purchase flows use Telegram Stars / XTR as the primary and default payment rail.

For digital goods and services inside Telegram apps, Telegram requires Stars with currency `XTR`. Delivery must happen only after authoritative payment success, not after invoice UI close.

## Flow Overview

1. User selects a plan.
2. Frontend requests quote.
3. Backend validates pricing, attribution, and eligibility.
4. Frontend requests invoice creation.
5. Backend creates Telegram Stars invoice server-side.
6. Frontend opens invoice with Telegram WebApp API.
7. Telegram closes invoice UI.
8. Bot runtime handles `pre_checkout_query` and explicit validation.
9. Backend reconciles payment state.
10. Entitlement activates only after authoritative `successful_payment`.
11. User receives config or device onboarding.

## Quote Creation

Quote creation must include:

- plan and add-ons;
- runtime tenant context;
- referral and campaign metadata;
- active discounts and trial interactions;
- commercial policy restrictions.

Quote output should be immutable enough for invoice creation and reconciliation.

## Invoice Creation

Invoice creation must:

- reference a valid quote;
- bind payment to user, tenant, and attribution context;
- generate a Telegram-compatible invoice with currency `XTR`;
- persist payment ID before invoice URL is returned.

For Telegram Stars digital flows:

- third-party provider semantics do not define fulfillment;
- quote, tenant, and attribution must be locked before invoice open.

## Invoice Open

Frontend uses Telegram runtime to open invoice. The Mini App should:

- lock double-submit behavior;
- record `invoice_opened`;
- show pending state until backend refresh completes.

## Invoice Closed

When invoice UI closes:

- frontend refreshes payment status;
- backend may still report `pending` until authoritative payment update lands;
- UI must distinguish between `cancelled`, `pending`, and `paid`.
- UI close alone does not authorize delivery.

## Pre-Checkout Validation

The Telegram payment path must explicitly validate:

- quote still valid;
- tenant context still valid;
- pricing unchanged;
- commercial policy still allows the purchase;
- user and partner state not suspended.

The bot runtime must answer pre-checkout queries within Telegram time limits and reject unsafe or inconsistent orders.

## Successful Payment Handling

Required sequence:

1. payment success event reaches backend;
2. payment record becomes authoritative success;
3. order is finalized;
4. entitlement is activated;
5. config delivery becomes available;
6. partner attribution and analytics are finalized.

Authoritative success comes from Telegram payment events, not from the client UI.

## Refund Handling

The platform must define:

- when refunds are allowed;
- which support path is used;
- how partner revenue and internal settlement react to refunds;
- how entitlement state changes after refund.

Refund handling must create reversal effects in partner settlement accounting rather than mutating historical sale entries.

## Reconciliation

Use a dedicated reconciliation worker to:

- retry delayed status fetches;
- deduplicate webhook or event processing;
- repair transient mismatches;
- expose a clear operational dashboard.

This worker must also tolerate duplicate `successful_payment` events and refund follow-up events safely.

## Partner Attribution

Partner attribution must be attached at quote time and preserved through:

- invoice creation;
- payment success;
- entitlement creation;
- settlement accounting.

## Failure Cases

- quote expired before invoice creation;
- invoice creation failure;
- user closes invoice without payment;
- delayed payment success;
- duplicate success event;
- entitlement creation failure after payment success;
- refund after entitlement activation.

## Idempotency Rules

- one payment intent per quote and idempotency key;
- invoice creation returns existing live invoice where safe;
- payment success processing is idempotent;
- entitlement activation must not duplicate on replay;
- partner settlement reversal must not duplicate on refund replay.
