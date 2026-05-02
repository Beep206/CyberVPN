# CyberVPN Platform Foundation P3.7 PostHog Dashboard Foundation Execution Packet

**Date:** 2026-04-23  
**Status:** implementation in progress; repo foundation slice complete, live dashboard evidence pending  
**Packet:** `P3.7`  
**Primary owners:** `growth-platform`  
**Supporting owners:** `backend-platform`, `partner-platform`, `transport-backend`, `docs-program`

---

## 1. Packet Role

This document is the execution packet for `P3.7` in the platform-foundation roadmap.

It is the implementation companion to:

- [2026-04-21-platform-foundation-phased-implementation-plan.md](2026-04-21-platform-foundation-phased-implementation-plan.md)
- [2026-04-21-platform-foundation-target-state-architecture.md](2026-04-21-platform-foundation-target-state-architecture.md)
- [2026-04-21-platform-foundation-temporary-exceptions-register.md](2026-04-21-platform-foundation-temporary-exceptions-register.md)
- [2026-04-22-platform-foundation-p3-6-posthog-bridge-and-flag-wrapper-execution-packet.md](2026-04-22-platform-foundation-p3-6-posthog-bridge-and-flag-wrapper-execution-packet.md)
- [../api/platform-foundation-posthog-dashboard-foundation-spec.md](../api/platform-foundation-posthog-dashboard-foundation-spec.md)
- [../api/platform-foundation-posthog-bridge-and-flag-wrapper-spec.md](../api/platform-foundation-posthog-bridge-and-flag-wrapper-spec.md)

`P3.7` exists to introduce the first canonical `PostHog` dashboard foundation for:

- checkout funnel;
- onboarding funnel;
- partner workspace usage;
- retention lifecycle.

Implementation note:

- this packet is executed as a pre-launch `repo/validation` slice because there is no live
  `PostHog` runtime, no live insight provisioning, and no live partner runtime evidence in
  the current session;
- the repository slice is implemented and locally validated;
- remaining closure work is live dashboard population, live authoritative signal proof, and
  live capture evidence across checkout and onboarding flows.

---

## 2. Canonical Decisions For P3.7

1. `P3.7` freezes dashboard contracts in-repo before any live dashboard UI becomes
   authoritative by convention.
2. Checkout and onboarding dashboards may use governed frontend UX events, but their
   authoritative commercial anchors remain server-side or `nats_bridge`.
3. The first retention dashboard slice uses `subscription_activated` as the authoritative
   activation signal and does not pretend renewal or cancellation are live if they are not.
4. Dashboard contracts are validated against the governed event catalog and may not depend
   on undefined event names.
5. `P3.7` is allowed to remain partial only where the partiality is explicit and documented
   as reserved follow-up work.

---

## 3. Scope

In scope for `P3.7`:

- extend `backend/` with the first retention-side authoritative bridge mapping:
  - `entitlement.grant.activated -> subscription_activated`;
- extend `partner/` with:
  - typed dashboard contracts;
  - typed checkout and onboarding event builders;
  - checkout route and submission instrumentation;
  - onboarding route and stage-completion instrumentation;
- add focused tests for dashboard contracts, event builders, and authoritative bridge
  mappings;
- update packet evidence and program records.

Out of scope for this repository slice:

- live `PostHog` dashboard creation through a deployment or API bootstrap path;
- live renewal or cancellation retention events;
- live experiment population for partner workspace usage dashboards;
- live screenshot or funnel-proof evidence from a deployed partner runtime.

---

## 4. Resulting Repository Touchpoints

- `backend/src/application/services/posthog_bridge.py`
- `backend/tests/unit/application/services/test_posthog_bridge.py`
- `partner/src/lib/product-intelligence/contracts.ts`
- `partner/src/lib/product-intelligence/dashboard-contracts.ts`
- `partner/src/lib/product-intelligence/event-builders.ts`
- `partner/src/lib/product-intelligence/__tests__/contracts.test.ts`
- `partner/src/lib/product-intelligence/__tests__/dashboard-contracts.test.ts`
- `partner/src/lib/product-intelligence/__tests__/event-builders.test.ts`
- `partner/src/features/storefront-shell/components/storefront-checkout-analytics-reporter.tsx`
- `partner/src/features/storefront-shell/components/storefront-checkout-shell.tsx`
- `partner/src/features/partner-onboarding/components/partner-onboarding-analytics-reporter.tsx`
- `partner/src/features/partner-onboarding/components/application-foundation-page.tsx`
- `partner/README.md`
- [../evidence/platform-foundation/2026-04-23/p3-7-posthog-dashboard-foundation/evidence-pack.md](../evidence/platform-foundation/2026-04-23/p3-7-posthog-dashboard-foundation/evidence-pack.md)

