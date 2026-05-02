# CyberVPN Platform Foundation P3.7 PostHog Dashboard Foundation Evidence Pack

**Date:** 2026-04-23  
**Status:** in progress  
**Packet:** `P3.7`  
**Phase:** `P3`  
**Primary owners:** `growth-platform`  
**Supporting owners:** `backend-platform`, `partner-platform`, `transport-backend`, `docs-program`

---

## 1. Scope And Packet Links

This evidence pack belongs to:

- [2026-04-23-platform-foundation-p3-7-posthog-dashboard-foundation-execution-packet.md](../../../../plans/2026-04-23-platform-foundation-p3-7-posthog-dashboard-foundation-execution-packet.md)
- [2026-04-21-platform-foundation-phased-implementation-plan.md](../../../../plans/2026-04-21-platform-foundation-phased-implementation-plan.md)
- [platform-foundation-posthog-dashboard-foundation-spec.md](../../../../api/platform-foundation-posthog-dashboard-foundation-spec.md)

Important gate note:

- `Gate D` still cannot be claimed.
- `P3.7` carries `EX-036` as the formal reason later work may continue while live
  `PostHog` dashboards and deployed runtime evidence are still absent.

---

## 2. Result Snapshot

Current `P3.7` result:

- the backend now exposes a first retention-side authoritative bridge mapping:
  - `entitlement.grant.activated -> subscription_activated`
- the partner app now contains a typed dashboard contract registry for:
  - `checkout_funnel_v1`
  - `onboarding_funnel_v1`
  - `partner_workspace_usage_v1`
  - `retention_lifecycle_v1`
- checkout and onboarding UX event builders now exist as governed payload factories;
- checkout and onboarding route-level reporters now emit the first dashboard-feeding UX
  events through the same-origin product-intelligence route;
- retention follow-ups are explicitly partial:
  - `subscription_renewed`
  - `subscription_cancelled`
  remain reserved and are not falsely claimed live.

This packet is **not yet claimed complete** because:

- there is no live `PostHog` dashboard or insight provisioning evidence;
- there is no live checkout/onboarding capture proof from a deployed partner runtime;
- there is no live authoritative consumer evidence populating dashboards end to end;
- retention lifecycle remains intentionally partial until renewal/cancellation signals exist.

---

## 3. Verification Evidence

All commands below were executed on 2026-04-23 in the repository workspace.

### 3.1 Partner Product-Intelligence Tests

```bash
cd partner
npx vitest run \
  src/lib/product-intelligence/__tests__/contracts.test.ts \
  src/lib/product-intelligence/__tests__/server.test.ts \
  src/lib/product-intelligence/__tests__/dashboard-contracts.test.ts \
  src/lib/product-intelligence/__tests__/event-builders.test.ts \
  src/app/api/analytics/product-events/route.test.ts \
  src/app/providers/__tests__/product-intelligence-provider.test.tsx
```

Result:

- `Test Files  6 passed (6)`
- `Tests  18 passed (18)`

### 3.2 Partner Targeted Lint

```bash
cd partner
npx eslint \
  src/lib/product-intelligence/contracts.ts \
  src/lib/product-intelligence/server.ts \
  src/lib/product-intelligence/client.ts \
  src/lib/product-intelligence/dashboard-contracts.ts \
  src/lib/product-intelligence/event-builders.ts \
  src/lib/product-intelligence/__tests__/contracts.test.ts \
  src/lib/product-intelligence/__tests__/server.test.ts \
  src/lib/product-intelligence/__tests__/dashboard-contracts.test.ts \
  src/lib/product-intelligence/__tests__/event-builders.test.ts \
  src/app/providers/product-intelligence-provider.tsx \
  src/app/providers/__tests__/product-intelligence-provider.test.tsx \
  src/shared/ui/atoms/product-analytics-reporter.tsx \
  src/app/api/analytics/product-events/route.ts \
  src/app/api/analytics/product-events/route.test.ts \
  src/features/storefront-shell/components/storefront-checkout-analytics-reporter.tsx \
  src/features/storefront-shell/components/storefront-checkout-shell.tsx \
  src/features/partner-onboarding/components/partner-onboarding-analytics-reporter.tsx \
  src/features/partner-onboarding/components/application-foundation-page.tsx
```

Result:

- targeted eslint completed successfully with no remaining diagnostics

### 3.3 Backend Bridge Tests

```bash
cd backend
.venv/bin/python -m pytest --no-cov tests/unit/application/services/test_posthog_bridge.py
```

Result:

- `5 passed in 0.09s`

### 3.4 Backend Syntax Check

```bash
cd backend
.venv/bin/python -m py_compile src/application/services/posthog_bridge.py
```

Result:

- compilation completed successfully

### 3.5 Typecheck Advisory

Advisory commands executed:

```bash
cd partner
npx tsc --noEmit
```

```bash
cd partner
(npx tsc --noEmit || true) | rg 'product-intelligence/dashboard-contracts|application-foundation-page|storefront-checkout-shell|partner-onboarding-analytics-reporter|storefront-checkout-analytics-reporter|event-builders'
```

Observed result:

- full `partner` typecheck is still blocked by a pre-existing repo-wide TypeScript backlog
  outside the `P3.7` files;
- the filtered advisory command produced no matches for the `P3.7` surfaces, so the
  current packet did not add new `tsc` regressions after the final fixes.

### 3.6 Local Foundation Coverage

Observed validated baseline:

- dashboard contracts cover the four canonical `P3.7` slices and validate against the
  governed event catalog;
- checkout route instrumentation now emits:
  - `checkout_started`
  - `checkout_step_viewed`
  - `checkout_payment_submitted`
  - `checkout_step_completed`
- onboarding instrumentation now emits:
  - `onboarding_started`
  - `onboarding_step_completed`
- retention lifecycle now has an authoritative server-side anchor beyond payment capture:
  - `subscription_activated`

---

## 4. Remaining Live Closure Requirements

`P3.7` can only move from "repo slice complete" to "packet complete" when:

1. a deployed partner runtime proves governed checkout and onboarding events entering live
   `PostHog`;
2. at least one live `PostHog` dashboard or insight view is populated from the frozen
   contract set;
3. at least one authoritative commercial signal and one governed UX signal are both visible
   in the live dashboard foundation;
4. retention lifecycle receives its documented next-step signals or an approved superseding
   decision explicitly redefines the partial scope;
5. `EX-036` is removed from the exceptions register.

