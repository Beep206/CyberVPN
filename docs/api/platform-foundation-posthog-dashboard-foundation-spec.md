# Platform Foundation PostHog Dashboard Foundation Spec

**Date:** 2026-04-23  
**Status:** `P3.7` frozen repository-slice spec

This document defines the first `P3.7` repository slice for `PostHog` dashboard foundation:

- dashboard contract registry for `checkout`, `onboarding`, `partner workspace`, and
  `retention lifecycle`;
- first governed UX event expansion for storefront checkout and partner onboarding;
- first retention-side authoritative bridge expansion beyond `checkout_payment_captured`.

It complements:

- [platform-foundation-posthog-bridge-and-flag-wrapper-spec.md](platform-foundation-posthog-bridge-and-flag-wrapper-spec.md)
- [../growth-platform/posthog-product-taxonomy-and-privacy-baseline.md](../growth-platform/posthog-product-taxonomy-and-privacy-baseline.md)
- [../growth-platform/posthog-feature-flag-governance.md](../growth-platform/posthog-feature-flag-governance.md)
- [../plans/2026-04-23-platform-foundation-p3-7-posthog-dashboard-foundation-execution-packet.md](../plans/2026-04-23-platform-foundation-p3-7-posthog-dashboard-foundation-execution-packet.md)

## 1. Canonical Decisions

1. `P3.7` does not claim live `PostHog` dashboards; it freezes the canonical dashboard
   contracts and first repository-backed event sources.
2. Dashboard contracts are explicit and typed; no team may improvise metric meaning directly
   inside a live `PostHog` UI without a repo-level contract.
3. Checkout and onboarding dashboards may use governed frontend UX events, but each dashboard
   must also identify its authoritative server-side anchors.
4. Retention lifecycle dashboards use `checkout_payment_captured` and `subscription_activated`
   as the first authoritative anchors in this repository slice.
5. `subscription_renewed` and `subscription_cancelled` remain reserved follow-up events and
   are not falsely presented as live in `P3.7`.

## 2. Canonical Dashboard Keys

Frozen dashboard keys:

- `checkout_funnel_v1`
- `onboarding_funnel_v1`
- `partner_workspace_usage_v1`
- `retention_lifecycle_v1`

Every dashboard contract must define:

- owner;
- title;
- description;
- primary metric;
- guardrail metrics;
- required events;
- authoritative events;
- reserved future events, if the slice is intentionally partial.

## 3. Dashboard Event Matrix

| Dashboard | Required events | Authoritative events |
|---|---|---|
| `checkout_funnel_v1` | `checkout_started`, `checkout_step_viewed`, `checkout_step_completed`, `checkout_payment_submitted`, `checkout_payment_captured` | `checkout_payment_captured` |
| `onboarding_funnel_v1` | `onboarding_started`, `onboarding_step_completed`, `partner_user_activated` | `partner_user_activated` |
| `partner_workspace_usage_v1` | `partner_dashboard_viewed`, `feature_flag_evaluated`, `experiment_exposure_recorded` | `feature_flag_evaluated`, `experiment_exposure_recorded` |
| `retention_lifecycle_v1` | `checkout_payment_captured`, `subscription_activated` | `checkout_payment_captured`, `subscription_activated` |

Reserved retention follow-ups:

- `subscription_renewed`
- `subscription_cancelled`

## 4. Repository-Slice Touchpoints

The first `P3.7` repository slice is implemented through:

- `backend/src/application/services/posthog_bridge.py`
  - authoritative expansion for `entitlement.grant.activated -> subscription_activated`
- `partner/src/lib/product-intelligence/dashboard-contracts.ts`
  - canonical dashboard catalog and validation
- `partner/src/lib/product-intelligence/event-builders.ts`
  - typed UX event builders for checkout and onboarding
- `partner/src/features/storefront-shell/components/storefront-checkout-analytics-reporter.tsx`
  - route-level checkout entry instrumentation
- `partner/src/features/storefront-shell/components/storefront-checkout-shell.tsx`
  - payment-submission and order-ready UX event publication
- `partner/src/features/partner-onboarding/components/partner-onboarding-analytics-reporter.tsx`
  - onboarding-start and step-completion instrumentation
- `partner/src/features/partner-onboarding/components/application-foundation-page.tsx`
  - runtime mount point for onboarding analytics

## 5. P3.7 Repository-Slice Limits

This repository slice intentionally does **not** claim:

- live `PostHog` insight creation or dashboard API provisioning;
- live `PostHog` funnel screenshots or query execution proof;
- live retention metrics for renewal and cancellation;
- live commercial bridge consumer execution against deployed NATS or outbox dispatchers.

Those remain closure work for `P3.7+` and later `Gate D` evidence.

