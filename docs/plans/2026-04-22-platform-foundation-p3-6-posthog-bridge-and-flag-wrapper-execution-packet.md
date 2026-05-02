# CyberVPN Platform Foundation P3.6 PostHog Bridge And Flag Wrapper Execution Packet

**Date:** 2026-04-22  
**Status:** implementation in progress; repo foundation slice complete, live PostHog evidence pending  
**Packet:** `P3.6`  
**Primary owners:** `growth-platform`  
**Supporting owners:** `backend-platform`, `partner-platform`, `transport-backend`, `docs-program`

---

## 1. Packet Role

This document is the execution packet for `P3.6` in the platform-foundation roadmap.

It is the implementation companion to:

- [2026-04-21-platform-foundation-phased-implementation-plan.md](2026-04-21-platform-foundation-phased-implementation-plan.md)
- [2026-04-21-platform-foundation-target-state-architecture.md](2026-04-21-platform-foundation-target-state-architecture.md)
- [2026-04-21-platform-foundation-temporary-exceptions-register.md](2026-04-21-platform-foundation-temporary-exceptions-register.md)
- [2026-04-22-platform-foundation-p1-4-posthog-nonprod-foundation-execution-packet.md](2026-04-22-platform-foundation-p1-4-posthog-nonprod-foundation-execution-packet.md)
- [2026-04-22-platform-foundation-p2-6-event-backbone-execution-packet.md](2026-04-22-platform-foundation-p2-6-event-backbone-execution-packet.md)
- [../api/platform-foundation-posthog-bridge-and-flag-wrapper-spec.md](../api/platform-foundation-posthog-bridge-and-flag-wrapper-spec.md)
- [../growth-platform/posthog-product-taxonomy-and-privacy-baseline.md](../growth-platform/posthog-product-taxonomy-and-privacy-baseline.md)
- [../growth-platform/posthog-feature-flag-governance.md](../growth-platform/posthog-feature-flag-governance.md)

`P3.6` exists to connect `PostHog` to the canonical product-event taxonomy through:

- authoritative server-side bridge mappings for commercial events;
- same-origin internal ingestion for governed frontend UX events;
- a typed product feature-flag wrapper with deterministic default-off fallback.

Implementation note:

- this packet is executed as a pre-launch `repo/validation` slice because there is no live
  `PostHog` runtime, no live authoritative bridge consumer, and no live identified
  server-side flag evaluation evidence in the current session;
- the repository slice is implemented and locally validated;
- remaining closure work is live capture, live authoritative bridge execution, and live
  identified feature-flag bootstrap evidence.

---

## 2. Canonical Decisions For P3.6

1. Critical commercial events do not go browser -> `PostHog` directly.
2. Authoritative commercial analytics enters through a server-side or `nats_bridge` path.
3. Frontend UX events use a same-origin internal route with allowlisted payloads.
4. Product feature flags are consumed only through a typed wrapper with deterministic
   fallback.
5. The wrapper may expose `server_evaluated`, `fallback`, or `disabled` bootstrap source;
   undefined evaluation never becomes implicit feature enablement.

---

## 3. Scope

In scope for `P3.6`:

- extend `backend/` with an authoritative `PostHog` bridge mapper for the first commercial
  event families;
- extend `partner/` with:
  - typed product-event contracts and privacy sanitation;
  - server-side `posthog-node` helper;
  - same-origin internal product-event route;
  - product-intelligence provider and typed feature-flag hook;
  - dashboard-level bootstrap and governed event reporter;
- add focused tests for route sanitation, server helper behavior, typed wrapper fallback,
  and backend bridge mappings;
- update packet evidence and program records.

Out of scope for this repository slice:

- live `PostHog` project bootstrap or runtime smoke against a deployed host;
- live authoritative consumer wired from the real outbox dispatcher or NATS consumer;
- live experiment management or retention dashboards;
- live identified flag evaluation for every dashboard route or user session.

---

## 4. Resulting Repository Touchpoints

- `backend/src/application/services/posthog_bridge.py`
- `backend/tests/unit/application/services/test_posthog_bridge.py`
- `partner/src/lib/product-intelligence/contracts.ts`
- `partner/src/lib/product-intelligence/server.ts`
- `partner/src/lib/product-intelligence/client.ts`
- `partner/src/app/providers/product-intelligence-provider.tsx`
- `partner/src/shared/ui/atoms/product-analytics-reporter.tsx`
- `partner/src/app/api/analytics/product-events/route.ts`
- `partner/src/app/api/analytics/product-events/route.test.ts`
- `partner/src/lib/product-intelligence/__tests__/contracts.test.ts`
- `partner/src/lib/product-intelligence/__tests__/server.test.ts`
- `partner/src/app/providers/__tests__/product-intelligence-provider.test.tsx`
- `partner/src/app/[locale]/(dashboard)/layout.tsx`
- `partner/package.json`
- `partner/README.md`
- [../evidence/platform-foundation/2026-04-22/p3-6-posthog-bridge-and-flag-wrapper/evidence-pack.md](../evidence/platform-foundation/2026-04-22/p3-6-posthog-bridge-and-flag-wrapper/evidence-pack.md)

