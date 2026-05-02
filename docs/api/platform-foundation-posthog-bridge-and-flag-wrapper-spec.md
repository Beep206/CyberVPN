# Platform Foundation PostHog Bridge And Flag Wrapper Spec

**Date:** 2026-04-22  
**Status:** `P3.6` frozen repository-slice spec

This document defines the first authoritative `P3.6` repository slice for:

- `PostHog` server-side analytics bridge inputs;
- internal frontend product-event ingestion path;
- typed product feature-flag wrapper and bootstrap model.

It complements:

- [platform-foundation-event-taxonomy.md](platform-foundation-event-taxonomy.md)
- [../growth-platform/posthog-product-taxonomy-and-privacy-baseline.md](../growth-platform/posthog-product-taxonomy-and-privacy-baseline.md)
- [../growth-platform/posthog-feature-flag-governance.md](../growth-platform/posthog-feature-flag-governance.md)
- [../plans/2026-04-22-platform-foundation-p3-6-posthog-bridge-and-flag-wrapper-execution-packet.md](../plans/2026-04-22-platform-foundation-p3-6-posthog-bridge-and-flag-wrapper-execution-packet.md)

## 1. Canonical Decisions

1. Critical commercial events do not go browser -> PostHog directly.
2. Authoritative commercial analytics enters through a server-side or `nats_bridge` path.
3. Frontend UX events use a same-origin internal route with allowlisted payloads.
4. Product feature flags are consumed through a typed wrapper with deterministic default-off fallback.
5. Product flag wrappers may bootstrap fallback values before live server-side identity wiring exists.

## 2. First Authoritative Bridge Mappings

The `P3.6` repository slice freezes the first authoritative bridge mappings:

| Source event | Source class | PostHog event | Distinct ID source |
|---|---|---|---|
| `order.finalized` | `nats_bridge` | `checkout_payment_captured` | `actor_context.principal_id` |
| `invite.redeemed` | `nats_bridge` | `partner_user_activated` | `event_payload.redeemer_user_id` or `actor_context.principal_id` |

Rules:

1. Unsupported source events are ignored, not loosely guessed into analytics names.
2. Every bridge payload carries `source_event_type`, `source_event_key`, `source_event_version`, and `source_class`.
3. `$insert_id` equals the authoritative outbox event key for idempotent downstream capture.

## 3. Frontend Product Event Ingestion Path

The first frontend-safe internal ingestion path is:

```text
client reporter
  -> same-origin /api/analytics/product-events
  -> allowlist + privacy sanitation
  -> server-side PostHog capture helper
```

Allowed frontend event names in this repository slice:

- `partner_dashboard_viewed`
- `feature_flag_evaluated`
- `experiment_exposure_recorded`

Blocked behavior:

- arbitrary raw SDK calls spread across the UI
- direct browser delivery of commercial events
- raw email, IP, VPN activity, or destination data in product-event payloads

## 4. Typed Feature-Flag Wrapper Model

The first governed product-flag contracts are:

- `partner_portal_dashboard_spotlight_v1`
- `partner_portal_realtime_workspace_feed_v1`

Wrapper model:

```text
server helper
  -> optional PostHog server evaluation when distinct_id is available
  -> otherwise deterministic default-off bootstrap
  -> ProductIntelligenceProvider
  -> typed hook useProductFeatureFlag(flag_key)
```

Rules:

1. Undefined or unavailable evaluation becomes the contract fallback.
2. The wrapper exposes `evaluationSource` so the app knows whether a value is `server_evaluated`, `fallback`, or `disabled`.
3. The wrapper exists even before live identified server-side evaluation is wired to every route.

## 5. P3.6 Repository-Slice Limits

This repository slice intentionally does **not** claim:

- live PostHog availability or capture smoke;
- live server-side identified flag evaluation in dashboard requests;
- live experiment exposure analytics;
- full dashboard/onboarding/retention dashboard population.

Those remain later closure work for `P3.6+` and `P3.7`.
